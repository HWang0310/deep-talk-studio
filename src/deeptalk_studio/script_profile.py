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
    base_required = {
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
    if not isinstance(profile, dict) or not base_required.issubset(profile):
        raise ScriptValidationError("Script Profile 字段不完整或包含未知字段")
    version = profile["profile_version"]
    expected = base_required | ({"duration_range_minutes", "quality_gate_checks"} if version == "1" else set())
    if set(profile) != expected:
        raise ScriptValidationError("Script Profile 字段不完整或包含未知字段")
    if version not in {"0.4", "1"}:
        raise ScriptValidationError("只支持 Script Profile 0.4 或 1")
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
    if version == "1":
        duration_range = profile["duration_range_minutes"]
        if duration_range != [5, 6]:
            raise ScriptValidationError("Script Profile 1 的正式时长范围必须为 5 到 6 分钟")
        checks = profile["quality_gate_checks"]
        if not isinstance(checks, list) or len(checks) != 17 or len(set(checks)) != 17:
            raise ScriptValidationError("Script Profile 1 必须声明 17 项 Script Quality Gate")
    return profile


def parse_target_duration(value: str, default: float = 12) -> float:
    clean = (value or "").strip()
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|到|至)\s*(\d+(?:\.\d+)?)\s*分钟", clean)
    match = re.search(r"(\d+(?:\.\d+)?)\s*分钟", clean)
    if range_match:
        duration = (float(range_match.group(1)) + float(range_match.group(2))) / 2
    elif match:
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
