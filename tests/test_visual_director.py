import unittest

from deeptalk_studio.visual_director import VisualDirectorError, build_visual_director_plan


class VisualDirectorTests(unittest.TestCase):
    def test_uses_alignment_range_and_defaults_to_keep_aroll(self):
        plan = build_visual_director_plan(
            {"alignment_digest": "a" * 64, "ranges": {"C001": ("12.0", "18.0")}},
            [{"opportunity_id": "VO001", "cue_id": "C001", "visual_intent": "保留情绪", "why_visual": "情绪表演更重要"}],
            plan_id="VD-1", created_at="2026-08-24T00:00:00+00:00",
        )
        item = plan["opportunities"][0]
        self.assertEqual(item["decision"], "KEEP_A_ROLL")
        self.assertEqual(item["source_time_range"], {"start_seconds": "12.0", "end_seconds": "18.0"})

    def test_rejects_proposal_supplied_clock(self):
        with self.assertRaises(VisualDirectorError):
            build_visual_director_plan(
                {"alignment_digest": "a" * 64, "ranges": {"C001": ("12.0", "18.0")}},
                [{"opportunity_id": "VO001", "cue_id": "C001", "start_seconds": "1", "visual_intent": "x", "why_visual": "y"}],
                plan_id="VD-1", created_at="2026-08-24T00:00:00+00:00",
            )
