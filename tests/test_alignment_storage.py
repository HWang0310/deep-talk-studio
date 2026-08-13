import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.alignment_builder import build_script_alignment
from deeptalk_studio.alignment_storage import AlignmentStorageError, load_script_alignment, save_script_alignment
from tests.alignment_fixtures import NOW, cue_fixture, mapping_fixture, profile_fixture, script_fixture, transcript_fixture


class AlignmentStorageTests(unittest.TestCase):
    def setUp(self):
        self.artifact = build_script_alignment(
            script_fixture(), transcript_fixture(), mapping_fixture(), profile_fixture(), cue_fixture(),
            alignment_id="AL001", created_at=NOW,
        )

    def test_json_and_readable_markdown_save_exclusively(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = save_script_alignment(self.artifact, Path(temp))
            self.assertTrue(paths.json_path.is_file())
            self.assertTrue(paths.markdown_path.is_file())
            self.assertEqual(load_script_alignment(paths.json_path), self.artifact)
            self.assertIn("对齐状态", paths.markdown_path.read_text(encoding="utf-8"))
            with self.assertRaises(AlignmentStorageError):
                save_script_alignment(self.artifact, Path(temp))

    def test_path_traversal_and_tamper_fail(self):
        bad = dict(self.artifact)
        bad["alignment_id"] = "../escape"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(AlignmentStorageError):
                save_script_alignment(bad, Path(temp))
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps({"artifact_version": "bad"}), encoding="utf-8")
            with self.assertRaises(AlignmentStorageError):
                load_script_alignment(path)


if __name__ == "__main__":
    unittest.main()
