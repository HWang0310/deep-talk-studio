"""Strict validation for the frozen Visual Asset Plugin Contract V1."""

from __future__ import annotations

from typing import Any, Mapping


CONTRACT_VERSION = "visual-asset-plugin-contract/1"
SUITABILITY_OPERATION_STATUSES = frozenset({"COMPLETED", "FAILED", "UNAVAILABLE"})
SUITABILITY_STATUSES = frozenset({"SUITABLE", "BORDERLINE", "ABSTAIN"})
GENERATION_OPERATION_STATUSES = frozenset({"COMPLETED", "FAILED", "BLOCKED", "UNAVAILABLE"})
CANDIDATE_STATUSES = frozenset({"READY", "QA_REJECTED"})
ARTIFACT_ROLES = frozenset({"PRIMARY_MEDIA", "PREVIEW", "MANIFEST", "QA_REPORT"})


class VisualAssetPluginContractError(ValueError):
    """A deterministic error for malformed Plugin Contract V1 data."""


def validate_suitability_request(value: Any) -> None:
    data = _mapping(value, "suitability request")
    _only_fields(data, {"contract_version", "request_id", "opportunity"}, "suitability request")
    _required_fields(data, {"contract_version", "request_id", "opportunity"}, "suitability request")
    _validate_contract_version(data["contract_version"])
    _identifier(data["request_id"], "request_id")
    _validate_opportunity(data["opportunity"])


def validate_generation_request(value: Any) -> None:
    data = _mapping(value, "generation request")
    _only_fields(data, {"contract_version", "request_id", "proposal_id", "opportunity"}, "generation request")
    _required_fields(data, {"contract_version", "request_id", "proposal_id", "opportunity"}, "generation request")
    _validate_contract_version(data["contract_version"])
    _identifier(data["request_id"], "request_id")
    _identifier(data["proposal_id"], "proposal_id")
    _validate_opportunity(data["opportunity"])


def validate_suitability_response(value: Any) -> None:
    data = _mapping(value, "suitability response")
    allowed = {
        "contract_version", "request_id", "opportunity_id", "plugin_id", "plugin_version",
        "proposal_id", "operation_status", "suitability", "reason", "problem",
    }
    _only_fields(data, allowed, "suitability response")
    _required_fields(
        data,
        {"contract_version", "request_id", "opportunity_id", "plugin_id", "plugin_version", "operation_status"},
        "suitability response",
    )
    _validate_common_response(data)
    status = _enum(data["operation_status"], SUITABILITY_OPERATION_STATUSES, "operation_status")
    completed_fields = {"proposal_id", "suitability", "reason"}
    if status == "COMPLETED":
        _required_fields(data, completed_fields, "COMPLETED suitability response")
        _forbid_fields(data, {"problem"}, "COMPLETED suitability response")
        _identifier(data["proposal_id"], "proposal_id")
        _enum(data["suitability"], SUITABILITY_STATUSES, "suitability")
        _text(data["reason"], "reason")
    else:
        _required_fields(data, {"problem"}, f"{status} suitability response")
        _forbid_fields(data, completed_fields, f"{status} suitability response")
        _validate_problem(data["problem"])


def validate_generation_result(value: Any, opportunity: Mapping[str, Any]) -> None:
    data = _mapping(value, "generation result")
    allowed = {
        "contract_version", "request_id", "opportunity_id", "proposal_id", "plugin_id",
        "plugin_version", "operation_status", "candidate", "problem",
    }
    _only_fields(data, allowed, "generation result")
    _required_fields(
        data,
        {"contract_version", "request_id", "opportunity_id", "proposal_id", "plugin_id", "plugin_version", "operation_status"},
        "generation result",
    )
    _validate_common_response(data)
    _identifier(data["proposal_id"], "proposal_id")
    status = _enum(data["operation_status"], GENERATION_OPERATION_STATUSES, "operation_status")
    if status == "COMPLETED":
        _required_fields(data, {"candidate"}, "COMPLETED generation result")
        _forbid_fields(data, {"problem"}, "COMPLETED generation result")
        _validate_candidate(data["candidate"], opportunity)
    else:
        _required_fields(data, {"problem"}, f"{status} generation result")
        _forbid_fields(data, {"candidate"}, f"{status} generation result")
        _validate_problem(data["problem"])


