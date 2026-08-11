import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import prepare_codex_materials, run_codex_material_review
from deeptalk_studio.production_renderers.base import (
    CommandResult,
    PreparedProject,
    RenderBatch,
    RenderOutput,
    RendererCheckResult,
)
from deeptalk_studio.production_workflow import run_production_workflow
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
            {"check_name": name, "outcome": "pass", "reason": "通过。"}
            for name in MATERIAL_REVIEW_CHECK_NAMES
        ],
        "overall_notes": "通过。",
    }


class FakeRenderer:
    name = "remotion"

    def prepare_project(self, plan, package, profile, material_root, projects_root):
        project = Path(projects_root) / plan["production_id"] / self.name
        project.mkdir(parents=True)
        plan_path = project / "production-plan.json"
        plan_path.write_text("{}", encoding="utf-8")
        return PreparedProject(self.name, project, plan_path, ())

    def validate_project(self, prepared):
        return (RendererCheckResult(
            "remotion_typecheck", "remotion", 0, "pass", "typecheck", "ok",
        ),)

    def preview(self, prepared, *, port=3210):
        return RendererCheckResult(
            "remotion_preview", "remotion", 0, "pass", "preview", "http://localhost",
        )

    def render(self, prepared, plan, output_root):
        outputs = []
        for item in plan["motion_assets"]:
            suffix = "." + item["requested_format"]
            path = Path(output_root) / plan["production_id"] / "assets" / (item["motion_asset_id"] + suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"real-enough-for-fake-probe")
            outputs.append(RenderOutput(
                item["motion_asset_id"], item["scene_id"], item["asset_kind"], path, "fake render"
            ))
        return RenderBatch(tuple(outputs), ())


class ProductionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report, self.script, _ = reviewed_inputs()
        profile = load_material_profile()
        prepared = prepare_codex_materials(
            valid_material_content(), self.script, self.report,
            self.root / "material-packages", self.root / "material-assets", profile,
            inspection_manifest(), rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-workflow",
        )
        reviewed = run_codex_material_review(
            passing_review(), prepared.package, self.script, self.report,
            self.root / "material-packages", profile,
            created_at="2026-08-11T11:00:00+08:00", review_id="MRV-workflow",
        )
        self.package_path = reviewed.paths.json

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def probe(path):
        if Path(path).suffix == ".png":
            return {"width": 1920, "height": 1080, "fps": 0.0, "duration_seconds": 0.0}
        return {"width": 1920, "height": 1080, "fps": 30.0, "duration_seconds": 14.0 if "MAPREVIEW" in str(path) else 6.0 if "MA001" in str(path) else 8.0}

    def test_one_call_creates_plan_project_real_manifest_qa_and_summary(self):
        result = run_production_workflow(
            self.package_path, self.script, self.report,
            material_asset_root=self.root / "material-assets",
            package_root=self.root / "production-packages",
            asset_root=self.root / "production-assets",
            project_root=self.root / "production-projects",
            renderer_mode="remotion", renderer_factory=lambda name: FakeRenderer(),
            created_at="2026-08-11T12:00:00+08:00", production_id="PROD-workflow",
            manifest_id="MAM-workflow", qa_id="PQA-workflow", probe_func=self.probe,
        )
        self.assertEqual(result.qa["package_gate_status"], "pass")
        self.assertEqual(len(result.manifest["assets"]), 4)
        self.assertTrue(result.plan_path.exists())
        self.assertTrue(result.manifest_path.exists())
        self.assertTrue(result.qa_path.exists())
        self.assertTrue(result.project_dir.exists())
        self.assertIn("粗剪视觉预览：已生成", result.summary)
        self.assertEqual(result.plan["selected_renderer"], "remotion")

    def test_normal_run_instantiates_only_the_selected_renderer(self):
        requested = []

        def factory(name):
            requested.append(name)
            return FakeRenderer()

        run_production_workflow(
            self.package_path, self.script, self.report,
            material_asset_root=self.root / "material-assets",
            package_root=self.root / "p2", asset_root=self.root / "a2", project_root=self.root / "j2",
            renderer_mode="auto", renderer_factory=factory,
            created_at="2026-08-11T13:00:00+08:00", production_id="PROD-one-renderer",
            manifest_id="MAM-one-renderer", qa_id="PQA-one-renderer", probe_func=self.probe,
        )
        self.assertEqual(requested, ["remotion"])


if __name__ == "__main__":
    unittest.main()
