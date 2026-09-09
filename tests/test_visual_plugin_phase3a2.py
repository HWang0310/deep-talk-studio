import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from deeptalk_studio.visual_plugin_adapter import (
    VisualPluginPreflightError,
    preflight_visual_plugin,
    run_visual_plugin,
)


ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
MG_SHA = "7ae59f1115da8a011113c81f31d320783b0ce8a4"
TASK_ID = "DT-CORE-3A2-001"
OPPORTUNITY = {
    "opportunity_id": "VO-phase3a2-unit",
    "spoken_semantics": "压力经由机制逐步传导，导致系统发生变化。",
    "visual_purpose": "解释因果机制。",
    "a_roll_window": {"start_ms": 1000, "end_ms": 8000},
    "target_duration_ms": 7000,
    "language": "zh-CN",
    "canvas": {"width": 1920, "height": 1080},
}


def fake_plugin(scenario="suitable", *, timeout=2, environment=None, version="fake-1"):
    return {
        "plugin_id": "fake-visual-plugin",
        "plugin_version": version,
        "plugin_root": str(ROOT),
        "argv_prefix": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--scenario", scenario],
        "timeout_seconds": timeout,
        "environment": dict(environment or {}),
        "enabled": True,
        "plugin_version_command": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--version"],
        "expected_source_revision": CORE_SHA,
        "require_clean_worktree": False,
    }


def init_git_checkout(root: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Phase 3A-2 Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "phase3a2@example.invalid"], cwd=root, check=True)
    (root / "tracked.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True
    ).stdout.strip()


def pinned_plugin(root: Path, revision: str) -> dict:
    plugin = fake_plugin()
    plugin.update({
        "plugin_root": str(root),
        "expected_source_revision": revision,
        "require_clean_worktree": True,
    })
    return plugin


