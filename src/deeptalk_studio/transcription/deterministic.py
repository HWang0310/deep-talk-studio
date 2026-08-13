"""Offline deterministic timed transcription provider for tests and evals."""

from typing import Any, Dict, Sequence

from ..narration_media import canonical_digest
from ..transcription_chunking import TranscriptionChunkPlan
from .base import (
    ProviderTimedUnit,
    ProviderTranscript,
    TranscriptionProviderError,
    boundary_risks_from_plan,
    validate_provider_units,
)


class DeterministicTranscriptionProvider:
    def __init__(self, units: Sequence[ProviderTimedUnit], *, granularity: str):
        if granularity not in {"word", "token", "segment"}:
            raise TranscriptionProviderError("timestamp granularity 无效")
        self._units = tuple(units)
        self._granularity = granularity

    def transcribe(
        self,
        extracted_audio_artifact: Dict[str, Any],
        chunk_plan: TranscriptionChunkPlan,
        language: str,
        configured_model: str,
    ) -> ProviderTranscript:
        validate_provider_units(self._units, chunk_plan)
        metadata = {
            "source": "deterministic_fixture",
            "unit_count": len(self._units),
            "extracted_audio_digest": extracted_audio_artifact.get("artifact_digest", ""),
            "chunk_plan_digest": chunk_plan.digest,
        }
        return ProviderTranscript(
            provider="deterministic",
            provider_model=configured_model,
            provider_model_version="fixture/1",
            provider_request_id="",
            language=language,
            timestamp_granularity=self._granularity,
            units=self._units,
            boundary_risks=boundary_risks_from_plan(chunk_plan),
            raw_metadata=metadata,
            raw_response_digest=canonical_digest(metadata),
            chunk_plan_digest=chunk_plan.digest,
        )
