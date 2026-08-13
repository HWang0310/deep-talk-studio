import unittest
from types import SimpleNamespace
from unittest.mock import patch

from deeptalk_studio.edit_bridge_qa import (
    REQUIRED_GROUPS,
    build_canonical_edit_bridge_qa_inputs,
    run_canonical_edit_bridge_qa,
)


class CanonicalEditBridgeQATests(unittest.TestCase):
    def context(self):
        return SimpleNamespace(
            placements=({"placement_id": "VP1", "placement_status": "ready"},),
            preview_used_placement_ids=("VP1",),
        )

    def test_factory_owns_exactly_one_concrete_validator_per_required_group(self):
        inputs = build_canonical_edit_bridge_qa_inputs(self.context())
        self.assertEqual({check.group for check in inputs.checks}, REQUIRED_GROUPS)
        self.assertEqual(len(inputs.checks), len(REQUIRED_GROUPS))

    def test_canonical_path_calls_all_repository_owned_validators(self):
        targets = (
            "_validate_root_chain", "_validate_transcript_chain",
            "_validate_alignment_chain", "_validate_placement_chain",
            "_validate_preview_chain",
        )
        patches = [patch(f"deeptalk_studio.edit_bridge_qa.{name}") for name in targets]
        mocks = [item.start() for item in patches]
        try:
            qa = run_canonical_edit_bridge_qa(self.context())
        finally:
            for item in reversed(patches):
                item.stop()
        self.assertEqual(qa["package_gate_status"], "pass")
        self.assertTrue(all(mock.call_count == 1 for mock in mocks))

    def test_mapping_asset_or_preview_failure_has_stable_group_issue(self):
        cases = (
            ("_validate_transcript_chain", "invalid_transcript_chain"),
            ("_validate_placement_chain", "invalid_placement_chain"),
            ("_validate_preview_chain", "preview_audio_presentation_mismatch"),
        )
        for target, issue_type in cases:
            with self.subTest(target=target), patch(
                f"deeptalk_studio.edit_bridge_qa.{target}", side_effect=ValueError("tamper")
            ):
                qa = run_canonical_edit_bridge_qa(self.context())
                self.assertEqual(qa["package_gate_status"], "fail")
                self.assertIn(issue_type, {item["issue_type"] for item in qa["issues"]})


if __name__ == "__main__":
    unittest.main()
