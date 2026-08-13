"""Build and independently rederive canonical Timed Transcript artifacts."""

from decimal import Decimal
from typing import Any, Dict, Mapping

from .audio_timestamp_mapping import map_extracted_seconds
from .narration_media import canonical_digest
from .transcription import ProviderTranscript
from .transcription_chunking import TranscriptionChunkPlan


class TimedTranscriptError(ValueError):
    """Provider transcript cannot form a valid canonical timeline."""


def _chunk_record(chunk) -> Dict[str, Any]:
    return {
        "chunk_index": chunk.chunk_index,
        "start_sample": chunk.start_sample,
        "end_sample": chunk.end_sample,
        "sample_rate": chunk.sample_rate,
        "extracted_start_seconds": format(chunk.extracted_start_seconds, "f"),
        "extracted_end_seconds": format(chunk.extracted_end_seconds, "f"),
        "media_start_seconds": format(chunk.media_start_seconds, "f"),
        "media_end_seconds": format(chunk.media_end_seconds, "f"),
        "selection_mode": chunk.selection_mode,
        "boundary_evidence_digest": chunk.boundary_evidence_digest,
        "chunk_digest": chunk.chunk_digest,
        "profile_digest": chunk.profile_digest,
    }


def _risk_records(provider_result: ProviderTranscript, mapping: Mapping[str, Any]):
    records = []
    for risk in provider_result.boundary_risks:
        records.append(
            {
                "risk_id": risk.risk_id,
                "chunk_boundary_index": risk.boundary_index,
                "risk_level": risk.risk_level,
                "reason": risk.reason,
                "extracted_guard_start_seconds": format(risk.guard_start_seconds, "f"),
                "extracted_guard_end_seconds": format(risk.guard_end_seconds, "f"),
                "media_guard_start_seconds": format(
                    map_extracted_seconds(mapping, risk.guard_start_seconds), "f"
                ),
                "media_guard_end_seconds": format(
                    map_extracted_seconds(mapping, risk.guard_end_seconds), "f"
                ),
                "chunk_plan_digest": risk.chunk_plan_digest,
            }
        )
    return records


def build_timed_transcript(
    provider_result: ProviderTranscript,
    media: Mapping[str, Any],
    extracted: Mapping[str, Any],
    mapping: Mapping[str, Any],
    chunk_plan: TranscriptionChunkPlan,
    *,
    transcript_id: str,
    created_at: str,
) -> Dict[str, Any]:
    if provider_result.chunk_plan_digest != chunk_plan.digest:
        raise TimedTranscriptError("Provider Transcript 绑定了错误 Chunk Plan")
    chunks = {chunk.chunk_index: chunk for chunk in chunk_plan.chunks}
    risk_ids = {risk.risk_id for risk in provider_result.boundary_risks}
    risk_windows = {
        risk.risk_id: (risk.guard_start_seconds, risk.guard_end_seconds)
        for risk in provider_result.boundary_risks
    }
    units = []
    previous_start = Decimal("-1")
    previous_end = Decimal("-1")
    for order, unit in enumerate(provider_result.units):
        chunk = chunks.get(unit.chunk_index)
        if chunk is None:
            raise TimedTranscriptError("Provider unit 引用了不存在的 chunk")
        extracted_start = chunk.extracted_start_seconds + unit.local_start_seconds
        extracted_end = chunk.extracted_start_seconds + unit.local_end_seconds
        if extracted_start < chunk.extracted_start_seconds or extracted_end > chunk.extracted_end_seconds:
            raise TimedTranscriptError("Provider unit 超出 chunk-local timeline")
        if extracted_start < previous_start or extracted_end < previous_end:
            raise TimedTranscriptError("Provider unit 全局时间不单调")
        if previous_end >= 0 and extracted_start < previous_end:
            raise TimedTranscriptError("Provider unit 存在真实 overlap")
        if not set(unit.boundary_risk_ids).issubset(risk_ids):
            raise TimedTranscriptError("Provider unit 引用了未知 boundary risk")
        derived_risk_ids = [
            risk_id
            for risk_id, (guard_start, guard_end) in risk_windows.items()
            if extracted_start < guard_end and extracted_end > guard_start
        ]
        units.append(
            {
                "unit_id": f"TU{order:06d}",
                "order": order,
                "chunk_index": unit.chunk_index,
                "chunk_digest": chunk.chunk_digest,
                "extracted_start_seconds": format(extracted_start, "f"),
                "extracted_end_seconds": format(extracted_end, "f"),
                "media_start_seconds": format(
                    map_extracted_seconds(mapping, extracted_start), "f"
                ),
                "media_end_seconds": format(
                    map_extracted_seconds(mapping, extracted_end), "f"
                ),
                "spoken_text": unit.spoken_text,
                "provider_confidence": unit.provider_confidence,
                "boundary_risk_ids": derived_risk_ids,
            }
        )
        previous_start, previous_end = extracted_start, extracted_end
    if not units:
        raise TimedTranscriptError("Timed Transcript 不能为空")
    artifact = {
        "artifact_version": "timed-transcript/1",
        "transcript_id": transcript_id,
        "revision": 1,
        "created_at": created_at,
        "narration_media_id": media["media_id"],
        "narration_media_sha256": media["sha256"],
        "extracted_audio_digest": extracted["artifact_digest"],
        "timestamp_mapping_id": mapping["mapping_id"],
        "timestamp_mapping_digest": mapping["mapping_digest"],
        "transcription_chunk_plan_digest": chunk_plan.digest,
        "transcription_chunks": [_chunk_record(chunk) for chunk in chunk_plan.chunks],
        "boundary_risks": _risk_records(provider_result, mapping),
        "provider": provider_result.provider,
        "provider_model": provider_result.provider_model,
        "provider_model_version": provider_result.provider_model_version,
        "provider_request_id": provider_result.provider_request_id,
        "language": provider_result.language,
        "timestamp_granularity": provider_result.timestamp_granularity,
        "timed_units": units,
        "provider_metadata_digest": canonical_digest(provider_result.raw_metadata),
    }
    artifact["transcript_digest"] = canonical_digest(artifact)
    return artifact


