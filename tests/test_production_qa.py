import hashlib
import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from deeptalk_studio.production_qa import (
    ManifestResult,
    build_motion_asset_manifest,
    prepare_production_qa,
    validate_motion_manifest,
    validate_production_qa,
)
from deeptalk_studio.production_renderers.base import RenderBatch, RenderOutput
from deeptalk_studio.production_profile import ProductionValidationError
from deeptalk_studio.artifact_runtime import RuntimeArtifactResolver, load_artifact_runtime_config


def tiny_plan():
    return {
        "production_id": "PROD-qa", "plan_digest": "plan-digest",
        "canvas": {"width": 1920, "height": 1080, "fps": 30},
        "scenes": [{
            "scene_id": "S001", "duration_seconds": 2.0,
            "source_material_ids": [], "source_visual_ids": ["V001"],
        }],
        "motion_assets": [
            {"motion_asset_id": "MA001", "scene_id": "S001", "asset_kind": "motion_clip", "requested_format": "mp4"},
            {"motion_asset_id": "MAPREVIEW", "scene_id": "S001", "asset_kind": "rough_preview", "requested_format": "mp4"},
            {"motion_asset_id": "HERO001", "scene_id": "S001", "asset_kind": "hero_still", "requested_format": "png"},
        ],
    }


def renderer_checks(*, environment="pass", validation="pass", preview="pass"):
    return [
        {"check_name": "environment", "renderer": "core",
         "exit_code": 0 if environment == "pass" else 127,
         "outcome": environment, "command_category": "environment", "summary": "环境检查。"},
        {"check_name": "remotion_typecheck", "renderer": "remotion",
         "exit_code": 0 if validation == "pass" else 2, "outcome": validation,
         "command_category": "typecheck", "summary": "类型检查。"},
        {"check_name": "remotion_preview", "renderer": "remotion",
         "exit_code": 0 if preview == "pass" else 3, "outcome": preview,
         "command_category": "preview", "summary": "预览检查。"},
    ]


class ProductionQATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.clip = self.root / "MA001.mp4"
        self.clip.write_bytes(b"fictional video bytes")

    def tearDown(self):
        self.temp.cleanup()

    def probe(self, path):
        if Path(path).suffix == ".png":
            return {"width": 1920, "height": 1080, "fps": 0.0, "duration_seconds": 0.0}
        return {"width": 1920, "height": 1080, "fps": 30.0, "duration_seconds": 2.0}

    def test_manifest_records_real_file_metadata_hash_binding_and_command(self):
        batch = RenderBatch((RenderOutput(
            "MA001", "S001", "motion_clip", self.clip, "renderer command",
        ),), ())
        result = build_motion_asset_manifest(
            tiny_plan(), "remotion", batch, created_at="2026-08-11T13:00:00+08:00",
            manifest_id="MAM-test", probe_func=self.probe,
        )
        asset = result.manifest["assets"][0]
        self.assertEqual(asset["byte_size"], self.clip.stat().st_size)
        self.assertEqual(asset["sha256"], hashlib.sha256(self.clip.read_bytes()).hexdigest())
        self.assertEqual(asset["source_visual_ids"], ["V001"])
        self.assertEqual(asset["production_plan_digest"], "plan-digest")
        validate_motion_manifest(result.manifest, tiny_plan())

    def test_relocated_manifest_validates_runtime_file_without_rewriting_history(self):
        base = self.root
        historical_root = base / "historical-repository"
        canonical_root = base / "canonical-repository"
        historical_root.mkdir()
        canonical_root.mkdir()
        old_clip = historical_root / "production_assets/PROD-qa/assets/MA001.mp4"
        old_clip.parent.mkdir(parents=True)
        old_clip.write_bytes(b"sanitized relocated motion")
        result = build_motion_asset_manifest(
            tiny_plan(), "remotion",
            RenderBatch((RenderOutput("MA001", "S001", "motion_clip", old_clip, "ok"),), ()),
            created_at="2026-08-11T13:00:00+08:00", manifest_id="MAM-relocated",
            probe_func=self.probe,
        )
        original = json.dumps(result.manifest, ensure_ascii=False, sort_keys=True)
        target = canonical_root / "production_assets/PROD-qa/assets/MA001.mp4"
        target.parent.mkdir(parents=True)
        shutil.copy2(old_clip, target)
        shutil.rmtree(historical_root)
        config_path = base / "artifact-runtime.json"
        config_path.write_text(json.dumps({
            "config_version": "artifact-runtime/1",
            "canonical_repository_root": str(canonical_root),
            "trusted_historical_repository_roots": [str(historical_root.resolve())],
            "current_production_id": "PROD-qa",
        }), encoding="utf-8")
        resolver = RuntimeArtifactResolver(
            load_artifact_runtime_config(canonical_root, config_path)
        )

        observations = validate_motion_manifest(
            result.manifest, tiny_plan(), artifact_resolver=resolver
        )

        self.assertEqual(observations["MA001"].resolved_path, target.resolve())
        self.assertEqual(
            json.dumps(result.manifest, ensure_ascii=False, sort_keys=True), original
        )
        tampered = deepcopy(result.manifest)
        tampered["assets"][0]["output_path"] = str(
            historical_root.resolve() / "production_assets/PROD-qa/assets/MA999.mp4"
        )
        from deeptalk_studio.production_qa import _digest
        tampered["manifest_digest"] = _digest(tampered, "manifest_digest")
        with self.assertRaisesRegex(ProductionValidationError, "identity"):
            validate_motion_manifest(
                tampered, tiny_plan(), artifact_resolver=resolver
            )

    def test_zero_byte_wrong_dimensions_and_missing_output_become_clip_failures(self):
        zero = self.root / "zero.mp4"
        zero.write_bytes(b"")
        wrong = lambda path: {"width": 1280, "height": 720, "fps": 24.0, "duration_seconds": 9.0}
        batch = RenderBatch((
            RenderOutput("MA001", "S001", "motion_clip", zero, "zero"),
        ), ({"motion_asset_id": "MAPREVIEW", "issue_type": "render_failed", "details": "renderer failed"},))
        result = build_motion_asset_manifest(
            tiny_plan(), "remotion", batch, created_at="2026-08-11T13:00:00+08:00",
            manifest_id="MAM-fail", probe_func=wrong,
        )
        types = {failure["issue_type"] for failure in result.failures}
        self.assertIn("blank_render", types)
        self.assertIn("render_failed", types)
        self.assertIn("missing_render_output", types)

        self.clip.write_bytes(b"non-empty")
        result = build_motion_asset_manifest(
            tiny_plan(), "remotion",
            RenderBatch((RenderOutput("MA001", "S001", "motion_clip", self.clip, "wrong"),), ()),
            created_at="2026-08-11T13:00:00+08:00", manifest_id="MAM-wrong",
            probe_func=wrong,
        )
        types = {failure["issue_type"] for failure in result.failures}
        self.assertIn("wrong_dimensions", types)
        self.assertIn("invalid_duration", types)

    def test_one_failed_clip_keeps_safe_clip_ready_but_package_blocker_stops_all(self):
        batch = RenderBatch((RenderOutput(
            "MA001", "S001", "motion_clip", self.clip, "ok",
        ),), ({"motion_asset_id": "MAPREVIEW", "issue_type": "render_failed", "details": "failed"},))
        manifest = build_motion_asset_manifest(
            tiny_plan(), "remotion", batch, created_at="2026-08-11T13:00:00+08:00",
            manifest_id="MAM-partial", probe_func=self.probe,
        )
        qa = prepare_production_qa(
            tiny_plan(), manifest, created_at="2026-08-11T13:01:00+08:00",
            qa_id="PQA-partial", renderer_checks=renderer_checks(),
        )
        self.assertEqual(qa["package_gate_status"], "warnings")
        self.assertEqual(qa["clip_results"][0], {"motion_asset_id": "MA001", "status": "ready"})

        blocked = prepare_production_qa(
            tiny_plan(), manifest, created_at="2026-08-11T13:01:00+08:00",
            qa_id="PQA-blocked", renderer_checks=renderer_checks(validation="fail"),
        )
        self.assertEqual(blocked["package_gate_status"], "fail")
        self.assertIn("renderer_validation_failed", {issue["issue_type"] for issue in blocked["issues"]})

    def test_model_cannot_self_declare_manifest_or_qa_pass(self):
        result = build_motion_asset_manifest(
            tiny_plan(), "remotion",
            RenderBatch((RenderOutput("MA001", "S001", "motion_clip", self.clip, "ok"),), ()),
            created_at="2026-08-11T13:00:00+08:00", manifest_id="MAM-tamper",
            probe_func=self.probe,
        )
        manifest = deepcopy(result.manifest)
        manifest["assets"][0]["width"] = 999
        with self.assertRaises(ProductionValidationError):
            validate_motion_manifest(manifest, tiny_plan())
        qa = prepare_production_qa(
            tiny_plan(), result, created_at="2026-08-11T13:01:00+08:00",
            qa_id="PQA-tamper", renderer_checks=renderer_checks(),
        )
        qa["package_gate_status"] = "pass" if qa["package_gate_status"] != "pass" else "fail"
        with self.assertRaises(ProductionValidationError):
            validate_production_qa(qa, tiny_plan(), result.manifest)

    def test_failed_check_cannot_coexist_with_a_passing_gate_even_when_files_exist(self):
        result = build_motion_asset_manifest(
            tiny_plan(), "remotion",
            RenderBatch((RenderOutput("MA001", "S001", "motion_clip", self.clip, "ok"),), ()),
            created_at="2026-08-11T13:00:00+08:00", manifest_id="MAM-check-fail",
            probe_func=self.probe,
        )
        qa = prepare_production_qa(
            tiny_plan(), result, created_at="2026-08-11T13:01:00+08:00",
            qa_id="PQA-check-fail", renderer_checks=renderer_checks(preview="fail"),
        )
        self.assertEqual(qa["package_gate_status"], "fail")
        self.assertIn("renderer_preview_failed", {issue["issue_type"] for issue in qa["issues"]})
        environment_qa = prepare_production_qa(
            tiny_plan(), result, created_at="2026-08-11T13:01:00+08:00",
            qa_id="PQA-environment-fail", renderer_checks=renderer_checks(environment="fail"),
        )
        self.assertEqual(environment_qa["package_gate_status"], "fail")
        self.assertIn(
            "production_environment_unavailable",
            {issue["issue_type"] for issue in environment_qa["issues"]},
        )
        tampered = deepcopy(qa)
        tampered["issues"] = [issue for issue in tampered["issues"] if issue["issue_type"] != "renderer_preview_failed"]
        for index, issue in enumerate(tampered["issues"], 1):
            issue["issue_id"] = f"PQI{index:03d}"
        tampered["package_gate_status"] = "warnings"
        from deeptalk_studio.production_qa import _digest
        tampered["qa_digest"] = _digest(tampered, "qa_digest")
        with self.assertRaisesRegex(ProductionValidationError, "fail check"):
            validate_production_qa(tampered, tiny_plan(), result.manifest)


if __name__ == "__main__":
    unittest.main()
