import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_storage import (
    MaterialStorageError,
    load_material_package,
    save_material_package,
    save_material_review_artifact,
)
from deeptalk_studio.material_validation import prepare_material_package
from deeptalk_studio.material_validation import material_package_digest
from deeptalk_studio.material_workflow import (
    prepare_codex_materials,
    run_codex_material_review,
)
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


def review_content():
    return {
        "issues": [],
        "checks": [{"check_name": name, "outcome": "pass", "reason": "正式检查通过。"}
                   for name in MATERIAL_REVIEW_CHECK_NAMES],
        "overall_notes": "通过。",
    }


class MaterialStorageWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.profile = load_material_profile()

    def test_workflow_renders_svg_and_saves_json_and_simple_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = prepare_codex_materials(
                valid_material_content(), self.script, self.report, root / "packages",
                root / "assets", self.profile, inspection_manifest(), rights_manifest(),
                created_at="2026-08-11T10:00:00+08:00", package_id="MAT-flow",
            )
            data = json.loads(result.paths.json.read_text(encoding="utf-8"))
            markdown = result.paths.markdown.read_text(encoding="utf-8")
            self.assertEqual(data["generated_visuals"][0]["render_status"], "rendered")
            self.assertTrue(Path(data["generated_visuals"][0]["local_path"]).exists())
            self.assertIn("画面提示", markdown)
            self.assertIn("可直接使用", markdown)
            self.assertNotIn("VC001", markdown)
            self.assertNotIn("M001", markdown)

    def test_storage_is_immutable_and_duplicate_safe(self):
        package = prepare_material_package(
            valid_material_content(), self.script, self.report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest=rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-store",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save_material_package(package, root)
            with self.assertRaisesRegex(MaterialStorageError, "覆盖"):
                save_material_package(package, root)

    def test_reviewed_load_requires_matching_material_review_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared = prepare_codex_materials(
                valid_material_content(), self.script, self.report, root / "packages",
                root / "assets", self.profile, inspection_manifest(), rights_manifest(),
                created_at="2026-08-11T10:00:00+08:00", package_id="MAT-load",
            )
            reviewed = run_codex_material_review(
                review_content(), prepared.package, self.script, self.report,
                root / "packages", self.profile,
                created_at="2026-08-11T11:00:00+08:00", review_id="MRV-load",
            )
            loaded = load_material_package(
                reviewed.paths.json, self.script, self.report, self.profile
            )
            self.assertEqual(loaded.status, "reviewed")
            reviewed.review_artifact.unlink()
            with self.assertRaisesRegex(MaterialStorageError, "Review Artifact"):
                load_material_package(reviewed.paths.json, self.script, self.report, self.profile)

    def test_reviewed_loader_rederives_r1_review_r2_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared = prepare_codex_materials(
                valid_material_content(), self.script, self.report, root / "packages",
                root / "assets", self.profile, inspection_manifest(), rights_manifest(),
                created_at="2026-08-11T10:00:00+08:00", package_id="MAT-canonical",
            )
            reviewed = run_codex_material_review(
                review_content(), prepared.package, self.script, self.report,
                root / "packages", self.profile,
                created_at="2026-08-11T11:00:00+08:00", review_id="MRV-canonical",
            )
            for path, mutate in (
                (reviewed.paths.json, lambda data: data["materials"][0].update(eligibility_status="reference_only")),
                (reviewed.paths.json, lambda data: data["materials"][0].update(rights_status="unknown")),
                (reviewed.paths.json, lambda data: data["materials"][0].update(provenance_status="unmatched")),
                (reviewed.paths.json, lambda data: data["materials"][0].update(ranking_score=99)),
                (reviewed.paths.json, lambda data: data.update(status="reviewed_with_warnings")),
            ):
                original = json.loads(path.read_text(encoding="utf-8"))
                data = json.loads(path.read_text(encoding="utf-8"))
                mutate(data)
                data["package_digest"] = material_package_digest(data)
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(MaterialStorageError, "canonical|provenance|Review"):
                    load_material_package(path, self.script, self.report, self.profile)
                path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
            review_artifact = reviewed.review_artifact
            original_review = json.loads(review_artifact.read_text(encoding="utf-8"))
            wrong_review = dict(original_review, package_revision=999)
            review_artifact.write_text(json.dumps(wrong_review, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(MaterialStorageError, "Review Artifact"):
                load_material_package(reviewed.paths.json, self.script, self.report, self.profile)
            review_artifact.write_text(json.dumps(original_review, ensure_ascii=False), encoding="utf-8")
            inspection_artifact = reviewed.paths.json.parent / "material-inspection-for-r0001.json"
            inspection_artifact.unlink()
            with self.assertRaisesRegex(MaterialStorageError, "provenance"):
                load_material_package(reviewed.paths.json, self.script, self.report, self.profile)

    def test_canonical_loader_rejects_reference_or_rejected_item_promoted_to_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = valid_material_content()
            content["materials"][0]["claimed_rights_status"] = "unknown"
            prepared = prepare_codex_materials(
                content, self.script, self.report, root / "packages", root / "assets", self.profile,
                inspection_manifest(), {"entries": []},
                created_at="2026-08-11T10:00:00+08:00", package_id="MAT-promote",
            )
            reviewed = run_codex_material_review(
                review_content(), prepared.package, self.script, self.report, root / "packages", self.profile,
                created_at="2026-08-11T11:00:00+08:00", review_id="MRV-promote",
            )
            data = json.loads(reviewed.paths.json.read_text(encoding="utf-8"))
            self.assertEqual(data["materials"][0]["eligibility_status"], "reference_only")
            data["materials"][0]["eligibility_status"] = "ready_to_use"
            data["package_digest"] = material_package_digest(data)
            reviewed.paths.json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(MaterialStorageError, "canonical"):
                load_material_package(reviewed.paths.json, self.script, self.report, self.profile)

            blocked = review_content()
            blocked["issues"] = [{
                "issue_type": "rights_misrepresented", "material_ids": ["M001"], "visual_ids": [],
                "cue_ids": ["VC001"], "explanation": "权利依据不成立。", "suggested_fix": "不要使用。",
            }]
            for check in blocked["checks"]:
                if check["check_name"] == "rights_reuse":
                    check["outcome"] = "fail"
            prepared = prepare_codex_materials(
                valid_material_content(), self.script, self.report, root / "packages-2", root / "assets-2", self.profile,
                inspection_manifest(), rights_manifest(),
                created_at="2026-08-11T10:00:00+08:00", package_id="MAT-rejected",
            )
            rejected = run_codex_material_review(
                blocked, prepared.package, self.script, self.report, root / "packages-2", self.profile,
                created_at="2026-08-11T11:00:00+08:00", review_id="MRV-rejected",
            )
            data = json.loads(rejected.paths.json.read_text(encoding="utf-8"))
            self.assertEqual(data["materials"][0]["eligibility_status"], "rejected")
            data["materials"][0]["eligibility_status"] = "ready_to_use"
            data["package_digest"] = material_package_digest(data)
            rejected.paths.json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(MaterialStorageError, "canonical"):
                load_material_package(rejected.paths.json, self.script, self.report, self.profile)


if __name__ == "__main__":
    unittest.main()
