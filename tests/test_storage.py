import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.storage import save_report, slugify
from tests.fixtures import valid_report_data


class StorageTests(unittest.TestCase):
    def test_slugify_blocks_path_traversal_and_keeps_readable_topic(self):
        self.assertEqual(slugify("../../AI 热点：真假？"), "ai-热点-真假")

    def test_save_report_writes_markdown_and_json_in_date_path(self):
        report = ResearchReport.from_dict(valid_report_data())

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = save_report(report, Path(temp_dir))

            self.assertTrue(paths.markdown.exists())
            self.assertTrue(paths.json.exists())
            self.assertIn("2026/08/10", paths.markdown.as_posix())
            saved = json.loads(paths.json.read_text(encoding="utf-8"))
            self.assertEqual(saved["topic"], "示例公共事件")


if __name__ == "__main__":
    unittest.main()

