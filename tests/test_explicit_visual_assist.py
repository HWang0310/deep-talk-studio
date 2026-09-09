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
    _resolve_latest_visual_opportunity_plan,
    _resolve_default_plugin_config,
    resolve_visual_family,
    run_explicit_visual_assist,
    run_explicit_visual_assist_auto,
)
from deeptalk_studio.visual_generation_policy import load_candidate_generation_policy
from deeptalk_studio.visual_opportunity_storage import save_visual_opportunity_plan


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

    def test_ready_accepted_candidate_includes_media_locator(self):
        """Regression: READY + ACCEPTED candidate must include a usable media locator."""
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
        candidate = result["summary"]["candidates"][0]
        self.assertIn("media_locator", candidate)
        self.assertTrue(candidate["media_locator"].startswith("local-plugin-artifact://"))
        self.assertIn("media_uri", candidate)
        self.assertTrue(candidate["media_uri"].startswith("local-runner://"))

    def test_ready_accepted_candidate_includes_media_sha256(self):
        """Regression: READY + ACCEPTED candidate must include verified sha256."""
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
        candidate = result["summary"]["candidates"][0]
        self.assertIn("media_sha256", candidate)
        self.assertEqual(len(candidate["media_sha256"]), 64)
        self.assertIn("observed_sha256", candidate)
        self.assertEqual(candidate["media_sha256"], candidate["observed_sha256"])


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


# ---------------------------------------------------------------------------
# 14. Auto-resolution: resolve latest Visual Opportunity Plan from disk
# ---------------------------------------------------------------------------
class AutoResolutionPlanTests(unittest.TestCase):
    def _make_valid_plan(self, opportunities: list[dict] | None = None) -> dict:
        """Build a minimal valid visual-opportunity-plan/1 artifact."""
        import hashlib
        import json as _json
        opps = opportunities or [OPPORTUNITY]
        plan = {
            "artifact_version": "visual-opportunity-plan/1",
            "plan_id": "VOP-" + hashlib.sha256(b"test-plan").hexdigest()[:24],
            "semantic_timeline_digest": "a" * 64,
            "alignment_digest": "b" * 64,
            "transcript_digest": "c" * 64,
            "directives_digest": "d" * 64,
            "reviewed_script_digest": "e" * 64,
            "defaults_digest": "f" * 64,
            "span_audit": [
                {"span_id": "span-1", "status": "OPPORTUNITY_CREATED"},
            ],
            "opportunities": opps,
        }
        payload = dict(plan)
        digest = hashlib.sha256(
            _json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        plan["plan_digest"] = digest
        return plan

    def test_resolve_latest_plan_finds_existing_plan(self):
        plan = self._make_valid_plan()
        with tempfile.TemporaryDirectory() as root:
            save_visual_opportunity_plan(plan, Path(root))
            loaded, digest = _resolve_latest_visual_opportunity_plan(Path(root))
        self.assertEqual(loaded["plan_id"], plan["plan_id"])
        self.assertEqual(digest, plan["plan_digest"])

    def test_resolve_latest_plan_no_plans_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ExplicitVisualAssistError) as ctx:
                _resolve_latest_visual_opportunity_plan(Path(root))
        self.assertIn("未找到", str(ctx.exception))

    def test_resolve_latest_plan_picks_most_recent(self):
        import time
        import hashlib
        import json as _json
        plan_old = self._make_valid_plan()
        time.sleep(0.05)
        # Build a second plan with a different plan_id from scratch
        plan_new = {
            "artifact_version": "visual-opportunity-plan/1",
            "plan_id": "VOP-" + hashlib.sha256(b"second-plan").hexdigest()[:24],
            "semantic_timeline_digest": "a" * 64,
            "alignment_digest": "b" * 64,
            "transcript_digest": "c" * 64,
            "directives_digest": "d" * 64,
            "reviewed_script_digest": "e" * 64,
            "defaults_digest": "f" * 64,
            "span_audit": [
                {"span_id": "span-1", "status": "OPPORTUNITY_CREATED"},
            ],
            "opportunities": [OPPORTUNITY],
        }
        payload = dict(plan_new)
        plan_new["plan_digest"] = hashlib.sha256(
            _json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        with tempfile.TemporaryDirectory() as root:
            save_visual_opportunity_plan(plan_old, Path(root))
            save_visual_opportunity_plan(plan_new, Path(root))
            loaded, _ = _resolve_latest_visual_opportunity_plan(Path(root))
        self.assertEqual(loaded["plan_id"], plan_new["plan_id"])

    def test_resolve_default_plugin_config_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ExplicitVisualAssistError) as ctx:
                _resolve_default_plugin_config(Path(root))
        self.assertIn("不存在", str(ctx.exception))


