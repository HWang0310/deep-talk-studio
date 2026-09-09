"""Evidence-derived extracted-audio to media-presentation mapping."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping

from .narration_media import canonical_digest
from .narration_schema import (
    AUDIO_TIMESTAMP_MAPPING_SCHEMA,
    EXTRACTED_AUDIO_SCHEMA,
    NARRATION_MEDIA_SCHEMA,
)
from .validation import ReportValidationError, validate_json_schema


class TimestampMappingError(ValueError):
    """A machine mapping cannot be rederived from bound media evidence."""


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TimestampMappingError(f"{field} 不是有效 decimal seconds") from exc
    if not result.is_finite():
        raise TimestampMappingError(f"{field} 不是有限数字")
    return result


def _time_base_tick(value: str) -> Decimal:
    try:
        numerator, denominator = str(value).split("/", 1)
        denominator_value = Decimal(denominator)
        if denominator_value == 0:
            return Decimal(0)
        return abs(Decimal(numerator) / denominator_value)
    except (ValueError, InvalidOperation):
        return Decimal(0)


def _tolerance(media: Mapping[str, Any], extracted: Mapping[str, Any]) -> Decimal:
    audio = media["audio_stream"]
    output_tick = Decimal(1) / Decimal(extracted["sample_rate"])
    frame = Decimal(0)
    if audio["codec_frame_samples"] and audio["sample_rate"]:
        frame = Decimal(audio["codec_frame_samples"]) / Decimal(audio["sample_rate"])
    return max(output_tick, frame, _time_base_tick(audio["time_base"]))


def derive_timestamp_mapping(
    media: Mapping[str, Any],
    extracted: Mapping[str, Any],
    *,
    mapping_id: str,
    created_at: str,
) -> Dict[str, Any]:
    del created_at  # identity is content/evidence-derived; creation time stays in storage metadata.
    try:
        validate_json_schema(dict(media), NARRATION_MEDIA_SCHEMA, "media")
        validate_json_schema(dict(extracted), EXTRACTED_AUDIO_SCHEMA, "audio")
    except ReportValidationError as exc:
        raise TimestampMappingError(str(exc)) from exc
    if extracted["narration_media_id"] != media["media_id"]:
        raise TimestampMappingError("派生音频绑定了错误的 media_id")
    if extracted["narration_media_sha256"] != media["sha256"]:
        raise TimestampMappingError("派生音频绑定了错误的媒体 SHA")
    if extracted["source_stream_index"] != media["audio_stream"]["stream_index"]:
        raise TimestampMappingError("派生音频绑定了错误的音轨")
    offset = _decimal(extracted["source_audio_presentation_start_seconds"], "audio offset")
    duration = Decimal(extracted["sample_count"]) / Decimal(extracted["sample_rate"])
    mapped_start = offset
    mapped_end = offset + duration
    evidence = {
        "media_presentation_evidence_digest": media["presentation_evidence"]["evidence_digest"],
        "media_probe_digest": media["probe_digest"],
        "extracted_audio_artifact_digest": extracted["artifact_digest"],
        "source_audio_presentation_start_seconds": extracted[
            "source_audio_presentation_start_seconds"
        ],
        "source_audio_presentation_end_seconds": extracted[
            "source_audio_presentation_end_seconds"
        ],
        "sample_count": extracted["sample_count"],
        "sample_rate": extracted["sample_rate"],
        "resampler_delay_samples": extracted["resampler_delay_samples"],
    }
    mapping = {
        "artifact_version": "audio-timestamp-mapping/1",
        "mapping_id": mapping_id,
        "narration_media_id": media["media_id"],
        "narration_media_sha256": media["sha256"],
        "extracted_audio_id": extracted["audio_id"],
        "extracted_audio_digest": extracted["artifact_digest"],
        "source_stream_index": extracted["source_stream_index"],
        "source_time_base": extracted["source_time_base"],
        "presentation_origin_seconds": media["presentation_evidence"][
            "presentation_origin_seconds"
        ],
        "first_included_source_pts": extracted["first_included_source_pts"],
        "last_included_source_pts": extracted["last_included_source_pts"],
        "first_extracted_sample_index": extracted["first_extracted_sample_index"],
        "last_extracted_sample_index": extracted["last_extracted_sample_index"],
        "scale_numerator": 1,
        "scale_denominator": 1,
        "offset_seconds": format(offset, "f"),
        "mapped_start_seconds": format(mapped_start, "f"),
        "mapped_end_seconds": format(mapped_end, "f"),
        "rounding_mode": "decimal_exact",
        "mapping_tolerance_seconds": format(_tolerance(media, extracted), "f"),
        "evidence_digest": canonical_digest(evidence),
    }
    mapping["mapping_digest"] = canonical_digest(mapping)
    try:
        validate_json_schema(mapping, AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")
    except ReportValidationError as exc:
        raise TimestampMappingError(str(exc)) from exc
    return mapping


def map_extracted_seconds(mapping: Mapping[str, Any], value: Decimal) -> Decimal:
    if mapping["scale_numerator"] != 1 or mapping["scale_denominator"] != 1:
        raise TimestampMappingError("首版 Timestamp Mapping 不允许 time-stretch")
    extracted = _decimal(value, "extracted seconds")
    if extracted < 0:
        raise TimestampMappingError("extracted seconds 不能为负数")
    return extracted + _decimal(mapping["offset_seconds"], "offset_seconds")


def validate_timestamp_mapping(
    mapping: Mapping[str, Any],
    media: Mapping[str, Any],
    extracted: Mapping[str, Any],
) -> None:
    try:
        validate_json_schema(dict(mapping), AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")
    except ReportValidationError as exc:
        raise TimestampMappingError(str(exc)) from exc
    expected = derive_timestamp_mapping(
        media,
        extracted,
        mapping_id=str(mapping["mapping_id"]),
        created_at="",
    )
    if dict(mapping) != expected:
        raise TimestampMappingError("Timestamp Mapping 与媒体证据重推导结果不一致")
    if mapping["scale_numerator"] != 1 or mapping["scale_denominator"] != 1:
        raise TimestampMappingError("首版 Timestamp Mapping 不允许 time-stretch")
    tolerance = _decimal(mapping["mapping_tolerance_seconds"], "mapping tolerance")
    mapped_start = _decimal(mapping["mapped_start_seconds"], "mapped start")
    mapped_end = _decimal(mapping["mapped_end_seconds"], "mapped end")
    presentation_end = _decimal(media["presentation_duration_seconds"], "media duration")
    if mapped_start < -tolerance or mapped_end > presentation_end + tolerance:
        raise TimestampMappingError("Timestamp Mapping 超出 Clean A-roll presentation timeline")
    duration = Decimal(extracted["sample_count"]) / Decimal(extracted["sample_rate"])
    if abs((mapped_end - mapped_start) - duration) > tolerance:
        raise TimestampMappingError("Timestamp Mapping duration 与 PCM sample count 不一致")
