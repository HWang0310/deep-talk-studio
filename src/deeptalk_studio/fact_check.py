"""Independent Fact Check artifact validation and application."""

from copy import deepcopy
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from .models import ResearchReport
from .schema import FACT_CHECK_JSON_SCHEMA
from .sources import normalize_and_group_sources, normalize_report_sources, normalize_url
from .validation import ReportValidationError, validate_json_schema, validate_report


def queue_fact_checks(report: ResearchReport) -> List[str]:
    validate_report(report)
    return [
        claim["id"]
        for claim in report.data["claims"]
        if claim["risk_level"] in {"high", "critical"}
    ]


def _unique(values: List[str], label: str) -> Set[str]:
    if len(values) != len(set(values)):
        raise ReportValidationError(f"{label} 不能包含重复 ID")
    return set(values)


def _http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_fact_check_sources(
    artifact: Dict[str, Any], report: ResearchReport
) -> Dict[str, Any]:
    """Canonicalize new Fact Check sources together with the Research Draft."""

    validate_report(report)
    result = deepcopy(artifact)
    new_source_ids = [source["id"] for source in result["new_sources"]]
    grouped = normalize_and_group_sources(
        list(report.data["sources"]) + result["new_sources"]
    )
    grouped_by_id = {source["id"]: source for source in grouped}
    result["new_sources"] = [grouped_by_id[source_id] for source_id in new_source_ids]
    for link in result["evidence_links"]:
        source = grouped_by_id.get(link["source_id"])
        if source:
            link["independence_group"] = source["independence_group"]
    return result


def validate_fact_check_artifact(
    artifact: Dict[str, Any], report: ResearchReport
) -> None:
    validate_report(report)
    validate_json_schema(artifact, FACT_CHECK_JSON_SCHEMA, "fact_check_artifact")
    canonical = normalize_fact_check_sources(artifact, report)
    if (
        artifact["new_sources"] != canonical["new_sources"]
        or artifact["evidence_links"] != canonical["evidence_links"]
    ):
        raise ReportValidationError(
            "FactCheck 新来源和 Evidence Link 必须使用系统确定的规范化与独立性分组"
        )
    if artifact["report_id"] != report.report_id:
        raise ReportValidationError("FactCheck Artifact 的 report_id 与报告不一致")
    if artifact["report_revision"] != report.revision:
        raise ReportValidationError("FactCheck Artifact 的 report_revision 与报告不一致")

    claim_map = {claim["id"]: claim for claim in report.data["claims"]}
    claim_ids = set(claim_map)
    existing_sources = {source["id"]: source for source in report.data["sources"]}
    existing_evidence_ids = {link["id"] for link in report.data["evidence_links"]}

    queued = _unique(artifact["queued_claim_ids"], "queued_claim_ids")
    unknown_queued = queued - claim_ids
    if unknown_queued:
        raise ReportValidationError(
            "queued_claim_ids 引用了不存在的 ID：" + sorted(unknown_queued)[0]
        )
    expected_high_risk = set(queue_fact_checks(report))
    missing_high_risk = expected_high_risk - queued
    if missing_high_risk:
        raise ReportValidationError(
            "高风险 claim 未进入 Fact Check 队列：" + sorted(missing_high_risk)[0]
        )
    tool_provenance = artifact["tool_provenance"]
    if not tool_provenance["search_call_ids"] or not (
        tool_provenance["consulted_urls"] or tool_provenance["citation_urls"]
    ):
        raise ReportValidationError(
            "FactCheck Artifact 必须保留独立检索的 tool provenance"
        )
    provenance_urls: Set[str] = set()
    for url in tool_provenance["consulted_urls"] + tool_provenance["citation_urls"]:
        if not _http_url(url):
            raise ReportValidationError("FactCheck tool provenance 包含无效 URL")
        provenance_urls.add(normalize_url(url))

    new_sources: Dict[str, Dict[str, Any]] = {}
    for source in artifact["new_sources"]:
        if source["id"] in existing_sources or source["id"] in new_sources:
            raise ReportValidationError(f"FactCheck source ID 重复：{source['id']}")
        if not _http_url(source["url"]) or not _http_url(source["normalized_url"]):
            raise ReportValidationError(
                f"FactCheck source {source['id']} 的 URL 必须是有效 HTTP(S) 地址"
            )
        new_sources[source["id"]] = source
    all_sources = dict(existing_sources)
    all_sources.update(new_sources)

    seen_evidence: Set[str] = set()
    for link in artifact["evidence_links"]:
        if link["id"] in existing_evidence_ids or link["id"] in seen_evidence:
            raise ReportValidationError(f"FactCheck evidence ID 重复：{link['id']}")
        seen_evidence.add(link["id"])
        if link["claim_id"] not in claim_ids:
            raise ReportValidationError(
                f"FactCheck evidence {link['id']} 引用了不存在的 claim：{link['claim_id']}"
            )
        if link["source_id"] not in all_sources:
            raise ReportValidationError(
                f"FactCheck evidence {link['id']} 引用了不存在的 source：{link['source_id']}"
            )
        if link["independence_group"] != all_sources[link["source_id"]]["independence_group"]:
            raise ReportValidationError(
                f"FactCheck evidence {link['id']} 的 independence_group 与来源不一致"
            )

    checked: Set[str] = set()
    for index, check in enumerate(artifact["checks"]):
        claim_id = check["claim_id"]
        if claim_id not in claim_ids:
            raise ReportValidationError(
                f"checks[{index}].claim_id 引用了不存在的 ID：{claim_id}"
            )
        if claim_id in checked:
            raise ReportValidationError(f"checks 出现重复 claim：{claim_id}")
        checked.add(claim_id)
        if check["original_classification"] != claim_map[claim_id]["classification"]:
            raise ReportValidationError(f"check {claim_id} 的 original_classification 与草稿不一致")
        for source_id in check["source_ids"]:
            if source_id not in all_sources:
                raise ReportValidationError(
                    f"check {claim_id}.source_ids 引用了不存在的 ID：{source_id}"
                )
        if claim_id in expected_high_risk and not check["searched_new_sources"]:
            raise ReportValidationError(f"高风险 claim {claim_id} 必须记录新的来源检索")
        if claim_id in expected_high_risk and not any(
            normalize_url(all_sources[source_id]["url"]) in provenance_urls
            for source_id in check["source_ids"]
        ):
            raise ReportValidationError(
                f"高风险 claim {claim_id} 的核查来源没有出现在本次独立检索 provenance 中"
            )
    unchecked_queued = queued - checked
    if unchecked_queued:
        raise ReportValidationError(
            "FactCheck 队列中的 claim 没有检查结果：" + sorted(unchecked_queued)[0]
        )