class PinnedPluginPreflightTests(unittest.TestCase):
    def test_clean_exact_revision_returns_resolved_fail_closed_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            revision = init_git_checkout(root)
            evidence = preflight_visual_plugin(pinned_plugin(root, revision))

        self.assertEqual(evidence["resolved_plugin_root"], str(root.resolve()))
        self.assertEqual(evidence["expected_source_revision"], revision)
        self.assertEqual(evidence["actual_source_revision"], revision)
        self.assertTrue(evidence["require_clean_worktree"])
        self.assertTrue(evidence["clean_worktree"])

    def test_head_mismatch_and_dirty_checkout_fail_before_plugin_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            revision = init_git_checkout(root)
            with self.assertRaisesRegex(VisualPluginPreflightError, "source_revision_mismatch"):
                preflight_visual_plugin(pinned_plugin(root, "0" * 40))

            (root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(VisualPluginPreflightError, "dirty_worktree"):
                preflight_visual_plugin(pinned_plugin(root, revision))

            with tempfile.TemporaryDirectory() as jobs:
                result = run_visual_plugin(
                    pinned_plugin(root, revision),
                    operation="suitability",
                    opportunity=OPPORTUNITY,
                    job_root=Path(jobs),
                    plugin_config_digest="a" * 64,
                    task_id=TASK_ID,
                )

        self.assertEqual(result["execution"]["reason"], "dirty_worktree")
        self.assertIsNone(result["raw_response"])
        self.assertIsNone(result["request_snapshot"])
        self.assertFalse(result["execution"]["preflight"]["clean_worktree"])

    def test_missing_plugin_root_fails_closed(self):
        plugin = fake_plugin()
        plugin["plugin_root"] = "/definitely/not/a/deeptalk/plugin"
        plugin["expected_source_revision"] = MG_SHA
        plugin["require_clean_worktree"] = True
        with self.assertRaisesRegex(VisualPluginPreflightError, "plugin_root_unresolvable"):
            preflight_visual_plugin(plugin)


class IdentityAndEvidenceTests(unittest.TestCase):
    def test_canonical_config_pins_mg_runner_version_and_full_revision(self):
        config = json.loads((ROOT / "config/visual-asset-plugins.example.json").read_text(encoding="utf-8"))
        mg = next(item for item in config["plugins"] if item["plugin_id"] == "org.deeptalk.mg")
        self.assertEqual(mg["plugin_version"], "1.0.0-contract-v1")
        self.assertEqual(mg["argv_prefix"], ["node", "scripts/contract-runner.js"])
        self.assertEqual(mg["plugin_version_command"], ["node", "scripts/contract-runner.js", "--version"])
        self.assertEqual(mg["expected_source_revision"], MG_SHA)
        self.assertTrue(mg["require_clean_worktree"])

    def test_execution_records_task_preflight_commands_argv_environment_and_identity(self):
        with tempfile.TemporaryDirectory() as jobs:
            result = run_visual_plugin(
                fake_plugin(),
                operation="suitability",
                opportunity=OPPORTUNITY,
                job_root=Path(jobs),
                plugin_config_digest="b" * 64,
                task_id=TASK_ID,
            )

        execution = result["execution"]
        self.assertEqual(execution["task_id"], TASK_ID)
        self.assertEqual(execution["configured_runner"], fake_plugin()["argv_prefix"])
        self.assertEqual(execution["configured_version_command"], fake_plugin()["plugin_version_command"])
        self.assertEqual(execution["resolved_argv"][:4], fake_plugin()["argv_prefix"])
        self.assertEqual(execution["preflight"]["resolved_plugin_root"], str(ROOT.resolve()))
        self.assertEqual(len(execution["environment_digest"]), 64)
        self.assertEqual(execution["request_identity"]["contract_version"], "visual-asset-plugin-contract/1")
        self.assertEqual(execution["result_identity"]["plugin_id"], "fake-visual-plugin")
        self.assertEqual(execution["result_identity"]["plugin_version"], "fake-1")

    def test_wrong_reported_version_plugin_id_and_contract_version_fail_closed(self):
        cases = []
        wrong_version = fake_plugin(version="expected-version")
        cases.append(("plugin_version_mismatch", wrong_version))
        wrong_id = fake_plugin(environment={"FAKE_PLUGIN_ID": "wrong-plugin"})
        cases.append(("invalid_result", wrong_id))
        wrong_contract = fake_plugin("wrong-contract")
        cases.append(("invalid_result", wrong_contract))
        for expected, plugin in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as jobs:
                result = run_visual_plugin(
                    plugin,
                    operation="suitability",
                    opportunity=OPPORTUNITY,
                    job_root=Path(jobs),
                    plugin_config_digest="c" * 64,
                    task_id=TASK_ID,
                )
                self.assertEqual(result["execution"]["reason"], expected)
                self.assertIsNone(result["raw_response"])

    def test_generation_operational_failures_never_create_a_candidate(self):
        for scenario in ("generation-failed", "generation-blocked", "generation-unavailable"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as jobs:
                result = run_visual_plugin(
                    fake_plugin(scenario),
                    operation="generation",
                    opportunity=OPPORTUNITY,
                    proposal_id="PROP-phase3a2",
                    job_root=Path(jobs),
                    plugin_config_digest="d" * 64,
                    task_id=TASK_ID,
                )
                self.assertIn(result["raw_response"]["operation_status"], {"FAILED", "BLOCKED", "UNAVAILABLE"})
                self.assertNotIn("candidate", result["raw_response"])

    def test_non_executable_runner_fails_closed_without_blocking_a_healthy_plugin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / "not-executable"
            runner.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            runner.chmod(0o600)
            broken = fake_plugin()
            broken["argv_prefix"] = [str(runner)]
            failed = run_visual_plugin(
                broken,
                operation="suitability",
                opportunity=OPPORTUNITY,
                job_root=root / "failed",
                plugin_config_digest="d" * 64,
                task_id=TASK_ID,
            )
            healthy = run_visual_plugin(
                fake_plugin(),
                operation="suitability",
                opportunity=OPPORTUNITY,
                job_root=root / "healthy",
                plugin_config_digest="d" * 64,
                task_id=TASK_ID,
            )

        self.assertEqual(failed["execution"]["reason"], "launch_failed")
        self.assertIsNone(failed["raw_response"])
        self.assertEqual(healthy["execution"]["status"], "COMPLETED")


class ProcessReapingRegressionTests(unittest.TestCase):
    def test_sigterm_ignored_escalates_to_sigkill_and_reaps_child(self):
        with tempfile.TemporaryDirectory() as jobs:
            pid_path = Path(jobs) / "stubborn.pid"
            result = run_visual_plugin(
                fake_plugin("ignore-term", timeout=0.5, environment={"FAKE_PID_FILE": str(pid_path)}),
                operation="suitability",
                opportunity=OPPORTUNITY,
                job_root=Path(jobs) / "runs",
                plugin_config_digest="e" * 64,
                task_id=TASK_ID,
            )
            pid = int(pid_path.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
            with self.assertRaises(ChildProcessError):
                os.waitpid(pid, os.WNOHANG)

        self.assertEqual(result["execution"]["status"], "FAILED")
        self.assertEqual(result["execution"]["reason"], "timeout")
        self.assertEqual(result["execution"]["termination"], {
            "terminate_signal": signal.SIGTERM,
            "kill_signal": signal.SIGKILL,
            "escalated": True,
            "reaped": True,
            "process_group_terminated": True,
        })
        self.assertIsNone(result["raw_response"])

    def test_parent_exit_does_not_leave_sigterm_ignoring_process_group_member(self):
        with tempfile.TemporaryDirectory() as jobs:
            pid_path = Path(jobs) / "orphan.pid"
            pid = None
            try:
                result = run_visual_plugin(
                    fake_plugin("orphan-ignore-term", timeout=0.5, environment={"FAKE_PID_FILE": str(pid_path)}),
                    operation="suitability",
                    opportunity=OPPORTUNITY,
                    job_root=Path(jobs) / "runs",
                    plugin_config_digest="f" * 64,
                    task_id=TASK_ID,
                )
                pid = int(pid_path.read_text(encoding="utf-8"))
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.02)
                else:
                    self.fail("SIGTERM-ignoring process-group member survived timeout cleanup")
            finally:
                if pid is not None:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

        self.assertEqual(result["execution"]["reason"], "timeout")
        self.assertTrue(result["execution"]["termination"]["escalated"])
        self.assertTrue(result["execution"]["termination"]["process_group_terminated"])


if __name__ == "__main__":
    unittest.main()
