"""Compatibility migration from Research Report 0.1 to 0.2."""

import uuid
from copy import deepcopy
from typing import Any, Dict, List, Set

from .models import ResearchReport
from .quality import calculate_quality_summary
from .schema import _enum, _object, _string, _string_array
from .sources import normalize_report_sources
from .validation import ReportValidationError, validate_json_schema


V01_REPORT_JSON_SCHEMA = _object(
    {
        "schema_version": _enum(["0.1"]),
        "topic": _string(),
        "research_question": _string(),
        "generated_at": _string(),
        "scope_summary": _string(),
        "executive_summary": _string(),
        "sources": {
            "type": "array",
            "items": _object(
                {
                    "id": _string(),
                    "title": _string(),
                    "url": _string(),
                    "publisher": _string(),
                    "published_at": _string(allow_empty=True),
                    "accessed_at": _string(),
                    "source_type": _enum(
                        [
                            "official",
                            "primary",
                            "media",
                            "academic",
                            "expert",
                            "creator",
                            "social",
                            "other",
                        ]
                    ),
                    "stance_summary": _string(),
                    "credibility_notes": _string(),
                }
            ),
        },
        "claims": {
            "type": "array",
            "items": _object(
                {
                    "id": _string(),
                    "claim": _string(),
                    "classification": _enum(
                        [
                            "confirmed_fact",
                            "media_report",
                            "party_statement",
                            "commentary",
                            "unverified",
                        ]
                    ),
                    "confidence": _enum(["high", "medium", "low"]),
                    "source_ids": _string_array(),
                    "notes": _string(allow_empty=True),
                }
            ),
        },
        "timeline": {
            "type": "array",
            "items": _object(
                {
                    "date": _string(),
                    "event": _string(),
                    "claim_ids": _string_array(),
                    "source_ids": _string_array(),
                }
            ),
        },
        "perspectives": {
            "type": "array",
            "items": _object(
                {
                    "id": _string(),
                    "actor": _string(),
                    "position": _string(),
                    "reasoning": _string(),
                    "source_ids": _string_array(),
                    "category": _enum(["party", "media", "expert", "creator", "public", "other"]),
                }
            ),
        },
        "conflicts": {
            "type": "array",
            "items": _object(
                {
                    "question": _string(),
                    "side_a": _string(),
                    "side_b": _string(),
                    "evidence_state": _string(),
                    "source_ids": _string_array(),
                }
            ),
        },
        "open_questions": {
            "type": "array",
            "items": _object(
                {
                    "question": _string(),
                    "why_it_matters": _string(),
                    "suggested_next_step": _string(),
                }
            ),
        },
        "angles": {
            "type": "array",
            "items": _object(
                {
                    "title": _string(),
                    "core_question": _string(),
                    "why_now": _string(),
                    "audience_value": _string(),
                    "risks": _string(),
                    "required_claim_ids": _string_array(),
                }
            ),
        },
        "fact_check_notes": {
            "type": "array",
            "items": _object(
                {
                    "claim_id": _string(),
                    "status": _enum(
                        ["verified", "partially_verified", "unverified", "disputed"]
                    ),
                    "explanation": _string(),
                }
            ),
        },
        "limitations": _string_array(),
        "handoff_to_script_agent": _object(
            {
                "recommended_angle": _string(),
                "central_tension": _string(),
                "must_keep_claim_ids": _string_array(),
                "avoid_claims": _string_array(),
                "follow_up_research": _string_array(),
            }
        ),
    }
)


def _unique_ids(items: List[Dict[str, Any]], label: str) -> Set[str]:
    values = [item["id"] for item in items]
    if len(values) != len(set(values)):
        raise ReportValidationError(f"V0.1 {label} 出现重复 ID")
    return set(values)


