import json
import subprocess
import sys
import unittest
from pathlib import Path

from deeptalk_studio.visual_asset_plugin_contract import (
    CONTRACT_VERSION,
    VisualAssetPluginContractError,
    validate_generation_request,
    validate_generation_result,
    validate_suitability_request,
    validate_suitability_response,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "multi_asset_synthetic"


def fixture(name):
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class VisualAssetPluginContractTests(unittest.TestCase):
    def test_accepts_only_the_frozen_contract_version_in_both_request_envelopes(self):
        self.assertEqual(CONTRACT_VERSION, "visual-asset-plugin-contract/1")
        validate_suitability_request(fixture("suitability-request.json"))
        validate_generation_request(fixture("generation-request.json"))

    def test_accepts_all_completed_suitability_outcomes(self):
        for name in (
            "suitability-completed-suitable.json",
            "suitability-completed-borderline.json",
            "suitability-completed-abstain.json",
        ):
            validate_suitability_response(fixture(name))

    def test_accepts_operational_suitability_failures_without_a_proposal(self):
        for name in ("suitability-failed.json", "suitability-unavailable.json"):
            validate_suitability_response(fixture(name))

    def test_completed_suitability_requires_the_proposal_suitability_and_reason(self):
        # Removing any completed-proposal field would let a plugin create an
        # audit record that cannot safely decide whether generation is allowed.
        bad = fixture("suitability-completed-suitable.json")
        del bad["proposal_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractError, "proposal_id"):
            validate_suitability_response(bad)

    def test_failed_suitability_cannot_smuggle_completed_proposal_fields(self):
        with self.assertRaisesRegex(VisualAssetPluginContractError, "FAILED"):
            validate_suitability_response(fixture("invalid/suitability-failed-with-proposal.json"))

    def test_accepts_completed_ready_and_qa_rejected_generation_results(self):
        opportunity = fixture("opportunity.json")
        validate_generation_result(fixture("generation-completed-ready.json"), opportunity)
        validate_generation_result(fixture("generation-completed-qa-rejected.json"), opportunity)

    def test_accepts_generation_operational_failures_without_a_candidate(self):
        opportunity = fixture("opportunity.json")
        for name in ("generation-failed.json", "generation-blocked.json", "generation-unavailable.json"):
            validate_generation_result(fixture(name), opportunity)

    def test_ready_requires_primary_media_passed_qa_and_nonempty_provenance(self):
        opportunity = fixture("opportunity.json")
        for name, expected in (
            ("invalid/ready-without-primary-media.json", "PRIMARY_MEDIA"),
            ("invalid/ready-qa-not-passed.json", "PASSED"),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(VisualAssetPluginContractError, expected):
                validate_generation_result(fixture(name), opportunity)

    def test_qa_rejected_requires_a_real_candidate_and_failed_qa(self):
        with self.assertRaisesRegex(VisualAssetPluginContractError, "FAILED"):
            validate_generation_result(
                fixture("invalid/qa-rejected-qa-not-failed.json"), fixture("opportunity.json")
            )

    def test_generation_and_candidate_statuses_are_separate_closed_enums(self):
        with self.assertRaisesRegex(VisualAssetPluginContractError, "operation_status"):
            validate_generation_result(
                fixture("invalid/abstain-generation.json"), fixture("opportunity.json")
            )
        with self.assertRaisesRegex(VisualAssetPluginContractError, "candidate_status"):
            validate_generation_result(
                fixture("invalid/invalid-enum.json"), fixture("opportunity.json")
            )

    def test_candidate_duration_need_not_equal_its_recommended_placement_duration(self):
        result = fixture("generation-completed-ready.json")
        candidate = result["candidate"]
        self.assertNotEqual(
            candidate["duration_ms"],
            candidate["suggested_placement"]["end_ms"] - candidate["suggested_placement"]["start_ms"],
        )
        validate_generation_result(result, fixture("opportunity.json"))

    def test_placement_must_be_ordered_and_contained_by_the_real_aroll_window(self):
        for name, expected in (
            ("invalid/placement-out-of-window.json", "a_roll_window"),
            ("invalid/placement-ordering.json", "suggested_placement"),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(VisualAssetPluginContractError, expected):
                validate_generation_result(fixture(name), fixture("opportunity.json"))

    def test_rejects_malformed_problem_missing_ids_versions_invalid_duration_and_duplicate_artifacts(self):
        invalid_cases = (
            ("invalid/malformed-problem.json", validate_suitability_response, None, "problem"),
            ("invalid/missing-request-id.json", validate_suitability_response, None, "request_id"),
            ("invalid/wrong-contract-version.json", validate_suitability_response, None, "contract_version"),
            ("invalid/invalid-duration.json", validate_generation_result, fixture("opportunity.json"), "duration_ms"),
            ("invalid/duplicate-artifacts.json", validate_generation_result, fixture("opportunity.json"), "重复"),
        )
        for name, validator, opportunity, expected in invalid_cases:
            with self.subTest(name=name), self.assertRaisesRegex(VisualAssetPluginContractError, expected):
                if opportunity is None:
                    validator(fixture(name))
                else:
                    validator(fixture(name), opportunity)


class SyntheticFixtureBoundaryTests(unittest.TestCase):
    def test_directive_fixture_is_clock_free_and_contains_no_v1_decision_or_asset_fields(self):
        directive = fixture("visual-opportunity-directives.json")
        self.assertEqual(directive["artifact_version"], "visual-opportunity-directives/1")
        encoded = json.dumps(directive, ensure_ascii=False)
        for forbidden in (
            "start_ms", "end_ms", "decision", "visual_kind", "asset_class",
            "KEEP_A_ROLL", "REAL_MATERIAL", "MG_MOTION", "ADVANCED_MOTION",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_fake_runner_returns_deterministic_fixture_output_without_importing_a_plugin(self):
        completed = subprocess.run(
            [sys.executable, "tests/visual_asset_plugin_fakes.py", "ready"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            text=True,
            capture_output=True,
        )
        result = json.loads(completed.stdout)
        validate_generation_result(result, fixture("opportunity.json"))


class PhaseZeroConfigExamplesTests(unittest.TestCase):
    def test_tracked_examples_are_secret_free_static_shapes_with_all_three_profiles(self):
        repo = Path(__file__).resolve().parents[1]
        plugins = json.loads((repo / "config/visual-asset-plugins.example.json").read_text(encoding="utf-8"))
        profile = json.loads((repo / "config/candidate-generation-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(plugins["config_version"], "visual-asset-plugin-config/1")
        self.assertEqual(len(plugins["plugins"]), 3)
        for plugin in plugins["plugins"]:
            self.assertEqual(
                set(plugin),
                {
                    "plugin_id", "plugin_root", "argv_prefix", "timeout_seconds",
                    "environment", "enabled", "plugin_version_command",
                    "expected_source_revision", "require_clean_worktree",
                },
            )
            self.assertFalse(plugin["enabled"])
            self.assertNotIn("token", json.dumps(plugin).lower())
        self.assertEqual(profile["profile_version"], "candidate-generation-profile/1")
        self.assertEqual(set(profile["profiles"]), {"LEAN", "STANDARD", "RICH"})


if __name__ == "__main__":
    unittest.main()
