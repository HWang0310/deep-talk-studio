"""Alignment-bound visual decisions for the Visual Asset Engine MVP."""
import hashlib
import json


class VisualDirectorError(ValueError):
    pass


DECISIONS = {"KEEP_A_ROLL", "REAL_MATERIAL", "MG_MOTION", "ADVANCED_MOTION"}


def _digest(value):
    copy = dict(value); copy.pop("plan_digest", None)
    return hashlib.sha256(json.dumps(copy, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_visual_director_plan(roots, proposals, *, plan_id, created_at, revision=1, previous_revision=0):
    """Build a deterministic plan. Proposal clocks are forbidden by contract."""
    if len(str(roots.get("alignment_digest", ""))) != 64:
        raise VisualDirectorError("Visual Director 缺少通过 Gate 的 Alignment binding")
    opportunities = []
    seen = set()
    for raw in proposals:
        if {"start_seconds", "end_seconds", "duration_seconds"} & set(raw):
            raise VisualDirectorError("Visual Director 不得自行创建或改写 A-roll 时间")
        required = {"opportunity_id", "cue_id", "visual_intent", "why_visual"}
        if not required <= set(raw) or raw["opportunity_id"] in seen:
            raise VisualDirectorError("Visual Director opportunity 不完整或重复")
        clock = roots.get("ranges", {}).get(raw["cue_id"])
        if not clock or len(clock) != 2:
            raise VisualDirectorError("Visual Director 只能使用已通过 Alignment 的局部时间")
        decision = raw.get("decision", "KEEP_A_ROLL")
        if decision not in DECISIONS:
            raise VisualDirectorError("Visual Director decision 无效")
        if decision != "KEEP_A_ROLL" and len(str(raw["why_visual"]).strip()) < 6:
            raise VisualDirectorError("升级视觉必须说明为什么值得覆盖真人")
        start, end = map(str, clock)
        item = {"opportunity_id": raw["opportunity_id"], "cue_id": raw["cue_id"], "source_time_range": {"start_seconds": start, "end_seconds": end}, "visual_intent": raw["visual_intent"], "why_visual": raw["why_visual"], "decision": decision, "importance": raw.get("importance", "supporting"), "review_requirement": "advanced_spec_review" if decision == "ADVANCED_MOTION" else ("plan_review" if decision != "KEEP_A_ROLL" else "not_needed"), "risk_flags": list(raw.get("risk_flags", [])), "alignment_digest": roots["alignment_digest"], "status": "keep" if decision == "KEEP_A_ROLL" else "proposed"}
        opportunities.append(item); seen.add(raw["opportunity_id"])
    data = {"artifact_version": "visual-director-plan/1", "plan_id": str(plan_id), "revision": int(revision), "previous_revision": int(previous_revision), "created_at": str(created_at), "alignment_digest": roots["alignment_digest"], "opportunities": opportunities}
    data["plan_digest"] = _digest(data)
    return data
