import random
import unittest

from deeptalk_studio.alignment_profile import load_alignment_profile
from deeptalk_studio.sequence_alignment import _align_sequences_full_reference, align_sequences
from tests.test_sequence_alignment import timed_tokens, tokens


class SequenceAlignmentPropertyTests(unittest.TestCase):
    def test_random_short_inputs_match_reference_and_repeat_digest(self):
        rng = random.Random(13082026)
        profile = load_alignment_profile()
        alphabet = "甲乙丙"
        for _ in range(100):
            left = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 7)))
            right = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 7)))
            optimized = align_sequences(tokens(left), timed_tokens(right), profile)
            reference = _align_sequences_full_reference(tokens(left), timed_tokens(right), profile)
            self.assertEqual(optimized.operations, reference.operations)
            self.assertEqual(optimized.candidate_windows, reference.candidate_windows)
            self.assertEqual(optimized.digest, align_sequences(tokens(left), timed_tokens(right), profile).digest)

    def test_long_input_is_deterministic(self):
        left = "甲乙丙" * 100
        right = "甲乙丙" * 50 + "丁" + "甲乙丙" * 50
        one = align_sequences(tokens(left), timed_tokens(right), load_alignment_profile())
        two = align_sequences(tokens(left), timed_tokens(right), load_alignment_profile())
        self.assertEqual(one.digest, two.digest)


if __name__ == "__main__":
    unittest.main()
