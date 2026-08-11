"""Versioned visual identity and renderer defaults for Production 0.6.1."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCTION_PROFILE = REPO_ROOT / "config" / "production-profile.json"


class ProductionValidationError(ValueError):
    """A production contract, environment or safety error safe to show users."""


def load_production_profile(
    path: Optional[Path] = None, *, data: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    if data is not None:
        profile = deepcopy(dict(data))
    else:
        selected = Path(path or DEFAULT_PRODUCTION_PROFILE)
        try:
            profile = json.loads(selected.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductionValidationError(f"无法读取 Production Profile：{selected}") from exc
    expected = {
        "profile_version", "platform", "default_renderer", "canvas", "design_tokens",
        "scene_defaults", "dependencies",
    }
    if not isinstance(profile, dict) or set(profile) != expected:
        raise ProductionValidationError("Production Profile 字段不完整或包含未知字段")
    if profile["profile_version"] != "0.6.1" or profile["platform"] != "bilibili":
        raise ProductionValidationError("V0.6.1 必须使用 Bilibili Production Profile 0.6.1")
    if profile["default_renderer"] not in {"remotion", "hyperframes"}:
        raise ProductionValidationError("default_renderer 必须是 remotion 或 hyperframes")
    if profile["canvas"] != {
        "width": 1920, "height": 1080, "aspect_ratio": "16:9", "fps": 30,
    }:
        raise ProductionValidationError("V0.6 默认画布必须是 1920×1080、16:9、30 fps")
    token_keys = {
        "colors", "typography", "spacing_unit", "safe_area", "motion_intensity",
        "source_attribution_style",
    }
    tokens = profile["design_tokens"]
    if not isinstance(tokens, dict) or set(tokens) != token_keys:
        raise ProductionValidationError("Production Profile design_tokens 字段无效")
    if set(tokens["colors"]) != {
        "background", "surface", "foreground", "muted", "accent", "danger",
    } or set(tokens["typography"]) != {"display", "body", "data"}:
        raise ProductionValidationError("Production Profile 颜色或字体 token 不完整")
    if tokens["safe_area"] != {"horizontal": 96, "vertical": 100}:
        raise ProductionValidationError("Production Profile safe area 必须保留 96×100 像素边距")
    if set(profile["dependencies"]) != {"remotion", "hyperframes", "gsap"}:
        raise ProductionValidationError("Production Profile dependency lock 字段无效")
    if not all(str(value).strip() for value in profile["dependencies"].values()):
        raise ProductionValidationError("Production Profile dependency version 不能为空")
    return profile
