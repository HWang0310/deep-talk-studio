"""Deterministic Topic Discovery preflight, ranking and Research handoff."""

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence

from .discovery_derivation import (
    SCORE_WEIGHTS,
    calculate_total_score,
    canonical_provenance_context,
    derive_candidate_set_fields,
)
from .discovery_validation import (
    DiscoveryValidationError,
    validate_candidate_set,
    validate_discovery_raw,
    validate_research_handoff,
)
from .models import TopicCandidateSet


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHANNEL_PROFILE = REPO_ROOT / "config" / "channel-profile.json"
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


def prepare_discovery(
    raw: dict,
    channel_profile: Mapping[str, object],
    *,
    now: Optional[datetime] = None,
    discovery_id: str = "",
    provenance_urls: Optional[Iterable[str]] = None,
    discovery_mode: str = "openai_api",
    category_filter: Sequence[str] = (),
    inspection_manifest: Optional[Mapping[str, object]] = None,
) -> TopicCandidateSet:
    """Turn raw Discovery judgments into the machine-owned Candidate Set 0.3."""

    validate_discovery_raw(raw)
    if discovery_mode not in {"codex_skill", "openai_api", "fixture"}:
        raise DiscoveryValidationError("discovery_mode 无效")
    moment = now or _default_clock()
    try:
        provenance_context = canonical_provenance_context(
            provenance_urls, inspection_manifest
        )
    except ValueError as exc:
        raise DiscoveryValidationError(str(exc)) from None
    raw_candidates = list(raw["candidates"])
    if category_filter:
        allowed = set(category_filter)
        raw_candidates = [item for item in raw_candidates if item["category"] in allowed]
    fields = derive_candidate_set_fields(
        raw_candidates,
        generated_at=moment,
        discovery_mode=discovery_mode,
        provenance_context=provenance_context,
        stable_ids=True,
    )
    artifact = {
        "artifact_version": "0.3",
        "discovery_id": discovery_id or _new_id(),
        "generated_at": _iso(moment),
        "discovery_mode": discovery_mode,
        "query": raw["query"],
        "time_window_hours": raw["time_window_hours"],
        "channel_profile_version": str(channel_profile["profile_version"]),
        "channel_profile_name": str(channel_profile["name"]),
        "seed_provenance": provenance_context,
        **fields,
        "limitations": [
            "Source Seeds 是后续研究入口，不是已确认事实或完整 Evidence Ledger。",
            "Creator attention 如有仅是辅助讨论信号，不作为事实证据，也不收集创作者稿件或字幕。",
        ],
    }
    validate_candidate_set(artifact)
    return TopicCandidateSet.from_dict(artifact)


def prepare_codex_discovery(
    raw: dict,
    channel_profile: Mapping[str, object],
    inspection_manifest: Optional[Mapping[str, object]] = None,
    **kwargs: object,
) -> TopicCandidateSet:
    """Prepare a Candidate Set after the Codex Skill has opened Source Seed pages."""

    kwargs["discovery_mode"] = "codex_skill"
    kwargs["inspection_manifest"] = inspection_manifest
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
