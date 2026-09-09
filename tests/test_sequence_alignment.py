import unittest
from decimal import Decimal

from deeptalk_studio.alignment_profile import load_alignment_profile
from deeptalk_studio.sequence_alignment import align_sequences, rederive_alignment_trace
from deeptalk_studio.text_normalization import (
    NormalizedToken,
    normalization_profile,
    normalize_script_text,
)


def tokens(text):
    return normalize_script_text(text, normalization_profile())


def timed_tokens(text):
    plain = tokens(text)
    return tuple(
        NormalizedToken(
            token_id=f"TT{index + 1:06d}", normalized_text=token.normalized_text,
            match_keys=token.match_keys, original_start_char=token.original_start_char,
            original_end_char=token.original_end_char, source_unit_id=f"TU{index + 1:04d}",
            media_start_seconds=Decimal(index), media_end_seconds=Decimal(index + 1),
            timestamp_granularity="word",
        )
        for index, token in enumerate(plain)
    )


class SequenceAlignmentTests(unittest.TestCase):
    def test_exact_and_numeric_alias_matches_are_distinct_and_stable(self):
        trace = align_sequences(tokens("增长三十"), timed_tokens("增长30"), load_alignment_profile())
        self.assertEqual([op.operation for op in trace.operations], ["primary_match", "primary_match", "numeric_match"])
        self.assertEqual(trace.digest, rederive_alignment_trace(tokens("增长三十"), timed_tokens("增长30"), load_alignment_profile()).digest)

    def test_repeated_span_exposes_candidates_instead_of_hiding_tie(self):
        trace = align_sequences(tokens("甲乙甲乙"), timed_tokens("甲乙甲乙甲乙"), load_alignment_profile())
        self.assertGreaterEqual(len(trace.candidate_windows), 2)
        self.assertEqual(trace.ambiguity_code, "ambiguous_match")
        windows = [(w.transcript_token_start, w.transcript_token_end) for w in trace.candidate_windows]
        self.assertIn((0, 4), windows)
        self.assertIn((2, 6), windows)

    def test_insertions_deletions_substitutions_and_gaps_are_preserved(self):
        inserted = align_sequences(tokens("甲乙"), timed_tokens("甲丙乙"), load_alignment_profile())
        self.assertIn("transcript_insertion", [op.operation for op in inserted.operations])
        self.assertIn("ad_lib_transcript_span", [gap.gap_type for gap in inserted.gaps])
        deleted = align_sequences(tokens("甲丙乙"), timed_tokens("甲乙"), load_alignment_profile())
        self.assertIn("script_deletion", [op.operation for op in deleted.operations])
        self.assertIn("omitted_script_span", [gap.gap_type for gap in deleted.gaps])
        substituted = align_sequences(tokens("甲"), timed_tokens("乙"), load_alignment_profile())
        self.assertEqual(substituted.operations[0].operation, "substitution")

    def test_tie_break_prefers_insertion_then_deletion_over_substitution(self):
        profile = load_alignment_profile()
        custom = dict(profile)
        custom.update(substitution_score=-3.5, transcript_insertion_score=-1.5, script_deletion_score=-2.0)
        trace = align_sequences(tokens("甲"), timed_tokens("乙"), custom)
        self.assertEqual([op.operation for op in trace.operations], ["script_deletion", "transcript_insertion"])

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            align_sequences((), timed_tokens("甲"), load_alignment_profile())


if __name__ == "__main__":
    unittest.main()
