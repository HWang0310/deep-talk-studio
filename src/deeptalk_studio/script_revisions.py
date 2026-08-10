"""Script revision creation and comparison."""

from typing import Any, Dict, Mapping

from .models import ResearchReport, ScriptDraft
from .script_validation import (
    ScriptValidationError,
    prepare_script_draft,
    validate_script_draft,
)


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
    target = (
        previous.target_duration_minutes
        if target_duration_minutes is None
        else target_duration_minutes
    )
    return prepare_script_draft(
        content,
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
