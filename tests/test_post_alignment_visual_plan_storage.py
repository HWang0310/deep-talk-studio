import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.post_alignment_visual_plan import build_post_alignment_visual_plan
from deeptalk_studio.post_alignment_visual_plan_storage import (
    PostAlignmentVisualPlanStorageError,
    load_post_alignment_visual_plan,
    save_post_alignment_visual_plan,
)


def script():
    return {"script_id": "SCR-1", "revision": 2, "beats": [{"beat_id": "B001", "narration": "甲乙"}]}


def transcript():
    return {"timestamp_granularity": "token", "timed_units": [
        {"unit_id": "TU1", "media_start_seconds": "1.0", "media_end_seconds": "1.2", "boundary_risk_ids": []},
        {"unit_id": "TU2", "media_start_seconds": "1.2", "media_end_seconds": "1.4", "boundary_risk_ids": []},
    ]}


def alignment():
    return {"alignment_id": "AL-1", "artifact_digest": "a" * 64, "transcript_digest": "c" * 64,
            "beat_timeline": [{"beat_id": "B001", "actual_start_seconds": "1.0", "actual_end_seconds": "1.4", "alignment_status": "aligned", "confidence": "high"}],
            "global_mapping": {"ambiguity_code": "none", "script_units": [
                {"script_char_start": 0, "script_char_end": 1, "operation": "primary_match", "transcript_token_index": 0, "transcript_unit_id": "TU1"},
                {"script_char_start": 1, "script_char_end": 2, "operation": "primary_match", "transcript_token_index": 1, "transcript_unit_id": "TU2"},
            ]}, "gaps": []}


def preference():
    return {"preference_digest": "e" * 64, "resolved_preference": {
        "overall_visual_density": "high", "real_material_preference": "high", "motion_preference": "high", "a_roll_preference": "balanced",
    }}


class PostAlignmentVisualPlanStorageTests(unittest.TestCase):
    def test_plan_is_immutable_and_revalidates_against_canonical_roots(self):
        plan = build_post_alignment_visual_plan(
            script(), transcript(), alignment(), preference(), [
                {"opportunity_id": "OP1", "beat_id": "B001", "semantic_char_start": 0, "semantic_char_end": 2,
                 "visual_kind": "original_motion", "visual_role": "explanation", "semantic_target": "结构",
                 "source_binding": {"scene_id": "S001"}},
            ], plan_id="VPLAN-1", created_at="2026-08-22T10:00:00+08:00",
        )
        with tempfile.TemporaryDirectory() as temp:
            path = save_post_alignment_visual_plan(plan, Path(temp))
            self.assertEqual(load_post_alignment_visual_plan(path, script(), transcript(), alignment(), preference()), plan)
            with self.assertRaises(PostAlignmentVisualPlanStorageError):
                save_post_alignment_visual_plan(plan, Path(temp))


if __name__ == "__main__":
    unittest.main()
