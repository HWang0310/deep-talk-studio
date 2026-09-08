"""V2 Phase C tests: Studio/Core Placement Planner (WHEN).

Covers the required core behaviours:
  1. no hint              -> candidate centred on the opportunity window
  2. hint                 -> candidate centred on the hint, full duration kept
  3. hint near a boundary -> whole window clamped inside, duration preserved
  4. duration > window    -> UNPLACEABLE, no fabricated final_placement
  5. malformed / outside hint -> fail closed
  6. non-READY candidate  -> never PLACED
  7. two candidates, one opportunity -> two different final placements
  8. input order changes  -> identical plan identity / placements / digest
  9. inputs are never mutated

Plus boundary purity: the plan contains no winner / ranking / overlap
resolution / NLE / auto-edit / plugin-selection fields, and never carries
candidate provenance, artifacts, QA, or asset_family.
"""
from __future__ import annotations

import copy
import json
import re
import unittest

from deeptalk_studio.placement_planner import (
    PLACEMENT_PLAN_VERSION,
    PlacementPlannerError,
    build_candidate_placement_plan,
)


def _opportunity(start_ms: int = 10000, end_ms: int = 20000) -> dict:
    return {
        "opportunity_id": "VO-test-01",
        "spoken_semantics": "Market share shifts.",
        "visual_purpose": "Illustrate the shift.",
        "a_roll_window": {"start_ms": start_ms, "end_ms": end_ms},
        "target_duration_ms": 3000,
        "language": "zh-CN",
        "canvas": {"width": 1920, "height": 1080},
        "factual_context": [],
    }


def _candidate(
    candidate_id: str = "cand-a",
    duration_ms: int = 4000,
    hint: dict | None = None,
    status: str = "READY",
    opportunity_id: str | None = None,
) -> dict:
    candidate = {
        "candidate_id": candidate_id,
        "asset_family": "MG",
        "candidate_status": status,
        "duration_ms": duration_ms,
        "qa": {"status": "PASSED"},
        "provenance": {"origin": "plugin-generated"},
        "artifacts": [{"role": "PRIMARY_MEDIA", "uri": "file:///tmp/a.mp4"}],
        "plugin_metadata": {"seed": 7},
    }
    if hint is not None:
        candidate["intrinsic_placement_hint"] = hint
    if opportunity_id is not None:
        candidate["opportunity_id"] = opportunity_id
    return candidate


def _placement_for(plan: dict, candidate_id: str) -> dict:
    for item in plan["placements"]:
        if item["candidate_id"] == candidate_id:
            return item
    raise AssertionError(f"missing placement for {candidate_id}")


_FORBIDDEN_TOP_LEVEL = frozenset({
    "winner", "winner_candidate_id", "selected_candidate", "selected_candidate_id",
    "ranking", "rank", "ranked_candidates", "suggested_review_order",
    "overlap_resolution", "resolved_overlap", "nle_project", "edit_decision",
    "auto_edit", "auto_insert", "plugin_selection", "selected_plugin",
    "final_cut", "render", "renderer",
})
_FORBIDDEN_PLACEMENT = frozenset({
    "winner", "selected", "selected_candidate", "ranking", "rank", "score",
    "overlap_resolution", "nle_project", "auto_edit", "plugin_selection",
    "provenance", "artifacts", "qa", "asset_family", "plugin_metadata",
    "suggested_review_order",
})


# ===========================================================================
# 1-3. placement rules
# ===========================================================================

