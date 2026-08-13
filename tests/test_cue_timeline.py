import unittest

from deeptalk_studio.alignment_builder import build_script_alignment
from tests.alignment_fixtures import NOW, mapping_fixture, profile_fixture, script_fixture, transcript_fixture


class CueTimelineTests(unittest.TestCase):
    def build(self, cues, transcript=None):
        return build_script_alignment(
            script_fixture(), transcript or transcript_fixture(), mapping_fixture(), profile_fixture(), cues,
            alignment_id="AL-cues", created_at=NOW,
        )

    def test_same_beat_multiple_cues_have_semantic_spans_to_next_anchor(self):
        cues = [
            {"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "事件发生"},
            {"cue_id": "VC002", "beat_id": "B001", "placement_anchor": "八月九日"},
        ]
        timeline = self.build(cues)["cue_timeline"]
        self.assertEqual(timeline[0]["semantic_char_end"], timeline[1]["anchor_char_start"])
        self.assertTrue(all(cue["placement_status"] == "aligned" for cue in timeline))

    def test_missing_or_duplicate_script_anchor_is_unplaced(self):
        cues = [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "不存在"}]
        self.assertEqual(self.build(cues)["cue_timeline"][0]["placement_status"], "unplaced")
        script = script_fixture()
        script["beats"][0]["narration"] = "事件发生，然后事件发生。"
        result = build_script_alignment(script, transcript_fixture(), mapping_fixture(), profile_fixture(),
            [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "事件发生"}],
            alignment_id="AL-dup", created_at=NOW)
        self.assertEqual(result["cue_timeline"][0]["placement_status"], "unplaced")
        self.assertIn("ambiguous_anchor", result["cue_timeline"][0]["deviation_codes"])

    def test_segment_and_boundary_risk_are_not_ready(self):
        cue = [{"cue_id": "VC001", "beat_id": "B002", "placement_anchor": "流程故障"}]
        coarse = self.build(cue, transcript_fixture(granularity="segment"))["cue_timeline"][0]
        self.assertEqual(coarse["placement_status"], "coarse")
        risky = self.build(cue, transcript_fixture(risky=True))["cue_timeline"][0]
        self.assertEqual(risky["placement_status"], "needs_review")
        self.assertIn("chunk_boundary_risk", risky["deviation_codes"])


if __name__ == "__main__":
    unittest.main()
