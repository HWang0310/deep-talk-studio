import unittest

from deeptalk_studio.semantic_timeline import SemanticTimelineError, build_semantic_timeline


NOW = "2026-08-24T10:00:00+08:00"


def script():
    return {"script_id": "SCR-1", "revision": 4, "beats": [
        {"beat_id": "B001", "narration": "第一段说明为什么反常。"},
        {"beat_id": "B002", "narration": "第二段解释票房变化。"},
    ]}


def alignment(actual=True):
    return {
        "artifact_digest": "a" * 64,
        "transcript_digest": "b" * 64,
        "timing_provenance": "actual_aroll_alignment" if actual else "estimated_script_timing",
        "beat_timeline": [
            {"beat_id": "B001", "actual_start_seconds": "0.0", "actual_end_seconds": "12.4", "alignment_status": "aligned", "confidence": "high"},
            {"beat_id": "B002", "actual_start_seconds": "12.4", "actual_end_seconds": "20.0", "alignment_status": "aligned", "confidence": "high"},
        ],
    }


class SemanticTimelineTests(unittest.TestCase):
    def test_requires_actual_clean_aroll_alignment(self):
        with self.assertRaisesRegex(SemanticTimelineError, "Clean A-roll Alignment"):
            build_semantic_timeline(script(), alignment(actual=False), [], timeline_id="ST-1", created_at=NOW)

    def test_keeps_real_times_and_marks_fact_conflict_span_keep_only(self):
        conflicts = [{"beat_id": "B002", "display_blocked": True}]
        result = build_semantic_timeline(script(), alignment(), conflicts, timeline_id="ST-1", created_at=NOW)
        self.assertEqual(result["spans"][1]["actual_start_seconds"], "12.4")
        self.assertEqual(result["spans"][1]["visual_eligibility"], "keep_only")
        self.assertEqual(result["spans"][1]["summary"], "第二段解释票房变化。")


if __name__ == "__main__":
    unittest.main()
