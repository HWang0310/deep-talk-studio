import copy
import json
import unittest
from pathlib import Path

from deeptalk_studio.visual_plugin_config import (
    VisualPluginConfigError,
    config_digest,
    normalize_visual_plugin_config,
)


def fake_config():
    return {"config_version": "visual-asset-plugin-config/1", "plugins": [{
        "plugin_id": "fake-visual-plugin", "plugin_root": ".", "argv_prefix": ["python3", "tests/visual_asset_plugin_fakes.py"],
        "timeout_seconds": 3, "environment": {"FAKE_PLUGIN": "1"}, "enabled": True,
        "plugin_version_command": ["python3", "--version"], "expected_source_revision": "fake-only", "require_clean_worktree": False,
    }]}


class VisualPluginConfigTests(unittest.TestCase):
    def test_normalizes_fake_static_config_and_has_deterministic_digest(self):
        self.assertEqual(normalize_visual_plugin_config(fake_config()), fake_config())
        self.assertEqual(config_digest(fake_config()), config_digest(copy.deepcopy(fake_config())))

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

    def test_tracked_real_plugin_examples_remain_disabled(self):
        path = Path(__file__).resolve().parents[1] / "config/visual-asset-plugins.example.json"
        config = normalize_visual_plugin_config(json.loads(path.read_text(encoding="utf-8")))
        self.assertTrue(all(not plugin["enabled"] for plugin in config["plugins"]))


if __name__ == "__main__":
    unittest.main()
