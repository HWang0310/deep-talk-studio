"""Strict machine contracts for narration media and timed transcription."""

from .schema import _array, _enum, _integer, _number, _object, _string


def _signed_integer():
    return {"type": "integer"}


def _decimal_string(allow_empty=False):
    return _string(allow_empty=allow_empty)


def _digest():
    return _string()


VIDEO_STREAM_SCHEMA = _object(
    {
        "present": {"type": "boolean"},
        "stream_index": _integer(),
        "codec": _string(allow_empty=True),
        "width": _integer(),
        "height": _integer(),
        "nominal_fps": _string(allow_empty=True),
        "average_fps": _string(allow_empty=True),
        "is_vfr": {"type": "boolean"},
        "time_base": _string(allow_empty=True),
        "start_pts": _signed_integer(),
        "start_time_seconds": _decimal_string(),
        "duration_ts": _signed_integer(),
        "duration_seconds": _decimal_string(),
    }
)


AUDIO_STREAM_SCHEMA = _object(
    {
        "present": {"type": "boolean"},
        "stream_index": _integer(),
        "codec": _string(allow_empty=True),
        "sample_rate": _integer(),
        "channels": _integer(),
        "channel_layout": _string(allow_empty=True),
        "time_base": _string(allow_empty=True),
        "start_pts": _signed_integer(),
        "start_time_seconds": _decimal_string(),
        "duration_ts": _signed_integer(),
        "duration_seconds": _decimal_string(),
        "codec_frame_samples": _integer(),
        "initial_padding_samples": _integer(),
        "trailing_padding_samples": _integer(),
        "skip_samples": _integer(),
        "discard_padding_samples": _integer(),
        "side_data_digest": _digest(),
    }
)


PRESENTATION_EVIDENCE_SCHEMA = _object(
    {
        "presentation_origin_seconds": _decimal_string(),
        "presentation_end_seconds": _decimal_string(),
        "audio_presentation_start_seconds": _decimal_string(allow_empty=True),
        "audio_presentation_end_seconds": _decimal_string(allow_empty=True),
        "edit_list_applied": {"type": "boolean"},
        "packet_probe_digest": _digest(),
        "frame_probe_digest": _digest(),
        "internal_audio_gaps": _array(
            _object(
                {
                    "start_seconds": _decimal_string(),
                    "end_seconds": _decimal_string(),
                }
            )
        ),
        "evidence_digest": _digest(),
    }
)


NARRATION_MEDIA_SCHEMA = _object(
    {
        "artifact_version": _enum(["narration-media/1"]),
        "media_id": _string(),
        "revision": _integer(1),
        "previous_revision": _integer(),
        "imported_at": _string(),
        "media_kind": _enum(["video", "audio"]),
        "safe_original_filename": _string(),
        "immutable_local_path": _string(),
        "sha256": _digest(),
        "byte_size": _integer(1),
        "container": _string(),
        "presentation_duration_seconds": _decimal_string(),
        "format_duration_seconds": _decimal_string(),
        "format_start_time_seconds": _decimal_string(),
        "video_stream": VIDEO_STREAM_SCHEMA,
        "audio_stream": AUDIO_STREAM_SCHEMA,
        "presentation_evidence": PRESENTATION_EVIDENCE_SCHEMA,
        "probe_tool": _string(),
        "probe_version": _string(),
        "probe_digest": _digest(),
        "artifact_digest": _digest(),
    }
)


EXTRACTED_AUDIO_SCHEMA = _object(
    {
        "artifact_version": _enum(["extracted-audio/1"]),
        "audio_id": _string(),
        "revision": _integer(1),
        "created_at": _string(),
        "narration_media_id": _string(),
        "narration_media_sha256": _digest(),
        "source_stream_index": _integer(),
        "immutable_local_path": _string(),
        "sha256": _digest(),
        "byte_size": _integer(1),
        "codec": _enum(["pcm_s16le", "pcm_s24le", "pcm_s32le"]),
        "sample_rate": _integer(1),
        "channels": _integer(1),
        "sample_width_bytes": _integer(1),
        "sample_count": _integer(1),
        "duration_seconds": _decimal_string(),
        "source_time_base": _string(),
        "first_included_source_pts": _signed_integer(),
        "last_included_source_pts": _signed_integer(),
        "first_extracted_sample_index": _integer(),
        "last_extracted_sample_index": _integer(),
        "source_audio_presentation_start_seconds": _decimal_string(),
        "source_audio_presentation_end_seconds": _decimal_string(),
        "resampler_delay_samples": _integer(),
        "applied_timeline_operations": {
            "type": "array",
            "items": _enum(
                [
                    "presentation_decode",
                    "aac_priming_excluded",
                    "trailing_padding_excluded",
                    "internal_gap_preserved",
                    "deterministic_resample",
                    "deterministic_channel_conversion",
                ]
            ),
            "uniqueItems": True,
        },
        "extraction_profile_version": _enum(["audio-extraction-profile/1"]),
        "extraction_profile_digest": _digest(),
        "ffmpeg_version": _string(),
        "command_arguments_digest": _digest(),
        "timestamp_mapping_id": _string(),
        "timestamp_mapping_digest": _digest(),
        "artifact_digest": _digest(),
    },
    optional=("timestamp_mapping_id", "timestamp_mapping_digest"),
)


