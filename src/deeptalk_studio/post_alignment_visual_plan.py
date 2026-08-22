"""Safe, alignment-derived visual opportunity planning for a real episode."""

import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from typing import Mapping, Sequence


class PostAlignmentVisualPlanError(ValueError):
    pass


MAPPED_OPERATIONS = {"primary_match", "numeric_match", "substitution"}
VISUAL_KINDS = {"a_roll", "real_material", "original_motion", "hybrid"}


def _digest(value: Mapping) -> str:
    payload = deepcopy(dict(value))
    payload.pop("plan_digest", None)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _script_digest(script: Mapping) -> str:
    return hashlib.sha256(
        json.dumps(dict(script), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _tail_policy(alignment: Mapping) -> dict:
    tail = next((gap for gap in alignment.get("gaps", []) if gap.get("gap_type") == "trailing_ad_lib_transcript_span"), None)
    if tail is None:
        return {"status": "none", "start_seconds": "", "end_seconds": ""}
    return {"status": "aroll", "start_seconds": str(tail.get("actual_start_seconds", "")), "end_seconds": str(tail.get("actual_end_seconds", ""))}


def _beat_audits(script: Mapping, alignment: Mapping, preference: Mapping) -> list:
    timeline = {item["beat_id"]: item for item in alignment.get("beat_timeline", [])}
    audits = []
    for beat in script.get("beats", []):
        record = timeline.get(beat.get("beat_id"))
        if record is None:
            raise PostAlignmentVisualPlanError("Visual Plan 缺少 Beat Alignment")
        status = record.get("alignment_status")
        rationale = "保留真人承接观点、情绪或无法安全投影的口播。"
        if status == "needs_review":
            rationale = "该 Beat 存在真实对齐不确定性；仅独立安全 span 可进入辅助画面。"
        elif beat.get("beat_id") == "B018":
            rationale = "结论与 CTA 默认保留真人；Script 外尾段始终保留真人。"
        audits.append({
            "beat_id": beat["beat_id"], "actual_start_seconds": str(record.get("actual_start_seconds", "")),
            "actual_end_seconds": str(record.get("actual_end_seconds", "")), "alignment_status": status,
            "confidence": record.get("confidence", "none"), "semantic_purpose": "待由已审核 Script 视觉规划解释",
            "a_roll_rationale": rationale, "existing_assets": [], "missing_assets": [],
            "preference_effect": dict(preference["resolved_preference"]),
        })
    return audits


def _project(opportunity: Mapping, alignment: Mapping, transcript: Mapping) -> dict:
    output = deepcopy(dict(opportunity))
    units = [
        item for item in alignment.get("global_mapping", {}).get("script_units", [])
        if int(item.get("script_char_start", -1)) >= int(opportunity["semantic_char_start"])
        and int(item.get("script_char_end", -1)) <= int(opportunity["semantic_char_end"])
    ]
    output.update({
        "mapped_transcript_unit_ids": [], "actual_in_seconds": "", "actual_out_seconds": "",
        "duration_seconds": "", "confidence": "none", "timing_status": "unplaced",
        "placement_status": "unplaced", "timing_reason": "semantic_span_unmatched",
    })
    if not units:
        return output
    indices = [int(item.get("transcript_token_index", -1)) for item in units]
    if alignment.get("global_mapping", {}).get("ambiguity_code") != "none" or any(item.get("operation") not in MAPPED_OPERATIONS for item in units):
        return output
    if indices != sorted(indices) or len(set(indices)) != len(indices) or min(indices) < 0:
        output["timing_reason"] = "semantic_span_ambiguous"
        return output
    by_id = {unit["unit_id"]: unit for unit in transcript.get("timed_units", [])}
    mapped_ids = list(dict.fromkeys(str(item.get("transcript_unit_id", "")) for item in units if item.get("transcript_unit_id")))
    mapped = [by_id[item] for item in mapped_ids if item in by_id]
    if transcript.get("timestamp_granularity") not in {"token", "word"} or not mapped or any(unit.get("boundary_risk_ids") for unit in mapped):
        output["timing_reason"] = "timestamp_or_boundary_risk"
        return output
    start = Decimal(str(mapped[0]["media_start_seconds"])); end = Decimal(str(mapped[-1]["media_end_seconds"]))
    if start < 0 or end <= start:
        output["timing_reason"] = "invalid_mapped_time"
        return output
    output.update({
        "mapped_transcript_unit_ids": mapped_ids, "actual_in_seconds": str(start), "actual_out_seconds": str(end),
        "duration_seconds": str(end - start), "confidence": "high", "timing_status": "ready",
        "placement_status": "ready", "timing_reason": "global_monotonic_projection",
    })
    return output


def _coverage(audits: Sequence[Mapping], opportunities: Sequence[Mapping], preference: Mapping) -> dict:
    ready = [item for item in opportunities if item["placement_status"] == "ready"]
    kinds = {item["visual_kind"] for item in opportunities}
    def status(kind: str, pref: str) -> str:
        if kind in kinds:
            return "pass"
        return "warning" if pref == "high" else "pass"
    return {
        "visual_coverage_status": "pass" if audits and opportunities else "blocked",
        "real_material_coverage_status": status("real_material", preference["resolved_preference"]["real_material_preference"]),
        "motion_coverage_status": status("original_motion", preference["resolved_preference"]["motion_preference"]),
        "audited_beat_count": len(audits), "opportunity_count": len(opportunities),
        "ready_opportunity_count": len(ready), "unplaced_opportunity_count": len(opportunities) - len(ready),
        "decorative_opportunity_count": sum(1 for item in opportunities if item["visual_role"] == "transition"),
    }


def build_post_alignment_visual_plan(
    script: Mapping,
    transcript: Mapping,
    alignment: Mapping,
    preference: Mapping,
    opportunities: Sequence[Mapping],
    *,
    plan_id: str,
    created_at: str,
    revision: int = 1,
    previous_revision: int = 0,
) -> dict:
    if alignment.get("artifact_version") not in {None, "script-alignment/2"}:
        raise PostAlignmentVisualPlanError("Post-Alignment Visual Plan 只接受 script-alignment/2")
    if not preference.get("preference_digest") or set(preference.get("resolved_preference", {})) != {
        "overall_visual_density", "real_material_preference", "motion_preference", "a_roll_preference",
    }:
        raise PostAlignmentVisualPlanError("Episode Visual Preference binding 无效")
    beat_ids = {beat["beat_id"] for beat in script.get("beats", [])}
    seen = set(); projected = []
    for raw in opportunities:
        required = {"opportunity_id", "beat_id", "semantic_char_start", "semantic_char_end", "visual_kind", "visual_role", "semantic_target", "source_binding"}
        if set(raw) != required or raw["opportunity_id"] in seen or raw["beat_id"] not in beat_ids or raw["visual_kind"] not in VISUAL_KINDS:
            raise PostAlignmentVisualPlanError("Visual Opportunity 身份或 Beat binding 无效")
        if int(raw["semantic_char_end"]) <= int(raw["semantic_char_start"]):
            raise PostAlignmentVisualPlanError("Visual Opportunity semantic span 无效")
        seen.add(raw["opportunity_id"]); projected.append(_project(raw, alignment, transcript))
    audits = _beat_audits(script, alignment, preference)
    data = {
        "artifact_version": "post-alignment-visual-plan/1", "plan_id": str(plan_id), "revision": int(revision),
        "previous_revision": int(previous_revision), "created_at": str(created_at),
        "script_id": str(script.get("script_id", "")), "script_revision": int(script.get("revision", 0)),
        "script_digest": _script_digest(script), "transcript_digest": str(alignment.get("transcript_digest", "")),
        "alignment_id": str(alignment.get("alignment_id", "")), "alignment_digest": str(alignment.get("artifact_digest", "")),
        "episode_visual_preference_digest": str(preference["preference_digest"]),
        "beat_audits": audits, "opportunities": projected, "tail_policy": _tail_policy(alignment),
    }
    data["coverage_gate"] = _coverage(audits, projected, preference)
    data["plan_digest"] = _digest(data)
    return data


def validate_post_alignment_visual_plan(value: Mapping, script: Mapping, transcript: Mapping, alignment: Mapping, preference: Mapping) -> None:
    required = {
        "artifact_version", "plan_id", "revision", "previous_revision", "created_at", "script_id", "script_revision",
        "script_digest", "transcript_digest", "alignment_id", "alignment_digest", "episode_visual_preference_digest",
        "beat_audits", "opportunities", "tail_policy", "coverage_gate", "plan_digest",
    }
    if set(value) != required or value.get("artifact_version") != "post-alignment-visual-plan/1":
        raise PostAlignmentVisualPlanError("Post-Alignment Visual Plan 字段或版本无效")
    raw = [{key: item[key] for key in ("opportunity_id", "beat_id", "semantic_char_start", "semantic_char_end", "visual_kind", "visual_role", "semantic_target", "source_binding")} for item in value["opportunities"]]
    expected = build_post_alignment_visual_plan(
        script, transcript, alignment, preference, raw, plan_id=value["plan_id"], created_at=value["created_at"],
        revision=value["revision"], previous_revision=value["previous_revision"],
    )
    if dict(value) != expected:
        raise PostAlignmentVisualPlanError("Post-Alignment Visual Plan 无法从 canonical roots 重推导")
