import unittest

from deeptalk_studio.alignment_builder import build_script_alignment
from tests.alignment_fixtures import (
    NOW, cue_fixture, mapping_fixture, profile_fixture, script_fixture, transcript_fixture,
)


class AlignmentBuilderTests(unittest.TestCase):
    def build(self, transcript=None, cues=None):
        return build_script_alignment(
            script_fixture(), transcript or transcript_fixture(), mapping_fixture(),
            profile_fixture(), cue_fixture() if cues is None else cues,
            alignment_id="AL001", created_at=NOW,
        )

    def test_exact_anchor_reuses_existing_beat_and_cue_identity(self):
        artifact = self.build()
        self.assertEqual(artifact["beat_timeline"][0]["beat_id"], "B001")
        self.assertEqual(artifact["cue_timeline"][0]["cue_id"], "VC001")
        self.assertTrue(all(beat["alignment_status"] == "aligned" for beat in artifact["beat_timeline"]))
        self.assertTrue(all(beat["confidence"] == "high" for beat in artifact["beat_timeline"]))

    def test_missing_middle_beat_does_not_block_later_recovery(self):
        artifact = self.build(transcript_fixture(omit_second=True))
        statuses = {beat["beat_id"]: beat["alignment_status"] for beat in artifact["beat_timeline"]}
        self.assertEqual(statuses["B002"], "unmatched")
        self.assertEqual(statuses["B003"], "aligned")

    def test_segment_transcript_is_coarse_and_never_aligned_high(self):
        artifact = self.build(transcript_fixture(granularity="segment"))
        self.assertTrue(all(beat["alignment_status"] == "needs_review" for beat in artifact["beat_timeline"]))
        self.assertTrue(all(beat["confidence"] != "high" for beat in artifact["beat_timeline"]))

    def test_boundary_risk_forces_affected_area_but_later_beat_recovers(self):
        artifact = self.build(transcript_fixture(risky=True))
        beats = {beat["beat_id"]: beat for beat in artifact["beat_timeline"]}
        self.assertEqual(beats["B002"]["alignment_status"], "needs_review")
        self.assertIn("chunk_boundary_risk", beats["B002"]["deviation_codes"])
        self.assertEqual(beats["B003"]["alignment_status"], "aligned")

    def test_digest_and_timestamps_are_stable_and_monotonic(self):
        one = self.build()
        two = self.build()
        self.assertEqual(one["artifact_digest"], two["artifact_digest"])
        starts = [float(beat["actual_start_seconds"]) for beat in one["beat_timeline"]]
        self.assertEqual(starts, sorted(starts))


if __name__ == "__main__":
    unittest.main()
