"""Opt-in real-runner acceptance for DT-CORE-5-001."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from evaluations.visual_asset_engine.phase5_three_plugin_eval import (
    EXPECTED_FAMILIES,
    PLUGIN_IDS,
    _probe_media,
    real_plugin_config,
    run_phase5_evaluation,
)


CORE_ROOT = Path(__file__).resolve().parents[1]
DEEPTALK_ROOT = CORE_ROOT.parents[1] if CORE_ROOT.parent.name == ".worktrees" else CORE_ROOT.parent


class Phase5EvaluationConfigTests(unittest.TestCase):
    def test_runtime_config_enables_exactly_three_without_mutating_tracked_config(self):
        tracked_path = CORE_ROOT / "config/visual-asset-plugins.example.json"
        before = tracked_path.read_bytes()
        roots = {
            "org.deeptalk.mg": DEEPTALK_ROOT / "deeptalk-mg",
            "org.deeptalk.illustrated-metaphor": DEEPTALK_ROOT / "deeptalk-illustrated-metaphor",
            "org.deeptalk.handdrawn-animation": DEEPTALK_ROOT / "deeptalk-handdrawn-animation",
        }
        runtime = real_plugin_config(roots)
        self.assertEqual({item["plugin_id"] for item in runtime["plugins"]}, set(PLUGIN_IDS))
        self.assertTrue(all(item["enabled"] for item in runtime["plugins"]))
        self.assertEqual(tracked_path.read_bytes(), before)
        tracked = json.loads(before)
        self.assertTrue(all(not item["enabled"] for item in tracked["plugins"]))

    def test_media_probe_rejects_wrong_codec_resolution_and_duration(self):
        cases = {
            "codec": {
                "streams": [{"codec_name": "mpeg4", "width": 1920, "height": 1080}],
                "format": {"duration": "7.000000"},
            },
            "resolution": {
                "streams": [{"codec_name": "h264", "width": 1280, "height": 720}],
                "format": {"duration": "7.000000"},
            },
            "duration": {
                "streams": [{"codec_name": "h264", "width": 1920, "height": 1080}],
                "format": {"duration": "6.800000"},
            },
        }
        for name, payload in cases.items():
            with self.subTest(name=name), patch(
                "evaluations.visual_asset_engine.phase5_three_plugin_eval.subprocess.run",
                return_value=SimpleNamespace(stdout=json.dumps(payload)),
            ), self.assertRaisesRegex(RuntimeError, "PRIMARY_MEDIA"):
                _probe_media(Path("candidate.mp4"), expected_duration_ms=7000)


@unittest.skipUnless(
    os.environ.get("DEEPTALK_RUN_PHASE5_INTEGRATION") == "1",
    "set DEEPTALK_RUN_PHASE5_INTEGRATION=1 and DEEPTALK_PHASE5_OUTPUT_ROOT for real renders",
)
class RealThreePluginIntegrationTests(unittest.TestCase):
    def test_three_pinned_runners_order_failure_pack_and_map(self):
        output = os.environ.get("DEEPTALK_PHASE5_OUTPUT_ROOT")
        self.assertTrue(output, "DEEPTALK_PHASE5_OUTPUT_ROOT is required")
        evidence = run_phase5_evaluation(
            Path(output),
            {
                "org.deeptalk.mg": Path(os.environ.get("DEEPTALK_MG_PLUGIN_ROOT", DEEPTALK_ROOT / "deeptalk-mg")),
                "org.deeptalk.illustrated-metaphor": Path(os.environ.get("DEEPTALK_ILLUSTRATED_PLUGIN_ROOT", DEEPTALK_ROOT / "deeptalk-illustrated-metaphor")),
                "org.deeptalk.handdrawn-animation": Path(os.environ.get("DEEPTALK_HANDDRAWN_PLUGIN_ROOT", DEEPTALK_ROOT / "deeptalk-handdrawn-animation")),
            },
        )
        self.assertEqual(evidence["order_independence"], "PASS")
        self.assertEqual(evidence["failure_isolation"], "PASS")
        self.assertEqual(set(evidence["asset_families"]), EXPECTED_FAMILIES)
        self.assertEqual(len(evidence["candidate_ids"]), 3)
        self.assertEqual(evidence["creator_eligible_candidate_ids"], evidence["candidate_ids"])
        self.assertEqual(set(evidence["numeric_no_call_plugins"]), set(PLUGIN_IDS))
        self.assertEqual(set(evidence["numeric_abstain_plugins"]), set(PLUGIN_IDS))
        for path in evidence["artifacts"].values():
            self.assertTrue(Path(path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
