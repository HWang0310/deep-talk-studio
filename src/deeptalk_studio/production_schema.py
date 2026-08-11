"""Strict machine contracts for the DeepTalk Studio Production 0.6.1 layer."""

from .schema import _array, _enum, _integer, _number, _object, _string, _string_array


PRODUCTION_ARTIFACT_VERSION = "0.6.1"
SCENE_TYPES = [
    "timeline_motion", "bar_motion", "comparison_motion", "diagram_motion",
    "document_reveal", "screenshot_pan", "image_pan_zoom", "text_explainer",
    "transition_card", "aroll_placeholder",
]
RENDERERS = ["remotion", "hyperframes"]

DISPLAY_TEXT_SCHEMA = _object({
    "text": _string(),
    "origin": _enum([
        "machine_editorial", "research_fact", "research_attribution",
        "material_caption", "visual_label",
    ]),
    "text_kind": _enum(["editorial", "factual", "attribution"]),
    "claim_ids": _string_array(),
    "evidence_link_ids": _string_array(),
})

TIMELINE_EVENT_PAYLOAD_SCHEMA = _object({
    "order": _integer(1), "date": DISPLAY_TEXT_SCHEMA, "label": DISPLAY_TEXT_SCHEMA,
})
BAR_POINT_PAYLOAD_SCHEMA = _object({
    "order": _integer(1), "label": DISPLAY_TEXT_SCHEMA, "value": _number(),
    "value_label": DISPLAY_TEXT_SCHEMA,
})
COMPARISON_ITEM_PAYLOAD_SCHEMA = _object({
    "order": _integer(1), "label": DISPLAY_TEXT_SCHEMA,
    "left_text": DISPLAY_TEXT_SCHEMA, "right_text": DISPLAY_TEXT_SCHEMA,
})
DIAGRAM_NODE_PAYLOAD_SCHEMA = _object({
    "order": _integer(1), "node_id": _string(), "label": DISPLAY_TEXT_SCHEMA,
})
DIAGRAM_EDGE_PAYLOAD_SCHEMA = _object({
    "order": _integer(1), "from_node": _string(), "to_node": _string(),
    "label": DISPLAY_TEXT_SCHEMA,
})
SCENE_PAYLOAD_SCHEMA = _object({
    "payload_version": _enum([PRODUCTION_ARTIFACT_VERSION]),
    "payload_type": _enum(["timeline", "bar", "comparison", "diagram", "image", "aroll"]),
    "timeline_events": _array(TIMELINE_EVENT_PAYLOAD_SCHEMA),
    "bar_data_points": _array(BAR_POINT_PAYLOAD_SCHEMA),
    "comparison_items": _array(COMPARISON_ITEM_PAYLOAD_SCHEMA),
    "diagram_nodes": _array(DIAGRAM_NODE_PAYLOAD_SCHEMA),
    "diagram_edges": _array(DIAGRAM_EDGE_PAYLOAD_SCHEMA),
    "image_asset_id": _string(allow_empty=True),
    "capture_region": _string(allow_empty=True),
})

PRODUCTION_SCENE_SCHEMA = _object({
    "scene_id": _string(), "cue_id": _string(), "beat_id": _string(),
    "placement_anchor": _string(), "visual_role": _string(),
    "source_material_ids": _string_array(), "source_visual_ids": _string_array(),
    "scene_type": _enum(SCENE_TYPES), "duration_seconds": _number(1, 60),
    "duration_frames": _integer(1), "renderer_intent": _string(),
    "transition_intent": _string(), "layout_intent": _string(),
    "scene_payload": SCENE_PAYLOAD_SCHEMA,
    "on_screen_text": _array(DISPLAY_TEXT_SCHEMA),
    "audio_mode": _enum(["none", "aroll_placeholder"]), "warnings": _string_array(),
})

PRODUCTION_GAP_SCHEMA = _object({
    "gap_id": _string(), "cue_id": _string(), "beat_id": _string(),
    "reason": _string(), "recommended_fallback": _string(),
})

