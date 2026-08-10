"""Pure deterministic derivation for Topic Candidate Set machine fields."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from .sources import normalize_url


SCORE_WEIGHTS = {
    "researchability": 30,
    "depth_conflict": 25,
    "freshness": 20,
    "channel_fit": 15,
    "attention_signal": 10,
}
QUALIFYING_SEED_TYPES = {"official", "primary", "media", "academic", "expert"}
HIGH_RISK_LEVELS = {"high", "critical"}
FUTURE_TIMESTAMP_TOLERANCE = timedelta(minutes=5)
DISPLAY_LIMIT = 5


def parse_timestamp(value: str, field: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} 必须是 ISO 8601 日期时间") from None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def calculate_total_score(breakdown: Mapping[str, Mapping[str, object]]) -> int:
    if set(breakdown) != set(SCORE_WEIGHTS):
        raise ValueError("score breakdown 必须完整包含五个固定维度")
    total = 0.0
    for name, weight in SCORE_WEIGHTS.items():
        score = breakdown[name].get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 5:
            raise ValueError(f"{name}.score 必须是 0 到 5 的整数")
        total += weight * score / 5
    return int(round(total))


def canonical_provenance_context(
    provenance_urls: Optional[Iterable[str]] = None,
    inspection_manifest: Optional[Mapping[str, object]] = None,
) -> Dict[str, object]:
    """Normalize the only external inputs allowed to determine Seed provenance."""

    matched_urls = sorted(
        {normalize_url(str(url)) for url in (provenance_urls or ())}
    )
    inspections = []
    if inspection_manifest is not None:
        if not isinstance(inspection_manifest, Mapping):
            raise ValueError("Codex inspection manifest 必须是 JSON 对象")
        entries = inspection_manifest.get("inspections")
        if set(inspection_manifest) != {"inspections"} or not isinstance(entries, list):
            raise ValueError("Codex inspection manifest 必须只包含 inspections 列表")
        seen = set()
        for entry in entries:
            allowed_fields = {"url", "tool_reference", "inspected_at"}
            required_fields = {"url", "inspected_at"}
            if (
                not isinstance(entry, Mapping)
                or not required_fields.issubset(entry)
                or not set(entry).issubset(allowed_fields)
            ):
                raise ValueError("Codex inspection manifest 条目字段不完整或包含未知字段")
            url = str(entry["url"])
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Codex inspection manifest 的 URL 必须是有效 HTTP(S) 地址")
            inspected_at = str(entry["inspected_at"])
            parse_timestamp(inspected_at, "Codex inspection manifest.inspected_at")
            normalized_url = normalize_url(url)
            tool_reference = str(entry.get("tool_reference", ""))
            key = (normalized_url, tool_reference, inspected_at)
            if key in seen:
                raise ValueError("Codex inspection manifest 不能包含重复检查记录")
            seen.add(key)
            inspections.append(
                {
                    "url": normalized_url,
                    "tool_reference": tool_reference,
                    "inspected_at": inspected_at,
                }
            )
    inspections.sort(
        key=lambda item: (item["url"], item["tool_reference"], item["inspected_at"])
    )
    return {"matched_urls": matched_urls, "codex_inspections": inspections}


def _candidate_id(candidate: Mapping[str, object], index: int, stable_ids: bool) -> str:
    if not stable_ids:
        return f"TPC-{index}"
    # The ordinal is part of the deterministic identity so an accidentally
    # duplicated Raw Candidate cannot create duplicate machine identifiers.
    payload = json.dumps(
        {"candidate": candidate, "ordinal": index},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"TPC-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _seed_status(
    url: str,
    discovery_mode: str,
    provenance_context: Mapping[str, object],
    existing_status: str = "",
) -> str:
    if discovery_mode == "codex_skill":
        inspected = {
            item["url"] for item in provenance_context.get("codex_inspections", [])
        }
        return "manual_open" if normalize_url(url) in inspected else "unmatched"
    if discovery_mode in {"openai_api", "fixture"}:
        matched = set(provenance_context.get("matched_urls", []))
        return "matched" if normalize_url(url) in matched else "unmatched"
    return existing_status


def _qualifying_direction_count(seeds: Sequence[Mapping[str, object]]) -> int:
    """Count directions conservatively: duplicate URL, publisher or host are one group."""

    usable = []
    seen_urls = set()
    for seed in seeds:
        if seed.get("provenance_status") not in {"matched", "manual_open"}:
            continue
        if seed.get("source_type") not in QUALIFYING_SEED_TYPES:
            continue
        normalized_url = normalize_url(str(seed["url"]))
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        usable.append(
            (
                str(seed["publisher"]).strip().casefold(),
                urlparse(normalized_url).netloc.casefold(),
            )
        )

    parents = list(range(len(usable)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        first, second = find(left), find(right)
        if first != second:
            parents[second] = first

    for left, (publisher, host) in enumerate(usable):
        for right in range(left):
            other_publisher, other_host = usable[right]
            if publisher == other_publisher or host == other_host:
                union(left, right)
    return len({find(index) for index in range(len(usable))})


def _preflight(candidate: Mapping[str, object], now: datetime) -> Tuple[str, Sequence[str]]:
    reasons = []
    signals = candidate["eligibility_signals"]
    seeds = candidate["source_seeds"]
    started = parse_timestamp(str(candidate["event_started_at"]), "event_started_at")
    updated = parse_timestamp(str(candidate["latest_update_at"]), "latest_update_at")
    future_time = started > now + FUTURE_TIMESTAMP_TOLERANCE or updated > now + FUTURE_TIMESTAMP_TOLERANCE
    if future_time:
        reasons.append("事件时间明显晚于本次发现时间，不能当作已发生的新进展。")
    recent_cutoff = now - timedelta(hours=72)
    ongoing_cutoff = now - timedelta(days=14)
    within_recent = not future_time and updated >= recent_cutoff and started >= recent_cutoff
    ongoing_with_update = not future_time and started >= ongoing_cutoff and updated >= recent_cutoff
    if not within_recent and not ongoing_with_update:
        reasons.append("事件不在最近 72 小时内，也没有最近 14 天持续事件的新进展。")
    if signals["anonymous_rumor_only"]:
        reasons.append("只有单一匿名传言，不能作为推荐选题。")
    if not signals["public_evidence_available"] or not seeds:
        reasons.append("缺少可检查的公开资料入口。")
    if signals["material_unverified_allegation"]:
        reasons.append("核心价值依赖未经证实的指控。")
    if signals["emotion_only"]:
        reasons.append("只有情绪热度，缺少可研究的事实基础。")
    if signals["creator_imitation_dependency"]:
        reasons.append("内容价值不能建立在模仿其他创作者表达之上。")
    directions = _qualifying_direction_count(seeds)
    sufficient_preflight = directions >= 2 and signals["research_directions"] >= 2
    if not sufficient_preflight:
        reasons.append("轻量 Preflight 尚未找到两个独立、可继续调查的公开来源方向。")
    hard_reject = any(
        (
            future_time,
            signals["anonymous_rumor_only"],
            signals["material_unverified_allegation"],
            signals["emotion_only"],
            signals["creator_imitation_dependency"],
        )
    )
    if hard_reject:
        return "rejected", reasons
    if not (within_recent or ongoing_with_update):
        return "rejected", reasons
    if (not signals["public_evidence_available"] or not seeds) and signals["major_fast_event"]:
        reasons.append("重大快速事件尚在发展，先保留观察而不推荐。")
        return "watch", reasons
    if not signals["public_evidence_available"] or not seeds:
        return "rejected", reasons
    if candidate["risk_level"] in HIGH_RISK_LEVELS and not sufficient_preflight:
        reasons.append("高风险事件的可靠证据基础仍薄弱，先保留观察。")
        return "watch", reasons
    if not sufficient_preflight:
        if signals["major_fast_event"]:
            reasons.append("重大快速事件可能值得后续跟进，暂列观察。")
            return "watch", reasons
        return "rejected", reasons
    return "eligible", reasons


def _rank_key(candidate: Mapping[str, object]) -> Tuple[int, str, str]:
    return (-int(candidate["total_score"]), str(candidate["title"]).casefold(), str(candidate["candidate_id"]))


def _recommendation(status: str, total: int) -> str:
    if status == "watch":
        return "watch"
    if status == "rejected":
        return "reject"
    return "recommend" if total >= 75 else "consider"


def select_display_candidates(candidates: Sequence[Mapping[str, object]]) -> Sequence[str]:
    """Prefer category diversity, then fill empty seats without duplicating events."""

    ranked = sorted(candidates, key=_rank_key)
    selected = []
    selected_ids = set()
    seen_clusters = set()
    category_count: Dict[str, int] = {}
    for candidate in ranked:
        if candidate["eligibility_status"] != "eligible":
            continue
        cluster = str(candidate["event_cluster_key"]).casefold()
        category = str(candidate["category"])
        if cluster in seen_clusters or category_count.get(category, 0) >= 2:
            continue
        selected.append(candidate["candidate_id"])
        selected_ids.add(candidate["candidate_id"])
        seen_clusters.add(cluster)
        category_count[category] = category_count.get(category, 0) + 1
        if len(selected) == DISPLAY_LIMIT:
            return selected
    for candidate in ranked:
        if candidate["eligibility_status"] != "eligible":
            continue
        cluster = str(candidate["event_cluster_key"]).casefold()
        if candidate["candidate_id"] in selected_ids or cluster in seen_clusters:
            continue
        selected.append(candidate["candidate_id"])
        selected_ids.add(candidate["candidate_id"])
        seen_clusters.add(cluster)
        if len(selected) == DISPLAY_LIMIT:
            break
    return selected


def derive_candidate_set_fields(
    raw_candidates: Sequence[Mapping[str, object]],
    *,
    generated_at: datetime,
    discovery_mode: str,
    provenance_context: Mapping[str, object],
    stable_ids: bool,
) -> Dict[str, object]:
    """Return every deterministic Candidate machine-owned field from raw content."""

    normalized = []
    for index, proposed in enumerate(raw_candidates, 1):
        score_breakdown = deepcopy(proposed["score_assessments"])
        seeds = []
        for seed in proposed["source_seeds"]:
            copied = deepcopy(seed)
            copied["provenance_status"] = _seed_status(
                str(copied["url"]),
                discovery_mode,
                provenance_context,
                str(copied.get("provenance_status", "")),
            )
            seeds.append(copied)
        preflight_input = deepcopy(proposed)
        preflight_input["source_seeds"] = seeds
        status, reasons = _preflight(preflight_input, generated_at)
        candidate = {
            "candidate_id": _candidate_id(proposed, index, stable_ids),
            **deepcopy(proposed),
            "source_seeds": seeds,
            "score_breakdown": score_breakdown,
            "total_score": calculate_total_score(score_breakdown),
            "eligibility_status": status,
            "eligibility_reasons": list(reasons),
            "recommendation": _recommendation(status, calculate_total_score(score_breakdown)),
            "is_primary": False,
        }
        normalized.append(candidate)
    display_ids = list(select_display_candidates(normalized))
    if display_ids:
        next(item for item in normalized if item["candidate_id"] == display_ids[0])["is_primary"] = True
    return {
        "candidates": normalized,
        "display_candidate_ids": display_ids,
        "watch_candidate_count": sum(item["eligibility_status"] == "watch" for item in normalized),
        "rejected_candidate_count": sum(item["eligibility_status"] == "rejected" for item in normalized),
    }
