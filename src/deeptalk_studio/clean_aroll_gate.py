"""Immutable Clean A-roll acceptance boundary.

The gate can refuse a file that plainly contains an announced full retake, but
it never ranks takes, creates an edit decision, or changes user media.  Normal
pauses, filler words, ad-libs, and natural wording changes are not blockers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class CleanARollGateError(ValueError):
    pass


@dataclass(frozen=True)
class CleanARollGateResult:
    status: str
    media_id: str
    media_digest: str
    blocking_pattern_count: int
    user_message: str

    def to_dict(self) -> dict:
        return {
            "artifact_version": "clean-aroll-gate/1",
            "status": self.status,
            "media_id": self.media_id,
            "media_digest": self.media_digest,
            "blocking_pattern_count": self.blocking_pattern_count,
            "user_message": self.user_message,
        }


def _text(transcript: Mapping | None) -> str:
    if not transcript:
        return ""
    if isinstance(transcript.get("text"), str):
        return transcript["text"]
    return "".join(str(item.get("text", "")) for item in transcript.get("timed_units", []))


def _explicit_full_retake_count(text: str) -> int:
    """Count only explicit production retake signals, never ordinary speech flaws."""
    normalized = "".join(str(text).split())
    markers = ("重新录一遍", "重新录一次", "从头再录", "这一段重录", "重录这一段", "重录一次")
    return sum(normalized.count(marker) for marker in markers)


def inspect_clean_aroll(media: Mapping, transcript: Mapping | None = None) -> CleanARollGateResult:
    if media.get("media_kind") != "video" or not str(media.get("media_id", "")).strip() or len(str(media.get("artifact_digest", ""))) != 64:
        raise CleanARollGateError("Clean A-roll 媒体身份无效")
    blocker_count = _explicit_full_retake_count(_text(transcript))
    if transcript:
        try:
            complete_runs = int(transcript.get("complete_script_run_count", 1))
        except (TypeError, ValueError):
            complete_runs = 1
        if complete_runs > 1:
            blocker_count += complete_runs - 1
    if blocker_count:
        return CleanARollGateResult(
            "needs_manual_cleanup", str(media["media_id"]), str(media["artifact_digest"]), blocker_count,
            "这还不是稳定的 Clean A-roll，请先完成一次人工清理后重新提供。",
        )
    return CleanARollGateResult("accepted", str(media["media_id"]), str(media["artifact_digest"]), 0, "Clean A-roll 已接受。")


def require_clean_aroll(media: Mapping, transcript: Mapping | None = None) -> CleanARollGateResult:
    result = inspect_clean_aroll(media, transcript)
    if result.status != "accepted":
        raise CleanARollGateError(result.user_message)
    return result
