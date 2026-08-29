import copy
import unittest

from deeptalk_studio.visual_opportunity import (
    VisualOpportunityError,
    build_visual_opportunity_plan,
)


def timeline():
    return {
        "artifact_version": "semantic-timeline/1",
        "timeline_id": "ST-synthetic-01",
        "timing_provenance": "actual_aroll_alignment",
        "alignment_digest": "c" * 64,
        "transcript_digest": "d" * 64,
        "timeline_digest": "a" * 64,
        "spans": [
            {"span_id": "ST001", "actual_start_seconds": "1.234", "actual_end_seconds": "4.567", "summary": "Synthetic safe semantics.", "visual_eligibility": "safe", "reason": "safe_real_alignment"},
            {"span_id": "ST002", "actual_start_seconds": "4.567", "actual_end_seconds": "7.000", "summary": "Conflict semantics.", "visual_eligibility": "keep_only", "reason": "FACT_CONFLICT"},
            {"span_id": "ST003", "actual_start_seconds": "7.000", "actual_end_seconds": "9.000", "summary": "Safe base layer semantics.", "visual_eligibility": "safe", "reason": "safe_real_alignment"},
        ],
    }


def directives():
    return {
        "artifact_version": "visual-opportunity-directives/1", "directives_id": "VOD-synthetic-01", "revision": 1,
        "semantic_timeline_digest": "a" * 64, "reviewed_script_digest": "b" * 64,
        "directives": [{
            "directive_id": "vod-synthetic-01", "span_id": "ST001", "visual_purpose": "Explain the synthetic sequence.",
            "why_opportunity": "A synthetic causal sequence.", "semantic_context_selector": {"include_neighboring_spans": 1},
            "factual_context_refs": [{"claim_id": "claim-01", "evidence_id": "evidence-01"}],
        }],
    }


DEFAULTS = {"language": "zh-CN", "canvas": {"width": 1920, "height": 1080}, "target_duration_ms": 2400}


class VisualOpportunityTests(unittest.TestCase):
    def test_safe_span_creates_exactly_timed_opportunity_and_full_span_audit(self):
        plan = build_visual_opportunity_plan(timeline(), directives(), defaults=DEFAULTS)
        opportunity = plan["opportunities"][0]
        self.assertEqual(opportunity["a_roll_window"], {"start_ms": 1234, "end_ms": 4567})
        self.assertEqual(opportunity["target_duration_ms"], 2400)
        self.assertEqual(opportunity["factual_context"], directives()["directives"][0]["factual_context_refs"])
        self.assertEqual(
            plan["span_audit"],
            [
                {"span_id": "ST001", "status": "OPPORTUNITY_CREATED"},
                {"span_id": "ST002", "status": "NO_OPPORTUNITY", "reason": "fact_conflict"},
                {"span_id": "ST003", "status": "NO_OPPORTUNITY", "reason": "creator_base_layer"},
            ],
        )

    def test_rejects_digest_mismatch_non_integral_ms_and_directive_clock_leakage(self):
        mismatch = directives(); mismatch["semantic_timeline_digest"] = "e" * 64
        with self.assertRaisesRegex(VisualOpportunityError, "semantic_timeline_digest"):
            build_visual_opportunity_plan(timeline(), mismatch, defaults=DEFAULTS)
        fractional = timeline(); fractional["spans"][0]["actual_end_seconds"] = "4.5678"
        with self.assertRaisesRegex(VisualOpportunityError, "millisecond"):
            build_visual_opportunity_plan(fractional, directives(), defaults=DEFAULTS)
        leaky = directives(); leaky["directives"][0]["start_ms"] = 1
        with self.assertRaises(VisualOpportunityError):
            build_visual_opportunity_plan(timeline(), leaky, defaults=DEFAULTS)

    def test_opportunity_identity_is_deterministic_but_changes_for_revised_directives(self):
        first = build_visual_opportunity_plan(timeline(), directives(), defaults=DEFAULTS)
        second = build_visual_opportunity_plan(copy.deepcopy(timeline()), copy.deepcopy(directives()), defaults=copy.deepcopy(DEFAULTS))
        self.assertEqual(first["plan_id"], second["plan_id"])
        self.assertEqual(first["opportunities"][0]["opportunity_id"], second["opportunities"][0]["opportunity_id"])
        revised = directives(); revised["revision"] = 2
        changed = build_visual_opportunity_plan(timeline(), revised, defaults=DEFAULTS)
        self.assertNotEqual(first["plan_id"], changed["plan_id"])
        self.assertNotEqual(first["opportunities"][0]["opportunity_id"], changed["opportunities"][0]["opportunity_id"])


if __name__ == "__main__":
    unittest.main()
