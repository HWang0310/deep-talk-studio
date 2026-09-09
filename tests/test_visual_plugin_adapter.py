import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.visual_plugin_adapter import run_visual_plugin


ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
OPPORTUNITY = {"opportunity_id": "VO-synthetic-01", "spoken_semantics": "Synthetic semantics.", "visual_purpose": "Explain.", "a_roll_window": {"start_ms": 1000, "end_ms": 3000}, "target_duration_ms": 1500, "language": "zh-CN", "canvas": {"width": 1920, "height": 1080}}


def plugin(scenario, timeout=2):
    return {"plugin_id": "fake-visual-plugin", "plugin_version": "fake-1", "plugin_root": str(ROOT), "argv_prefix": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--scenario", scenario], "timeout_seconds": timeout, "environment": {}, "enabled": True, "plugin_version_command": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--version"], "expected_source_revision": CORE_SHA, "require_clean_worktree": False}


class VisualPluginAdapterTests(unittest.TestCase):
    def test_caller_supplied_request_id_is_preserved_and_path_safe(self):
        with tempfile.TemporaryDirectory() as root:
            result = run_visual_plugin(
                plugin("suitable"), operation="suitability", opportunity=OPPORTUNITY,
                job_root=Path(root), request_id="REQ-stable-order-proof",
            )
            self.assertEqual(result["execution"]["request_id"], "REQ-stable-order-proof")
            self.assertEqual(result["raw_response"]["request_id"], "REQ-stable-order-proof")
            self.assertTrue((Path(root) / "REQ-stable-order-proof" / "request.json").is_file())
            with self.assertRaisesRegex(ValueError, "request_id"):
                run_visual_plugin(
                    plugin("suitable"), operation="suitability", opportunity=OPPORTUNITY,
                    job_root=Path(root), request_id="../unsafe",
                )
            for unsafe in (".", ".."):
                with self.subTest(request_id=unsafe), self.assertRaisesRegex(ValueError, "request_id"):
                    run_visual_plugin(
                        plugin("suitable"), operation="suitability", opportunity=OPPORTUNITY,
                        job_root=Path(root), request_id=unsafe,
                    )

    def test_valid_suitability_and_abstain_are_raw_contract_responses(self):
        with tempfile.TemporaryDirectory() as root:
            suitable = run_visual_plugin(plugin("suitable"), operation="suitability", opportunity=OPPORTUNITY, job_root=Path(root))
            abstain = run_visual_plugin(plugin("abstain"), operation="suitability", opportunity=OPPORTUNITY, job_root=Path(root))
        self.assertEqual(suitable["execution"]["status"], "COMPLETED")
        self.assertEqual(suitable["raw_response"]["suitability"], "SUITABLE")
        self.assertEqual(abstain["raw_response"]["suitability"], "ABSTAIN")

    def test_core_failures_never_fabricate_raw_response(self):
        with tempfile.TemporaryDirectory() as root:
            missing = plugin("suitable"); missing["argv_prefix"] = ["not-a-real-executable"]
            result = run_visual_plugin(missing, operation="suitability", opportunity=OPPORTUNITY, job_root=Path(root))
        self.assertEqual(result["execution"]["status"], "FAILED")
        self.assertTrue(result["execution"]["retryable"])
        self.assertIsNone(result["raw_response"])

    def test_invalid_operation_or_generation_without_proposal_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "operation"):
                run_visual_plugin(plugin("suitable"), operation="unknown", opportunity=OPPORTUNITY, job_root=Path(root))
            with self.assertRaisesRegex(ValueError, "proposal_id"):
                run_visual_plugin(plugin("ready"), operation="generation", opportunity=OPPORTUNITY, job_root=Path(root))

    def test_generation_ready_and_malformed_or_timeout_results_are_separated(self):
        with tempfile.TemporaryDirectory() as root:
            ready = run_visual_plugin(plugin("ready"), operation="generation", opportunity=OPPORTUNITY, proposal_id="PROP-01", job_root=Path(root))
            malformed = run_visual_plugin(plugin("malformed"), operation="generation", opportunity=OPPORTUNITY, proposal_id="PROP-01", job_root=Path(root))
            # Keep enough headroom for the separate version subprocess while
            # remaining far below the fixture runner's deterministic 5 s sleep.
            timed_out = run_visual_plugin(plugin("timeout", timeout=0.5), operation="generation", opportunity=OPPORTUNITY, proposal_id="PROP-01", job_root=Path(root))
        self.assertEqual(ready["raw_response"]["candidate"]["candidate_status"], "READY")
        self.assertEqual(malformed["execution"]["status"], "FAILED")
        self.assertIsNone(malformed["raw_response"])
        self.assertEqual(timed_out["execution"]["reason"], "timeout")
        self.assertIsNone(timed_out["raw_response"])


if __name__ == "__main__":
    unittest.main()
