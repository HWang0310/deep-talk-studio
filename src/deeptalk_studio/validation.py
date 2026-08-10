from typing import Any, Dict, Iterable, List, Set
from urllib.parse import urlparse

from .models import ResearchReport


CLAIM_CLASSIFICATIONS = {
    "confirmed_fact",
    "media_report",
    "party_statement",
    "commentary",
    "unverified",
}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
FACT_CHECK_STATUSES = {"verified", "partially_verified", "unverified", "disputed"}


class ReportValidationError(ValueError):
    pass


def _require_list(value: Any, field: str) -> List[Any]:
    if not isinstance(value, list):
        raise ReportValidationError(f"{field} 必须是列表")
    return value


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportValidationError(f"{field} 不能为空")
    return value


def _unique_ids(items: Iterable[Dict[str, Any]], field: str) -> Set[str]:
    seen: Set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ReportValidationError(f"{field}[{index}] 必须是对象")
        item_id = _require_text(item.get("id"), f"{field}[{index}].id")
        if item_id in seen:
            raise ReportValidationError(f"{field} 出现重复 ID：{item_id}")
        seen.add(item_id)
    return seen


def _check_refs(refs: Any, known: Set[str], field: str) -> None:
    for ref in _require_list(refs, field):
        if ref not in known:
            raise ReportValidationError(f"{field} 引用了不存在的 ID：{ref}")


def validate_report(report: ResearchReport) -> None:
    data = report.data
    if data["schema_version"] != "0.1":
        raise ReportValidationError("schema_version 必须是 0.1")
    _require_text(data["topic"], "topic")
    _require_text(data["research_question"], "research_question")
    _require_text(data["generated_at"], "generated_at")
    _require_text(data["scope_summary"], "scope_summary")
    _require_text(data["executive_summary"], "executive_summary")

    sources = _require_list(data["sources"], "sources")
    claims = _require_list(data["claims"], "claims")
    source_ids = _unique_ids(sources, "sources")
    claim_ids = _unique_ids(claims, "claims")
    _unique_ids(_require_list(data["perspectives"], "perspectives"), "perspectives")

    for source in sources:
        url = _require_text(source.get("url"), f"source {source['id']}.url")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ReportValidationError(
                f"source {source['id']} 的 URL 必须是有效 HTTP(S) 地址"
            )

    for claim in claims:
        classification = claim.get("classification")
        if classification not in CLAIM_CLASSIFICATIONS:
            raise ReportValidationError(
                f"claim {claim['id']} 的 classification 无效：{classification}"
            )
        if claim.get("confidence") not in CONFIDENCE_LEVELS:
            raise ReportValidationError(f"claim {claim['id']} 的 confidence 无效")
        refs = _require_list(claim.get("source_ids"), f"claim {claim['id']}.source_ids")
        if classification == "confirmed_fact" and not refs:
            raise ReportValidationError(
                f"confirmed_fact {claim['id']} 必须至少引用一个来源"
            )
        _check_refs(refs, source_ids, f"claim {claim['id']}.source_ids")

    for index, item in enumerate(_require_list(data["timeline"], "timeline")):
        _check_refs(item.get("claim_ids"), claim_ids, f"timeline[{index}].claim_ids")
        _check_refs(item.get("source_ids"), source_ids, f"timeline[{index}].source_ids")

    for item in data["perspectives"]:
        _check_refs(
            item.get("source_ids"), source_ids, f"perspective {item['id']}.source_ids"
        )

    for index, item in enumerate(_require_list(data["conflicts"], "conflicts")):
        _check_refs(item.get("source_ids"), source_ids, f"conflicts[{index}].source_ids")

    _require_list(data["open_questions"], "open_questions")
    for index, item in enumerate(_require_list(data["angles"], "angles")):
        _check_refs(
            item.get("required_claim_ids"),
            claim_ids,
            f"angles[{index}].required_claim_ids",
        )

    for index, item in enumerate(
        _require_list(data["fact_check_notes"], "fact_check_notes")
    ):
        claim_id = item.get("claim_id")
        if claim_id not in claim_ids:
            raise ReportValidationError(
                f"fact_check_notes[{index}] 引用了不存在的 ID：{claim_id}"
            )
        if item.get("status") not in FACT_CHECK_STATUSES:
            raise ReportValidationError(
                f"fact_check_notes[{index}] 的 status 无效：{item.get('status')}"
            )

    _require_list(data["limitations"], "limitations")
    handoff = data["handoff_to_script_agent"]
    if not isinstance(handoff, dict):
        raise ReportValidationError("handoff_to_script_agent 必须是对象")
    _check_refs(
        handoff.get("must_keep_claim_ids"),
        claim_ids,
        "handoff_to_script_agent.must_keep_claim_ids",
    )
    _require_list(handoff.get("avoid_claims"), "handoff_to_script_agent.avoid_claims")
    _require_list(
        handoff.get("follow_up_research"),
        "handoff_to_script_agent.follow_up_research",
    )

