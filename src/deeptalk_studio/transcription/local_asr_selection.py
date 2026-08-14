"""Evidence-only parsers used by the V1 local ASR selection Gate.

This module is deliberately not a production provider or a default bootstrap path.
It turns an official whisper.cpp JSON result into the existing provider-neutral
contract so a candidate can be tested through Timed Transcript and Script
Alignment without changing the V1 runtime selection.  VibeASR.cpp is rejected
unless a future runtime exposes machine-owned media timestamps; prompt-generated
``Start``/``End`` fields are never accepted as evidence.
"""

import json
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

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


def parse_whisper_cpp_json(
    path: Path,
    *,
    chunk_index: int = 0,
    model_version: str,
    chunk_plan: Optional[TranscriptionChunkPlan] = None,
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
                    provider_order=len(units),
                    local_start_seconds=start,
                    local_end_seconds=end,
                    spoken_text=text,
                    provider_confidence=str(token.get("p") or ""),
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
        "timestamp_provenance": "runtime token offsets from whisper.cpp --dtw medium",
        "raw_json_path": str(path),
        "token_unit_count": len(units),
        "model_type": str((payload.get("model") or {}).get("type") or ""),
        "language": language,
    }
    return ProviderTranscript(
        provider="whisper.cpp",
        provider_model=str((payload.get("model") or {}).get("type") or "medium"),
        provider_model_version=model_version,
        provider_request_id="local-eval-whisper-cpp",
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
