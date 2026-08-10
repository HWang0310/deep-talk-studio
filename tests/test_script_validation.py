import unittest
from copy import deepcopy

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile, parse_target_duration
from deeptalk_studio.script_validation import (
    ScriptValidationError,
    assert_report_ready_for_script,
    prepare_script_draft,
    validate_script_draft,
)
from tests.fixtures import approved_report_data, valid_report_data, valid_script_content


class ScriptValidationTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile()

    def prepare(self, content=None, **kwargs):
        return prepare_script_draft(
            content or valid_script_content(),
            self.report,
            self.profile,
            created_at="2026-08-10T13:00:00+08:00",
            script_id="SCR-test",
            target_duration_minutes=12,
            **kwargs,
        )

    def test_only_fully_approved_ready_report_can_enter_script(self):
        assert_report_ready_for_script(self.report)
        for status in ("draft", "fact_check_pending", "reviewed"):
            with self.subTest(status=status):
                data = valid_report_data()
                data["status"] = status
                candidate = ResearchReport.from_dict(data)
                with self.assertRaisesRegex(ScriptValidationError, "用户确认|ready_for_script"):
                    assert_report_ready_for_script(candidate)

    def test_valid_script_gets_machine_identity_metrics_beats_and_coverage(self):
        script = self.prepare()

        self.assertEqual(script.data["artifact_version"], "0.4")
        self.assertEqual(script.data["script_id"], "SCR-test")
        self.assertEqual(script.data["report_id"], self.report.report_id)
        self.assertEqual(script.data["report_revision"], 2)
        self.assertEqual(script.data["status"], "draft")
        self.assertEqual([beat["beat_id"] for beat in script.data["beats"]], ["B001", "B002", "B003", "B004"])
        self.assertGreater(script.data["character_count"], 100)
        self.assertGreater(script.data["estimated_duration_minutes"], 0)
        self.assertEqual(script.data["missing_must_keep_claim_ids"], [])

    def test_model_cannot_spoof_script_identity_revision_status_or_metrics(self):
        for field, value in (
            ("script_id", "forged"),
            ("revision", 99),
            ("status", "reviewed"),
            ("character_count", 1),
        ):
            with self.subTest(field=field):
                content = valid_script_content()
                content[field] = value
                with self.assertRaisesRegex(ScriptValidationError, "未知字段"):
                    self.prepare(content)

    def test_unknown_claim_evidence_and_mismatched_evidence_are_rejected(self):
        content = valid_script_content()
        content["beats"][0]["claim_ids"] = ["C404"]
        with self.assertRaisesRegex(ScriptValidationError, "C404"):
            self.prepare(content)

        content = valid_script_content()
        content["beats"][0]["evidence_link_ids"] = ["E404"]
        with self.assertRaisesRegex(ScriptValidationError, "E404"):
            self.prepare(content)

        content = valid_script_content()
        content["beats"][0]["evidence_link_ids"] = ["E3"]
        with self.assertRaisesRegex(ScriptValidationError, "对应"):
            self.prepare(content)

    def test_fact_beat_rejects_unverified_media_statement_and_high_risk_overclaim(self):
        for claim_id, evidence_id in (("C2", "E3"), ("C3", "E4")):
            with self.subTest(claim_id=claim_id):
                content = valid_script_content()
                content["beats"][0]["claim_ids"] = [claim_id]
                content["beats"][0]["evidence_link_ids"] = [evidence_id]
                with self.assertRaisesRegex(ScriptValidationError, "fact"):
                    self.prepare(content)

        data = approved_report_data()
        data["claims"][0]["verification_status"] = "partially_verified"
        data["fact_check"]["unresolved_claim_ids"] = ["C1"]
        data["quality_summary"]["unresolved_high_risk_count"] = 1
        data["quality_summary"]["gate_status"] = "fail"
        data["quality_summary"]["gate_reasons"] = ["仍有未解决的高风险主张"]
        data["status"] = "draft"
        data["approval_gate"].update(status="pending", user_confirmation="", ready_for_script=False)
        with self.assertRaises(ScriptValidationError):
            assert_report_ready_for_script(ResearchReport.from_dict(data))

    def test_attribution_and_analysis_boundaries_are_enforced(self):
        content = valid_script_content()
        content["beats"][1]["content_kind"] = "fact"
        with self.assertRaisesRegex(ScriptValidationError, "fact"):
            self.prepare(content)

        content = valid_script_content()
        content["beats"][2]["analysis_basis_claim_ids"] = []
        with self.assertRaisesRegex(ScriptValidationError, "analysis_basis"):
            self.prepare(content)

    def test_avoid_claim_and_machine_ids_cannot_enter_spoken_text(self):
        data = approved_report_data()
        data["handoff_to_script_agent"]["avoid_claims"] = ["这句禁止进入稿件"]
        report = ResearchReport.from_dict(data)
        content = valid_script_content()
        content["beats"][0]["narration"] += "这句禁止进入稿件。"
        with self.assertRaisesRegex(ScriptValidationError, "avoid_claim"):
            prepare_script_draft(
                content,
                report,
                self.profile,
                created_at="2026-08-10T13:00:00+08:00",
                script_id="SCR-test",
            )

        content = valid_script_content()
        content["beats"][0]["narration"] += " 根据 C1 和 E1。"
        with self.assertRaisesRegex(ScriptValidationError, "机器 ID"):
            self.prepare(content)

    def test_avoid_claim_imperative_prefix_cannot_hide_forbidden_conclusion(self):
        report_data = approved_report_data()
        report_data["handoff_to_script_agent"]["avoid_claims"] = [
            "不要断言人为操纵已经得到证实。"
        ]
        report = ResearchReport.from_dict(report_data)
        content = valid_script_content()
        content["closing"] = "人为操纵已经得到证实。"

        with self.assertRaisesRegex(ScriptValidationError, "avoid_claim"):
            prepare_script_draft(
                content,
                report,
                self.profile,
                created_at="2026-08-10T13:00:00+08:00",
                script_id="SCR-avoid-core",
            )

    def test_final_artifact_fails_closed_on_report_binding_or_metric_tampering(self):
        script = self.prepare().to_dict()
        script["report_revision"] = 999
        with self.assertRaisesRegex(ScriptValidationError, "report_revision"):
            validate_script_draft(script, self.report, self.profile)

        script = self.prepare().to_dict()
        script["character_count"] = 1
        with self.assertRaisesRegex(ScriptValidationError, "character_count"):
            validate_script_draft(script, self.report, self.profile)

    def test_duration_parser_handles_explicit_and_coarse_natural_language(self):
        self.assertEqual(parse_target_duration("写成 8 分钟"), 8)
        self.assertEqual(parse_target_duration("15 分钟左右"), 15)
        self.assertEqual(parse_target_duration("压到 10 分钟"), 10)
        self.assertEqual(parse_target_duration("做长一点"), 15)
        self.assertEqual(parse_target_duration("更紧凑一点"), 10)
        self.assertEqual(parse_target_duration(""), 12)
        with self.assertRaisesRegex(ScriptValidationError, "3 到 30"):
            parse_target_duration("写成 90 分钟")


if __name__ == "__main__":
    unittest.main()
