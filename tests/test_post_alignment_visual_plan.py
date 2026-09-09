import unittest

from deeptalk_studio.post_alignment_visual_plan import (
    PostAlignmentVisualPlanError,
    build_post_alignment_visual_plan,
    validate_post_alignment_visual_plan,
)


def script():
    return {"script_id": "SCR-1", "revision": 2, "beats": [
        {"beat_id": "B001", "narration": "甲乙"},
        {"beat_id": "B011", "narration": "丙丁戊"},
        {"beat_id": "B018", "narration": "己庚"},
    ]}


def transcript():
    return {"timestamp_granularity": "token", "timed_units": [
        {"unit_id": "TU1", "media_start_seconds": "1.0", "media_end_seconds": "1.2", "boundary_risk_ids": []},
        {"unit_id": "TU2", "media_start_seconds": "1.2", "media_end_seconds": "1.4", "boundary_risk_ids": []},
        {"unit_id": "TU3", "media_start_seconds": "2.0", "media_end_seconds": "2.2", "boundary_risk_ids": []},
        {"unit_id": "TU4", "media_start_seconds": "2.2", "media_end_seconds": "2.4", "boundary_risk_ids": []},
        {"unit_id": "TU5", "media_start_seconds": "3.0", "media_end_seconds": "3.2", "boundary_risk_ids": []},
        {"unit_id": "TU6", "media_start_seconds": "3.2", "media_end_seconds": "3.4", "boundary_risk_ids": []},
    ]}


def alignment():
    return {
        "alignment_id": "AL-1", "artifact_digest": "a" * 64,
        "script_content_digest": "b" * 64, "transcript_digest": "c" * 64,
        "presentation_duration_seconds": "10.0",
        "beat_timeline": [
            {"beat_id": "B001", "intended_char_start": 0, "intended_char_end": 2, "actual_start_seconds": "1.0", "actual_end_seconds": "1.4", "alignment_status": "aligned", "confidence": "high"},
            {"beat_id": "B011", "intended_char_start": 2, "intended_char_end": 5, "actual_start_seconds": "2.0", "actual_end_seconds": "2.4", "alignment_status": "needs_review", "confidence": "medium"},
            {"beat_id": "B018", "intended_char_start": 5, "intended_char_end": 7, "actual_start_seconds": "3.0", "actual_end_seconds": "3.4", "alignment_status": "aligned", "confidence": "high"},
        ],
        "global_mapping": {"mapping_version": "global-monotonic-projection/1", "trace_digest": "d" * 64, "ambiguity_code": "none", "script_units": [
            {"script_token_index": 0, "script_char_start": 0, "script_char_end": 1, "operation": "primary_match", "transcript_token_index": 0, "transcript_unit_id": "TU1", "actual_start_seconds": "1.0", "actual_end_seconds": "1.2"},
            {"script_token_index": 1, "script_char_start": 1, "script_char_end": 2, "operation": "primary_match", "transcript_token_index": 1, "transcript_unit_id": "TU2", "actual_start_seconds": "1.2", "actual_end_seconds": "1.4"},
            {"script_token_index": 2, "script_char_start": 2, "script_char_end": 3, "operation": "primary_match", "transcript_token_index": 2, "transcript_unit_id": "TU3", "actual_start_seconds": "2.0", "actual_end_seconds": "2.2"},
            {"script_token_index": 3, "script_char_start": 3, "script_char_end": 4, "operation": "script_deletion", "transcript_token_index": -1, "transcript_unit_id": "", "actual_start_seconds": "", "actual_end_seconds": ""},
            {"script_token_index": 4, "script_char_start": 4, "script_char_end": 5, "operation": "primary_match", "transcript_token_index": 3, "transcript_unit_id": "TU4", "actual_start_seconds": "2.2", "actual_end_seconds": "2.4"},
            {"script_token_index": 5, "script_char_start": 5, "script_char_end": 6, "operation": "primary_match", "transcript_token_index": 4, "transcript_unit_id": "TU5", "actual_start_seconds": "3.0", "actual_end_seconds": "3.2"},
            {"script_token_index": 6, "script_char_start": 6, "script_char_end": 7, "operation": "primary_match", "transcript_token_index": 5, "transcript_unit_id": "TU6", "actual_start_seconds": "3.2", "actual_end_seconds": "3.4"},
        ]},
        "gaps": [{"gap_id": "GAP1", "gap_type": "trailing_ad_lib_transcript_span", "reason_code": "post_script_transcript_tail", "actual_start_seconds": "8.0", "actual_end_seconds": "10.0"}],
    }


