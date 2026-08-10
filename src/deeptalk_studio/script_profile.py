"""Versioned Script Profile and conservative duration parsing."""

import json
import re
from pathlib import Path
from typing import Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCRIPT_PROFILE = REPO_ROOT / "config" / "script-profile.json"


class ScriptValidationError(ValueError):
    """A user-readable Script contract or grounding error."""


def load_script_profile(path: Optional[Path] = None) -> Dict[str, object]:
    profile_path = path or DEFAULT_SCRIPT_PROFILE
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScriptValidationError(f"无法读取 Script Profile：{profile_path}") from exc
    required = {
        "profile_version",
        "platform",
        "format",
        "language",
        "default_duration_minutes",
        "chars_per_minute",
        "duration_tolerance_ratio",
        "oral_style",
        "avoid",
        "required_elements",
        "originality_boundaries",
    }
    if not isinstance(profile, dict) or set(profile) != required:
        raise ScriptValidationError("Script Profile 字段不完整或包含未知字段")
    if profile["profile_version"] != "0.4":
        raise ScriptValidationError("V0.4 必须使用 Script Profile 0.4")
    if not 3 <= profile["default_duration_minutes"] <= 30:
        raise ScriptValidationError("默认口播时长必须在 3 到 30 分钟之间")
    if not isinstance(profile["chars_per_minute"], int) or profile["chars_per_minute"] <= 0:
        raise ScriptValidationError("chars_per_minute 必须是正整数")
    if not 0 < profile["duration_tolerance_ratio"] <= 0.5:
        raise ScriptValidationError("时长容差必须在 0 到 0.5 之间")
    for field in ("oral_style", "avoid", "required_elements", "originality_boundaries"):
        if not isinstance(profile[field], list) or not profile[field] or not all(
            isinstance(item, str) and item.strip() for item in profile[field]
        ):
            raise ScriptValidationError(f"Script Profile.{field} 必须是非空文本列表")
    return profile


def parse_target_duration(value: str, default: float = 12) -> float:
    clean = (value or "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*分钟", clean)
    if match:
        duration = float(match.group(1))
    elif "长一点" in clean or "做长" in clean:
        duration = 15.0
    elif any(token in clean for token in ("紧凑", "短一点", "压缩")):
        duration = 10.0
    else:
        duration = float(default)
    if not 3 <= duration <= 30:
        raise ScriptValidationError("目标口播时长必须在 3 到 30 分钟之间")
    return int(duration) if duration.is_integer() else duration
