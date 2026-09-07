"""Phase A tests: isolated Visual Asset Plugin Contract V2 result view.

This is a design-only, additive compatibility surface for V2.  It is **not**
a production protocol and does not change the frozen
``visual-asset-plugin-contract/1`` runtime path.
"""
from __future__ import annotations

import unittest

from deeptalk_studio.visual_asset_plugin_contract_v2 import (
    CONTRACT_VERSION_V2,
    VisualAssetPluginContractV2Error,
    validate_v2_result_view,
)


def _opportunity() -> dict:
    return {
        "opportunity_id": "opp-synthetic-market-shift-01",
        "spoken_semantics": "一个虚构市场指标从稳定转向收缩，解释变化的因果链。",
        "visual_purpose": "用短结构动画帮助观众看清变化顺序。",
        "a_roll_window": {"start_ms": 12000, "end_ms": 19000},
        "target_duration_ms": 6000,
        "language": "zh-CN",
        "canvas": {"width": 1920, "height": 1080},
    }


def _ready_result() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "gen-req-synthetic-01",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "proposal_id": "prop-synthetic-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "operation_status": "COMPLETED",
        "candidate": {
            "candidate_id": "cand-synthetic-01",
            "asset_family": "SYNTHETIC_MOTION",
            "candidate_status": "READY",
            "duration_ms": 6800,
            "intrinsic_placement_hint": {"start_ms": 12500, "end_ms": 18500},
            "artifacts": [
                {
                    "role": "PRIMARY_MEDIA",
                    "uri": "synthetic://candidate-01/media.mp4",
                    "media_type": "video/mp4",
                    "duration_ms": 6800,
                },
                {
                    "role": "QA_REPORT",
                    "uri": "synthetic://candidate-01/qa.json",
                    "media_type": "application/json",
                },
            ],
            "qa": {"status": "PASSED", "summary": "合成机械检查通过。"},
            "provenance": {"origin": "plugin-generated", "source_ref": "synthetic manifest v1"},
        },
    }


def _rejected_result() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "gen-req-synthetic-02",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "proposal_id": "prop-synthetic-02",
        "plugin_id": "org.example.synthetic-metaphor",
        "plugin_version": "0.0.0-test",
        "operation_status": "COMPLETED",
        "candidate": {
            "candidate_id": "cand-synthetic-02",
            "asset_family": "SYNTHETIC_METAPHOR",
            "candidate_status": "QA_REJECTED",
            "qa": {"status": "FAILED", "summary": "合成可读性检查未通过。"},
            "artifacts": [
                {
                    "role": "QA_REPORT",
                    "uri": "synthetic://candidate-02/qa.json",
                    "media_type": "application/json",
                }
            ],
        },
    }


class V2ContractVersionTests(unittest.TestCase):
    def test_v2_version_is_a_distinct_contract_string(self):
        self.assertEqual(CONTRACT_VERSION_V2, "visual-asset-plugin-contract/2")
        self.assertNotEqual(CONTRACT_VERSION_V2, "visual-asset-plugin-contract/1")


class V2ResultViewTests(unittest.TestCase):
    def test_ready_candidate_may_omit_intrinsic_placement_hint(self):
        result = _ready_result()
        del result["candidate"]["intrinsic_placement_hint"]
        validate_v2_result_view(result, _opportunity())

    def test_ready_candidate_with_placement_hint_is_valid(self):
        validate_v2_result_view(_ready_result(), _opportunity())

    def test_ready_requires_duration_primary_media_passed_qa_and_provenance(self):
        result = _ready_result()
        del result["candidate"]["duration_ms"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "duration_ms"):
            validate_v2_result_view(result, _opportunity())

        result = _ready_result()
        result["candidate"]["artifacts"] = [
            a for a in result["candidate"]["artifacts"] if a["role"] != "PRIMARY_MEDIA"
        ]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "PRIMARY_MEDIA"):
            validate_v2_result_view(result, _opportunity())

        result = _ready_result()
        result["candidate"]["qa"]["status"] = "FAILED"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "PASSED"):
            validate_v2_result_view(result, _opportunity())

        result = _ready_result()
        del result["candidate"]["provenance"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "provenance"):
            validate_v2_result_view(result, _opportunity())

    def test_qa_rejected_requires_failed_qa(self):
        result = _rejected_result()
        result["candidate"]["qa"]["status"] = "PASSED"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "FAILED"):
            validate_v2_result_view(result, _opportunity())

    def test_duration_need_not_equal_placement_hint_duration(self):
        result = _ready_result()
        hint = result["candidate"]["intrinsic_placement_hint"]
        self.assertNotEqual(result["candidate"]["duration_ms"], hint["end_ms"] - hint["start_ms"])
        validate_v2_result_view(result, _opportunity())

    def test_rejects_unknown_fields(self):
        result = _ready_result()
        result["candidate"]["unknown_field"] = True
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "unknown_field"):
            validate_v2_result_view(result, _opportunity())

    def test_rejects_invalid_status_and_out_of_window_hint(self):
        result = _ready_result()
        result["candidate"]["candidate_status"] = "PENDING"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "candidate_status"):
            validate_v2_result_view(result, _opportunity())

        result = _ready_result()
        result["candidate"]["intrinsic_placement_hint"] = {"start_ms": 11000, "end_ms": 18500}
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "a_roll_window"):
            validate_v2_result_view(result, _opportunity())

    def test_rejects_failure_statuses(self):
        result = _ready_result()
        result["operation_status"] = "FAILED"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "COMPLETED"):
            validate_v2_result_view(result, _opportunity())

    def test_rejects_wrong_contract_version(self):
        result = _ready_result()
        result["contract_version"] = "visual-asset-plugin-contract/1"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "contract_version"):
            validate_v2_result_view(result, _opportunity())


if __name__ == "__main__":
    unittest.main()