def preference():
    return {"preference_digest": "e" * 64, "resolved_preference": {
        "overall_visual_density": "high", "real_material_preference": "high", "motion_preference": "high", "a_roll_preference": "balanced",
    }}


class PostAlignmentVisualPlanTests(unittest.TestCase):
    def test_every_beat_is_audited_and_safe_opportunities_can_be_multiple(self):
        plan = build_post_alignment_visual_plan(
            script(), transcript(), alignment(), preference(), [
                {"opportunity_id": "OP1", "beat_id": "B001", "semantic_char_start": 0, "semantic_char_end": 2, "visual_kind": "real_material", "visual_role": "evidence", "semantic_target": "事件公开说明", "source_binding": {"material_id": "M001"}},
                {"opportunity_id": "OP2", "beat_id": "B001", "semantic_char_start": 0, "semantic_char_end": 2, "visual_kind": "original_motion", "visual_role": "context", "semantic_target": "攻击链结构", "source_binding": {"visual_id": "V001", "scene_id": "S001"}},
            ],
            plan_id="VPLAN-1", created_at="2026-08-22T10:00:00+08:00",
        )
        self.assertEqual([item["beat_id"] for item in plan["beat_audits"]], ["B001", "B011", "B018"])
        self.assertEqual([item["timing_status"] for item in plan["opportunities"]], ["ready", "ready"])
        self.assertEqual(plan["coverage_gate"]["visual_coverage_status"], "pass")
        self.assertEqual(plan["tail_policy"], {"status": "aroll", "start_seconds": "8.0", "end_seconds": "10.0"})
        validate_post_alignment_visual_plan(plan, script(), transcript(), alignment(), preference())

    def test_b011_isolated_safe_span_can_be_ready_but_uncertain_span_fails_closed(self):
        plan = build_post_alignment_visual_plan(
            script(), transcript(), alignment(), preference(), [
                {"opportunity_id": "OP-safe", "beat_id": "B011", "semantic_char_start": 2, "semantic_char_end": 3, "visual_kind": "real_material", "visual_role": "context", "semantic_target": "独立安全片段", "source_binding": {"material_id": "M003"}},
                {"opportunity_id": "OP-unsafe", "beat_id": "B011", "semantic_char_start": 2, "semantic_char_end": 5, "visual_kind": "original_motion", "visual_role": "context", "semantic_target": "包含遗漏词的片段", "source_binding": {"visual_id": "V011"}},
            ], plan_id="VPLAN-2", created_at="2026-08-22T10:00:00+08:00",
        )
        self.assertEqual(plan["opportunities"][0]["timing_status"], "ready")
        self.assertEqual(plan["opportunities"][1]["timing_status"], "unplaced")

    def test_opportunity_with_unknown_beat_is_rejected(self):
        with self.assertRaises(PostAlignmentVisualPlanError):
            build_post_alignment_visual_plan(
                script(), transcript(), alignment(), preference(), [
                    {"opportunity_id": "OP-bad", "beat_id": "B404", "semantic_char_start": 0, "semantic_char_end": 1, "visual_kind": "real_material", "visual_role": "evidence", "semantic_target": "无效", "source_binding": {"material_id": "M001"}},
                ], plan_id="VPLAN-3", created_at="2026-08-22T10:00:00+08:00",
            )


if __name__ == "__main__":
    unittest.main()
