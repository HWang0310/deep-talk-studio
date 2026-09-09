import tempfile
import unittest
import hashlib
from copy import deepcopy
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import prepare_codex_materials, run_codex_material_review
from deeptalk_studio.models import ResearchReport
from deeptalk_studio.production_planner import (
    prepare_production_plan,
    production_plan_digest,
    validate_production_plan,
)
from deeptalk_studio.production_profile import (
    ProductionValidationError,
    load_production_profile,
)
from deeptalk_studio.production_validation import validate_production_input
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


def passing_review():
    return {
        "issues": [],
        "checks": [
            {"check_name": name, "outcome": "pass", "reason": "检查完成。"}
            for name in MATERIAL_REVIEW_CHECK_NAMES
        ],
        "overall_notes": "通过。",
    }


class ProductionPlannerTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.material_profile = load_material_profile()
        self.production_profile = load_production_profile()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        prepared = prepare_codex_materials(
            valid_material_content(), self.script, self.report,
            self.root / "packages", self.root / "assets", self.material_profile,
            inspection_manifest(), rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-plan",
        )
        reviewed = run_codex_material_review(
            passing_review(), prepared.package, self.script, self.report,
            self.root / "packages", self.material_profile,
            created_at="2026-08-11T11:00:00+08:00", review_id="MRV-plan",
        )
        self.package = validate_production_input(
            reviewed.paths.json, self.script, self.report, self.material_profile
        )

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, mode="auto"):
        return prepare_production_plan(
            self.package, self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-test", renderer_mode=mode,
        )

    def test_plan_maps_grounded_visual_and_uses_aroll_for_missing_safe_file(self):
        plan = self.plan()
        self.assertEqual([scene["scene_id"] for scene in plan["scenes"]], ["S001", "S002"])
        self.assertEqual(plan["scenes"][0]["scene_type"], "aroll_placeholder")
        self.assertEqual(plan["scenes"][1]["scene_type"], "timeline_motion")
        self.assertEqual(plan["scenes"][1]["source_visual_ids"], ["V001"])
        payload = plan["scenes"][1]["scene_payload"]
        self.assertEqual(payload["payload_type"], "timeline")
        self.assertEqual(len(payload["timeline_events"]), 1)
        self.assertEqual(payload["timeline_events"][0]["order"], 1)
        self.assertEqual(payload["timeline_events"][0]["date"]["text"], "2026-08-09")
        self.assertEqual(
            payload["timeline_events"][0]["label"]["text"],
            "事件发生并由机构发布首次说明。",
        )
        self.assertTrue(plan["production_gaps"])
        self.assertIn("真实语音时间码", " ".join(gap["reason"] for gap in plan["production_gaps"]))

    def test_ids_duration_and_digest_are_machine_owned_and_deterministic(self):
        first = self.plan()
        second = self.plan()
        self.assertEqual(first, second)
        self.assertEqual(first["motion_assets"][0]["motion_asset_id"], "MA001")
        for scene in first["scenes"]:
            self.assertEqual(scene["duration_frames"], round(scene["duration_seconds"] * 30))
        self.assertEqual(first["plan_digest"], production_plan_digest(first))
        validate_production_plan(first, self.package, self.script, self.production_profile)

    def test_post_alignment_visual_context_is_bound_without_breaking_legacy_plans(self):
        preference = {"preference_digest": "v" * 64}
        visual_plan = {"plan_digest": "p" * 64}
        plan = prepare_production_plan(
            self.package, self.script, self.report, self.production_profile, self.root / "assets",
            created_at="2026-08-11T12:00:00+08:00", production_id="PROD-visual-context",
            episode_visual_preference=preference, post_alignment_visual_plan=visual_plan,
        )
        self.assertEqual(plan["episode_visual_preference_digest"], "v" * 64)
        self.assertEqual(plan["post_alignment_visual_plan_digest"], "p" * 64)
        validate_production_plan(
            plan, self.package, self.script, self.production_profile,
            episode_visual_preference=preference, post_alignment_visual_plan=visual_plan,
        )

    def test_renderer_auto_is_transparent_and_explicit_modes_are_respected(self):
        self.assertEqual(self.plan("auto")["selected_renderer"], "remotion")
        self.assertEqual(self.plan("remotion")["selected_renderer"], "remotion")
        self.assertEqual(self.plan("hyperframes")["selected_renderer"], "hyperframes")
        with self.assertRaisesRegex(ProductionValidationError, "renderer"):
            self.plan("unknown")

    def test_plan_rejects_invalid_cue_beat_material_visual_or_tampered_binding(self):
        for field, value in (
            ("cue_id", "VC404"), ("beat_id", "B404"),
        ):
            plan = self.plan()
            plan["scenes"][0][field] = value
            plan["plan_digest"] = production_plan_digest(plan)
            with self.subTest(field=field):
                with self.assertRaises(ProductionValidationError):
                    validate_production_plan(
                        plan, self.package, self.script, self.production_profile
                    )
        plan = self.plan()
        plan["scenes"][1]["source_visual_ids"] = ["V404"]
        plan["plan_digest"] = production_plan_digest(plan)
        with self.assertRaisesRegex(ProductionValidationError, "Visual"):
            validate_production_plan(plan, self.package, self.script, self.production_profile)
        plan = self.plan()
        plan["scenes"][0]["source_material_ids"] = ["M404"]
        plan["plan_digest"] = production_plan_digest(plan)
        with self.assertRaisesRegex(ProductionValidationError, "Material"):
            validate_production_plan(plan, self.package, self.script, self.production_profile)
        plan = self.plan()
        plan["scenes"][0]["scene_payload"]["timeline_events"] = deepcopy(
            plan["scenes"][1]["scene_payload"]["timeline_events"]
        )
        plan["plan_digest"] = production_plan_digest(plan)
        with self.assertRaisesRegex(ProductionValidationError, "payload"):
            validate_production_plan(
                plan, self.package, self.script, self.production_profile, report=self.report,
            )

    def test_all_four_visual_types_have_motion_mapping(self):
        mapping = {
            "timeline": "timeline_motion", "bar": "bar_motion",
            "comparison": "comparison_motion", "diagram": "diagram_motion",
        }
        valid_payloads = {
            "timeline": {
                "events": deepcopy(self.package.to_dict()["generated_visuals"][0]["events"]),
            },
            "bar": {
                "data_points": [
                    {"label": "事件", "value": value, "value_label": str(value),
                     "claim_ids": ["C1"], "evidence_link_ids": ["E1"]}
                    for value in (2026, 8)
                ],
            },
            "comparison": {
                "comparison_items": [
                    {"label": "事件", "left_text": "事件在 2026 年 8 月 9 日发生",
                     "right_text": "事件", "claim_ids": ["C1"],
                     "evidence_link_ids": ["E1"]}
                    for _ in range(2)
                ],
            },
            "diagram": {
                "nodes": [
                    {"node_id": "N1", "label": "事件", "claim_ids": ["C1"]},
                    {"node_id": "N2", "label": "流程故障", "claim_ids": ["C2"]},
                ],
                "edges": [
                    {"from_node": "N1", "to_node": "N2", "label": "流程故障"},
                ],
            },
        }
        for visual_type, expected in mapping.items():
            with self.subTest(visual_type=visual_type):
                package = self.package.to_dict()
                visual = package["generated_visuals"][0]
                visual["visual_type"] = visual_type
                for key in ("events", "data_points", "comparison_items", "nodes", "edges"):
                    visual[key] = deepcopy(valid_payloads[visual_type].get(key, []))
                plan = prepare_production_plan(
                    type(self.package)(package), self.script, self.report,
                    self.production_profile, self.root / "assets",
                    created_at="2026-08-11T12:00:00+08:00",
                    production_id="PROD-" + visual_type, renderer_mode="remotion",
                )
                self.assertEqual(plan["scenes"][1]["scene_type"], expected)

    def test_bar_comparison_and_diagram_payloads_preserve_independent_elements(self):
        cases = {
            "bar": {
                "data_points": [
                    {"label": "事件", "value": value, "value_label": str(value),
                     "claim_ids": ["C1"], "evidence_link_ids": ["E1"]}
                    for value in (2026, 8, 9)
                ],
            },
            "comparison": {
                "comparison_items": [
                    {"label": "事件", "left_text": "事件在 2026 年 8 月 9 日发生",
                     "right_text": "事件", "claim_ids": ["C1"],
                     "evidence_link_ids": ["E1"]}
                    for _ in range(2)
                ],
            },
            "diagram": {
                "nodes": [
                    {"node_id": "N1", "label": "事件", "claim_ids": ["C1"]},
                    {"node_id": "N2", "label": "流程故障", "claim_ids": ["C2"]},
                    {"node_id": "N3", "label": "人为操纵", "claim_ids": ["C3"]},
                ],
                "edges": [
                    {"from_node": "N1", "to_node": "N2", "label": "流程故障"},
                    {"from_node": "N2", "to_node": "N3", "label": "人为操纵"},
                ],
            },
        }
        expected_counts = {"bar": 3, "comparison": 2, "diagram": 3}
        for visual_type, updates in cases.items():
            with self.subTest(visual_type=visual_type):
                data = self.package.to_dict()
                visual = data["generated_visuals"][0]
                visual["visual_type"] = visual_type
                for key in ("events", "data_points", "comparison_items", "nodes", "edges"):
                    visual[key] = updates.get(key, [])
                plan = prepare_production_plan(
                    type(self.package)(data), self.script, self.report, self.production_profile,
                    self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
                    production_id="PROD-payload-" + visual_type, renderer_mode="remotion",
                )
                payload = plan["scenes"][1]["scene_payload"]
                key = {"bar": "bar_data_points", "comparison": "comparison_items", "diagram": "diagram_nodes"}[visual_type]
                self.assertEqual(len(payload[key]), expected_counts[visual_type])
                self.assertEqual([item["order"] for item in payload[key]], list(range(1, expected_counts[visual_type] + 1)))

    def test_three_item_comparison_uses_neutral_heading_and_preserves_bindings(self):
        data = self.package.to_dict()
        visual = data["generated_visuals"][0]
        visual["visual_type"] = "comparison"
        visual["events"] = []
        visual["comparison_items"] = [
            {
                "label": "事件", "left_text": "事件在 2026 年 8 月 9 日发生",
                "right_text": "事件", "claim_ids": ["C1"],
                "evidence_link_ids": ["E1"],
            },
            {
                "label": "流程故障", "left_text": "当事机构称原因是流程故障",
                "right_text": "流程故障", "claim_ids": ["C2"],
                "evidence_link_ids": ["E3"],
            },
            {
                "label": "人为操纵", "left_text": "网络流传事件由人为操纵造成",
                "right_text": "人为操纵", "claim_ids": ["C3"],
                "evidence_link_ids": ["E4"],
            },
        ]
        visual["nodes"] = []
        visual["edges"] = []
        plan = prepare_production_plan(
            type(self.package)(data), self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-13T12:00:00+08:00",
            production_id="PROD-comparison-cards", renderer_mode="remotion",
        )
        scene = plan["scenes"][1]
        self.assertEqual(scene["on_screen_text"][0]["text"], "要点对照")
        self.assertNotEqual(scene["on_screen_text"][0]["text"], "两个解释")
        items = scene["scene_payload"]["comparison_items"]
        self.assertEqual([item["label"]["text"] for item in items], ["事件", "流程故障", "人为操纵"])
        for source, item in zip(visual["comparison_items"], items):
            for key in ("label", "left_text", "right_text"):
                self.assertEqual(item[key]["claim_ids"], source["claim_ids"])
                self.assertEqual(item[key]["evidence_link_ids"], source["evidence_link_ids"])

    def test_excessive_diagram_text_fails_before_renderer(self):
        data = self.package.to_dict()
        visual = data["generated_visuals"][0]
        visual["visual_type"] = "diagram"
        visual["events"] = []
        visual["nodes"] = [
            {"node_id": "N1", "label": "事件" * 30, "claim_ids": ["C1"]},
            {"node_id": "N2", "label": "流程故障", "claim_ids": ["C2"]},
        ]
        visual["edges"] = [{"from_node": "N1", "to_node": "N2", "label": "流程故障"}]
        with self.assertRaisesRegex(ProductionValidationError, "Diagram node.*安全布局"):
            prepare_production_plan(
                type(self.package)(data), self.script, self.report, self.production_profile,
                self.root / "assets", created_at="2026-08-13T12:00:00+08:00",
                production_id="PROD-diagram-overflow", renderer_mode="remotion",
            )

    def test_raw_pdf_becomes_exact_gap_but_registered_capture_is_renderable(self):
        data = self.package.to_dict()
        data["generated_visuals"] = []
        item = data["materials"][0]
        pdf = self.root / "assets" / "official.pdf"
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-1.7\nsynthetic")
        item.update(local_path=str(pdf), byte_size=pdf.stat().st_size,
                    sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    eligibility_status="ready_to_use")
        plan = prepare_production_plan(
            type(self.package)(data), self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-pdf-gap", renderer_mode="remotion",
        )
        self.assertIn(
            "文件已取得，但尚无可安全展示的页面截图。",
            [gap["reason"] for gap in plan["production_gaps"]],
        )
        capture = self.root / "assets" / "capture.png"
        capture.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic")
        item.update(asset_type="document_screenshot", local_path=str(capture),
                    byte_size=capture.stat().st_size,
                    sha256=hashlib.sha256(capture.read_bytes()).hexdigest())
        plan = prepare_production_plan(
            type(self.package)(data), self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-capture", renderer_mode="remotion",
        )
        self.assertEqual(plan["scenes"][0]["scene_payload"]["payload_type"], "image")
        self.assertEqual(plan["scenes"][0]["scene_payload"]["image_asset_id"], "M001")

    def test_plan_validator_rederives_payload_and_rejects_hidden_bar_value_tampering(self):
        data = self.package.to_dict()
        visual = data["generated_visuals"][0]
        visual["visual_type"] = "bar"
        visual["events"] = []
        visual["data_points"] = [{
            "label": "事件", "value": 2026, "value_label": "2026",
            "claim_ids": ["C1"], "evidence_link_ids": ["E1"],
        }]
        package = type(self.package)(data)
        plan = prepare_production_plan(
            package, self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-payload-tamper", renderer_mode="remotion",
        )
        plan["scenes"][1]["scene_payload"]["bar_data_points"][0]["value"] = 999
        plan["plan_digest"] = production_plan_digest(plan)
        with self.assertRaisesRegex(ProductionValidationError, "payload"):
            validate_production_plan(
                plan, package, self.script, self.production_profile, report=self.report,
            )

    def test_contested_timeline_preserves_two_exact_research_events_in_order(self):
        report_data = self.report.to_dict()
        report_data["timeline"].append({
            "date": "2026-08-10", "event": "当事机构称原因是流程故障。",
            "claim_ids": ["C2"], "evidence_link_ids": ["E3"],
        })
        report = ResearchReport(report_data)
        data = self.package.to_dict()
        data["generated_visuals"][0]["events"].append({
            "date": "2026-08-10", "label": "当事机构称原因是流程故障。",
            "claim_ids": ["C2"], "evidence_link_ids": ["E3"],
        })
        plan = prepare_production_plan(
            type(self.package)(data), self.script, report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-two-event-timeline", renderer_mode="remotion",
        )
        events = plan["scenes"][1]["scene_payload"]["timeline_events"]
        self.assertEqual([event["order"] for event in events], [1, 2])
        self.assertEqual([event["date"]["text"] for event in events], ["2026-08-09", "2026-08-10"])

    def test_comparison_needs_two_items_and_causal_edge_needs_matching_claim(self):
        for visual_type, updates, message in (
            ("comparison", {
                "comparison_items": [{"label": "事件", "left_text": "事件", "right_text": "事件",
                                      "claim_ids": ["C1"], "evidence_link_ids": ["E1"]}],
            }, "至少.*2"),
            ("diagram", {
                "nodes": [{"node_id": "N1", "label": "事件", "claim_ids": ["C1"]},
                          {"node_id": "N2", "label": "流程故障", "claim_ids": ["C2"]}],
                "edges": [{"from_node": "N1", "to_node": "N2", "label": "事件导致流程故障"}],
            }, "语义"),
        ):
            data = self.package.to_dict()
            visual = data["generated_visuals"][0]
            visual["visual_type"] = visual_type
            for key in ("events", "data_points", "comparison_items", "nodes", "edges"):
                visual[key] = updates.get(key, [])
            with self.subTest(visual_type=visual_type):
                with self.assertRaisesRegex(ProductionValidationError, message):
                    prepare_production_plan(
                        type(self.package)(data), self.script, self.report, self.production_profile,
                        self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
                        production_id="PROD-reject-" + visual_type, renderer_mode="remotion",
                    )

    def test_reference_only_is_never_selected_even_if_it_has_a_local_path(self):
        package = self.package.to_dict()
        item = package["materials"][0]
        item["eligibility_status"] = "reference_only"
        item["local_path"] = package["generated_visuals"][0]["local_path"]
        item["byte_size"] = package["generated_visuals"][0]["byte_size"]
        item["sha256"] = package["generated_visuals"][0]["sha256"]
        plan = prepare_production_plan(
            type(self.package)(package), self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-reference", renderer_mode="auto",
        )
        self.assertNotIn("M001", [mid for scene in plan["scenes"] for mid in scene["source_material_ids"]])

    def test_visual_title_cannot_bypass_grounding_with_a_valid_but_unrelated_claim(self):
        package = self.package.to_dict()
        package["generated_visuals"][0]["title"] = "公司已经承认全部责任"
        plan = prepare_production_plan(
            type(self.package)(package), self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-numeric-title", renderer_mode="remotion",
        )
        self.assertNotIn(
            "公司已经承认全部责任",
            [entry["text"] for entry in plan["scenes"][1]["on_screen_text"]],
        )
        self.assertEqual(plan["scenes"][1]["on_screen_text"][0]["text"], "关键时间点")


if __name__ == "__main__":
    unittest.main()
