import unittest

from deeptalk_studio.fact_conflict import detect_fact_conflicts


class FactConflictTests(unittest.TestCase):
    def test_conflict_records_actual_time_and_blocks_wrong_display(self):
        alignment = {"beat_timeline": [{"beat_id": "B001", "actual_start_seconds": "12.4", "actual_end_seconds": "16.8"}]}
        script = {"beats": [{"beat_id": "B001", "narration": "票房约七千元。"}]}
        transcript = {"text": "票房约七万元。"}
        conflicts = detect_fact_conflicts(script, transcript, alignment, [{"beat_id": "B001", "value": "七千元", "kind": "number"}])
        self.assertEqual(conflicts[0]["conflict_type"], "FACT_CONFLICT")
        self.assertEqual(conflicts[0]["actual_start_seconds"], "12.4")
        self.assertTrue(conflicts[0]["display_blocked"])

    def test_ordinary_paraphrase_is_not_a_fact_conflict(self):
        alignment = {"beat_timeline": [{"beat_id": "B001", "actual_start_seconds": "1.0", "actual_end_seconds": "3.0"}]}
        script = {"beats": [{"beat_id": "B001", "narration": "这个现象很反常。"}]}
        self.assertEqual(detect_fact_conflicts(script, {"text": "这事挺反常。"}, alignment, []), [])


if __name__ == "__main__":
    unittest.main()
