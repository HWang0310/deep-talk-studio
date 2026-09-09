import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from deeptalk_studio.narration_media import (
    NarrationMediaError,
    audio_extraction_profile,
    extract_transcription_audio,
    import_narration_media,
)
from deeptalk_studio.narration_schema import EXTRACTED_AUDIO_SCHEMA
from deeptalk_studio.validation import validate_json_schema
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture


NOW = "2026-08-13T12:00:00+08:00"


def count_pcm_samples(path: Path) -> int:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes()


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class AudioExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _media(self, spec):
        source = build_media_fixture(self.root / "inputs", spec)
        return import_narration_media(
            source,
            self.root / "media",
            imported_at=NOW,
            id_factory=lambda _: "MEDIA-" + spec.name,
        ).artifact

    def test_extraction_preserves_internal_silence_and_records_real_samples(self):
        media = self._media(
            MediaFixtureSpec(name="gap", video=True, audio=True, internal_gap=True)
        )
        output = self.root / "audio" / "gap.wav"
        result = extract_transcription_audio(
            media, output, profile=audio_extraction_profile(), created_at=NOW
        )
        self.assertEqual(result.artifact["sample_count"], count_pcm_samples(output))
        self.assertIn("internal_gap_preserved", result.artifact["applied_timeline_operations"])
        self.assertEqual(
            result.artifact["extraction_profile_version"], "audio-extraction-profile/1"
        )
        self.assertNotRegex(
            " ".join(result.command_arguments),
            r"silenceremove|loudnorm|atempo|atrim",
        )
        validate_json_schema(result.artifact, EXTRACTED_AUDIO_SCHEMA, "audio")

    def test_positive_audio_offset_is_evidence_not_leading_silence(self):
        media = self._media(
            MediaFixtureSpec(
                name="offset", video=True, audio=True, audio_offset="0.375"
            )
        )
        result = extract_transcription_audio(
            media,
            self.root / "audio" / "offset.wav",
            profile=audio_extraction_profile(),
            created_at=NOW,
        )
        self.assertGreaterEqual(float(result.artifact["source_audio_presentation_start_seconds"]), 0.35)
        self.assertEqual(result.artifact["first_extracted_sample_index"], 0)

    def test_resampling_is_deterministic_and_duplicate_or_no_audio_fails(self):
        media = self._media(
            MediaFixtureSpec(
                name="rate441", video=True, audio=True, audio_sample_rate=44100
            )
        )
        profile = audio_extraction_profile(sample_rate=48000, channels=1)
        output = self.root / "audio" / "rate.wav"
        result = extract_transcription_audio(media, output, profile=profile, created_at=NOW)
        self.assertEqual(result.artifact["sample_rate"], 48000)
        self.assertEqual(result.artifact["sample_count"], count_pcm_samples(output))
        with self.assertRaisesRegex(NarrationMediaError, "覆盖"):
            extract_transcription_audio(media, output, profile=profile, created_at=NOW)

        no_audio = self._media(MediaFixtureSpec(name="silent", video=True, audio=False))
        with self.assertRaisesRegex(NarrationMediaError, "没有音轨"):
            extract_transcription_audio(
                no_audio,
                self.root / "audio" / "silent.wav",
                profile=profile,
                created_at=NOW,
            )


if __name__ == "__main__":
    unittest.main()
