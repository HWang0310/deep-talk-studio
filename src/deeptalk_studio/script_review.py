"""Independent Script Review Artifact 0.4 and code-owned review gate."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .models import ResearchReport, ScriptDraft
from .schema import (
    SCRIPT_REVIEW_CHECK_NAMES,
    SCRIPT_REVIEW_CONTENT_JSON_SCHEMA,
    SCRIPT_REVIEW_JSON_SCHEMA,
)
from .script_profile import ScriptValidationError
from .script_validation import validate_script_draft
from .validation import ReportValidationError, validate_json_schema


BLOCKING_ISSUE_TYPES = {
    "unsupported_fact",
    "attribution_error",
    "avoid_claim_usage",
    "unverified_as_fact",
    "high_risk_overclaim",
    "material_uncertainty_loss",
    "analysis_as_fact",
    "research_gap_filled",
    "perspective_distortion",
}


@dataclass(frozen=True)
class ScriptReviewResult:
    artifact: Dict[str, Any]
    script: ScriptDraft


def _schema(value: Any, schema: Dict[str, Any], path: str) -> None:
    try:
        validate_json_schema(value, schema, path)
    except ReportValidationError as exc:
        raise ScriptValidationError(str(exc)) from None


def _canonical_issues(content: Mapping[str, Any], script: ScriptDraft) -> list:
    issues = [deepcopy(issue) for issue in content["issues"]]
    explained = {
        claim_id
        for issue in issues
        if issue["issue_type"] == "must_keep_omission"
        for claim_id in issue["claim_ids"]
    }
    missing = [
        claim_id
        for claim_id in script.missing_must_keep_claim_ids
        if claim_id not in explained
    ]
    if missing:
        reasons = {
            item["claim_id"]: item["reason"]
            for item in script.must_keep_omission_reasons
        }
        explanation = "；".join(
            f"{claim_id}：{reasons.get(claim_id, '稿件未覆盖，且 Writer 未提供遗漏理由')}"
            for claim_id in missing
        )
        issues.append(
            {
                "issue_type": "must_keep_omission",
                "beat_ids": [],
                "claim_ids": missing,
                "explanation": explanation,
                "suggested_fix": "确认结构性遗漏是否合理；如不合理，下一修订版补回。",
            }
        )
    canonical = []
    for index, issue in enumerate(issues, 1):
        issue_type = issue["issue_type"]
        canonical.append(
            {
                "issue_id": f"SI{index:03d}",
                **issue,
                "severity": (
                    "blocking" if issue_type in BLOCKING_ISSUE_TYPES else "advisory"
                ),
            }
        )
    return canonical


def _derived_gate(issues: list) -> Dict[str, object]:
    blocking = sum(issue["severity"] == "blocking" for issue in issues)
    return {
        "blocking_issue_count": blocking,
        "gate_status": "fail" if blocking else "pass",
    }


def _reviewed_script_revision(
    script: ScriptDraft,
    report: ResearchReport,
    profile: Mapping[str, object],
    generated_at: str,
    gate_status: str,
) -> ScriptDraft:
    data = script.to_dict()
    data["previous_revision"] = script.revision
    data["revision"] = script.revision + 1
    data["generated_at"] = generated_at
    data["status"] = "reviewed" if gate_status == "pass" else "draft"
    data["change_summary"] = (
        "独立 Script Review 通过，生成 reviewed 稿件修订版。"
        if gate_status == "pass"
        else "独立 Script Review 发现阻断问题，保留 draft 状态。"
    )
    return ScriptDraft.from_dict(data, report, dict(profile))


def prepare_script_review(
    content: Dict[str, Any],
    report: ResearchReport,
    script: ScriptDraft,
    profile: Mapping[str, object],
    *,
    created_at: str,
    review_id: str,
    review_mode: str = "codex_skill",
) -> ScriptReviewResult:
    validate_script_draft(script, report, profile)
    _schema(content, SCRIPT_REVIEW_CONTENT_JSON_SCHEMA, "script_review_content")
    if review_mode not in {"codex_skill", "openai_api", "fixture"}:
        raise ScriptValidationError("review_mode 无效")
    issues = _canonical_issues(content, script)
    gate = _derived_gate(issues)
    artifact = {
        "artifact_version": "0.4",
        "review_id": review_id,
        "script_id": script.script_id,
        "script_revision": script.revision,
        "report_id": report.report_id,
        "report_revision": report.revision,
        "created_at": created_at,
        "review_mode": review_mode,
        "issues": issues,
        "checks": deepcopy(content["checks"]),
        "overall_notes": content["overall_notes"],
        **gate,
    }
    validate_script_review_artifact(artifact, report, script)
    reviewed = _reviewed_script_revision(
        script, report, profile, created_at, artifact["gate_status"]
    )
    return ScriptReviewResult(artifact=artifact, script=reviewed)


def validate_script_review_artifact(
    artifact: Any, report: ResearchReport, script: ScriptDraft
) -> None:
    _schema(artifact, SCRIPT_REVIEW_JSON_SCHEMA, "script_review")
    if artifact["script_id"] != script.script_id:
        raise ScriptValidationError("Script Review script_id 与稿件不一致")
    if artifact["script_revision"] != script.revision:
        raise ScriptValidationError("Script Review script_revision 与稿件不一致")
    if artifact["report_id"] != report.report_id:
        raise ScriptValidationError("Script Review report_id 与 Research Report 不一致")
    if artifact["report_revision"] != report.revision:
        raise ScriptValidationError("Script Review report_revision 与 Research Report 不一致")
    beat_ids = {beat["beat_id"] for beat in script.beats}
    claim_ids = {claim["id"] for claim in report.claims}
    for issue in artifact["issues"]:
        for beat_id in issue["beat_ids"]:
            if beat_id not in beat_ids:
                raise ScriptValidationError(f"Script Review 引用了不存在的 Beat：{beat_id}")
        for claim_id in issue["claim_ids"]:
            if claim_id not in claim_ids:
                raise ScriptValidationError(f"Script Review 引用了不存在的 Claim：{claim_id}")
    expected_ids = [f"SI{index:03d}" for index in range(1, len(artifact["issues"]) + 1)]
    if [issue["issue_id"] for issue in artifact["issues"]] != expected_ids:
        raise ScriptValidationError("Script Review issue_id 必须由程序生成")
    for issue in artifact["issues"]:
        expected_severity = (
            "blocking"
            if issue["issue_type"] in BLOCKING_ISSUE_TYPES
            else "advisory"
        )
        if issue["severity"] != expected_severity:
            raise ScriptValidationError("Script Review severity 必须由 issue_type 推导")
    check_names = [check["check_name"] for check in artifact["checks"]]
    if len(check_names) != len(set(check_names)):
        raise ScriptValidationError("Script Review checks 不能重复")
    missing_checks = sorted(set(SCRIPT_REVIEW_CHECK_NAMES) - set(check_names))
    if missing_checks:
        raise ScriptValidationError(
            "Script Review 缺少必检项：" + "、".join(missing_checks)
        )
    expected_gate = _derived_gate(artifact["issues"])
    for field, value in expected_gate.items():
        if artifact[field] != value:
            raise ScriptValidationError(f"Script Review 机器字段不一致：{field}")
