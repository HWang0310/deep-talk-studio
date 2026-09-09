"""V2 Phase C — Studio/Core Placement Planner (WHEN).

This module answers exactly one question:

    For one already-generated concrete Candidate, from which millisecond of the
    A-roll to which millisecond should it be *recommended* to appear?

It deliberately separates three different kinds of time:

1. ``a_roll_window``            — WHERE.  The Visual Opportunity's semantic
                                  opportunity window.  Owned by Studio/Core.
2. ``intrinsic_placement_hint`` — WHAT.  A plugin-owned timing *hint* carried on
                                  the Candidate (read-only V1
                                  ``suggested_placement`` -> V2 hint mapping).
3. ``final_placement``          — WHEN.  The Studio/Core Placement Planner's
                                  recommended insertion window for one concrete
                                  Candidate.  Produced only here.

``final_placement`` is a machine-readable **recommendation**, never the
creator's final edit.  This module never trims, retimes, splices, renders,
auto-inserts, or publishes anything.

Identity authority (accepted V2 architecture §5.3):
  - ``placement_plan_id`` is **Studio/Core-created** and deterministic.
  - ``opportunity_id`` / ``candidate_id`` creator semantics are unchanged.
    Core does not re-create or re-assign them.

Non-goals enforced here (raise or omit, never silently do):
  - no winner selection, ranking, or ``suggested_review_order`` semantics;
  - no overlap resolution between Candidates or between Opportunities
    (overlapping recommendations are explicitly allowed);
  - no auto-edit, NLE project, trimming, stretching, or speed change — a
    Candidate's ``duration_ms`` is always preserved exactly;
  - no LLM, no randomness, no clock, no filesystem state.  Same inputs always
    produce the same ``placement_plan_id``, ``placements`` and
    ``placement_plan_digest``.

Placements are emitted in canonical ascending ``candidate_id`` order.  That
order exists purely so the plan identity is independent of input list order;
it is **not** a review order, ranking, or preference signal.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

PLACEMENT_PLAN_VERSION = "candidate-placement-plan/1"

PLACEMENT_STATUSES = frozenset({"PLACED", "UNPLACEABLE"})
UNPLACEABLE_REASONS = frozenset({"CANDIDATE_LONGER_THAN_OPPORTUNITY"})
READY_CANDIDATE_STATUS = "READY"

_CENTER_SOURCE_HINT = "intrinsic_placement_hint"
_CENTER_SOURCE_OPPORTUNITY = "opportunity_center"


class PlacementPlannerError(ValueError):
    """A deterministic, fail-closed Placement Planner error."""


def build_candidate_placement_plan(
    opportunity: Mapping[str, Any],
    candidates: Any,
) -> dict[str, Any]:
    """Build a deterministic ``candidate-placement-plan/1`` for one Opportunity.

    ``candidates`` is a sequence of concrete Candidates.  Each Candidate must
    carry ``candidate_id``, ``candidate_status`` and ``duration_ms``; it may
    carry a plugin-owned ``intrinsic_placement_hint``.  Anything malformed or
    non-READY fails closed — this planner never fabricates a placement.
    """
    window = _validate_opportunity(opportunity)
    opportunity_id = str(opportunity["opportunity_id"])
    normalized = _validate_candidates(candidates, opportunity_id, window)

    placements = []
    for candidate in normalized:
        placements.append(_plan_one(candidate, window))
    placements.sort(key=lambda item: item["candidate_id"])

    identity = {
        "artifact_version": PLACEMENT_PLAN_VERSION,
        "opportunity_id": opportunity_id,
        "a_roll_window": dict(window),
        "placements": placements,
    }
    plan = {
        "artifact_version": PLACEMENT_PLAN_VERSION,
        "placement_plan_id": "CPP-" + _digest(identity)[:24],
        "opportunity_id": opportunity_id,
        "a_roll_window": dict(window),
        "placements": placements,
    }
    plan["placement_plan_digest"] = _digest(plan)
    return plan


# ===========================================================================
# Placement rules
# ===========================================================================

def _plan_one(candidate: Mapping[str, Any], window: Mapping[str, int]) -> dict[str, Any]:
    duration = int(candidate["duration_ms"])
    window_start, window_end = int(window["start_ms"]), int(window["end_ms"])
    window_duration = window_end - window_start

    if duration > window_duration:
        # Never trim / compress / retime to make it fit.  Fail honestly.
        return {
            "candidate_id": candidate["candidate_id"],
            "status": "UNPLACEABLE",
            "reason": "CANDIDATE_LONGER_THAN_OPPORTUNITY",
            "duration_ms": duration,
        }

    hint = candidate.get("intrinsic_placement_hint")
    if hint is None:
        hint_used = False
        center_source = _CENTER_SOURCE_OPPORTUNITY
        desired_start = (window_start + window_end - duration) // 2
    else:
        hint_used = True
        center_source = _CENTER_SOURCE_HINT
        # The hint's midpoint is a *preference*, not a command.  The Candidate
        # keeps its full duration; the window is centred on the hint midpoint.
        desired_start = (int(hint["start_ms"]) + int(hint["end_ms"]) - duration) // 2

    clamped = False
    if desired_start < window_start:
        desired_start, clamped = window_start, True
    elif desired_start + duration > window_end:
        desired_start, clamped = window_end - duration, True

    final_placement = {"start_ms": desired_start, "end_ms": desired_start + duration}
    _assert_within(final_placement, window, duration)
    return {
        "candidate_id": candidate["candidate_id"],
        "status": "PLACED",
        "final_placement": final_placement,
        "duration_ms": duration,
        "basis": {
            "intrinsic_hint_used": hint_used,
            "center_source": center_source,
            "clamped": clamped,
        },
    }


def _assert_within(
    placement: Mapping[str, int], window: Mapping[str, int], duration: int
) -> None:
    start, end = int(placement["start_ms"]), int(placement["end_ms"])
    if start < int(window["start_ms"]) or end > int(window["end_ms"]):
        raise PlacementPlannerError("final_placement 必须位于 a_roll_window 内")
    if start >= end:
        raise PlacementPlannerError("final_placement 必须满足 start_ms < end_ms")
    if end - start != duration:
        raise PlacementPlannerError("final_placement 必须精确保留 Candidate duration_ms")


# ===========================================================================
# Validation
# ===========================================================================

def _validate_opportunity(value: Any) -> dict[str, int]:
    data = _mapping(value, "opportunity")
    _identifier(data.get("opportunity_id"), "opportunity.opportunity_id")
    window = _mapping(data.get("a_roll_window"), "opportunity.a_roll_window")
    _only_fields(window, {"start_ms", "end_ms"}, "opportunity.a_roll_window")
    start = _nonnegative_int(window.get("start_ms"), "a_roll_window.start_ms")
    end = _nonnegative_int(window.get("end_ms"), "a_roll_window.end_ms")
    if start >= end:
        raise PlacementPlannerError("a_roll_window 必须满足 start_ms < end_ms")
    return {"start_ms": start, "end_ms": end}


def _validate_candidates(
    value: Any, opportunity_id: str, window: Mapping[str, int]
) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        raise PlacementPlannerError("candidates 必须是列表")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        label = f"candidates[{index}]"
        candidate = _mapping(raw, label)
        candidate_id = _identifier(candidate.get("candidate_id"), f"{label}.candidate_id")
        if candidate_id in seen:
            raise PlacementPlannerError(f"candidate_id 重复：{candidate_id}")
        seen.add(candidate_id)

        status = candidate.get("candidate_status")
        if not isinstance(status, str) or not status.strip():
            raise PlacementPlannerError(f"{label}.candidate_status 必须是非空文本")
        if status != READY_CANDIDATE_STATUS:
            # FAILED / BLOCKED / UNAVAILABLE / ABSTAIN / QA_REJECTED must never
            # receive a PLACED recommendation.  Fail closed instead.
            raise PlacementPlannerError(
                f"{label} 的 candidate_status 为 {status}：非 READY Candidate 不得产生 placement"
            )

        # Opportunity lineage: never plan an Opportunity A candidate into B.
        if "opportunity_id" in candidate:
            _identifier(candidate["opportunity_id"], f"{label}.opportunity_id")
            if candidate["opportunity_id"] != opportunity_id:
                raise PlacementPlannerError(
                    f"{label}.opportunity_id 与传入 Opportunity 不一致"
                )

        duration = _positive_int(candidate.get("duration_ms"), f"{label}.duration_ms")

        hint = None
        if "intrinsic_placement_hint" in candidate:
            hint = _validate_hint(candidate["intrinsic_placement_hint"], label)
            # A plugin hint is never trusted blindly: outside the opportunity
            # window is fail-closed, not silently clamped into a fake placement.
            _hint_within_window(hint, window)

        entry: dict[str, Any] = {
            "candidate_id": candidate_id,
            "candidate_status": status,
            "duration_ms": duration,
        }
        if hint is not None:
            entry["intrinsic_placement_hint"] = hint
        normalized.append(entry)
    return normalized


def _validate_hint(value: Any, label: str) -> dict[str, int]:
    """Validate the plugin-owned hint.  Malformed or out-of-window -> fail closed."""
    hint = _mapping(value, f"{label}.intrinsic_placement_hint")
    _only_fields(hint, {"start_ms", "end_ms"}, f"{label}.intrinsic_placement_hint")
    start = _nonnegative_int(hint.get("start_ms"), "intrinsic_placement_hint.start_ms")
    end = _nonnegative_int(hint.get("end_ms"), "intrinsic_placement_hint.end_ms")
    if start >= end:
        raise PlacementPlannerError(
            "intrinsic_placement_hint 必须满足 start_ms < end_ms"
        )
    return {"start_ms": start, "end_ms": end}


def _hint_within_window(hint: Mapping[str, int], window: Mapping[str, int]) -> None:
    if int(hint["start_ms"]) < int(window["start_ms"]):
        raise PlacementPlannerError("intrinsic_placement_hint 越出 a_roll_window 下界")
    if int(hint["end_ms"]) > int(window["end_ms"]):
        raise PlacementPlannerError("intrinsic_placement_hint 越出 a_roll_window 上界")


# ===========================================================================
# Helpers
# ===========================================================================

def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PlacementPlannerError(f"{field} 必须是 JSON 对象")
    return value


def _only_fields(data: Mapping[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(data).difference(allowed))
    if unknown:
        raise PlacementPlannerError(f"{field} 包含未知字段：{', '.join(unknown)}")


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlacementPlannerError(f"{field} 必须是非空文本")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PlacementPlannerError(f"{field} 必须是非负整数")
    return value


def _positive_int(value: Any, field: str) -> int:
    value = _nonnegative_int(value, field)
    if value <= 0:
        raise PlacementPlannerError(f"{field} 必须是正整数")
    return value


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
