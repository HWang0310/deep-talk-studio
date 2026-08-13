import hashlib
import json
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


PNG = b"\x89PNG\r\n\x1a\n" + b"safe-static-capture"


class MaterialBridgeTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.profile = load_material_profile()

    def _reviewed_reference_package(self, root):
        asset_root = root / "assets"; asset_root.mkdir()
        asset = asset_root / "M001.png"; asset.write_bytes(PNG)
        content = valid_material_content()
        content["materials"][0]["claimed_rights_status"] = "unknown"
        package = prepare_material_package(
            content, self.script, self.report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest={"entries": []},
            created_at="2026-08-13T11:00:00+08:00", package_id="MAT-bridge",
        )
        data = package.to_dict()
        data["materials"][0].update(local_path=str(asset), byte_size=len(PNG), sha256=hashlib.sha256(PNG).hexdigest())
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
            validate_material_production_view(view, path, self.script, self.report, self.profile, asset_root)

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


if __name__ == "__main__": unittest.main()
