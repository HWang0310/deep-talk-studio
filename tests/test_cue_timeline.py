import unittest

from deeptalk_studio.alignment_builder import build_script_alignment
from tests.alignment_fixtures import NOW, mapping_fixture, profile_fixture, script_fixture, transcript_fixture


class CueTimelineTests(unittest.TestCase):
    def build(self, cues, transcript=None, media_duration="30"):
        return build_script_alignment(
            script_fixture(), transcript or transcript_fixture(), mapping_fixture(), profile_fixture(), cues,
            alignment_id="AL-cues", created_at=NOW, media={"media_id":"NM-align","sha256":"m"*64,"presentation_duration_seconds":media_duration},
        )

    def test_one_short_anchor_maps_out_to_full_spoken_beat_end(self):
        cue=self.build([{"cue_id":"VC001","beat_id":"B001","placement_anchor":"事件"}])["cue_timeline"][0]
        beat=self.build([{"cue_id":"VC001","beat_id":"B001","placement_anchor":"事件"}])["beat_timeline"][0]
        self.assertEqual(cue["actual_end_seconds"],beat["actual_end_seconds"])
        self.assertGreater(float(cue["actual_end_seconds"])-float(cue["actual_start_seconds"]),1)

    def test_same_beat_multiple_cues_have_semantic_spans_to_next_anchor(self):
        cues = [
            {"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "事件发生"},
            {"cue_id": "VC002", "beat_id": "B001", "placement_anchor": "八月九日"},
        ]
        transcript = transcript_fixture()
        units = []
        cursor = 0.0
        for text in ("事件发生在八月九日", "机构说问题来自流程故障", "还有第三种选择"):
            for char in text:
                units.append({
                    "unit_id": f"TU{len(units) + 1:04d}",
                    "order": len(units),
                    "spoken_text": char,
                    "media_start_seconds": str(cursor),
                    "media_end_seconds": str(cursor + 0.25),
                    "boundary_risk_ids": [],
                })
                cursor += 0.25
        transcript["timed_units"] = units
        result = self.build(cues, transcript=transcript)
        timeline = result["cue_timeline"]
        self.assertEqual(timeline[0]["semantic_char_end"], timeline[1]["anchor_char_start"])
        self.assertEqual(timeline[0]["actual_end_seconds"], timeline[1]["actual_start_seconds"])
        beat_end=result["beat_timeline"][0]["actual_end_seconds"]
        self.assertEqual(timeline[1]["actual_end_seconds"],beat_end)
        self.assertTrue(all(cue["placement_status"] == "aligned" for cue in timeline))

    def test_alignment_duration_comes_from_clean_aroll_not_last_spoken_unit(self):
        result=self.build([{"cue_id":"VC001","beat_id":"B001","placement_anchor":"事件"}],media_duration="42.5")
        self.assertEqual(result["presentation_duration_seconds"],"42.5")
        self.assertNotEqual(result["presentation_duration_seconds"],result["beat_timeline"][-1]["actual_end_seconds"])

    def test_media_duration_shorter_than_last_spoken_unit_fails(self):
        with self.assertRaisesRegex(ValueError, "不能短于"):
            self.build([{"cue_id":"VC001","beat_id":"B001","placement_anchor":"事件"}], media_duration="1")

    def test_missing_or_duplicate_script_anchor_is_unplaced(self):
        cues = [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "不存在"}]
        self.assertEqual(self.build(cues)["cue_timeline"][0]["placement_status"], "unplaced")
        script = script_fixture()
        script["beats"][0]["narration"] = "事件发生，然后事件发生。"
        result = build_script_alignment(script, transcript_fixture(), mapping_fixture(), profile_fixture(),
            [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "事件发生"}],
            alignment_id="AL-dup", created_at=NOW,media={"media_id":"NM-align","sha256":"m"*64,"presentation_duration_seconds":"30"})
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
