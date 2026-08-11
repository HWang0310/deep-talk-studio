import copy
import unittest

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_validation import (
    MaterialValidationError,
    prepare_material_package,
    validate_material_inputs,
)
from tests.fixtures import approved_report_data, valid_script_content
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


class MaterialValidationTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, self.review = reviewed_inputs()
        self.profile = load_material_profile()

    def prepare(self, content=None, inspection=None, rights=None):
        return prepare_material_package(
            content or valid_material_content(),
            self.script,
            self.report,
            self.profile,
            inspection_manifest=inspection or inspection_manifest(),
            rights_manifest=rights or rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00",
            package_id="MAT-test",
        )

    def test_reviewed_script_and_exact_research_pass_input_gate(self):
        validate_material_inputs(self.script, self.report, self.profile, self.review)

    def test_draft_script_is_rejected_before_material_search(self):
        data = self.script.to_dict()
        data["status"] = "draft"
        data["review_state"] = {
            "state": "not_reviewed", "review_id": "", "reviewed_from_revision": 0,
            "review_gate_status": "not_run", "reviewed_content_digest": "",
        }
        with self.assertRaisesRegex(MaterialValidationError, "reviewed"):
            validate_material_inputs(data, self.report, self.profile, None)

    def test_fake_review_linkage_is_rejected(self):
        data = self.script.to_dict()
        data["review_state"]["review_id"] = "SRV-fake"
        with self.assertRaises(MaterialValidationError):
            validate_material_inputs(data, self.report, self.profile, self.review)

    def test_wrong_research_revision_is_rejected(self):
        wrong = self.report.to_dict()
        wrong["revision"] += 1
        wrong["previous_revision"] += 1
        with self.assertRaisesRegex(MaterialValidationError, "revision"):
            validate_material_inputs(self.script, wrong, self.profile, self.review)

    def test_cue_anchor_must_exist_in_bound_beat(self):
        content = valid_material_content()
        content["cue_sheet"][0]["placement_anchor"] = "不存在的原句"
        with self.assertRaisesRegex(MaterialValidationError, "anchor"):
            self.prepare(content)

    def test_not_every_beat_needs_a_cue(self):
        package = self.prepare()
        self.assertEqual(len(package.cue_sheet), 2)
        self.assertEqual(len(self.script.beats), 4)

    def test_machine_ids_and_ranking_are_derived(self):
        package = self.prepare()
        self.assertEqual(package.cue_sheet[0]["cue_id"], "VC001")
        self.assertEqual(package.materials[0]["material_id"], "M001")
        self.assertIsInstance(package.materials[0]["ranking_score"], float)

    def test_inspected_and_verified_press_asset_is_ready_to_use(self):
        item = self.prepare().materials[0]
        self.assertEqual(item["provenance_status"], "inspected")
        self.assertEqual(item["rights_status"], "official_press_asset")
        self.assertEqual(item["eligibility_status"], "ready_to_use")

    def test_asset_open_without_rights_page_open_is_not_ready_to_use(self):
        inspection = inspection_manifest()
        inspection["entries"] = inspection["entries"][:1]
        item = self.prepare(inspection=inspection).materials[0]
        self.assertEqual(item["eligibility_status"], "reference_only")

    def test_forged_rights_tool_reference_is_not_ready_to_use(self):
        rights = rights_manifest()
        rights["entries"][0]["tool_reference"] = "open:forged"
        item = self.prepare(rights=rights).materials[0]
        self.assertEqual(item["eligibility_status"], "reference_only")

    def test_separate_opened_license_page_can_prove_a_cc_rights_basis(self):
        rights = rights_manifest()
        rights["entries"][0].update(
            rights_status="creative_commons",
            rights_evidence_url="https://example.com/reuse-notice",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            tool_reference="open:reuse-notice",
        )
        inspection = inspection_manifest()
        inspection["entries"].extend([
            {
                "url": "https://example.com/reuse-notice", "inspected_at": "2026-08-11T09:06:00+08:00",
                "inspection_method": "codex_web_open", "tool_reference": "open:reuse-notice",
            },
            {
                "url": "https://creativecommons.org/licenses/by/4.0/", "inspected_at": "2026-08-11T09:07:00+08:00",
                "inspection_method": "codex_web_open", "tool_reference": "open:cc-by",
            },
        ])
        self.assertEqual(self.prepare(inspection=inspection, rights=rights).materials[0]["eligibility_status"], "ready_to_use")

    def test_fake_license_url_is_not_ready_to_use(self):
        rights = rights_manifest()
        rights["entries"][0]["license_url"] = "https://example.com/fake-license"
        item = self.prepare(rights=rights).materials[0]
        self.assertEqual(item["eligibility_status"], "reference_only")

    def test_model_claimed_rights_never_controls_final_eligibility(self):
        content = valid_material_content()
        content["materials"][0]["claimed_rights_status"] = "creative_commons"
        item = self.prepare(content, rights={"entries": []}).materials[0]
        self.assertEqual(item["eligibility_status"], "reference_only")

    def test_search_result_or_unopened_url_cannot_self_certify_inspection(self):
        item = self.prepare(inspection={"entries": []}).materials[0]
        self.assertEqual(item["provenance_status"], "unmatched")
        self.assertNotEqual(item["eligibility_status"], "ready_to_use")

    def test_unknown_rights_is_reference_only(self):
        item = self.prepare(rights={"entries": []}).materials[0]
        self.assertEqual(item["rights_status"], "unknown")
        self.assertEqual(item["eligibility_status"], "reference_only")

    def test_permission_required_never_becomes_ready(self):
        manifest = rights_manifest()
        manifest["entries"][0]["rights_status"] = "permission_required"
        item = self.prepare(rights=manifest).materials[0]
        self.assertEqual(item["eligibility_status"], "permission_required")

    def test_evidence_material_requires_real_claim_and_evidence_binding(self):
        content = valid_material_content()
        content["materials"][0]["evidence_link_ids"] = ["E4"]
        with self.assertRaisesRegex(MaterialValidationError, "Evidence"):
            self.prepare(content)

    def test_illustration_cannot_masquerade_as_evidence(self):
        content = valid_material_content()
        item = content["materials"][0]
        item["intended_role"] = "illustration"
        item["illustrative_only"] = False
        with self.assertRaisesRegex(MaterialValidationError, "illustrative_only"):
            self.prepare(content)

    def test_duplicate_normalized_urls_are_rejected(self):
        content = valid_material_content()
        duplicate = copy.deepcopy(content["materials"][0])
        duplicate["source_url"] += "?utm_source=copy"
        content["materials"].append(duplicate)
        with self.assertRaisesRegex(MaterialValidationError, "重复"):
            self.prepare(content)

    def test_research_update_signal_blocks_silent_script_update(self):
        content = valid_material_content()
        content["research_update_signals"] = [{
            "beat_ids": ["B001"], "claim_ids": ["C1"],
            "reason": "新文件给出了冲突日期，需要先回到 Research。",
            "new_source_url": "https://example.net/update",
        }]
        package = self.prepare(content)
        self.assertTrue(package.research_update_required["required"])
        self.assertEqual(package.status, "research_update_required")

    def test_timeline_child_unknown_claim_is_rejected(self):
        content = valid_material_content()
        content["visual_specs"][0]["events"][0]["claim_ids"] = ["C404"]
        with self.assertRaisesRegex(MaterialValidationError, "不存在"):
            self.prepare(content)

    def test_timeline_child_unknown_or_wrong_claim_evidence_is_rejected(self):
        content = valid_material_content()
        content["visual_specs"][0]["events"][0]["evidence_link_ids"] = ["E404"]
        with self.assertRaisesRegex(MaterialValidationError, "不存在"):
            self.prepare(content)
        content = valid_material_content()
        content["visual_specs"][0]["events"][0]["evidence_link_ids"] = ["E3"]
        content["visual_specs"][0]["events"][0]["claim_ids"] = ["C1"]
        with self.assertRaisesRegex(MaterialValidationError, "对应"):
            self.prepare(content)

    def test_timeline_research_evidence_binding_mismatch_is_rejected(self):
        content = valid_material_content()
        content["visual_specs"][0]["events"][0]["evidence_link_ids"] = ["E1", "E2"]
        with self.assertRaisesRegex(MaterialValidationError, "Research timeline"):
            self.prepare(content)


if __name__ == "__main__":
    unittest.main()