def _check_v01_references(data: Dict[str, Any]) -> None:
    source_ids = _unique_ids(data["sources"], "sources")
    claim_ids = _unique_ids(data["claims"], "claims")
    _unique_ids(data["perspectives"], "perspectives")
    for claim in data["claims"]:
        for source_id in claim["source_ids"]:
            if source_id not in source_ids:
                raise ReportValidationError(f"V0.1 claim {claim['id']} 引用了不存在的来源：{source_id}")
    for collection, claim_field, source_field in (
        (data["timeline"], "claim_ids", "source_ids"),
        (data["perspectives"], None, "source_ids"),
        (data["conflicts"], None, "source_ids"),
    ):
        for item in collection:
            if claim_field:
                for claim_id in item[claim_field]:
                    if claim_id not in claim_ids:
                        raise ReportValidationError(f"V0.1 引用了不存在的 claim：{claim_id}")
            for source_id in item[source_field]:
                if source_id not in source_ids:
                    raise ReportValidationError(f"V0.1 引用了不存在的 source：{source_id}")
    for angle in data["angles"]:
        for claim_id in angle["required_claim_ids"]:
            if claim_id not in claim_ids:
                raise ReportValidationError(f"V0.1 angle 引用了不存在的 claim：{claim_id}")


def _risk_defaults(classification: str) -> Dict[str, Any]:
    if classification == "party_statement":
        return {"risk_level": "medium", "risk_factors": ["attribution", "responsibility"]}
    if classification == "commentary":
        return {"risk_level": "medium", "risk_factors": ["attribution"]}
    if classification == "unverified":
        return {"risk_level": "medium", "risk_factors": ["contested"]}
    return {"risk_level": "medium", "risk_factors": []}


