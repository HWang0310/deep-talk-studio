"""Research Draft → Independent Fact Check → reviewed revision workflow."""

import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .fact_check import apply_fact_check, validate_fact_check_artifact
from .models import ResearchReport
from .provenance import ProviderProvenance, reconcile_provenance, reconcile_source_records
from .providers.base import ProviderResult, ResearchProvider
from .quality import apply_quality_gate, calculate_quality_summary
from .revisions import create_revision
from .schema import (
    API_RESEARCH_DRAFT_JSON_SCHEMA,
    CODEX_DRAFT_JSON_SCHEMA,
    FACT_CHECK_JSON_SCHEMA,
)
from .sources import normalize_report_sources
from .storage import ReportPaths, save_fact_check_artifact, save_report
from .validation import validate_json_schema


@dataclass(frozen=True)
class WorkflowResult:
    draft: ReportPaths
    fact_check: Path
    reviewed: ReportPaths
    report_id: str
    final_status: str


@dataclass(frozen=True)
class ReviewResult:
    fact_check: Path
    reviewed: ReportPaths
    final_status: str


def _default_clock() -> datetime:
    return datetime.now().astimezone()


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        return moment.astimezone().isoformat()
    return moment.isoformat()


def _provenance_manifest(provenance: ProviderProvenance) -> dict:
    search_call_ids = [call.call_id for call in provenance.search_calls if call.call_id]
    search_queries = []
    consulted_urls = []
    for call in provenance.search_calls:
        search_queries.extend(call.queries)
        consulted_urls.extend(call.source_urls)
    citation_urls = [citation.url for citation in provenance.citations]
    return {
        "search_call_ids": list(dict.fromkeys(search_call_ids)),
        "search_queries": list(dict.fromkeys(search_queries)),
        "consulted_urls": list(dict.fromkeys(consulted_urls)),
        "citation_urls": list(dict.fromkeys(citation_urls)),
    }


def _prepare_draft(
    topic: str,
    provider_result: ProviderResult,
    created_at: str,
    report_id: str,
) -> ResearchReport:
    validate_json_schema(
        provider_result.data, API_RESEARCH_DRAFT_JSON_SCHEMA, "api_research_draft"
    )
    content = deepcopy(provider_result.data)
    for source in content["sources"]:
        source.update(
            normalized_url=source["url"],
            inspection_method="not_inspected",
            provenance_method="web_search_action_source",
            provenance_status="unmatched",
            provenance_refs=[],
            independence_group="pending",
        )
    for claim in content["claims"]:
        claim["verification_status"] = "not_checked"
    for link in content["evidence_links"]:
        link["independence_group"] = "pending"
        link["verified_in_review"] = False
    data = {
        "schema_version": "0.2",
        "report_id": report_id,
        "revision": 1,
        "previous_revision": 0,
        "created_at": created_at,
        "generated_at": created_at,
        "research_mode": "openai_api",
        "status": "fact_check_pending",
        "change_summary": "完成 Research Draft，等待独立 Fact Check。",
        "corrections": [],
        **content,
        "topic": topic,
        "fact_check": {
            "review_id": "",
            "reviewed_at": "",
            "status": "not_run",
            "checked_claim_ids": [],
            "unresolved_claim_ids": [],
        },
        "quality_summary": {},
        "approval_gate": {
            "status": "pending",
            "requires_user_confirmation": True,
            "high_risk_claim_ids": [
                claim["id"]
                for claim in content["claims"]
                if claim["risk_level"] in {"high", "critical"}
            ],
            "user_confirmation": "",
            "ready_for_script": False,
        },
    }
    data = reconcile_provenance(data, provider_result.provenance)
    data["quality_summary"] = calculate_quality_summary(data)
    return ResearchReport.from_dict(data)