def apply_fact_check(
    report: ResearchReport, artifact: Dict[str, Any]
) -> Dict[str, Any]:
    artifact = normalize_fact_check_sources(artifact, report)
    validate_fact_check_artifact(artifact, report)
    result = report.to_dict()
    result["sources"].extend(deepcopy(artifact["new_sources"]))
    result["evidence_links"].extend(deepcopy(artifact["evidence_links"]))
    result = normalize_report_sources(result)
    claims = {claim["id"]: claim for claim in result["claims"]}
    reviewed_source_pairs = {
        (check["claim_id"], source_id)
        for check in artifact["checks"]
        for source_id in check["source_ids"]
    }
    for link in result["evidence_links"]:
        if (link["claim_id"], link["source_id"]) in reviewed_source_pairs:
            link["verified_in_review"] = True
    corrections = list(result["corrections"])
    unresolved: List[str] = []
    for check in artifact["checks"]:
        claim = claims[check["claim_id"]]
        previous_classification = claim["classification"]
        claim["classification"] = check["recommended_classification"]
        claim["verification_status"] = check["outcome"]
        claim["notes"] = f"{claim['notes']} 独立核查：{check['verification_notes']}".strip()
        if previous_classification != claim["classification"]:
            corrections.append(
                {
                    "claim_id": claim["id"],
                    "summary": f"分类由 {previous_classification} 调整为 {claim['classification']}。",
                    "reason": check["verification_notes"],
                    "source_ids": list(check["source_ids"]),
                }
            )
        if check["outcome"] != "verified":
            unresolved.append(claim["id"])
    result["corrections"] = corrections
    result["fact_check"] = {
        "review_id": artifact["review_id"],
        "reviewed_at": artifact["created_at"],
        "status": artifact["status"],
        "checked_claim_ids": [check["claim_id"] for check in artifact["checks"]],
        "unresolved_claim_ids": unresolved,
    }
    result["status"] = "draft"
    result["change_summary"] = "应用独立 Fact Check 结果，等待质量 Gate 复算。"
    return result
