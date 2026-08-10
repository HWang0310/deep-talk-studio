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

    def test_unknown_sources_in_different_groups_do_not_count_as_independent(self):
        data = valid_report_data()
        for source in data["sources"]:
            source["independence_status"] = "unknown"

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["confirmed_fact_independent_count"], 0)
        self.assertEqual(summary["confirmed_fact_independent_coverage"], 0.0)
        self.assertEqual(summary["gate_status"], "fail")

    def test_one_independent_and_one_unknown_source_are_not_two_confirmations(self):
        data = valid_report_data()
        data["sources"][1]["independence_status"] = "unknown"

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["confirmed_fact_independent_count"], 0)
        self.assertEqual(summary["gate_status"], "fail")

    def test_two_matched_independent_groups_satisfy_confirmation_gate(self):
        summary = calculate_quality_summary(valid_report_data())

        self.assertEqual(summary["confirmed_fact_independent_count"], 1)
        self.assertEqual(summary["confirmed_fact_independent_coverage"], 1.0)
        self.assertEqual(summary["gate_status"], "pass")

    def test_non_independent_status_never_adds_confirmation_even_with_new_group(self):
        for status in ("related", "syndicated", "duplicate"):
            with self.subTest(status=status):
                data = valid_report_data()
                data["sources"][1]["independence_status"] = status
                data["sources"][1]["independence_group"] = "IG-separate"
                data["evidence_links"][1]["independence_group"] = "IG-separate"

                summary = calculate_quality_summary(data)

                self.assertEqual(summary["confirmed_fact_independent_count"], 0)
                self.assertEqual(summary["gate_status"], "fail")

    def test_context_only_link_does_not_count_as_claim_source_coverage(self):
        data = valid_report_data()
        data["evidence_links"][3]["relation"] = "context"

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["sourced_claim_count"], 2)
        self.assertEqual(summary["claim_source_coverage"], 0.6667)
        self.assertEqual(summary["gate_status"], "fail")

    def test_unmatched_attribute_does_not_clear_unsourced_attribution(self):
        data = valid_report_data()
        data["sources"][0]["provenance_status"] = "unmatched"
        data["sources"][0]["provenance_refs"] = []

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["unsourced_attribution_count"], 1)

    def test_duplicate_or_syndicated_records_do_not_inflate_source_type_diversity(self):
        data = valid_report_data()
        for source in data["sources"]:
            source["source_type"] = "official"
        copied = dict(data["sources"][0])
        copied.update(
            id="S3",
            source_type="academic",
            independence_status="duplicate",
            syndication_of="S1",
        )
        data["sources"].append(copied)

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["source_type_diversity_count"], 1)

    def test_duplicate_records_do_not_inflate_provenance_match_rate(self):
        data = valid_report_data()
        data["sources"][1]["provenance_status"] = "unmatched"
        data["sources"][1]["provenance_refs"] = []
        for index in range(3, 7):
            copied = dict(data["sources"][0])
            copied.update(
                id=f"S{index}",
                independence_status="duplicate",
                syndication_of="S1",
            )
            data["sources"].append(copied)

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["provenance_matched_source_count"], 1)
        self.assertEqual(summary["provenance_match_rate"], 0.5)
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

    def test_model_declared_check_without_reviewed_evidence_does_not_count(self):
        data = valid_report_data()
        for link in data["evidence_links"]:
            if link["claim_id"] == "C1":
                link["verified_in_review"] = False

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["high_risk_checked_count"], 0)
        self.assertEqual(summary["high_risk_fact_check_coverage"], 0.0)
        self.assertEqual(summary["gate_status"], "fail")

    def test_partially_verified_review_still_counts_coverage_but_stays_unresolved(self):
        data = valid_report_data()
        data["claims"][0]["verification_status"] = "partially_verified"
        data["fact_check"]["status"] = "needs_follow_up"
        data["fact_check"]["unresolved_claim_ids"] = ["C1"]

        summary = calculate_quality_summary(data)

        self.assertEqual(summary["high_risk_fact_check_coverage"], 1.0)
        self.assertEqual(summary["unresolved_high_risk_count"], 1)
        self.assertEqual(summary["gate_status"], "fail")

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