AUDIO_TIMESTAMP_MAPPING_SCHEMA = _object(
    {
        "artifact_version": _enum(["audio-timestamp-mapping/1"]),
        "mapping_id": _string(),
        "narration_media_id": _string(),
        "narration_media_sha256": _digest(),
        "extracted_audio_id": _string(),
        "extracted_audio_digest": _digest(),
        "source_stream_index": _integer(),
        "source_time_base": _string(),
        "presentation_origin_seconds": _decimal_string(),
        "first_included_source_pts": _signed_integer(),
        "last_included_source_pts": _signed_integer(),
        "first_extracted_sample_index": _integer(),
        "last_extracted_sample_index": _integer(),
        "scale_numerator": _integer(1),
        "scale_denominator": _integer(1),
        "offset_seconds": _decimal_string(),
        "mapped_start_seconds": _decimal_string(),
        "mapped_end_seconds": _decimal_string(),
        "rounding_mode": _enum(["decimal_exact"]),
        "mapping_tolerance_seconds": _decimal_string(),
        "evidence_digest": _digest(),
        "mapping_digest": _digest(),
    }
)


TRANSCRIPTION_CHUNK_SCHEMA = _object(
    {
        "chunk_index": _integer(),
        "start_sample": _integer(),
        "end_sample": _integer(1),
        "sample_rate": _integer(1),
        "extracted_start_seconds": _decimal_string(),
        "extracted_end_seconds": _decimal_string(),
        "media_start_seconds": _decimal_string(),
        "media_end_seconds": _decimal_string(),
        "selection_mode": _enum(["final", "safe_pause", "low_energy_fallback"]),
        "boundary_evidence_digest": _digest(),
        "chunk_digest": _digest(),
        "profile_digest": _digest(),
    }
)


BOUNDARY_RISK_SCHEMA = _object(
    {
        "risk_id": _string(),
        "chunk_boundary_index": _integer(),
        "risk_level": _enum(["high"]),
        "reason": _enum(["no_safe_pause_fallback"]),
        "extracted_guard_start_seconds": _decimal_string(),
        "extracted_guard_end_seconds": _decimal_string(),
        "media_guard_start_seconds": _decimal_string(),
        "media_guard_end_seconds": _decimal_string(),
        "chunk_plan_digest": _digest(),
    }
)


TIMED_UNIT_SCHEMA = _object(
    {
        "unit_id": _string(),
        "order": _integer(),
        "chunk_index": _integer(),
        "chunk_digest": _digest(),
        "extracted_start_seconds": _decimal_string(),
        "extracted_end_seconds": _decimal_string(),
        "media_start_seconds": _decimal_string(),
        "media_end_seconds": _decimal_string(),
        "spoken_text": _string(),
        "provider_confidence": _decimal_string(allow_empty=True),
        "boundary_risk_ids": {"type": "array", "items": _string(), "uniqueItems": True},
    }
)


TIMED_TRANSCRIPT_SCHEMA = _object(
    {
        "artifact_version": _enum(["timed-transcript/1"]),
        "transcript_id": _string(),
        "revision": _integer(1),
        "created_at": _string(),
        "narration_media_id": _string(),
        "narration_media_sha256": _digest(),
        "extracted_audio_digest": _digest(),
        "timestamp_mapping_id": _string(),
        "timestamp_mapping_digest": _digest(),
        "transcription_chunk_plan_digest": _digest(),
        "transcription_chunks": _array(TRANSCRIPTION_CHUNK_SCHEMA),
        "boundary_risks": _array(BOUNDARY_RISK_SCHEMA),
        "provider": _string(),
        "provider_model": _string(),
        "provider_model_version": _string(allow_empty=True),
        "provider_request_id": _string(allow_empty=True),
        "language": _string(),
        "timestamp_granularity": _enum(["word", "token", "segment"]),
        "timed_units": _array(TIMED_UNIT_SCHEMA),
        "provider_metadata_digest": _digest(),
        "transcript_digest": _digest(),
    }
)
