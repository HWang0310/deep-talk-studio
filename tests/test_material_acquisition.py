import hashlib
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_acquisition import (
    AcquisitionError,
    FetchResponse,
    register_local_capture,
    safe_download_material,
)
from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_validation import prepare_material_package
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


class MaterialAcquisitionTests(unittest.TestCase):
    def setUp(self):
        report, script, _ = reviewed_inputs()
        self.profile = load_material_profile()
        self.package = prepare_material_package(
            valid_material_content(), script, report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest=rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-acquire",
        )
        self.item = self.package.materials[0]

    def test_safe_download_records_path_size_and_sha(self):
        content = b"%PDF-1.7\nfictional safe fixture\n"
        fetcher = lambda url, max_bytes: FetchResponse(200, url, "application/pdf", content)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = safe_download_material(
                self.item, Path(temp_dir), self.profile, fetcher=fetcher
            )
            path = Path(result["local_path"])
            self.assertTrue(path.exists())
            self.assertEqual(result["byte_size"], len(content))
            self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())

    def test_unknown_rights_item_cannot_be_downloaded(self):
        item = dict(self.item, eligibility_status="reference_only")
        with self.assertRaisesRegex(AcquisitionError, "ready_to_use"):
            safe_download_material(item, Path("material_assets"), self.profile)

    def test_private_or_local_url_is_rejected(self):
        item = dict(self.item, source_url="http://127.0.0.1/secret.pdf")
        with self.assertRaisesRegex(AcquisitionError, "公开"):
            safe_download_material(item, Path("material_assets"), self.profile)

    def test_dangerous_mime_and_oversize_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fetcher = lambda url, max_bytes: FetchResponse(200, url, "text/javascript", b"alert(1)")
            with self.assertRaisesRegex(AcquisitionError, "MIME"):
                safe_download_material(self.item, Path(temp_dir), self.profile, fetcher=fetcher)
            huge = b"x" * (self.profile["max_download_bytes"] + 1)
            fetcher = lambda url, max_bytes: FetchResponse(200, url, "application/pdf", huge)
            with self.assertRaisesRegex(AcquisitionError, "大小"):
                safe_download_material(self.item, Path(temp_dir), self.profile, fetcher=fetcher)

    def test_existing_target_is_never_overwritten(self):
        content = b"%PDF-1.7\nfixture\n"
        fetcher = lambda url, max_bytes: FetchResponse(200, url, "application/pdf", content)
        with tempfile.TemporaryDirectory() as temp_dir:
            safe_download_material(self.item, Path(temp_dir), self.profile, fetcher=fetcher)
            with self.assertRaisesRegex(AcquisitionError, "覆盖"):
                safe_download_material(self.item, Path(temp_dir), self.profile, fetcher=fetcher)

    def test_capture_registration_preserves_proof_and_limit_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "capture.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\nfictional")
            target_root = root / "assets"
            result = register_local_capture(self.item, source, target_root)
            self.assertEqual(result["capture"]["page_number"], 1)
            self.assertIn("日期", result["capture"]["what_it_proves"])
            self.assertIn("不证明", result["capture"]["what_it_does_not_prove"])
            self.assertTrue(Path(result["local_path"]).exists())


if __name__ == "__main__":
    unittest.main()

