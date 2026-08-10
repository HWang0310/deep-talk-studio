"""Validation for the upstream Topic Candidate Set 0.3 contract."""

from copy import deepcopy
from typing import Any, Dict, Iterable, Set
from urllib.parse import urlparse

from .schema import (
    DISCOVERY_RAW_JSON_SCHEMA,
    RESEARCH_HANDOFF_BRIEF_JSON_SCHEMA,
    TOPIC_CANDIDATE_SET_JSON_SCHEMA,
)
from .discovery_derivation import (
    calculate_total_score,
    canonical_provenance_context,
    derive_candidate_set_fields,
    parse_timestamp,
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


def validate_discovery_raw(data: Any, *, require_candidate_pool: bool = True) -> None:
    _schema(data, DISCOVERY_RAW_JSON_SCHEMA, "topic_discovery_raw")
    if data["time_window_hours"] != 72:
        raise DiscoveryValidationError("V0.3 默认发现窗口必须是 72 小时")
    if require_candidate_pool and len(data["candidates"]) < 7:
        raise DiscoveryValidationError("Discovery 原始候选池至少需要 7 个候选，不能把少量结果假装成完整搜索。")
    for index, candidate in enumerate(data["candidates"]):
        if not 0 <= candidate["eligibility_signals"]["research_directions"]:
            raise DiscoveryValidationError(f"candidates[{index}] research_directions 不能小于 0")
        for key, score in candidate["score_assessments"].items():
            if not 0 <= score["score"] <= 5:
                raise DiscoveryValidationError(
                    f"candidates[{index}].score_assessments.{key}.score 必须在 0 到 5 之间"
                )
        try:
            started = parse_timestamp(candidate["event_started_at"], f"candidates[{index}].event_started_at")
            updated = parse_timestamp(candidate["latest_update_at"], f"candidates[{index}].latest_update_at")
        except ValueError as exc:
            raise DiscoveryValidationError(str(exc)) from None
        if started > updated:
            raise DiscoveryValidationError(f"candidates[{index}] 的事件开始时间不能晚于最新进展时间")
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
    raw_candidates = []
    for candidate in data["candidates"]:
        raw = {
            key: deepcopy(candidate[key])
            for key in DISCOVERY_RAW_JSON_SCHEMA["properties"]["candidates"]["items"]["properties"]
        }
        raw["score_assessments"] = deepcopy(candidate["score_assessments"])
        raw["source_seeds"] = [
            {key: value for key, value in seed.items() if key != "provenance_status"}
            for seed in candidate["source_seeds"]
        ]
        raw_candidates.append(raw)
    validate_discovery_raw(
        {
            "query": data["query"],
            "time_window_hours": data["time_window_hours"],
            "candidates": raw_candidates,
        },
        require_candidate_pool=False,
    )
    try:
        generated_at = parse_timestamp(data["generated_at"], "generated_at")
        if "seed_provenance" in data:
            context = canonical_provenance_context(
                data["seed_provenance"]["matched_urls"],
                {"inspections": data["seed_provenance"]["codex_inspections"]},
            )
            if context != data["seed_provenance"]:
                raise DiscoveryValidationError("seed_provenance 必须是规范化的机器字段")
            stable_ids = True
            derivation_mode = data["discovery_mode"]
        else:
            context = {"matched_urls": [], "codex_inspections": []}
            stable_ids = False
            for raw, candidate in zip(raw_candidates, data["candidates"]):
                for seed, saved in zip(raw["source_seeds"], candidate["source_seeds"]):
                    seed["provenance_status"] = saved["provenance_status"]
            derivation_mode = "legacy"
        expected = derive_candidate_set_fields(
            raw_candidates,
            generated_at=generated_at,
            discovery_mode=derivation_mode,
            provenance_context=context,
            stable_ids=stable_ids,
        )
    except ValueError as exc:
        raise DiscoveryValidationError(str(exc)) from None
    if len(data["display_candidate_ids"]) > 5:
        raise DiscoveryValidationError("默认最多展示 5 个候选题")
    for actual, derived in zip(data["candidates"], expected["candidates"]):
        for field in (
            "candidate_id",
            "source_seeds",
            "score_breakdown",
            "total_score",
            "eligibility_status",
            "eligibility_reasons",
            "recommendation",
            "is_primary",
        ):
            if actual[field] != derived[field]:
                if field == "total_score":
                    raise DiscoveryValidationError("total_score 必须由固定评分权重计算")
                raise DiscoveryValidationError(f"Candidate 机器字段不一致：{field}")
    for field in (
        "display_candidate_ids",
        "watch_candidate_count",
        "rejected_candidate_count",
    ):
        if data[field] != expected[field]:
            raise DiscoveryValidationError(f"Candidate Set 机器字段不一致：{field}")


def validate_research_handoff(data: Any) -> None:
    _schema(data, RESEARCH_HANDOFF_BRIEF_JSON_SCHEMA, "research_handoff_brief")
    for seed in data["source_seeds"]:
        if not _valid_http_url(seed["url"]):
            raise DiscoveryValidationError("Research Handoff 的 Source Seed URL 必须是有效 HTTP(S) 地址")
