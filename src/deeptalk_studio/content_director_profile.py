"""Versioned Content Director profile."""

import json
from pathlib import Path
from typing import Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTENT_DIRECTOR_PROFILE = REPO_ROOT / "config" / "content-director-profile.json"


class ContentDirectorValidationError(ValueError):
    """A user-readable Content Director contract error."""


def load_content_director_profile(path: Optional[Path] = None) -> Dict[str, object]:
    profile_path = path or DEFAULT_CONTENT_DIRECTOR_PROFILE
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentDirectorValidationError(
            f"无法读取 Content Director Profile：{profile_path}"
        ) from exc
    required = {
        "profile_version", "platform", "language", "required_audience_dimensions",
        "thesis_gate_checks", "originality_boundary",
    }
    if not isinstance(profile, dict) or set(profile) != required:
        raise ContentDirectorValidationError("Content Director Profile 字段不完整或包含未知字段")
    if profile["profile_version"] != "1":
        raise ContentDirectorValidationError("Content Director 必须使用 Profile 1")
    for field in ("required_audience_dimensions", "thesis_gate_checks"):
        value = profile[field]
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ContentDirectorValidationError(f"Content Director Profile.{field} 必须是非空文本列表")
    return profile
