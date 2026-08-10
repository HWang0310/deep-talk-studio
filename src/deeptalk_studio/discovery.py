"""Deterministic Topic Discovery preflight, ranking and Research handoff."""

import json
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from .discovery_validation import (
    DiscoveryValidationError,
    validate_candidate_set,
    validate_discovery_raw,
    validate_research_handoff,
)
from .models import TopicCandidateSet
from .sources import normalize_url


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHANNEL_PROFILE = REPO_ROOT / "config" / "channel-profile.json"
SCORE_WEIGHTS = {
    "researchability": 30,
    "depth_conflict": 25,
    "freshness": 20,
    "channel_fit": 15,
    "attention_signal": 10,
}
QUALIFYING_SEED_TYPES = {"official", "primary", "media", "academic", "expert"}
HIGH_RISK_LEVELS = {"high", "critical"}


def _default_clock() -> datetime:
    return datetime.now().astimezone()


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def _new_id() -> str:
    return f"DISC-{uuid.uuid4().hex}"


def load_channel_profile(path: Optional[Path] = None) -> Dict[str, object]:
    """Load the stable, versioned default channel description."""

    profile_path = path or DEFAULT_CHANNEL_PROFILE
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiscoveryValidationError(f"无法读取 Channel Profile：{profile_path}") from exc
    required = {
        "profile_version",
        "name",
        "platform",
        "format",
        "content_characteristics",
        "topic_domains",
        "avoid",
    }
    if not isinstance(profile, dict) or set(profile) != required:
        raise DiscoveryValidationError("Channel Profile 字段不完整或包含未知字段")
    if not all(isinstance(profile[key], str) and profile[key] for key in required - {"content_characteristics", "topic_domains", "avoid"}):
        raise DiscoveryValidationError("Channel Profile 的文本字段不能为空")
    for key in ("content_characteristics", "topic_domains", "avoid"):
        if not isinstance(profile[key], list) or not profile[key] or not all(
            isinstance(item, str) and item for item in profile[key]
        ):
            raise DiscoveryValidationError(f"Channel Profile.{key} 必须是非空文本列表")
    return profile


def calculate_total_score(breakdown: Mapping[str, Mapping[str, object]]) -> int:
    """Calculate the only authoritative total from documented V0.3 weights."""

    if set(breakdown) != set(SCORE_WEIGHTS):
        raise DiscoveryValidationError("score breakdown 必须完整包含五个固定维度")
    total = 0.0
    for name, weight in SCORE_WEIGHTS.items():
        score = breakdown[name].get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 5:
            raise DiscoveryValidationError(f"{name}.score 必须是 0 到 5 的整数")
        total += weight * score / 5
    return int(round(total))


