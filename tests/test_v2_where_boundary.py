"""V2 WHERE boundary: output purity + storage tamper tests.

Proves that visual-opportunity-plan/1 opportunities contain only WHERE fields
and never leak WHAT (asset_family, plugin_id, proposal_id, candidate_id,
candidate, selected_plugin) or WHEN (suggested_placement, final_placement,
selected_placement, intrinsic_placement_hint, renderer) fields.
"""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.visual_opportunity import (
    VisualOpportunityError,
    build_visual_opportunity_plan,
)
from deeptalk_studio.visual_opportunity_storage import (
    VisualOpportunityStorageError,
    save_visual_opportunity_plan,
    load_visual_opportunity_plan,
)


def _timeline():
    result = {
        "artifact_version": "semantic-timeline/1",
        "timeline_id": "ST-boundary-01",
        "timing_provenance": "actual_aroll_alignment",
        "alignment_digest": "c" * 64,
        "transcript_digest": "d" * 64,
        "spans": [
            {"span_id": "S01", "actual_start_seconds": "1.000", "actual_end_seconds": "3.000", "summary": "Boundary safe span one.", "visual_eligibility": "safe", "reason": "safe_real_alignment"},
            {"span_id": "S02", "actual_start_seconds": "3.000", "actual_end_seconds": "5.000", "summary": "Boundary safe span two.", "visual_eligibility": "safe", "reason": "safe_real_alignment"},
        ],
    }
    result["timeline_digest"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return result


def _directives():
    return {
        "artifact_version": "visual-opportunity-directives/1",
        "directives_id": "VOD-boundary-01",
        "revision": 1,
        "semantic_timeline_digest": _timeline()["timeline_digest"],
        "reviewed_script_digest": "b" * 64,
        "directives": [
            {"directive_id": "d01", "span_id": "S01", "visual_purpose": "Illustrate concept one.", "why_opportunity": "Visual aid helps.", "semantic_context_selector": {"include_neighboring_spans": 1}, "factual_context_refs": [{"claim_id": "c1", "evidence_id": "e1"}]},
            {"directive_id": "d02", "span_id": "S02", "visual_purpose": "Illustrate concept two.", "why_opportunity": "Visual aid helps.", "semantic_context_selector": {"include_neighboring_spans": 0}, "factual_context_refs": []},
        ],
    }


_DEFAULTS = {"language": "zh-CN", "canvas": {"width": 1920, "height": 1080}, "target_duration_ms": 3000}

_WHERE_FIELDS = frozenset({
    "opportunity_id", "spoken_semantics", "visual_purpose", "a_roll_window",
    "target_duration_ms", "language", "canvas", "factual_context", "semantic_context",
})
_WHAT_FIELDS = frozenset({
    "asset_family", "plugin_id", "proposal_id", "candidate_id", "candidate", "selected_plugin",
})
_WHEN_FIELDS = frozenset({
    "suggested_placement", "final_placement", "selected_placement",
    "intrinsic_placement_hint", "renderer",
})


def _build_plan():
    return build_visual_opportunity_plan(_timeline(), _directives(), defaults=_DEFAULTS)


def _recompute_digest(plan):
    payload = dict(plan)
    payload.pop("plan_digest", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class WhereOutputPurityTests(unittest.TestCase):
    def test_opportunity_output_contains_only_where_fields(self):
        plan = _build_plan()
        self.assertEqual(len(plan["opportunities"]), 2)
        for opp in plan["opportunities"]:
            actual_fields = set(opp.keys())
            self.assertTrue(
                actual_fields.issubset(_WHERE_FIELDS),
                f"unexpected fields: {actual_fields - _WHERE_FIELDS}",
            )
            for required in ("opportunity_id", "spoken_semantics", "visual_purpose",
                             "a_roll_window", "target_duration_ms", "language",
                             "canvas", "factual_context"):
                self.assertIn(required, opp, f"missing required field: {required}")

    def test_opportunity_output_excludes_what_and_when_fields(self):
        plan = _build_plan()
        for opp in plan["opportunities"]:
            for field in _WHAT_FIELDS | _WHEN_FIELDS:
                self.assertNotIn(field, opp, f"opportunity leaked {field}")

    def test_plan_level_fields_exclude_what_and_when(self):
        plan = _build_plan()
        for field in _WHAT_FIELDS | _WHEN_FIELDS:
            self.assertNotIn(field, plan, f"plan leaked {field}")


class StorageTamperTests(unittest.TestCase):
    def test_storage_save_load_equivalence(self):
        plan = _build_plan()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = save_visual_opportunity_plan(plan, root)
            loaded = load_visual_opportunity_plan(path)
            self.assertEqual(loaded, plan)

    def test_storage_duplicate_save_fails(self):
        plan = _build_plan()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_visual_opportunity_plan(plan, root)
            with self.assertRaisesRegex(VisualOpportunityStorageError, "不会覆盖"):
                save_visual_opportunity_plan(plan, root)

    def test_storage_plan_digest_tamper_fails(self):
        plan = _build_plan()
        plan["plan_digest"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(VisualOpportunityStorageError):
                save_visual_opportunity_plan(plan, Path(tmp))

    def test_storage_rejects_opportunity_with_what_field(self):
        plan = _build_plan()
        plan["opportunities"][0]["asset_family"] = "illustration"
        plan["plan_digest"] = _recompute_digest(plan)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(VisualOpportunityStorageError):
                save_visual_opportunity_plan(plan, Path(tmp))

    def test_storage_rejects_opportunity_with_when_field(self):
        plan = _build_plan()
        plan["opportunities"][0]["final_placement"] = "overlay"
        plan["plan_digest"] = _recompute_digest(plan)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(VisualOpportunityStorageError):
                save_visual_opportunity_plan(plan, Path(tmp))

    def test_storage_rejects_duplicate_opportunity_id(self):
        plan = _build_plan()
        plan["opportunities"].append(copy.deepcopy(plan["opportunities"][0]))
        plan["plan_digest"] = _recompute_digest(plan)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(VisualOpportunityStorageError):
                save_visual_opportunity_plan(plan, Path(tmp))


if __name__ == "__main__":
    unittest.main()
