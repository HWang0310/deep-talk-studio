"""Versioned output and safety profile for Material Package 0.5."""

import json
from pathlib import Path
from typing import Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATERIAL_PROFILE = REPO_ROOT / "config" / "material-profile.json"


class MaterialValidationError(ValueError):
    """A user-readable material contract or safety error."""


def load_material_profile(path: Optional[Path] = None) -> Dict[str, object]:
    profile_path = path or DEFAULT_MATERIAL_PROFILE
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterialValidationError(f"无法读取 Material Profile：{profile_path}") from exc
    expected = {
        "profile_version", "platform", "canvas_width", "canvas_height",
        "aspect_ratio", "safe_area_percent", "visual_style", "avoid",
        "default_cue_duration_seconds", "max_download_bytes",
        "allowed_download_mime_types",
    }
    if not isinstance(profile, dict) or set(profile) != expected:
        raise MaterialValidationError("Material Profile 字段不完整或包含未知字段")
    if profile["profile_version"] != "0.5":
        raise MaterialValidationError("V0.5 必须使用 Material Profile 0.5")
    if (profile["canvas_width"], profile["canvas_height"], profile["aspect_ratio"]) != (
        1920, 1080, "16:9"
    ):
        raise MaterialValidationError("V0.5 默认画布必须是 B 站 1920×1080 16:9")
    if not isinstance(profile["max_download_bytes"], int) or profile["max_download_bytes"] <= 0:
        raise MaterialValidationError("max_download_bytes 必须是正整数")
    for field in ("visual_style", "avoid", "allowed_download_mime_types"):
        values = profile[field]
        if not isinstance(values, list) or not values or not all(
            isinstance(item, str) and item.strip() for item in values
        ):
            raise MaterialValidationError(f"Material Profile.{field} 必须是非空文本列表")
    return profile