# ---------------------------------------------------------------------------
# 15. Auto-resolution: run_explicit_visual_assist_auto end-to-end
# ---------------------------------------------------------------------------
class AutoResolutionIntegrationTests(unittest.TestCase):
    def _make_valid_plan(self, opportunities: list[dict] | None = None) -> dict:
        import hashlib
        import json as _json
        opps = opportunities or [OPPORTUNITY]
        plan = {
            "artifact_version": "visual-opportunity-plan/1",
            "plan_id": "VOP-" + hashlib.sha256(b"test-auto-plan").hexdigest()[:24],
            "semantic_timeline_digest": "a" * 64,
            "alignment_digest": "b" * 64,
            "transcript_digest": "c" * 64,
            "directives_digest": "d" * 64,
            "reviewed_script_digest": "e" * 64,
            "defaults_digest": "f" * 64,
            "span_audit": [
                {"span_id": "span-1", "status": "OPPORTUNITY_CREATED"},
            ],
            "opportunities": opps,
        }
        payload = dict(plan)
        digest = hashlib.sha256(
            _json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        plan["plan_digest"] = digest
        return plan

    def _make_project_tree(self, tmpdir: str, config: dict, plan: dict) -> Path:
        """Create a minimal project tree with config + VOP artifact."""
        root = Path(tmpdir)
        # Plugin config
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "visual-asset-plugins.local.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Policy
        policy_src = ROOT / "config" / "candidate-generation-profile.json"
        (config_dir / "candidate-generation-profile.json").write_text(
            policy_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
        # VOP artifact
        vop_root = root / ".artifacts" / "visual-opportunity"
        save_visual_opportunity_plan(plan, vop_root)
        return root

    def test_auto_resolution_runs_plugin_and_returns_media(self):
        config = _three_plugin_config(mg_scenario="suitable")
        plan = self._make_valid_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self._make_project_tree(tmpdir, config, plan)
            with tempfile.TemporaryDirectory() as job_root:
                result = run_explicit_visual_assist_auto(
                    "mg",
                    project_root=project_root,
                    job_root=Path(job_root),
                )
        self.assertEqual(result["summary"]["status"], "READY")
        candidate = result["summary"]["candidates"][0]
        self.assertIn("media_locator", candidate)
        self.assertTrue(candidate["media_locator"].startswith("local-plugin-artifact://"))
        self.assertIn("media_uri", candidate)

    def test_auto_resolution_no_plan_fails_closed(self):
        config = _three_plugin_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "visual-asset-plugins.local.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (config_dir / "candidate-generation-profile.json").write_text(
                (ROOT / "config" / "candidate-generation-profile.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with tempfile.TemporaryDirectory() as job_root:
                with self.assertRaises(ExplicitVisualAssistError) as ctx:
                    run_explicit_visual_assist_auto(
                        "mg",
                        project_root=project_root,
                        job_root=Path(job_root),
                    )
        # Directory doesn't exist → clear error about missing VOP
        msg = str(ctx.exception)
        self.assertTrue("不存在" in msg or "未找到" in msg, f"Expected error about missing plan, got: {msg}")

    def test_auto_resolution_no_config_fails_closed(self):
        plan = self._make_valid_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            vop_root = project_root / ".artifacts" / "visual-opportunity"
            save_visual_opportunity_plan(plan, vop_root)
            # Don't create config/visual-asset-plugins.local.json
            (project_root / "config").mkdir(parents=True, exist_ok=True)
            (project_root / "config" / "candidate-generation-profile.json").write_text(
                (ROOT / "config" / "candidate-generation-profile.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with tempfile.TemporaryDirectory() as job_root:
                with self.assertRaises(ExplicitVisualAssistError) as ctx:
                    run_explicit_visual_assist_auto(
                        "mg",
                        project_root=project_root,
                        job_root=Path(job_root),
                    )
        self.assertIn("不存在", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
