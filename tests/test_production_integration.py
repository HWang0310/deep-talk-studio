import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import prepare_codex_materials, run_codex_material_review
from deeptalk_studio.production_planner import prepare_production_plan
from deeptalk_studio.production_profile import load_production_profile
from deeptalk_studio.production_qa import build_motion_asset_manifest, prepare_production_qa
from deeptalk_studio.production_renderers import get_renderer
from tests.material_fixtures import reviewed_inputs, valid_material_content


def review_pass():
    return {
        "issues": [],
        "checks": [
            {"check_name": name, "outcome": "pass", "reason": "实际渲染评测通过。"}
            for name in MATERIAL_REVIEW_CHECK_NAMES
        ],
        "overall_notes": "评测用安全原创视觉。",
    }


@unittest.skipUnless(
    os.environ.get("DEEPTALK_RUN_RENDER_INTEGRATION") == "1",
    "set DEEPTALK_RUN_RENDER_INTEGRATION=1 to run real renderer integration",
)
class RealRendererIntegrationTests(unittest.TestCase):
    def test_same_tiny_plan_previews_and_renders_with_both_engines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            report, script, _ = reviewed_inputs()
            material_profile = load_material_profile()
            production_profile = load_production_profile()
            content = deepcopy(valid_material_content())
            content["cue_sheet"] = [content["cue_sheet"][1]]
            content["materials"] = []
            content["visual_specs"][0]["suggested_duration_seconds"] = 1
            prepared_package = prepare_codex_materials(
                content, script, report, temp / "packages", temp / "material-assets",
                material_profile, {"entries": []}, {"entries": []},
                created_at="2026-08-11T15:00:00+08:00", package_id="MAT-v060-render-eval",
            )
            reviewed = run_codex_material_review(
                review_pass(), prepared_package.package, script, report,
                temp / "packages", material_profile,
                created_at="2026-08-11T15:01:00+08:00", review_id="MRV-v060-render-eval",
            )
            plan = prepare_production_plan(
                reviewed.package, script, report, production_profile,
                temp / "material-assets", created_at="2026-08-11T15:02:00+08:00",
                production_id="PROD-v060-cross-renderer", renderer_mode="remotion",
            )
            configured_root = os.environ.get("DEEPTALK_RENDER_EVAL_ROOT", "").strip()
            root = Path(configured_root).resolve() if configured_root else temp / "outputs"
            results = {}
            for index, renderer_name in enumerate(("remotion", "hyperframes"), 1):
                renderer = get_renderer(renderer_name)
                project = renderer.prepare_project(
                    plan, reviewed.package, production_profile, temp / "material-assets",
                    root / "projects" / renderer_name,
                )
                validation = renderer.validate_project(project)
                preview = renderer.preview(project, port=3240 + index)
                batch = renderer.render(project, plan, root / "assets" / renderer_name)
                manifest = build_motion_asset_manifest(
                    plan, renderer_name, batch,
                    created_at="2026-08-11T15:03:00+08:00",
                    manifest_id=f"MAM-v060-{renderer_name}",
                )
                qa = prepare_production_qa(
                    plan, manifest, created_at="2026-08-11T15:04:00+08:00",
                    qa_id=f"PQA-v060-{renderer_name}",
                    renderer_checks={"project_validation": bool(validation), "preview": preview.exit_code == 0},
                )
                results[renderer_name] = (manifest, qa)

            self.assertEqual(results["remotion"][1]["package_gate_status"], "pass")
            self.assertEqual(results["hyperframes"][1]["package_gate_status"], "pass")
            self.assertEqual(len(results["remotion"][0].manifest["assets"]), 3)
            self.assertEqual(len(results["hyperframes"][0].manifest["assets"]), 3)


if __name__ == "__main__":
    unittest.main()
