import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_review import (
    prepare_script_review,
    validate_script_review_artifact,
)
from deeptalk_studio.script_validation import (
    ScriptValidationError,
    prepare_script_draft,
    validate_script_draft,
)
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
        self.assertEqual(result.artifact["review_consistency_version"], "0.4.2")
        self.assertEqual(result.artifact["gate_status"], "pass")
        self.assertEqual(result.artifact["blocking_issue_count"], 0)
        self.assertEqual(result.script.revision, 2)
        self.assertEqual(result.script.previous_revision, 1)
        self.assertEqual(result.script.status, "reviewed")
        with self.assertRaisesRegex(ScriptValidationError, "Review Artifact"):
            validate_script_draft(result.script.to_dict(), self.report, self.profile)
        validate_script_draft(result.script, self.report, self.profile, result.artifact)

    def test_reviewed_script_rejects_forged_or_mismatched_review_linkage(self):
        result = self.review()
        forged = result.script.to_dict()
        forged["review_state"] = dict(forged["review_state"])
        forged["review_state"]["review_id"] = "SRV-forged"

        with self.assertRaisesRegex(ScriptValidationError, "Review linkage"):
            validate_script_draft(forged, self.report, self.profile, result.artifact)

        changed = result.script.to_dict()
        changed["beats"][0]["narration"] = changed["beats"][0]["narration"].replace(
            "八月九日", "八月十日"
        )
        with self.assertRaisesRegex(ScriptValidationError, "content digest"):
            validate_script_draft(changed, self.report, self.profile, result.artifact)

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
        self.assertEqual(result.script.review_state["state"], "not_reviewed")

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

    def test_duplicate_review_check_is_rejected(self):
        content = valid_script_review_content()
        content["checks"].append(dict(content["checks"][0]))

        with self.assertRaisesRegex(ScriptValidationError, "不能重复"):
            self.review(content)

    def test_review_artifact_for_wrong_script_revision_is_rejected(self):
        result = self.review()
        artifact = dict(result.artifact)
        artifact["script_revision"] = 2

        with self.assertRaisesRegex(ScriptValidationError, "script_revision"):
            validate_script_review_artifact(artifact, self.report, self.script)

    def test_critical_failed_checks_without_their_blocking_issue_fail_closed(self):
        required_issue_types = {
            "factual_grounding": "unsupported_fact",
            "attribution_integrity": "attribution_error",
            "uncertainty_preservation": "material_uncertainty_loss",
            "avoid_claim_compliance": "avoid_claim_usage",
            "high_risk_boundary": "high_risk_overclaim",
            "analysis_fact_separation": "analysis_as_fact",
            "perspective_fairness": "perspective_distortion",
            "research_gap_integrity": "research_gap_filled",
        }
        for check_name, issue_type in required_issue_types.items():
            with self.subTest(check_name=check_name):
                content = valid_script_review_content()
                check = next(
                    item for item in content["checks"] if item["check_name"] == check_name
                )
                check["outcome"] = "fail"
                check["reason"] = "受控测试：此项未通过。"
                with self.assertRaisesRegex(ScriptValidationError, "blocking issue"):
                    self.review(content)

                content["issues"] = [
                    {
                        "issue_type": issue_type,
                        "beat_ids": ["B001"],
                        "claim_ids": ["C1"],
                        "explanation": "受控测试：问题已明确记录。",
                        "suggested_fix": "收窄或改正这一处表达。",
                    }
                ]
                result = self.review(content)
                self.assertEqual(result.artifact["gate_status"], "fail")

    def test_editorial_failed_check_with_matching_advisory_can_keep_gate_passing(self):
        content = valid_script_review_content()
        check = next(
            item
            for item in content["checks"]
            if item["check_name"] == "oral_naturalness"
        )
        check["outcome"] = "fail"
        check["reason"] = "句子偏书面。"
        content["issues"] = [
            {
                "issue_type": "oral_naturalness",
                "beat_ids": ["B001"],
                "claim_ids": [],
                "explanation": "开场句不够自然。",
                "suggested_fix": "改成更口语的短句。",
            }
        ]

        result = self.review(content)

        self.assertEqual(result.artifact["gate_status"], "pass")
        self.assertEqual(result.script.status, "reviewed")

    def test_failed_editorial_check_without_issue_is_rejected(self):
        content = valid_script_review_content()
        check = next(
            item
            for item in content["checks"]
            if item["check_name"] == "information_density"
        )
        check["outcome"] = "fail"
        check["reason"] = "信息重复。"

        with self.assertRaisesRegex(ScriptValidationError, "对应 issue"):
            self.review(content)

    def test_missing_hook_structure_is_blocking_under_narrative_review(self):
        content = valid_script_review_content()
        check = next(
            item for item in content["checks"]
            if item["check_name"] == "narrative_structure"
        )
        check["outcome"] = "fail"
        check["reason"] = "开场没有价值承诺，中段没有信息转折，结尾也没有兑现开场问题。"
        content["issues"] = [{
            "issue_type": "hook_structure",
            "beat_ids": ["B001"],
            "claim_ids": [],
            "explanation": "Hook-aware 结构不完整。",
            "suggested_fix": "用研究支持的问题重写开场，并让结尾兑现观众承诺。",
        }]

        result = self.review(content)

        self.assertEqual(result.artifact["review_consistency_version"], "0.4.2")
        self.assertEqual(result.artifact["gate_status"], "fail")
        self.assertEqual(result.artifact["issues"][0]["severity"], "blocking")
        self.assertEqual(result.script.status, "draft")

    def test_legacy_041_review_artifact_remains_valid(self):
        result = self.review()
        legacy = dict(result.artifact)
        legacy["review_consistency_version"] = "0.4.1"

        validate_script_review_artifact(legacy, self.report, self.script)

    def test_critical_check_cannot_be_marked_not_applicable(self):
        content = valid_script_review_content()
        check = next(
            item
            for item in content["checks"]
            if item["check_name"] == "factual_grounding"
        )
        check["outcome"] = "not_applicable"
        check["reason"] = "不应允许跳过事实核验。"

        with self.assertRaisesRegex(ScriptValidationError, "not_applicable"):
            self.review(content)


if __name__ == "__main__":
    unittest.main()