def validate_timed_transcript(
    transcript: Mapping[str, Any],
    media: Mapping[str, Any],
    extracted: Mapping[str, Any],
    mapping: Mapping[str, Any],
    chunk_plan: TranscriptionChunkPlan,
) -> None:
    from .narration_schema import TIMED_TRANSCRIPT_SCHEMA
    from .validation import ReportValidationError, validate_json_schema

    try:
        validate_json_schema(dict(transcript), TIMED_TRANSCRIPT_SCHEMA, "transcript")
    except ReportValidationError as exc:
        raise TimedTranscriptError(str(exc)) from exc
    if transcript["narration_media_id"] != media["media_id"] or transcript["narration_media_sha256"] != media["sha256"]:
        raise TimedTranscriptError("Timed Transcript Media binding 不一致")
    if transcript["extracted_audio_digest"] != extracted["artifact_digest"]:
        raise TimedTranscriptError("Timed Transcript Extracted Audio binding 不一致")
    if transcript["timestamp_mapping_digest"] != mapping["mapping_digest"]:
        raise TimedTranscriptError("Timed Transcript Mapping binding 不一致")
    if transcript["transcription_chunk_plan_digest"] != chunk_plan.digest:
        raise TimedTranscriptError("Timed Transcript Chunk Plan binding 不一致")
    expected_chunks = [_chunk_record(chunk) for chunk in chunk_plan.chunks]
    if transcript["transcription_chunks"] != expected_chunks:
        raise TimedTranscriptError("Timed Transcript chunk records 被修改")
    risks = {risk["risk_id"]: risk for risk in transcript["boundary_risks"]}
    previous_end = Decimal("-1")
    for order, unit in enumerate(transcript["timed_units"]):
        if unit["order"] != order:
            raise TimedTranscriptError("Timed unit order 不连续")
        chunk = chunk_plan.chunks[unit["chunk_index"]]
        start = Decimal(unit["extracted_start_seconds"])
        end = Decimal(unit["extracted_end_seconds"])
        if start < previous_end:
            raise TimedTranscriptError("Timed units overlap 或倒退")
        if unit["chunk_digest"] != chunk.chunk_digest:
            raise TimedTranscriptError("Timed unit chunk digest 不一致")
        if Decimal(unit["media_start_seconds"]) != map_extracted_seconds(mapping, start):
            raise TimedTranscriptError("Timed unit media start 不是 Mapping 推导结果")
        if Decimal(unit["media_end_seconds"]) != map_extracted_seconds(mapping, end):
            raise TimedTranscriptError("Timed unit media end 不是 Mapping 推导结果")
        expected_risks = []
        for risk_id, risk in risks.items():
            guard_start = Decimal(risk["extracted_guard_start_seconds"])
            guard_end = Decimal(risk["extracted_guard_end_seconds"])
            if start < guard_end and end > guard_start:
                expected_risks.append(risk_id)
        if unit["boundary_risk_ids"] != expected_risks:
            raise TimedTranscriptError("Timed unit boundary risk propagation 不一致")
        previous_end = end
    digest_payload = dict(transcript)
    actual_digest = digest_payload.pop("transcript_digest")
    if actual_digest != canonical_digest(digest_payload):
        raise TimedTranscriptError("Timed Transcript digest 不一致")
