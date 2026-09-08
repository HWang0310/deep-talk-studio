"""Producer-driven integration test: build_semantic_timeline() -> build_visual_opportunity_plan().

Proves that the canonical Semantic Timeline producer's real output is
consumed by the V2 WHERE boundary, and that a_roll_window values are
exactly projected from actual_start_seconds / actual_end_seconds.
"""
import hashlib
import json
import unittest

from deeptalk_studio.semantic_timeline import build_semantic_timeline
from deeptalk_studio.visual_opportunity import build_visual_opportunity_plan
from deeptalk_studio.visual_opportunity_directive import normalize_visual_opportunity_directives


NOW = "2026-09-08T10:00:00+08:00"
DEFAULTS = {"language": "zh-CN", "canvas": {"width": 1920, "height": 1080}, "target_duration_ms": 3000}


def _synthetic_script():
    return {
        "script_id": "SCR-producer-01",
        "revision": 1,
        "beats": [
            {"beat_id": "P001", "narration": "Synthetic segment one for timing projection."},
            {"beat_id": "P002", "narration": "Synthetic segment two for timing projection."},
            {"beat_id": "P003", "narration": "Synthetic segment three with fact conflict."},
        ],
    }


def _synthetic_alignment():
    return {
        "artifact_digest": "a" * 64,
        "transcript_digest": "b" * 64,
        "timing_provenance": "actual_aroll_alignment",
        "beat_timeline": [
            {"beat_id": "P001", "actual_start_seconds": "1.234", "actual_end_seconds": "4.567",
             "alignment_status": "aligned", "confidence": "high"},
            {"beat_id": "P002", "actual_start_seconds": "4.567", "actual_end_seconds": "7.890",
             "alignment_status": "aligned", "confidence": "high"},
            {"beat_id": "P003", "actual_start_seconds": "7.890", "actual_end_seconds": "10.000",
             "alignment_status": "aligned", "confidence": "medium"},
        ],
    }


def _synthetic_fact_conflicts():
    return [{"beat_id": "P003", "display_blocked": True}]


class ProducerDrivenTimingTests(unittest.TestCase):
    def test_build_semantic_timeline_to_visual_opportunity_exact_ms_projection(self):
        """Producer-driven: real build_semantic_timeline() output -> build_visual_opportunity_plan().

        a_roll_window must be exactly projected from actual_*_seconds.
        """
        timeline = build_semantic_timeline(
            _synthetic_script(),
            _synthetic_alignment(),
            _synthetic_fact_conflicts(),
            timeline_id="ST-producer-01",
            created_at=NOW,
        )
        self.assertEqual(timeline["artifact_version"], "semantic-timeline/1")
        self.assertEqual(timeline["timing_provenance"], "actual_aroll_alignment")

        safe_spans = [s for s in timeline["spans"] if s["visual_eligibility"] == "safe"]
        self.assertEqual(len(safe_spans), 2)
        keep_only_spans = [s for s in timeline["spans"] if s["visual_eligibility"] == "keep_only"]
        self.assertEqual(len(keep_only_spans), 1)

        directives = {
            "artifact_version": "visual-opportunity-directives/1",
            "directives_id": "VOD-producer-01",
            "revision": 1,
            "semantic_timeline_digest": timeline["timeline_digest"],
            "reviewed_script_digest": "e" * 64,
            "directives": [
                {
                    "directive_id": "d-p01",
                    "span_id": "ST001",
                    "visual_purpose": "Illustrate segment one.",
                    "why_opportunity": "Visual aid helps explain the concept.",
                    "semantic_context_selector": {"include_neighboring_spans": 0},
                    "factual_context_refs": [],
                },
                {
                    "directive_id": "d-p02",
                    "span_id": "ST002",
                    "visual_purpose": "Illustrate segment two.",
                    "why_opportunity": "Visual aid helps explain the concept.",
                    "semantic_context_selector": {"include_neighboring_spans": 0},
                    "factual_context_refs": [],
                },
            ],
        }

        plan = build_visual_opportunity_plan(timeline, directives, defaults=DEFAULTS)
        self.assertEqual(plan["artifact_version"], "visual-opportunity-plan/1")
        self.assertEqual(len(plan["opportunities"]), 2)

        self.assertEqual(
            plan["opportunities"][0]["a_roll_window"],
            {"start_ms": 1234, "end_ms": 4567},
        )
        self.assertEqual(
            plan["opportunities"][1]["a_roll_window"],
            {"start_ms": 4567, "end_ms": 7890},
        )

        span_ids_in_audit = {a["span_id"] for a in plan["span_audit"]}
        self.assertIn("ST003", span_ids_in_audit)
        st003_audit = [a for a in plan["span_audit"] if a["span_id"] == "ST003"][0]
        self.assertEqual(st003_audit["status"], "NO_OPPORTUNITY")
        self.assertEqual(st003_audit["reason"], "fact_conflict")

    def test_producer_timing_values_come_from_real_build_not_hand_construction(self):
        """Sanity: the timeline is produced by build_semantic_timeline(), not hand-crafted."""
        timeline = build_semantic_timeline(
            _synthetic_script(),
            _synthetic_alignment(),
            _synthetic_fact_conflicts(),
            timeline_id="ST-producer-02",
            created_at=NOW,
        )
        payload = dict(timeline)
        supplied = payload.pop("timeline_digest")
        recomputed = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")
        ).hexdigest()
        self.assertEqual(supplied, recomputed, "timeline_digest must be self-consistent")
        self.assertEqual(timeline["spans"][0]["actual_start_seconds"], "1.234")
        self.assertEqual(timeline["spans"][0]["actual_end_seconds"], "4.567")
        self.assertEqual(timeline["spans"][1]["actual_start_seconds"], "4.567")
        self.assertEqual(timeline["spans"][1]["actual_end_seconds"], "7.890")


if __name__ == "__main__":
    unittest.main()