def _validate_common_response(data: Mapping[str, Any]) -> None:
    _validate_contract_version(data["contract_version"])
    for field in ("request_id", "opportunity_id", "plugin_id", "plugin_version"):
        _identifier(data[field], field)


def _validate_opportunity(value: Any) -> None:
    data = _mapping(value, "opportunity")
    allowed = {
        "opportunity_id", "spoken_semantics", "visual_purpose", "a_roll_window",
        "target_duration_ms", "language", "canvas", "semantic_context", "factual_context", "plugin_context",
    }
    _only_fields(data, allowed, "opportunity")
    _required_fields(
        data,
        {"opportunity_id", "spoken_semantics", "visual_purpose", "a_roll_window", "target_duration_ms", "language", "canvas"},
        "opportunity",
    )
    _identifier(data["opportunity_id"], "opportunity_id")
    for field in ("spoken_semantics", "visual_purpose", "language"):
        _text(data[field], f"opportunity.{field}")
    _positive_int(data["target_duration_ms"], "opportunity.target_duration_ms")
    _validate_window(data["a_roll_window"], "a_roll_window")
    canvas = _mapping(data["canvas"], "opportunity.canvas")
    _only_fields(canvas, {"width", "height"}, "opportunity.canvas")
    _required_fields(canvas, {"width", "height"}, "opportunity.canvas")
    _positive_int(canvas["width"], "opportunity.canvas.width")
    _positive_int(canvas["height"], "opportunity.canvas.height")
    if "semantic_context" in data:
        _text(data["semantic_context"], "opportunity.semantic_context")
    if "factual_context" in data and not isinstance(data["factual_context"], list):
        raise VisualAssetPluginContractError("opportunity.factual_context 必须是列表")


def _validate_candidate(value: Any, opportunity: Mapping[str, Any]) -> None:
    data = _mapping(value, "candidate")
    allowed = {
        "candidate_id", "asset_family", "candidate_status", "duration_ms", "suggested_placement",
        "artifacts", "qa", "provenance", "plugin_metadata",
    }
    _only_fields(data, allowed, "candidate")
    _required_fields(data, {"candidate_id", "asset_family", "candidate_status"}, "candidate")
    _identifier(data["candidate_id"], "candidate_id")
    _text(data["asset_family"], "asset_family")
    status = _enum(data["candidate_status"], CANDIDATE_STATUSES, "candidate_status")
    if "duration_ms" in data:
        _positive_int(data["duration_ms"], "duration_ms")
    if "suggested_placement" in data:
        _validate_placement(data["suggested_placement"], opportunity)
    if "artifacts" in data:
        _validate_artifacts(data["artifacts"])
    if "provenance" in data:
        _mapping(data["provenance"], "provenance")
    if status == "READY":
        _required_fields(data, {"duration_ms", "suggested_placement", "artifacts", "qa", "provenance"}, "READY candidate")
        if not any(item["role"] == "PRIMARY_MEDIA" for item in data["artifacts"]):
            raise VisualAssetPluginContractError("READY candidate 必须包含 PRIMARY_MEDIA artifact")
        _validate_qa(data["qa"], "PASSED")
        if not data["provenance"]:
            raise VisualAssetPluginContractError("provenance 不能为空")
    else:
        _required_fields(data, {"qa"}, "QA_REJECTED candidate")
        _validate_qa(data["qa"], "FAILED")


