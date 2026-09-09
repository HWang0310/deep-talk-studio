import json
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import prepare_codex_materials, run_codex_material_review
from deeptalk_studio.production_planner import prepare_production_plan
from deeptalk_studio.production_profile import load_production_profile
from deeptalk_studio.production_renderers import get_renderer
from deeptalk_studio.production_renderers.base import RendererError, run_command, run_renderer_check
from deeptalk_studio.production_renderers.remotion import browser_executable_args
from deeptalk_studio.production_renderers.hyperframes import hyperframes_browser_env
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


class ProductionRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report, self.script, _ = reviewed_inputs()
        material_profile = load_material_profile()
        prepared = prepare_codex_materials(
            valid_material_content(), self.script, self.report,
            self.root / "packages", self.root / "material-assets", material_profile,
            inspection_manifest(), rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-renderer",
        )
        reviewed = run_codex_material_review(
            passing_review(), prepared.package, self.script, self.report,
            self.root / "packages", material_profile,
            created_at="2026-08-11T11:00:00+08:00", review_id="MRV-renderer",
        )
        self.package = validate_production_input(
            reviewed.paths.json, self.script, self.report, material_profile
        )
        self.profile = load_production_profile()
        self.plan = prepare_production_plan(
            self.package, self.script, self.report, self.profile,
            self.root / "material-assets", created_at="2026-08-11T12:00:00+08:00",
            production_id="PROD-renderer", renderer_mode="remotion",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_factory_returns_both_renderers_and_clean_error_for_unknown(self):
        self.assertEqual(get_renderer("remotion").name, "remotion")
        self.assertEqual(get_renderer("hyperframes").name, "hyperframes")
        with self.assertRaisesRegex(RendererError, "不支持"):
            get_renderer("unknown")

    def test_remotion_can_reuse_an_existing_browser_instead_of_downloading_one(self):
        browser = self.root / "Chrome"
        browser.write_bytes(b"executable")
        browser.chmod(0o755)
        self.assertEqual(
            browser_executable_args(str(browser)),
            (f"--browser-executable={browser.resolve()}",),
        )
        self.assertEqual(
            hyperframes_browser_env(str(browser)),
            {"HYPERFRAMES_BROWSER_PATH": str(browser.resolve())},
        )

    def test_command_runner_records_exit_output_and_turns_failure_into_clean_error(self):
        success = run_command([sys.executable, "-c", "print('ok')"], self.root)
        self.assertEqual(success.exit_code, 0)
        self.assertIn("ok", success.stdout_summary)
        with self.assertRaisesRegex(RendererError, "执行失败"):
            run_command([sys.executable, "-c", "raise SystemExit(4)"], self.root)
        inherited = run_command(
            [sys.executable, "-c", "import os; print(os.environ['DEEPTALK_TEST_ENV'])"],
            self.root, env={"DEEPTALK_TEST_ENV": "safe-browser"},
        )
        self.assertIn("safe-browser", inherited.stdout_summary)

    def test_structured_check_summary_redacts_local_paths_and_preview_addresses(self):
        result = run_renderer_check(
            "privacy", "remotion", "validate",
            [sys.executable, "-c", "import os; print(os.getcwd()); print('http://192.168.0.8:3210')"],
            self.root,
        )
        self.assertEqual(result.outcome, "pass")
        self.assertNotIn(str(self.root), result.summary)
        self.assertNotIn("192.168.0.8", result.summary)
        self.assertIn("<project>", result.summary)
        self.assertIn("<local-preview>", result.summary)

    def test_remotion_project_consumes_plan_and_only_stages_allowed_assets(self):
        project = get_renderer("remotion").prepare_project(
            self.plan, self.package, self.profile, self.root / "material-assets",
            self.root / "projects",
        )
        stored = json.loads(project.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(stored, self.plan)
        asset_map = json.loads((project.project_dir / "src/asset-map.json").read_text(encoding="utf-8"))
        self.assertEqual(asset_map, {})
        self.assertFalse(project.staged_assets)
        source = (project.project_dir / "src/ProductionComposition.tsx").read_text(encoding="utf-8")
        self.assertIn("useCurrentFrame", source)
        self.assertIn("interpolate", source)
        self.assertIn("staticFile", source)
        self.assertIn("TimelineMotion", source)
        self.assertIn("BarMotion", source)
        self.assertIn("ComparisonMotion", source)
        self.assertIn("DiagramMotion", source)
        self.assertIn('data-motion-element="timeline-marker"', source)
        self.assertIn('data-motion-element="bar"', source)
        self.assertNotIn("source_visual_ids[0]", source)
        self.assertNotIn("animation:", source)
        self.assertNotIn("transition:", source)
        self.assertNotIn("https://example.com", json.dumps(asset_map))

    def test_remotion_timeline_keeps_edge_text_inside_safe_area(self):
        project = get_renderer("remotion").prepare_project(
            self.plan, self.package, self.profile, self.root / "material-assets",
            self.root / "safe-area-projects",
        )
        source = (project.project_dir / "src/ProductionComposition.tsx").read_text(
            encoding="utf-8"
        )
        self.assertIn("const x1 = 300;", source)
        self.assertIn("const x2 = 1620;", source)
        self.assertIn('foreignObject x={x - 240}', source)
        self.assertIn('width="480"', source)

    def test_remotion_uses_three_comparison_cards_and_safe_diagram_labels(self):
        project = get_renderer("remotion").prepare_project(
            self.plan, self.package, self.profile, self.root / "material-assets",
            self.root / "readability-projects",
        )
        source = (project.project_dir / "src/ProductionComposition.tsx").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-motion-element="comparison-card"', source)
        self.assertNotIn('gridTemplateColumns: "1fr 1fr"', source)
        self.assertEqual(source.count("{item.label.text}"), 1)
        self.assertIn("overflowWrap: \"anywhere\"", source)
        self.assertIn('data-motion-element="diagram-edge-label-plate"', source)
        self.assertIn('data-motion-element="diagram-node-label"', source)
        self.assertIn("overflow: \"hidden\"", source)

    def test_hyperframes_uses_same_card_and_diagram_layout_contract(self):
        from deeptalk_studio.production_planner import production_plan_digest
        grounded = self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["label"]
        cases = {
            "comparison": {
                "comparison_items": [
                    {"order": index, "label": dict(grounded, text=label),
                     "left_text": dict(grounded, text=f"第 {index} 项已核查事实甲"),
                     "right_text": dict(grounded, text=f"第 {index} 项已核查事实乙")}
                    for index, label in enumerate(("SAFE 草案", "加州 SB-53", "NASA"), 1)
                ],
            },
            "diagram": {
                "diagram_nodes": [
                    {"order": index, "node_id": f"N{index}",
                     "label": dict(grounded, text=label)}
                    for index, label in enumerate((
                        "软件包代理中的未知漏洞", "第三方代码执行环境",
                        "Hugging Face 数据处理漏洞", "多重信任边界",
                    ), 1)
                ],
                "diagram_edges": [
                    {"order": index, "from_node": f"N{index}", "to_node": f"N{index + 1}",
                     "label": dict(grounded, text=label)}
                    for index, label in enumerate((
                        "离开隔离环境", "再借第三方代码执行环境", "跨越多重信任边界",
                    ), 1)
                ],
            },
        }
        for index, (kind, updates) in enumerate(cases.items(), 1):
            plan = json.loads(json.dumps(self.plan))
            plan["production_id"] = f"PROD-hyperframes-{kind}"
            plan["selected_renderer"] = "hyperframes"
            plan["renderer_mode"] = "hyperframes"
            scene = plan["scenes"][1]
            scene["scene_type"] = kind + "_motion"
            scene["on_screen_text"] = [dict(grounded, text="要点对照" if kind == "comparison" else "关系说明")]
            payload = scene["scene_payload"]
            for key in ("timeline_events", "bar_data_points", "comparison_items", "diagram_nodes", "diagram_edges"):
                payload[key] = updates.get(key, [])
            payload["payload_type"] = kind
            plan["plan_digest"] = production_plan_digest(plan)
            project = get_renderer("hyperframes").prepare_project(
                plan, self.package, self.profile, self.root / "material-assets",
                self.root / f"hyperframes-readability-projects-{index}",
            )
            source = (project.project_dir / "compositions/S002.html").read_text(encoding="utf-8")
            if kind == "comparison":
                self.assertEqual(source.count('data-motion-element="comparison-card"'), 3)
                for label in ("SAFE 草案", "加州 SB-53", "NASA"):
                    self.assertEqual(source.count(label), 1)
                self.assertNotIn('class="comparison-side right"', source)
            else:
                self.assertIn("Hugging Face 数据处理漏洞", source)
                self.assertEqual(source.count('data-motion-element="diagram-edge-label-plate"'), 3)
                self.assertEqual(source.count('data-motion-element="diagram-node-label"'), 4)
            self.assertIn("overflow-wrap:anywhere", source)

    def test_hyperframes_project_has_design_first_and_deterministic_timeline_contract(self):
        plan = dict(self.plan, selected_renderer="hyperframes", renderer_mode="hyperframes")
        from deeptalk_studio.production_planner import production_plan_digest
        plan["plan_digest"] = production_plan_digest(plan)
        project = get_renderer("hyperframes").prepare_project(
            plan, self.package, self.profile, self.root / "material-assets",
            self.root / "projects",
        )
        design = (project.project_dir / "DESIGN.md").read_text(encoding="utf-8")
        html = (project.project_dir / "index.html").read_text(encoding="utf-8")
        standalone = (project.project_dir / "compositions/S002.html").read_text(encoding="utf-8")
        self.assertIn(self.profile["design_tokens"]["colors"]["accent"], design)
        self.assertIn('data-composition-id="main"', html)
        self.assertIn("data-start=", html)
        self.assertIn("data-duration=", html)
        self.assertIn("data-track-index=", html)
        self.assertIn('class="scene clip"', html)
        self.assertIn('data-motion-element="timeline-baseline"', standalone)
        self.assertEqual(standalone.count('data-motion-element="timeline-marker"'), 1)
        self.assertIn("timeline-marker-1", standalone)
        self.assertNotIn('../assets/', standalone)
        self.assertIn("gsap.timeline({ paused: true })", html)
        self.assertIn('window.__timelines["main"] = tl', html)
        self.assertNotIn("Math.random", html)
        self.assertNotIn("Date.now", html)
        self.assertNotIn("repeat: -1", html)
        self.assertNotIn('tl.to("#scene-', html)
        self.assertNotIn("https://example.com", html)

    def test_projects_are_immutable_and_do_not_copy_reference_only_files(self):
        renderer = get_renderer("remotion")
        renderer.prepare_project(
            self.plan, self.package, self.profile, self.root / "material-assets",
            self.root / "projects",
        )
        with self.assertRaisesRegex(RendererError, "覆盖"):
            renderer.prepare_project(
                self.plan, self.package, self.profile, self.root / "material-assets",
                self.root / "projects",
            )

    def test_both_projects_expose_independent_motion_elements_for_all_four_payloads(self):
        payloads = {
            "bar": ("bar_data_points", [{"order": i, "label": self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["label"], "value": i, "value_label": self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["date"]} for i in range(1, 4)], "bar"),
            "comparison": ("comparison_items", [{"order": i, "label": self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["label"], "left_text": self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["label"], "right_text": self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["label"]} for i in range(1, 3)], "comparison-card"),
            "diagram": ("diagram_nodes", [{"order": i, "node_id": f"N{i}", "label": self.plan["scenes"][1]["scene_payload"]["timeline_events"][0]["label"]} for i in range(1, 4)], "diagram-node"),
        }
        from deeptalk_studio.production_planner import production_plan_digest
        for index, (kind, (field, elements, marker)) in enumerate(payloads.items(), 1):
            with self.subTest(kind=kind):
                plan = json.loads(json.dumps(self.plan))
                plan["production_id"] = f"PROD-semantic-{kind}"
                scene = plan["scenes"][1]
                scene["scene_type"] = kind + "_motion"
                payload = scene["scene_payload"]
                for key in ("timeline_events", "bar_data_points", "comparison_items", "diagram_nodes", "diagram_edges"):
                    payload[key] = []
                payload["payload_type"] = kind
                payload[field] = elements
                if kind == "diagram":
                    payload["diagram_edges"] = [{"order": 1, "from_node": "N1", "to_node": "N2", "label": elements[0]["label"]}]
                plan["plan_digest"] = production_plan_digest(plan)
                project = get_renderer("hyperframes").prepare_project(
                    plan, self.package, self.profile, self.root / "material-assets",
                    self.root / f"semantic-projects-{index}",
                )
                html = (project.project_dir / "compositions/S002.html").read_text(encoding="utf-8")
                self.assertEqual(html.count(f'data-motion-element="{marker}"'), len(elements))


if __name__ == "__main__":
    unittest.main()
