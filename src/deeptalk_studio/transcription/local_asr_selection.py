"""Strict parser for the official whisper.cpp full JSON token evidence.

The original selection Gate used this parser as an evidence-only spike.  The
parser is intentionally kept provider-neutral so the production local provider
can reuse exactly the same timestamp contract.  VibeASR.cpp is rejected unless
a future runtime exposes machine-owned media timestamps; prompt-generated
``Start``/``End`` fields are never accepted as evidence.
"""

import json
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..narration_media import canonical_digest
from ..transcription_chunking import TranscriptionChunkPlan
from .base import ProviderTimedUnit, ProviderTranscript, TranscriptionProviderError


class LocalASRSelectionError(TranscriptionProviderError):
    """A local candidate result cannot satisfy the selection evidence contract."""


def _milliseconds(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value)) / Decimal("1000")
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise LocalASRSelectionError(f"whisper.cpp {field} 不是有效毫秒值") from exc
    if not result.is_finite() or result < 0:
        raise LocalASRSelectionError(f"whisper.cpp {field} 不是有效时间")
    return result


def _control_token(text: str) -> bool:
    # whisper.cpp uses bracketed control tokens such as [_BEG_] and [_TT_962].
    return text.startswith("[_") and text.endswith("]")


def _has_matchable_text(text: str) -> bool:
    return any(
        char.isalnum() or ("\u3400" <= char <= "\u9fff")
        for char in text
        if not unicodedata.category(char).startswith(("P", "S"))
    )


def _intersecting_risks(
    chunk_plan: TranscriptionChunkPlan, chunk_index: int, start: Decimal, end: Decimal
) -> Tuple[str, ...]:
    """Bind a runtime token to an existing high-risk chunk boundary, if any."""

    chunk = chunk_plan.chunks[chunk_index]
    global_start = chunk.extracted_start_seconds + start
    global_end = chunk.extracted_start_seconds + end
    risk_ids = []
    for boundary in chunk_plan.boundaries:
        if (
            boundary.boundary_risk != "high"
            or boundary.guard_start_seconds is None
            or boundary.guard_end_seconds is None
        ):
            continue
        if global_start < boundary.guard_end_seconds and global_end > boundary.guard_start_seconds:
            risk_ids.append(f"CBR-{boundary.boundary_index:04d}")
    return tuple(risk_ids)


def inspect_whisper_cpp_token_overlaps(
    path: Path,
    *,
    chunk_index: int,
    provider_order_start: int,
    model: str,
    dtw_preset: str,
    runtime_version: str,
    is_chunk_boundary: bool = False,
) -> Tuple[Dict[str, Any], ...]:
    """Return raw DTW overlap evidence without changing any runtime timestamp.

    Only spoken candidates that the Provider would preserve are compared. This
    makes an overlap evidence item a direct explanation of the exact canonical
    Provider unit pair that must currently fail closed.
    """

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalASRSelectionError("无法读取 whisper.cpp JSON 时间证据") from exc
    transcriptions = payload.get("transcription")
    if not isinstance(transcriptions, list):
        raise LocalASRSelectionError("whisper.cpp JSON 缺少 transcription 数组")
    response_digest = canonical_digest(payload)
    candidates = []
    provider_order = provider_order_start
    for segment_index, segment in enumerate(transcriptions):
        if not isinstance(segment, Mapping):
            raise LocalASRSelectionError("whisper.cpp segment 结构无效")
        tokens = segment.get("tokens")
        if not isinstance(tokens, list):
            raise LocalASRSelectionError("whisper.cpp JSON 缺少 token offsets")
        for token_index, token in enumerate(tokens):
            if not isinstance(token, Mapping):
                raise LocalASRSelectionError("whisper.cpp token 结构无效")
            text = str(token.get("text") or "")
            is_control = _control_token(text)
            if not text or is_control or not _has_matchable_text(text):
                continue
            offsets = token.get("offsets")
            if not isinstance(offsets, Mapping):
                raise LocalASRSelectionError("whisper.cpp token 缺少 offsets")
            start = _milliseconds(offsets.get("from"), "token.from")
            end = _milliseconds(offsets.get("to"), "token.to")
            if end <= start:
                continue
            candidates.append(
                {
                    "segment_index": segment_index,
                    "raw_token_index": token_index,
                    "provider_order": provider_order,
                    "text": text,
                    "start": start,
                    "end": end,
                    "is_control_token": is_control,
                }
            )
            provider_order += 1
    overlaps = []
    for previous, current in zip(candidates, candidates[1:]):
        if current["start"] >= previous["end"]:
            continue
        overlaps.append(
            {
                "chunk_id": f"chunk-{chunk_index:04d}",
                "chunk_index": chunk_index,
                "previous_segment_index": previous["segment_index"],
                "current_segment_index": current["segment_index"],
                "same_segment": previous["segment_index"] == current["segment_index"],
                "previous_raw_token_index": previous["raw_token_index"],
                "current_raw_token_index": current["raw_token_index"],
                "previous_provider_order": previous["provider_order"],
                "current_provider_order": current["provider_order"],
                "previous_token_text": previous["text"],
                "current_token_text": current["text"],
                "previous_raw_start_seconds": format(previous["start"], "f"),
                "previous_raw_end_seconds": format(previous["end"], "f"),
                "current_raw_start_seconds": format(current["start"], "f"),
                "current_raw_end_seconds": format(current["end"], "f"),
                "overlap_duration_seconds": format(previous["end"] - current["start"], "f"),
                "previous_is_control_token": previous["is_control_token"],
                "current_is_control_token": current["is_control_token"],
                "is_chunk_boundary": is_chunk_boundary,
                "model": model,
                "dtw_preset": dtw_preset,
                "runtime_version": runtime_version,
                "raw_response_digest": response_digest,
            }
        )
    return tuple(overlaps)


