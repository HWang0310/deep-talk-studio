import copy
import unittest

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import (
    MATERIAL_REVIEW_CHECK_NAMES,
    MaterialReviewError,
    prepare_material_review,
)
from deeptalk_studio.material_validation import prepare_material_package
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


def passing_review_content():
    return {
        "issues": [],
        "checks": [
            {"check_name": name, "outcome": "pass", "reason": "已按正式素材契约核对。"}
            for name in MATERIAL_REVIEW_CHECK_NAMES
        ],
        "overall_notes": "素材来源、权利、画面数据和使用方式均通过检查。",
    }


class MaterialReviewTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.profile = load_material_profile()
        self.package = prepare_material_package(
            valid_material_content(), self.script, self.report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest=rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-review",
        )

    def review(self, content):
        return prepare_material_review(
            content, self.package, self.script, self.report, self.profile,
            created_at="2026-08-11T11:00:00+08:00", review_id="MRV-test",
        )

    def test_passing_review_creates_new_reviewed_revision(self):
        result = self.review(passing_review_content())
        self.assertEqual(result.package.revision, 2)
        self.assertEqual(result.package.status, "reviewed")
        self.assertEqual(result.artifact["gate_status"], "pass")

    def test_all_required_checks_must_be_present(self):
        content = passing_review_content()
        content["checks"].pop()
        with self.assertRaisesRegex(MaterialReviewError, "缺少"):
            self.review(content)

    def test_failed_check_without_matching_issue_is_rejected(self):
        content = passing_review_content()
        content["checks"][0]["outcome"] = "fail"
        with self.assertRaisesRegex(MaterialReviewError, "issue"):
            self.review(content)

    def test_dangerous_item_is_isolated_when_safe_original_visual_remains(self):
        content = passing_review_content()
        content["issues"] = [{
            "issue_type": "rights_misrepresented", "material_ids": ["M001"],
            "visual_ids": [], "cue_ids": ["VC001"], "explanation": "复用依据与页面不符。",
            "suggested_fix": "仅保留引用链接，改用原创时间线。",
        }]
        for check in content["checks"]:
            if check["check_name"] == "rights_reuse":
                check["outcome"] = "fail"
        result = self.review(content)
        self.assertEqual(result.package.status, "reviewed_with_warnings")
        self.assertEqual(result.package.materials[0]["eligibility_status"], "rejected")

    def test_ai_visual_as_real_evidence_is_blocking(self):
        content = passing_review_content()
        content["issues"] = [{
            "issue_type": "ai_visual_as_real_evidence", "material_ids": [],
            "visual_ids": ["V001"], "cue_ids": ["VC002"],
            "explanation": "原创图被标成真实现场画面。", "suggested_fix": "改为说明性画面并明确标注。",
        }]
        for check in content["checks"]:
            if check["check_name"] == "ai_real_confusion":
                check["outcome"] = "fail"
        result = self.review(content)
        self.assertEqual(result.package.status, "reviewed_with_warnings")
        self.assertEqual(result.package.generated_visuals[0]["eligibility_status"], "rejected")

    def test_package_level_fabricated_source_blocks_entire_package(self):
        content = passing_review_content()
        content["issues"] = [{
            "issue_type": "fabricated_source", "material_ids": [], "visual_ids": [],
            "cue_ids": [], "explanation": "包级来源记录无法对应真实页面。",
            "suggested_fix": "停止使用并重新搜索。",
        }]
        for check in content["checks"]:
            if check["check_name"] == "provenance_integrity":
                check["outcome"] = "fail"
        self.assertEqual(self.review(content).package.status, "blocked")

    def test_research_update_required_cannot_be_overridden_by_review(self):
        content = valid_material_content()
        content["research_update_signals"] = [{
            "beat_ids": ["B001"], "claim_ids": ["C1"], "reason": "日期冲突",
            "new_source_url": "https://example.net/new",
        }]
        package = prepare_material_package(
            content, self.script, self.report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest=rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-update",
        )
        result = prepare_material_review(
            passing_review_content(), package, self.script, self.report, self.profile,
            created_at="2026-08-11T11:00:00+08:00", review_id="MRV-update",
        )
        self.assertEqual(result.package.status, "research_update_required")


if __name__ == "__main__":
    unittest.main()

