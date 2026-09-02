"""Phase 5 compatibility tests for three independent Contract V1 runners."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_edit_map import (
    build_edit_map_csv,
    build_edit_map_json,
    build_edit_map_markdown,
)
from deeptalk_studio.candidate_pack_workflow import build_candidate_asset_pack
from deeptalk_studio.candidate_portfolio import orchestrate_candidate_portfolio
from deeptalk_studio.visual_generation_policy import load_candidate_generation_policy


ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True,
).stdout.strip()
POLICY = load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json")
OPPORTUNITY = {
    "opportunity_id": "VO-DT-CORE-5-001-order",
    "spoken_semantics": "持续累积的资源占用通过传导机制，使分散压力逐步集中并越过临界点。",
    "visual_purpose": "用结构化因果过程解释积累、压力与临界变化。",
    "a_roll_window": {"start_ms": 1000, "end_ms": 2000},
    "target_duration_ms": 1000,
    "language": "zh-CN",
    "canvas": {"width": 16, "height": 16},
    "factual_context": [],
}
PLUGIN_IDS = ("org.example.alpha", "org.example.beta", "org.example.gamma")


def _plugin(plugin_id: str, scenario: str = "suitable") -> dict:
    return {
        "plugin_id": plugin_id,
        "plugin_version": "fake-1",
        "plugin_root": str(ROOT),
        "argv_prefix": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--scenario", scenario],
        "timeout_seconds": 5,
        "environment": {
            "FAKE_PLUGIN_ID": plugin_id,
            "FAKE_PLUGIN_VERSION": "fake-1",
            "FAKE_CANDIDATE_ID": "CAN-" + plugin_id.rsplit(".", 1)[-1],
            "FAKE_WRITE_MEDIA": "1",
        },
        "enabled": True,
        "plugin_version_command": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--version"],
        "expected_source_revision": CORE_SHA,
        "require_clean_worktree": False,
    }


def _config(scenarios: tuple[str, str, str] = ("suitable", "suitable", "suitable")) -> dict:
    return {
        "config_version": "visual-asset-plugin-config/1",
        "plugins": [_plugin(plugin_id, scenario) for plugin_id, scenario in zip(PLUGIN_IDS, scenarios)],
    }


def _run(root: Path, config: dict, *, invocation: tuple[str, ...], collection: tuple[str, ...]) -> dict:
    return orchestrate_candidate_portfolio(
        [OPPORTUNITY],
        config,
        production_profile="RICH",
        policy=POLICY,
        job_root=root,
        visual_opportunity_plan_digest="5" * 64,
        task_id="DT-CORE-5-001",
        request_namespace="DT-CORE-5-001-order-proof",
        plugin_invocation_order=invocation,
        plugin_collection_order=collection,
    )


def _raw_semantics(portfolio: dict) -> dict:
    block = portfolio["opportunities"][0]
    return {
        "portfolio_id": portfolio["portfolio_id"],
        "plugin_config_digest": portfolio["plugin_config_digest"],
        "opportunity": block["opportunity"],
        "proposals": [
            (item["plugin_id"], item["suitability_raw"])
            for item in block["proposals"]
        ],
        "policy_records": block["policy_records"],
        "generations": [
            (item["plugin_id"], item["generation_raw"])
            for item in block["generation_records"]
        ],
        "candidates": [
            {
                "plugin_id": item["plugin_id"],
                "proposal_id": item["proposal_id"],
                "suitability": item["suitability"],
                "plugin_candidate": item["plugin_candidate"],
                "core_acceptance": item["core_acceptance"],
                "suggested_review_order": item.get("suggested_review_order"),
            }
            for item in block["candidates"]
        ],
        "audit_lineage": [
            {
                "opportunity_id": item["opportunity_id"],
                "plugin_id": item["plugin_id"],
                "operation": item["operation"],
                "request_identity": item["execution"]["request_identity"],
                "result_identity": item["execution"]["result_identity"],
                "raw_response": item["raw_response"],
                "request_snapshot": item["request_snapshot"],
            }
            for item in portfolio["audit_records"]
        ],
    }


class ThreePluginOrderingTests(unittest.TestCase):
    def test_actual_invocation_and_collection_order_do_not_change_semantics(self):
        with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as second_raw:
            first = _run(
                Path(first_raw), _config(),
                invocation=PLUGIN_IDS,
                collection=tuple(reversed(PLUGIN_IDS)),
            )
            second = _run(
                Path(second_raw), _config(),
                invocation=tuple(reversed(PLUGIN_IDS)),
                collection=PLUGIN_IDS,
            )

        self.assertEqual(_raw_semantics(first), _raw_semantics(second))
        candidates = first["opportunities"][0]["candidates"]
        self.assertEqual([item["plugin_id"] for item in candidates], list(PLUGIN_IDS))
        self.assertEqual([item["suggested_review_order"] for item in candidates], [1, 2, 3])
        self.assertTrue(all(item["core_acceptance"]["status"] == "ACCEPTED" for item in candidates))

    def test_config_list_order_is_not_part_of_portable_identity(self):
        with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as second_raw:
            config = _config()
            reversed_config = copy.deepcopy(config)
            reversed_config["plugins"].reverse()
            first = _run(Path(first_raw), config, invocation=PLUGIN_IDS, collection=PLUGIN_IDS)
            second = _run(Path(second_raw), reversed_config, invocation=PLUGIN_IDS, collection=PLUGIN_IDS)
        self.assertEqual(_raw_semantics(first), _raw_semantics(second))


class ThreePluginFailureIsolationTests(unittest.TestCase):
    def test_preflight_failure_preserves_two_candidates_through_pack_and_map(self):
        config = _config()
        config["plugins"][1]["expected_source_revision"] = "0" * 40
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            portfolio = _run(root / "jobs", config, invocation=PLUGIN_IDS, collection=PLUGIN_IDS)
            block = portfolio["opportunities"][0]
            failed = next(item for item in block["proposals"] if item["plugin_id"] == PLUGIN_IDS[1])
            self.assertEqual(failed["suitability_execution"]["status"], "FAILED")
            self.assertIsNone(failed["suitability_raw"])

            accepted = [item for item in block["candidates"] if item["core_acceptance"]["status"] == "ACCEPTED"]
            self.assertEqual([item["plugin_id"] for item in accepted], [PLUGIN_IDS[0], PLUGIN_IDS[2]])

            pack = build_candidate_asset_pack(
                portfolio, job_root=root / "jobs", dest_root=root / "staged",
            )
            edit_map = build_edit_map_json(pack)
            csv_text = build_edit_map_csv(pack)
            markdown = build_edit_map_markdown(pack)
            self.assertEqual(len(pack["opportunities"][0]["candidates"]), 2)
            self.assertEqual(len(edit_map["opportunities"][0]["candidates"]), 2)
            self.assertEqual(csv_text.count("\n"), 3)
            self.assertIn("CAN-alpha", markdown)
            self.assertIn("CAN-gamma", markdown)
            self.assertNotIn("CAN-beta", markdown)

    def test_mixed_outcomes_never_force_a_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            portfolio = _run(
                Path(raw), _config(("suitable", "abstain", "unavailable")),
                invocation=PLUGIN_IDS, collection=tuple(reversed(PLUGIN_IDS)),
            )
        block = portfolio["opportunities"][0]
        self.assertEqual(len(block["candidates"]), 1)
        self.assertEqual(block["candidates"][0]["plugin_id"], PLUGIN_IDS[0])
        policy = {item["plugin_id"]: item for item in block["policy_records"]}
        self.assertEqual(policy[PLUGIN_IDS[1]]["no_call_reason"], "ABSTAIN")
        self.assertEqual(policy[PLUGIN_IDS[2]]["no_call_reason"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
