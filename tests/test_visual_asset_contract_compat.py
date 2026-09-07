"""Phase A tests: Contract V1 -> V2 read-only compatibility adapter.

The adapter must not mutate inputs, must not create new IDs, and must never
reinterpret a failed/abstained plugin outcome into a production-ready V2
result view.
"""
from __future__ import annotations

import copy
import json
import unittest

from deeptalk_studio.visual_asset_contract_compat import (
    ContractV1ToV2Adapter,
    ContractV1ToV2AdapterError,
    convert_v1_generation_result_to_v2_candidate,
)
from deeptalk_studio.visual_asset_plugin_contract_v2 import (
    validate_v2_result_view,
)

FIXTURES = "tests/fixtures/multi_asset_synthetic"


def _opportunity() -> dict:
    with open(f"{FIXTURES}/opportunity.json", encoding="utf-8") as handle:
        return json.load(handle)


def _v1_result(name: str) -> dict:
    with open(f"{FIXTURES}/{name}.json", encoding="utf-8") as handle:
        return json.load(handle)


class ContractV1ToV2AdapterTests(unittest.TestCase):
    def test_reads_v1_ready_result_and_preserves_identity(self):
        result = _v1_result("generation-completed-ready")
        view = convert_v1_generation_result_to_v2_candidate(result, _opportunity())
        self.assertEqual(view["contract_version"], "visual-asset-plugin-contract/2")
        self.assertEqual(view["candidate"]["candidate_id"], "cand-synthetic-01")
        self.assertEqual(view["plugin_id"], "org.example.synthetic-motion")
        self.assertEqual(view["proposal_id"], "prop-synthetic-01")
        self.assertEqual(view["request_id"], "gen-req-synthetic-01")
        self.assertEqual(view["opportunity_id"], "opp-synthetic-market-shift-01")
        # placement hint is plugin-owned, not a final recommendation.
        self.assertEqual(
            view["candidate"]["intrinsic_placement_hint"],
            {"start_ms": 12500, "end_ms": 18500},
        )

    def test_reads_v1_ready_result_and_keeps_raw_candidate_artifacts(self):
        view = convert_v1_generation_result_to_v2_candidate(
            _v1_result("generation-completed-ready"), _opportunity()
        )
        self.assertEqual(len(view["candidate"]["artifacts"]), 4)
        self.assertEqual(view["candidate"]["artifacts"][0]["role"], "PRIMARY_MEDIA")
        self.assertEqual(view["candidate"]["duration_ms"], 6800)
        self.assertEqual(view["candidate"]["candidate_status"], "READY")

    def test_v1_ready_result_has_no_final_placement(self):
        view = convert_v1_generation_result_to_v2_candidate(
            _v1_result("generation-completed-ready"), _opportunity()
        )
        self.assertNotIn("final_placement", view["candidate"])

    def test_v2_view_round_trips_through_validator(self):
        view = convert_v1_generation_result_to_v2_candidate(
            _v1_result("generation-completed-ready"), _opportunity()
        )
        validate_v2_result_view(view, _opportunity())

    def test_qa_rejected_without_hint_has_no_hint_in_v2(self):
        result = _v1_result("generation-completed-qa-rejected")
        view = convert_v1_generation_result_to_v2_candidate(result, _opportunity())
        self.assertEqual(view["candidate"]["candidate_status"], "QA_REJECTED")
        self.assertEqual(view["candidate"]["qa"]["status"], "FAILED")
        self.assertNotIn("intrinsic_placement_hint", view["candidate"])
        validate_v2_result_view(view, _opportunity())

    def test_failed_generation_does_not_produce_candidate(self):
        with self.assertRaisesRegex(ContractV1ToV2AdapterError, "no_candidate"):
            convert_v1_generation_result_to_v2_candidate(
                _v1_result("generation-failed"), _opportunity()
            )

    def test_blocked_generation_does_not_produce_candidate(self):
        with self.assertRaisesRegex(ContractV1ToV2AdapterError, "no_candidate"):
            convert_v1_generation_result_to_v2_candidate(
                _v1_result("generation-blocked"), _opportunity()
            )

    def test_unavailable_generation_does_not_produce_candidate(self):
        with self.assertRaisesRegex(ContractV1ToV2AdapterError, "no_candidate"):
            convert_v1_generation_result_to_v2_candidate(
                _v1_result("generation-unavailable"), _opportunity()
            )

    def test_adapter_is_read_only_and_never_mutates_input(self):
        result = _v1_result("generation-completed-ready")
        before = json.dumps(result, ensure_ascii=False, sort_keys=True)
        convert_v1_generation_result_to_v2_candidate(result, _opportunity())
        after = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_duration_need_not_match_placement_hint(self):
        result = _v1_result("generation-completed-ready")
        result["candidate"]["suggested_placement"] = {"start_ms": 12000, "end_ms": 13000}
        view = convert_v1_generation_result_to_v2_candidate(result, _opportunity())
        self.assertEqual(view["candidate"]["duration_ms"], 6800)
        self.assertEqual(
            view["candidate"]["intrinsic_placement_hint"], {"start_ms": 12000, "end_ms": 13000}
        )
        validate_v2_result_view(view, _opportunity())

    def test_malformed_v1_ready_without_required_fields_fails_closed(self):
        result = _v1_result("generation-completed-ready")
        del result["candidate"]["artifacts"]
        with self.assertRaises(ContractV1ToV2AdapterError):
            convert_v1_generation_result_to_v2_candidate(result, _opportunity())


class ContractV1ToV2AdapterFunctionalTests(unittest.TestCase):
    def test_adapter_is_exposed_as_a_callable_instance(self):
        self.assertTrue(callable(ContractV1ToV2Adapter))
        view = ContractV1ToV2Adapter(
            _v1_result("generation-completed-ready"), _opportunity()
        )()
        self.assertEqual(view["contract_version"], "visual-asset-plugin-contract/2")


if __name__ == "__main__":
    unittest.main()