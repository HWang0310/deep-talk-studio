"""Independent Material Review Artifact 0.5 and deterministic package gate."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .material_profile import MaterialValidationError
from .material_schema import MATERIAL_REVIEW_CHECK_NAMES
from .material_validation import (
    material_package_digest,
    validate_material_package_integrity,
)
from .models import MaterialPackage


class MaterialReviewError(MaterialValidationError):
    pass


BLOCKING_ISSUE_TYPES = {
    "missing_provenance", "claim_mismatch", "fabricated_source", "rights_misrepresented",
    "misleading_crop", "outdated_factual_visual", "wrong_identity",
    "generated_visual_unsupported_data", "ai_visual_as_real_evidence",
}

CHECK_ISSUE_TYPES = {
    "provenance_integrity": {"missing_provenance", "fabricated_source"},
    "claim_alignment": {"claim_mismatch"},
    "rights_reuse": {"rights_misrepresented", "permission_needed"},
    "crop_integrity": {"misleading_crop"},
    "freshness": {"outdated_factual_visual"},
    "identity_accuracy": {"wrong_identity"},
    "generated_visual_grounding": {"generated_visual_unsupported_data"},
    "ai_real_confusion": {"ai_visual_as_real_evidence"},
    "duplicate_control": {"near_duplicate"},
    "editorial_usefulness": {"low_usefulness"},
}


@dataclass(frozen=True)
class MaterialReviewResult:
    artifact: Dict[str, Any]
    package: MaterialPackage


def _canonical_issues(content: Mapping[str, Any], package: MaterialPackage) -> list:
    material_ids = {item["material_id"] for item in package.materials}
    visual_ids = {item["visual_id"] for item in package.generated_visuals}
    cue_ids = {item["cue_id"] for item in package.cue_sheet}
    result = []
    for index, raw in enumerate(content.get("issues", []), 1):
        expected = {
            "issue_type", "material_ids", "visual_ids", "cue_ids", "explanation", "suggested_fix"
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise MaterialReviewError("Material Review issue 字段不完整或包含未知字段")
        issue_type = raw["issue_type"]
        if issue_type not in set().union(*CHECK_ISSUE_TYPES.values()):
            raise MaterialReviewError(f"Material Review issue_type 无效：{issue_type}")
        if not set(raw["material_ids"]) <= material_ids:
            raise MaterialReviewError("Material Review 引用了不存在的 material_id")
        if not set(raw["visual_ids"]) <= visual_ids:
            raise MaterialReviewError("Material Review 引用了不存在的 visual_id")
        if not set(raw["cue_ids"]) <= cue_ids:
            raise MaterialReviewError("Material Review 引用了不存在的 cue_id")
        result.append({
            "issue_id": f"MI{index:03d}", **deepcopy(raw),
            "severity": "blocking" if issue_type in BLOCKING_ISSUE_TYPES else "advisory",
        })
    return result


def _validate_checks(content: Mapping[str, Any], issues: list) -> list:
    checks = deepcopy(content.get("checks"))
    if not isinstance(checks, list):
        raise MaterialReviewError("Material Review checks 必须是列表")
    names = []
    issue_types = {issue["issue_type"] for issue in issues}
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"check_name", "outcome", "reason"}:
            raise MaterialReviewError("Material Review check 字段无效")
        name = check["check_name"]
        if name not in MATERIAL_REVIEW_CHECK_NAMES or name in names:
            raise MaterialReviewError("Material Review checks 包含未知项或重复项")
        if check["outcome"] not in {"pass", "fail"} or not str(check["reason"]).strip():
            raise MaterialReviewError("Material Review check outcome 或 reason 无效")
        names.append(name)
        if check["outcome"] == "fail" and not (CHECK_ISSUE_TYPES[name] & issue_types):
            raise MaterialReviewError(f"Material Review {name}=fail 必须包含对应 issue")
    missing = [name for name in MATERIAL_REVIEW_CHECK_NAMES if name not in names]
    if missing:
        raise MaterialReviewError("Material Review 缺少必检项：" + "、".join(missing))
    return checks


def prepare_material_review(
    content: Dict[str, Any], package: MaterialPackage, script: Any, report: Any,
    profile: Mapping[str, Any], *, created_at: str, review_id: str,
    review_mode: str = "codex_skill",
) -> MaterialReviewResult:
    package = validate_material_package_integrity(package, script, report, profile)
    if review_mode not in {"codex_skill", "openai_api", "fixture"}:
        raise MaterialReviewError("review_mode 无效")
    issues = _canonical_issues(content, package)
    checks = _validate_checks(content, issues)
    data = package.to_dict()
    package_level_block = any(
        issue["severity"] == "blocking" and not issue["material_ids"] and not issue["visual_ids"]
        for issue in issues
    )
    blocked_materials = {
        item_id for issue in issues if issue["severity"] == "blocking" for item_id in issue["material_ids"]
    }
    blocked_visuals = {
        item_id for issue in issues if issue["severity"] == "blocking" for item_id in issue["visual_ids"]
    }
    for item in data["materials"]:
        if item["material_id"] in blocked_materials:
            item["eligibility_status"] = "rejected"
    for visual in data["generated_visuals"]:
        if visual["visual_id"] in blocked_visuals:
            visual["eligibility_status"] = "rejected"
    safe_count = sum(item["eligibility_status"] == "ready_to_use" for item in data["materials"])
    safe_count += sum(item["eligibility_status"] == "ready_to_use" for item in data["generated_visuals"])
    if package.research_update_required["required"]:
        final_status, gate = "research_update_required", "fail"
    elif package_level_block or safe_count == 0:
        final_status, gate = "blocked", "fail"
    elif issues:
        final_status, gate = "reviewed_with_warnings", "warnings"
    else:
        final_status, gate = "reviewed", "pass"
    artifact = {
        "artifact_version": "0.5", "review_id": review_id,
        "package_id": package.package_id, "package_revision": package.revision,
        "script_id": package.script_id, "script_revision": package.script_revision,
        "report_id": package.report_id, "report_revision": package.report_revision,
        "created_at": created_at, "review_mode": review_mode,
        "issues": issues, "checks": checks,
        "overall_notes": str(content.get("overall_notes", "")).strip(),
        "blocking_issue_count": sum(issue["severity"] == "blocking" for issue in issues),
        "gate_status": gate, "reviewed_package_digest": package.package_digest,
    }
    if not artifact["overall_notes"]:
        raise MaterialReviewError("Material Review overall_notes 不能为空")
    data.update(
        revision=package.revision + 1, previous_revision=package.revision,
        generated_at=created_at, status=final_status,
        review_state={
            "state": "reviewed", "review_id": review_id,
            "reviewed_from_revision": package.revision, "review_gate_status": gate,
            "reviewed_package_digest": package.package_digest,
        },
    )
    data["warnings"] = list(dict.fromkeys(data["warnings"] + [issue["explanation"] for issue in issues]))
    data["package_digest"] = material_package_digest(data)
    return MaterialReviewResult(artifact, MaterialPackage(data))


def validate_material_review_artifact(artifact: Mapping[str, Any], package: MaterialPackage) -> None:
    required = {
        "artifact_version", "review_id", "package_id", "package_revision", "script_id",
        "script_revision", "report_id", "report_revision", "created_at", "review_mode",
        "issues", "checks", "overall_notes", "blocking_issue_count", "gate_status",
        "reviewed_package_digest",
    }
    if not isinstance(artifact, dict) or set(artifact) != required:
        raise MaterialReviewError("Material Review Artifact 字段无效")
    if artifact["artifact_version"] != "0.5" or artifact["package_id"] != package.package_id:
        raise MaterialReviewError("Material Review Artifact binding 无效")
    if artifact["package_revision"] != package.previous_revision:
        raise MaterialReviewError("Material Review Artifact revision binding 无效")
    if artifact["review_id"] != package.review_state["review_id"]:
        raise MaterialReviewError("Material Review Artifact ID 与 package linkage 不一致")
    if (
        artifact["script_id"] != package.script_id
        or artifact["script_revision"] != package.script_revision
        or artifact["report_id"] != package.report_id
        or artifact["report_revision"] != package.report_revision
    ):
        raise MaterialReviewError("Material Review Artifact 的 Script / Research binding 无效")
    expected_ids = [f"MI{index:03d}" for index in range(1, len(artifact["issues"]) + 1)]
    if [issue.get("issue_id") for issue in artifact["issues"]] != expected_ids:
        raise MaterialReviewError("Material Review issue_id 必须由程序生成")
    for issue in artifact["issues"]:
        expected = "blocking" if issue["issue_type"] in BLOCKING_ISSUE_TYPES else "advisory"
        if issue.get("severity") != expected:
            raise MaterialReviewError("Material Review severity 与 issue_type 不一致")
    blocking = sum(issue["severity"] == "blocking" for issue in artifact["issues"])
    if artifact["blocking_issue_count"] != blocking:
        raise MaterialReviewError("Material Review blocking count 被篡改")
    if artifact["reviewed_package_digest"] != package.review_state["reviewed_package_digest"]:
        raise MaterialReviewError("Material Review digest 与 package linkage 不一致")
    expected_gate = {
        "reviewed": "pass", "reviewed_with_warnings": "warnings",
        "blocked": "fail", "research_update_required": "fail",
    }.get(package.status)
    if expected_gate and artifact["gate_status"] != expected_gate:
        raise MaterialReviewError("Material Review Gate 与 package status 不一致")
    _validate_checks(artifact, list(artifact["issues"]))