class PlacementRuleTests(unittest.TestCase):
    def test_no_hint_places_candidate_at_opportunity_center(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000), [_candidate("cand-a", duration_ms=3000)]
        )
        entry = _placement_for(plan, "cand-a")
        self.assertEqual(entry["status"], "PLACED")
        self.assertEqual(entry["final_placement"], {"start_ms": 13500, "end_ms": 16500})
        self.assertEqual(entry["duration_ms"], 3000)
        self.assertFalse(entry["basis"]["intrinsic_hint_used"])
        self.assertEqual(entry["basis"]["center_source"], "opportunity_center")
        self.assertFalse(entry["basis"]["clamped"])

    def test_hint_center_used_with_full_duration_preserved(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000),
            [_candidate("cand-a", duration_ms=4000, hint={"start_ms": 11000, "end_ms": 15000})],
        )
        entry = _placement_for(plan, "cand-a")
        self.assertEqual(entry["final_placement"], {"start_ms": 11000, "end_ms": 15000})
        self.assertEqual(entry["duration_ms"], 4000)
        self.assertTrue(entry["basis"]["intrinsic_hint_used"])
        self.assertEqual(entry["basis"]["center_source"], "intrinsic_placement_hint")

    def test_hint_near_lower_boundary_clamps_without_changing_duration(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000),
            [_candidate("cand-a", duration_ms=4000, hint={"start_ms": 10000, "end_ms": 10500})],
        )
        entry = _placement_for(plan, "cand-a")
        self.assertEqual(entry["final_placement"], {"start_ms": 10000, "end_ms": 14000})
        self.assertTrue(entry["basis"]["clamped"])
        self.assertEqual(entry["duration_ms"], 4000)

    def test_hint_near_upper_boundary_clamps_without_changing_duration(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000),
            [_candidate("cand-a", duration_ms=4000, hint={"start_ms": 19000, "end_ms": 20000})],
        )
        entry = _placement_for(plan, "cand-a")
        self.assertEqual(entry["final_placement"], {"start_ms": 16000, "end_ms": 20000})
        self.assertTrue(entry["basis"]["clamped"])
        self.assertEqual(entry["duration_ms"], 4000)

    def test_exact_fit_candidate_fills_window(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000), [_candidate("cand-a", duration_ms=10000)]
        )
        self.assertEqual(
            _placement_for(plan, "cand-a")["final_placement"],
            {"start_ms": 10000, "end_ms": 20000},
        )


# ===========================================================================
# 4. UNPLACEABLE
# ===========================================================================

class UnplaceableTests(unittest.TestCase):
    def test_candidate_longer_than_opportunity_is_unplaceable(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000), [_candidate("cand-long", duration_ms=20001)]
        )
        entry = _placement_for(plan, "cand-long")
        self.assertEqual(entry["status"], "UNPLACEABLE")
        self.assertEqual(entry["reason"], "CANDIDATE_LONGER_THAN_OPPORTUNITY")
        self.assertEqual(entry["duration_ms"], 20001)
        self.assertNotIn("final_placement", entry)
        self.assertNotIn("basis", entry)

    def test_unplaceable_does_not_trim_candidate(self):
        # The planner must never shorten the candidate to make it fit.
        plan = build_candidate_placement_plan(
            _opportunity(10000, 11000), [_candidate("cand-long", duration_ms=11000)]
        )
        entry = _placement_for(plan, "cand-long")
        self.assertEqual(entry["status"], "UNPLACEABLE")
        self.assertEqual(entry["duration_ms"], 11000)


# ===========================================================================
# 5. malformed / outside hint fails closed
# ===========================================================================

class HintFailClosedTests(unittest.TestCase):
    def test_hint_outside_window_lower_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(10000, 20000),
                [_candidate(hint={"start_ms": 9000, "end_ms": 12000})],
            )

    def test_hint_outside_window_upper_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(10000, 20000),
                [_candidate(hint={"start_ms": 15000, "end_ms": 21000})],
            )

    def test_hint_start_not_before_end_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(10000, 20000),
                [_candidate(hint={"start_ms": 15000, "end_ms": 15000})],
            )

    def test_hint_not_integer_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(10000, 20000),
                [_candidate(hint={"start_ms": 12000.5, "end_ms": 15000})],
            )

    def test_hint_unknown_field_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(10000, 20000),
                [_candidate(hint={"start_ms": 12000, "end_ms": 15000, "confidence": 0.9})],
            )

    def test_hint_not_mapping_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(10000, 20000), [_candidate(hint=[12000, 15000])]
            )


# ===========================================================================
# 6. non-READY candidates are never PLACED
# ===========================================================================

