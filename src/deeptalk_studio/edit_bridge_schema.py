"""Strict orthogonal contracts for visual placement and Edit Bridge artifacts."""

from .schema import _array, _enum, _integer, _number, _object, _string

_D = _string(); _T = _string(allow_empty=True)

VISUAL_PLACEMENT_SCHEMA = _object({
    "artifact_version": _enum(["visual-placement/1"]), "placement_id": _string(),
    "track_order": _integer(), "source_kind": _enum(["clean_aroll", "real_image", "real_video", "original_motion"]),
    "source_id": _string(), "safe_filename": _string(allow_empty=True),
    "beat_id": _string(allow_empty=True), "cue_id": _string(allow_empty=True), "scene_id": _string(allow_empty=True),
    "visual_role": _string(), "asset_type": _string(), "placement_anchor": _string(allow_empty=True),
    "semantic_in_seconds": _T, "semantic_out_seconds": _T, "semantic_duration_seconds": _T,
    "canonical_in_timecode": _T, "canonical_out_timecode": _T,
    "natural_duration_seconds": _T, "target_duration_seconds": _T,
    "source_clip_in_seconds": _T, "source_clip_out_seconds": _T,
    "preview_effective_in_seconds": _T, "preview_effective_out_seconds": _T,
    "preview_in_frame": {"type": "integer"}, "preview_out_frame": {"type": "integer"},
    "preview_in_frame_timecode": _T, "preview_out_frame_timecode": _T,
    "preview_adjustment_id": _string(allow_empty=True),
    "preview_enabled": {"type": "boolean"},
    "layout_mode": _enum(["full_screen_aroll", "full_screen_broll", "full_screen_visual", "picture_in_picture", "split_screen", "side_card"]),
    "layout_source": _enum(["profile_default", "production_plan", "user_adjustment"]),
    "audio_policy": _enum(["clean_aroll_primary", "mute_source_keep_aroll"]),
    "placement_status": _enum(["ready", "coarse", "needs_review", "unplaced", "missing_asset", "clip_selection_needed", "rejected"]),
    "timing_status": _enum(["clear", "warning", "blocking"]),
    "duration_status": _enum(["natural", "long_still_warning", "asset_shorter", "asset_longer", "unknown"]),
    "confidence": _enum(["high", "medium", "low", "none"]),
    "notes": _array(_string()), "timing_conflict_ids": _array(_string()),
    "local_path": _string(allow_empty=True), "byte_size": _integer(), "sha256": _string(allow_empty=True),
})

TIMING_CONFLICT_SCHEMA = _object({
    "artifact_version": _enum(["timing-conflict/1"]), "conflict_id": _string(),
    "conflict_type": _enum(["motion_longer_than_semantic_window", "motion_shorter_than_semantic_window", "source_clip_shorter_than_semantic_window", "source_clip_longer_than_semantic_window", "visual_overlap", "same_start_selection_ambiguity", "out_of_media_bounds"]),
    "placement_ids": _array(_string()), "conflict_class": _enum(["timing_warning", "selection_blocker"]),
    "severity": _enum(["warning", "blocking"]), "human_summary": _string(),
    "preview_policy": _string(), "resolution_status": _enum(["unresolved", "preview_adjusted", "user_resolved"]),
})

PREVIEW_ADJUSTMENT_SCHEMA = _object({
    "artifact_version": _enum(["preview-adjustment/1"]), "adjustment_id": _string(),
    "placement_id": _string(), "adjustment_type": _string(), "reason": _string(),
    "original_in_seconds": _T, "original_out_seconds": _T,
    "preview_in_seconds": _T, "preview_out_seconds": _T,
    "provenance": _enum(["rough_cut_profile", "frame_mapping", "overlap_policy", "user_feedback"]),
})

EDIT_BRIDGE_SCHEMA = _object({
    "artifact_version": _enum(["edit-bridge/1"]), "bridge_id": _string(), "revision": _integer(1),
    "previous_revision": _integer(), "created_at": _string(),
    "root_bindings": _object({
        "narration_media_digest": _D, "extracted_audio_digest": _D, "timestamp_mapping_digest": _D,
        "chunk_plan_digest": _D, "transcript_digest": _D, "script_content_digest": _D,
        "research_digest": _D, "material_package_digest": _D, "material_view_digest": _D,
        "production_plan_digest": _D, "motion_manifest_digest": _D, "production_qa_digest": _D,
        "alignment_digest": _D, "alignment_profile_digest": _D,
        "rough_cut_profile_digest": _D, "aligned_preview_profile_digest": _D,
    }),
    "visual_placements": _array(VISUAL_PLACEMENT_SCHEMA), "timing_conflicts": _array(TIMING_CONFLICT_SCHEMA),
    "preview_adjustments": _array(PREVIEW_ADJUSTMENT_SCHEMA), "alignment_gaps": _array(_object({
        "gap_id": _string(), "gap_type": _string(), "reason_code": _string(),
    })), "qa_state": _enum(["not_run", "pass", "warnings", "fail"]), "package_digest": _D,
})
