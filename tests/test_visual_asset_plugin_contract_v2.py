"""Phase A tests: isolated Visual Asset Plugin Contract V2 compatibility views.

This is a design-only, additive compatibility surface for V2.  It is **not**
a production protocol and does not change the frozen
``visual-asset-plugin-contract/1`` runtime path.

Two compatibility surfaces exist in Phase A:
  - ``validate_v2_result_view``      — generation result envelope
  - ``validate_v2_suitability_view`` — suitability response envelope

Both accept COMPLETED and failure (FAILED / BLOCKED / UNAVAILABLE) statuses,
preserving raw V1 evidence without loss.
"""
from __future__ import annotations

import unittest

from deeptalk_studio.visual_asset_plugin_contract_v2 import (
    CONTRACT_VERSION_V2,
    VisualAssetPluginContractV2Error,
    validate_v2_result_view,
    validate_v2_suitability_view,
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


def _failed_result() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "gen-req-synthetic-03",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "proposal_id": "prop-synthetic-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "operation_status": "FAILED",
        "problem": {
            "code": "SYNTHETIC_GENERATION_FAILED",
            "message": "合成测试生成失败。",
            "retryability": True,
        },
    }


def _blocked_result() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "gen-req-synthetic-04",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "proposal_id": "prop-synthetic-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "operation_status": "BLOCKED",
        "problem": {
            "code": "SYNTHETIC_INPUT_BLOCKED",
            "message": "合成测试输入被阻止。",
            "retryability": False,
        },
    }


def _unavailable_result() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "gen-req-synthetic-05",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "proposal_id": "prop-synthetic-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "operation_status": "UNAVAILABLE",
        "problem": {
            "code": "SYNTHETIC_BACKEND_UNAVAILABLE",
            "message": "合成测试后端不可用。",
            "retryability": True,
        },
    }


# ---------------------------------------------------------------------------
# Suitability fixtures
# ---------------------------------------------------------------------------

def _suitable_suitability() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "suit-req-synthetic-01",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "proposal_id": "prop-synthetic-01",
        "operation_status": "COMPLETED",
        "suitability": "SUITABLE",
        "reason": "虚构变化链适合由结构动画解释。",
    }


def _borderline_suitability() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "suit-req-synthetic-02",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "plugin_id": "org.example.synthetic-metaphor",
        "plugin_version": "0.0.0-test",
        "proposal_id": "prop-synthetic-02",
        "operation_status": "COMPLETED",
        "suitability": "BORDERLINE",
        "reason": "可表现压力变化，但无法精确表达虚构指标。",
    }


def _abstain_suitability() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "suit-req-synthetic-03",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "plugin_id": "org.example.synthetic-handdrawn",
        "plugin_version": "0.0.0-test",
        "proposal_id": "prop-synthetic-03",
        "operation_status": "COMPLETED",
        "suitability": "ABSTAIN",
        "reason": "此虚构变化不适合这个手绘家族。",
    }


def _failed_suitability() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "suit-req-synthetic-04",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "operation_status": "FAILED",
        "problem": {
            "code": "SYNTHETIC_RENDERER_ERROR",
            "message": "合成测试中的插件判断失败。",
            "retryability": True,
        },
    }


def _unavailable_suitability() -> dict:
    return {
        "contract_version": "visual-asset-plugin-contract/2",
        "request_id": "suit-req-synthetic-05",
        "opportunity_id": "opp-synthetic-market-shift-01",
        "plugin_id": "org.example.synthetic-motion",
        "plugin_version": "0.0.0-test",
        "operation_status": "UNAVAILABLE",
        "problem": {
            "code": "SYNTHETIC_DEPENDENCY_MISSING",
            "message": "合成测试中的插件依赖不可用。",
            "retryability": False,
        },
    }


# ---------------------------------------------------------------------------
# Contract version
# ---------------------------------------------------------------------------

class V2ContractVersionTests(unittest.TestCase):
    def test_v2_version_is_a_distinct_contract_string(self):
        self.assertEqual(CONTRACT_VERSION_V2, "visual-asset-plugin-contract/2")
        self.assertNotEqual(CONTRACT_VERSION_V2, "visual-asset-plugin-contract/1")


# ---------------------------------------------------------------------------
# Generation result view
# ---------------------------------------------------------------------------

