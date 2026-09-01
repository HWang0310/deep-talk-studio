"""Readiness records for the independently reviewed Phase 3B runners."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.visual_plugin_adapter import (
    VisualPluginPreflightError,
    preflight_visual_plugin,
    resolve_plugin_version,
)
from deeptalk_studio.visual_plugin_config import config_digest, normalize_visual_plugin_config


CORE_ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=CORE_ROOT, check=True, text=True, capture_output=True
).stdout.strip()
ILLUSTRATED_SHA = "48848affe018fc2cff8ee15bad7a09bb002776e4"
HANDDRAWN_SHA = "67698fd8ea09109ff91c912f51e4c2d4f0b8482f"


def readiness_config() -> dict:
    return json.loads((CORE_ROOT / "config/visual-asset-plugins.example.json").read_text(encoding="utf-8"))


def fake_plugin(*, root: Path, revision: str, version: str = "fake-1", clean: bool = True) -> dict:
    return {
        "plugin_id": "phase3b-fake-plugin",
        "plugin_version": version,
        "plugin_root": str(root),
        "argv_prefix": [sys.executable, str(CORE_ROOT / "tests" / "visual_asset_plugin_fakes.py")],
        "timeout_seconds": 2,
        "environment": {},
        "enabled": False,
        "plugin_version_command": [sys.executable, str(CORE_ROOT / "tests" / "visual_asset_plugin_fakes.py"), "--version"],
        "expected_source_revision": revision,
        "require_clean_worktree": clean,
    }


def init_checkout(root: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Phase 3B Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "phase3b@example.invalid"], cwd=root, check=True)
    (root / "tracked.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True
    ).stdout.strip()


class Phase3BStaticReadinessTests(unittest.TestCase):
    def test_three_exact_disabled_readiness_records_are_static_and_portable(self):
        config = readiness_config()
        normalized = normalize_visual_plugin_config(config)
        self.assertEqual(normalized, config)
        self.assertEqual(
            config["plugins"],
            [
                {
                    "plugin_id": "org.deeptalk.mg",
                    "plugin_version": "1.0.0-contract-v1",
                    "plugin_root": "<plugin-root>/deeptalk-mg",
                    "argv_prefix": ["node", "scripts/contract-runner.js"],
                    "timeout_seconds": 180,
                    "environment": {"TZ": "UTC", "DEEPTALK_DETERMINISTIC": "1"},
                    "enabled": False,
                    "plugin_version_command": ["node", "scripts/contract-runner.js", "--version"],
                    "expected_source_revision": "7ae59f1115da8a011113c81f31d320783b0ce8a4",
                    "require_clean_worktree": True,
                },
                {
                    "plugin_id": "org.deeptalk.illustrated-metaphor",
                    "plugin_version": "0.2.0-contract-runner",
                    "plugin_root": "<plugin-root>/deeptalk-illustrated-metaphor",
                    "argv_prefix": ["python3", "scripts/contract_runner.py"],
                    "timeout_seconds": 120,
                    "environment": {"TZ": "UTC", "DEEPTALK_DETERMINISTIC": "1"},
                    "enabled": False,
                    "plugin_version_command": ["python3", "scripts/contract_runner.py", "--version"],
                    "expected_source_revision": ILLUSTRATED_SHA,
                    "require_clean_worktree": True,
                },
                {
                    "plugin_id": "org.deeptalk.handdrawn-animation",
                    "plugin_version": "handdrawn-animation-contract/0.1.0",
                    "plugin_root": "<plugin-root>/deeptalk-handdrawn-animation",
                    "argv_prefix": ["node", "src/contract-runner.js"],
                    "timeout_seconds": 120,
                    "environment": {"TZ": "UTC", "DEEPTALK_DETERMINISTIC": "1"},
                    "enabled": False,
                    "plugin_version_command": ["node", "src/contract-runner.js", "--version"],
                    "expected_source_revision": HANDDRAWN_SHA,
                    "require_clean_worktree": True,
                },
            ],
        )
        self.assertTrue(all(not plugin["enabled"] for plugin in config["plugins"]))

        relocated = copy.deepcopy(config)
        for plugin in relocated["plugins"]:
            plugin["plugin_root"] = "/another-machine/plugins/" + plugin["plugin_id"]
        self.assertEqual(config_digest(config), config_digest(relocated))

    def test_wrong_revision_and_dirty_checkout_fail_before_runner_version_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            revision = init_checkout(root)
            with self.assertRaisesRegex(VisualPluginPreflightError, "source_revision_mismatch"):
                preflight_visual_plugin(fake_plugin(root=root, revision="0" * 40))

            (root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(VisualPluginPreflightError, "dirty_worktree"):
                preflight_visual_plugin(fake_plugin(root=root, revision=revision))

    def test_version_mismatch_fails_closed_after_a_clean_exact_preflight(self):
        plugin = fake_plugin(root=CORE_ROOT, revision=CORE_SHA, version="wrong-version", clean=False)
        with self.assertRaisesRegex(ValueError, "plugin_version_mismatch"):
            resolve_plugin_version(plugin)


@unittest.skipUnless(
    os.environ.get("DEEPTALK_RUN_PHASE3B_READINESS") == "1",
    "set DEEPTALK_RUN_PHASE3B_READINESS=1 for real preflight/version checks only",
)
class RealPhase3BReadinessTests(unittest.TestCase):
    def test_pinned_illustrated_and_handdrawn_checkouts_pass_preflight_and_version_without_generation(self):
        roots = {
            "org.deeptalk.illustrated-metaphor": Path(
                os.environ.get("DEEPTALK_ILLUSTRATED_PLUGIN_ROOT", CORE_ROOT.parent / "deeptalk-illustrated-metaphor")
            ),
            "org.deeptalk.handdrawn-animation": Path(
                os.environ.get("DEEPTALK_HANDDRAWN_PLUGIN_ROOT", CORE_ROOT.parent / "deeptalk-handdrawn-animation")
            ),
        }
        for entry in readiness_config()["plugins"]:
            if entry["plugin_id"] not in roots:
                continue
            with self.subTest(plugin_id=entry["plugin_id"]):
                plugin = copy.deepcopy(entry)
                plugin["plugin_root"] = str(roots[entry["plugin_id"]])
                runner_path = roots[entry["plugin_id"]].joinpath(*plugin["argv_prefix"][1:])
                self.assertTrue(runner_path.is_file(), runner_path)
                preflight = preflight_visual_plugin(plugin)
                self.assertEqual(preflight["actual_source_revision"], plugin["expected_source_revision"])
                self.assertTrue(preflight["clean_worktree"])
                self.assertEqual(resolve_plugin_version(plugin, preflight=preflight), plugin["plugin_version"])


if __name__ == "__main__":
    unittest.main()