def migrate_v01_to_v02(data: Dict[str, Any]) -> Dict[str, Any]:
    validate_json_schema(data, V01_REPORT_JSON_SCHEMA, "v0.1_report")
    _check_v01_references(data)
    original = deepcopy(data)
    report_id = "RPT-" + uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"deep-talk-studio:{original['topic']}:{original['generated_at']}",
    ).hex[:16]

    sources = []
    for source in original["sources"]:
        migrated = deepcopy(source)
        migrated.update(
            normalized_url=source["url"],
            inspection_method="not_inspected",
            provenance_method="migration",
            provenance_status="unmatched",
            provenance_refs=[],
            independence_group="pending",
            independence_status="unknown",
            syndication_of="",
        )
        sources.append(migrated)

    claims = []
    evidence_links = []
    evidence_lookup: Dict[str, List[str]] = {}
    next_evidence = 1
    for old_claim in original["claims"]:
        classification = old_claim["classification"]
        risk = _risk_defaults(classification)
        claim = {
            "id": old_claim["id"],
            "claim": old_claim["claim"],
            "classification": classification,
            "confidence": old_claim["confidence"],
            "importance": "key" if classification in {"confirmed_fact", "media_report", "party_statement"} else "background",
            "risk_level": risk["risk_level"],
            "risk_factors": risk["risk_factors"],
            "verification_status": "not_checked",
            "notes": f"{old_claim['notes']} 从 V0.1 迁移，尚未完成独立复核。".strip(),
        }
        claims.append(claim)
        for source_id in old_claim["source_ids"]:
            relation = (
                "attributes"
                if classification in {"party_statement", "commentary"}
                else "supports"
                if classification in {"confirmed_fact", "media_report"}
                else "context"
            )
            evidence_id = f"E{next_evidence}"
            next_evidence += 1
            evidence_links.append(
                {
                    "id": evidence_id,
                    "claim_id": old_claim["id"],
                    "source_id": source_id,
                    "relation": relation,
                    "evidence_summary": "从 V0.1 claim.source_ids 迁移，需重新打开来源核查。",
                    "evidence_locator": "V0.1 未保存 locator",
                    "independence_group": "pending",
                    "verification_notes": "迁移不等于独立事实核查。",
                    "verified_in_review": False,
                }
            )
            evidence_lookup.setdefault(old_claim["id"], []).append(evidence_id)

    source_claims: Dict[str, List[str]] = {}
    source_evidence: Dict[str, List[str]] = {}
    for link in evidence_links:
        source_claims.setdefault(link["source_id"], []).append(link["claim_id"])
        source_evidence.setdefault(link["source_id"], []).append(link["id"])

    def refs_for_sources(source_ids: List[str]) -> Dict[str, List[str]]:
        claim_values: List[str] = []
        evidence_values: List[str] = []
        for source_id in source_ids:
            claim_values.extend(source_claims.get(source_id, []))
            evidence_values.extend(source_evidence.get(source_id, []))
        return {
            "claim_ids": list(dict.fromkeys(claim_values)),
            "evidence_link_ids": list(dict.fromkeys(evidence_values)),
        }

    timeline = []
    for item in original["timeline"]:
        evidence_ids: List[str] = []
        for claim_id in item["claim_ids"]:
            evidence_ids.extend(evidence_lookup.get(claim_id, []))
        timeline.append(
            {
                "date": item["date"],
                "event": item["event"],
                "claim_ids": item["claim_ids"],
                "evidence_link_ids": list(dict.fromkeys(evidence_ids)),
            }
        )

    perspectives = []
    for item in original["perspectives"]:
        refs = refs_for_sources(item["source_ids"])
        perspectives.append(
            {
                "id": item["id"],
                "actor": item["actor"],
                "position": item["position"],
                "reasoning": item["reasoning"],
                "claim_ids": refs["claim_ids"],
                "evidence_link_ids": refs["evidence_link_ids"],
                "category": item["category"],
            }
        )

    conflicts = []
    for item in original["conflicts"]:
        refs = refs_for_sources(item["source_ids"])
        conflicts.append(
            {
                "question": item["question"],
                "side_a": item["side_a"],
                "side_b": item["side_b"],
                "evidence_state": item["evidence_state"],
                "claim_ids": refs["claim_ids"],
                "evidence_link_ids": refs["evidence_link_ids"],
            }
        )

    result = {
        "schema_version": "0.2",
        "report_id": report_id,
        "revision": 1,
        "previous_revision": 0,
        "created_at": original["generated_at"],
        "generated_at": original["generated_at"],
        "research_mode": "migration",
        "status": "draft",
        "change_summary": "从 Research Report 0.1 确定性迁移到 0.2；所有来源需重新核查。",
        "corrections": [],
        "topic": original["topic"],
        "research_question": original["research_question"],
        "scope_summary": original["scope_summary"],
        "executive_summary": original["executive_summary"],
        "sources": sources,
        "claims": claims,
        "evidence_links": evidence_links,
        "timeline": timeline,
        "perspectives": perspectives,
        "conflicts": conflicts,
        "open_questions": original["open_questions"],
        "angles": original["angles"],
        "fact_check": {
            "review_id": "",
            "reviewed_at": "",
            "status": "not_run",
            "checked_claim_ids": [],
            "unresolved_claim_ids": [],
        },
        "quality_summary": {},
        "limitations": original["limitations"]
        + ["V0.1 内嵌 fact_check_notes 不视为独立事实核查。"],
        "approval_gate": {
            "status": "pending",
            "requires_user_confirmation": True,
            "high_risk_claim_ids": [],
            "user_confirmation": "",
            "ready_for_script": False,
        },
        "handoff_to_script_agent": original["handoff_to_script_agent"],
    }
    result = normalize_report_sources(result)
    result["quality_summary"] = calculate_quality_summary(result)
    ResearchReport.from_dict(result)
    return result


def load_compatible_report(data: Dict[str, Any]) -> ResearchReport:
    if not isinstance(data, dict):
        raise ReportValidationError("Research Report 必须是 JSON 对象")
    if data.get("schema_version") == "0.1":
        return ResearchReport.from_dict(migrate_v01_to_v02(data))
    return ResearchReport.from_dict(data)
