"""Independent Thesis Gate for Content Director V1.

The gate is deliberately controlled: a free-form reviewer cannot invent a
passing criterion, and a passing machine review is still insufficient until a
human explicitly confirms the direction in ordinary language.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Mapping

from .content_director import (
    ContentDirectorValidationError,
    thesis_content_digest,
    validate_content_thesis_card,
)
from .models import ContentThesisCard, ResearchReport


class ContentThesisReviewError(ValueError):
    pass


_ISSUE_TYPES = {
    "thesis_unclear",
    "unsupported_thesis",
    "counter_evidence_ignored",
    "audience_value_missing",
    "competitive_imitation_risk",
    "retention_promise_weak",
}


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _parse_time(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ContentThesisReviewError(f"{field} 必须是 ISO 8601 日期时间")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContentThesisReviewError(f"{field} 必须是 ISO 8601 日期时间") from exc
    return value


def _review_content(review_content: Mapping[str, Any], profile: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(review_content, Mapping):
        raise ContentThesisReviewError("Thesis Review 内容必须是对象")
    required = {"checks", "issues", "overall_summary"}
    if set(review_content) != required:
        raise ContentThesisReviewError("Thesis Review 内容字段不完整或包含未知字段")
    expected = list(profile["thesis_gate_checks"])
    checks = review_content["checks"]
    if not isinstance(checks, list) or len(checks) != len(expected):
        raise ContentThesisReviewError("Thesis Review 必须覆盖全部受控检查项")
    seen = []
    normalized_checks = []
    for check in checks:
        if not isinstance(check, Mapping) or set(check) != {"check_name", "outcome", "reason"}:
            raise ContentThesisReviewError("每个 Thesis Review 检查项字段必须固定")
        name, outcome, reason = check["check_name"], check["outcome"], check["reason"]
        if name not in expected or name in seen:
            raise ContentThesisReviewError("Thesis Review 检查项不得遗漏、重复或自定义")
        if outcome not in {"pass", "fail"} or not isinstance(reason, str) or not reason.strip():
            raise ContentThesisReviewError("Thesis Review 检查结果或理由无效")
        seen.append(name)
        normalized_checks.append({"check_name": name, "outcome": outcome, "reason": reason.strip()})
    if set(seen) != set(expected):
        raise ContentThesisReviewError("Thesis Review 必须覆盖全部受控检查项")
    issues = review_content["issues"]
    if not isinstance(issues, list):
        raise ContentThesisReviewError("Thesis Review issues 必须是列表")
    normalized_issues = []
    for issue in issues:
        if not isinstance(issue, Mapping) or set(issue) != {"issue_type", "severity", "description"}:
            raise ContentThesisReviewError("Thesis Review issue 字段必须固定")
        if issue["issue_type"] not in _ISSUE_TYPES or issue["severity"] not in {"blocking", "advisory"}:
            raise ContentThesisReviewError("Thesis Review issue 类型或严重级别无效")
        if not isinstance(issue["description"], str) or not issue["description"].strip():
            raise ContentThesisReviewError("Thesis Review issue 必须说明问题")
        normalized_issues.append(dict(issue))
    summary = review_content["overall_summary"]
    if not isinstance(summary, str) or not summary.strip():
        raise ContentThesisReviewError("Thesis Review 必须给出总结")
    failed = {check["check_name"] for check in normalized_checks if check["outcome"] == "fail"}
    blocking = [issue for issue in normalized_issues if issue["severity"] == "blocking"]
    if failed and not blocking:
        raise ContentThesisReviewError("失败的 Thesis Gate 检查项必须有 blocking issue")
    return {"checks": normalized_checks, "issues": normalized_issues, "overall_summary": summary.strip()}


def validate_content_thesis_review(
    artifact: Mapping[str, Any],
    card: ContentThesisCard,
    report: ResearchReport,
    profile: Mapping[str, Any],
) -> None:
    try:
        validate_content_thesis_card(card, report, profile)
    except ContentDirectorValidationError as exc:
        raise ContentThesisReviewError(str(exc)) from exc
    expected = {
        "artifact_type", "artifact_version", "review_id", "created_at", "report_id",
        "report_revision", "report_content_digest", "card_id", "card_revision",
        "card_content_digest", "profile_version", "gate", "content", "content_digest",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != expected:
        raise ContentThesisReviewError("Thesis Review Artifact 字段不完整或包含未知字段")
    if artifact["artifact_type"] != "content_thesis_review" or artifact["artifact_version"] != 1:
        raise ContentThesisReviewError("Thesis Review Artifact 类型或版本不支持")
    if not isinstance(artifact["review_id"], str) or not artifact["review_id"].strip():
        raise ContentThesisReviewError("Thesis Review 必须有 review_id")
    _parse_time(artifact["created_at"], "created_at")
    expected_bindings = {
        "report_id": report.report_id,
        "report_revision": report.revision,
        "report_content_digest": card.report_content_digest,
        "card_id": card.card_id,
        "card_revision": card.revision,
        "card_content_digest": thesis_content_digest(card.to_dict()),
        "profile_version": profile["profile_version"],
    }
    for field, value in expected_bindings.items():
        if artifact.get(field) != value:
            raise ContentThesisReviewError(f"Thesis Review 的 {field} 与绑定工件不一致")
    content = _review_content(artifact["content"], profile)
    if content != artifact["content"] or artifact["content_digest"] != _digest(content):
        raise ContentThesisReviewError("Thesis Review 内容或摘要不一致")
    failed = any(check["outcome"] == "fail" for check in content["checks"])
    blocking = any(issue["severity"] == "blocking" for issue in content["issues"])
    expected_decision = "needs_revision" if failed or blocking else "pass"
    if artifact["gate"] != {"decision": expected_decision, "blocking_issue_count": sum(issue["severity"] == "blocking" for issue in content["issues"])}:
        raise ContentThesisReviewError("Thesis Gate 决策与检查结果不一致")


def prepare_content_thesis_review(
    card: ContentThesisCard,
    report: ResearchReport,
    profile: Mapping[str, Any],
    review_content: Mapping[str, Any],
    *,
    created_at: str,
    review_id: str,
) -> Dict[str, Any]:
    try:
        validate_content_thesis_card(card, report, profile)
    except ContentDirectorValidationError as exc:
        raise ContentThesisReviewError(str(exc)) from exc
    if card.status != "draft":
        raise ContentThesisReviewError("只有 draft Content Thesis Card 可以进入 Thesis Review")
    _parse_time(created_at, "created_at")
    if not isinstance(review_id, str) or not review_id.strip():
        raise ContentThesisReviewError("review_id 必须是非空文本")
    content = _review_content(review_content, profile)
    blocking_count = sum(issue["severity"] == "blocking" for issue in content["issues"])
    failed = any(check["outcome"] == "fail" for check in content["checks"])
    artifact = {
        "artifact_type": "content_thesis_review",
        "artifact_version": 1,
        "review_id": review_id.strip(),
        "created_at": created_at,
        "report_id": report.report_id,
        "report_revision": report.revision,
        "report_content_digest": card.report_content_digest,
        "card_id": card.card_id,
        "card_revision": card.revision,
        "card_content_digest": thesis_content_digest(card.to_dict()),
        "profile_version": profile["profile_version"],
        "gate": {
            "decision": "needs_revision" if failed or blocking_count else "pass",
            "blocking_issue_count": blocking_count,
        },
        "content": content,
        "content_digest": _digest(content),
    }
    validate_content_thesis_review(artifact, card, report, profile)
    return artifact


def approve_content_thesis_card(
    card: ContentThesisCard,
    review_artifact: Mapping[str, Any],
    report: ResearchReport,
    profile: Mapping[str, Any],
    *,
    confirmation: str,
    approved_at: str | None = None,
) -> ContentThesisCard:
    validate_content_thesis_review(review_artifact, card, report, profile)
    if review_artifact["gate"]["decision"] != "pass":
        raise ContentThesisReviewError("Thesis Gate 未通过，不能进入人工确认")
    if not isinstance(confirmation, str) or "确认" not in confirmation or "进入写稿" not in confirmation:
        raise ContentThesisReviewError("需要明确的普通语言确认：确认本期内容方向，进入写稿。")
    timestamp = approved_at or datetime.now(timezone.utc).isoformat()
    _parse_time(timestamp, "approved_at")
    approved = deepcopy(card.to_dict())
    approved["previous_revision"] = card.revision
    approved["revision"] = card.revision + 1
    approved["status"] = "approved_for_script"
    approved["review_state"] = {
        "state": "reviewed",
        "review_id": review_artifact["review_id"],
        "reviewed_from_revision": card.revision,
        "review_gate_status": "pass",
        "reviewed_content_digest": card.content_digest,
        "user_confirmation": confirmation.strip(),
    }
    approved["change_summary"] = "Thesis Gate 通过并已获得人工内容方向确认。"
    return ContentThesisCard.from_dict(approved, report, dict(profile), review_artifact)
