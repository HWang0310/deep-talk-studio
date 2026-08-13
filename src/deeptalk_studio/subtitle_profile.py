"""Single versioned Basic Subtitle V1 display profile."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "config" / "subtitle-profile.json"


class SubtitleProfileError(ValueError):
    pass


def _digest(value):
    payload = dict(value); payload.pop("profile_digest", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_subtitle_profile(path=None):
    try:
        profile = json.loads(Path(path or DEFAULT_PROFILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubtitleProfileError("无法读取 Subtitle Profile") from exc
    expected = {
        "artifact_version", "canvas_width", "canvas_height", "subtitle_region_top_px",
        "subtitle_region_bottom_px", "content_safe_bottom_px", "max_lines",
        "max_chars_per_line", "max_cue_duration_seconds", "max_join_gap_seconds",
        "font_size_px", "line_height_ratio", "plate_opacity", "horizontal_padding_px",
        "vertical_padding_px", "text_color", "plate_color", "render_mode", "profile_digest",
    }
    if set(profile) != expected or profile.get("artifact_version") != "subtitle-profile/1":
        raise SubtitleProfileError("Subtitle Profile 字段或版本无效")
    if (profile.get("canvas_width"), profile.get("canvas_height"), profile.get("max_lines")) != (1920, 1080, 2):
        raise SubtitleProfileError("Subtitle Profile 画布或行数无效")
    if not 0 < int(profile["content_safe_bottom_px"]) < int(profile["subtitle_region_top_px"]) < int(profile["subtitle_region_bottom_px"]) <= 1080:
        raise SubtitleProfileError("Subtitle safe area 无效")
    if profile.get("render_mode") != "burned_in_static_phrase" or profile.get("profile_digest") != _digest(profile):
        raise SubtitleProfileError("Subtitle Profile 受控值或 digest 无效")
    return profile
