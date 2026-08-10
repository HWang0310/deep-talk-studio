"""Validation for the upstream Topic Candidate Set 0.3 contract."""

from datetime import datetime
from typing import Any, Dict, Iterable, Set
from urllib.parse import urlparse

from .schema import (
    DISCOVERY_RAW_JSON_SCHEMA,
    RESEARCH_HANDOFF_BRIEF_JSON_SCHEMA,
    TOPIC_CANDIDATE_SET_JSON_SCHEMA,
)
from .validation import ReportValidationError, validate_json_schema


class DiscoveryValidationError(ReportValidationError):
    """A user-readable Topic Discovery contract error."""


def _schema(value: Any, schema: Dict[str, Any], path: str) -> None:
    try:
        validate_json_schema(value, schema, path)
    except ReportValidationError as exc:
        raise DiscoveryValidationError(str(exc)) from None


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _parse_timestamp(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DiscoveryValidationError(f"{field} 必须是 ISO 8601 日期时间") from None


def validate_discovery_raw(data: Any) -> None:
    _schema(data, DISCOVERY_RAW_JSON_SCHEMA, "topic_discovery_raw")
    if data["time_window_hours"] != 72:
        raise DiscoveryValidationError("V0.3 默认发现窗口必须是 72 小时")
    for index, candidate in enumerate(data["candidates"]):
        if not 0 <= candidate["eligibility_signals"]["research_directions"]:
            raise DiscoveryValidationError(f"candidates[{index}] research_directions 不能小于 0")
        for key, score in candidate["score_assessments"].items():
            if not 0 <= score["score"] <= 5:
                raise DiscoveryValidationError(
                    f"candidates[{index}].score_assessments.{key}.score 必须在 0 到 5 之间"
                )
        _parse_timestamp(candidate["event_started_at"], f"candidates[{index}].event_started_at")
        _parse_timestamp(candidate["latest_update_at"], f"candidates[{index}].latest_update_at")
        for seed in candidate["source_seeds"]:
            if not _valid_http_url(seed["url"]):
                raise DiscoveryValidationError(
                    f"candidates[{index}] 的 Source Seed URL 必须是有效 HTTP(S) 地址"
                )


def _unique(values: Iterable[str], field: str) -> Set[str]:
    seen: Set[str] = set()
    for value in values:
        if value in seen:
            raise DiscoveryValidationError(f"{field} 不能包含重复值：{value}")
        seen.add(value)
    return seen


def validate_candidate_set(candidate_set: Any) -> None:
    data = candidate_set.data if hasattr(candidate_set, "data") else candidate_set
    _schema(data, TOPIC_CANDIDATE_SET_JSON_SCHEMA, "topic_candidate_set")
    ids = _unique((item["candidate_id"] for item in data["candidates"]), "candidates")
    display = data["display_candidate_ids"]
    _unique(display, "display_candidate_ids")
    if len(display) > 5:
        raise DiscoveryValidationError("默认最多展示 5 个候选题")
    if any(candidate_id not in ids for candidate_id in display):
        raise DiscoveryValidationError("display_candidate_ids 引用了不存在的 candidate")
    candidates = {item["candidate_id"]: item for item in data["candidates"]}
    primary = [item for item in candidates.values() if item["is_primary"]]
    if display and len(primary) != 1:
        raise DiscoveryValidationError("有展示候选时必须且只能有一个首选")
    if primary and primary[0]["candidate_id"] != display[0]:
        raise DiscoveryValidationError("首选必须是展示列表第 1 项")
    for candidate_id in display:
        candidate = candidates[candidate_id]
        if candidate["eligibility_status"] != "eligible":
            raise DiscoveryValidationError("watch 或 rejected 候选不能进入 Top 5")
        if candidate["recommendation"] not in {"recommend", "consider"}:
            raise DiscoveryValidationError("Top 5 只能展示 recommend 或 consider")
    if data["watch_candidate_count"] != sum(
        item["eligibility_status"] == "watch" for item in candidates.values()
    ):
        raise DiscoveryValidationError("watch_candidate_count 与候选状态不一致")
    if data["rejected_candidate_count"] != sum(
        item["eligibility_status"] == "rejected" for item in candidates.values()
    ):
        raise DiscoveryValidationError("rejected_candidate_count 与候选状态不一致")
    for candidate in candidates.values():
        if not 0 <= candidate["total_score"] <= 100:
            raise DiscoveryValidationError("total_score 必须在 0 到 100 之间")
        from .discovery import calculate_total_score

        if candidate["total_score"] != calculate_total_score(candidate["score_breakdown"]):
            raise DiscoveryValidationError("total_score 必须由固定评分权重计算")
        for seed in candidate["source_seeds"]:
            if not _valid_http_url(seed["url"]):
                raise DiscoveryValidationError("Source Seed URL 必须是有效 HTTP(S) 地址")


def validate_research_handoff(data: Any) -> None:
    _schema(data, RESEARCH_HANDOFF_BRIEF_JSON_SCHEMA, "research_handoff_brief")
    for seed in data["source_seeds"]:
        if not _valid_http_url(seed["url"]):
            raise DiscoveryValidationError("Research Handoff 的 Source Seed URL 必须是有效 HTTP(S) 地址")
