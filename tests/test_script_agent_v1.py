import unittest
from pathlib import Path

from deeptalk_studio.content_director import prepare_content_thesis_card
from deeptalk_studio.content_director_profile import load_content_director_profile
from deeptalk_studio.content_thesis_review import approve_content_thesis_card, prepare_content_thesis_review
from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import ScriptValidationError, load_script_profile
from deeptalk_studio.script_review import prepare_script_review
from deeptalk_studio.script_validation import prepare_script_draft
from deeptalk_studio.schema import SCRIPT_QUALITY_GATE_CHECK_NAMES_V1, SCRIPT_REVIEW_CHECK_NAMES_LEGACY
from tests.fixtures import approved_report_data
from tests.test_content_director import valid_thesis_content


def _approved_thesis(report):
    director = load_content_director_profile()
    card = prepare_content_thesis_card(valid_thesis_content(), report, director, created_at="2026-08-24T10:00:00+08:00", card_id="v1-card")
    review = prepare_content_thesis_review(
        card, report, director,
        {"checks": [{"check_name": item, "outcome": "pass", "reason": "符合方向要求"} for item in director["thesis_gate_checks"]], "issues": [], "overall_summary": "通过。"},
        created_at="2026-08-24T10:01:00+08:00", review_id="v1-thesis-review",
    )
    return approve_content_thesis_card(card, review, report, director, confirmation="确认本期内容方向，进入写稿。", approved_at="2026-08-24T10:02:00+08:00")


def _v1_content():
    line = "当一个事件的信息还不完整时，人们会急着寻找解释；可解释越完整，越需要追问它有没有证据。"
    narration = line * 36
    return {
        "working_title": "为什么完整答案反而更危险",
        "thesis": "把解释与事实分开，才是热点里真正稀缺的能力。",
        "audience_promise": "用五分钟看清，为什么我们会被太快的完整答案带着走。",
        "beats": [
            {"purpose": "提出异常", "content_kind": "fact", "narration": narration, "claim_ids": ["C1"], "evidence_link_ids": ["E1"], "analysis_basis_claim_ids": [], "risk_notes": ""}
        ],
        "closing": "真正成熟的判断，不是抢着站队，而是愿意在证据不够的时候把问题留下来。",
        "research_caveats": ["原因仍有待独立核实。"],
        "research_gaps": ["仍需更多独立材料。"],
        "must_keep_omission_reasons": [],
    }


class ScriptAgentV1Tests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile(Path("config/script-profile-v1.json"))
        self.thesis = _approved_thesis(self.report)

    def test_v1_requires_human_confirmed_thesis_and_enforces_five_to_six_minutes(self):
        with self.assertRaises(ScriptValidationError):
            prepare_script_draft(_v1_content(), self.report, self.profile, created_at="2026-08-24T10:03:00+08:00", script_id="v1-missing", target_duration_minutes=5.5)
        script = prepare_script_draft(_v1_content(), self.report, self.profile, created_at="2026-08-24T10:03:00+08:00", script_id="v1-script", target_duration_minutes=5.5, content_thesis_card=self.thesis)
        self.assertEqual(script.artifact_version, "1")
        self.assertEqual(script.content_thesis_card_id, "v1-card")
        with self.assertRaises(ScriptValidationError):
            prepare_script_draft(_v1_content(), self.report, self.profile, created_at="2026-08-24T10:03:00+08:00", script_id="v1-wrong-duration", target_duration_minutes=8, content_thesis_card=self.thesis)

    def test_v1_audio_only_failure_is_a_blocking_quality_gate(self):
        script = prepare_script_draft(_v1_content(), self.report, self.profile, created_at="2026-08-24T10:03:00+08:00", script_id="v1-quality", target_duration_minutes=5.5, content_thesis_card=self.thesis)
        checks = []
        for name in [*SCRIPT_REVIEW_CHECK_NAMES_LEGACY, *SCRIPT_QUALITY_GATE_CHECK_NAMES_V1]:
            checks.append({"check_name": name, "outcome": "fail" if name == "audio_only_interest" else "pass", "reason": "纯听时缺乏推进" if name == "audio_only_interest" else "通过"})
        result = prepare_script_review(
            {"checks": checks, "issues": [{"issue_type": "quality_gate_failure", "beat_ids": ["B001"], "claim_ids": [], "explanation": "纯听时缺少冲突、转折与新问题。", "suggested_fix": "重写该段推进。"}], "overall_notes": "需要修订。"},
            self.report, script, self.profile, created_at="2026-08-24T10:04:00+08:00", review_id="v1-quality-review"
        )
        self.assertEqual(result.artifact["gate_status"], "fail")
        self.assertEqual(result.script.status, "draft")


if __name__ == "__main__":
    unittest.main()
