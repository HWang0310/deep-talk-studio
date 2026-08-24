import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.edit_map import build_edit_map
from deeptalk_studio.visual_asset_pack import build_manifest, write_asset_pack


class VisualAssetPackTests(unittest.TestCase):
    def test_exports_only_ready_assets_without_machine_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); clip = root / "clip.mp4"; clip.write_bytes(b"fixture")
            manifest = build_manifest([
                {"filename": "可用素材.mp4", "local_path": str(clip), "qa_status": "ready", "sha256": "a" * 64, "duration_seconds": "8", "time_range": {"start_seconds": "12", "end_seconds": "20"}, "purpose": "解释", "why": "清楚", "fallback": "保留真人"},
                {"filename": "失败素材.mp4", "local_path": str(clip), "qa_status": "failed", "sha256": "b" * 64, "duration_seconds": "8", "time_range": {"start_seconds": "20", "end_seconds": "28"}, "purpose": "x", "why": "x", "fallback": "保留真人"},
            ])
            result = write_asset_pack(root / "episode", manifest)
            view = build_edit_map(manifest, result["edit_dir"])
            self.assertIn("可用素材.mp4", view["markdown"])
            self.assertNotIn("失败素材.mp4", view["markdown"])
            self.assertNotIn("sha256", view["markdown"].lower())
