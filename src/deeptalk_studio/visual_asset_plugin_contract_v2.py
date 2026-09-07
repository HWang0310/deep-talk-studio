"""Design-only compatibility surface: Visual Asset Plugin Contract V2 views.

This module is **not** a production protocol.  It exists so that Phase A can
express plugin-owned timing hints (``intrinsic_placement_hint``) separately
from Core-owned Placement Planner output (``final_placement``, Phase B+),
without touching the frozen ``visual-asset-plugin-contract/1`` runtime path.

Identity creation authority (per accepted V2 architecture §5.3):
  - ``opportunity_id``  — Studio/Core-created
  - ``request_id``      — Studio/Core-created, plugin echoes
  - ``proposal_id``     — **plugin-created** in Suitability Response
  - ``candidate_id``    — **plugin-created** in Generation Result
  - ``portfolio_id``    — Studio/Core-created

Core validates, persists, binds lineage, and audits all IDs, but Core does
**not** create ``proposal_id`` or ``candidate_id``.

Two compatibility surfaces exist in Phase A:
  - ``validate_v2_result_view``      — generation result envelope
  - ``validate_v2_suitability_view`` — suitability response envelope

Both accept COMPLETED and failure (FAILED / BLOCKED / UNAVAILABLE) statuses,
preserving raw V1 evidence without loss.
"""
from __future__ import annotations

from typing import Any, Mapping

CONTRACT_VERSION_V2 = "visual-asset-plugin-contract/2"

CANDIDATE_STATUSES_V2 = frozenset({"READY", "QA_REJECTED"})
ARTIFACT_ROLES_V2 = frozenset({"PRIMARY_MEDIA", "PREVIEW", "MANIFEST", "QA_REPORT"})
SUITABILITY_STATUSES_V2 = frozenset({"SUITABLE", "BORDERLINE", "ABSTAIN"})
FAILURE_OPERATION_STATUSES = frozenset({"FAILED", "BLOCKED", "UNAVAILABLE"})

# V2 result view fields (V1 envelope, contract_version bumped to /2).
_RESULT_FIELDS_V2 = frozenset(
    {
        "contract_version", "request_id", "opportunity_id", "proposal_id",
        "plugin_id", "plugin_version", "operation_status", "candidate",
        "problem",
    }
)

# V2 suitability view fields.
_SUITABILITY_FIELDS_V2 = frozenset(
    {
        "contract_version", "request_id", "opportunity_id", "plugin_id",
        "plugin_version", "operation_status", "proposal_id", "suitability",
        "reason", "problem",
    }
)

# Candidate fields inside the result view.  ``intrinsic_placement_hint`` is
# plugin-owned and optional for READY; ``final_placement`` is reserved for
# Phase B and is **not** allowed here.
_CANDIDATE_FIELDS_V2 = frozenset(
    {
        "candidate_id", "asset_family", "candidate_status", "duration_ms",
        "intrinsic_placement_hint", "artifacts", "qa", "provenance",
        "plugin_metadata",
    }
)

_RESULT_LINEAGE_FIELDS = (
    "request_id", "opportunity_id", "proposal_id", "plugin_id", "plugin_version",
)
_SUITABILITY_LINEAGE_FIELDS = (
    "request_id", "opportunity_id", "plugin_id", "plugin_version",
)


class VisualAssetPluginContractV2Error(ValueError):
    """A deterministic error for malformed V2 views."""


# ===========================================================================
# Generation result view
# ===========================================================================

def validate_v2_result_view(value: Any, opportunity: Mapping[str, Any]) -> None:
    """Validate an isolated V2 generation result view against an opportunity.

    Accepts COMPLETED (with candidate) and FAILED / BLOCKED / UNAVAILABLE
    (with problem, no candidate).  All lineage IDs are required.
    """
    data = _mapping(value, "result")
    _only_fields(data, _RESULT_FIELDS_V2, "result")
    if data.get("contract_version") != CONTRACT_VERSION_V2:
        raise VisualAssetPluginContractV2Error(
            f"contract_version 必须是 {CONTRACT_VERSION_V2}"
        )
    for field in _RESULT_LINEAGE_FIELDS:
        _required_fields(data, {field}, "result")
        _identifier(data[field], field)
    status = _required_enum(
        data, "operation_status",
        frozenset({"COMPLETED"}) | FAILURE_OPERATION_STATUSES,
        "operation_status",
    )
    if status == "COMPLETED":
        _required_fields(data, {"candidate"}, "COMPLETED result")
        _forbid_fields(data, {"problem"}, "COMPLETED result")
        _validate_candidate(data["candidate"], opportunity)
    else:
        _required_fields(data, {"problem"}, f"{status} result")
        _forbid_fields(data, {"candidate"}, f"{status} result")
        _validate_problem(data["problem"])


