import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.quality import (
    apply_quality_gate,
    approve_for_script,
    calculate_quality_summary,
)
from deeptalk_studio.validation import ReportValidationError
from tests.fixtures import valid_report_data


class QualityTests(unittest.TestCase):
    def test_quality_metrics_are_derived_from_evidence_not_declared_score(self):
        summary = calculate_quality_summary(valid_report_data())

        self.assertEqual(summary["claim_count"], 3)
        self.assertEqual(summary["sourced_claim_count"], 3)
        self.assertEqual(summary["claim_source_coverage"], 1.0)
        self.assertEqual(summary["high_risk_fact_check_coverage"], 1.0)
        self.assertEqual(summary["confirmed_fact_independent_coverage"], 1.0)
        self.assertEqual(summary["source_type_diversity_count"], 2)
        self.assertEqual(summary["unresolved_high_risk_count"], 0)
        self.assertEqual(summary["unsourced_attribution_count"], 0)
        self.assertEqual(summary["gate_status"], "pass")

    def test_duplicate_groups_do_not_count_as_independent_confirmation(self):
        data = valid_report_data()
        data["sources"][1]["independence_group"] = "IG1"
        data["sources"][1]["independence_status"] = "duplicate"
        data["sources"][1]["syndication_of"] = "S1"
        data["evidence_links"][1]["independence_group"] = "IG1"

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["confirmed_fact_independent_count"], 0)
        self.assertEqual(summary["duplicate_source_count"], 1)
        self.assertEqual(summary["gate_status"], "fail")

    def test_unchecked_high_risk_claim_blocks_reviewed_status(self):
        data = valid_report_data()
        data["claims"][0]["verification_status"] = "not_checked"
        data["fact_check"]["checked_claim_ids"] = []
        data["fact_check"]["status"] = "not_run"
        data["status"] = "draft"

        gated = apply_quality_gate(data)

        self.assertEqual(gated["quality_summary"]["high_risk_fact_check_coverage"], 0.0)
        self.assertEqual(gated["quality_summary"]["unresolved_high_risk_count"], 1)
        self.assertEqual(gated["quality_summary"]["gate_status"], "fail")
        self.assertEqual(gated["status"], "draft")

    def test_party_statement_without_attribution_is_counted(self):
        data = valid_report_data()
        data["evidence_links"] = [
            link for link in data["evidence_links"] if link["claim_id"] != "C2"
        ]

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["unsourced_attribution_count"], 1)
        self.assertEqual(summary["gate_status"], "fail")

    def test_user_approval_is_required_before_ready_for_script(self):
        report = ResearchReport.from_dict(valid_report_data())

        ready = approve_for_script(report, "我已查看高风险主张并确认继续")

        self.assertEqual(ready["status"], "ready_for_script")
        self.assertEqual(ready["approval_gate"]["status"], "approved")
        self.assertTrue(ready["approval_gate"]["ready_for_script"])
        self.assertEqual(ready["approval_gate"]["high_risk_claim_ids"], ["C1"])

    def test_empty_user_confirmation_is_rejected(self):
        report = ResearchReport.from_dict(valid_report_data())

        with self.assertRaisesRegex(ReportValidationError, "确认"):
            approve_for_script(report, "  ")


if __name__ == "__main__":
    unittest.main()
