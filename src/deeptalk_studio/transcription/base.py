"""Provider-neutral, chunk-local timed transcription protocol."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Protocol, Sequence, Tuple

from ..transcription_chunking import TranscriptionChunkPlan


class TranscriptionProviderError(ValueError):
    """Provider input/output violates the neutral transcription contract."""


@dataclass(frozen=True)
class ProviderTimedUnit:
    chunk_index: int
    provider_order: int
    local_start_seconds: Decimal
    local_end_seconds: Decimal
    spoken_text: str
    provider_confidence: str = ""
    boundary_risk_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderBoundaryRisk:
    risk_id: str
    boundary_index: int
    guard_start_seconds: Decimal
    guard_end_seconds: Decimal
    risk_level: str
    reason: str
    chunk_plan_digest: str


@dataclass(frozen=True)
class ProviderTranscript:
    provider: str
    provider_model: str
    provider_model_version: str
    provider_request_id: str
    language: str
    timestamp_granularity: str
    units: Tuple[ProviderTimedUnit, ...]
    boundary_risks: Tuple[ProviderBoundaryRisk, ...]
    raw_metadata: Dict[str, Any]
    raw_response_digest: str
    chunk_plan_digest: str


class TranscriptionProvider(Protocol):
    def transcribe(
        self,
        extracted_audio_artifact: Dict[str, Any],
        chunk_plan: TranscriptionChunkPlan,
        language: str,
        configured_model: str,
    ) -> ProviderTranscript:
        ...


def boundary_risks_from_plan(plan: TranscriptionChunkPlan) -> Tuple[ProviderBoundaryRisk, ...]:
    risks = []
    for boundary in plan.boundaries:
        if boundary.boundary_risk != "high":
            continue
        if boundary.guard_start_seconds is None or boundary.guard_end_seconds is None:
            raise TranscriptionProviderError("high boundary risk 缺少 guard")
        risks.append(
            ProviderBoundaryRisk(
                risk_id=f"CBR-{boundary.boundary_index:04d}",
                boundary_index=boundary.boundary_index,
                guard_start_seconds=boundary.guard_start_seconds,
                guard_end_seconds=boundary.guard_end_seconds,
                risk_level="high",
                reason=boundary.reason,
                chunk_plan_digest=plan.digest,
            )
        )
    return tuple(risks)


def validate_provider_units(
    units: Sequence[ProviderTimedUnit], plan: TranscriptionChunkPlan
) -> None:
    if not units:
        raise TranscriptionProviderError("Provider Transcript 不能为空")
    known_risks = {risk.risk_id for risk in boundary_risks_from_plan(plan)}
    chunks = {chunk.chunk_index: chunk for chunk in plan.chunks}
    last_key = None
    for unit in units:
        if unit.chunk_index not in chunks:
            raise TranscriptionProviderError("Provider unit 引用了不存在的 chunk")
        if unit.provider_order < 0:
            raise TranscriptionProviderError("Provider unit order 不能为负数")
        if not unit.spoken_text.strip():
            raise TranscriptionProviderError("Provider unit spoken_text 不能为空")
        if unit.local_start_seconds < 0 or unit.local_end_seconds <= unit.local_start_seconds:
            raise TranscriptionProviderError("Provider unit local timestamp 无效")
        chunk_duration = chunks[unit.chunk_index].extracted_end_seconds - chunks[unit.chunk_index].extracted_start_seconds
        if unit.local_end_seconds > chunk_duration:
            raise TranscriptionProviderError("Provider unit 超出 request chunk")
        if not set(unit.boundary_risk_ids).issubset(known_risks):
            raise TranscriptionProviderError("Provider unit 引用了未知 boundary risk")
        key = (unit.chunk_index, unit.provider_order)
        if last_key is not None and key <= last_key:
            raise TranscriptionProviderError("Provider unit order 必须连续递增")
        last_key = key
