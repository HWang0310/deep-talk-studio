import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.validation import ReportValidationError, validate_report
from tests.fixtures import valid_report_data


class ValidationTests(unittest.TestCase):
    def test_valid_report_passes_complete_schema_and_business_rules(self):
        report = ResearchReport.from_dict(valid_report_data())
        validate_report(report)

    def test_missing_nested_required_field_is_report_validation_error(self):
        data = valid_report_data()
        del data["sources"][0]["publisher"]

        with self.assertRaisesRegex(ReportValidationError, r"sources\[0\]\.publisher"):
            ResearchReport.from_dict(data)

    def test_unknown_nested_field_is_rejected(self):
        data = valid_report_data()
        data["sources"][0]["invented"] = "不应接受"

        with self.assertRaisesRegex(ReportValidationError, r"sources\[0\]\.invented"):
            ResearchReport.from_dict(data)

    def test_wrong_nested_enum_is_rejected(self):
        data = valid_report_data()
        data["perspectives"][0]["category"] = "influencer"

        with self.assertRaisesRegex(ReportValidationError, "category"):
            ResearchReport.from_dict(data)

    def test_wrong_nested_type_is_rejected(self):
        data = valid_report_data()
        data["quality_summary"]["claim_count"] = "3"

        with self.assertRaisesRegex(ReportValidationError, "claim_count"):
            ResearchReport.from_dict(data)

    def test_malformed_source_url_is_rejected_without_key_error(self):
        data = valid_report_data()
        data["sources"][0]["url"] = "javascript:alert(1)"

        with self.assertRaisesRegex(ReportValidationError, "HTTP"):
            ResearchReport.from_dict(data)

    def test_invalid_evidence_relation_is_rejected(self):
        data = valid_report_data()
        data["evidence_links"][0]["relation"] = "copies"

        with self.assertRaisesRegex(ReportValidationError, "relation"):
            ResearchReport.from_dict(data)

    def test_unknown_evidence_claim_reference_is_rejected(self):
        data = valid_report_data()
        data["evidence_links"][0]["claim_id"] = "C404"

        with self.assertRaisesRegex(ReportValidationError, "C404"):
            ResearchReport.from_dict(data)

    def test_unknown_evidence_source_reference_is_rejected(self):
        data = valid_report_data()
        data["evidence_links"][0]["source_id"] = "S404"

        with self.assertRaisesRegex(ReportValidationError, "S404"):
            ResearchReport.from_dict(data)

    def test_evidence_independence_group_must_match_source(self):
        data = valid_report_data()
        data["evidence_links"][0]["independence_group"] = "IG404"

        with self.assertRaisesRegex(ReportValidationError, "independence_group"):
            ResearchReport.from_dict(data)

    def test_confirmed_fact_requires_supporting_evidence(self):
        data = valid_report_data()
        data["evidence_links"][0]["relation"] = "context"
        data["evidence_links"][1]["relation"] = "context"

        with self.assertRaisesRegex(ReportValidationError, "confirmed_fact C1"):
            ResearchReport.from_dict(data)

    def test_reviewed_report_requires_passing_quality_gate(self):
        data = valid_report_data()
        data["quality_summary"]["gate_status"] = "fail"
        data["quality_summary"]["gate_reasons"] = ["来源不足"]

        with self.assertRaisesRegex(ReportValidationError, "reviewed"):
            ResearchReport.from_dict(data)

    def test_approval_gate_must_expose_every_high_risk_claim(self):
        data = valid_report_data()
        data["approval_gate"]["high_risk_claim_ids"] = []

        with self.assertRaisesRegex(ReportValidationError, "高风险"):
            ResearchReport.from_dict(data)

    def test_ready_for_script_requires_nonempty_user_confirmation(self):
        data = valid_report_data()
        data["status"] = "ready_for_script"
        data["approval_gate"].update(status="approved", ready_for_script=True)

        with self.assertRaisesRegex(ReportValidationError, "用户确认"):
            ResearchReport.from_dict(data)

    def test_approved_gate_cannot_disagree_with_report_ready_status(self):
        data = valid_report_data()
        data["approval_gate"].update(
            status="approved",
            user_confirmation="我已确认",
            ready_for_script=False,
        )

        with self.assertRaisesRegex(ReportValidationError, "approved"):
            ResearchReport.from_dict(data)

    def test_user_confirmation_gate_cannot_be_disabled(self):
        data = valid_report_data()
        data["approval_gate"]["requires_user_confirmation"] = False

        with self.assertRaisesRegex(ReportValidationError, "用户确认"):
            ResearchReport.from_dict(data)

    def test_declared_quality_metrics_must_match_evidence(self):
        data = valid_report_data()
        data["quality_summary"]["claim_count"] = 4

        with self.assertRaisesRegex(ReportValidationError, "quality_summary"):
            ResearchReport.from_dict(data)

    def test_unknown_timeline_evidence_reference_is_rejected(self):
        data = valid_report_data()
        data["timeline"][0]["evidence_link_ids"] = ["E404"]

        with self.assertRaisesRegex(ReportValidationError, "E404"):
            ResearchReport.from_dict(data)

    def test_non_object_report_uses_domain_error(self):
        with self.assertRaisesRegex(ReportValidationError, "JSON 对象"):
            ResearchReport.from_dict([])


if __name__ == "__main__":
    unittest.main()
