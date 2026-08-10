import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.revisions import create_approval_revision, create_revision
from deeptalk_studio.validation import ReportValidationError
from tests.fixtures import valid_report_data


class RevisionTests(unittest.TestCase):
    def test_approval_revision_increments_history_and_preserves_research_content(self):
        report = ResearchReport.from_dict(valid_report_data())

        approved = create_approval_revision(
            report,
            confirmation="确认，开始写稿",
            generated_at="2026-08-10T12:00:00+08:00",
        )

        self.assertEqual(approved["revision"], 2)
        self.assertEqual(approved["previous_revision"], 1)
        self.assertEqual(approved["status"], "ready_for_script")
        self.assertEqual(approved["approval_gate"]["status"], "approved")
        self.assertEqual(
            approved["approval_gate"]["user_confirmation"], "确认，开始写稿"
        )
        for field in (
            "sources",
            "claims",
            "evidence_links",
            "fact_check",
            "quality_summary",
            "executive_summary",
            "handoff_to_script_agent",
        ):
            self.assertEqual(approved[field], report.data[field])

    def test_approval_revision_rejects_draft_and_empty_confirmation(self):
        data = valid_report_data()
        data["status"] = "draft"
        draft = ResearchReport.from_dict(data)

        with self.assertRaisesRegex(ReportValidationError, "reviewed"):
            create_approval_revision(
                draft, "确认进入写稿", "2026-08-10T12:00:00+08:00"
            )
        with self.assertRaisesRegex(ReportValidationError, "确认"):
            create_approval_revision(
                ResearchReport.from_dict(valid_report_data()),
                "   ",
                "2026-08-10T12:00:00+08:00",
            )

    def test_revision_preserves_report_identity_and_created_at(self):
        report = ResearchReport.from_dict(valid_report_data())

        revised = create_revision(
            report,
            generated_at="2026-08-10T12:00:00+08:00",
            change_summary="应用独立事实核查。",
        )

        self.assertEqual(revised["report_id"], report.report_id)
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["previous_revision"], 1)
        self.assertEqual(revised["created_at"], report.created_at)
        self.assertEqual(revised["generated_at"], "2026-08-10T12:00:00+08:00")
        self.assertEqual(revised["status"], "draft")

    def test_revision_appends_correction_history(self):
        report = ResearchReport.from_dict(valid_report_data())
        correction = {
            "claim_id": "C1",
            "summary": "修正日期表述。",
            "reason": "发现新的原始文件。",
            "source_ids": ["S1"],
        }

        revised = create_revision(
            report,
            generated_at="2026-08-10T12:00:00+08:00",
            change_summary="修正 C1。",
            corrections=[correction],
        )

        self.assertEqual(revised["corrections"], [correction])

    def test_normal_content_revision_resets_an_existing_approval(self):
        approved = create_approval_revision(
            ResearchReport.from_dict(valid_report_data()),
            "确认进入写稿",
            "2026-08-10T12:00:00+08:00",
        )

        revised = create_revision(
            ResearchReport.from_dict(approved),
            generated_at="2026-08-10T13:00:00+08:00",
            change_summary="补充新的事实材料。",
        )

        self.assertEqual(revised["status"], "draft")
        self.assertEqual(revised["approval_gate"]["status"], "pending")
        self.assertEqual(revised["approval_gate"]["user_confirmation"], "")
        self.assertFalse(revised["approval_gate"]["ready_for_script"])


if __name__ == "__main__":
    unittest.main()