def _parse(value: str, field: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DiscoveryValidationError(f"{field} 必须是 ISO 8601 日期时间") from None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def _seed_direction(seed: Mapping[str, object]) -> Tuple[str, str]:
    publisher = str(seed["publisher"]).strip().casefold()
    host = urlparse(str(seed["url"])).netloc.casefold()
    return publisher, host


def _preflight(candidate: Mapping[str, object], now: datetime) -> Tuple[str, Sequence[str]]:
    reasons = []
    signals = candidate["eligibility_signals"]
    seeds = candidate["source_seeds"]
    started = _parse(str(candidate["event_started_at"]), "event_started_at")
    updated = _parse(str(candidate["latest_update_at"]), "latest_update_at")
    recent_cutoff = now - timedelta(hours=72)
    ongoing_cutoff = now - timedelta(days=14)
    within_recent = updated >= recent_cutoff and started >= recent_cutoff
    ongoing_with_update = started >= ongoing_cutoff and updated >= recent_cutoff
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
    checked_seeds = [
        seed
        for seed in seeds
        if seed.get("provenance_status") in {"matched", "manual_open"}
    ]
    directions = {_seed_direction(seed) for seed in checked_seeds}
    usable_seed_count = sum(
        seed["source_type"] in QUALIFYING_SEED_TYPES for seed in checked_seeds
    )
    sufficient_preflight = (
        len(directions) >= 2
        and signals["research_directions"] >= 2
        and usable_seed_count >= 2
    )
    if not sufficient_preflight:
        reasons.append("轻量 Preflight 尚未找到两个独立、可继续调查的公开来源方向。")
    hard_reject = any(
        (
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


def _seed_provenance(url: str, provenance_urls: Optional[Iterable[str]], mode: str) -> str:
    if mode == "codex_skill":
        return "manual_open"
    if provenance_urls is None:
        return "unmatched"
    normalized = normalize_url(url)
    known = {normalize_url(item) for item in provenance_urls}
    return "matched" if normalized in known else "unmatched"


def _rank_key(candidate: Mapping[str, object]) -> Tuple[int, str, str]:
    return (-int(candidate["total_score"]), str(candidate["title"]).casefold(), str(candidate["candidate_id"]))


def _recommendation(status: str, total: int) -> str:
    if status == "watch":
        return "watch"
    if status == "rejected":
        return "reject"
    return "recommend" if total >= 75 else "consider"


def _display_ids(candidates: Sequence[Mapping[str, object]], count: int) -> Sequence[str]:
    selected = []
    seen_clusters = set()
    category_count: Dict[str, int] = {}
    for candidate in sorted(candidates, key=_rank_key):
        if candidate["eligibility_status"] != "eligible":
            continue
        cluster = candidate["event_cluster_key"].casefold()
        category = candidate["category"]
        if cluster in seen_clusters or category_count.get(category, 0) >= 2:
            continue
        selected.append(candidate["candidate_id"])
        seen_clusters.add(cluster)
        category_count[category] = category_count.get(category, 0) + 1
        if len(selected) == count:
            break
    return selected


def prepare_discovery(
    raw: dict,
    channel_profile: Mapping[str, object],
    *,
    now: Optional[datetime] = None,
    discovery_id: str = "",
    provenance_urls: Optional[Iterable[str]] = None,
    discovery_mode: str = "openai_api",
    display_count: int = 5,
    category_filter: Sequence[str] = (),
) -> TopicCandidateSet:
    """Turn raw Discovery judgments into the machine-owned Candidate Set 0.3."""

    validate_discovery_raw(raw)
    if discovery_mode not in {"codex_skill", "openai_api", "fixture"}:
        raise DiscoveryValidationError("discovery_mode 无效")
    moment = now or _default_clock()
    normalized = []
    for index, proposed in enumerate(raw["candidates"], 1):
        score_breakdown = deepcopy(proposed["score_assessments"])
        total = calculate_total_score(score_breakdown)
        seeds = []
        for seed in proposed["source_seeds"]:
            copied = deepcopy(seed)
            copied["provenance_status"] = _seed_provenance(
                copied["url"], provenance_urls, discovery_mode
            )
            seeds.append(copied)
        preflight_input = deepcopy(proposed)
        preflight_input["source_seeds"] = seeds
        status, reasons = _preflight(preflight_input, moment)
        candidate = {
            "candidate_id": f"TPC-{index}",
            **deepcopy(proposed),
            "source_seeds": seeds,
            "score_breakdown": score_breakdown,
            "total_score": total,
            "eligibility_status": status,
            "eligibility_reasons": list(reasons),
            "recommendation": _recommendation(status, total),
            "is_primary": False,
        }
        normalized.append(candidate)
    if category_filter:
        allowed = set(category_filter)
        normalized = [item for item in normalized if item["category"] in allowed]
    display_ids = list(_display_ids(normalized, display_count))
    if display_ids:
        next(item for item in normalized if item["candidate_id"] == display_ids[0])["is_primary"] = True
    artifact = {
        "artifact_version": "0.3",
        "discovery_id": discovery_id or _new_id(),
        "generated_at": _iso(moment),
        "discovery_mode": discovery_mode,
        "query": raw["query"],
        "time_window_hours": raw["time_window_hours"],
        "channel_profile_version": str(channel_profile["profile_version"]),
        "channel_profile_name": str(channel_profile["name"]),
        "candidates": normalized,
        "display_candidate_ids": display_ids,
        "watch_candidate_count": sum(item["eligibility_status"] == "watch" for item in normalized),
        "rejected_candidate_count": sum(item["eligibility_status"] == "rejected" for item in normalized),
        "limitations": [
            "Source Seeds 是后续研究入口，不是已确认事实或完整 Evidence Ledger。",
            "Creator attention 如有仅是辅助讨论信号，不作为事实证据，也不收集创作者稿件或字幕。",
        ],
    }
    validate_candidate_set(artifact)
    return TopicCandidateSet.from_dict(artifact)


def prepare_codex_discovery(
    raw: dict, channel_profile: Mapping[str, object], **kwargs: object
) -> TopicCandidateSet:
    """Prepare a Candidate Set after the Codex Skill has opened Source Seed pages."""

    kwargs["discovery_mode"] = "codex_skill"
    return prepare_discovery(raw, channel_profile, **kwargs)


def parse_selection(value: str) -> int:
    clean = value.strip()
    if clean.startswith("研究"):
        clean = clean[2:].strip()
    if not clean.isdigit() or int(clean) < 1:
        raise DiscoveryValidationError("请选择候选编号，例如“1”或“研究 1”。")
    return int(clean)


def build_research_handoff(candidate_set: TopicCandidateSet, selection: str) -> dict:
    """Build the structured bridge into V0.2 Research without parsing Markdown."""

    validate_candidate_set(candidate_set)
    position = parse_selection(selection)
    display = candidate_set.display_candidate_ids
    if position > len(display):
        raise DiscoveryValidationError("候选编号不存在，请回复当前列表中的编号。")
    candidate_id = display[position - 1]
    candidate = next(item for item in candidate_set.candidates if item["candidate_id"] == candidate_id)
    handoff = {
        "artifact_version": "0.3",
        "discovery_id": candidate_set.discovery_id,
        "selected_position": position,
        "candidate_id": candidate_id,
        "title": candidate["title"],
        "research_question": candidate["research_question"],
        "core_tension": candidate["core_tension"],
        "why_now": candidate["why_now"],
        "risk_level": candidate["risk_level"],
        "risk_notes": candidate["risk_notes"],
        "warnings": candidate["warnings"] + candidate["eligibility_reasons"],
        "source_seeds": candidate["source_seeds"],
    }
    validate_research_handoff(handoff)
    return handoff
