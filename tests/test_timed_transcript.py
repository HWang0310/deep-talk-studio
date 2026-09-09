import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.transcript_builder import (
    TimedTranscriptError,
    build_timed_transcript,
    validate_timed_transcript,
)
from deeptalk_studio.transcription import (
    DeterministicTranscriptionProvider,
    ProviderTimedUnit,
)
from deeptalk_studio.transcription_chunking import (
    load_transcription_chunk_profile,
    plan_transcription_chunks,
    profile_with_overrides,
)
from tests.test_transcription_chunking import mapping, write_pcm


NOW = "2026-08-13T12:00:00+08:00"


class TimedTranscriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audio = write_pcm(Path(self.temp.name) / "audio.wav", [12000] * 1400)
        self.audio.update(
            audio_id="AUDIO001",
            narration_media_id="MEDIA001",
            narration_media_sha256="a" * 64,
        )
        self.mapping = mapping("0.375")
        self.mapping.update(
            mapping_id="MAP001",
            mapping_digest="b" * 64,
            narration_media_id="MEDIA001",
        )
        self.media = {
            "media_id": "MEDIA001",
            "sha256": "a" * 64,
            "presentation_duration_seconds": "3",
        }
        profile = profile_with_overrides(
            load_transcription_chunk_profile(), request_cap_bytes=1244, search_window_ms=600
        )
        self.plan = plan_transcription_chunks(self.audio, self.mapping, profile)
        risk_id = f"CBR-{self.plan.boundaries[0].boundary_index:04d}"
        self.provider = DeterministicTranscriptionProvider(
            [
                ProviderTimedUnit(0, 0, Decimal("0"), Decimal("0.2"), "第一", boundary_risk_ids=(risk_id,)),
                ProviderTimedUnit(1, 1, Decimal("0"), Decimal("0.2"), "第二", boundary_risk_ids=(risk_id,)),
            ],
            granularity="word",
        ).transcribe(self.audio, self.plan, "zh", "fixture")

    def tearDown(self):
        self.temp.cleanup()

    def test_builder_maps_every_real_provider_boundary_once(self):
        artifact = build_timed_transcript(
            self.provider,
            self.media,
            self.audio,
            self.mapping,
            self.plan,
            transcript_id="TR001",
            created_at=NOW,
        )
        self.assertEqual(artifact["timed_units"][0]["media_start_seconds"], "0.375")
        expected_second = self.plan.chunks[1].extracted_start_seconds + Decimal("0.375")
        self.assertEqual(
            Decimal(artifact["timed_units"][1]["media_start_seconds"]), expected_second
        )
        validate_timed_transcript(
            artifact, self.media, self.audio, self.mapping, self.plan
        )

    def test_high_risk_chunk_guard_survives_canonical_transcript_build(self):
        artifact = build_timed_transcript(
            self.provider,
            self.media,
            self.audio,
            self.mapping,
            self.plan,
            transcript_id="TR002",
            created_at=NOW,
        )
        self.assertEqual(artifact["boundary_risks"][0]["risk_level"], "high")
        risk_id = artifact["boundary_risks"][0]["risk_id"]
        self.assertIn(risk_id, artifact["timed_units"][0]["boundary_risk_ids"])

    def test_validator_rejects_order_overlap_binding_and_risk_tamper(self):
        artifact = build_timed_transcript(
            self.provider,
            self.media,
            self.audio,
            self.mapping,
            self.plan,
            transcript_id="TR003",
            created_at=NOW,
        )
        mutations = []
        wrong_order = copy.deepcopy(artifact); wrong_order["timed_units"][1]["order"] = 9; mutations.append(wrong_order)
        wrong_map = copy.deepcopy(artifact); wrong_map["timed_units"][0]["media_start_seconds"] = "0"; mutations.append(wrong_map)
        wrong_risk = copy.deepcopy(artifact); wrong_risk["timed_units"][0]["boundary_risk_ids"] = []; mutations.append(wrong_risk)
        wrong_digest = copy.deepcopy(artifact); wrong_digest["transcript_digest"] = "x" * 64; mutations.append(wrong_digest)
        for forged in mutations:
            with self.assertRaises(TimedTranscriptError):
                validate_timed_transcript(
                    forged, self.media, self.audio, self.mapping, self.plan
                )


if __name__ == "__main__":
    unittest.main()
