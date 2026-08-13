"""Strict contracts for alignment profiles and Script Alignment artifacts."""

from .schema import _array, _enum, _integer, _number, _object, _string


_DIGEST = _string()
_DECIMAL = _string(allow_empty=True)

ALIGNMENT_PROFILE_SCHEMA = _object(
    {
        "artifact_version": _enum(["alignment-profile/1"]),
        "algorithm_version": _enum(["alignment-algorithm/1"]),
        "normalization_profile_version": _enum(["normalization-profile/1"]),
        "value_revision": _integer(1),
        "calibration_status": _enum(["candidate", "accepted"]),
        "primary_match_score": _number(),
        "numeric_alias_match_score": _number(),
        "substitution_score": {"type": "number", "maximum": 0},
        "script_deletion_score": {"type": "number", "maximum": 0},
        "transcript_insertion_score": {"type": "number", "maximum": 0},
        "ambiguity_normalized_margin": _number(0, 1),
        "accepted_floors": _object({"coverage": _number(0, 1), "similarity": _number(0, 1)}),
        "review_floors": _object({"coverage": _number(0, 1), "similarity": _number(0, 1)}),
        "long_gap_token_threshold": _integer(1),
        "timestamp_epsilon_seconds": _string(),
        "source_design_head": _string(),
        "source_design_digest": _DIGEST,
        "profile_digest": _DIGEST,
    }
)

CANDIDATE_WINDOW_SCHEMA = _object(
    {
        "script_token_start": _integer(), "script_token_end": _integer(1),
        "transcript_token_start": _integer(), "transcript_token_end": _integer(1),
        "transcript_unit_start": _string(), "transcript_unit_end": _string(),
        "actual_start_seconds": _string(), "actual_end_seconds": _string(),
        "score": {"type": "number"}, "normalized_margin": _number(0),
    }
)

GAP_SCHEMA = _object(
    {
        "gap_id": _string(),
        "gap_type": _enum([
            "omitted_script_span", "ad_lib_transcript_span", "repeated_or_ambiguous_span",
            "beat_order_changed", "chunk_boundary_risk",
        ]),
        "script_char_start": _integer(), "script_char_end": _integer(),
        "transcript_unit_ids": _array(_string()),
        "actual_start_seconds": _DECIMAL, "actual_end_seconds": _DECIMAL,
        "reason_code": _string(),
    }
)

BEAT_TIMELINE_SCHEMA = _object(
    {
        "beat_id": _string(),
        "intended_char_start": _integer(), "intended_char_end": _integer(1),
        "matched_transcript_unit_ids": _array(_string()),
        "actual_start_seconds": _DECIMAL, "actual_end_seconds": _DECIMAL,
        "timestamp_source": _enum(["provider_timed_transcript", "none"]),
        "timestamp_granularity": _enum(["word", "token", "segment", "none"]),
        "match_score": _number(0, 1), "token_coverage": _number(0, 1),
        "similarity": _number(0, 1),
        "confidence": _enum(["high", "medium", "low", "none"]),
        "alignment_status": _enum(["aligned", "needs_review", "unmatched"]),
        "deviation_codes": {"type": "array", "items": _enum([
            "omitted_script_span", "ad_lib_transcript_span", "ambiguous_match",
            "long_gap", "beat_order_changed", "segment_coarse", "chunk_boundary_risk",
        ]), "uniqueItems": True},
        "deviation_summary": _string(allow_empty=True),
        "boundary_risk_ids": {"type": "array", "items": _string(), "uniqueItems": True},
        "candidate_windows": _array(CANDIDATE_WINDOW_SCHEMA),
    }
)

CUE_TIMELINE_SCHEMA = _object(
    {
        "cue_id": _string(), "beat_id": _string(), "placement_anchor": _string(),
        "anchor_char_start": _integer(), "anchor_char_end": _integer(),
        "semantic_char_start": _integer(), "semantic_char_end": _integer(),
        "matched_transcript_unit_ids": _array(_string()),
        "actual_start_seconds": _DECIMAL, "actual_end_seconds": _DECIMAL,
        "placement_status": _enum(["aligned", "needs_review", "coarse", "unplaced"]),
        "timestamp_granularity": _enum(["word", "token", "segment", "none"]),
        "confidence": _enum(["high", "medium", "low", "none"]),
        "deviation_codes": {"type": "array", "items": _string(), "uniqueItems": True},
        "boundary_risk_ids": {"type": "array", "items": _string(), "uniqueItems": True},
        "candidate_windows": _array(CANDIDATE_WINDOW_SCHEMA),
    }
)

ALIGNMENT_OPERATION_SCHEMA = _object(
    {
        "operation": _enum(["primary_match", "numeric_match", "substitution", "script_deletion", "transcript_insertion"]),
        "script_token_index": {"type": "integer"}, "transcript_token_index": {"type": "integer"},
        "score": {"type": "number"},
    }
)

SCRIPT_ALIGNMENT_SCHEMA = _object(
    {
        "artifact_version": _enum(["script-alignment/1"]),
        "alignment_id": _string(), "revision": _integer(1), "created_at": _string(),
        "script_id": _string(), "script_revision": _integer(1), "script_content_digest": _DIGEST,
        "narration_media_id": _string(), "narration_media_sha256": _DIGEST,
        "presentation_duration_seconds": _string(),
        "timestamp_mapping_id": _string(), "timestamp_mapping_digest": _DIGEST,
        "transcript_id": _string(), "transcript_digest": _DIGEST,
        "transcription_chunk_plan_digest": _DIGEST,
        "normalization_profile_version": _enum(["normalization-profile/1"]),
        "normalization_digest": _DIGEST,
        "alignment_profile_version": _enum(["alignment-profile/1"]),
        "alignment_profile_digest": _DIGEST,
        "algorithm_version": _enum(["alignment-algorithm/1"]),
        "alignment_trace_digest": _DIGEST,
        "operations": _array(ALIGNMENT_OPERATION_SCHEMA),
        "candidate_windows": _array(CANDIDATE_WINDOW_SCHEMA),
        "beat_timeline": _array(BEAT_TIMELINE_SCHEMA),
        "cue_timeline": _array(CUE_TIMELINE_SCHEMA),
        "gaps": _array(GAP_SCHEMA),
        "artifact_digest": _DIGEST,
    }
)
