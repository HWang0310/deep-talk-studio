import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import prepare_codex_materials, run_codex_material_review
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

    def test_all_four_visual_types_have_motion_mapping(self):
        mapping = {
            "timeline": "timeline_motion", "bar": "bar_motion",
            "comparison": "comparison_motion", "diagram": "diagram_motion",
        }
        for visual_type, expected in mapping.items():
            with self.subTest(visual_type=visual_type):
                package = self.package.to_dict()
                visual = package["generated_visuals"][0]
                visual["visual_type"] = visual_type
                plan = prepare_production_plan(
                    type(self.package)(package), self.script, self.report,
                    self.production_profile, self.root / "assets",
                    created_at="2026-08-11T12:00:00+08:00",
                    production_id="PROD-" + visual_type, renderer_mode="remotion",
                )
                self.assertEqual(plan["scenes"][1]["scene_type"], expected)

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

    def test_numeric_visual_title_is_factual_and_must_be_grounded(self):
        package = self.package.to_dict()
        package["generated_visuals"][0]["title"] = "2026 年事件核查"
        plan = prepare_production_plan(
            type(self.package)(package), self.script, self.report, self.production_profile,
            self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-numeric-title", renderer_mode="remotion",
        )
        title = plan["scenes"][1]["on_screen_text"][0]
        self.assertEqual(title["text_kind"], "factual")
        self.assertEqual(title["claim_ids"], ["C1", "C2"])

        package["generated_visuals"][0]["title"] = "999 年事件核查"
        with self.assertRaisesRegex(ProductionValidationError, "999"):
            prepare_production_plan(
                type(self.package)(package), self.script, self.report, self.production_profile,
                self.root / "assets", created_at="2026-08-11T12:00:00+08:00",
                production_id="PROD-bad-title", renderer_mode="remotion",
            )


if __name__ == "__main__":
    unittest.main()
