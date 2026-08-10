import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.revisions import create_revision
from tests.fixtures import valid_report_data


class RevisionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
