import copy
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.subtitle_profile import SubtitleProfileError, load_subtitle_profile


class SubtitleProfileTests(unittest.TestCase):
    def test_default_profile_is_one_versioned_1080p_two_line_safe_layout(self):
        profile = load_subtitle_profile()
        self.assertEqual(profile["artifact_version"], "subtitle-profile/1")
        self.assertEqual((profile["canvas_width"], profile["canvas_height"]), (1920, 1080))
        self.assertEqual(profile["max_lines"], 2)
        self.assertLess(profile["content_safe_bottom_px"], profile["subtitle_region_top_px"])

    def test_tampered_profile_fails_digest_validation(self):
        profile = load_subtitle_profile()
        profile["max_lines"] = 3
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(SubtitleProfileError):
                load_subtitle_profile(path)


if __name__ == "__main__":
    unittest.main()
