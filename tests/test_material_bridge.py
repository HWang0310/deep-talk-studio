import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_bridge import MaterialBridgeError, build_material_production_view, validate_material_production_view
from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES, prepare_material_review
from deeptalk_studio.material_storage import save_material_package, save_material_review_artifact
from deeptalk_studio.material_validation import material_package_digest, prepare_material_package
from deeptalk_studio.models import MaterialPackage
from tests.material_fixtures import inspection_manifest, reviewed_inputs, valid_material_content
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture


PNG = b"\x89PNG\r\n\x1a\n" + b"safe-static-capture"


class MaterialBridgeTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.profile = load_material_profile()

    def _reviewed_reference_package(self, root, *, asset_type="official_document", video_reference=None, attach_package_file=True):
        asset_root = root / "assets"; asset_root.mkdir()
        if asset_type == "video_clip_reference":
            asset = build_media_fixture(asset_root, MediaFixtureSpec(name="M001", duration="2"))
            asset_bytes = asset.read_bytes()
        else:
            asset = asset_root / "M001.png"; asset.write_bytes(PNG); asset_bytes = PNG
        content = valid_material_content()
        content["materials"][0]["claimed_rights_status"] = "unknown"
        content["materials"][0]["asset_type"] = asset_type
        if video_reference is not None:
            content["materials"][0]["video_reference"] = video_reference
        package = prepare_material_package(
            content, self.script, self.report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest={"entries": []},
            created_at="2026-08-13T11:00:00+08:00", package_id="MAT-bridge",
        )
        if attach_package_file:
            data = package.to_dict()
            data["materials"][0].update(local_path=str(asset), byte_size=len(asset_bytes), sha256=hashlib.sha256(asset_bytes).hexdigest())
            data["package_digest"] = material_package_digest(data)
            package = MaterialPackage(data)
        r1_paths = save_material_package(package, root / "packages")
        review = prepare_material_review({
            "issues": [{
                "issue_type": "permission_needed", "material_ids": ["M001"], "visual_ids": [],
                "cue_ids": ["VC001"], "explanation": "未记录复用授权。", "suggested_fix": "仅保留提示。",
            }],
            "checks": [{"check_name": name, "outcome": "fail" if name == "rights_reuse" else "pass", "reason": "独立检查完成。"} for name in MATERIAL_REVIEW_CHECK_NAMES],
            "overall_notes": "只存在权利复用提示。",
        }, package, self.script, self.report, self.profile, created_at="2026-08-13T11:10:00+08:00", review_id="MRV-bridge")
        save_material_review_artifact(review.artifact, package, root / "packages")
        r2_paths = save_material_package(review.package, root / "packages")
        return r2_paths.json, asset_root, review.package

    def test_rights_only_reference_item_can_be_production_eligible_without_rewriting_history(self):
        with tempfile.TemporaryDirectory() as temp:
            path, asset_root, original = self._reviewed_reference_package(Path(temp))
            view = build_material_production_view(path, self.script, self.report, self.profile, asset_root)
            self.assertEqual(original.materials[0]["eligibility_status"], "reference_only")
            self.assertEqual(view["items"][0]["production_status"], "ready")
            self.assertEqual(view["items"][0]["rights_status"], "unknown")
            self.assertEqual(view["items"][0]["asset_type"], "official_document")
            self.assertEqual(view["items"][0]["capture"]["page_number"], 1)
            validate_material_production_view(view, path, self.script, self.report, self.profile, asset_root)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
    def test_reviewed_video_projection_preserves_range_for_real_placement(self):
        from deeptalk_studio.edit_bridge_planner import build_visual_placements
        from tests.edit_bridge_fixtures import alignment, media
        with tempfile.TemporaryDirectory() as temp:
            ref={"title":"公开片段","start_seconds":0.25,"end_seconds":1.25,"usage_reason":"展示现场机制"}
            path,asset_root,_=self._reviewed_reference_package(Path(temp),asset_type="video_clip_reference",video_reference=ref)
            view=build_material_production_view(path,self.script,self.report,self.profile,asset_root)
            self.assertEqual(view["items"][0]["video_reference"],ref)
            placement=build_visual_placements(alignment(),view,{}, {},media(),[asset_root])[0]
            self.assertEqual((placement["source_kind"],placement["placement_status"]),("real_video","ready"))
            self.assertEqual((placement["source_clip_in_seconds"],placement["source_clip_out_seconds"]),("0.25","1.25"))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
    def test_reviewed_video_without_range_requires_clip_selection(self):
        from deeptalk_studio.edit_bridge_planner import build_visual_placements
        from tests.edit_bridge_fixtures import alignment, media
        with tempfile.TemporaryDirectory() as temp:
            ref={"title":"公开片段","start_seconds":0,"end_seconds":0,"usage_reason":"尚未选取具体片段"}
            path,asset_root,_=self._reviewed_reference_package(Path(temp),asset_type="video_clip_reference",video_reference=ref)
            view=build_material_production_view(path,self.script,self.report,self.profile,asset_root)
            placement=build_visual_placements(alignment(),view,{}, {},media(),[asset_root])[0]
            self.assertEqual(placement["source_kind"],"real_video")
            self.assertEqual(placement["placement_status"],"clip_selection_needed")

    def test_missing_tampered_or_outside_asset_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            path, asset_root, _ = self._reviewed_reference_package(Path(temp))
            view = build_material_production_view(path, self.script, self.report, self.profile, asset_root)
            Path(view["items"][0]["local_path"]).write_bytes(PNG + b"tamper")
            with self.assertRaises(MaterialBridgeError):
                validate_material_production_view(view, path, self.script, self.report, self.profile, asset_root)

    def test_url_only_stays_missing_and_projection_digest_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            path, asset_root, _ = self._reviewed_reference_package(Path(temp))
            data = json.loads(path.read_text())
            data["materials"][0].update(local_path="", byte_size=0, sha256="")
            data["package_digest"] = material_package_digest(data)
            path.write_text(json.dumps(data, ensure_ascii=False))
            # Canonical replay rejects modified r2 before projection.
            with self.assertRaises(Exception):
                build_material_production_view(path, self.script, self.report, self.profile, asset_root)

    def test_reviewed_reference_capture_manifest_projects_real_image_without_rewriting_history(self):
        from deeptalk_studio.material_capture_manifest import build_material_capture_manifest, save_material_capture_manifest
        with tempfile.TemporaryDirectory() as temp:
            package_path, asset_root, original = self._reviewed_reference_package(Path(temp), attach_package_file=False)
            capture_root = asset_root / "captures"; capture_root.mkdir(parents=True)
            capture = capture_root / "M001-capture.png"; capture.write_bytes(PNG)
            item = original.materials[0]
            record = {
                "material_id": "M001", "source_url": item["source_url"], "source_title": item["title"],
                "page_number": item["capture"]["page_number"], "capture_region": item["capture"]["capture_region"],
                "local_path": str(capture), "mime_type": "image/png", "byte_size": capture.stat().st_size,
                "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(), "cue_ids": item["cue_ids"],
                "captured_at": "2026-08-14T10:00:00+08:00",
            }
            save_material_capture_manifest(build_material_capture_manifest(original.to_dict(), [record], created_at="2026-08-14T10:00:00+08:00"), asset_root)
            view = build_material_production_view(package_path, self.script, self.report, self.profile, asset_root)
            self.assertEqual(view["items"][0]["production_status"], "ready")
            self.assertEqual(view["items"][0]["local_path"], str(capture.resolve()))

    def test_relocated_capture_resolves_from_immutable_manifest_and_package(self):
        from deeptalk_studio.artifact_runtime import RuntimeArtifactResolver, load_artifact_runtime_config
        from deeptalk_studio.material_capture_manifest import build_material_capture_manifest, save_material_capture_manifest
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / "package-history").mkdir()
            package_path, _, original = self._reviewed_reference_package(
                base / "package-history", attach_package_file=False
            )
            old_repo = base / "old" / "deep-talk-studio"
            new_repo = base / "new" / "deep-talk-studio"
            old_asset_root = old_repo / "material_assets" / original.package_id
            capture = old_asset_root / "captures/registered/M001-capture.png"
            capture.parent.mkdir(parents=True)
            capture.write_bytes(PNG)
            item = original.materials[0]
            record = {
                "material_id": "M001", "source_url": item["source_url"], "source_title": item["title"],
                "page_number": item["capture"]["page_number"], "capture_region": item["capture"]["capture_region"],
                "local_path": str(capture.resolve()), "mime_type": "image/png", "byte_size": capture.stat().st_size,
                "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(), "cue_ids": item["cue_ids"],
                "captured_at": "2026-08-14T10:00:00+08:00",
            }
            capture_manifest_path = save_material_capture_manifest(
                build_material_capture_manifest(
                    original.to_dict(), [record], created_at="2026-08-14T10:00:00+08:00"
                ), old_asset_root,
            )
            package_bytes = package_path.read_bytes()
            manifest_bytes = capture_manifest_path.read_bytes()
            new_repo.mkdir(parents=True)
            shutil.copytree(old_repo / "material_assets", new_repo / "material_assets")
            shutil.rmtree(old_repo)
            config_path = base / "artifact-runtime.json"
            config_path.write_text(json.dumps({
                "config_version": "artifact-runtime/1",
                "canonical_repository_root": str(new_repo.resolve()),
                "trusted_historical_repository_roots": [str(old_repo.resolve())],
                "current_production_id": "",
            }), encoding="utf-8")
            resolver = RuntimeArtifactResolver(load_artifact_runtime_config(new_repo, config_path))
            new_asset_root = new_repo / "material_assets" / original.package_id

            view = build_material_production_view(
                package_path, self.script, self.report, self.profile, new_asset_root,
                artifact_resolver=resolver,
            )

            projected = view["items"][0]
            self.assertEqual(projected["production_status"], "ready")
            self.assertEqual(projected["recorded_local_path"], record["local_path"])
            self.assertEqual(projected["local_path"], str(
                (new_asset_root / "captures/registered/M001-capture.png").resolve()
            ))
            self.assertEqual(package_path.read_bytes(), package_bytes)
            self.assertEqual(
                (new_asset_root / "captures/material-capture-manifest-r0001.json").read_bytes(),
                manifest_bytes,
            )


if __name__ == "__main__": unittest.main()
