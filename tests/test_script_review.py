import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_review import (
    prepare_script_review,
    validate_script_review_artifact,
)
from deeptalk_studio.script_validation import ScriptValidationError, prepare_script_draft
from tests.fixtures import (
    approved_report_data,
    valid_script_content,
    valid_script_review_content,
)


class ScriptReviewTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile()
        self.script = prepare_script_draft(
            valid_script_content(),
            self.report,
            self.profile,
            created_at="2026-08-10T13:00:00+08:00",
            script_id="SCR-review",
        )

    def review(self, content=None):
        return prepare_script_review(
            content or valid_script_review_content(),
            self.report,
            self.script,
            self.profile,
            created_at="2026-08-10T14:00:00+08:00",
            review_id="SRV-test",
        )

    def test_no_blocking_issue_creates_pass_artifact_and_reviewed_script_revision(self):
        result = self.review()

        self.assertEqual(result.artifact["artifact_version"], "0.4")
        self.assertEqual(result.artifact["gate_status"], "pass")
        self.assertEqual(result.artifact["blocking_issue_count"], 0)
        self.assertEqual(result.script.revision, 2)
        self.assertEqual(result.script.previous_revision, 1)
        self.assertEqual(result.script.status, "reviewed")

    def test_blocking_issue_keeps_script_draft_and_code_owns_severity(self):
        content = valid_script_review_content()
        content["issues"] = [
            {
                "issue_type": "unsupported_fact",
                "beat_ids": ["B001"],
                "claim_ids": ["C1"],
                "explanation": "这一句超出了 Research Claim 的表达强度。",
                "suggested_fix": "收窄为报告已确认的日期事实。",
            }
        ]

        result = self.review(content)

        self.assertEqual(result.artifact["gate_status"], "fail")
        self.assertEqual(result.artifact["blocking_issue_count"], 1)
        self.assertEqual(result.artifact["issues"][0]["severity"], "blocking")
        self.assertEqual(result.script.status, "draft")

    def test_model_cannot_spoof_review_identity_gate_status_or_severity(self):
        for field, value in (
            ("review_id", "forged"),
            ("gate_status", "pass"),
            ("blocking_issue_count", 0),
        ):
            with self.subTest(field=field):
                content = valid_script_review_content()
                content[field] = value
                with self.assertRaisesRegex(ScriptValidationError, "未知字段"):
                    self.review(content)

        content = valid_script_review_content()
        content["issues"] = [
            {
                "issue_type": "avoid_claim_usage",
                "severity": "advisory",
                "beat_ids": ["B001"],
                "claim_ids": [],
                "explanation": "使用了禁讲结论。",
                "suggested_fix": "删除。",
            }
        ]
        with self.assertRaisesRegex(ScriptValidationError, "未知字段"):
            self.review(content)

    def test_issue_references_must_exist(self):
        for field, value in (("beat_ids", ["B404"]), ("claim_ids", ["C404"])):
            with self.subTest(field=field):
                content = valid_script_review_content()
                content["issues"] = [
                    {
                        "issue_type": "oral_naturalness",
                        "beat_ids": [],
                        "claim_ids": [],
                        "explanation": "测试引用。",
                        "suggested_fix": "修改。",
                    }
                ]
                content["issues"][0][field] = value
                with self.assertRaisesRegex(ScriptValidationError, "B404|C404"):
                    self.review(content)

    def test_missing_must_keep_claim_gets_explicit_advisory_explanation(self):
        content = valid_script_content()
        content["beats"] = content["beats"][:-1]
        content["must_keep_omission_reasons"] = [
            {"claim_id": "C3", "reason": "这版只在编辑风险提示中保留该边界。"}
        ]
        script = prepare_script_draft(
            content,
            self.report,
            self.profile,
            created_at="2026-08-10T13:00:00+08:00",
            script_id="SCR-missing",
        )

        result = prepare_script_review(
            valid_script_review_content(),
            self.report,
            script,
            self.profile,
            created_at="2026-08-10T14:00:00+08:00",
            review_id="SRV-missing",
        )

        omission = next(
            issue for issue in result.artifact["issues"] if issue["issue_type"] == "must_keep_omission"
        )
        self.assertEqual(omission["claim_ids"], ["C3"])
        self.assertEqual(omission["severity"], "advisory")

    def test_final_review_gate_is_rederived_and_tampering_fails_closed(self):
        result = self.review()
        tampered = dict(result.artifact)
        tampered["gate_status"] = "fail"
        with self.assertRaisesRegex(ScriptValidationError, "gate_status"):
            validate_script_review_artifact(tampered, self.report, self.script)

    def test_review_cannot_pass_when_required_check_dimensions_are_missing(self):
        content = valid_script_review_content()
        content["checks"] = content["checks"][:-1]

        with self.assertRaisesRegex(ScriptValidationError, "缺少必检项"):
            self.review(content)


if __name__ == "__main__":
    unittest.main()