class V2ResultViewTests(unittest.TestCase):
    # --- COMPLETED with candidate ---

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

    # --- Failure statuses preserve evidence ---

    def test_failed_result_view_is_valid_with_problem(self):
        validate_v2_result_view(_failed_result(), _opportunity())

    def test_blocked_result_view_is_valid_with_problem(self):
        validate_v2_result_view(_blocked_result(), _opportunity())

    def test_unavailable_result_view_is_valid_with_problem(self):
        validate_v2_result_view(_unavailable_result(), _opportunity())

    def test_failed_result_must_not_have_candidate(self):
        result = _failed_result()
        result["candidate"] = {"candidate_id": "fake"}
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "candidate"):
            validate_v2_result_view(result, _opportunity())

    def test_failed_result_must_have_problem(self):
        result = _failed_result()
        del result["problem"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "problem"):
            validate_v2_result_view(result, _opportunity())

    # --- Required lineage IDs ---

    def test_missing_request_id_rejected(self):
        result = _ready_result()
        del result["request_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "request_id"):
            validate_v2_result_view(result, _opportunity())

    def test_missing_opportunity_id_rejected(self):
        result = _ready_result()
        del result["opportunity_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "opportunity_id"):
            validate_v2_result_view(result, _opportunity())

    def test_missing_proposal_id_rejected(self):
        result = _ready_result()
        del result["proposal_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "proposal_id"):
            validate_v2_result_view(result, _opportunity())

    def test_missing_plugin_id_rejected(self):
        result = _ready_result()
        del result["plugin_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "plugin_id"):
            validate_v2_result_view(result, _opportunity())

    def test_missing_plugin_version_rejected(self):
        result = _ready_result()
        del result["plugin_version"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "plugin_version"):
            validate_v2_result_view(result, _opportunity())

    def test_rejects_wrong_contract_version(self):
        result = _ready_result()
        result["contract_version"] = "visual-asset-plugin-contract/1"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "contract_version"):
            validate_v2_result_view(result, _opportunity())


# ---------------------------------------------------------------------------
# Suitability view
# ---------------------------------------------------------------------------

class V2SuitabilityViewTests(unittest.TestCase):
    def test_suitable_is_valid(self):
        validate_v2_suitability_view(_suitable_suitability())

    def test_borderline_is_valid(self):
        validate_v2_suitability_view(_borderline_suitability())

    def test_abstain_is_valid(self):
        validate_v2_suitability_view(_abstain_suitability())

    def test_abstain_preserves_proposal_id_and_reason(self):
        view = _abstain_suitability()
        validate_v2_suitability_view(view)
        self.assertEqual(view["suitability"], "ABSTAIN")
        self.assertEqual(view["proposal_id"], "prop-synthetic-03")
        self.assertIn("reason", view)

    def test_failed_suitability_is_valid(self):
        validate_v2_suitability_view(_failed_suitability())

    def test_unavailable_suitability_is_valid(self):
        validate_v2_suitability_view(_unavailable_suitability())

    def test_failed_suitability_must_not_have_proposal_id(self):
        view = _failed_suitability()
        view["proposal_id"] = "fake-prop"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "proposal_id"):
            validate_v2_suitability_view(view)

    def test_failed_suitability_must_have_problem(self):
        view = _failed_suitability()
        del view["problem"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "problem"):
            validate_v2_suitability_view(view)

    def test_missing_request_id_rejected(self):
        view = _suitable_suitability()
        del view["request_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "request_id"):
            validate_v2_suitability_view(view)

    def test_missing_opportunity_id_rejected(self):
        view = _suitable_suitability()
        del view["opportunity_id"]
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "opportunity_id"):
            validate_v2_suitability_view(view)

    def test_rejects_wrong_contract_version(self):
        view = _suitable_suitability()
        view["contract_version"] = "visual-asset-plugin-contract/1"
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "contract_version"):
            validate_v2_suitability_view(view)

    def test_rejects_unknown_fields(self):
        view = _suitable_suitability()
        view["unknown_field"] = True
        with self.assertRaisesRegex(VisualAssetPluginContractV2Error, "unknown_field"):
            validate_v2_suitability_view(view)


if __name__ == "__main__":
    unittest.main()