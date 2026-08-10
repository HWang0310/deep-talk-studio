"""Script revision creation, stable Beat identity, and comparison."""

from copy import deepcopy
from typing import Any, Dict, Mapping, Tuple

from .models import ResearchReport, ScriptDraft
from .schema import SCRIPT_REVISION_CONTENT_JSON_SCHEMA
from .script_validation import (
    ScriptValidationError,
    beat_id_number,
    prepare_script_draft,
    validate_script_draft,
)
from .validation import ReportValidationError, validate_json_schema


def _validate_revision_content(content: Any) -> None:
    try:
        validate_json_schema(content, SCRIPT_REVISION_CONTENT_JSON_SCHEMA, "script_revision")
    except ReportValidationError as exc:
        raise ScriptValidationError(str(exc)) from None


def _beat_signature(beat: Mapping[str, Any]) -> Tuple[Any, ...]:
    """Use stable grounding/intent fields for unambiguous automatic continuity."""

    return (
        beat["purpose"],
        beat["content_kind"],
        tuple(beat["claim_ids"]),
        tuple(beat["evidence_link_ids"]),
        tuple(beat["analysis_basis_claim_ids"]),
    )


def _previous_identity(previous: ScriptDraft) -> Tuple[dict, dict]:
    data = previous.to_dict()
    active = {beat["beat_id"]: beat for beat in data["beats"]}
    identity = data.get("beat_identity")
    if identity is None:
        # Legacy V0.4 drafts are strictly sequential; derive their first
        # V0.4.1 identity state rather than trusting a user supplied mapping.
        active_numbers = [beat_id_number(beat_id) for beat_id in active]
        return active, {
            "next_beat_number": max(active_numbers, default=0) + 1,
            "retired_beat_ids": [],
        }
    return active, deepcopy(identity)


def _assign_stable_beat_ids(content: Mapping[str, Any], previous: ScriptDraft):
    previous_beats, identity = _previous_identity(previous)
    unmatched = set(previous_beats)
    used_origins = set()
    assigned_ids = []
    clean_beats = []
    next_number = identity["next_beat_number"]

    for raw_beat in content["beats"]:
        beat = deepcopy(raw_beat)
        origin = beat.pop("origin_beat_id", "").strip()
        if origin:
            if origin not in previous_beats:
                raise ScriptValidationError(f"origin_beat_id 引用了不存在的 Beat：{origin}")
            if origin in used_origins:
                raise ScriptValidationError(f"origin_beat_id 不能重复使用：{origin}")
            beat_id = origin
        else:
            signature = _beat_signature(beat)
            candidates = [
                beat_id
                for beat_id in unmatched
                if _beat_signature(previous_beats[beat_id]) == signature
            ]
            if len(candidates) > 1:
                raise ScriptValidationError(
                    "存在多个可能的原 Beat，请由程序/Skill 提供唯一 origin_beat_id"
                )
            if candidates:
                beat_id = candidates[0]
            else:
                beat_id = f"B{next_number:03d}"
                next_number += 1
        used_origins.add(beat_id)
        unmatched.discard(beat_id)
        assigned_ids.append(beat_id)
        clean_beats.append(beat)

    retired = sorted(
        set(identity["retired_beat_ids"]) | unmatched,
        key=beat_id_number,
    )
    all_numbers = [beat_id_number(beat_id) for beat_id in assigned_ids + retired]
    next_number = max(next_number, max(all_numbers, default=0) + 1)
    return clean_beats, assigned_ids, {
        "next_beat_number": next_number,
        "retired_beat_ids": retired,
    }


def create_script_revision(
    content: Dict[str, Any],
    previous: ScriptDraft,
    report: ResearchReport,
    profile: Mapping[str, object],
    *,
    generated_at: str,
    target_duration_minutes: float = None,
    change_summary: str = "根据用户反馈修改稿件。",
) -> ScriptDraft:
    if (
        previous.report_id != report.report_id
        or previous.report_revision != report.revision
    ):
        raise ScriptValidationError(
            "Script revision 不能静默切换到另一份 Research revision"
        )
    validate_script_draft(previous, report, profile)
    _validate_revision_content(content)
    clean_content = deepcopy(content)
    clean_beats, assigned_ids, identity = _assign_stable_beat_ids(content, previous)
    clean_content["beats"] = clean_beats
    target = (
        previous.target_duration_minutes
        if target_duration_minutes is None
        else target_duration_minutes
    )
    return prepare_script_draft(
        clean_content,
        report,
        profile,
        created_at=previous.created_at,
        generated_at=generated_at,
        script_id=previous.script_id,
        target_duration_minutes=target,
        script_mode=previous.script_mode,
        revision=previous.revision + 1,
        previous_revision=previous.revision,
        change_summary=change_summary,
        beat_ids=assigned_ids,
        beat_identity=identity,
    )


def compare_script_revisions(first: ScriptDraft, second: ScriptDraft) -> dict:
    if first.script_id != second.script_id:
        raise ScriptValidationError("只能比较同一个 script_id 的修订版")
    if first.report_id != second.report_id or first.report_revision != second.report_revision:
        raise ScriptValidationError("只能比较绑定同一 Research revision 的稿件")
    first_beats = {beat["beat_id"]: beat for beat in first.beats}
    second_beats = {beat["beat_id"]: beat for beat in second.beats}
    common = first_beats.keys() & second_beats.keys()
    changed = sorted(
        beat_id for beat_id in common if first_beats[beat_id] != second_beats[beat_id]
    )
    first_coverage = set(first.covered_must_keep_claim_ids)
    second_coverage = set(second.covered_must_keep_claim_ids)
    return {
        "script_id": first.script_id,
        "from_revision": first.revision,
        "to_revision": second.revision,
        "changed_beat_ids": changed,
        "added_beat_ids": sorted(second_beats.keys() - first_beats.keys()),
        "removed_beat_ids": sorted(first_beats.keys() - second_beats.keys()),
        "character_count_change": second.character_count - first.character_count,
        "estimated_duration_change_minutes": round(
            second.estimated_duration_minutes - first.estimated_duration_minutes, 1
        ),
        "target_duration_change_minutes": (
            second.target_duration_minutes - first.target_duration_minutes
        ),
        "added_claim_coverage": sorted(second_coverage - first_coverage),
        "removed_claim_coverage": sorted(first_coverage - second_coverage),
    }
