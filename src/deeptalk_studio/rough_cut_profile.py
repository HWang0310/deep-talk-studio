"""Derived rough-cut duration and fixed aligned-preview profiles."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Optional


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUGH_CUT = ROOT / "config/rough-cut-duration-profile.json"
DEFAULT_PREVIEW = ROOT / "config/aligned-preview-profile.json"


class EditBridgeProfileError(ValueError):
    pass


def _digest(value, field="profile_digest"):
    payload = deepcopy(dict(value)); payload.pop(field, None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _material_digest(profile: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(profile), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_rough_cut_profile(material_profile: Mapping[str, Any], path: Optional[Path] = None):
    try: raw = json.loads(Path(path or DEFAULT_ROUGH_CUT).read_text())
    except (OSError, json.JSONDecodeError) as exc: raise EditBridgeProfileError("无法读取 Rough Cut Profile") from exc
    if set(raw) != {"artifact_version", "still_exposure_seconds", "source_profile_version", "source_profile_digest", "profile_digest"}:
        raise EditBridgeProfileError("Rough Cut Profile 字段无效")
    if material_profile.get("profile_version") != "0.5" or raw["artifact_version"] != "rough-cut-duration-profile/1":
        raise EditBridgeProfileError("Rough Cut Profile 来源版本无效")
    if raw["still_exposure_seconds"] != material_profile.get("default_cue_duration_seconds"):
        raise EditBridgeProfileError("still exposure 必须继承 Material Profile")
    result = dict(raw)
    result["source_profile_digest"] = _material_digest(material_profile)
    result["profile_digest"] = _digest(result)
    return result


def load_aligned_preview_profile(path: Optional[Path] = None):
    try: result = json.loads(Path(path or DEFAULT_PREVIEW).read_text())
    except (OSError, json.JSONDecodeError) as exc: raise EditBridgeProfileError("无法读取 Aligned Preview Profile") from exc
    expected = {
        "artifact_version": "aligned-preview-profile/1", "width": 1920, "height": 1080,
        "aspect_ratio": "16:9", "fps": 30, "frame_rounding": "ceil",
        "out_frame_semantics": "exclusive", "audio_policy": "single_clean_aroll_audio",
    }
    if {key: result.get(key) for key in expected} != expected or set(result) != set(expected) | {"profile_digest"}:
        raise EditBridgeProfileError("Aligned Preview Profile 受控值无效")
    if result["profile_digest"] != _digest(result):
        raise EditBridgeProfileError("Aligned Preview Profile digest 不匹配")
    return result
