"""Transparent research quality metrics and human approval gates."""

from copy import deepcopy
from typing import Any, Dict, List, Set

from .models import ResearchReport
from .validation import ReportValidationError, validate_report


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def calculate_quality_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    claims = data["claims"]
    sources = {source["id"]: source for source in data["sources"]}
    evidence = data["evidence_links"]
    evidence_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for link in evidence:
        evidence_by_claim.setdefault(link["claim_id"], []).append(link)

    claim_count = len(claims)
    sourced_claim_count = sum(bool(evidence_by_claim.get(claim["id"])) for claim in claims)

    high_risk = [claim for claim in claims if claim["risk_level"] in {"high", "critical"}]
    checked_ids = set(data["fact_check"]["checked_claim_ids"])
    high_risk_checked = [
        claim
        for claim in high_risk
        if claim["id"] in checked_ids and claim["verification_status"] != "not_checked"
    ]
    unresolved_high_risk = [
        claim for claim in high_risk if claim["verification_status"] != "verified"
    ]

    confirmed = [claim for claim in claims if claim["classification"] == "confirmed_fact"]
    confirmed_independent = []
    for claim in confirmed:
        groups: Set[str] = set()
        for link in evidence_by_claim.get(claim["id"], []):
            source = sources.get(link["source_id"])
            if (
                link["relation"] == "supports"
                and source
                and source["provenance_status"] == "matched"
            ):
                groups.add(source["independence_group"])
        if len(groups) >= 2:
            confirmed_independent.append(claim)

    unsourced_attribution = 0
    for claim in claims:
        if claim["classification"] not in {"party_statement", "commentary"}:
            continue
        if not any(
            link["relation"] == "attributes"
            for link in evidence_by_claim.get(claim["id"], [])
        ):
            unsourced_attribution += 1

    duplicate_count = sum(
        source["independence_status"] == "duplicate" for source in sources.values()
    )
    syndicated_count = sum(
        source["independence_status"] == "syndicated" for source in sources.values()
    )
    provenance_matched = sum(
        source["provenance_status"] == "matched" for source in sources.values()
    )

    summary = {
        "claim_count": claim_count,
        "sourced_claim_count": sourced_claim_count,
        "claim_source_coverage": _ratio(sourced_claim_count, claim_count),
        "high_risk_claim_count": len(high_risk),
        "high_risk_checked_count": len(high_risk_checked),
        "high_risk_fact_check_coverage": _ratio(len(high_risk_checked), len(high_risk)),
        "confirmed_fact_count": len(confirmed),
        "confirmed_fact_independent_count": len(confirmed_independent),
        "confirmed_fact_independent_coverage": _ratio(
            len(confirmed_independent), len(confirmed)
        ),
        "source_type_diversity_count": len(
            {source["source_type"] for source in sources.values()}
        ),
        "duplicate_source_count": duplicate_count,
        "syndicated_source_count": syndicated_count,
        "unresolved_high_risk_count": len(unresolved_high_risk),
        "unsourced_attribution_count": unsourced_attribution,
        "provenance_matched_source_count": provenance_matched,
        "provenance_match_rate": _ratio(provenance_matched, len(sources)),
        "gate_status": "pass",
        "gate_reasons": [],
    }

    reasons: List[str] = []
    if summary["claim_source_coverage"] < 0.8:
        reasons.append("主张来源覆盖率低于 80%")
    if summary["high_risk_fact_check_coverage"] < 1.0:
        reasons.append("高风险主张独立核查覆盖率未达到 100%")
    if summary["confirmed_fact_independent_coverage"] < 0.8:
        reasons.append("confirmed_fact 独立来源覆盖率低于 80%")
    if summary["source_type_diversity_count"] < 2:
        reasons.append("来源类型少于两类")
    if summary["unresolved_high_risk_count"]:
        reasons.append("仍有未解决的高风险主张")
    if summary["unsourced_attribution_count"]:
        reasons.append("存在没有 attribution 证据的说法或评论")
    if summary["provenance_match_rate"] < 0.8:
        reasons.append("来源 provenance 匹配率低于 80%")
    if data["fact_check"]["status"] != "completed":
        reasons.append("独立 Fact Check 尚未完成")
    summary["gate_reasons"] = reasons
    summary["gate_status"] = "fail" if reasons else "pass"
    return summary


def apply_quality_gate(data: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(data)
    result["quality_summary"] = calculate_quality_summary(result)
    high_risk_ids = [
        claim["id"]
        for claim in result["claims"]
        if claim["risk_level"] in {"high", "critical"}
    ]
    result["approval_gate"]["high_risk_claim_ids"] = high_risk_ids
    result["approval_gate"]["requires_user_confirmation"] = True
    if result["quality_summary"]["gate_status"] == "pass":
        if result["approval_gate"]["status"] == "approved":
            result["status"] = "ready_for_script"
            result["approval_gate"]["ready_for_script"] = True
        else:
            result["status"] = "reviewed"
            result["approval_gate"]["status"] = "pending"
            result["approval_gate"]["ready_for_script"] = False
    else:
        result["status"] = "draft"
        result["approval_gate"]["status"] = "pending"
        result["approval_gate"]["ready_for_script"] = False
    return result


def approve_for_script(report: ResearchReport, confirmation: str) -> Dict[str, Any]:
    validate_report(report)
    if report.status != "reviewed" or report.quality_summary["gate_status"] != "pass":
        raise ReportValidationError("只有通过质量 Gate 的 reviewed 报告才能确认")
    clean_confirmation = confirmation.strip()
    if not clean_confirmation:
        raise ReportValidationError("进入未来 Script Agent 前必须保留用户确认")
    result = report.to_dict()
    result["approval_gate"].update(
        status="approved",
        user_confirmation=clean_confirmation,
        ready_for_script=True,
    )
    result["status"] = "ready_for_script"
    ResearchReport.from_dict(result)
    return result
