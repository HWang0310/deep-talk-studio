"""Frame-rate-neutral canonical time helpers for edit-bridge artifacts."""

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Union


DecimalLike = Union[Decimal, int, str]


def _decimal(value: DecimalLike, field: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} 必须是有效数字") from exc
    if not result.is_finite():
        raise ValueError(f"{field} 必须是有限数字")
    return result


def format_canonical_timecode(seconds: DecimalLike) -> str:
    """Format non-negative decimal seconds as unbounded HH:MM:SS.mmm."""

    value = _decimal(seconds, "seconds")
    if value < 0:
        raise ValueError("seconds 不能为负数")
    millis = int((value * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def preview_frame(seconds: DecimalLike, fps: DecimalLike = 30) -> int:
    """Derive a Preview frame by ceiling without changing canonical seconds."""

    value = _decimal(seconds, "seconds")
    rate = _decimal(fps, "fps")
    if value < 0:
        raise ValueError("seconds 不能为负数")
    if rate <= 0:
        raise ValueError("fps 必须大于 0")
    return int((value * rate).to_integral_value(rounding=ROUND_CEILING))


def format_preview_frame_timecode(frame: int, fps: int = 30) -> str:
    """Format an integer Preview frame for the fixed integer-fps renderer."""

    if isinstance(frame, bool) or not isinstance(frame, int) or frame < 0:
        raise ValueError("frame 必须是非负整数")
    if isinstance(fps, bool) or not isinstance(fps, int) or fps <= 0:
        raise ValueError("fps 必须是正整数")
    total_seconds, frame_part = divmod(frame, fps)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_part:02d}"
