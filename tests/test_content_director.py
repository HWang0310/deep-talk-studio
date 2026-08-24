import unittest

from deeptalk_studio.content_director import (
    ContentDirectorValidationError,
    prepare_content_thesis_card,
)
from deeptalk_studio.content_director_profile import load_content_director_profile
from deeptalk_studio.models import ResearchReport
from tests.fixtures import approved_report_data, valid_report_data


def valid_thesis_content():
    return {
        "core_question": "公众为什么会在信息不足时迅速选择相信一种解释？",
        "one_sentence_answer": "人们需要解释，但不能把解释错当成事实。",
        "core_thesis": "这期不是替任何一方定罪，而是把事实、说法和推测重新分开。",
        "counterintuitive_point": "最容易让人失去判断的，不是没有信息，而是太快得到一个完整答案。",
        "target_emotion": "先被反差抓住，再获得一点判断上的踏实。",
        "resonance": "每个人都经历过热点里信息很多、结论却很快的时刻。",
        "approval_point": "我也不想被一句看似完整的话替我下结论。",
        "comment_tension": "解释公众疑问，和提前替事件定责，边界究竟在哪？",
        "spokesperson_value": "替观众说出：我需要解释，但我也不想被情绪替我判断。",
        "value_identity": "这个账号把判断权交还给观众，也愿意承认不知道。",
        "strongest_evidence_claim_ids": ["C1"],
        "counter_evidence_claim_ids": ["C2"],
        "uncertainty_limits": ["原因仍是当事机构说法，不能写成独立结论。"],
        "crowded_angles": ["直接猜测责任人"],
        "differentiated_angle": "把公众需要解释与证据尚不够之间的拉扯讲出来。",
        "hook_promise": "开头让观众看到：一个事件发生后，最危险的不一定是没答案，而是答案来得太快。",
        "ending_question_or_judgment": "成熟的判断，不是立刻站队，而是知道哪一步还不能跨过去。",
        "competitive_insight_notes": ["只吸收参考样本的反差与认知换挡机制，不复用其表达。"],
    }


class ContentDirectorTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_content_director_profile()

    def test_requires_ready_for_script_research(self):
        report = ResearchReport.from_dict(valid_report_data())
        with self.assertRaisesRegex(ContentDirectorValidationError, "ready_for_script"):
            prepare_content_thesis_card(
                valid_thesis_content(), report, self.profile,
                created_at="2026-08-24T10:00:00+08:00", card_id="THS-test",
            )

    def test_derives_draft_card_bound_to_verified_fact_and_counterevidence(self):
        card = prepare_content_thesis_card(
            valid_thesis_content(), self.report, self.profile,
            created_at="2026-08-24T10:00:00+08:00", card_id="THS-test",
        )
        self.assertEqual(card.status, "draft")
        self.assertEqual(card.report_id, self.report.report_id)
        self.assertEqual(card.report_revision, self.report.revision)
        self.assertEqual(card.strongest_evidence_claim_ids, ["C1"])
        self.assertEqual(card.counter_evidence_claim_ids, ["C2"])
        self.assertTrue(card.content_digest)

    def test_rejects_unknown_or_unverified_strongest_evidence(self):
        for claim_id in ("C404", "C2"):
            with self.subTest(claim_id=claim_id):
                content = valid_thesis_content()
                content["strongest_evidence_claim_ids"] = [claim_id]
                with self.assertRaisesRegex(ContentDirectorValidationError, "strongest"):
                    prepare_content_thesis_card(
                        content, self.report, self.profile,
                        created_at="2026-08-24T10:00:00+08:00", card_id="THS-test",
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
