"""Phase A tests: Contract V1 -> V2 read-only compatibility adapters.

Tests cover:
  - Generation result adapter (COMPLETED + READY / QA_REJECTED / FAILED / BLOCKED / UNAVAILABLE)
  - Suitability response adapter (SUITABLE / BORDERLINE / ABSTAIN / FAILED / UNAVAILABLE)
  - Deep-copy output isolation (modifying the output must not mutate the source)
  - Adapter never creates new IDs
"""
from __future__ import annotations

import copy
import json
import unittest

from deeptalk_studio.visual_asset_contract_compat import (
    ContractV1ToV2AdapterError,
    convert_v1_generation_result_to_v2,
    convert_v1_suitability_response_to_v2,
)
from deeptalk_studio.visual_asset_plugin_contract_v2 import (
    validate_v2_result_view,
    validate_v2_suitability_view,
)

FIXTURES = "tests/fixtures/multi_asset_synthetic"


def _opportunity() -> dict:
    with open(f"{FIXTURES}/opportunity.json", encoding="utf-8") as handle:
        return json.load(handle)


def _v1_gen(name: str) -> dict:
    with open(f"{FIXTURES}/{name}.json", encoding="utf-8") as handle:
        return json.load(handle)


def _v1_suit(name: str) -> dict:
    with open(f"{FIXTURES}/{name}.json", encoding="utf-8") as handle:
        return json.load(handle)


# ===========================================================================
# Generation Result Adapter
# ===========================================================================

class GenerationAdapterCompletedTests(unittest.TestCase):
    def test_reads_v1_ready_result_and_preserves_identity(self):
        result = _v1_gen("generation-completed-ready")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        self.assertEqual(view["contract_version"], "visual-asset-plugin-contract/2")
        self.assertEqual(view["candidate"]["candidate_id"], "cand-synthetic-01")
        self.assertEqual(view["plugin_id"], "org.example.synthetic-motion")
        self.assertEqual(view["proposal_id"], "prop-synthetic-01")
        self.assertEqual(view["request_id"], "gen-req-synthetic-01")
        self.assertEqual(view["opportunity_id"], "opp-synthetic-market-shift-01")
        self.assertEqual(
            view["candidate"]["intrinsic_placement_hint"],
            {"start_ms": 12500, "end_ms": 18500},
        )

    def test_reads_v1_ready_result_and_keeps_raw_candidate_artifacts(self):
        view = convert_v1_generation_result_to_v2(
            _v1_gen("generation-completed-ready"), _opportunity()
        )
        self.assertEqual(len(view["candidate"]["artifacts"]), 4)
        self.assertEqual(view["candidate"]["artifacts"][0]["role"], "PRIMARY_MEDIA")
        self.assertEqual(view["candidate"]["duration_ms"], 6800)
        self.assertEqual(view["candidate"]["candidate_status"], "READY")

    def test_v1_ready_result_has_no_final_placement(self):
        view = convert_v1_generation_result_to_v2(
            _v1_gen("generation-completed-ready"), _opportunity()
        )
        self.assertNotIn("final_placement", view["candidate"])

    def test_v2_view_round_trips_through_validator(self):
        view = convert_v1_generation_result_to_v2(
            _v1_gen("generation-completed-ready"), _opportunity()
        )
        validate_v2_result_view(view, _opportunity())

    def test_qa_rejected_without_hint_has_no_hint_in_v2(self):
        result = _v1_gen("generation-completed-qa-rejected")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        self.assertEqual(view["candidate"]["candidate_status"], "QA_REJECTED")
        self.assertEqual(view["candidate"]["qa"]["status"], "FAILED")
        self.assertNotIn("intrinsic_placement_hint", view["candidate"])
        validate_v2_result_view(view, _opportunity())

    def test_duration_need_not_match_placement_hint(self):
        result = _v1_gen("generation-completed-ready")
        result["candidate"]["suggested_placement"] = {"start_ms": 12000, "end_ms": 13000}
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        self.assertEqual(view["candidate"]["duration_ms"], 6800)
        self.assertEqual(
            view["candidate"]["intrinsic_placement_hint"], {"start_ms": 12000, "end_ms": 13000}
        )
        validate_v2_result_view(view, _opportunity())


class GenerationAdapterFailurePreservationTests(unittest.TestCase):
    """BLOCKER 1: FAILED / BLOCKED / UNAVAILABLE must preserve evidence."""

    def test_failed_generation_preserves_operation_status_and_problem(self):
        result = _v1_gen("generation-failed")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        self.assertEqual(view["operation_status"], "FAILED")
        self.assertEqual(view["problem"]["code"], "SYNTHETIC_GENERATION_FAILED")
        self.assertEqual(view["problem"]["message"], "合成测试生成失败。")
        self.assertTrue(view["problem"]["retryability"])
        self.assertNotIn("candidate", view)
        validate_v2_result_view(view, _opportunity())

    def test_blocked_generation_preserves_operation_status_and_problem(self):
        result = _v1_gen("generation-blocked")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        self.assertEqual(view["operation_status"], "BLOCKED")
        self.assertEqual(view["problem"]["code"], "SYNTHETIC_INPUT_BLOCKED")
        self.assertFalse(view["problem"]["retryability"])
        self.assertNotIn("candidate", view)
        validate_v2_result_view(view, _opportunity())

    def test_unavailable_generation_preserves_operation_status_and_problem(self):
        result = _v1_gen("generation-unavailable")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        self.assertEqual(view["operation_status"], "UNAVAILABLE")
        self.assertEqual(view["problem"]["code"], "SYNTHETIC_BACKEND_UNAVAILABLE")
        self.assertNotIn("candidate", view)
        validate_v2_result_view(view, _opportunity())

    def test_malformed_v1_ready_without_required_fields_fails_closed(self):
        result = _v1_gen("generation-completed-ready")
        del result["candidate"]["artifacts"]
        with self.assertRaises(ContractV1ToV2AdapterError):
            convert_v1_generation_result_to_v2(result, _opportunity())

    # --- opportunity_id lineage safety (BLOCKER) ---

    def test_adapter_rejects_opportunity_id_mismatch(self):
        """An Opportunity A result must not be converted to bind Opportunity B."""
        result = _v1_gen("generation-completed-ready")
        wrong_opportunity = _opportunity()
        wrong_opportunity["opportunity_id"] = "opp-DIFFERENT-adapter-01"
        with self.assertRaises(ContractV1ToV2AdapterError):
            convert_v1_generation_result_to_v2(result, wrong_opportunity)

    def test_adapter_rejects_failed_result_opportunity_id_mismatch(self):
        result = _v1_gen("generation-failed")
        wrong_opportunity = _opportunity()
        wrong_opportunity["opportunity_id"] = "opp-DIFFERENT-adapter-02"
        with self.assertRaises(ContractV1ToV2AdapterError):
            convert_v1_generation_result_to_v2(result, wrong_opportunity)