EXPECTED_MOTION_ASSET_SCHEMA = _object({
    "motion_asset_id": _string(), "scene_id": _string(),
    "asset_kind": _enum(["motion_clip", "rough_preview", "hero_still"]),
    "requested_format": _enum(["mp4", "webm", "png"]),
})

CANVAS_SCHEMA = _object({
    "width": _integer(1), "height": _integer(1), "aspect_ratio": _enum(["16:9"]),
    "fps": _integer(1),
})

PRODUCTION_PLAN_SCHEMA = _object({
    "artifact_version": _enum([PRODUCTION_ARTIFACT_VERSION]),
    "production_id": _string(), "revision": _integer(1), "previous_revision": _integer(),
    "created_at": _string(), "generated_at": _string(),
    "script_id": _string(), "script_revision": _integer(1),
    "script_content_digest": _string(), "material_package_id": _string(),
    "material_package_revision": _integer(1), "material_package_digest": _string(),
    "material_review_id": _string(), "production_profile_version": _enum(["0.6.1"]),
    "renderer_mode": _enum(["auto", "remotion", "hyperframes"]),
    "selected_renderer": _enum(RENDERERS), "canvas": CANVAS_SCHEMA,
    "scenes": _array(PRODUCTION_SCENE_SCHEMA),
    "motion_assets": _array(EXPECTED_MOTION_ASSET_SCHEMA),
    "production_gaps": _array(PRODUCTION_GAP_SCHEMA), "warnings": _string_array(),
    "qa_state": _object({"state": _enum(["not_run", "completed"])}),
    "plan_digest": _string(),
})

MOTION_ASSET_SCHEMA = _object({
    "motion_asset_id": _string(), "scene_id": _string(),
    "asset_kind": _enum(["motion_clip", "rough_preview", "hero_still"]),
    "renderer": _enum(RENDERERS), "output_path": _string(),
    "format": _enum(["mp4", "webm", "png"]), "width": _integer(1),
    "height": _integer(1), "fps": _number(), "duration_seconds": _number(),
    "byte_size": _integer(1), "sha256": _string(),
    "source_material_ids": _string_array(), "source_visual_ids": _string_array(),
    "production_plan_digest": _string(), "rendered_at": _string(),
    "render_command_summary": _string(),
    "qa_status": _enum(["ready", "failed"]),
})

MOTION_ASSET_MANIFEST_SCHEMA = _object({
    "artifact_version": _enum([PRODUCTION_ARTIFACT_VERSION]), "manifest_id": _string(),
    "production_id": _string(), "production_plan_digest": _string(),
    "renderer": _enum(RENDERERS), "created_at": _string(),
    "assets": _array(MOTION_ASSET_SCHEMA), "manifest_digest": _string(),
})

QA_CHECK_SCHEMA = _object({
    "check_name": _string(), "renderer": _enum(["core", "remotion", "hyperframes"]),
    "exit_code": _integer(), "outcome": _enum(["pass", "fail"]),
    "command_category": _enum([
        "environment", "install", "lint", "typecheck", "compositions",
        "doctor", "validate", "inspect", "preview",
    ]),
    "summary": _string(),
})

QA_ISSUE_SCHEMA = _object({
    "issue_id": _string(), "issue_type": _string(), "scope": _enum(["package", "clip"]),
    "motion_asset_id": _string(allow_empty=True), "blocking": {"type": "boolean"},
    "details": _string(),
})

PRODUCTION_QA_SCHEMA = _object({
    "artifact_version": _enum([PRODUCTION_ARTIFACT_VERSION]), "qa_id": _string(),
    "production_id": _string(), "production_plan_digest": _string(),
    "manifest_digest": _string(), "created_at": _string(),
    "checks": _array(QA_CHECK_SCHEMA), "issues": _array(QA_ISSUE_SCHEMA),
    "clip_results": _array(_object({
        "motion_asset_id": _string(), "status": _enum(["ready", "failed"]),
    })),
    "package_gate_status": _enum(["pass", "warnings", "fail"]),
    "qa_digest": _string(),
})
