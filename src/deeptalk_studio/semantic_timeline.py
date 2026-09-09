"""Readable real-A-roll semantic spans for the Asset Pack route."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence


class SemanticTimelineError(ValueError):
    pass


def build_semantic_timeline(
    script: Mapping,
    alignment: Mapping,
    fact_conflicts: Sequence[Mapping],
    *,
    timeline_id: str,
    created_at: str,
) -> dict:
    """Build one semantic span per safely aligned Script Beat.

    The real-time provenance marker prevents fixture or estimated timing from
    becoming a production clock.  Unsafe alignment and FACT_CONFLICT are
    intentionally retained as `keep_only` spans rather than being hidden.
    """
    if alignment.get("timing_provenance") != "actual_aroll_alignment":
        raise SemanticTimelineError("没有通过 Clean A-roll Alignment，不能生成正式真实时间轴")
    if len(str(alignment.get("artifact_digest", ""))) != 64 or len(str(alignment.get("transcript_digest", ""))) != 64:
        raise SemanticTimelineError("真实时间轴缺少 alignment lineage")
    clocks = {str(item.get("beat_id", "")): item for item in alignment.get("beat_timeline", [])}
    blocked = {str(item.get("beat_id", "")) for item in fact_conflicts if item.get("display_blocked")}
    spans = []
    previous_end = -1.0
    for index, beat in enumerate(script.get("beats", []), 1):
        beat_id = str(beat.get("beat_id", "")); clock = clocks.get(beat_id)
        if not clock:
            continue
        start = str(clock.get("actual_start_seconds", "")); end = str(clock.get("actual_end_seconds", ""))
        try:
            numeric_start = float(start); numeric_end = float(end)
        except (TypeError, ValueError):
            continue
        if numeric_start < previous_end or numeric_end <= numeric_start:
            raise SemanticTimelineError("真实时间轴不单调，不能创建视觉指令")
        previous_end = numeric_end
        safe = clock.get("alignment_status") == "aligned" and clock.get("confidence") in {"high", "medium"}
        spans.append({
            "span_id": f"ST{index:03d}",
            "beat_id": beat_id,
            "actual_start_seconds": start,
            "actual_end_seconds": end,
            "summary": str(beat.get("narration", "")).strip(),
            "alignment_status": str(clock.get("alignment_status", "")),
            "visual_eligibility": "keep_only" if beat_id in blocked or not safe else "safe",
            "reason": "FACT_CONFLICT" if beat_id in blocked else ("safe_real_alignment" if safe else "alignment_uncertain"),
        })
    payload = {
        "artifact_version": "semantic-timeline/1",
        "timeline_id": str(timeline_id),
        "created_at": str(created_at),
        "timing_provenance": "actual_aroll_alignment",
        "alignment_digest": alignment["artifact_digest"],
        "transcript_digest": alignment["transcript_digest"],
        "spans": spans,
    }
    payload["timeline_digest"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return payload
