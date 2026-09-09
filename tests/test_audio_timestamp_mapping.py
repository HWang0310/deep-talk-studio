import copy
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.audio_timestamp_mapping import (
    TimestampMappingError,
    derive_timestamp_mapping,
    map_extracted_seconds,
    validate_timestamp_mapping,
)
from deeptalk_studio.narration_media import (
    audio_extraction_profile,
    extract_transcription_audio,
    import_narration_media,
)
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture


NOW = "2026-08-13T12:00:00+08:00"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class AudioTimestampMappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _roots(self, *, name="identity", offset="0", sample_rate=48000):
        source = build_media_fixture(
            self.root / "inputs",
            MediaFixtureSpec(
                name=name,
                video=True,
                audio=True,
                audio_offset=offset,
                audio_sample_rate=sample_rate,
            ),
        )
        media = import_narration_media(
            source,
            self.root / "media",
            imported_at=NOW,
            id_factory=lambda _: "MEDIA-" + name,
        ).artifact
        extracted = extract_transcription_audio(
            media,
            self.root / "audio" / f"{name}.wav",
            profile=audio_extraction_profile(),
            created_at=NOW,
        ).artifact
        return media, extracted

    def test_nonzero_offset_is_evidence_backed_not_forced_to_identity(self):
        media, extracted = self._roots(name="offset", offset="0.375")
        mapping = derive_timestamp_mapping(
            media, extracted, mapping_id="MAP001", created_at=NOW
        )
        self.assertEqual(mapping["scale_numerator"], 1)
        self.assertGreaterEqual(Decimal(mapping["offset_seconds"]), Decimal("0.35"))
        self.assertEqual(
            map_extracted_seconds(mapping, Decimal("1")),
            Decimal("1") + Decimal(mapping["offset_seconds"]),
        )
        validate_timestamp_mapping(mapping, media, extracted)

    def test_tolerance_uses_sample_codec_frame_and_timebase_evidence(self):
        media, extracted = self._roots(name="aac")
        mapping = derive_timestamp_mapping(
            media, extracted, mapping_id="MAP002", created_at=NOW
        )
        expected = max(
            Decimal(1) / Decimal(extracted["sample_rate"]),
            Decimal(1024) / Decimal(media["audio_stream"]["sample_rate"]),
            Decimal(1) / Decimal(48000),
        )
        self.assertEqual(Decimal(mapping["mapping_tolerance_seconds"]), expected)

    def test_validator_rejects_scale_offset_digest_duration_and_bounds_tamper(self):
        media, extracted = self._roots(name="tamper")
        mapping = derive_timestamp_mapping(
            media, extracted, mapping_id="MAP003", created_at=NOW
        )
        for field, value in (
            ("scale_numerator", 2),
            ("offset_seconds", "9"),
            ("evidence_digest", "x" * 64),
            ("mapped_end_seconds", "999"),
        ):
            forged = copy.deepcopy(mapping)
            forged[field] = value
            with self.assertRaises(TimestampMappingError):
                validate_timestamp_mapping(forged, media, extracted)


if __name__ == "__main__":
    unittest.main()
