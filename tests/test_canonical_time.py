import unittest
from decimal import Decimal

from deeptalk_studio.canonical_time import (
    format_canonical_timecode,
    format_preview_frame_timecode,
    preview_frame,
)


class CanonicalTimeTests(unittest.TestCase):
    def test_canonical_time_is_fps_neutral_and_supports_more_than_24_hours(self):
        self.assertEqual(
            format_canonical_timecode(Decimal("90061.2345")),
            "25:01:01.235",
        )
        self.assertEqual(preview_frame(Decimal("1.001")), 31)

    def test_milliseconds_round_half_up_and_negative_time_is_rejected(self):
        self.assertEqual(format_canonical_timecode(Decimal("0.0005")), "00:00:00.001")
        self.assertEqual(format_canonical_timecode(Decimal("0.0004")), "00:00:00.000")
        with self.assertRaises(ValueError):
            format_canonical_timecode(Decimal("-0.001"))

    def test_preview_frames_are_ceil_rounded_for_common_and_fractional_rates(self):
        for fps in (Decimal("25"), Decimal("29.97"), Decimal("30"), Decimal("50"), Decimal("60")):
            self.assertEqual(preview_frame(Decimal("1.001"), fps), int((Decimal("1.001") * fps).to_integral_value(rounding="ROUND_CEILING")))
        self.assertEqual(format_preview_frame_timecode(31, 30), "00:00:01:01")
        with self.assertRaises(ValueError):
            preview_frame(Decimal("1"), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
