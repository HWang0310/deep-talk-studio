import tempfile
import unittest
import json
import os
import shutil
from pathlib import Path

from deeptalk_studio.edit_bridge_session import resolve_real_edit_bridge_session
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture
from tests.integrated_upstream_factory import create_integrated_roots


class RealEditBridgeSessionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
    def test_resolver_finds_one_video_and_exact_reviewed_trial_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            old_repo = base / "old" / "deep-talk-studio"
            _, _, package_path, _, plan, _, _ = create_integrated_roots(old_repo)
            protected = {
                "package": package_path.read_bytes(),
                "manifest": next(old_repo.rglob("motion-asset-manifest-r0001.json")).read_bytes(),
            }
            new_repo = base / "new" / "deep-talk-studio"
            new_repo.parent.mkdir(parents=True)
            shutil.copytree(old_repo, new_repo)
            shutil.rmtree(old_repo)
            config_dir = new_repo / "config"; config_dir.mkdir(exist_ok=True)
            (config_dir / "artifact-runtime.local.json").write_text(json.dumps({
                "config_version": "artifact-runtime/1",
                "canonical_repository_root": str(new_repo.resolve()),
                "trusted_historical_repository_roots": [str(old_repo.resolve())],
                "current_production_id": plan["production_id"],
            }), encoding="utf-8")
            session = base / "session"; session.mkdir()
            source = build_media_fixture(session, MediaFixtureSpec(name="formal-aroll"))
            resolved = resolve_real_edit_bridge_session(session, repo_root=new_repo)
            self.assertEqual(resolved.clean_aroll_path, source.resolve())
            self.assertEqual(resolved.script.status, "reviewed")
            self.assertEqual(resolved.report.status, "ready_for_script")
            self.assertEqual(resolved.production_plan["script_id"], resolved.script.script_id)
            self.assertEqual(resolved.production_qa["package_gate_status"], "pass")
            self.assertTrue(any(
                item["production_status"] == "ready"
                for item in resolved.material_view["items"]
            ))
            self.assertEqual(
                next(new_repo.rglob("material-package-r0002.json")).read_bytes(),
                protected["package"],
            )
            self.assertEqual(
                next(new_repo.rglob("motion-asset-manifest-r0001.json")).read_bytes(),
                protected["manifest"],
            )

    def test_current_production_selection_uses_pointer_then_artifact_time_not_mtime(self):
        from deeptalk_studio.edit_bridge_session import _select_current_production
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            older = root / "older.json"
            newer = root / "newer.json"
            older.write_text(json.dumps({
                "production_id": "PROD-older", "created_at": "2026-08-20T10:00:00+08:00",
                "revision": 1, "qa_state": {"state": "pass"},
            }), encoding="utf-8")
            newer.write_text(json.dumps({
                "production_id": "PROD-newer", "created_at": "2026-08-21T10:00:00+08:00",
                "revision": 1, "qa_state": {"state": "pass"},
            }), encoding="utf-8")
            os.utime(older, (2_000_000_000, 2_000_000_000))
            os.utime(newer, (1_000_000_000, 1_000_000_000))
            predicate = lambda value: value.get("qa_state", {}).get("state") == "pass"

            explicit_path, _ = _select_current_production(
                (older, newer), predicate, "PROD-older"
            )
            fallback_path, _ = _select_current_production(
                (older, newer), predicate, ""
            )

            self.assertEqual(explicit_path, older)
            self.assertEqual(fallback_path, newer)

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
