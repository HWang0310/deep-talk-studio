"""Approved Research → Script Draft → independent Script Review workflow."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Optional

from .models import ContentThesisCard, ResearchReport, ScriptDraft
from .providers.base import ScriptProvider
from .schema import SCRIPT_DRAFT_CONTENT_JSON_SCHEMA, SCRIPT_REVIEW_CONTENT_JSON_SCHEMA
from .script_profile import load_script_profile
from .script_review import ScriptReviewResult, prepare_script_review
from .script_storage import (
    ScriptPaths,
    save_script,
    save_script_review_artifact,
)
from .script_validation import (
    ScriptValidationError,
    assert_report_ready_for_script,
    prepare_script_draft,
)


DEFAULT_SCRIPT_OUTPUT = Path(__file__).resolve().parents[2] / "script_drafts"


@dataclass(frozen=True)
class PreparedScriptResult:
    script: ScriptDraft
    paths: ScriptPaths


@dataclass(frozen=True)
class ReviewedScriptResult:
    artifact: dict
    review_artifact: Path
    script: ScriptDraft
    paths: ScriptPaths


@dataclass(frozen=True)
class ScriptWorkflowResult:
    draft: ScriptPaths
    review_artifact: Path
    reviewed: ScriptPaths
    script_id: str
    final_status: str


def _default_clock() -> datetime:
    return datetime.now().astimezone()


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        return moment.astimezone().isoformat()
    return moment.isoformat()


def _require_no_search_provenance(result: object, step: str) -> None:
    provenance = result.provenance
    if provenance.search_calls or provenance.citations:
        raise ScriptValidationError(f"{step} 不允许携带网络搜索 provenance")


def prepare_codex_script(
    content: dict,
    report: ResearchReport,
    output_root: Path = DEFAULT_SCRIPT_OUTPUT,
    profile: Optional[Mapping[str, object]] = None,
    *,
    target_duration_minutes: float = 12,
    created_at: str = "",
    script_id: str = "",
    content_thesis_card: Optional[ContentThesisCard] = None,
) -> PreparedScriptResult:
    selected_profile = dict(profile or load_script_profile())
    timestamp = created_at or _iso(_default_clock())
    script = prepare_script_draft(
        content,
        report,
        selected_profile,
        created_at=timestamp,
        script_id=script_id or _default_id_factory("SCR"),
        target_duration_minutes=target_duration_minutes,
        script_mode="codex_skill",
        content_thesis_card=content_thesis_card,
    )
    return PreparedScriptResult(
        script=script,
        paths=save_script(script, report, selected_profile, output_root),
    )


def run_codex_script_review(
    content: dict,
    report: ResearchReport,
    script: ScriptDraft,
    output_root: Path = DEFAULT_SCRIPT_OUTPUT,
    profile: Optional[Mapping[str, object]] = None,
    *,
    created_at: str = "",
    review_id: str = "",
) -> ReviewedScriptResult:
    selected_profile = dict(profile or load_script_profile())
    timestamp = created_at or _iso(_default_clock())
    result = prepare_script_review(
        content,
        report,
        script,
        selected_profile,
        created_at=timestamp,
        review_id=review_id or _default_id_factory("SRV"),
        review_mode="codex_skill",
    )
    artifact_path = save_script_review_artifact(
        result.artifact, script, output_root
    ).json
    paths = save_script(
        result.script, report, selected_profile, output_root, result.artifact
    )
    return ReviewedScriptResult(
        artifact=result.artifact,
        review_artifact=artifact_path,
        script=result.script,
        paths=paths,
    )


def run_script_workflow(
    report: ResearchReport,
    provider: ScriptProvider,
    output_root: Path = DEFAULT_SCRIPT_OUTPUT,
    profile: Optional[Mapping[str, object]] = None,
    *,
    target_duration_minutes: float = 12,
    clock: Callable[[], datetime] = _default_clock,
    id_factory: Callable[[str], str] = _default_id_factory,
    content_thesis_card: Optional[ContentThesisCard] = None,
) -> ScriptWorkflowResult:
    assert_report_ready_for_script(report)
    selected_profile = dict(profile or load_script_profile())
    if selected_profile["profile_version"] == "1" and content_thesis_card is None:
        raise ScriptValidationError("Script Agent V1 必须先通过 Content Thesis Human Review")
    writer_input = report.to_dict()
    if content_thesis_card is not None:
        writer_input = {
            "approved_research": report.to_dict(),
            "approved_content_thesis_card": content_thesis_card.to_dict(),
        }
    writer_result = provider.write_script(
        writer_input,
        selected_profile,
        target_duration_minutes,
        SCRIPT_DRAFT_CONTENT_JSON_SCHEMA,
    )
    _require_no_search_provenance(writer_result, "Script Writer")
    draft = prepare_script_draft(
        writer_result.data,
        report,
        selected_profile,
        created_at=_iso(clock()),
        script_id=id_factory("SCR"),
        target_duration_minutes=target_duration_minutes,
        script_mode="openai_api",
        content_thesis_card=content_thesis_card,
    )
    draft_paths = save_script(draft, report, selected_profile, output_root)
    reviewer_input = writer_input
    reviewer_result = provider.review_script(reviewer_input, draft.to_dict(), SCRIPT_REVIEW_CONTENT_JSON_SCHEMA)
    _require_no_search_provenance(reviewer_result, "Script Reviewer")
    review = prepare_script_review(
        reviewer_result.data,
        report,
        draft,
        selected_profile,
        created_at=_iso(clock()),
        review_id=id_factory("SRV"),
        review_mode="openai_api",
    )
    artifact_path = save_script_review_artifact(
        review.artifact, draft, output_root
    ).json
    reviewed_paths = save_script(
        review.script, report, selected_profile, output_root, review.artifact
    )
    return ScriptWorkflowResult(
        draft=draft_paths,
        review_artifact=artifact_path,
        reviewed=reviewed_paths,
        script_id=draft.script_id,
        final_status=review.script.status,
    )
