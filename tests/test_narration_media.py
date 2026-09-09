import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.narration_media import (
    NarrationMediaError,
    import_narration_media,
    probe_narration_media,
)
from deeptalk_studio.validation import validate_json_schema
from deeptalk_studio.narration_schema import NARRATION_MEDIA_SCHEMA
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture


NOW = "2026-08-13T12:00:00+08:00"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class NarrationMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input_root = self.root / "input"
        self.media_root = self.root / "media"

    def tearDown(self):
        self.temp.cleanup()

    def test_import_copies_media_immutably_and_derives_identity(self):
        source = build_media_fixture(
            self.input_root,
            MediaFixtureSpec(name="真人 口播", video=True, audio=True),
        )
        result = import_narration_media(
            source,
            self.media_root,
            imported_at=NOW,
            id_factory=lambda _: "MEDIA001",
        )
        self.assertEqual(result.artifact["sha256"], sha256_file(result.immutable_path))
        self.assertNotEqual(result.immutable_path, source)
        self.assertTrue(result.artifact["presentation_evidence"]["evidence_digest"])
        self.assertEqual(result.artifact["media_kind"], "video")
        validate_json_schema(result.artifact, NARRATION_MEDIA_SCHEMA, "media")

    def test_probe_preserves_positive_audio_offset_and_vfr_evidence(self):
        source = build_media_fixture(
            self.input_root,
            MediaFixtureSpec(
                name="offset-vfr", video=True, audio=True, audio_offset="0.375", vfr=True
            ),
        )
        evidence = probe_narration_media(source)
        self.assertGreaterEqual(evidence.audio_presentation_start_seconds, 0.35)
        self.assertTrue(evidence.video_stream["is_vfr"])
        self.assertEqual(evidence.presentation_origin_seconds, 0.0)

    def test_audio_only_is_recorded_and_no_audio_video_remains_auditable(self):
        audio = build_media_fixture(
            self.input_root,
            MediaFixtureSpec(name="audio", suffix=".wav", video=False, audio=True),
        )
        silent_video = build_media_fixture(
            self.input_root,
            MediaFixtureSpec(name="silent", video=True, audio=False),
        )
        audio_result = import_narration_media(
            audio, self.media_root, imported_at=NOW, id_factory=lambda _: "MEDIA-AUDIO"
        )
        silent_result = import_narration_media(
            silent_video,
            self.media_root,
            imported_at=NOW,
            id_factory=lambda _: "MEDIA-SILENT",
        )
        self.assertEqual(audio_result.artifact["media_kind"], "audio")
        self.assertFalse(audio_result.artifact["video_stream"]["present"])
        self.assertFalse(silent_result.artifact["audio_stream"]["present"])

    def test_rejects_unsupported_symlink_empty_and_duplicate_target(self):
        unsupported = self.input_root / "bad.txt"
        unsupported.parent.mkdir(parents=True, exist_ok=True)
        unsupported.write_text("bad", encoding="utf-8")
        with self.assertRaises(NarrationMediaError):
            import_narration_media(
                unsupported, self.media_root, imported_at=NOW, id_factory=lambda _: "BAD"
            )
        empty = self.input_root / "empty.mp4"
        empty.touch()
        with self.assertRaises(NarrationMediaError):
            import_narration_media(
                empty, self.media_root, imported_at=NOW, id_factory=lambda _: "EMPTY"
            )
        source = build_media_fixture(
            self.input_root,
            MediaFixtureSpec(name="valid", video=True, audio=True),
        )
        link = self.input_root / "link.mp4"
        link.symlink_to(source)
        with self.assertRaises(NarrationMediaError):
            import_narration_media(
                link, self.media_root, imported_at=NOW, id_factory=lambda _: "LINK"
            )
        import_narration_media(
            source, self.media_root, imported_at=NOW, id_factory=lambda _: "DUP"
        )
        with self.assertRaisesRegex(NarrationMediaError, "覆盖"):
            import_narration_media(
                source, self.media_root, imported_at=NOW, id_factory=lambda _: "DUP"
            )


if __name__ == "__main__":
    unittest.main()
