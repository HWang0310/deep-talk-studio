from copy import deepcopy
import unittest

from deeptalk_studio.content_director import prepare_content_thesis_card
from deeptalk_studio.content_director_profile import load_content_director_profile
from deeptalk_studio.content_thesis_review import (
    ContentThesisReviewError,
    approve_content_thesis_card,
    prepare_content_thesis_review,
)
from deeptalk_studio.models import ResearchReport
from tests.fixtures import approved_report_data
from tests.test_content_director import valid_thesis_content


class ContentThesisReviewTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_content_director_profile()
        self.report = ResearchReport.from_dict(approved_report_data())
        self.card = prepare_content_thesis_card(
            valid_thesis_content(), self.report, self.profile,
            created_at="2026-08-24T10:00:00+08:00", card_id="thesis-review-test"
        )

    def test_review_requires_all_controlled_checks_and_approval_requires_real_confirmation(self):
        review = prepare_content_thesis_review(
            self.card,
            self.report,
            self.profile,
            {
                "checks": [
                    {"check_name": name, "outcome": "pass", "reason": "已满足本期要求"}
                    for name in self.profile["thesis_gate_checks"]
                ],
                "issues": [],
                "overall_summary": "本期内容方向可进入人工确认。",
            },
            created_at="2026-08-24T10:01:00+08:00",
            review_id="thesis-review-01",
        )
        with self.assertRaises(ContentThesisReviewError):
            approve_content_thesis_card(
                self.card, review, self.report, self.profile, confirmation="好的"
            )
        approved = approve_content_thesis_card(
            self.card,
            review,
            self.report,
            self.profile,
            confirmation="确认本期内容方向，进入写稿。",
            approved_at="2026-08-24T10:02:00+08:00",
        )
        self.assertEqual(approved.status, "approved_for_script")
        self.assertEqual(approved.review_state["state"], "reviewed")

    def test_failing_controlled_check_cannot_be_approved(self):
        review_content = {
            "checks": [
                {
                    "check_name": name,
                    "outcome": "fail" if name == "counter_evidence" else "pass",
                    "reason": "反证没有被保留" if name == "counter_evidence" else "已满足",
                }
                for name in self.profile["thesis_gate_checks"]
            ],
            "issues": [
                {"issue_type": "counter_evidence_ignored", "severity": "blocking", "description": "反证缺失"}
            ],
            "overall_summary": "需要修订。",
        }
        review = prepare_content_thesis_review(
            self.card, self.report, self.profile, review_content,
            created_at="2026-08-24T10:01:00+08:00", review_id="thesis-review-02"
        )
        self.assertEqual(review["gate"]["decision"], "needs_revision")
        with self.assertRaises(ContentThesisReviewError):
            approve_content_thesis_card(
                self.card, review, self.report, self.profile,
                confirmation="确认本期内容方向，进入写稿。",
            )


if __name__ == "__main__":
    unittest.main()
