import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_revisions import compare_script_revisions, create_script_revision
from deeptalk_studio.script_validation import ScriptValidationError, prepare_script_draft
from tests.fixtures import approved_report_data, valid_script_content


class ScriptRevisionTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile()
        self.first = prepare_script_draft(
            valid_script_content(),
            self.report,
            self.profile,
            created_at="2026-08-10T13:00:00+08:00",
            script_id="SCR-revision",
        )

    def test_user_edit_creates_new_draft_revision_with_new_duration(self):
        content = valid_script_content()
        content["beats"][0]["narration"] = "事情先从八月九日这个时间点说起。"

        revised = create_script_revision(
            content,
            self.first,
            self.report,
            self.profile,
            generated_at="2026-08-10T14:00:00+08:00",
            target_duration_minutes=8,
            change_summary="压到 8 分钟并更换开头。",
        )

        self.assertEqual(revised.script_id, self.first.script_id)
        self.assertEqual(revised.revision, 2)
        self.assertEqual(revised.previous_revision, 1)
        self.assertEqual(revised.report_revision, 2)
        self.assertEqual(revised.target_duration_minutes, 8)
        self.assertEqual(revised.status, "draft")

    def test_script_revision_cannot_silently_switch_research_revision(self):
        data = approved_report_data()
        data["revision"] = 3
        data["previous_revision"] = 2
        new_report = ResearchReport.from_dict(data)

        with self.assertRaisesRegex(ScriptValidationError, "Research revision"):
            create_script_revision(
                valid_script_content(),
                self.first,
                new_report,
                self.profile,
                generated_at="2026-08-10T14:00:00+08:00",
            )

    def test_comparison_reports_beats_duration_and_claim_coverage_changes(self):
        content = valid_script_content()
        content["beats"][0]["narration"] = "换一个更短的开头。"
        content["beats"] = content["beats"][:-1]
        content["must_keep_omission_reasons"] = [
            {"claim_id": "C3", "reason": "缩短版本中只保留在研究风险提示。"}
        ]
        revised = create_script_revision(
            content,
            self.first,
            self.report,
            self.profile,
            generated_at="2026-08-10T14:00:00+08:00",
            target_duration_minutes=8,
        )

        comparison = compare_script_revisions(self.first, revised)

        self.assertEqual(comparison["from_revision"], 1)
        self.assertEqual(comparison["to_revision"], 2)
        self.assertIn("B001", comparison["changed_beat_ids"])
        self.assertIn("B004", comparison["removed_beat_ids"])
        self.assertEqual(comparison["target_duration_change_minutes"], -4)
        self.assertEqual(comparison["removed_claim_coverage"], ["C3"])


if __name__ == "__main__":
    unittest.main()
