import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_review import prepare_script_review
from deeptalk_studio.script_revisions import compare_script_revisions, create_script_revision
from deeptalk_studio.script_validation import ScriptValidationError, prepare_script_draft
from tests.fixtures import (
    approved_report_data,
    valid_script_content,
    valid_script_review_content,
)


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
        self.assertEqual(revised.beats[0]["beat_id"], "B001")

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

    def test_user_edit_of_reviewed_script_resets_review_state_to_draft(self):
        approved_result = prepare_script_review(
            valid_script_review_content(),
            self.report,
            self.first,
            self.profile,
            created_at="2026-08-10T13:30:00+08:00",
            review_id="SRV-revision",
        )
        approved = approved_result.script

        revised = create_script_revision(
            valid_script_content(),
            approved,
            self.report,
            self.profile,
            generated_at="2026-08-10T14:00:00+08:00",
        )

        self.assertEqual(revised.status, "draft")
        self.assertEqual(revised.review_state["state"], "not_reviewed")
        reapproved = prepare_script_review(
            valid_script_review_content(),
            self.report,
            revised,
            self.profile,
            created_at="2026-08-10T14:30:00+08:00",
            review_id="SRV-r3",
        ).script
        self.assertEqual(reapproved.revision, 4)
        self.assertEqual(reapproved.status, "reviewed")

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

    def test_inserted_beat_does_not_renumber_retained_beats(self):
        content = valid_script_content()
        for beat, origin in zip(content["beats"], ["B001", "B002", "B003", "B004"]):
            beat["origin_beat_id"] = origin
        content["beats"].insert(
            1,
            {
                "purpose": "在事实与解释之间补一个转场。",
                "content_kind": "transition",
                "narration": "但真正需要分开的，是已经确认的事实和后续解释。",
                "claim_ids": [],
                "evidence_link_ids": [],
                "analysis_basis_claim_ids": [],
                "risk_notes": "不新增事实判断。",
            },
        )

        revised = create_script_revision(
            content,
            self.first,
            self.report,
            self.profile,
            generated_at="2026-08-10T14:00:00+08:00",
        )

        self.assertEqual(
            [beat["beat_id"] for beat in revised.beats],
            ["B001", "B005", "B002", "B003", "B004"],
        )
        comparison = compare_script_revisions(self.first, revised)
        self.assertEqual(comparison["added_beat_ids"], ["B005"])
        self.assertEqual(comparison["removed_beat_ids"], [])

    def test_deleted_beat_is_retired_and_never_reused(self):
        inserted = valid_script_content()
        for beat, origin in zip(inserted["beats"], ["B001", "B002", "B003", "B004"]):
            beat["origin_beat_id"] = origin
        inserted["beats"].insert(
            1,
            {
                "purpose": "新增转场。",
                "content_kind": "transition",
                "narration": "先把两层信息分开。",
                "claim_ids": [],
                "evidence_link_ids": [],
                "analysis_basis_claim_ids": [],
                "risk_notes": "不新增事实。",
            },
        )
        second = create_script_revision(
            inserted,
            self.first,
            self.report,
            self.profile,
            generated_at="2026-08-10T14:00:00+08:00",
        )
        third_content = valid_script_content()
        # Drop B002, retain the inserted B005, and then add a distinct question.
        third_content["beats"] = [
            inserted["beats"][0],
            inserted["beats"][1],
            inserted["beats"][3],
            inserted["beats"][4],
        ]
        for beat, origin in zip(
            third_content["beats"], ["B001", "B005", "B003", "B004"]
        ):
            beat["origin_beat_id"] = origin
        third_content["beats"].append(
            {
                "purpose": "留下可继续研究的问题。",
                "content_kind": "question",
                "narration": "接下来真正需要补上的，究竟是哪一份原始材料？",
                "claim_ids": [],
                "evidence_link_ids": [],
                "analysis_basis_claim_ids": [],
                "risk_notes": "明确这是开放问题。",
            }
        )

        third = create_script_revision(
            third_content,
            second,
            self.report,
            self.profile,
            generated_at="2026-08-10T15:00:00+08:00",
        )

        self.assertIn("B002", third.beat_identity["retired_beat_ids"])
        self.assertIn("B006", [beat["beat_id"] for beat in third.beats])
        self.assertNotIn("B002", [beat["beat_id"] for beat in third.beats])

    def test_duplicate_or_unknown_origin_beat_id_is_rejected(self):
        for origin_ids, message in (
            (["B001", "B001", "B003", "B004"], "重复"),
            (["B001", "B404", "B003", "B004"], "不存在"),
        ):
            with self.subTest(origin_ids=origin_ids):
                content = valid_script_content()
                for beat, origin in zip(content["beats"], origin_ids):
                    beat["origin_beat_id"] = origin
                with self.assertRaisesRegex(ScriptValidationError, message):
                    create_script_revision(
                        content,
                        self.first,
                        self.report,
                        self.profile,
                        generated_at="2026-08-10T14:00:00+08:00",
                    )

    def test_moved_and_edited_beat_keeps_identity_for_comparison(self):
        content = valid_script_content()
        content["beats"] = [content["beats"][2], content["beats"][0], content["beats"][1], content["beats"][3]]
        for beat, origin in zip(content["beats"], ["B003", "B001", "B002", "B004"]):
            beat["origin_beat_id"] = origin
        content["beats"][0]["narration"] += " 这一层需要单独说明。"

        revised = create_script_revision(
            content,
            self.first,
            self.report,
            self.profile,
            generated_at="2026-08-10T14:00:00+08:00",
            target_duration_minutes=10,
        )

        comparison = compare_script_revisions(self.first, revised)
        self.assertEqual(revised.beats[0]["beat_id"], "B003")
        self.assertEqual(comparison["added_beat_ids"], [])
        self.assertEqual(comparison["removed_beat_ids"], [])
        self.assertEqual(comparison["changed_beat_ids"], ["B003"])
        self.assertEqual(comparison["target_duration_change_minutes"], -2)


if __name__ == "__main__":
    unittest.main()
