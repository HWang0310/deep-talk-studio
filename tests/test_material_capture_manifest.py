import hashlib
import tempfile
import unittest
from pathlib import Path


class MaterialCaptureManifestTests(unittest.TestCase):
    def test_capture_manifest_binds_file_and_reviewed_material_identity(self):
        from deeptalk_studio.material_capture_manifest import (
            MaterialCaptureManifestError,
            build_material_capture_manifest,
            load_material_capture_manifest,
            save_material_capture_manifest,
        )

        package = {
            "package_id": "MAT1", "revision": 2, "package_digest": "p" * 64,
            "materials": [{
                "material_id": "M001", "source_url": "https://example.com/page",
                "page_url": "https://example.com/page", "provenance_status": "inspected",
                "title": "官方页", "cue_ids": ["VC001"],
                "capture": {"page_number": 1, "capture_region": "标题", "source_context": "官方页", "what_it_proves": "证明标题。", "what_it_does_not_prove": "不证明其他内容。"},
            }],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = root / "M001-capture.png"
            capture.write_bytes(b"\x89PNG\r\n\x1a\nreal-capture")
            record = {
                "material_id": "M001", "source_url": "https://example.com/page",
                "source_title": "官方页", "page_number": 1, "capture_region": "标题",
                "local_path": str(capture), "mime_type": "image/png",
                "byte_size": capture.stat().st_size,
                "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
                "cue_ids": ["VC001"], "captured_at": "2026-08-14T09:59:00+08:00",
            }
            manifest = build_material_capture_manifest(package, [record], created_at="2026-08-14T10:00:00+08:00")
            mismatched = dict(record); mismatched["capture_region"] = "错误区域"
            with self.assertRaises(MaterialCaptureManifestError):
                build_material_capture_manifest(package, [mismatched], created_at="2026-08-14T10:00:00+08:00")
            path = save_material_capture_manifest(manifest, root)
            self.assertEqual(load_material_capture_manifest(root, package)["records"][0]["sha256"], record["sha256"])
            capture.write_bytes(b"\x89PNG\r\n\x1a\ntampered")
            with self.assertRaises(MaterialCaptureManifestError):
                load_material_capture_manifest(root, package)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
