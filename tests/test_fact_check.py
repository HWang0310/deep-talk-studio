import unittest

from deeptalk_studio.fact_check import (
    apply_fact_check,
    normalize_fact_check_sources,
    queue_fact_checks,
    validate_fact_check_artifact,
)
from deeptalk_studio.models import ResearchReport
from deeptalk_studio.quality import calculate_quality_summary
from deeptalk_studio.validation import ReportValidationError
from tests.fixtures import valid_fact_check_data, valid_report_data


class FactCheckTests(unittest.TestCase):
    def _artifact_with_source(self, source):
        artifact = valid_fact_check_data()
        artifact["new_sources"] = [source]
        artifact["tool_provenance"]["consulted_urls"].append(source["url"])
        artifact["evidence_links"] = [
            {
                "id": "FE1",
                "claim_id": "C1",
                "source_id": source["id"],
                "relation": "supports",
                "evidence_summary": "用于测试来源归组。",
                "evidence_locator": "测试定位",
                "independence_group": "MODEL-GROUP",
                "verification_notes": "",
                "verified_in_review": False,
            }
        ]
        artifact["checks"][0]["source_ids"].append(source["id"])
        return artifact

    def test_high_risk_claims_are_automatically_queued(self):
        report = ResearchReport.from_dict(valid_report_data())

        self.assertEqual(queue_fact_checks(report), ["C1"])

    def test_valid_independent_artifact_passes(self):
        report = ResearchReport.from_dict(valid_report_data())

        validate_fact_check_artifact(valid_fact_check_data(), report)

    def test_artifact_claim_must_exist_in_report(self):
        report = ResearchReport.from_dict(valid_report_data())
        artifact = valid_fact_check_data()
        artifact["checks"][0]["claim_id"] = "C404"

        with self.assertRaisesRegex(ReportValidationError, "C404"):
            validate_fact_check_artifact(artifact, report)

    def test_high_risk_check_must_record_a_new_source_search(self):
        report = ResearchReport.from_dict(valid_report_data())
        artifact = valid_fact_check_data()
        artifact["checks"][0]["searched_new_sources"] = False

        with self.assertRaisesRegex(ReportValidationError, "新的来源检索"):
            validate_fact_check_artifact(artifact, report)

    def test_high_risk_check_must_link_to_a_url_from_second_pass_provenance(self):
        report = ResearchReport.from_dict(valid_report_data())
        artifact = valid_fact_check_data()
        artifact["tool_provenance"]["consulted_urls"] = ["https://unrelated.example/news"]
        artifact["tool_provenance"]["citation_urls"] = []

        with self.assertRaisesRegex(ReportValidationError, "本次独立检索"):
            validate_fact_check_artifact(artifact, report)

    def test_artifact_must_preserve_separate_tool_provenance(self):
        report = ResearchReport.from_dict(valid_report_data())
        artifact = valid_fact_check_data()
        artifact["tool_provenance"]["search_call_ids"] = []
        artifact["tool_provenance"]["consulted_urls"] = []
        artifact["tool_provenance"]["citation_urls"] = []

        with self.assertRaisesRegex(ReportValidationError, "tool provenance"):
            validate_fact_check_artifact(artifact, report)

    def test_new_evidence_must_reference_known_source(self):
        report = ResearchReport.from_dict(valid_report_data())
        artifact = valid_fact_check_data()
        link = dict(report.data["evidence_links"][0])
        link.update(id="FE1", source_id="S404")
        artifact["evidence_links"] = [link]

        with self.assertRaisesRegex(ReportValidationError, "S404"):
            validate_fact_check_artifact(artifact, report)

    def test_applying_artifact_updates_classification_and_review_summary(self):
        data = valid_report_data()
        data["claims"][0]["classification"] = "media_report"
        data["claims"][0]["verification_status"] = "not_checked"
        data["status"] = "fact_check_pending"
        data["fact_check"] = {
            "review_id": "",
            "reviewed_at": "",
            "status": "not_run",
            "checked_claim_ids": [],
            "unresolved_claim_ids": [],
        }
        for link in data["evidence_links"]:
            link["verified_in_review"] = False
        data["quality_summary"] = calculate_quality_summary(data)
        report = ResearchReport.from_dict(data)
        artifact = valid_fact_check_data(report.data)
        artifact["checks"][0]["original_classification"] = "media_report"

        updated = apply_fact_check(report, artifact)

        claim = next(item for item in updated["claims"] if item["id"] == "C1")
        self.assertEqual(claim["classification"], "confirmed_fact")
        self.assertEqual(claim["verification_status"], "verified")
        self.assertEqual(updated["fact_check"]["review_id"], artifact["review_id"])
        self.assertEqual(updated["fact_check"]["checked_claim_ids"], ["C1"])
        self.assertEqual(updated["fact_check"]["unresolved_claim_ids"], [])
        reviewed_links = [
            link
            for link in updated["evidence_links"]
            if link["claim_id"] == "C1" and link["source_id"] in {"S1", "S2"}
        ]
        self.assertTrue(reviewed_links)
        self.assertTrue(all(link["verified_in_review"] for link in reviewed_links))

    def test_partially_verified_claim_remains_in_unresolved_review_list(self):
        report = ResearchReport.from_dict(valid_report_data())
        artifact = valid_fact_check_data()
        artifact["checks"][0]["outcome"] = "partially_verified"

        updated = apply_fact_check(report, artifact)

        self.assertEqual(updated["fact_check"]["unresolved_claim_ids"], ["C1"])

    def test_fact_check_exact_old_url_is_canonicalized_as_duplicate(self):
        report = ResearchReport.from_dict(valid_report_data())
        source = dict(report.sources[0])
        source.update(
            id="S9",
            publisher="另一个页面标签",
            independence_group="MODEL-GROUP",
            independence_status="independent",
            syndication_of="",
        )

        normalized = normalize_fact_check_sources(
            self._artifact_with_source(source), report
        )

        self.assertEqual(normalized["new_sources"][0]["independence_status"], "duplicate")
        self.assertEqual(normalized["new_sources"][0]["independence_group"], "IG1")
        self.assertEqual(normalized["evidence_links"][0]["independence_group"], "IG1")

    def test_fact_check_tracking_url_to_old_source_is_duplicate(self):
        report = ResearchReport.from_dict(valid_report_data())
        source = dict(report.sources[0])
        source.update(
            id="S9",
            url="https://example.com/official?utm_source=factcheck&fbclid=x",
            normalized_url="https://forged.invalid/new",
            publisher="追踪链接页面",
            independence_group="MODEL-GROUP",
            independence_status="independent",
            syndication_of="",
        )

        normalized = normalize_fact_check_sources(
            self._artifact_with_source(source), report
        )

        self.assertEqual(normalized["new_sources"][0]["normalized_url"], "https://example.com/official")
        self.assertEqual(normalized["new_sources"][0]["independence_status"], "duplicate")
        self.assertEqual(normalized["new_sources"][0]["independence_group"], "IG1")

    def test_fact_check_same_title_repost_is_syndicated_not_independent(self):
        report = ResearchReport.from_dict(valid_report_data())
        source = dict(report.sources[0])
        source.update(
            id="S9",
            url="https://mirror.example.net/repost",
            normalized_url="https://mirror.example.net/repost",
            publisher="转载站",
            independence_group="MODEL-GROUP",
            independence_status="independent",
            syndication_of="",
        )

        normalized = normalize_fact_check_sources(
            self._artifact_with_source(source), report
        )

        self.assertEqual(normalized["new_sources"][0]["independence_status"], "syndicated")
        self.assertEqual(normalized["new_sources"][0]["independence_group"], "IG1")
        self.assertEqual(normalized["new_sources"][0]["syndication_of"], "S1")

    def test_fact_check_distinct_source_forms_a_new_group(self):
        report = ResearchReport.from_dict(valid_report_data())
        source = dict(report.sources[1])
        source.update(
            id="S9",
            title="独立第三方文件",
            url="https://independent.example.net/source",
            normalized_url="https://forged.invalid/source",
            publisher="独立发布者",
            independence_group="MODEL-GROUP",
            independence_status="independent",
            syndication_of="",
        )

        normalized = normalize_fact_check_sources(
            self._artifact_with_source(source), report
        )

        self.assertEqual(normalized["new_sources"][0]["independence_status"], "independent")
        self.assertEqual(normalized["new_sources"][0]["independence_group"], "IG3")


if __name__ == "__main__":
    unittest.main()