def _validate_artifacts(value: Any) -> None:
    if not isinstance(value, list):
        raise VisualAssetPluginContractError("artifacts 必须是列表")
    for index, raw in enumerate(value):
        artifact = _mapping(raw, f"artifacts[{index}]")
        allowed = {"role", "uri", "media_type", "sha256", "duration_ms", "metadata"}
        _only_fields(artifact, allowed, f"artifacts[{index}]")
        _required_fields(artifact, {"role", "uri"}, f"artifacts[{index}]")
        _enum(artifact["role"], ARTIFACT_ROLES, f"artifacts[{index}].role")
        _text(artifact["uri"], f"artifacts[{index}].uri")
        if "media_type" in artifact:
            _text(artifact["media_type"], f"artifacts[{index}].media_type")
        if "sha256" in artifact:
            _text(artifact["sha256"], f"artifacts[{index}].sha256")
        if "duration_ms" in artifact:
            _positive_int(artifact["duration_ms"], f"artifacts[{index}].duration_ms")


def _validate_qa(value: Any, expected_status: str) -> None:
    data = _mapping(value, "qa")
    if "status" not in data:
        raise VisualAssetPluginContractError("qa.status 缺少必填字段")
    if data["status"] != expected_status:
        raise VisualAssetPluginContractError(f"qa.status 必须是 {expected_status}")


def _validate_placement(value: Any, opportunity: Mapping[str, Any]) -> None:
    placement = _validate_window(value, "suggested_placement")
    _validate_opportunity(opportunity)
    window = opportunity["a_roll_window"]
    if placement["start_ms"] < window["start_ms"] or placement["end_ms"] > window["end_ms"]:
        raise VisualAssetPluginContractError("suggested_placement 必须位于 a_roll_window 内")


def _validate_window(value: Any, field: str) -> Mapping[str, int]:
    data = _mapping(value, field)
    _only_fields(data, {"start_ms", "end_ms"}, field)
    _required_fields(data, {"start_ms", "end_ms"}, field)
    _nonnegative_int(data["start_ms"], f"{field}.start_ms")
    _nonnegative_int(data["end_ms"], f"{field}.end_ms")
    if data["start_ms"] >= data["end_ms"]:
        raise VisualAssetPluginContractError(f"{field} 必须满足 start_ms < end_ms")
    return data


def _validate_problem(value: Any) -> None:
    data = _mapping(value, "problem")
    _only_fields(data, {"code", "message", "retryability"}, "problem")
    _required_fields(data, {"code", "message"}, "problem")
    _text(data["code"], "problem.code")
    _text(data["message"], "problem.message")
    if "retryability" in data and not isinstance(data["retryability"], bool):
        raise VisualAssetPluginContractError("problem.retryability 必须是布尔值")


def _validate_contract_version(value: Any) -> None:
    if value != CONTRACT_VERSION:
        raise VisualAssetPluginContractError(f"contract_version 必须是 {CONTRACT_VERSION}")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VisualAssetPluginContractError(f"{field} 必须是 JSON 对象")
    return value


def _required_fields(data: Mapping[str, Any], fields: set[str], field: str) -> None:
    for name in sorted(fields):
        if name not in data:
            raise VisualAssetPluginContractError(f"{field}.{name} 缺少必填字段")


def _forbid_fields(data: Mapping[str, Any], fields: set[str], field: str) -> None:
    present = sorted(fields.intersection(data))
    if present:
        raise VisualAssetPluginContractError(f"{field} 不能包含字段：{', '.join(present)}")


def _only_fields(data: Mapping[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(data).difference(allowed))
    if unknown:
        raise VisualAssetPluginContractError(f"{field} 包含未知字段：{', '.join(unknown)}")


def _identifier(value: Any, field: str) -> str:
    return _text(value, field)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VisualAssetPluginContractError(f"{field} 必须是非空文本")
    return value


def _positive_int(value: Any, field: str) -> int:
    _nonnegative_int(value, field)
    if value <= 0:
        raise VisualAssetPluginContractError(f"{field} 必须是正整数")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise VisualAssetPluginContractError(f"{field} 必须是非负整数")
    return value


def _enum(value: Any, allowed: frozenset[str], field: str) -> str:
    if value not in allowed:
        raise VisualAssetPluginContractError(
            f"{field} 的值无效：{value!r}；允许值为 {', '.join(sorted(allowed))}"
        )
    return value
