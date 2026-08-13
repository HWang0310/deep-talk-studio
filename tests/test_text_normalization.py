import unittest
from decimal import Decimal

from deeptalk_studio.text_normalization import (
    normalization_digest,
    normalization_profile,
    normalize_script_text,
    normalize_transcript_units,
)


class TextNormalizationTests(unittest.TestCase):
    def test_nfkc_numeric_alias_and_original_span_are_preserved(self):
        source = "ＡI增长百分之三十，约30%。"
        tokens = normalize_script_text(source, normalization_profile())
        self.assertIn("30%", {key for token in tokens for key in token.match_keys})
        self.assertEqual("ＡI", source[tokens[0].original_start_char:tokens[0].original_end_char])
        self.assertEqual(tokens[0].normalized_text, "ai")

    def test_punctuation_case_and_mixed_boundaries_are_stable(self):
        left = normalize_script_text("DeepTalk，事件 2026年8月13日。", normalization_profile())
        right = normalize_script_text("deeptalk 事件 2026-08-13", normalization_profile())
        self.assertEqual(left[0].match_keys, right[0].match_keys)
        self.assertEqual([t.normalized_text for t in left[:3]], ["deeptalk", "事", "件"])
        self.assertIn("2026-08-13", {k for t in left for k in t.match_keys})

    def test_strict_chinese_numerals_do_not_guess_ambiguous_list_words(self):
        parsed = normalize_script_text("负三点五 三十 二零二六年八月十三日", normalization_profile())
        keys = {key for token in parsed for key in token.match_keys}
        self.assertIn("-3.5", keys)
        self.assertIn("30", keys)
        self.assertIn("2026-08-13", keys)
        ambiguous = normalize_script_text("一、两种解释", normalization_profile())
        self.assertNotIn("1", {k for t in ambiguous for k in t.match_keys})
        self.assertNotIn("2", {k for t in ambiguous for k in t.match_keys})

    def test_transcript_tokens_keep_real_unit_boundaries(self):
        units = [
            {
                "unit_id": "TU0001",
                "spoken_text": "增长３０%",
                "media_start_seconds": "1.250",
                "media_end_seconds": "1.750",
            }
        ]
        tokens = normalize_transcript_units(units, normalization_profile(), granularity="word")
        self.assertTrue(all(t.source_unit_id == "TU0001" for t in tokens))
        self.assertTrue(all(t.media_start_seconds == Decimal("1.250") for t in tokens))
        self.assertTrue(all(t.timestamp_granularity == "word" for t in tokens))
        self.assertEqual(normalization_digest(tokens), normalization_digest(tokens))

    def test_profile_or_input_validation_is_strict(self):
        with self.assertRaises(ValueError):
            normalize_script_text("", normalization_profile())
        profile = normalization_profile()
        profile["profile_version"] = "normalization-profile/404"
        with self.assertRaises(ValueError):
            normalize_script_text("测试", profile)


if __name__ == "__main__":
    unittest.main()
