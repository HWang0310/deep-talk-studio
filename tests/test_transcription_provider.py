import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.transcription import (
    DeterministicTranscriptionProvider,
    ProviderTimedUnit,
    TranscriptionProviderError,
)
from deeptalk_studio.transcription_chunking import (
    load_transcription_chunk_profile,
    plan_transcription_chunks,
    profile_with_overrides,
)
from tests.test_transcription_chunking import mapping, write_pcm


class TranscriptionProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        audio = write_pcm(Path(self.temp.name) / "audio.wav", [1000] * 1400)
        self.audio = audio
        profile = profile_with_overrides(
            load_transcription_chunk_profile(), request_cap_bytes=1244, search_window_ms=600
        )
        self.chunk_plan = plan_transcription_chunks(audio, mapping(), profile)

    def tearDown(self):
        self.temp.cleanup()

    def test_deterministic_provider_returns_declared_real_granularity_only(self):
        units = [ProviderTimedUnit(0, 0, Decimal("0"), Decimal("0.2"), "你好")]
        result = DeterministicTranscriptionProvider(units, granularity="segment").transcribe(
            self.audio, self.chunk_plan, "zh", "fixture"
        )
        self.assertEqual(result.timestamp_granularity, "segment")
        self.assertFalse(hasattr(result.units[0], "interpolated_words"))
        self.assertEqual(result.units[0].chunk_index, 0)

    def test_provider_preserves_overlap_and_binds_known_boundary_risk(self):
        risk_id = f"CBR-{self.chunk_plan.boundaries[0].boundary_index:04d}"
        units = [
            ProviderTimedUnit(0, 0, Decimal("0.10"), Decimal("0.25"), "一", boundary_risk_ids=(risk_id,)),
            ProviderTimedUnit(0, 1, Decimal("0.20"), Decimal("0.30"), "二", boundary_risk_ids=(risk_id,)),
        ]
        result = DeterministicTranscriptionProvider(units, granularity="word").transcribe(
            self.audio, self.chunk_plan, "zh", "fixture"
        )
        self.assertLess(result.units[1].local_start_seconds, result.units[0].local_end_seconds)
        self.assertEqual(result.boundary_risks[0].risk_id, risk_id)

    def test_unknown_risk_negative_or_empty_unit_is_rejected(self):
        bad_units = [
            ProviderTimedUnit(0, 0, Decimal("-1"), Decimal("0"), "坏"),
            ProviderTimedUnit(0, 0, Decimal("0"), Decimal("1"), ""),
            ProviderTimedUnit(0, 0, Decimal("0"), Decimal("1"), "坏", boundary_risk_ids=("UNKNOWN",)),
        ]
        for unit in bad_units:
            with self.assertRaises(TranscriptionProviderError):
                DeterministicTranscriptionProvider([unit], granularity="word").transcribe(
                    self.audio, self.chunk_plan, "zh", "fixture"
                )


if __name__ == "__main__":
    unittest.main()
