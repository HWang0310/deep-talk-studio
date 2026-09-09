"""Immutable persistence for episode visual preference artifacts."""

import json
import re
from pathlib import Path
from typing import Mapping

from .episode_visual_preference import validate_episode_visual_preference


class EpisodeVisualPreferenceStorageError(ValueError):
    pass


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", str(value)):
        raise EpisodeVisualPreferenceStorageError("Episode Visual Preference ID 不安全")
    return str(value)


def save_episode_visual_preference(preference: Mapping, root: Path) -> Path:
    directory = Path(root) / _safe_id(preference["preference_id"])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"episode-visual-preference-r{int(preference['revision']):04d}.json"
    if path.exists():
        raise EpisodeVisualPreferenceStorageError("Episode Visual Preference 已存在，不得覆盖")
    path.write_text(json.dumps(dict(preference), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_episode_visual_preference(path: Path, persistent_default: Mapping) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError
        validate_episode_visual_preference(value, persistent_default)
        return value
    except Exception as exc:
        raise EpisodeVisualPreferenceStorageError("Episode Visual Preference 工件无效") from exc
