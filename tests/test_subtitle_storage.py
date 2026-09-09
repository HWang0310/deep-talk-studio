import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.subtitle_builder import build_subtitle_artifact
from deeptalk_studio.subtitle_profile import load_subtitle_profile
from deeptalk_studio.subtitle_storage import SubtitleStorageError, load_subtitle_artifact, save_subtitle_artifact
from tests.test_subtitle_builder import media, transcript


class SubtitleStorageTests(unittest.TestCase):
    def test_json_and_srt_are_immutable_and_reload_validates(self):
        artifact = build_subtitle_artifact(transcript(), media(), load_subtitle_profile(), subtitle_id="SUB1", created_at="now")
        with tempfile.TemporaryDirectory() as temp:
            paths = save_subtitle_artifact(artifact, Path(temp))
            self.assertTrue(paths.json.is_file()); self.assertTrue(paths.srt.is_file())
            self.assertIn("00:00:00,500 --> 00:00:01,800", paths.srt.read_text())
            self.assertEqual(load_subtitle_artifact(paths.json, transcript(), media(), load_subtitle_profile()), artifact)
            with self.assertRaises(SubtitleStorageError):
                save_subtitle_artifact(artifact, Path(temp))


if __name__ == "__main__":
    unittest.main()