class NonReadyRejectionTests(unittest.TestCase):
    def test_qa_rejected_rejected(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(), [_candidate(status="QA_REJECTED")]
            )

    def test_operation_failure_statuses_rejected(self):
        for status in ("FAILED", "BLOCKED", "UNAVAILABLE", "ABSTAIN"):
            with self.subTest(status=status):
                with self.assertRaises(PlacementPlannerError):
                    build_candidate_placement_plan(
                        _opportunity(), [_candidate(status=status)]
                    )

    def test_missing_duration_rejected(self):
        candidate = _candidate()
        candidate.pop("duration_ms")
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(_opportunity(), [candidate])

    def test_zero_duration_rejected(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(), [_candidate(duration_ms=0)]
            )


# ===========================================================================
# 7-8. multi-candidate + determinism
# ===========================================================================

class DeterminismTests(unittest.TestCase):
    def test_two_candidates_same_opportunity_get_different_placements(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000),
            [
                _candidate("cand-a", duration_ms=4000, hint={"start_ms": 11000, "end_ms": 15000}),
                _candidate("cand-b", duration_ms=7000, hint={"start_ms": 13000, "end_ms": 19000}),
            ],
        )
        placement_a = _placement_for(plan, "cand-a")["final_placement"]
        placement_b = _placement_for(plan, "cand-b")["final_placement"]
        self.assertEqual(placement_a, {"start_ms": 11000, "end_ms": 15000})
        self.assertEqual(placement_b, {"start_ms": 12500, "end_ms": 19500})
        self.assertNotEqual(placement_a, placement_b)

    def test_plan_id_and_digest_are_order_independent(self):
        first = _candidate("cand-a", duration_ms=4000, hint={"start_ms": 11000, "end_ms": 15000})
        second = _candidate("cand-b", duration_ms=7000, hint={"start_ms": 13000, "end_ms": 19000})
        forward = build_candidate_placement_plan(_opportunity(), [first, second])
        reverse = build_candidate_placement_plan(_opportunity(), [second, first])
        self.assertEqual(forward["placement_plan_id"], reverse["placement_plan_id"])
        self.assertEqual(forward["placement_plan_digest"], reverse["placement_plan_digest"])
        self.assertEqual(forward["placements"], reverse["placements"])

    def test_repeated_build_is_identical(self):
        payload = [_candidate("cand-a", duration_ms=4000)]
        first = build_candidate_placement_plan(_opportunity(), payload)
        second = build_candidate_placement_plan(_opportunity(), payload)
        self.assertEqual(first, second)

    def test_plan_id_is_deterministic_shape(self):
        plan = build_candidate_placement_plan(_opportunity(), [_candidate()])
        self.assertRegex(plan["placement_plan_id"], r"^CPP-[0-9a-f]{24}$")

    def test_different_windows_produce_different_plan_ids(self):
        narrow = build_candidate_placement_plan(
            _opportunity(10000, 20000), [_candidate(duration_ms=2000)]
        )
        wide = build_candidate_placement_plan(
            _opportunity(10000, 30000), [_candidate(duration_ms=2000)]
        )
        self.assertNotEqual(narrow["placement_plan_id"], wide["placement_plan_id"])


# ===========================================================================
# 9. input immutability
# ===========================================================================

class ImmutabilityTests(unittest.TestCase):
    def test_inputs_are_not_mutated(self):
        opportunity = _opportunity()
        candidates = [
            _candidate("cand-a", duration_ms=4000, hint={"start_ms": 11000, "end_ms": 15000}),
            _candidate("cand-b", duration_ms=2000),
        ]
        snapshot_opportunity = copy.deepcopy(opportunity)
        snapshot_candidates = copy.deepcopy(candidates)
        build_candidate_placement_plan(opportunity, candidates)
        self.assertEqual(opportunity, snapshot_opportunity)
        self.assertEqual(candidates, snapshot_candidates)

    def test_plan_holds_no_reference_to_candidate_objects(self):
        candidate = _candidate("cand-a", duration_ms=4000)
        plan = build_candidate_placement_plan(_opportunity(), [candidate])
        candidate["duration_ms"] = 9999
        candidate["candidate_id"] = "mutated"
        self.assertEqual(plan["placements"][0]["candidate_id"], "cand-a")
        self.assertEqual(plan["placements"][0]["duration_ms"], 4000)