# ===========================================================================
# Suitability view
# ===========================================================================

def validate_v2_suitability_view(value: Any) -> None:
    """Validate an isolated V2 suitability response view.

    Accepts COMPLETED (with proposal_id / suitability / reason) and
    FAILED / UNAVAILABLE (with problem, no proposal/suitability fields).
    """
    data = _mapping(value, "suitability")
    _only_fields(data, _SUITABILITY_FIELDS_V2, "suitability")
    if data.get("contract_version") != CONTRACT_VERSION_V2:
        raise VisualAssetPluginContractV2Error(
            f"contract_version 必须是 {CONTRACT_VERSION_V2}"
        )
    for field in _SUITABILITY_LINEAGE_FIELDS:
        _required_fields(data, {field}, "suitability")
        _identifier(data[field], field)
    status = _required_enum(
        data, "operation_status",
        frozenset({"COMPLETED"}) | FAILURE_OPERATION_STATUSES,
        "operation_status",
    )
    if status == "COMPLETED":
        for field in ("proposal_id", "suitability", "reason"):
            _required_fields(data, {field}, "COMPLETED suitability")
        _forbid_fields(data, {"problem"}, "COMPLETED suitability")
        _identifier(data["proposal_id"], "proposal_id")
        _enum(data["suitability"], SUITABILITY_STATUSES_V2, "suitability")
        _text(data["reason"], "reason")
    else:
        _required_fields(data, {"problem"}, f"{status} suitability")
        _forbid_fields(
            data, {"proposal_id", "suitability", "reason"}, f"{status} suitability"
        )
        _validate_problem(data["problem"])


# ===========================================================================
# Candidate validation (shared)
# ===========================================================================

def _validate_candidate(value: Any, opportunity: Mapping[str, Any]) -> None:
    data = _mapping(value, "candidate")
    _only_fields(data, _CANDIDATE_FIELDS_V2, "candidate")
    _required_fields(data, {"candidate_id", "asset_family", "candidate_status"}, "candidate")
    _identifier(data["candidate_id"], "candidate_id")
    _text(data["asset_family"], "asset_family")
    status = _enum(data["candidate_status"], CANDIDATE_STATUSES_V2, "candidate_status")

    if "duration_ms" in data:
        _positive_int(data["duration_ms"], "duration_ms")
    if "intrinsic_placement_hint" in data:
        _validate_placement(data["intrinsic_placement_hint"], opportunity)
    if "artifacts" in data:
        _validate_artifacts(data["artifacts"])
    if "provenance" in data:
        _mapping(data["provenance"], "provenance")

    if status == "READY":
        _required_fields(
            data, {"duration_ms", "artifacts", "qa", "provenance"}, "READY candidate"
        )
        if not any(item["role"] == "PRIMARY_MEDIA" for item in data["artifacts"]):
            raise VisualAssetPluginContractV2Error(
                "READY candidate 必须包含 PRIMARY_MEDIA artifact"
            )
        _validate_qa(data["qa"], "PASSED")
        if not data["provenance"]:
            raise VisualAssetPluginContractV2Error("provenance 不能为空")
    else:
        _required_fields(data, {"qa"}, "QA_REJECTED candidate")
        _validate_qa(data["qa"], "FAILED")


def _validate_artifacts(value: Any) -> None:
    if not isinstance(value, list):
        raise VisualAssetPluginContractV2Error("artifacts 必须是列表")
    for index, raw in enumerate(value):
        artifact = _mapping(raw, f"artifacts[{index}]")
        allowed = {"role", "uri", "media_type", "sha256", "duration_ms", "metadata"}
        _only_fields(artifact, allowed, f"artifacts[{index}]")
        _required_fields(artifact, {"role", "uri"}, f"artifacts[{index}]")
        _enum(artifact["role"], ARTIFACT_ROLES_V2, f"artifacts[{index}].role")
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
        raise VisualAssetPluginContractV2Error("qa.status 缺少必填字段")
    if data["status"] != expected_status:
        raise VisualAssetPluginContractV2Error(f"qa.status 必须是 {expected_status}")


