import shutil
import tempfile
import unittest
from pathlib import Path

from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture, probe_fixture


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class MediaFixtureFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_factory_builds_decodable_pts_offset_and_vfr_media(self):
        path = build_media_fixture(
            self.root,
            MediaFixtureSpec(
                name="offset",
                video=True,
                audio=True,
                audio_offset="0.375",
                vfr=True,
            ),
        )
        probe = probe_fixture(path)
        self.assertTrue(probe["has_video"] and probe["has_audio"])
        self.assertGreaterEqual(probe["audio_start_time"], 0.35)
        self.assertTrue(probe["decodable"])

    def test_factory_builds_audio_only_no_audio_and_internal_gap_cases(self):
        audio = probe_fixture(
            build_media_fixture(
                self.root,
                MediaFixtureSpec(name="audio", suffix=".wav", video=False, audio=True),
            )
        )
        silent_video = probe_fixture(
            build_media_fixture(
                self.root,
                MediaFixtureSpec(name="no-audio", video=True, audio=False),
            )
        )
        gap = probe_fixture(
            build_media_fixture(
                self.root,
                MediaFixtureSpec(name="gap", video=True, audio=True, internal_gap=True),
            )
        )
        self.assertFalse(audio["has_video"])
        self.assertTrue(audio["has_audio"])
        self.assertTrue(silent_video["has_video"])
        self.assertFalse(silent_video["has_audio"])
        self.assertGreaterEqual(len(gap["audio_gaps"]), 1)

    def test_factory_is_exclusive_and_probe_output_is_repeatable(self):
        spec = MediaFixtureSpec(name="identity", suffix=".mov", video=True, audio=True)
        path = build_media_fixture(self.root, spec)
        first = probe_fixture(path)
        second = probe_fixture(path)
        self.assertEqual(first, second)
        with self.assertRaises(FileExistsError):
            build_media_fixture(self.root, spec)


if __name__ == "__main__":
    unittest.main()
