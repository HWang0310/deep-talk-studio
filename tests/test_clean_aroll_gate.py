import unittest

from deeptalk_studio.clean_aroll_gate import (
    CleanARollGateError,
    inspect_clean_aroll,
    require_clean_aroll,
)


def media():
    return {"media_id": "NM-1", "artifact_digest": "a" * 64, "media_kind": "video"}


class CleanARollGateTests(unittest.TestCase):
    def test_multiple_complete_take_markers_require_manual_cleanup(self):
        result = inspect_clean_aroll(media(), {"text": "第一遍完整口播。重新录一遍。第二遍完整口播。"})
        self.assertEqual(result.status, "needs_manual_cleanup")
        self.assertIn("人工清理", result.user_message)

    def test_multiple_complete_script_runs_require_manual_cleanup_without_selecting_one(self):
        result = inspect_clean_aroll(media(), {"text": "正常口播内容。", "complete_script_run_count": 2})
        self.assertEqual(result.status, "needs_manual_cleanup")
        self.assertIn("人工清理", result.user_message)

    def test_natural_pause_and_adlib_are_accepted_without_cut_instruction(self):
        result = inspect_clean_aroll(media(), {"text": "这个，嗯，我想补一句，其实很重要。"})
        self.assertEqual(result.status, "accepted")
        self.assertNotIn("删除", result.user_message)

    def test_gate_never_returns_selection_or_edit_instructions(self):
        result = inspect_clean_aroll(media(), {"text": "第一遍。重录。第二遍。"})
        self.assertFalse(any(key in result.to_dict() for key in ("keep_take", "cut_ranges", "crop", "selection")))

    def test_require_clean_aroll_refuses_without_proposing_a_cut(self):
        with self.assertRaisesRegex(CleanARollGateError, "人工清理"):
            require_clean_aroll(media(), {"text": "重录一次。"})


if __name__ == "__main__":
    unittest.main()