# ===========================================================================
# Boundary purity
# ===========================================================================

class BoundaryPurityTests(unittest.TestCase):
    def test_artifact_version_and_top_level_shape(self):
        plan = build_candidate_placement_plan(_opportunity(), [_candidate()])
        self.assertEqual(plan["artifact_version"], PLACEMENT_PLAN_VERSION)
        self.assertEqual(
            set(plan),
            {"artifact_version", "placement_plan_id", "opportunity_id",
             "a_roll_window", "placements", "placement_plan_digest"},
        )

    def test_no_winner_ranking_or_edit_fields(self):
        plan = build_candidate_placement_plan(
            _opportunity(),
            [_candidate("cand-a", duration_ms=4000), _candidate("cand-b", duration_ms=5000)],
        )
        self.assertEqual(set(plan) & _FORBIDDEN_TOP_LEVEL, set())
        for entry in plan["placements"]:
            self.assertEqual(set(entry) & _FORBIDDEN_PLACEMENT, set())

    def test_overlapping_recommendations_are_allowed(self):
        # Two candidates may legitimately receive identical windows; Phase C
        # never resolves overlap and never drops a candidate.
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000),
            [
                _candidate("cand-a", duration_ms=4000, hint={"start_ms": 12000, "end_ms": 16000}),
                _candidate("cand-b", duration_ms=4000, hint={"start_ms": 12000, "end_ms": 16000}),
            ],
        )
        self.assertEqual(len(plan["placements"]), 2)
        self.assertEqual(
            _placement_for(plan, "cand-a")["final_placement"],
            _placement_for(plan, "cand-b")["final_placement"],
        )

    def test_all_placements_stay_inside_opportunity_window(self):
        plan = build_candidate_placement_plan(
            _opportunity(10000, 20000),
            [
                _candidate("cand-a", duration_ms=1000),
                _candidate("cand-b", duration_ms=9000, hint={"start_ms": 10000, "end_ms": 10100}),
                _candidate("cand-c", duration_ms=20000),
            ],
        )
        for entry in plan["placements"]:
            if entry["status"] != "PLACED":
                continue
            placement = entry["final_placement"]
            self.assertGreaterEqual(placement["start_ms"], 10000)
            self.assertLessEqual(placement["end_ms"], 20000)
            self.assertLess(placement["start_ms"], placement["end_ms"])
            self.assertEqual(
                placement["end_ms"] - placement["start_ms"], entry["duration_ms"]
            )

    def test_plan_is_json_serialisable_and_stable(self):
        plan = build_candidate_placement_plan(_opportunity(), [_candidate()])
        encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(json.loads(encoded), plan)
        self.assertNotIn("winner", encoded)


# ===========================================================================
# Validation / lineage
# ===========================================================================

class InputValidationTests(unittest.TestCase):
    def test_opportunity_lineage_mismatch_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(), [_candidate(opportunity_id="VO-other")]
            )

    def test_matching_opportunity_lineage_accepted(self):
        plan = build_candidate_placement_plan(
            _opportunity(), [_candidate(opportunity_id="VO-test-01")]
        )
        self.assertEqual(plan["opportunity_id"], "VO-test-01")

    def test_duplicate_candidate_id_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(),
                [_candidate("cand-a", duration_ms=1000), _candidate("cand-a", duration_ms=2000)],
            )

    def test_invalid_opportunity_window_fails_closed(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(
                _opportunity(20000, 10000), [_candidate()]
            )

    def test_candidates_must_be_a_list(self):
        with self.assertRaises(PlacementPlannerError):
            build_candidate_placement_plan(_opportunity(), _candidate())

    def test_empty_candidate_list_is_allowed(self):
        plan = build_candidate_placement_plan(_opportunity(), [])
        self.assertEqual(plan["placements"], [])
        self.assertRegex(plan["placement_plan_id"], r"^CPP-[0-9a-f]{24}$")


if __name__ == "__main__":
    unittest.main()
