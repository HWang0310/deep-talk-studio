"""TDD tests for DT-V1-AUX-001 — explicit generated visual plugin invocation.

These tests verify the invocation-scoped single-plugin selection path that lets
a creator explicitly request one named visual family (MG, 小黑漫画, 手绘动画)
without automatic family selection, winner ranking, or overlap resolution.

The tests reuse existing Contract V1 fixtures and the existing orchestration
runtime; they verify alias resolution, single-plugin isolation, ABSTAIN honesty,
failure isolation, disabled-plugin rejection, and unknown-alias fail-closed.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.explicit_visual_assist import (
    ExplicitVisualAssistError,
    resolve_visual_family,
    run_explicit_visual_assist,
)
from deeptalk_studio.visual_generation_policy import load_candidate_generation_policy


ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True,
).stdout.strip()
POLICY = load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json")

OPPORTUNITY = {
    "opportunity_id": "VO-DT-V1-AUX-001",
    "spoken_semantics": "Resource accumulation causes cascading pressure.",
    "visual_purpose": "Explain the causal chain with structured visuals.",
    "a_roll_window": {"start_ms": 1000, "end_ms": 2000},
    "target_duration_ms": 1000,
    "language": "zh-CN",
    "canvas": {"width": 16, "height": 16},
    "factual_context": [],
}

# Canonical plugin IDs from committed config
MG_ID = "org.deeptalk.mg"
ILLUSTRATED_ID = "org.deeptalk.illustrated-metaphor"
HANDDRAWN_ID = "org.deeptalk.handdrawn-animation"

# Plugin IDs used for synthetic fake-plugin tests (parallel to Phase 5 tests)
FAKE_MG_ID = "org.deeptalk.mg"
FAKE_ILLUSTRATED_ID = "org.deeptalk.illustrated-metaphor"
FAKE_HANDDRAWN_ID = "org.deeptalk.handdrawn-animation"


def _fake_plugin(plugin_id: str, scenario: str = "suitable", enabled: bool = True) -> dict:
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
        "enabled": enabled,
        "plugin_version_command": [sys.executable, "tests/visual_asset_plugin_fakes.py", "--version"],
        "expected_source_revision": CORE_SHA,
        "require_clean_worktree": False,
    }


def _config(plugins: list[dict]) -> dict:
    return {
        "config_version": "visual-asset-plugin-config/1",
        "plugins": plugins,
    }


def _three_plugin_config(
    mg_scenario: str = "suitable",
    ill_scenario: str = "suitable",
    hd_scenario: str = "suitable",
    enabled: tuple[bool, bool, bool] = (True, True, True),
) -> dict:
    return _config([
        _fake_plugin(FAKE_MG_ID, mg_scenario, enabled=enabled[0]),
        _fake_plugin(FAKE_ILLUSTRATED_ID, ill_scenario, enabled=enabled[1]),
        _fake_plugin(FAKE_HANDDRAWN_ID, hd_scenario, enabled=enabled[2]),
    ])


PLAN_DIGEST = "a" * 64


# ---------------------------------------------------------------------------
# 1. Alias -> canonical plugin id
# ---------------------------------------------------------------------------
class AliasResolutionTests(unittest.TestCase):
    def test_mg_alias(self):
        self.assertEqual(resolve_visual_family("mg"), MG_ID)

    def test_xiaohei_alias(self):
        self.assertEqual(resolve_visual_family("xiaohei"), ILLUSTRATED_ID)

    def test_handdrawn_alias(self):
        self.assertEqual(resolve_visual_family("handdrawn"), HANDDRAWN_ID)

    def test_case_insensitive(self):
        self.assertEqual(resolve_visual_family("MG"), MG_ID)
        self.assertEqual(resolve_visual_family("XiaoHei"), ILLUSTRATED_ID)
        self.assertEqual(resolve_visual_family("HandDrawn"), HANDDRAWN_ID)

    def test_unknown_alias_fails_closed(self):
        with self.assertRaises(ExplicitVisualAssistError):
            resolve_visual_family("unknown")
        with self.assertRaises(ExplicitVisualAssistError):
            resolve_visual_family("")


# ---------------------------------------------------------------------------
# 2-4. Only selected plugin is invoked
# ---------------------------------------------------------------------------
class SinglePluginInvocationTests(unittest.TestCase):
    def _run(self, config: dict, alias: str, scenario_overrides: dict | None = None):
        cfg = copy.deepcopy(config)
        if scenario_overrides:
            for p in cfg["plugins"]:
                if p["plugin_id"] in scenario_overrides:
                    p["argv_prefix"] = [
                        sys.executable, "tests/visual_asset_plugin_fakes.py",
                        "--scenario", scenario_overrides[p["plugin_id"]],
                    ]
        with tempfile.TemporaryDirectory() as root:
            return run_explicit_visual_assist(
                opportunity=OPPORTUNITY,
                plugin_config=cfg,
                alias=alias,
                production_profile="RICH",
                policy=POLICY,
                job_root=Path(root),
                visual_opportunity_plan_digest=PLAN_DIGEST,
                task_id="DT-V1-AUX-001",
            )

    def test_mg_only_invokes_mg(self):
        result = self._run(_three_plugin_config(), "mg")
        invoked = {r["plugin_id"] for r in result["portfolio"]["opportunities"][0]["proposals"] if r["suitability_execution"] is not None}
        self.assertIn(MG_ID, invoked)
        self.assertNotIn(ILLUSTRATED_ID, invoked)
        self.assertNotIn(HANDDRAWN_ID, invoked)

    def test_xiaohei_only_invokes_illustrated(self):
        result = self._run(_three_plugin_config(), "xiaohei")
        invoked = {r["plugin_id"] for r in result["portfolio"]["opportunities"][0]["proposals"] if r["suitability_execution"] is not None}
        self.assertIn(ILLUSTRATED_ID, invoked)
        self.assertNotIn(MG_ID, invoked)
        self.assertNotIn(HANDDRAWN_ID, invoked)

    def test_handdrawn_only_invokes_handdrawn(self):
        result = self._run(_three_plugin_config(), "handdrawn")
        invoked = {r["plugin_id"] for r in result["portfolio"]["opportunities"][0]["proposals"] if r["suitability_execution"] is not None}
        self.assertIn(HANDDRAWN_ID, invoked)
        self.assertNotIn(MG_ID, invoked)
        self.assertNotIn(ILLUSTRATED_ID, invoked)


# ---------------------------------------------------------------------------
# 5. Non-selected plugins are not invoked (no execution evidence)
# ---------------------------------------------------------------------------
class NonSelectedPluginExclusionTests(unittest.TestCase):
    def test_non_selected_plugins_have_no_execution(self):
        with tempfile.TemporaryDirectory() as root:
            result = run_explicit_visual_assist(
                opportunity=OPPORTUNITY,
                plugin_config=_three_plugin_config(),
                alias="mg",
                production_profile="RICH",
                policy=POLICY,
                job_root=Path(root),
                visual_opportunity_plan_digest=PLAN_DIGEST,
                task_id="DT-V1-AUX-001",
            )
        proposals = result["portfolio"]["opportunities"][0]["proposals"]
        for proposal in proposals:
            if proposal["plugin_id"] != MG_ID:
                self.assertIsNone(
                    proposal["suitability_execution"],
                    f"Plugin {proposal['plugin_id']} should not have been invoked",
                )


# ---------------------------------------------------------------------------
# 6. ABSTAIN -> no fake Candidate
# ---------------------------------------------------------------------------
class AbstainTests(unittest.TestCase):
    def test_abstain_produces_no_fake_candidate(self):
        config = _three_plugin_config(mg_scenario="abstain")
        with tempfile.TemporaryDirectory() as root:
            result = run_explicit_visual_assist(
                opportunity=OPPORTUNITY,
                plugin_config=config,
                alias="mg",
                production_profile="RICH",
                policy=POLICY,
                job_root=Path(root),
                visual_opportunity_plan_digest=PLAN_DIGEST,
                task_id="DT-V1-AUX-001",
            )
        candidates = result["portfolio"]["opportunities"][0]["candidates"]
        self.assertEqual(len(candidates), 0)
        self.assertEqual(result["summary"]["status"], "NO_CANDIDATE")
        self.assertIn("ABSTAIN", result["summary"]["reason"])


# ---------------------------------------------------------------------------
# 7. Plugin failure -> user-readable failure
# ---------------------------------------------------------------------------
class PluginFailureTests(unittest.TestCase):
    def test_plugin_failure_is_user_readable(self):
        config = _three_plugin_config(mg_scenario="failed")
        with tempfile.TemporaryDirectory() as root:
            result = run_explicit_visual_assist(
                opportunity=OPPORTUNITY,
                plugin_config=config,
                alias="mg",
                production_profile="RICH",
                policy=POLICY,
                job_root=Path(root),
                visual_opportunity_plan_digest=PLAN_DIGEST,
                task_id="DT-V1-AUX-001",
            )
        self.assertEqual(result["summary"]["status"], "FAILED")
        self.assertTrue(
            "mg" in result["summary"]["reason"].lower()
            or "org.deeptalk.mg" in result["summary"]["reason"]
        )


# ---------------------------------------------------------------------------
# 8. READY + Core ACCEPTED -> creator-visible result
# ---------------------------------------------------------------------------
class ReadyAcceptedTests(unittest.TestCase):
    def test_ready_accepted_returns_creator_visible_result(self):
        config = _three_plugin_config(mg_scenario="suitable")
        with tempfile.TemporaryDirectory() as root:
            result = run_explicit_visual_assist(
                opportunity=OPPORTUNITY,
                plugin_config=config,
                alias="mg",
                production_profile="RICH",
                policy=POLICY,
                job_root=Path(root),
                visual_opportunity_plan_digest=PLAN_DIGEST,
                task_id="DT-V1-AUX-001",
            )
        self.assertEqual(result["summary"]["status"], "READY")
        self.assertIn("candidates", result["summary"])
        self.assertGreater(len(result["summary"]["candidates"]), 0)
        candidate = result["summary"]["candidates"][0]
        self.assertEqual(candidate["candidate_status"], "READY")
        self.assertEqual(candidate["core_acceptance"], "ACCEPTED")
        self.assertIn("plugin_id", candidate)
        self.assertEqual(candidate["plugin_id"], MG_ID)


# ---------------------------------------------------------------------------
# 9. Disabled plugin -> clear failure
# ---------------------------------------------------------------------------
class DisabledPluginTests(unittest.TestCase):
    def test_disabled_plugin_fails_clearly(self):
        config = _three_plugin_config(enabled=(False, True, True))
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ExplicitVisualAssistError) as ctx:
                run_explicit_visual_assist(
                    opportunity=OPPORTUNITY,
                    plugin_config=config,
                    alias="mg",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest=PLAN_DIGEST,
                    task_id="DT-V1-AUX-001",
                )
        self.assertIn("disabled", str(ctx.exception).lower())


# ---------------------------------------------------------------------------
# 10. Unknown alias -> fail closed
# ---------------------------------------------------------------------------
class UnknownAliasTests(unittest.TestCase):
    def test_unknown_alias_fails_closed_before_invocation(self):
        config = _three_plugin_config()
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ExplicitVisualAssistError):
                run_explicit_visual_assist(
                    opportunity=OPPORTUNITY,
                    plugin_config=config,
                    alias="nonexistent",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest=PLAN_DIGEST,
                    task_id="DT-V1-AUX-001",
                )


# ---------------------------------------------------------------------------
# 11. Invalid / missing Visual Opportunity -> fail closed
# ---------------------------------------------------------------------------
class InvalidOpportunityTests(unittest.TestCase):
    def test_missing_opportunity_fails_closed(self):
        config = _three_plugin_config()
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ExplicitVisualAssistError, ValueError)):
                run_explicit_visual_assist(
                    opportunity=None,
                    plugin_config=config,
                    alias="mg",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest=PLAN_DIGEST,
                    task_id="DT-V1-AUX-001",
                )

    def test_empty_opportunities_list_fails_closed(self):
        config = _three_plugin_config()
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ExplicitVisualAssistError, ValueError)):
                run_explicit_visual_assist(
                    opportunity=[],
                    plugin_config=config,
                    alias="mg",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest=PLAN_DIGEST,
                    task_id="DT-V1-AUX-001",
                )

    def test_opportunity_missing_required_field_fails_closed(self):
        config = _three_plugin_config()
        bad_opp = {"opportunity_id": "VO-bad"}
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ExplicitVisualAssistError, ValueError)):
                run_explicit_visual_assist(
                    opportunity=bad_opp,
                    plugin_config=config,
                    alias="mg",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest=PLAN_DIGEST,
                    task_id="DT-V1-AUX-001",
                )


# ---------------------------------------------------------------------------
# 12. Plugin not in config -> fail closed
# ---------------------------------------------------------------------------
class PluginNotConfiguredTests(unittest.TestCase):
    def test_plugin_not_in_config_fails_closed(self):
        config = _config([
            _fake_plugin(FAKE_MG_ID, "suitable"),
            _fake_plugin(FAKE_HANDDRAWN_ID, "suitable"),
        ])
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ExplicitVisualAssistError) as ctx:
                run_explicit_visual_assist(
                    opportunity=OPPORTUNITY,
                    plugin_config=config,
                    alias="xiaohei",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest=PLAN_DIGEST,
                    task_id="DT-V1-AUX-001",
                )
        self.assertIn("not configured", str(ctx.exception).lower())


# ---------------------------------------------------------------------------
# 13. Missing plan digest -> fail closed
# ---------------------------------------------------------------------------
class InvalidPlanDigestTests(unittest.TestCase):
    def test_missing_plan_digest_fails_closed(self):
        config = _three_plugin_config()
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ExplicitVisualAssistError, ValueError)):
                run_explicit_visual_assist(
                    opportunity=OPPORTUNITY,
                    plugin_config=config,
                    alias="mg",
                    production_profile="RICH",
                    policy=POLICY,
                    job_root=Path(root),
                    visual_opportunity_plan_digest="",
                    task_id="DT-V1-AUX-001",
                )


if __name__ == "__main__":
    unittest.main()
