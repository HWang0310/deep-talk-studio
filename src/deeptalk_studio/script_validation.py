"""Script Draft 0.4 derivation and cross-artifact grounding validation."""

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Iterable, Mapping, Optional

from .models import ResearchReport, ScriptDraft
from .schema import SCRIPT_DRAFT_CONTENT_JSON_SCHEMA, SCRIPT_DRAFT_JSON_SCHEMA
from .script_profile import ScriptValidationError
from .validation import ReportValidationError, validate_json_schema, validate_report


MACHINE_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:IG|[CESPB])\d+(?![A-Za-z0-9])")
BEAT_ID_PATTERN = re.compile(r"^B(\d+)$")

EMPTY_REVIEW_STATE = {
    "state": "not_reviewed",
    "review_id": "",
    "reviewed_from_revision": 0,
    "review_gate_status": "not_run",
    "reviewed_content_digest": "",
}


def _schema(value: Any, schema: Dict[str, Any], path: str) -> None:
    try:
        validate_json_schema(value, schema, path)
    except ReportValidationError as exc:
        raise ScriptValidationError(str(exc)) from None


def _parse_timestamp(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise ScriptValidationError(f"{field} 必须是 ISO 8601 日期时间") from None


def assert_report_ready_for_script(report: ResearchReport) -> None:
    validate_report(report)
    approval = report.approval_gate
    if not (
        report.status == "ready_for_script"
        and report.quality_summary["gate_status"] == "pass"
        and report.fact_check["status"] == "completed"
        and approval["status"] == "approved"
        and approval["ready_for_script"]
        and approval["user_confirmation"].strip()
    ):
        raise ScriptValidationError(
            "Research Report 尚未经过用户确认并成为 ready_for_script，不能生成稿件"
        )


def count_spoken_characters(beats: Iterable[Mapping[str, Any]], closing: str) -> int:
    text = "".join(str(beat["narration"]) for beat in beats) + closing
    return sum(
        not char.isspace()
        and not unicodedata.category(char).startswith("P")
        and not unicodedata.category(char).startswith("Z")
        for char in text
    )


def estimate_duration_minutes(character_count: int, chars_per_minute: int) -> float:
    return round(character_count / chars_per_minute, 1)


def _coverage(
    beats: Iterable[Mapping[str, Any]], must_keep: Iterable[str]
) -> Dict[str, object]:
    used = set()
    for beat in beats:
        used.update(beat["claim_ids"])
        used.update(beat["analysis_basis_claim_ids"])
    required = list(must_keep)
    covered = [claim_id for claim_id in required if claim_id in used]
    missing = [claim_id for claim_id in required if claim_id not in used]
    return {
        "must_keep_claim_ids": required,
        "covered_must_keep_claim_ids": covered,
        "missing_must_keep_claim_ids": missing,
    }


def _normalized_phrase(value: str) -> str:
    return "".join(
        char.casefold()
        for char in value
        if not char.isspace() and not unicodedata.category(char).startswith(("P", "Z"))
    )


def _forbidden_conclusion(value: str) -> str:
    normalized = _normalized_phrase(value)
    directive_prefixes = (
        "请不要断言",
        "请不要声称",
        "请不要写成",
        "请不要写为",
        "不要断言",
        "不要声称",
        "不要写成",
        "不要写为",
        "不得断言",
        "不得声称",
        "不得写成",
        "不得写为",
        "禁止断言",
        "禁止声称",
        "不要把",
        "不要将",
        "不得把",
        "不得将",
        "请不要",
        "不要",
        "不得",
        "禁止",
        "避免",
    )
    for prefix in directive_prefixes:
        if normalized.startswith(prefix) and len(normalized) > len(prefix):
            return normalized[len(prefix) :]
    return normalized


def _validate_grounding(data: Mapping[str, Any], report: ResearchReport) -> None:
    claims = {claim["id"]: claim for claim in report.claims}
    evidence = {link["id"]: link for link in report.evidence_links}
    checked = set(report.fact_check["checked_claim_ids"])
    unresolved = set(report.fact_check["unresolved_claim_ids"])
    spoken = "".join(beat["narration"] for beat in data["beats"]) + data["closing"]
    if MACHINE_ID_PATTERN.search(spoken):
        raise ScriptValidationError("口播文本不能出现 Claim、Evidence 或其他机器 ID")
    normalized_spoken = _normalized_phrase(spoken)
    for forbidden in report.handoff_to_script_agent["avoid_claims"]:
        normalized = _forbidden_conclusion(forbidden)
        if normalized and normalized in normalized_spoken:
            raise ScriptValidationError("稿件直接使用了 handoff 中的 avoid_claim")

    for index, beat in enumerate(data["beats"]):
        refs = list(beat["claim_ids"]) + list(beat["analysis_basis_claim_ids"])
        for claim_id in refs:
            if claim_id not in claims:
                raise ScriptValidationError(f"beats[{index}] 引用了不存在的 Claim：{claim_id}")
        kind = beat["content_kind"]
        if kind == "analysis" and not beat["analysis_basis_claim_ids"]:
            raise ScriptValidationError("analysis Beat 必须保留 analysis_basis_claim_ids")
        for evidence_id in beat["evidence_link_ids"]:
            if evidence_id not in evidence:
                raise ScriptValidationError(
                    f"beats[{index}] 引用了不存在的 Evidence Link：{evidence_id}"
                )
            if evidence[evidence_id]["claim_id"] not in refs:
                raise ScriptValidationError(
                    f"beats[{index}] 的 Evidence Link 没有对应本 Beat 的 Claim"
                )
        if kind == "fact":
            if not beat["claim_ids"]:
                raise ScriptValidationError("fact Beat 必须引用 confirmed_fact Claim")
            for claim_id in beat["claim_ids"]:
                claim = claims[claim_id]
                if (
                    claim["classification"] != "confirmed_fact"
                    or claim["verification_status"] != "verified"
                ):
                    raise ScriptValidationError(
                        f"fact Beat 不能把 {claim['classification']} 或未核实 Claim 写成事实"
                    )
                if claim["risk_level"] in {"high", "critical"} and (
                    claim_id not in checked or claim_id in unresolved
                ):
                    raise ScriptValidationError("fact Beat 使用了尚未完成核查的高风险 Claim")
        elif kind == "attribution":
            if not beat["claim_ids"]:
                raise ScriptValidationError("attribution Beat 必须引用被归因的 Claim")
            for claim_id in beat["claim_ids"]:
                if claims[claim_id]["classification"] == "confirmed_fact":
                    raise ScriptValidationError(
                        "confirmed_fact 应使用 fact Beat，不应伪装成需要归因的说法"
                    )


def _derived_fields(
    data: Mapping[str, Any], report: ResearchReport, profile: Mapping[str, Any]
) -> Dict[str, object]:
    count = count_spoken_characters(data["beats"], data["closing"])
    return {
        "character_count": count,
        "estimated_duration_minutes": estimate_duration_minutes(
            count, int(profile["chars_per_minute"])
        ),
        **_coverage(data["beats"], report.handoff_to_script_agent["must_keep_claim_ids"]),
    }


def script_content_digest(data: Mapping[str, Any]) -> str:
    """Return the code-owned digest for the content a Review actually saw."""

    content = {
        field: deepcopy(data[field])
        for field in (
            "working_title",
            "thesis",
            "audience_promise",
            "beats",
            "closing",
            "research_caveats",
            "research_gaps",
            "must_keep_omission_reasons",
        )
    }
    canonical = json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def beat_id_number(beat_id: str) -> int:
    match = BEAT_ID_PATTERN.fullmatch(beat_id)
    if not match:
        raise ScriptValidationError("beat_id 必须由程序生成为 B001 形式")
    number = int(match.group(1))
    if number < 1:
        raise ScriptValidationError("beat_id 必须由程序生成为 B001 形式")
    if beat_id != f"B{number:03d}":
        raise ScriptValidationError("beat_id 必须由程序生成为 B001 形式")
    return number


def _validate_beat_identity(data: Mapping[str, Any]) -> None:
    active_ids = [beat["beat_id"] for beat in data["beats"]]
    if len(active_ids) != len(set(active_ids)):
        raise ScriptValidationError("beat_id 不能重复")
    active_numbers = [beat_id_number(beat_id) for beat_id in active_ids]
    identity = data.get("beat_identity")
    if identity is None:
        # V0.4.0 legacy drafts had positional IDs only. They stay readable, but
        # all newly created V0.4.1 drafts include explicit identity state.
        expected_ids = [f"B{index:03d}" for index in range(1, len(active_ids) + 1)]
        if active_ids != expected_ids:
            raise ScriptValidationError("legacy beat_id 必须按顺序生成")
        return
    retired_ids = identity["retired_beat_ids"]
    if len(retired_ids) != len(set(retired_ids)):
        raise ScriptValidationError("retired_beat_ids 不能重复")
    retired_numbers = [beat_id_number(beat_id) for beat_id in retired_ids]
    if set(active_ids) & set(retired_ids):
        raise ScriptValidationError("retired Beat 不能仍在当前稿件中")
    highest = max(active_numbers + retired_numbers, default=0)
    if identity["next_beat_number"] != highest + 1:
        raise ScriptValidationError("next_beat_number 必须由当前和 retired Beat 推导")


def _validate_review_state(
    data: Mapping[str, Any],
    report: ResearchReport,
    profile: Mapping[str, Any],
    review_artifact: Optional[Mapping[str, Any]],
) -> None:
    """Fail closed unless a reviewed Script can prove its passing Review."""

    review_state = data.get("review_state")
    if data["status"] == "draft":
        if review_state is not None and review_state != EMPTY_REVIEW_STATE:
            raise ScriptValidationError("draft Script 不能携带完成的 Review linkage")
        return

    if review_state is None:
        raise ScriptValidationError(
            "reviewed Script 缺少 Review linkage；旧版稿件必须重新审查"
        )
    if (
        review_state["state"] != "reviewed"
        or not review_state["review_id"]
        or review_state["reviewed_from_revision"] != data["previous_revision"]
        or review_state["review_gate_status"] != "pass"
    ):
        raise ScriptValidationError("reviewed Script 的 Review linkage 无效")
    actual_digest = script_content_digest(data)
    if review_state["reviewed_content_digest"] != actual_digest:
        raise ScriptValidationError("reviewed Script content digest 与内容不一致")
    if review_artifact is None:
        raise ScriptValidationError("reviewed Script 缺少匹配的 Review Artifact")

    from .script_review import validate_script_review_artifact

    validate_script_review_artifact(
        review_artifact,
        report,
        data,
        expected_script_revision=review_state["reviewed_from_revision"],
    )
    if (
        review_artifact["review_id"] != review_state["review_id"]
        or review_artifact["gate_status"] != "pass"
        or review_artifact.get("reviewed_content_digest")
        != review_state["reviewed_content_digest"]
    ):
        raise ScriptValidationError("reviewed Script 的 Review linkage 与 Artifact 不一致")


def prepare_script_draft(
    content: Dict[str, Any],
    report: ResearchReport,
    profile: Mapping[str, Any],
    *,
    created_at: str,
    script_id: str,
    target_duration_minutes: float = 12,
    script_mode: str = "codex_skill",
    revision: int = 1,
    previous_revision: int = 0,
    generated_at: Optional[str] = None,
    change_summary: str = "基于已批准 Research Report 生成第一版原创口播稿。",
    beat_ids: Optional[Iterable[str]] = None,
    beat_identity: Optional[Mapping[str, Any]] = None,
) -> ScriptDraft:
    assert_report_ready_for_script(report)
    _schema(content, SCRIPT_DRAFT_CONTENT_JSON_SCHEMA, "script_content")
    if script_mode not in {"codex_skill", "openai_api", "fixture"}:
        raise ScriptValidationError("script_mode 无效")
    if not isinstance(target_duration_minutes, (int, float)) or isinstance(
        target_duration_minutes, bool
    ) or not 3 <= target_duration_minutes <= 30:
        raise ScriptValidationError("目标口播时长必须在 3 到 30 分钟之间")
    timestamp = generated_at or created_at
    assigned_ids = list(beat_ids or ())
    if assigned_ids and len(assigned_ids) != len(content["beats"]):
        raise ScriptValidationError("程序分配的 Beat ID 数量与内容不一致")
    if not assigned_ids:
        assigned_ids = [f"B{index:03d}" for index in range(1, len(content["beats"]) + 1)]
    beats = [
        {"beat_id": beat_id, **deepcopy(beat)}
        for beat_id, beat in zip(assigned_ids, content["beats"])
    ]
    identity = dict(beat_identity or {})
    if not identity:
        identity = {
            "next_beat_number": len(beats) + 1,
            "retired_beat_ids": [],
        }
    artifact = {
        "artifact_version": "0.4",
        "script_id": script_id,
        "revision": revision,
        "previous_revision": previous_revision,
        "created_at": created_at,
        "generated_at": timestamp,
        "report_id": report.report_id,
        "report_revision": report.revision,
        "script_mode": script_mode,
        "status": "draft",
        "script_profile_version": str(profile["profile_version"]),
        "target_duration_minutes": target_duration_minutes,
        "working_title": content["working_title"],
        "thesis": content["thesis"],
        "audience_promise": content["audience_promise"],
        "beats": beats,
        "closing": content["closing"],
        "research_caveats": deepcopy(content["research_caveats"]),
        "research_gaps": deepcopy(content["research_gaps"]),
        "must_keep_omission_reasons": deepcopy(content["must_keep_omission_reasons"]),
        "change_summary": change_summary.strip(),
        "review_state": deepcopy(EMPTY_REVIEW_STATE),
        "beat_identity": identity,
    }
    artifact.update(_derived_fields(artifact, report, profile))
    return ScriptDraft.from_dict(artifact, report, dict(profile))


def validate_script_draft(
    script: Any,
    report: ResearchReport,
    profile: Mapping[str, Any],
    review_artifact: Optional[Mapping[str, Any]] = None,
) -> None:
    data = script.data if hasattr(script, "data") else script
    if review_artifact is None and hasattr(script, "review_artifact"):
        review_artifact = script.review_artifact
    _schema(data, SCRIPT_DRAFT_JSON_SCHEMA, "script_draft")
    assert_report_ready_for_script(report)
    if data["report_id"] != report.report_id:
        raise ScriptValidationError("Script report_id 与已批准 Research Report 不一致")
    if data["report_revision"] != report.revision:
        raise ScriptValidationError("Script report_revision 与已批准 Research Report 不一致")
    if data["script_profile_version"] != profile["profile_version"]:
        raise ScriptValidationError("Script Profile 版本与稿件不一致")
    if (data["revision"] == 1 and data["previous_revision"] != 0) or (
        data["revision"] > 1 and data["previous_revision"] != data["revision"] - 1
    ):
        raise ScriptValidationError("Script previous_revision 必须指向紧邻上一版")
    if _parse_timestamp(data["generated_at"], "generated_at") < _parse_timestamp(
        data["created_at"], "created_at"
    ):
        raise ScriptValidationError("Script generated_at 不能早于 created_at")
    _validate_beat_identity(data)
    _validate_grounding(data, report)
    expected = _derived_fields(data, report, profile)
    for field, value in expected.items():
        if data[field] != value:
            raise ScriptValidationError(f"Script 机器字段不一致：{field}")
    omission_ids = [item["claim_id"] for item in data["must_keep_omission_reasons"]]
    if len(omission_ids) != len(set(omission_ids)):
        raise ScriptValidationError("must_keep_omission_reasons 不能重复 Claim")
    for claim_id in omission_ids:
        if claim_id not in data["missing_must_keep_claim_ids"]:
            raise ScriptValidationError("must_keep omission 只能解释实际缺失的 Claim")
    _validate_review_state(data, report, profile, review_artifact)
