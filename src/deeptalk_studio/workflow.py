"""Research Draft → Independent Fact Check → reviewed revision workflow."""

import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .fact_check import (
    apply_fact_check,
    normalize_fact_check_sources,
    validate_fact_check_artifact,
)
from .discovery import load_channel_profile, prepare_discovery
from .discovery_storage import DiscoveryPaths, save_discovery
from .models import ResearchReport
from .provenance import ProviderProvenance, reconcile_provenance, reconcile_source_records
from .providers.base import ProviderResult, ResearchProvider
from .quality import apply_quality_gate, calculate_quality_summary
from .revisions import create_approval_revision, create_revision
from .schema import (
    API_RESEARCH_DRAFT_JSON_SCHEMA,
    CODEX_DRAFT_JSON_SCHEMA,
    DISCOVERY_RAW_JSON_SCHEMA,
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


@dataclass(frozen=True)
class TopicDiscoveryResult:
    candidate_set: object
    paths: DiscoveryPaths


def _default_clock() -> datetime:
    return datetime.now().astimezone()


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        return moment.astimezone().isoformat()
    return moment.isoformat()


def run_report_approval(
    report: ResearchReport,
    confirmation: str,
    output_root: Path,
    clock: Callable[[], datetime] = _default_clock,
) -> ReportPaths:
    """Persist explicit user approval as the next immutable report revision."""

    approved = create_approval_revision(report, confirmation, _iso(clock()))
    return save_report(ResearchReport.from_dict(approved), output_root)


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
    artifact = normalize_fact_check_sources(artifact, draft)
    validate_fact_check_artifact(artifact, draft)
    return artifact


def run_research(
    topic: str,
    provider: ResearchProvider,
    output_root: Path,
    clock: Callable[[], datetime] = _default_clock,
    id_factory: Callable[[str], str] = _default_id_factory,
    research_handoff: Optional[dict] = None,
) -> WorkflowResult:
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("主题不能为空")

    if research_handoff is None:
        research_result = provider.research(clean_topic, API_RESEARCH_DRAFT_JSON_SCHEMA)
    else:
        research_result = provider.research(
            clean_topic, API_RESEARCH_DRAFT_JSON_SCHEMA, research_handoff
        )
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


def run_topic_discovery(
    query: str,
    provider: ResearchProvider,
    output_root: Path,
    clock: Callable[[], datetime] = _default_clock,
    id_factory: Callable[[str], str] = _default_id_factory,
    category_filter: tuple = (),
) -> TopicDiscoveryResult:
    """Run a light Discovery pass and persist candidates before user selection."""

    clean_query = query.strip()
    if not clean_query:
        raise ValueError("选题请求不能为空")
    result = provider.discover(clean_query, DISCOVERY_RAW_JSON_SCHEMA)
    raw = deepcopy(result.data)
    raw["query"] = clean_query
    provenance_urls = []
    for call in result.provenance.search_calls:
        provenance_urls.extend(call.source_urls)
    provenance_urls.extend(citation.url for citation in result.provenance.citations)
    candidate_set = prepare_discovery(
        raw,
        load_channel_profile(),
        now=clock(),
        discovery_id=id_factory("DISC"),
        provenance_urls=provenance_urls,
        discovery_mode="openai_api",
        category_filter=category_filter,
    )
    return TopicDiscoveryResult(
        candidate_set=candidate_set,
        paths=save_discovery(candidate_set, output_root),
    )


def run_fact_check_review(
    draft: ResearchReport, artifact: dict, output_root: Path
) -> ReviewResult:
    """Apply a separately produced FactCheck Artifact to one draft revision."""

    artifact = normalize_fact_check_sources(artifact, draft)
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
