from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deeptalk_studio.content_director import prepare_content_thesis_card
from deeptalk_studio.content_director_profile import load_content_director_profile
from deeptalk_studio.content_thesis_renderer import render_content_thesis_review_markdown
from deeptalk_studio.content_thesis_review import approve_content_thesis_card, prepare_content_thesis_review
from deeptalk_studio.content_thesis_storage import ContentThesisStorageError, save_content_thesis_card, save_content_thesis_review_artifact
from deeptalk_studio.models import ResearchReport
from tests.fixtures import approved_report_data
from tests.test_content_director import valid_thesis_content


class ContentThesisStorageTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_content_director_profile()
        self.report = ResearchReport.from_dict(approved_report_data())
        self.card = prepare_content_thesis_card(
            valid_thesis_content(), self.report, self.profile,
            created_at="2026-08-24T10:00:00+08:00", card_id="thesis-storage-test"
        )
        self.review = prepare_content_thesis_review(
            self.card, self.report, self.profile,
            {"checks": [{"check_name": name, "outcome": "pass", "reason": "可进入人工确认"} for name in self.profile["thesis_gate_checks"]], "issues": [], "overall_summary": "可确认。"},
            created_at="2026-08-24T10:01:00+08:00", review_id="review-storage-test"
        )

    def test_immutable_machine_and_human_readable_artifacts(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            card_paths = save_content_thesis_card(self.card, self.report, self.profile, root)
            review_paths = save_content_thesis_review_artifact(
                self.review, self.card, self.report, self.profile, root
            )
            self.assertTrue(card_paths.json.exists())
            self.assertTrue(card_paths.user_review.exists())
            self.assertTrue(review_paths.json.exists())
            page = card_paths.user_review.read_text(encoding="utf-8")
            self.assertIn("本期内容方向", page)
            self.assertIn("不是最终稿", page)
            self.assertNotIn("C1", page)
            with self.assertRaises(ContentThesisStorageError):
                save_content_thesis_card(self.card, self.report, self.profile, root)

    def test_review_page_does_not_expose_machine_identifiers(self):
        page = render_content_thesis_review_markdown(self.card, self.review, self.report, self.profile)
        self.assertIn("# 本期内容方向", page)
        self.assertIn("需要你确认", page)
        self.assertNotIn(self.card.card_id, page)
        self.assertNotIn("C1", page)

    def test_confirmed_card_is_a_new_immutable_revision_with_its_review_binding(self):
        approved = approve_content_thesis_card(
            self.card, self.review, self.report, self.profile,
            confirmation="确认本期内容方向，进入写稿。",
            approved_at="2026-08-24T10:02:00+08:00",
        )
        self.assertEqual((approved.previous_revision, approved.revision), (1, 2))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            save_content_thesis_card(self.card, self.report, self.profile, root)
            paths = save_content_thesis_card(approved, self.report, self.profile, root, self.review)
        self.assertTrue(paths.json.name.endswith("r0002.json"))


if __name__ == "__main__":
    unittest.main()
