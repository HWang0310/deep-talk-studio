import copy
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from deeptalk_studio.transcription_chunking import (
    TranscriptionChunkingError,
    load_transcription_chunk_profile,
    plan_transcription_chunks,
    profile_with_overrides,
    validate_transcription_chunk_plan,
)


def write_pcm(path: Path, amplitudes, sample_rate=1000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"".join(struct.pack("<h", value) for value in amplitudes))
    return {
        "artifact_version": "extracted-audio/1",
        "audio_id": "AUDIO001",
        "immutable_local_path": str(path),
        "sha256": "fixture",
        "artifact_digest": "a" * 64,
        "sample_rate": sample_rate,
        "channels": 1,
        "sample_width_bytes": 2,
        "sample_count": len(amplitudes),
    }


def mapping(offset="0.375"):
    return {
        "mapping_id": "MAP001",
        "mapping_digest": "b" * 64,
        "scale_numerator": 1,
        "scale_denominator": 1,
        "offset_seconds": offset,
    }


class TranscriptionChunkingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = profile_with_overrides(
            load_transcription_chunk_profile(),
            request_cap_bytes=1244,
            search_window_ms=600,
            analysis_window_ms=20,
            hop_ms=10,
            safe_pause_min_ms=300,
            fallback_interval_ms=300,
            risk_guard_ms=1000,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_default_request_cap_is_below_provider_hard_limit(self):
        profile = load_transcription_chunk_profile()
        self.assertLess(profile["request_cap_bytes"], profile["provider_hard_limit_bytes"])
        self.assertEqual(profile["safe_pause_threshold_mean_square"], 67744)

    def test_nominal_mid_sentence_boundary_moves_to_natural_pause(self):
        amplitudes = [12000] * 150 + [0] * 350 + [12000] * 1100
        audio = write_pcm(self.root / "pause.wav", amplitudes)
        nominal = (self.profile["request_cap_bytes"] - 44) // 2
        plan = plan_transcription_chunks(audio, mapping(), self.profile)
        self.assertNotEqual(plan.chunks[0].end_sample, nominal)
        self.assertEqual(plan.boundaries[0].selection_mode, "safe_pause")
        self.assertEqual(plan.boundaries[0].boundary_risk, "none")
        validate_transcription_chunk_plan(plan, audio, mapping(), self.profile)

    def test_no_pause_uses_deterministic_risk_guard(self):
        audio = write_pcm(self.root / "speech.wav", [12000] * 1600)
        first = plan_transcription_chunks(audio, mapping(), self.profile)
        second = plan_transcription_chunks(audio, mapping(), self.profile)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.boundaries[0].boundary_risk, "high")
        self.assertEqual(first.boundaries[0].reason, "no_safe_pause_fallback")
        self.assertGreater(first.boundaries[0].guard_duration_seconds, 0)

    def test_chunks_cover_pcm_exactly_once_and_map_nonzero_offset(self):
        audio = write_pcm(self.root / "coverage.wav", [1000] * 1700)
        plan = plan_transcription_chunks(audio, mapping("0.375"), self.profile)
        self.assertEqual(plan.chunks[0].start_sample, 0)
        self.assertEqual(plan.chunks[-1].end_sample, 1700)
        for left, right in zip(plan.chunks, plan.chunks[1:]):
            self.assertEqual(left.end_sample, right.start_sample)
        self.assertEqual(str(plan.chunks[0].media_start_seconds), "0.375")
        self.assertTrue(all(chunk.path.stat().st_size <= self.profile["request_cap_bytes"] for chunk in plan.chunks))

    def test_profile_or_pcm_tamper_is_rejected(self):
        audio = write_pcm(self.root / "tamper.wav", [1000] * 1600)
        plan = plan_transcription_chunks(audio, mapping(), self.profile)
        changed = copy.deepcopy(self.profile)
        changed["search_window_ms"] += 10
        with self.assertRaises(TranscriptionChunkingError):
            validate_transcription_chunk_plan(plan, audio, mapping(), changed)
        with wave.open(str(Path(audio["immutable_local_path"])), "wb") as handle:
            handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(1000)
            handle.writeframes(struct.pack("<h", 1) * 1600)
        with self.assertRaises(TranscriptionChunkingError):
            validate_transcription_chunk_plan(plan, audio, mapping(), self.profile)


if __name__ == "__main__":
    unittest.main()
