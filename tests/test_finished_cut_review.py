import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.finished_cut_review import (
    FinishedCutReviewError,
    build_finished_cut_review,
    build_production_feedback,
    inspect_finished_cut_media,
    sequence_is_discriminative,
    write_finished_cut_feedback,
)


def edit_map():
    return {
        "artifact_version": "edit-map/1",
        "map_digest": "a" * 64,
        "asset_manifest_digest": "b" * 64,
        "rows": [
            {
                "sequence": 1,
                "span_id": "ST001",
                "actual_start_seconds": "10.0",
                "actual_end_seconds": "20.0",
                "decision": "MG_MOTION",
                "asset_filename": "MG_01_时间线.mp4",
                "spoken_summary": "用结构动画解释时间变化。",
                "placement_advice": "全屏覆盖，结束后回到人物。",
            },
            {
                "sequence": 2,
                "span_id": "ST002",
                "actual_start_seconds": "20.0",
                "actual_end_seconds": "30.0",
                "decision": "KEEP_A_ROLL",
                "asset_filename": "",
                "spoken_summary": "核心判断由讲述者表达。",
                "placement_advice": "保持人物画面。",
            },
        ],
    }


def manifest():
    return {
        "artifact_version": "visual-asset-manifest/1",
        "manifest_digest": "b" * 64,
        "assets": [
            {
                "filename": "MG_01_时间线.mp4",
                "asset_class": "MG_MOTION",
                "sha256": "c" * 64,
                "qa_status": "ready",
            }
        ],
    }


def finished_cut():
    return {
        "sha256": "d" * 64,
        "duration_seconds": "45.0",
        "resolution": {"width": 1920, "height": 1080},
        "frame_rate": "60/1",
        "streams": ["video", "audio"],
    }


def unknown_observation():
    return {
        "asset_filename": "MG_01_时间线.mp4",
        "status": "UNKNOWN",
        "actual_start_seconds": None,
        "actual_end_seconds": None,
        "presentation": "UNKNOWN",
        "evidence": "帧匹配不足，不能判断。",
    }


class FinishedCutReviewContractTests(unittest.TestCase):
    def test_unknown_asset_observation_never_becomes_used_or_not_used(self):
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [unknown_observation()])
        row = review["planned_vs_actual"][0]
        self.assertEqual(row["actual_status"], "UNKNOWN")
        selfIsNone = self.assertIsNone
        selfIsNone(row["actual_start_seconds"])
        selfIsNone(row["timing_offset_seconds"])

    def test_used_asset_compares_finished_cut_actual_time_to_planned_time(self):
        observed = dict(unknown_observation(), status="USED", actual_start_seconds="10.2", actual_end_seconds="19.6", presentation="full_screen", usage_mode="shortened")
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [observed])
        row = review["planned_vs_actual"][0]
        self.assertEqual(row["actual_status"], "USED")
        self.assertEqual(row["actual_start_seconds"], "10.2")
        self.assertEqual(row["timing_offset_seconds"], "0.2")
        self.assertEqual(row["actual_presentation"], "full_screen")
        self.assertEqual(row["actual_usage_mode"], "shortened")

    def test_explicit_not_used_asset_keeps_no_actual_timing(self):
        observed = dict(unknown_observation(), status="NOT_USED", presentation="UNKNOWN", usage_mode="UNKNOWN")
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [observed])
        row = review["planned_vs_actual"][0]
        self.assertEqual(row["actual_status"], "NOT_USED")
        self.assertIsNone(row["actual_start_seconds"])
        self.assertIsNone(row["actual_end_seconds"])
        self.assertIsNone(row["timing_offset_seconds"])

    def test_creator_override_is_an_observation_not_an_error(self):
        observed = dict(unknown_observation(), status="USED", actual_start_seconds="10.0", actual_end_seconds="16.0", presentation="partial_use")
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [observed])
        self.assertEqual(review["creator_override_observations"][0]["classification"], "USER_EDIT_OBSERVATION")
        self.assertEqual(review["creator_override_observations"][0]["asset_filename"], "MG_01_时间线.mp4")

    def test_shortened_full_screen_asset_is_still_a_creator_override(self):
        observed = dict(unknown_observation(), status="USED", actual_start_seconds="10.0", actual_end_seconds="18.0", presentation="full_screen", usage_mode="shortened")
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [observed])
        self.assertEqual(review["creator_override_observations"][0]["actual_usage_mode"], "shortened")

    def test_missing_edit_map_manifest_binding_is_rejected(self):
        broken = edit_map(); broken["asset_manifest_digest"] = "z" * 64
        with self.assertRaisesRegex(FinishedCutReviewError, "Asset Manifest"):
            build_finished_cut_review(broken, manifest(), finished_cut(), [])

    def test_episode_observation_can_only_create_candidate_rule(self):
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [unknown_observation()], episode_observations=[
            {
                "category": "timing_feedback",
                "finding": "首条动画实际比计划晚 0.2 秒进入。",
                "confidence": "medium",
                "evidence_episode": "EP-TEST",
            }
        ])
        feedback = build_production_feedback(review)
        self.assertEqual(feedback["candidate_product_rules"][0]["rule_status"], "CANDIDATE_PRODUCT_RULE")
        self.assertNotIn("accepted_product_rules", feedback)
        self.assertNotIn("global_strategy", feedback)

    def test_review_does_not_contain_virality_prediction_or_creator_score(self):
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [])
        encoded = json.dumps(review, ensure_ascii=False).lower()
        self.assertNotIn("views", encoded)
        self.assertNotIn("virality", encoded)
        self.assertNotIn("score", encoded)


