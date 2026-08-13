"""OpenAI file-transcription adapter with evidenced chunk-local timestamps."""

from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple

from ..narration_media import canonical_digest
from ..transcription_chunking import TranscriptionChunkPlan
from .base import (
    ProviderTimedUnit,
    ProviderTranscript,
    TranscriptionProviderError,
    boundary_risks_from_plan,
    validate_provider_units,
)


OPENAI_TRANSCRIPTION_CAPABILITIES = {
    "verified_on": "2026-08-13",
    "documentation": [
        "https://developers.openai.com/api/docs/guides/speech-to-text",
        "https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create",
    ],
    "endpoint": "/v1/audio/transcriptions",
    "word_timestamp_model": "whisper-1",
    "response_format": "verbose_json",
    "timestamp_granularities": ["word", "segment"],
    "file_limit": "25 MB",
}


class TranscriptionCapabilityError(TranscriptionProviderError):
    """The configured provider/model cannot supply required real timestamps."""


class TranscriptionEnvironmentError(RuntimeError):
    """API/key/network environment prevented a provider call."""


class OpenAITranscriptionTransport(Protocol):
    def create(
        self,
        file_path: str,
        model: str,
        response_format: str,
        timestamp_granularities: Sequence[str],
    ) -> Mapping[str, Any]:
        ...


class OpenAISDKTranscriptionTransport:
    """Thin official-SDK transport; Core still owns every timestamp decision."""

    def __init__(self, *, api_key: str, client_factory: Optional[Callable[..., Any]] = None):
        if not api_key:
            raise TranscriptionEnvironmentError("OpenAI API key 不可用")
        if client_factory is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise TranscriptionEnvironmentError("OpenAI Python SDK 未安装") from exc
            client_factory = OpenAI
        self._client = client_factory(api_key=api_key)

    def create(self, file_path, model, response_format, timestamp_granularities):
        try:
            with open(file_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format=response_format,
                    timestamp_granularities=list(timestamp_granularities),
                )
        except Exception as exc:
            raise TranscriptionEnvironmentError("OpenAI transcription SDK 调用失败") from exc
        if isinstance(response, Mapping):
            return dict(response)
        if hasattr(response, "model_dump"):
            value = response.model_dump()
            if isinstance(value, Mapping):
                return dict(value)
        raise TranscriptionCapabilityError("OpenAI SDK response 无法转换为时间化转录")


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TranscriptionCapabilityError(f"OpenAI {field} 无效") from exc
    if not result.is_finite():
        raise TranscriptionCapabilityError(f"OpenAI {field} 无效")
    return result


def _intersecting_risks(
    plan: TranscriptionChunkPlan, chunk_index: int, start: Decimal, end: Decimal
) -> Tuple[str, ...]:
    chunk = plan.chunks[chunk_index]
    global_start = chunk.extracted_start_seconds + start
    global_end = chunk.extracted_start_seconds + end
    risk_ids = []
    for boundary in plan.boundaries:
        if (
            boundary.boundary_risk != "high"
            or boundary.guard_start_seconds is None
            or boundary.guard_end_seconds is None
        ):
            continue
        if global_start < boundary.guard_end_seconds and global_end > boundary.guard_start_seconds:
            risk_ids.append(f"CBR-{boundary.boundary_index:04d}")
    return tuple(risk_ids)


class OpenAITranscriptionProvider:
    def __init__(self, *, api_key: str, transport: OpenAITranscriptionTransport):
        if not api_key:
            raise TranscriptionEnvironmentError("OpenAI API key 不可用")
        self._api_key = api_key
        self._transport = transport

    def transcribe(
        self,
        extracted_audio_artifact: Dict[str, Any],
        chunk_plan: TranscriptionChunkPlan,
        language: str,
        configured_model: str,
    ) -> ProviderTranscript:
        if configured_model != "whisper-1":
            raise TranscriptionCapabilityError(
                f"{configured_model} 在当前适配器中没有获准的真实 word 时间戳能力"
            )
        units: List[ProviderTimedUnit] = []
        response_digests = []
        request_ids = []
        provider_order = 0
        selected_granularity = "word"
        observed_granularities = set()
        for chunk in chunk_plan.chunks:
            try:
                response = self._transport.create(
                    str(chunk.path), configured_model, "verbose_json", ["word"]
                )
            except Exception as exc:
                raise TranscriptionEnvironmentError(
                    "OpenAI transcription 环境不可用；密钥、网络或 API 调用失败"
                ) from exc
            if not isinstance(response, Mapping):
                raise TranscriptionCapabilityError("OpenAI transcription response 不是对象")
            words = response.get("words")
            segments = response.get("segments")
            if isinstance(words, list) and words:
                timed_values = words
                granularity = "word"
                text_field = "word"
            elif isinstance(segments, list) and segments:
                timed_values = segments
                granularity = "segment"
                text_field = "text"
                selected_granularity = "segment"
            else:
                raise TranscriptionCapabilityError(
                    "OpenAI response 缺少真实 word 或 segment 时间戳"
                )
            observed_granularities.add(granularity)
            if len(observed_granularities) > 1:
                raise TranscriptionCapabilityError(
                    "OpenAI 各 chunk 的 timestamp granularity 不一致"
                )
            response_digests.append(canonical_digest(dict(response)))
            request_ids.append(str(response.get("request_id") or ""))
            for value in timed_values:
                if not isinstance(value, Mapping):
                    raise TranscriptionCapabilityError(
                        f"OpenAI {granularity} timestamp 结构无效"
                    )
                start = _decimal(value.get("start"), f"{granularity}.start")
                end = _decimal(value.get("end"), f"{granularity}.end")
                units.append(
                    ProviderTimedUnit(
                        chunk_index=chunk.chunk_index,
                        provider_order=provider_order,
                        local_start_seconds=start,
                        local_end_seconds=end,
                        spoken_text=str(value.get(text_field) or ""),
                        boundary_risk_ids=_intersecting_risks(
                            chunk_plan, chunk.chunk_index, start, end
                        ),
                    )
                )
                provider_order += 1
        validate_provider_units(units, chunk_plan)
        metadata = {
            "capability_record": OPENAI_TRANSCRIPTION_CAPABILITIES,
            "request_ids": request_ids,
            "response_digests": response_digests,
            "chunk_plan_digest": chunk_plan.digest,
            "selected_timestamp_granularity": selected_granularity,
            "used_previous_chunk_prompt": False,
            "used_overlap": False,
        }
        return ProviderTranscript(
            provider="openai",
            provider_model=configured_model,
            provider_model_version="",
            provider_request_id=",".join(value for value in request_ids if value),
            language=language,
            timestamp_granularity=selected_granularity,
            units=tuple(units),
            boundary_risks=boundary_risks_from_plan(chunk_plan),
            raw_metadata=metadata,
            raw_response_digest=canonical_digest(response_digests),
            chunk_plan_digest=chunk_plan.digest,
        )
