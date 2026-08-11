"""Executable JSON contracts for Material Package and Visual Spec 0.5."""

from .schema import _array, _enum, _integer, _number, _object, _string, _string_array


VISUAL_ROLES = ["evidence", "context", "illustration", "transition"]
ASSET_TYPES = [
    "official_document", "webpage", "document_screenshot", "webpage_screenshot",
    "photo", "video_clip_reference", "product_ui", "chart_source", "public_dataset",
    "map_source", "archive", "generated_chart", "generated_timeline",
    "generated_diagram", "generated_map", "illustration_reference",
]
RIGHTS_STATUSES = [
    "public_domain", "explicit_reuse_allowed", "creative_commons",
    "official_press_asset", "editorial_reference_only", "permission_required",
    "unknown", "avoid",
]
SAFE_REUSE_STATUSES = {
    "public_domain", "explicit_reuse_allowed", "creative_commons", "official_press_asset"
}
MATERIAL_ARTIFACT_VERSION = "0.5.1"

MATERIAL_CUE_RAW_SCHEMA = _object({
    "beat_id": _string(),
    "placement_anchor": _string(),
    "visual_role": _enum(VISUAL_ROLES),
    "suggested_duration_seconds": _number(1, 60),
    "preferred_asset_type": _enum(ASSET_TYPES),
    "priority": _enum(["high", "medium", "low"]),
    "reason": _string(),
})

CAPTURE_SCHEMA = _object({
    "page_number": _integer(1),
    "capture_region": _string(allow_empty=True),
    "source_context": _string(allow_empty=True),
    "what_it_proves": _string(allow_empty=True),
    "what_it_does_not_prove": _string(allow_empty=True),
})

VIDEO_REFERENCE_SCHEMA = _object({
    "title": _string(allow_empty=True),
    "start_seconds": _number(),
    "end_seconds": _number(),
    "usage_reason": _string(allow_empty=True),
})

MATERIAL_RAW_SCHEMA = _object({
    "title": _string(),
    "source_url": _string(),
    "page_url": _string(),
    "publisher_creator": _string(),
    "asset_type": _enum(ASSET_TYPES),
    "published_at": _string(allow_empty=True),
    "intended_role": _enum(VISUAL_ROLES),
    "cue_numbers": {"type": "array", "items": _integer(1), "uniqueItems": True},
    "claim_ids": _string_array(),
    "evidence_link_ids": _string_array(),
    "suggested_usage": _string(),
    "caption": _string(),
    "illustrative_only": {"type": "boolean"},
    "claimed_rights_status": _enum(RIGHTS_STATUSES),
    "claimed_rights_basis": _string(allow_empty=True),
    "claimed_license_url": _string(allow_empty=True),
    "relevance": _integer(),
    "grounding_strength": _integer(),
    "visual_clarity": _integer(),
    "reuse_safety": _integer(),
    "acquisition_effort": _integer(),
    "ranking_reason": _string(),
    "capture": CAPTURE_SCHEMA,
    "video_reference": VIDEO_REFERENCE_SCHEMA,
})

VISUAL_EVENT_SCHEMA = _object({
    "date": _string(), "label": _string(), "claim_ids": _string_array(),
    "evidence_link_ids": _string_array(),
})
VISUAL_DATA_POINT_SCHEMA = _object({
    "label": _string(), "value": _number(), "value_label": _string(),
    "claim_ids": _string_array(), "evidence_link_ids": _string_array(),
})
VISUAL_COMPARISON_SCHEMA = _object({
    "label": _string(), "left_text": _string(), "right_text": _string(),
    "claim_ids": _string_array(), "evidence_link_ids": _string_array(),
})
VISUAL_NODE_SCHEMA = _object({
    "node_id": _string(), "label": _string(), "claim_ids": _string_array(),
})
VISUAL_EDGE_SCHEMA = _object({
    "from_node": _string(), "to_node": _string(), "label": _string(allow_empty=True),
})
VISUAL_SPEC_RAW_SCHEMA = _object({
    "beat_id": _string(),
    "visual_type": _enum(["timeline", "bar", "comparison", "diagram"]),
    "purpose": _enum(["context", "illustration"]),
    "title": _string(), "subtitle": _string(allow_empty=True),
    "events": _array(VISUAL_EVENT_SCHEMA),
    "data_points": _array(VISUAL_DATA_POINT_SCHEMA),
    "comparison_items": _array(VISUAL_COMPARISON_SCHEMA),
    "nodes": _array(VISUAL_NODE_SCHEMA),
    "edges": _array(VISUAL_EDGE_SCHEMA),
    "claim_ids": _string_array(), "evidence_link_ids": _string_array(),
    "attribution": _string(), "aspect_ratio": _enum(["16:9"]),
    "safe_area": _string(), "suggested_duration_seconds": _number(1, 60),
    "animation_intent": _string(), "style_tokens": _string_array(),
    "on_screen_text": _string_array(),
    "render_target_hints": {"type": "array", "items": _enum(
        ["static", "remotion_candidate", "hyperframes_candidate"]
    ), "uniqueItems": True},
})