def _validate_placement(value: Any, opportunity: Mapping[str, Any]) -> None:
    placement = _validate_window(value, "intrinsic_placement_hint")
    _validate_opportunity(opportunity)
    window = opportunity["a_roll_window"]
    if placement["start_ms"] < window["start_ms"] or placement["end_ms"] > window["end_ms"]:
        raise VisualAssetPluginContractV2Error(
            "intrinsic_placement_hint 必须位于 a_roll_window 内"
        )


def _validate_problem(value: Any) -> None:
    data = _mapping(value, "problem")
    _only_fields(data, {"code", "message", "retryability"}, "problem")
    _required_fields(data, {"code", "message"}, "problem")
    _text(data["code"], "problem.code")
    _text(data["message"], "problem.message")
    if "retryability" in data and not isinstance(data["retryability"], bool):
        raise VisualAssetPluginContractV2Error("problem.retryability 必须是布尔值")


def _validate_opportunity(value: Any) -> None:
    data = _mapping(value, "opportunity")
    allowed = {
        "opportunity_id", "spoken_semantics", "visual_purpose", "a_roll_window",
        "target_duration_ms", "language", "canvas", "semantic_context",
        "factual_context", "plugin_context",
    }
    _only_fields(data, allowed, "opportunity")
    _required_fields(
        data,
        {"opportunity_id", "spoken_semantics", "visual_purpose", "a_roll_window",
         "target_duration_ms", "language", "canvas"},
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


def _validate_window(value: Any, field: str) -> Mapping[str, int]:
    data = _mapping(value, field)
    _only_fields(data, {"start_ms", "end_ms"}, field)
    _required_fields(data, {"start_ms", "end_ms"}, field)
    _nonnegative_int(data["start_ms"], f"{field}.start_ms")
    _nonnegative_int(data["end_ms"], f"{field}.end_ms")
    if data["start_ms"] >= data["end_ms"]:
        raise VisualAssetPluginContractV2Error(f"{field} 必须满足 start_ms < end_ms")
    return data


# ===========================================================================
# Helpers
# ===========================================================================

def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VisualAssetPluginContractV2Error(f"{field} 必须是 JSON 对象")
    return value


def _required_fields(data: Mapping[str, Any], fields: set[str], field: str) -> None:
    for name in sorted(fields):
        if name not in data:
            raise VisualAssetPluginContractV2Error(f"{field}.{name} 缺少必填字段")


def _forbid_fields(data: Mapping[str, Any], fields: set[str], field: str) -> None:
    present = sorted(fields.intersection(data))
    if present:
        raise VisualAssetPluginContractV2Error(f"{field} 不能包含字段：{', '.join(present)}")


def _only_fields(data: Mapping[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(data).difference(allowed))
    if unknown:
        raise VisualAssetPluginContractV2Error(
            f"{field} 包含未知字段：{', '.join(unknown)}"
        )


def _required_enum(
    data: Mapping[str, Any], key: str, allowed: frozenset[str], field: str
) -> str:
    if key not in data:
        raise VisualAssetPluginContractV2Error(f"{field} 缺少必填字段")
    value = data[key]
    if value not in allowed:
        raise VisualAssetPluginContractV2Error(
            f"{field} 的值无效：{value!r}；允许值为 {', '.join(sorted(allowed))}"
        )
    return value


def _identifier(value: Any, field: str) -> str:
    return _text(value, field)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VisualAssetPluginContractV2Error(f"{field} 必须是非空文本")
    return value


def _positive_int(value: Any, field: str) -> int:
    _nonnegative_int(value, field)
    if value <= 0:
        raise VisualAssetPluginContractV2Error(f"{field} 必须是正整数")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise VisualAssetPluginContractV2Error(f"{field} 必须是非负整数")
    return value


def _enum(value: Any, allowed: frozenset[str], field: str) -> str:
    if value not in allowed:
        raise VisualAssetPluginContractV2Error(
            f"{field} 的值无效：{value!r}；允许值为 {', '.join(sorted(allowed))}"
        )
    return value