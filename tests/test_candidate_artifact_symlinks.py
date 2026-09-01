import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_portfolio import core_accept_candidate
from deeptalk_studio.visual_plugin_adapter import run_visual_plugin


ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
).stdout.strip()
OPPORTUNITY = {
    "opportunity_id": "VO-artifact-symlink-regression",
    "spoken_semantics": "Synthetic symlink boundary regression.",
    "visual_purpose": "Verify Core artifact safety.",
    "a_roll_window": {"start_ms": 0, "end_ms": 1000},
    "target_duration_ms": 1000,
    "language": "zh-CN",
    "canvas": {"width": 16, "height": 16},
}


def plugin(scenario: str) -> dict:
    return {
        "plugin_id": "fake-visual-plugin",
        "plugin_version": "fake-1",
        "plugin_root": str(ROOT),
        "argv_prefix": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--scenario", scenario],
        "timeout_seconds": 3,
        "environment": {"FAKE_WRITE_MEDIA": "1"},
        "enabled": True,
        "plugin_version_command": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--version"],
        "expected_source_revision": CORE_SHA,
        "require_clean_worktree": False,
    }


class CandidateArtifactSymlinkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.suitability = run_visual_plugin(
            plugin("suitable"),
            operation="suitability",
            opportunity=OPPORTUNITY,
            job_root=self.root / "jobs",
        )
        self.generation = run_visual_plugin(
            plugin("ready"),
            operation="generation",
            opportunity=OPPORTUNITY,
            proposal_id=self.suitability["raw_response"]["proposal_id"],
            job_root=self.root / "jobs",
        )
        self.output_root = Path(self.generation["_output_root"])
        self.generation_raw = copy.deepcopy(self.generation["raw_response"])

    def tearDown(self):
        self.temporary.cleanup()

    def acceptance(self, *, output_root: Path | None = None, generation_raw: dict | None = None) -> dict:
        return core_accept_candidate(
            OPPORTUNITY,
            self.suitability["raw_response"],
            generation_raw or self.generation_raw,
            plugin("ready"),
            output_root or self.output_root,
        )

    def assert_unsafe_rejection(self, acceptance: dict) -> None:
        self.assertEqual(acceptance["status"], "REJECTED")
        self.assertIn("ARTIFACT_URI_UNSAFE", {item["code"] for item in acceptance["problems"]})

    def test_output_root_symlink_is_rejected_before_resolution(self):
        lexical_root = self.output_root
        real_root = lexical_root.with_name("real-output")
        lexical_root.rename(real_root)
        lexical_root.symlink_to(real_root, target_is_directory=True)

        self.assert_unsafe_rejection(self.acceptance(output_root=lexical_root))

    def test_artifact_parent_directory_symlink_is_rejected(self):
        media = self.output_root / "media.mp4"
        real_parent = self.output_root / "real-parent"
        real_parent.mkdir()
        media.rename(real_parent / "media.mp4")
        (self.output_root / "linked-parent").symlink_to(real_parent, target_is_directory=True)
        self.generation_raw["candidate"]["artifacts"][0]["uri"] = "local-runner://linked-parent/media.mp4"

        self.assert_unsafe_rejection(self.acceptance())

    def test_primary_media_symlink_to_external_file_is_rejected(self):
        media = self.output_root / "media.mp4"
        external = self.root / "external.mp4"
        media.rename(external)
        media.symlink_to(external)

        self.assert_unsafe_rejection(self.acceptance())

    def test_primary_media_symlink_to_file_inside_output_root_is_still_rejected(self):
        media = self.output_root / "media.mp4"
        real_media = self.output_root / "real-media.mp4"
        media.rename(real_media)
        media.symlink_to(real_media.name)

        self.assert_unsafe_rejection(self.acceptance())

    def test_normal_primary_media_file_remains_accepted(self):
        acceptance = self.acceptance()

        self.assertEqual(acceptance["status"], "ACCEPTED")
        self.assertNotIn("ARTIFACT_URI_UNSAFE", {item["code"] for item in acceptance["problems"]})


if __name__ == "__main__":
    unittest.main()
