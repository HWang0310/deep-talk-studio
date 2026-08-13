import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deeptalk_studio.edit_bridge_session import resolve_real_edit_bridge_session
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture


class RealEditBridgeSessionTests(unittest.TestCase):
    def test_resolver_finds_one_video_and_exact_reviewed_trial_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp)
            source = build_media_fixture(session, MediaFixtureSpec(name="formal-aroll"))
            resolved = resolve_real_edit_bridge_session(session)
        self.assertEqual(resolved.clean_aroll_path, source.resolve())
        self.assertEqual(resolved.script.status, "reviewed")
        self.assertEqual(resolved.report.status, "ready_for_script")
        self.assertEqual(resolved.production_plan["script_id"], resolved.script.script_id)
        self.assertEqual(resolved.production_qa["package_gate_status"], "pass")

    def test_resolver_rejects_missing_or_multiple_video_with_plain_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "只放入一个"):
                resolve_real_edit_bridge_session(temp)
            root = Path(temp)
            build_media_fixture(root, MediaFixtureSpec(name="one"))
            build_media_fixture(root, MediaFixtureSpec(name="two", suffix=".mov"))
            with self.assertRaisesRegex(ValueError, "只放入一个"):
                resolve_real_edit_bridge_session(temp)

    def test_production_entrypoint_is_concrete_not_stage_lambda_harness(self):
        import inspect
        from deeptalk_studio.edit_bridge_session import run_real_edit_bridge_session
        signature = inspect.signature(run_real_edit_bridge_session)
        self.assertNotIn("stages", signature.parameters)
        source = inspect.getsource(run_real_edit_bridge_session)
        for concrete in (
            "import_narration_media", "extract_transcription_audio",
            "plan_transcription_chunks", "build_timed_transcript",
            "build_script_alignment", "build_subtitle_artifact", "build_visual_placements",
            "mux_clean_aroll_audio", "run_canonical_edit_bridge_qa",
        ):
            self.assertIn(concrete, source)


if __name__ == "__main__":
    unittest.main()