class FinishedCutArtifactWriterTests(unittest.TestCase):
    def test_writer_creates_only_review_json_and_local_markdown(self):
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [])
        feedback = build_production_feedback(review)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            before = {item.relative_to(root) for item in root.rglob("*")}
            paths = write_finished_cut_feedback(root, review, feedback, episode_title="测试 Episode")
            self.assertEqual(paths["review_json"].parent.name, "_DeepTalk记录")
            self.assertEqual(paths["feedback_json"].parent.name, "_DeepTalk记录")
            self.assertEqual(paths["review_markdown"].parent.name, "10_成片")
            self.assertTrue(paths["review_markdown"].is_file())
            after = {item.relative_to(root) for item in root.rglob("*")}
            additions = after - before
            self.assertFalse(any(path.suffix.lower() in {".mp4", ".mov", ".fcpxml", ".xml"} for path in additions))

    def test_writer_rejects_feedback_from_a_different_review(self):
        review = build_finished_cut_review(edit_map(), manifest(), finished_cut(), [])
        feedback = dict(build_production_feedback(review))
        feedback["review_digest"] = "e" * 64
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(FinishedCutReviewError, "未绑定"):
                write_finished_cut_feedback(Path(raw), review, feedback, episode_title="测试 Episode")


class FinishedCutMediaInspectionTests(unittest.TestCase):
    def test_probe_is_read_only_and_returns_media_sha_for_existing_file(self):
        with tempfile.TemporaryDirectory() as raw:
            video = Path(raw) / "not-a-video.mp4"
            video.write_bytes(b"immutable-input")
            before = hashlib.sha256(video.read_bytes()).hexdigest()
            with self.assertRaises(FinishedCutReviewError):
                inspect_finished_cut_media(video)
            self.assertEqual(hashlib.sha256(video.read_bytes()).hexdigest(), before)

    def test_static_or_near_static_asset_sequence_is_not_discriminative_enough_to_claim_use(self):
        self.assertFalse(sequence_is_discriminative([bytes([20]) * 576, bytes([20]) * 576]))


class FinishedCutDocumentationTests(unittest.TestCase):
    def test_docs_name_finished_cut_review_as_read_only_after_human_nle_assembly(self):
        repo = Path(__file__).resolve().parents[1]
        corpus = "\n".join((repo / path).read_text(encoding="utf-8") for path in (
            "README.md", "PRD.md", "ROADMAP.md", "AGENTS.md", "docs/FINISHED_CUT_REVIEW_CONTRACT.md",
        ))
        self.assertIn("Finished Cut Review", corpus)
        self.assertIn("Production Feedback Loop", corpus)
        self.assertIn("不修改成片", corpus)


if __name__ == "__main__":
    unittest.main()
