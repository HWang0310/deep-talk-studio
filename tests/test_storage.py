import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.storage import ReportStorageError, save_report, slugify
from tests.fixtures import valid_report_data


class StorageTests(unittest.TestCase):
    def test_slugify_blocks_path_traversal_and_keeps_readable_topic(self):
        self.assertEqual(slugify("../../AI 热点：真假？"), "ai-热点-真假")

    def test_save_report_writes_revision_safe_markdown_and_json_path(self):
        report = ResearchReport.from_dict(valid_report_data())

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = save_report(report, Path(temp_dir))

            self.assertTrue(paths.markdown.exists())
            self.assertTrue(paths.json.exists())
            self.assertIn("2026/08/10", paths.markdown.as_posix())
            self.assertIn("RPT-20260810-example", paths.markdown.as_posix())
            self.assertEqual(paths.json.name, "research-report-r0001.json")
            saved = json.loads(paths.json.read_text(encoding="utf-8"))
            self.assertEqual(saved["topic"], "示例公共事件")

    def test_existing_revision_is_never_silently_overwritten(self):
        report = ResearchReport.from_dict(valid_report_data())

        with tempfile.TemporaryDirectory() as temp_dir:
            save_report(report, Path(temp_dir))
            with self.assertRaisesRegex(ReportStorageError, "已经存在"):
                save_report(report, Path(temp_dir))

    def test_revision_directory_stays_with_original_created_date(self):
        data = valid_report_data()
        data["generated_at"] = "2026-08-11T00:05:00+08:00"
        report = ResearchReport.from_dict(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = save_report(report, Path(temp_dir))

            self.assertIn("2026/08/10", paths.json.as_posix())


if __name__ == "__main__":
    unittest.main()
