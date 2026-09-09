"""Approved Research → immutable Content Thesis Card 1."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Mapping

from .content_director_profile import ContentDirectorValidationError
from .models import ContentThesisCard, ResearchReport
from .schema import CONTENT_THESIS_CARD_JSON_SCHEMA, CONTENT_THESIS_CONTENT_JSON_SCHEMA
from .script_validation import assert_report_ready_for_script
from .validation import ReportValidationError, validate_json_schema


EMPTY_THESIS_REVIEW_STATE = {
    "state": "not_reviewed",
    "review_id": "",
    "reviewed_from_revision": 0,
    "review_gate_status": "not_run",
    "reviewed_content_digest": "",
    "user_confirmation": "",
}


def _schema(value: Any, schema: Dict[str, Any], path: str) -> None:
    try:
        validate_json_schema(value, schema, path)
    except ReportValidationError as exc:
        raise ContentDirectorValidationError(str(exc)) from None


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def report_content_digest(report: ResearchReport) -> str:
    """Bind the card to the exact approved factual substrate."""

    return _digest(report.to_dict())


def thesis_content_digest(data: Mapping[str, Any]) -> str:
    return _digest({field: deepcopy(data[field]) for field in CONTENT_THESIS_CONTENT_JSON_SCHEMA["properties"]})


def _validated_claim_ids(
    content: Mapping[str, Any], report: ResearchReport
) -> None:
    claims = {claim["id"]: claim for claim in report.claims}
    strongest = content["strongest_evidence_claim_ids"]
    if not strongest:
        raise ContentDirectorValidationError("strongest_evidence_claim_ids 不能为空")
    for claim_id in strongest:
        claim = claims.get(claim_id)
        if claim is None or not (
            claim["classification"] == "confirmed_fact"
            and claim["verification_status"] == "verified"
        ):
            raise ContentDirectorValidationError(
                "strongest evidence 必须绑定已核验的 confirmed_fact Claim"
            )
    counters = content["counter_evidence_claim_ids"]
    if not counters:
        raise ContentDirectorValidationError("counter_evidence_claim_ids 不能为空")
    for claim_id in counters:
        if claim_id not in claims:
            raise ContentDirectorValidationError("counter evidence 引用了不存在的 Claim")
    if not content["uncertainty_limits"]:
        raise ContentDirectorValidationError("Thesis Card 必须明确 uncertainty_limits")


def prepare_content_thesis_card(
    content: Dict[str, Any], report: ResearchReport, profile: Mapping[str, object], *,
    created_at: str, card_id: str, revision: int = 1, previous_revision: int = 0,
    generated_at: str = "", change_summary: str = "基于已批准 Research 生成 Content Thesis Card。",
) -> ContentThesisCard:
    try:
        assert_report_ready_for_script(report)
    except Exception as exc:
        raise ContentDirectorValidationError(
            "Content Thesis Card 只能使用 ready_for_script 的已批准 Research"
        ) from exc
    _schema(content, CONTENT_THESIS_CONTENT_JSON_SCHEMA, "content_thesis_content")
    _validated_claim_ids(content, report)
    timestamp = generated_at or created_at
    data = {
        "artifact_version": "1",
        "card_id": card_id,
        "revision": revision,
        "previous_revision": previous_revision,
        "created_at": created_at,
        "generated_at": timestamp,
        "report_id": report.report_id,
        "report_revision": report.revision,
        "report_content_digest": report_content_digest(report),
        "content_director_profile_version": str(profile["profile_version"]),
        "status": "draft",
        "review_state": deepcopy(EMPTY_THESIS_REVIEW_STATE),
        "change_summary": change_summary,
        **deepcopy(content),
    }
    data["content_digest"] = thesis_content_digest(data)
    validate_content_thesis_card(data, report, profile)
    return ContentThesisCard.from_dict(data, report, dict(profile))


def validate_content_thesis_card(
    card: Any,
    report: ResearchReport,
    profile: Mapping[str, object],
    review_artifact: Mapping[str, Any] | None = None,
) -> None:
    data = card.data if hasattr(card, "data") else card
    _schema(data, CONTENT_THESIS_CARD_JSON_SCHEMA, "content_thesis_card")
    if data["report_id"] != report.report_id or data["report_revision"] != report.revision:
        raise ContentDirectorValidationError("Thesis Card 与 Research revision 不一致")
    if data["report_content_digest"] != report_content_digest(report):
        raise ContentDirectorValidationError("Thesis Card Research digest 不一致")
    if data["content_director_profile_version"] != str(profile["profile_version"]):
        raise ContentDirectorValidationError("Thesis Card Profile 版本不一致")
    if data["content_digest"] != thesis_content_digest(data):
        raise ContentDirectorValidationError("Thesis Card content digest 不一致")
    _validated_claim_ids(data, report)
    state = data["review_state"]
    if data["status"] == "draft":
        if state != EMPTY_THESIS_REVIEW_STATE:
            raise ContentDirectorValidationError("draft Thesis Card 不能携带完成的 Review linkage")
    elif not (
        state["state"] == "reviewed" and state["review_id"]
        and state["reviewed_from_revision"] == data["previous_revision"]
        and state["review_gate_status"] == "pass" and state["user_confirmation"].strip()
        and state["reviewed_content_digest"] == data["content_digest"]
    ):
        raise ContentDirectorValidationError("approved Thesis Card 缺少有效的人类 Review linkage")
    elif review_artifact is None:
        raise ContentDirectorValidationError("approved Thesis Card 必须随附可验证的 Thesis Review Artifact")
    else:
        from .content_thesis_review import ContentThesisReviewError, validate_content_thesis_review

        draft_data = deepcopy(data)
        draft_data["status"] = "draft"
        draft_data["revision"] = data["previous_revision"]
        draft_data["previous_revision"] = max(0, data["previous_revision"] - 1)
        draft_data["review_state"] = deepcopy(EMPTY_THESIS_REVIEW_STATE)
        draft_card = ContentThesisCard(draft_data)
        try:
            validate_content_thesis_review(review_artifact, draft_card, report, profile)
        except ContentThesisReviewError as exc:
            raise ContentDirectorValidationError("approved Thesis Card 的 Thesis Review Artifact 无效") from exc
        if review_artifact["review_id"] != state["review_id"]:
            raise ContentDirectorValidationError("approved Thesis Card 的 review_id 与 Artifact 不一致")