RESEARCH_UPDATE_SIGNAL_SCHEMA = _object({
    "beat_ids": _string_array(), "claim_ids": _string_array(),
    "reason": _string(), "new_source_url": _string(),
})

MATERIAL_CONTENT_JSON_SCHEMA = _object({
    "cue_sheet": _array(MATERIAL_CUE_RAW_SCHEMA),
    "materials": _array(MATERIAL_RAW_SCHEMA),
    "visual_specs": _array(VISUAL_SPEC_RAW_SCHEMA),
    "gaps": _string_array(),
    "research_update_signals": _array(RESEARCH_UPDATE_SIGNAL_SCHEMA),
    "warnings": _string_array(),
})

INSPECTION_MANIFEST_SCHEMA = _object({"entries": _array(_object({
    "url": _string(), "inspected_at": _string(),
    "inspection_method": _enum(["codex_web_open", "browser_page_open", "manual_open"]),
    "tool_reference": _string(),
}))})

RIGHTS_MANIFEST_SCHEMA = _object({"entries": _array(_object({
    "url": _string(), "rights_status": _enum(RIGHTS_STATUSES),
    "rights_basis": _string(), "rights_evidence_url": _string(),
    "license_url": _string(allow_empty=True),
    "verified_at": _string(), "tool_reference": _string(),
}))})

MATERIAL_REVIEW_ISSUE_TYPES = [
    "missing_provenance", "claim_mismatch", "fabricated_source", "rights_misrepresented",
    "misleading_crop", "outdated_factual_visual", "wrong_identity",
    "generated_visual_unsupported_data", "ai_visual_as_real_evidence",
    "permission_needed", "near_duplicate", "low_usefulness",
]
MATERIAL_REVIEW_CHECK_NAMES = [
    "provenance_integrity", "claim_alignment", "rights_reuse", "crop_integrity",
    "freshness", "identity_accuracy", "generated_visual_grounding",
    "ai_real_confusion", "duplicate_control", "editorial_usefulness",
]
MATERIAL_REVIEW_CONTENT_JSON_SCHEMA = _object({
    "issues": _array(_object({
        "issue_type": _enum(MATERIAL_REVIEW_ISSUE_TYPES),
        "material_ids": _string_array(), "visual_ids": _string_array(),
        "cue_ids": _string_array(), "explanation": _string(), "suggested_fix": _string(),
    })),
    "checks": _array(_object({
        "check_name": _enum(MATERIAL_REVIEW_CHECK_NAMES),
        "outcome": _enum(["pass", "fail"]), "reason": _string(),
    })),
    "overall_notes": _string(),
})

