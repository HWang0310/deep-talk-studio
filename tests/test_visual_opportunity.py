import copy
import hashlib
import json
import unittest
from decimal import Decimal

from deeptalk_studio.visual_opportunity import (
    VisualOpportunityError,
    build_visual_opportunity_plan,
)


def timeline():
    result = {
        "artifact_version": "semantic-timeline/1",
        "timeline_id": "ST-synthetic-01",
        "timing_provenance": "actual_aroll_alignment",
        "alignment_digest": "c" * 64,
        "transcript_digest": "d" * 64,
        "spans": [
            {"span_id": "ST001", "actual_start_seconds": "1.234", "actual_end_seconds": "4.567", "summary": "Synthetic safe semantics.", "visual_eligibility": "safe", "reason": "safe_real_alignment"},
            {"span_id": "ST002", "actual_start_seconds": "4.567", "actual_end_seconds": "7.000", "summary": "Conflict semantics.", "visual_eligibility": "keep_only", "reason": "FACT_CONFLICT"},
            {"span_id": "ST003", "actual_start_seconds": "7.000", "actual_end_seconds": "9.000", "summary": "Safe base layer semantics.", "visual_eligibility": "safe", "reason": "safe_real_alignment"},
        ],
    }
    result["timeline_digest"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return result


def directives():
    return {
        "artifact_version": "visual-opportunity-directives/1", "directives_id": "VOD-synthetic-01", "revision": 1,
        "semantic_timeline_digest": timeline()["timeline_digest"], "reviewed_script_digest": "b" * 64,
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
        fractional = timeline(); fractional["spans"][0]["actual_end_seconds"] = "4.5678"; payload = dict(fractional); payload.pop("timeline_digest"); fractional["timeline_digest"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        fractional_directives = directives(); fractional_directives["semantic_timeline_digest"] = fractional["timeline_digest"]
        with self.assertRaisesRegex(VisualOpportunityError, "millisecond"):
            build_visual_opportunity_plan(fractional, fractional_directives, defaults=DEFAULTS)
        leaky = directives(); leaky["directives"][0]["start_ms"] = 1
        with self.assertRaises(VisualOpportunityError):
            build_visual_opportunity_plan(timeline(), leaky, defaults=DEFAULTS)

    def test_rejects_tampered_or_incomplete_semantic_timeline_lineage(self):
        for field, value in (("actual_start_seconds", "1.000"), ("summary", "tampered")):
            changed = timeline(); changed["spans"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(VisualOpportunityError, "timeline_digest"):
                build_visual_opportunity_plan(changed, directives(), defaults=DEFAULTS)
        for field in ("alignment_digest", "transcript_digest"):
            missing = timeline(); missing[field] = ""
            with self.subTest(field=field), self.assertRaisesRegex(VisualOpportunityError, field):
                build_visual_opportunity_plan(missing, directives(), defaults=DEFAULTS)

    def test_opportunity_identity_is_deterministic_but_changes_for_revised_directives(self):
        first = build_visual_opportunity_plan(timeline(), directives(), defaults=DEFAULTS)
        second = build_visual_opportunity_plan(copy.deepcopy(timeline()), copy.deepcopy(directives()), defaults=copy.deepcopy(DEFAULTS))
        self.assertEqual(first["plan_id"], second["plan_id"])
        self.assertEqual(first["alignment_digest"], "c" * 64)
        self.assertEqual(first["transcript_digest"], "d" * 64)
        self.assertEqual(first["opportunities"][0]["opportunity_id"], second["opportunities"][0]["opportunity_id"])
        revised = directives(); revised["revision"] = 2
        changed = build_visual_opportunity_plan(timeline(), revised, defaults=DEFAULTS)
        self.assertNotEqual(first["plan_id"], changed["plan_id"])
        self.assertNotEqual(first["opportunities"][0]["opportunity_id"], changed["opportunities"][0]["opportunity_id"])

    def test_orphan_directive_span_not_in_timeline_raises(self):
        """Gap 1 RED: directive whose span_id is not in the Semantic Timeline must raise."""
        orphan = directives()
        orphan["directives"][0]["span_id"] = "ST_NONEXIST"
        with self.assertRaisesRegex(VisualOpportunityError, r"不在"):
            build_visual_opportunity_plan(timeline(), orphan, defaults=DEFAULTS)

    def test_directive_for_non_safe_span_raises(self):
        """Gap 2 RED: directive pointing to a non-safe span must raise."""
        non_safe = directives()
        non_safe["directives"][0]["span_id"] = "ST002"
        with self.assertRaisesRegex(VisualOpportunityError, r"safe"):
            build_visual_opportunity_plan(timeline(), non_safe, defaults=DEFAULTS)

    def test_a_roll_window_exactly_projected_for_multiple_spans(self):
        """Characterization GREEN: a_roll_window is exact ms projection of actual_*_seconds."""
        custom = {
            "artifact_version": "semantic-timeline/1",
            "timeline_id": "ST-timing-01",
            "timing_provenance": "actual_aroll_alignment",
            "alignment_digest": "e" * 64,
            "transcript_digest": "f" * 64,
            "spans": [
                {"span_id": "T01", "actual_start_seconds": "0.000", "actual_end_seconds": "2.500", "summary": "First segment.", "visual_eligibility": "safe", "reason": "safe"},
                {"span_id": "T02", "actual_start_seconds": "2.500", "actual_end_seconds": "5.000", "summary": "Second segment.", "visual_eligibility": "safe", "reason": "safe"},
                {"span_id": "T03", "actual_start_seconds": "5.000", "actual_end_seconds": "7.500", "summary": "Conflict segment.", "visual_eligibility": "keep_only", "reason": "FACT_CONFLICT"},
                {"span_id": "T04", "actual_start_seconds": "7.500", "actual_end_seconds": "10.000", "summary": "Fourth segment.", "visual_eligibility": "safe", "reason": "safe"},
            ],
        }
        custom["timeline_digest"] = hashlib.sha256(json.dumps(custom, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        custom_directives = {
            "artifact_version": "visual-opportunity-directives/1",
            "directives_id": "VOD-timing-01",
            "revision": 1,
            "semantic_timeline_digest": custom["timeline_digest"],
            "reviewed_script_digest": "a" * 64,
            "directives": [
                {"directive_id": "d01", "span_id": "T01", "visual_purpose": "Show first.", "why_opportunity": "Important.", "semantic_context_selector": {"include_neighboring_spans": 0}, "factual_context_refs": []},
                {"directive_id": "d02", "span_id": "T02", "visual_purpose": "Show second.", "why_opportunity": "Important.", "semantic_context_selector": {"include_neighboring_spans": 0}, "factual_context_refs": []},
                {"directive_id": "d04", "span_id": "T04", "visual_purpose": "Show fourth.", "why_opportunity": "Important.", "semantic_context_selector": {"include_neighboring_spans": 0}, "factual_context_refs": []},
            ],
        }
        plan = build_visual_opportunity_plan(custom, custom_directives, defaults=DEFAULTS)
        self.assertEqual(len(plan["opportunities"]), 3)
        expected_windows = [
            {"start_ms": 0, "end_ms": 2500},
            {"start_ms": 2500, "end_ms": 5000},
            {"start_ms": 7500, "end_ms": 10000},
        ]
        for i, expected in enumerate(expected_windows):
            self.assertEqual(plan["opportunities"][i]["a_roll_window"], expected, f"opportunity {i}")
        self.assertEqual(plan["span_audit"][2], {"span_id": "T03", "status": "NO_OPPORTUNITY", "reason": "fact_conflict"})


if __name__ == "__main__":
    unittest.main()
