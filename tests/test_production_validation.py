import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import prepare_codex_materials, run_codex_material_review
from deeptalk_studio.production_profile import ProductionValidationError
from deeptalk_studio.production_validation import (
    validate_display_text,
    validate_production_input,
    validate_render_asset,
)
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


def passing_review():
    return {
        "issues": [],
        "checks": [
            {"check_name": name, "outcome": "pass", "reason": "正式检查通过。"}
            for name in MATERIAL_REVIEW_CHECK_NAMES
        ],
        "overall_notes": "通过。",
    }


class ProductionValidationTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.material_profile = load_material_profile()

    def stored_package(self, root, review=None, content=None):
        prepared = prepare_codex_materials(
            content or valid_material_content(), self.script, self.report,
            root / "packages", root / "assets", self.material_profile,
            inspection_manifest(), rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-production",
        )
        reviewed = run_codex_material_review(
            review or passing_review(), prepared.package, self.script, self.report,
            root / "packages", self.material_profile,
            created_at="2026-08-11T11:00:00+08:00", review_id="MRV-production",
        )
        return prepared, reviewed

    def test_reviewed_and_reviewed_with_warnings_are_allowed_after_canonical_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, reviewed = self.stored_package(root)
            loaded = validate_production_input(
                reviewed.paths.json, self.script, self.report, self.material_profile
            )
            self.assertEqual(loaded.status, "reviewed")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review = passing_review()
            review["issues"] = [{
                "issue_type": "permission_needed", "material_ids": ["M001"],
                "visual_ids": [], "cue_ids": ["VC001"],
                "explanation": "需要额外人工确认。", "suggested_fix": "使用原创图。",
            }]
            for check in review["checks"]:
                if check["check_name"] == "rights_reuse":
                    check["outcome"] = "fail"
            _, reviewed = self.stored_package(root, review=review)
            loaded = validate_production_input(
                reviewed.paths.json, self.script, self.report, self.material_profile
            )
            self.assertEqual(loaded.status, "reviewed_with_warnings")

    def test_blocked_research_update_and_draft_are_rejected_before_renderer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared = prepare_codex_materials(
                valid_material_content(), self.script, self.report,
                root / "packages", root / "assets", self.material_profile,
                inspection_manifest(), rights_manifest(),
                created_at="2026-08-11T10:00:00+08:00", package_id="MAT-draft",
            )
            with self.assertRaisesRegex(ProductionValidationError, "reviewed"):
                validate_production_input(
                    prepared.paths.json, self.script, self.report, self.material_profile
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review = passing_review()
            review["issues"] = [{
                "issue_type": "fabricated_source", "material_ids": [], "visual_ids": [],
                "cue_ids": [], "explanation": "包级来源无效。", "suggested_fix": "重做。",
            }]
            for check in review["checks"]:
                if check["check_name"] == "provenance_integrity":
                    check["outcome"] = "fail"
            _, reviewed = self.stored_package(root, review=review)
            with self.assertRaisesRegex(ProductionValidationError, "blocked"):
                validate_production_input(
                    reviewed.paths.json, self.script, self.report, self.material_profile
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = valid_material_content()
            content["research_update_signals"] = [{
                "beat_ids": ["B001"], "claim_ids": ["C1"], "reason": "日期冲突",
                "new_source_url": "https://example.net/update",
            }]
            _, reviewed = self.stored_package(root, content=content)
            with self.assertRaisesRegex(ProductionValidationError, "Research"):
                validate_production_input(
                    reviewed.paths.json, self.script, self.report, self.material_profile
                )

    def test_missing_canonical_provenance_or_fake_reviewed_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, reviewed = self.stored_package(root)
            (reviewed.paths.json.parent / "material-rights-for-r0001.json").unlink()
            with self.assertRaisesRegex(ProductionValidationError, "canonical"):
                validate_production_input(
                    reviewed.paths.json, self.script, self.report, self.material_profile
                )

    def test_render_asset_checks_root_sha_size_type_and_eligibility(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "V001.svg"
            payload = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
            path.write_bytes(payload)
            asset = {
                "visual_id": "V001", "local_path": str(path), "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(), "render_status": "rendered",
                "eligibility_status": "ready_to_use",
            }
            self.assertEqual(
                validate_render_asset(asset, root, generated_visual=True), path.resolve()
            )
            path.write_bytes(payload + b"tampered")
            with self.assertRaisesRegex(ProductionValidationError, "SHA|大小"):
                validate_render_asset(asset, root, generated_visual=True)

    def test_render_asset_rejects_missing_path_traversal_and_unsafe_statuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outside = root.parent / "outside-production.png"
            outside.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            try:
                asset = {
                    "material_id": "M001", "local_path": str(outside),
                    "byte_size": outside.stat().st_size,
                    "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                    "eligibility_status": "ready_to_use",
                }
                with self.assertRaisesRegex(ProductionValidationError, "允许的素材目录"):
                    validate_render_asset(asset, root)
                asset["local_path"] = str(root / "missing.png")
                with self.assertRaisesRegex(ProductionValidationError, "不存在"):
                    validate_render_asset(asset, root)
                asset["eligibility_status"] = "reference_only"
                with self.assertRaisesRegex(ProductionValidationError, "reference_only"):
                    validate_render_asset(asset, root)
            finally:
                outside.unlink(missing_ok=True)

    def test_display_text_allows_editorial_heading_and_grounded_date(self):
        validate_display_text(
            {"text": "发生了什么", "origin": "machine_editorial", "text_kind": "editorial", "claim_ids": [],
             "evidence_link_ids": []}, self.report
        )
        validate_display_text(
            {"text": "2026-08-09", "origin": "research_fact", "text_kind": "factual",
             "claim_ids": ["C1"], "evidence_link_ids": ["E1"]}, self.report,
            additional_grounded_texts=("2026-08-09",),
        )

    def test_display_text_rejects_unsupported_number_date_and_bar_extra_number(self):
        for text in ("2026-08-10", "9，同比增长 999%"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ProductionValidationError, "屏幕文字"):
                    validate_display_text(
                        {"text": text, "origin": "research_fact", "text_kind": "factual", "claim_ids": ["C1"],
                         "evidence_link_ids": ["E1"]}, self.report
                    )

    def test_display_text_can_use_an_exact_approved_timeline_entry_as_extra_grounding(self):
        entry = {"text": "2026-05-08", "origin": "research_fact", "text_kind": "factual", "claim_ids": ["C1"],
                 "evidence_link_ids": ["E1"]}
        validate_display_text(
            entry, self.report, additional_grounded_texts=("2026-05-08",)
        )
        with self.assertRaisesRegex(ProductionValidationError, "999"):
            validate_display_text(
                dict(entry, text="2026-05-08 / 999"), self.report,
                additional_grounded_texts=("2026-05-08",),
            )

    def test_display_text_rejects_nonnumeric_fact_unrelated_claim_and_fake_caption(self):
        cases = [
            {"text": "公司已经承认全部责任", "origin": "research_fact", "text_kind": "factual",
             "claim_ids": ["C1"], "evidence_link_ids": ["E1"]},
            {"text": "监管机构认定违法", "origin": "material_caption", "text_kind": "factual",
             "claim_ids": ["C1"], "evidence_link_ids": ["E1"]},
        ]
        for entry in cases:
            with self.subTest(text=entry["text"]):
                with self.assertRaisesRegex(ProductionValidationError, "语义|回查"):
                    validate_display_text(entry, self.report)

    def test_only_versioned_machine_editorial_phrases_can_be_unbound(self):
        for text in ("关键时间点", "要点对照", "真人口播"):
            validate_display_text(
                {"text": text, "origin": "machine_editorial", "text_kind": "editorial",
                 "claim_ids": [], "evidence_link_ids": []}, self.report,
            )
        with self.assertRaisesRegex(ProductionValidationError, "白名单"):
            validate_display_text(
                {"text": "公司已经承认全部责任", "origin": "machine_editorial",
                 "text_kind": "editorial", "claim_ids": [], "evidence_link_ids": []},
                self.report,
            )
        with self.assertRaisesRegex(ProductionValidationError, "白名单"):
            validate_display_text(
                {"text": "三种事故报告机制", "origin": "machine_editorial",
                 "text_kind": "editorial", "claim_ids": [], "evidence_link_ids": []},
                self.report,
            )

    def test_raw_pdf_is_provenance_only_and_cannot_enter_image_renderer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "official.pdf"
            payload = b"%PDF-1.7\nsynthetic"
            path.write_bytes(payload)
            asset = {
                "material_id": "M001", "local_path": str(path), "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(), "eligibility_status": "ready_to_use",
            }
            with self.assertRaisesRegex(ProductionValidationError, "PDF"):
                validate_render_asset(asset, root)


if __name__ == "__main__":
    unittest.main()
