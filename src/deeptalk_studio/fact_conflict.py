"""Detect when actual spoken high-risk facts diverge from approved facts.

The output is a display safety signal, not a transcript correction and never an
audio-edit instruction.  Its clocks are copied from real A-roll alignment.
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence


HIGH_RISK_KINDS = {"number", "date", "person", "organization", "work", "policy", "causality"}


def _text(transcript: Mapping) -> str:
    if isinstance(transcript.get("text"), str):
        return transcript["text"]
    return "".join(str(item.get("text", "")) for item in transcript.get("timed_units", []))


def _spoken_alternative(kind: str, approved: str, transcript_text: str) -> str:
    if kind == "number":
        candidates = re.findall(r"[零一二三四五六七八九十百千万亿0-9]+(?:\.\d+)?(?:元|万|亿|%|人|次|部)", transcript_text)
        return next((value for value in candidates if value != approved), "")
    return ""


def detect_fact_conflicts(script: Mapping, transcript: Mapping, alignment: Mapping, approved_facts: Sequence[Mapping]) -> list[dict]:
    """Return only explicit high-risk disagreements that must block display.

    `approved_facts` is intentionally a constrained input from reviewed
    upstream artifacts. It is not inferred from a freeform transcript.
    """
    transcript_text = _text(transcript)
    beats = {str(item.get("beat_id", "")): item for item in script.get("beats", [])}
    clocks = {str(item.get("beat_id", "")): item for item in alignment.get("beat_timeline", [])}
    results = []
    for fact in approved_facts:
        kind = str(fact.get("kind", ""))
        value = str(fact.get("value", "")).strip()
        beat_id = str(fact.get("beat_id", ""))
        if kind not in HIGH_RISK_KINDS or not value or beat_id not in beats or beat_id not in clocks:
            continue
        script_text = str(beats[beat_id].get("narration", ""))
        # A conflict must be an explicit approved fact present in the reviewed
        # beat but absent from the actual transcript while another explicit
        # conflicting value is supplied by the fact-binding caller.
        spoken_value = str(fact.get("spoken_value", "")).strip() or _spoken_alternative(kind, value, transcript_text)
        if not spoken_value or spoken_value == value or value not in script_text or spoken_value not in transcript_text:
            continue
        clock = clocks[beat_id]
        results.append({
            "artifact_version": "fact-conflict/1",
            "conflict_type": "FACT_CONFLICT",
            "beat_id": beat_id,
            "fact_kind": kind,
            "approved_value": value,
            "spoken_value": spoken_value,
            "actual_start_seconds": str(clock.get("actual_start_seconds", "")),
            "actual_end_seconds": str(clock.get("actual_end_seconds", "")),
            "display_blocked": True,
            "resolution": "保留原始音频；不得生成或显示错误事实素材。",
        })
    return results