def parse_whisper_cpp_json(
    path: Path,
    *,
    chunk_index: int = 0,
    model_version: str,
    dtw_preset: str = "medium",
    chunk_plan: Optional[TranscriptionChunkPlan] = None,
    provider_order_start: int = 0,
    provider_request_id: str = "local-eval-whisper-cpp",
) -> ProviderTranscript:
    """Parse direct token offsets emitted by official whisper.cpp JSON output.

    The parser only accepts the offsets already emitted by the runtime.  It does
    not interpolate from segments, characters, confidence, or token order.
    """

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalASRSelectionError("无法读取 whisper.cpp JSON 评测结果") from exc
    transcriptions = payload.get("transcription")
    if not isinstance(transcriptions, list):
        raise LocalASRSelectionError("whisper.cpp JSON 缺少 transcription 数组")

    units: List[ProviderTimedUnit] = []
    for segment in transcriptions:
        if not isinstance(segment, Mapping):
            raise LocalASRSelectionError("whisper.cpp segment 结构无效")
        tokens = segment.get("tokens")
        if not isinstance(tokens, list):
            raise LocalASRSelectionError("whisper.cpp JSON 缺少 token offsets")
        for token in tokens:
            if not isinstance(token, Mapping):
                raise LocalASRSelectionError("whisper.cpp token 结构无效")
            text = str(token.get("text") or "")
            if not text or _control_token(text) or not _has_matchable_text(text):
                continue
            offsets = token.get("offsets")
            timestamps = token.get("timestamps")
            # The integer offsets are the canonical machine-readable evidence;
            # the formatted timestamp strings are retained only as raw evidence.
            if not isinstance(offsets, Mapping):
                raise LocalASRSelectionError("whisper.cpp token 缺少 offsets")
            start = _milliseconds(offsets.get("from"), "token.from")
            end = _milliseconds(offsets.get("to"), "token.to")
            if end <= start:
                # Zero-width special/end markers are not spoken units.
                continue
            units.append(
                ProviderTimedUnit(
                    chunk_index=chunk_index,
                    provider_order=provider_order_start + len(units),
                    local_start_seconds=start,
                    local_end_seconds=end,
                    spoken_text=text,
                    provider_confidence=str(token.get("p") or ""),
                    boundary_risk_ids=(
                        _intersecting_risks(chunk_plan, chunk_index, start, end)
                        if chunk_plan is not None
                        else ()
                    ),
                )
            )
            if timestamps is not None and not isinstance(timestamps, Mapping):
                raise LocalASRSelectionError("whisper.cpp token timestamps 结构无效")
    if not units:
        raise LocalASRSelectionError("whisper.cpp JSON 没有可用 token 时间戳")

    if chunk_plan is not None:
        from .base import validate_provider_units

        validate_provider_units(units, chunk_plan)
        plan_digest = chunk_plan.digest
    else:
        plan_digest = ""
    language = str((payload.get("result") or {}).get("language") or payload.get("language") or "")
    metadata: Dict[str, Any] = {
        "source": "official_whisper_cpp_json",
        "timestamp_provenance": f"runtime token offsets from whisper.cpp --dtw {dtw_preset}",
        "raw_json_path": str(path),
        "token_unit_count": len(units),
        "model_type": str((payload.get("model") or {}).get("type") or ""),
        "language": language,
        "provider_request_id": provider_request_id,
    }
    return ProviderTranscript(
        provider="whisper.cpp",
        provider_model=str((payload.get("model") or {}).get("type") or "medium"),
        provider_model_version=model_version,
        provider_request_id=provider_request_id,
        language=language,
        timestamp_granularity="token",
        units=tuple(units),
        boundary_risks=(),
        raw_metadata=metadata,
        raw_response_digest=canonical_digest(payload),
        chunk_plan_digest=plan_digest,
    )


def vibeasr_timestamp_gate_failure() -> str:
    """Return the fixed reason VibeASR.cpp cannot pass the V1 timestamp Gate."""

    return (
        "VibeASR.cpp official asr_infer has no machine-owned media timestamp output. "
        "Its optional Start/End JSON shape is part of the language-model prompt/output, "
        "not an evidenced audio-to-token timeline; the real run therefore cannot form "
        "a truthful ProviderTranscript."
    )
