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
from deeptalk_studio.production_renderers.base import RendererError, run_command
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

    def test_remotion_project_consumes_plan_and_only_stages_allowed_assets(self):
        project = get_renderer("remotion").prepare_project(
            self.plan, self.package, self.profile, self.root / "material-assets",
            self.root / "projects",
        )
        stored = json.loads(project.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(stored, self.plan)
        asset_map = json.loads((project.project_dir / "src/asset-map.json").read_text(encoding="utf-8"))
        self.assertEqual(set(asset_map), {"V001"})
        source = (project.project_dir / "src/ProductionComposition.tsx").read_text(encoding="utf-8")
        self.assertIn("useCurrentFrame", source)
        self.assertIn("interpolate", source)
        self.assertIn("staticFile", source)
        self.assertIn("const revealRight", source)
        self.assertIn("isCompleteGeneratedVisual", source)
        self.assertIn("transform: `translateY", source)
        self.assertNotIn('["inset(', source)
        self.assertNotIn("animation:", source)
        self.assertNotIn("transition:", source)
        self.assertNotIn("https://example.com", json.dumps(asset_map))

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
        self.assertIn("complete-generated-visual", html)
        self.assertNotIn('../assets/', standalone)
        self.assertIn("gsap.timeline({ paused: true })", html)
        self.assertIn('window.__timelines["main"] = tl', html)
        self.assertNotIn("Math.random", html)
        self.assertNotIn("Date.now", html)
        self.assertNotIn("repeat: -1", html)
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


if __name__ == "__main__":
    unittest.main()
