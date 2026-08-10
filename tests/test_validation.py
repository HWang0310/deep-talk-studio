import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.validation import ReportValidationError, validate_report
from tests.fixtures import valid_report_data


class ValidationTests(unittest.TestCase):
    def test_valid_report_passes(self):
        report = ResearchReport.from_dict(valid_report_data())
        validate_report(report)

    def test_unknown_source_reference_is_rejected(self):
        data = valid_report_data()
        data["claims"][0]["source_ids"] = ["S404"]
        report = ResearchReport.from_dict(data)

        with self.assertRaisesRegex(ReportValidationError, "S404"):
            validate_report(report)

    def test_confirmed_fact_without_source_is_rejected(self):
        data = valid_report_data()
        data["claims"][0]["source_ids"] = []
        report = ResearchReport.from_dict(data)

        with self.assertRaisesRegex(ReportValidationError, "confirmed_fact"):
            validate_report(report)

    def test_non_http_source_url_is_rejected(self):
        data = valid_report_data()
        data["sources"][0]["url"] = "javascript:alert(1)"
        report = ResearchReport.from_dict(data)

        with self.assertRaisesRegex(ReportValidationError, "HTTP"):
            validate_report(report)

    def test_unknown_claim_reference_is_rejected(self):
        data = valid_report_data()
        data["angles"][0]["required_claim_ids"] = ["C404"]
        report = ResearchReport.from_dict(data)

        with self.assertRaisesRegex(ReportValidationError, "C404"):
            validate_report(report)


if __name__ == "__main__":
    unittest.main()

