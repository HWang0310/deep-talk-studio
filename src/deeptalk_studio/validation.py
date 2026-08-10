"""Deterministic schema and cross-reference validation."""

import json
from typing import Any, Dict, Iterable, Set
from urllib.parse import urlparse

from .schema import REPORT_JSON_SCHEMA


class ReportValidationError(ValueError):
    """A user-readable Research Report contract error."""


def _child_path(path: str, key: str) -> str:
    return key if path == "$" else f"{path}.{key}"


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return False


def _type_label(expected: str) -> str:
    return {
        "object": "JSON 对象",
        "array": "列表",
        "string": "文本",
        "integer": "整数",
        "number": "数字",
        "boolean": "布尔值",
    }.get(expected, expected)


def validate_json_schema(value: Any, schema: Dict[str, Any], path: str = "$") -> None:
    """Execute the JSON Schema subset used by this project.

    The implementation intentionally supports every keyword emitted by schema.py;
    unsupported schema keywords fail closed rather than being silently ignored.
    """

    supported = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "minLength",
        "minItems",
        "uniqueItems",
        "minimum",
        "maximum",
    }
    unknown_keywords = set(schema) - supported
    if unknown_keywords:
        raise RuntimeError("校验器不支持 Schema 关键字：" + ", ".join(sorted(unknown_keywords)))

    expected = schema.get("type")
    if expected and not _type_matches(value, expected):
        field = "Research Report" if path == "$" else path
        raise ReportValidationError(f"{field} 必须是{_type_label(expected)}")

    if "enum" in schema and value not in schema["enum"]:
        raise ReportValidationError(
            f"{path} 的值无效：{value!r}；允许值为 {', '.join(schema['enum'])}"
        )

    if expected == "string" and len(value) < schema.get("minLength", 0):
        raise ReportValidationError(f"{path} 不能为空")

    if expected in {"integer", "number"}:
        if "minimum" in schema and value < schema["minimum"]:
            raise ReportValidationError(f"{path} 不能小于 {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ReportValidationError(f"{path} 不能大于 {schema['maximum']}")

    if expected == "array":
        if len(value) < schema.get("minItems", 0):
            raise ReportValidationError(f"{path} 至少需要 {schema['minItems']} 项")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ReportValidationError(f"{path} 不能包含重复项")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_json_schema(item, item_schema, f"{path}[{index}]" if path != "$" else f"[{index}]")

    if expected == "object":
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                raise ReportValidationError(f"{_child_path(path, key)} 缺少必填字段")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    raise ReportValidationError(f"{_child_path(path, key)} 是未知字段")
        for key, child_schema in properties.items():
            if key in value:
                validate_json_schema(value[key], child_schema, _child_path(path, key))


def _unique_ids(items: Iterable[Dict[str, Any]], field: str) -> Set[str]:
    seen: Set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            raise ReportValidationError(f"{field} 出现重复 ID：{item_id}")
        seen.add(item_id)
    return seen


def _check_refs(refs: Iterable[str], known: Set[str], field: str) -> None:
    for ref in refs:
        if ref not in known:
            raise ReportValidationError(f"{field} 引用了不存在的 ID：{ref}")


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_report(report: Any) -> None:
    data = report.data if hasattr(report, "data") else report
    validate_json_schema(data, REPORT_JSON_SCHEMA)

    source_ids = _unique_ids(data["sources"], "sources")
    claim_ids = _unique_ids(data["claims"], "claims")
    evidence_ids = _unique_ids(data["evidence_links"], "evidence_links")
    _unique_ids(data["perspectives"], "perspectives")

    sources = {source["id"]: source for source in data["sources"]}
    for source in data["sources"]:
        if not _valid_http_url(source["url"]) or not _valid_http_url(source["normalized_url"]):
            raise ReportValidationError(
                f"source {source['id']} 的 URL 必须是有效 HTTP(S) 地址"
            )
        if source["provenance_status"] == "matched" and not source["provenance_refs"]:
            raise ReportValidationError(
                f"source {source['id']} 标记为 matched 时必须保留 provenance_refs"
            )
        if source["syndication_of"]:
            if source["syndication_of"] not in source_ids:
                raise ReportValidationError(
                    f"source {source['id']}.syndication_of 引用了不存在的 ID：{source['syndication_of']}"
                )
            if source["syndication_of"] == source["id"]:
                raise ReportValidationError(f"source {source['id']} 不能转载自己")

    support_by_claim = {claim_id: 0 for claim_id in claim_ids}
    for link in data["evidence_links"]:
        if link["claim_id"] not in claim_ids:
            raise ReportValidationError(
                f"evidence {link['id']}.claim_id 引用了不存在的 ID：{link['claim_id']}"
            )
        if link["source_id"] not in source_ids:
            raise ReportValidationError(
                f"evidence {link['id']}.source_id 引用了不存在的 ID：{link['source_id']}"
            )
        if link["independence_group"] != sources[link["source_id"]]["independence_group"]:
            raise ReportValidationError(
                f"evidence {link['id']}.independence_group 与来源不一致"
            )
        if link["relation"] == "supports":
            support_by_claim[link["claim_id"]] += 1

    for claim in data["claims"]:
        if claim["classification"] == "confirmed_fact" and not support_by_claim[claim["id"]]:
            raise ReportValidationError(
                f"confirmed_fact {claim['id']} 必须至少有一个 supports Evidence Link"
            )

    for index, item in enumerate(data["timeline"]):
        _check_refs(item["claim_ids"], claim_ids, f"timeline[{index}].claim_ids")
        _check_refs(
            item["evidence_link_ids"], evidence_ids, f"timeline[{index}].evidence_link_ids"
        )
    for item in data["perspectives"]:
        _check_refs(item["claim_ids"], claim_ids, f"perspective {item['id']}.claim_ids")
        _check_refs(
            item["evidence_link_ids"], evidence_ids, f"perspective {item['id']}.evidence_link_ids"
        )
    for index, item in enumerate(data["conflicts"]):
        _check_refs(item["claim_ids"], claim_ids, f"conflicts[{index}].claim_ids")
        _check_refs(
            item["evidence_link_ids"], evidence_ids, f"conflicts[{index}].evidence_link_ids"
        )
    for index, item in enumerate(data["angles"]):
        _check_refs(item["required_claim_ids"], claim_ids, f"angles[{index}].required_claim_ids")
    for index, correction in enumerate(data["corrections"]):
        _check_refs([correction["claim_id"]], claim_ids, f"corrections[{index}].claim_id")
        _check_refs(correction["source_ids"], source_ids, f"corrections[{index}].source_ids")

    fact_check = data["fact_check"]
    _check_refs(fact_check["checked_claim_ids"], claim_ids, "fact_check.checked_claim_ids")
    _check_refs(fact_check["unresolved_claim_ids"], claim_ids, "fact_check.unresolved_claim_ids")
    checked_claim_ids = set(fact_check["checked_claim_ids"])
    expected_unresolved = {
        claim["id"]
        for claim in data["claims"]
        if claim["id"] in checked_claim_ids and claim["verification_status"] != "verified"
    }
    if set(fact_check["unresolved_claim_ids"]) != expected_unresolved:
        raise ReportValidationError(
            "fact_check.unresolved_claim_ids 与已核查 claim 的状态不一致"
        )
    approval = data["approval_gate"]
    _check_refs(approval["high_risk_claim_ids"], claim_ids, "approval_gate.high_risk_claim_ids")
    expected_high_risk = {
        claim["id"]
        for claim in data["claims"]
        if claim["risk_level"] in {"high", "critical"}
    }
    if set(approval["high_risk_claim_ids"]) != expected_high_risk:
        raise ReportValidationError(
            "approval_gate 必须向用户完整暴露所有高风险 claim"
        )
    if not approval["requires_user_confirmation"]:
        raise ReportValidationError("进入未来 Script Agent 前必须要求用户确认")
    handoff = data["handoff_to_script_agent"]
    _check_refs(handoff["must_keep_claim_ids"], claim_ids, "handoff_to_script_agent.must_keep_claim_ids")

    revision = data["revision"]
    previous = data["previous_revision"]
    if (revision == 1 and previous != 0) or (revision > 1 and previous != revision - 1):
        raise ReportValidationError("previous_revision 必须指向紧邻的上一修订版")

    gate_status = data["quality_summary"]["gate_status"]
    if data["status"] in {"reviewed", "ready_for_script"}:
        if gate_status != "pass":
            raise ReportValidationError(f"{data['status']} 报告必须通过 quality gate")
        if fact_check["status"] != "completed":
            raise ReportValidationError(f"{data['status']} 报告必须完成独立 Fact Check")
    if approval["ready_for_script"]:
        if (
            approval["status"] != "approved"
            or data["status"] != "ready_for_script"
            or not approval["user_confirmation"].strip()
        ):
            raise ReportValidationError("ready_for_script 必须经过用户确认并使用同名报告状态")
    if data["status"] == "ready_for_script" and not approval["ready_for_script"]:
        raise ReportValidationError("ready_for_script 报告必须通过人工审批 Gate")
    if approval["status"] == "approved":
        if not approval["user_confirmation"].strip():
            raise ReportValidationError("approval_gate.approved 必须保留非空用户确认")
        if not approval["ready_for_script"] or data["status"] != "ready_for_script":
            raise ReportValidationError(
                "approval_gate.approved 必须与 ready_for_script 报告状态一致"
            )

    # Import lazily to keep schema/cross-reference validation independent from the
    # metric implementation while still preventing a model from inventing scores.
    from .quality import calculate_quality_summary

    calculated_quality = calculate_quality_summary(data)
    if data["quality_summary"] != calculated_quality:
        raise ReportValidationError(
            "quality_summary 与来源、Evidence Link 和 Fact Check 实际计算结果不一致"
        )
