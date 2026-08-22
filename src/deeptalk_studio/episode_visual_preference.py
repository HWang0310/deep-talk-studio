"""Versioned, natural-language episode visual preference resolution."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "config" / "episode-visual-default.json"
PREFERENCE_KEYS = (
    "overall_visual_density",
    "real_material_preference",
    "motion_preference",
    "a_roll_preference",
)
PREFERENCE_VALUES = {"low", "balanced", "high"}


class EpisodeVisualPreferenceError(ValueError):
    pass


def _digest(value: Mapping, field: str) -> str:
    payload = deepcopy(dict(value))
    payload.pop(field, None)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_episode_visual_default(path=None) -> dict:
    try:
        profile = json.loads(Path(path or DEFAULT_PROFILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EpisodeVisualPreferenceError("无法读取长期视觉默认风格") from exc
    if set(profile) != {"artifact_version", "preferences", "profile_digest"}:
        raise EpisodeVisualPreferenceError("长期视觉默认风格字段无效")
    if profile.get("artifact_version") != "episode-visual-default/1":
        raise EpisodeVisualPreferenceError("长期视觉默认风格版本无效")
    if set(profile.get("preferences", {})) != set(PREFERENCE_KEYS) or set(profile["preferences"].values()) - PREFERENCE_VALUES:
        raise EpisodeVisualPreferenceError("长期视觉默认偏好无效")
    if profile.get("profile_digest") != _digest(profile, "profile_digest"):
        raise EpisodeVisualPreferenceError("长期视觉默认风格 digest 无效")
    return profile


def _has_more(text: str) -> bool:
    return any(token in text for token in ("多一点", "更多", "丰富一点", "增强", "增加"))


def _has_less(text: str) -> bool:
    return any(token in text for token in ("少一点", "收一点", "收些", "减少", "别太多"))


def _scope(text: str, *, human_preview: bool) -> str:
    if human_preview:
        return "human_preview"
    if re.search(r"(?:以后|今后|之后).*(?:默认|都这样|一直这样)|(?:默认|都这样|一直这样).*(?:以后|今后|之后)", text):
        return "persistent"
    return "episode"


def parse_visual_preference_feedback(text: str, *, human_preview: bool = False) -> dict:
    raw = str(text).strip()
    if not raw:
        raise EpisodeVisualPreferenceError("视觉偏好不能是空白")
    patch = {}
    intents = []
    material_words = ("素材", "截图", "文件", "证据", "网页", "真实画面")
    motion_words = ("动画", "motion", "机制画面", "动态")
    aroll_words = ("真人", "本人", "a-roll", "A-roll")
    overall_words = ("整体", "视觉", "画面")
    if any(word in raw for word in material_words):
        if _has_more(raw): patch["real_material_preference"] = "high"; intents.append("real_material_more")
        elif _has_less(raw): patch["real_material_preference"] = "low"; intents.append("real_material_less")
    if any(word in raw for word in motion_words):
        if _has_more(raw): patch["motion_preference"] = "high"; intents.append("motion_more")
        elif _has_less(raw): patch["motion_preference"] = "low"; intents.append("motion_less")
    if any(word in raw for word in aroll_words):
        if any(token in raw for token in ("多留", "一直留", "留真人", "结尾多留", "多看")):
            patch["a_roll_preference"] = "high"; intents.append("aroll_more")
        elif _has_less(raw):
            patch["a_roll_preference"] = "low"; intents.append("aroll_less")
    if any(word in raw for word in overall_words):
        if _has_more(raw): patch["overall_visual_density"] = "high"; intents.append("overall_more")
        elif _has_less(raw): patch["overall_visual_density"] = "low"; intents.append("overall_less")
    if {"real_material_preference", "motion_preference"} <= set(patch) and all(value == "high" for value in patch.values() if value == "high"):
        patch.setdefault("overall_visual_density", "high")
    return {"scope": _scope(raw, human_preview=human_preview), "raw_text": raw, "patch": patch, "recognized_intents": intents}


def _resolved(default: Mapping, override: Mapping, revisions: Sequence[Mapping]) -> dict:
    result = dict(default["preferences"])
    result.update(override["patch"])
    for revision in revisions:
        result.update(revision["patch"])
    return result


def build_episode_visual_preference(
    persistent_default: Mapping,
    episode_feedback: str,
    *,
    preference_id: str,
    created_at: str,
    human_preview_feedback: Sequence[str] = (),
    revision: int = 1,
    previous_revision: int = 0,
) -> dict:
    default = load_episode_visual_default() if persistent_default is None else dict(persistent_default)
    if default != load_episode_visual_default(DEFAULT_PROFILE) and default.get("profile_digest") != _digest(default, "profile_digest"):
        raise EpisodeVisualPreferenceError("长期视觉默认风格不可信")
    override = parse_visual_preference_feedback(episode_feedback)
    if override["scope"] == "persistent":
        raise EpisodeVisualPreferenceError("本期 Episode Override 不能直接改写长期默认")
    revisions = [parse_visual_preference_feedback(item, human_preview=True) for item in human_preview_feedback]
    data = {
        "artifact_version": "episode-visual-preference/1",
        "preference_id": str(preference_id),
        "revision": int(revision),
        "previous_revision": int(previous_revision),
        "created_at": str(created_at),
        "persistent_default": {"profile_digest": default["profile_digest"], "preferences": dict(default["preferences"])},
        "episode_override": override,
        "human_preview_revisions": revisions,
        "resolved_preference": _resolved(default, override, revisions),
    }
    data["preference_digest"] = _digest(data, "preference_digest")
    return data


def validate_episode_visual_preference(value: Mapping, persistent_default: Mapping) -> None:
    expected = {
        "artifact_version", "preference_id", "revision", "previous_revision", "created_at",
        "persistent_default", "episode_override", "human_preview_revisions", "resolved_preference", "preference_digest",
    }
    if set(value) != expected or value.get("artifact_version") != "episode-visual-preference/1":
        raise EpisodeVisualPreferenceError("Episode Visual Preference 字段或版本无效")
    default = dict(persistent_default)
    if value["persistent_default"] != {"profile_digest": default.get("profile_digest"), "preferences": default.get("preferences")}:
        raise EpisodeVisualPreferenceError("Episode Visual Preference 长期默认 binding 无效")
    override = parse_visual_preference_feedback(value["episode_override"]["raw_text"])
    if override != value["episode_override"] or override["scope"] != "episode":
        raise EpisodeVisualPreferenceError("Episode Override 不是确定性自然语言解析结果")
    revisions = [parse_visual_preference_feedback(item["raw_text"], human_preview=True) for item in value["human_preview_revisions"]]
    if revisions != value["human_preview_revisions"]:
        raise EpisodeVisualPreferenceError("Human Preview Revision 不是确定性自然语言解析结果")
    if value["resolved_preference"] != _resolved(default, override, revisions):
        raise EpisodeVisualPreferenceError("Episode Visual Preference precedence 无效")
    if set(value["resolved_preference"]) != set(PREFERENCE_KEYS) or set(value["resolved_preference"].values()) - PREFERENCE_VALUES:
        raise EpisodeVisualPreferenceError("Episode Visual Preference 取值无效")
    if value.get("preference_digest") != _digest(value, "preference_digest"):
        raise EpisodeVisualPreferenceError("Episode Visual Preference digest 无效")