MATERIAL_CUE_SCHEMA = _object({
    "cue_id": _string(), **MATERIAL_CUE_RAW_SCHEMA["properties"],
})
MATERIAL_SCHEMA = _object({
    **MATERIAL_RAW_SCHEMA["properties"],
    "material_id": _string(), "normalized_source_url": _string(),
    "cue_ids": _string_array(), "provenance_status": _enum(["inspected", "discovered", "unmatched"]),
    "inspection_method": _enum(["codex_web_open", "browser_page_open", "manual_open", "not_inspected"]),
    "inspected_at": _string(allow_empty=True), "inspection_reference": _string(allow_empty=True),
    "rights_status": _enum(RIGHTS_STATUSES), "rights_basis": _string(),
    "license_url": _string(allow_empty=True), "rights_verified_at": _string(allow_empty=True),
    "rights_reference": _string(allow_empty=True), "rights_evidence_url": _string(allow_empty=True),
    "eligibility_status": _enum(["ready_to_use", "reference_only", "permission_required", "rejected"]),
    "ranking_score": _number(), "local_path": _string(allow_empty=True),
    "byte_size": _integer(), "sha256": _string(allow_empty=True),
    "search_references": _string_array(),
})
VISUAL_SPEC_SCHEMA = _object({
    **VISUAL_SPEC_RAW_SCHEMA["properties"],
    "visual_id": _string(), "width": _integer(1), "height": _integer(1),
    "render_status": _enum(["not_rendered", "rendered"]),
    "local_path": _string(allow_empty=True), "byte_size": _integer(),
    "sha256": _string(allow_empty=True),
    "eligibility_status": _enum(["ready_to_use", "rejected"]),
})
MATERIAL_REVIEW_STATE_SCHEMA = _object({
    "state": _enum(["not_reviewed", "reviewed"]), "review_id": _string(allow_empty=True),
    "reviewed_from_revision": _integer(),
    "review_gate_status": _enum(["not_run", "pass", "warnings", "fail"]),
    "reviewed_package_digest": _string(allow_empty=True),
})
PROVIDER_PROVENANCE_SCHEMA = _object({
    "search_call_ids": _string_array(), "search_queries": _string_array(),
    "source_urls": _string_array(), "citation_urls": _string_array(),
})
MATERIAL_INPUT_PROVENANCE_SCHEMA = _object({
    "artifact_version": _enum([MATERIAL_ARTIFACT_VERSION]), "artifact_type": _enum(["material_input"]),
    "package_id": _string(), "package_revision": _integer(1), "script_id": _string(),
    "script_revision": _integer(1), "report_id": _string(), "report_revision": _integer(1),
    "created_at": _string(), "content": MATERIAL_CONTENT_JSON_SCHEMA, "artifact_digest": _string(),
})
MATERIAL_INSPECTION_PROVENANCE_SCHEMA = _object({
    "artifact_version": _enum([MATERIAL_ARTIFACT_VERSION]), "artifact_type": _enum(["material_inspection"]),
    "package_id": _string(), "package_revision": _integer(1), "script_id": _string(),
    "script_revision": _integer(1), "report_id": _string(), "report_revision": _integer(1),
    "created_at": _string(), "entries": INSPECTION_MANIFEST_SCHEMA["properties"]["entries"], "artifact_digest": _string(),
})
MATERIAL_RIGHTS_PROVENANCE_SCHEMA = _object({
    "artifact_version": _enum([MATERIAL_ARTIFACT_VERSION]), "artifact_type": _enum(["material_rights"]),
    "package_id": _string(), "package_revision": _integer(1), "script_id": _string(),
    "script_revision": _integer(1), "report_id": _string(), "report_revision": _integer(1),
    "created_at": _string(), "entries": RIGHTS_MANIFEST_SCHEMA["properties"]["entries"], "artifact_digest": _string(),
})
MATERIAL_PROVENANCE_BUNDLE_SCHEMA = _object({
    "input": MATERIAL_INPUT_PROVENANCE_SCHEMA,
    "inspection": MATERIAL_INSPECTION_PROVENANCE_SCHEMA,
    "rights": MATERIAL_RIGHTS_PROVENANCE_SCHEMA,
})
RESEARCH_UPDATE_STATE_SCHEMA = _object({
    "required": {"type": "boolean"}, "signals": _array(RESEARCH_UPDATE_SIGNAL_SCHEMA),
})
MATERIAL_PACKAGE_JSON_SCHEMA = _object({
    "artifact_version": _enum([MATERIAL_ARTIFACT_VERSION]), "package_id": _string(),
    "revision": _integer(1), "previous_revision": _integer(),
    "created_at": _string(), "generated_at": _string(),
    "package_mode": _enum(["codex_skill", "openai_api", "fixture"]),
    "status": _enum(["draft", "reviewed", "reviewed_with_warnings", "research_update_required", "blocked"]),
    "script_id": _string(), "script_revision": _integer(1),
    "script_content_digest": _string(), "script_review_id": _string(),
    "report_id": _string(), "report_revision": _integer(1),
    "material_profile_version": _enum(["0.5"]),
    "cue_sheet": _array(MATERIAL_CUE_SCHEMA), "materials": _array(MATERIAL_SCHEMA),
    "generated_visuals": _array(VISUAL_SPEC_SCHEMA), "gaps": _string_array(),
    "research_update_required": RESEARCH_UPDATE_STATE_SCHEMA,
    "warnings": _string_array(), "review_state": MATERIAL_REVIEW_STATE_SCHEMA,
    "provider_provenance": PROVIDER_PROVENANCE_SCHEMA,
    "provenance_bundle": MATERIAL_PROVENANCE_BUNDLE_SCHEMA, "package_digest": _string(),
})