class GenerationAdapterIsolationTests(unittest.TestCase):
    """BLOCKER 4: deep-copy — modifying output must not mutate source."""

    def test_adapter_does_not_mutate_input(self):
        result = _v1_gen("generation-completed-ready")
        before = json.dumps(result, ensure_ascii=False, sort_keys=True)
        convert_v1_generation_result_to_v2(result, _opportunity())
        after = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_modifying_output_does_not_mutate_source(self):
        result = _v1_gen("generation-completed-ready")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        before = json.dumps(result, ensure_ascii=False, sort_keys=True)
        # Mutate the output deeply.
        view["candidate"]["artifacts"][0]["uri"] = "changed"
        view["candidate"]["qa"]["status"] = "changed"
        view["candidate"]["provenance"]["x"] = "changed"
        after = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_modifying_failure_output_does_not_mutate_source(self):
        result = _v1_gen("generation-failed")
        view = convert_v1_generation_result_to_v2(result, _opportunity())
        before = json.dumps(result, ensure_ascii=False, sort_keys=True)
        view["problem"]["code"] = "changed"
        after = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)


# ===========================================================================
# Suitability Response Adapter
# ===========================================================================

class SuitabilityAdapterTests(unittest.TestCase):
    """BLOCKER 2: Suitability V1 -> V2 compatibility."""

    def test_suitable_preserves_proposal_id_and_reason(self):
        view = convert_v1_suitability_response_to_v2(_v1_suit("suitability-completed-suitable"))
        self.assertEqual(view["contract_version"], "visual-asset-plugin-contract/2")
        self.assertEqual(view["operation_status"], "COMPLETED")
        self.assertEqual(view["suitability"], "SUITABLE")
        self.assertEqual(view["proposal_id"], "prop-synthetic-01")
        self.assertEqual(view["reason"], "虚构变化链适合由结构动画解释。")
        validate_v2_suitability_view(view)

    def test_borderline_preserves_proposal_id_and_reason(self):
        view = convert_v1_suitability_response_to_v2(_v1_suit("suitability-completed-borderline"))
        self.assertEqual(view["suitability"], "BORDERLINE")
        self.assertEqual(view["proposal_id"], "prop-synthetic-02")
        validate_v2_suitability_view(view)

    def test_abstain_preserves_proposal_id_and_reason(self):
        view = convert_v1_suitability_response_to_v2(_v1_suit("suitability-completed-abstain"))
        self.assertEqual(view["suitability"], "ABSTAIN")
        self.assertEqual(view["proposal_id"], "prop-synthetic-03")
        self.assertEqual(view["reason"], "此虚构变化不适合这个手绘家族。")
        validate_v2_suitability_view(view)

    def test_failed_suitability_preserves_operation_status_and_problem(self):
        view = convert_v1_suitability_response_to_v2(_v1_suit("suitability-failed"))
        self.assertEqual(view["operation_status"], "FAILED")
        self.assertEqual(view["problem"]["code"], "SYNTHETIC_RENDERER_ERROR")
        self.assertNotIn("proposal_id", view)
        self.assertNotIn("suitability", view)
        validate_v2_suitability_view(view)

    def test_unavailable_suitability_preserves_operation_status_and_problem(self):
        view = convert_v1_suitability_response_to_v2(_v1_suit("suitability-unavailable"))
        self.assertEqual(view["operation_status"], "UNAVAILABLE")
        self.assertEqual(view["problem"]["code"], "SYNTHETIC_DEPENDENCY_MISSING")
        self.assertNotIn("proposal_id", view)
        validate_v2_suitability_view(view)


class SuitabilityAdapterIsolationTests(unittest.TestCase):
    def test_suitability_adapter_does_not_mutate_input(self):
        result = _v1_suit("suitability-completed-suitable")
        before = json.dumps(result, ensure_ascii=False, sort_keys=True)
        convert_v1_suitability_response_to_v2(result)
        after = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_modifying_suitability_output_does_not_mutate_source(self):
        result = _v1_suit("suitability-completed-suitable")
        view = convert_v1_suitability_response_to_v2(result)
        before = json.dumps(result, ensure_ascii=False, sort_keys=True)
        view["reason"] = "changed"
        view["proposal_id"] = "changed"
        after = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()