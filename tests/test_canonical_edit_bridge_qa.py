import unittest
import copy
from types import SimpleNamespace
from unittest.mock import patch

from deeptalk_studio.edit_bridge_qa import (
    REQUIRED_GROUPS,
    EditBridgeQAError,
    _validate_root_chain,
    build_canonical_edit_bridge_qa_inputs,
    run_canonical_edit_bridge_qa,
)
from deeptalk_studio.subtitle_builder import build_subtitle_artifact
from deeptalk_studio.subtitle_profile import load_subtitle_profile
from tests.test_subtitle_builder import media, transcript


class CanonicalEditBridgeQATests(unittest.TestCase):
    def context(self):
        return SimpleNamespace(
            placements=({"placement_id": "VP1", "placement_status": "ready"},),
            preview_used_placement_ids=("VP1",),
        )

    def test_factory_owns_exactly_one_concrete_validator_per_required_group(self):
        inputs = build_canonical_edit_bridge_qa_inputs(self.context())
        self.assertEqual({check.group for check in inputs.checks}, REQUIRED_GROUPS)
        self.assertEqual(len(inputs.checks), len(REQUIRED_GROUPS) + 1)

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

    def test_subtitle_tamper_is_a_blocking_canonical_transcript_failure(self):
        profile = load_subtitle_profile()
        subtitle = build_subtitle_artifact(transcript(), media(), profile, subtitle_id="SUB1", created_at="now")
        subtitle = copy.deepcopy(subtitle); subtitle["cues"][0]["text"] = "被篡改"
        context = SimpleNamespace(
            mapping={}, media=media(), extracted={}, chunk_plan=object(), chunk_profile={},
            transcript=transcript(), subtitle_artifact=subtitle, subtitle_profile=profile,
            placements=(), preview_used_placement_ids=(),
        )
        with patch("deeptalk_studio.audio_timestamp_mapping.validate_timestamp_mapping"), patch(
            "deeptalk_studio.transcription_chunking.validate_transcription_chunk_plan"
        ), patch("deeptalk_studio.transcript_builder.validate_timed_transcript"):
            qa = run_canonical_edit_bridge_qa(context)
        self.assertEqual(qa["package_gate_status"], "fail")
        self.assertIn("invalid_transcript_chain", {item["issue_type"] for item in qa["issues"]})

    def test_visual_context_roots_must_be_an_all_or_nothing_pair(self):
        with self.assertRaises(EditBridgeQAError):
            _validate_root_chain(SimpleNamespace(episode_visual_preference={}, post_alignment_visual_plan=None))

    def test_output_truth_failure_is_blocking(self):
        with patch("deeptalk_studio.edit_bridge_qa._validate_output_truth_chain", side_effect=ValueError("no final frame evidence")):
            qa = run_canonical_edit_bridge_qa(self.context())
        self.assertEqual(qa["package_gate_status"], "fail")
        self.assertIn("invalid_output_truth", {item["issue_type"] for item in qa["issues"]})


if __name__ == "__main__":
    unittest.main()
