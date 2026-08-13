import random
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.transcription_chunking import (
    load_transcription_chunk_profile,
    plan_transcription_chunks,
    profile_with_overrides,
)
from tests.test_transcription_chunking import mapping, write_pcm


class TranscriptionChunkingPropertyTests(unittest.TestCase):
    def test_seeded_pcm_has_repeat_stable_monotonic_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            rng = random.Random(7331)
            samples = [rng.randint(-14000, 14000) for _ in range(2400)]
            samples[500:850] = [0] * 350
            samples[1300:1650] = [0] * 350
            audio = write_pcm(Path(temp) / "seeded.wav", samples)
            profile = profile_with_overrides(
                load_transcription_chunk_profile(),
                request_cap_bytes=1244,
                search_window_ms=600,
            )
            first = plan_transcription_chunks(audio, mapping(), profile)
            second = plan_transcription_chunks(audio, mapping(), profile)
            self.assertEqual(first.digest, second.digest)
            ends = [chunk.end_sample for chunk in first.chunks]
            self.assertEqual(ends, sorted(ends))
            self.assertEqual(sum(chunk.end_sample - chunk.start_sample for chunk in first.chunks), len(samples))


if __name__ == "__main__":
    unittest.main()
