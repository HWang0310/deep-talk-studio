import copy
import json
import subprocess
import unittest
from pathlib import Path

from deeptalk_studio.visual_plugin_config import (
    VisualPluginConfigError,
    config_digest,
    normalize_visual_plugin_config,
)

ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def fake_config():
    return {"config_version": "visual-asset-plugin-config/1", "plugins": [{
        "plugin_id": "fake-visual-plugin", "plugin_version": "fake-1", "plugin_root": ".", "argv_prefix": ["python3", "tests/visual_asset_plugin_fakes.py"],
        "timeout_seconds": 3, "environment": {"FAKE_PLUGIN": "1"}, "enabled": True,
        "plugin_version_command": ["python3", "--version"], "expected_source_revision": CORE_SHA, "require_clean_worktree": False,
    }]}


class VisualPluginConfigTests(unittest.TestCase):
    def test_normalizes_fake_static_config_and_has_deterministic_digest(self):
        self.assertEqual(normalize_visual_plugin_config(fake_config()), fake_config())
        self.assertEqual(config_digest(fake_config()), config_digest(copy.deepcopy(fake_config())))

    def test_config_digest_keeps_machine_plugin_root_out_of_portable_identity(self):
        first = fake_config(); first["plugins"][0]["plugin_root"] = "/machine-a/plugins/mg"
        second = fake_config(); second["plugins"][0]["plugin_root"] = "/machine-b/checkouts/mg"
        self.assertEqual(config_digest(first), config_digest(second))

    def test_rejects_shell_string_duplicates_bad_timeout_and_unknown_fields(self):
        shell = fake_config(); shell["plugins"][0]["argv_prefix"] = "python plugin.py"
        with self.assertRaisesRegex(VisualPluginConfigError, "argv_prefix"):
            normalize_visual_plugin_config(shell)
        duplicate = fake_config(); duplicate["plugins"].append(copy.deepcopy(duplicate["plugins"][0]))
        with self.assertRaisesRegex(VisualPluginConfigError, "plugin_id"):
            normalize_visual_plugin_config(duplicate)
        timeout = fake_config(); timeout["plugins"][0]["timeout_seconds"] = 0
        with self.assertRaisesRegex(VisualPluginConfigError, "timeout"):
            normalize_visual_plugin_config(timeout)
        unknown = fake_config(); unknown["plugins"][0]["shell"] = True
        with self.assertRaises(VisualPluginConfigError):
            normalize_visual_plugin_config(unknown)
        unpinned = fake_config(); unpinned["plugins"][0]["expected_source_revision"] = "fake-only"
        with self.assertRaisesRegex(VisualPluginConfigError, "expected_source_revision"):
            normalize_visual_plugin_config(unpinned)

    def test_tracked_real_plugin_examples_remain_disabled(self):
        path = Path(__file__).resolve().parents[1] / "config/visual-asset-plugins.example.json"
        config = normalize_visual_plugin_config(json.loads(path.read_text(encoding="utf-8")))
        self.assertTrue(all(not plugin["enabled"] for plugin in config["plugins"]))

    def test_config_v1_accepts_disabled_legacy_entry_without_static_plugin_version(self):
        legacy = fake_config()
        plugin = legacy["plugins"][0]
        plugin.pop("plugin_version")
        plugin["enabled"] = False
        plugin["expected_source_revision"] = "0" * 40
        normalized = normalize_visual_plugin_config(legacy)
        self.assertNotIn("plugin_version", normalized["plugins"][0])

    def test_enabled_pinned_entry_requires_static_plugin_version(self):
        pinned = fake_config()
        pinned["plugins"][0].pop("plugin_version")
        with self.assertRaisesRegex(VisualPluginConfigError, "plugin_version"):
            normalize_visual_plugin_config(pinned)


if __name__ == "__main__":
    unittest.main()