def prepare_codex_draft(
    input_data: dict,
    created_at: str = "",
    report_id: str = "",
) -> ResearchReport:
    """Turn a judgment-focused Codex payload into a deterministic draft artifact."""

    validate_json_schema(input_data, CODEX_DRAFT_JSON_SCHEMA, "codex_draft")
    timestamp = created_at or _iso(_default_clock())
    identity = report_id or _default_id_factory("RPT")
    content = deepcopy(input_data)
    for source in content["sources"]:
        source["normalized_url"] = source["url"]
        source["independence_group"] = "pending"
    for claim in content["claims"]:
        claim["verification_status"] = "not_checked"
    for link in content["evidence_links"]:
        link["independence_group"] = "pending"
        link["verified_in_review"] = False
    data = {
        "schema_version": "0.2",
        "report_id": identity,
        "revision": 1,
        "previous_revision": 0,
        "created_at": timestamp,
        "generated_at": timestamp,
        "research_mode": "codex_skill",
        "status": "fact_check_pending",
        "change_summary": "完成 Codex Skill Research Draft，等待独立 Fact Check。",
        "corrections": [],
        **content,
        "fact_check": {
            "review_id": "",
            "reviewed_at": "",
            "status": "not_run",
            "checked_claim_ids": [],
            "unresolved_claim_ids": [],
        },
        "quality_summary": {},
        "approval_gate": {
            "status": "pending",
            "requires_user_confirmation": True,
            "high_risk_claim_ids": [
                claim["id"]
                for claim in content["claims"]
                if claim["risk_level"] in {"high", "critical"}
            ],
            "user_confirmation": "",
            "ready_for_script": False,
        },
    }
    data = normalize_report_sources(data)
    data["quality_summary"] = calculate_quality_summary(data)
    return ResearchReport.from_dict(data)


def _prepare_fact_check_artifact(
    result: ProviderResult,
    draft: ResearchReport,
    created_at: str,
    review_id: str,
) -> dict:
    artifact = deepcopy(result.data)
    artifact.update(
        artifact_version="0.2",
        review_id=review_id,
        report_id=draft.report_id,
        report_revision=draft.revision,
        created_at=created_at,
        research_mode="openai_api",
        tool_provenance=_provenance_manifest(result.provenance),
    )
    artifact["new_sources"] = reconcile_source_records(
        artifact["new_sources"], result.provenance
    )
    source_groups = {
        source["id"]: source["independence_group"]
        for source in draft.data["sources"] + artifact["new_sources"]
    }
    for link in artifact["evidence_links"]:
        if link["source_id"] in source_groups:
            link["independence_group"] = source_groups[link["source_id"]]
    validate_fact_check_artifact(artifact, draft)
    return artifact


def run_research(
    topic: str,
    provider: ResearchProvider,
    output_root: Path,
    clock: Callable[[], datetime] = _default_clock,
    id_factory: Callable[[str], str] = _default_id_factory,
) -> WorkflowResult:
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("主题不能为空")

    research_result = provider.research(clean_topic, API_RESEARCH_DRAFT_JSON_SCHEMA)
    draft = _prepare_draft(
        clean_topic,
        research_result,
        _iso(clock()),
        id_factory("RPT"),
    )
    draft_paths = save_report(draft, output_root)

    fact_check_result = provider.fact_check(draft.to_dict(), FACT_CHECK_JSON_SCHEMA)
    artifact = _prepare_fact_check_artifact(
        fact_check_result,
        draft,
        _iso(clock()),
        id_factory("FCR"),
    )
    review_result = run_fact_check_review(draft, artifact, output_root)
    return WorkflowResult(
        draft=draft_paths,
        fact_check=review_result.fact_check,
        reviewed=review_result.reviewed,
        report_id=draft.report_id,
        final_status=review_result.final_status,
    )


def run_fact_check_review(
    draft: ResearchReport, artifact: dict, output_root: Path
) -> ReviewResult:
    """Apply a separately produced FactCheck Artifact to one draft revision."""

    validate_fact_check_artifact(artifact, draft)
    artifact_path = save_fact_check_artifact(artifact, draft, output_root).json
    applied = apply_fact_check(draft, artifact)
    applied["quality_summary"] = calculate_quality_summary(applied)
    applied_report = ResearchReport.from_dict(applied)
    revised = create_revision(
        applied_report,
        generated_at=artifact["created_at"],
        change_summary="应用独立 Fact Check，并重新计算研究质量 Gate。",
    )
    final_data = apply_quality_gate(revised)
    final_report = ResearchReport.from_dict(final_data)
    reviewed_paths = save_report(final_report, output_root)
    return ReviewResult(
        fact_check=artifact_path,
        reviewed=reviewed_paths,
        final_status=final_report.status,
    )
