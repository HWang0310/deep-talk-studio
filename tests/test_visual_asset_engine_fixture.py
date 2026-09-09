import tempfile
import unittest
from pathlib import Path

from evaluations.visual_asset_engine.fixture_episode import run_fixture_episode


class VisualAssetEngineFixtureTests(unittest.TestCase):
    def test_exports_five_qa_ready_assets_and_edit_map(self):
        with tempfile.TemporaryDirectory() as raw:
            result = run_fixture_episode(Path(raw))
            self.assertEqual(result["manifest"]["asset_count"], 5)
            self.assertTrue((Path(raw) / "09_剪辑表" / "剪辑表.md").is_file())
            self.assertTrue(all(item["qa_status"] == "ready" for item in result["manifest"]["assets"]))
            self.assertTrue(result["chinese_stress_path"].is_file())
            self.assertTrue((Path(raw) / "07_MG动画" / "时间线.text-reference.png").is_file())
            visible = "\n".join(result["chinese_stress_evidence"]["visible_text"])
            for text in ("为什么票房还在上涨？", "首周口碑", "社交讨论", "二次传播", "3.2 亿", "+47%", "8 月 24 日", "B站 / AI"):
                self.assertIn(text, visible)
