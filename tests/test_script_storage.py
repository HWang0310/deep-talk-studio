import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_renderer import render_editor_markdown, render_teleprompter_markdown
from deeptalk_studio.script_storage import ScriptStorageError, load_script, save_script
from deeptalk_studio.script_validation import prepare_script_draft
from tests.fixtures import approved_report_data, valid_script_content


class ScriptStorageTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile()
        self.script = prepare_script_draft(
            valid_script_content(),
            self.report,
            self.profile,
            created_at="2026-08-10T13:00:00+08:00",
            script_id="SCR-storage",
        )

    def test_editor_exposes_grounding_while_teleprompter_is_only_spoken_copy(self):
        editor = render_editor_markdown(self.script, self.report, self.profile)
        teleprompter = render_teleprompter_markdown(self.script)

        self.assertIn("预计口播", editor)
        self.assertIn("B001", editor)
        self.assertIn("事实", editor)
        self.assertIn("C1", editor)
        self.assertIn("风险", editor)
        self.assertNotIn("B001", teleprompter)
        self.assertNotIn("C1", teleprompter)
        self.assertNotIn("http", teleprompter)
        self.assertNotIn("character_count", teleprompter)
        self.assertIn(self.script.beats[0]["narration"], teleprompter)
        self.assertIn(self.script.closing, teleprompter)

    def test_save_writes_three_immutable_files_and_latest_can_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = save_script(self.script, self.report, self.profile, root)
            loaded = load_script(paths.json, self.report, self.profile)
            latest = json.loads((root / "latest.json").read_text(encoding="utf-8"))

            self.assertTrue(paths.json.exists())
            self.assertTrue(paths.editor.exists())
            self.assertTrue(paths.teleprompter.exists())
            self.assertIn("2026/08/10", paths.json.as_posix())
            self.assertEqual(loaded.script_id, "SCR-storage")
            self.assertEqual(latest["script_id"], "SCR-storage")
            with self.assertRaisesRegex(ScriptStorageError, "不能静默覆盖"):
                save_script(self.script, self.report, self.profile, root)


if __name__ == "__main__":
    unittest.main()
