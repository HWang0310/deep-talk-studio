import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.asset_pack_workflow import (
    AssetPackWorkflowError,
    build_production_asset_pack,
)


NOW = "2026-08-24T10:00:00+08:00"


def accepted_roots():
    return {
        "clean_aroll_gate_status": "accepted",
        "alignment_digest": "a" * 64,
        "transcript_digest": "b" * 64,
        "timing_provenance": "actual_aroll_alignment",
    }


def spans():
    return [
        {
            "span_id": "ST001",
            "actual_start_seconds": "0.0",
            "actual_end_seconds": "12.4",
            "summary": "开头 Hook，先让观众理解这个现象为什么反常。",
            "visual_eligibility": "safe",
        },
        {
            "span_id": "ST002",
            "actual_start_seconds": "12.4",
            "actual_end_seconds": "20.0",
            "summary": "用票房反差解释为什么值得继续听。",
            "visual_eligibility": "safe",
        },
    ]


def plan(decision="MG_MOTION"):
    return {
        "alignment_digest": "a" * 64,
        "opportunities": [
            {
                "opportunity_id": "VO001",
                "span_id": "ST001",
                "decision": "KEEP_A_ROLL",
                "why_visual": "开头需要先保留讲述者。",
                "review_requirement": "not_needed",
            },
            {
                "opportunity_id": "VO002",
                "span_id": "ST002",
                "decision": decision,
                "why_visual": "票房反差适合用结构画面解释。",
                "review_requirement": "not_needed",
            },
        ],
    }


def ready_asset(path):
    path.write_bytes(b"qa-ready-asset")
    return {
        "opportunity_id": "VO002",
        "asset_class": "MG_MOTION",
        "filename": "MG_01_票房反差.mp4",
        "local_path": str(path),
        "qa_status": "ready",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "provenance": "原创结构动画，事实绑定已通过。",
        "placement_advice": "从这一刻开始全屏覆盖，结束后回到人物。",
    }


class AssetPackWorkflowTests(unittest.TestCase):
    def test_requires_accepted_clean_aroll_alignment_before_formal_map(self):
        with tempfile.TemporaryDirectory() as raw:
            roots = accepted_roots(); roots["clean_aroll_gate_status"] = "needs_manual_cleanup"
            with self.assertRaisesRegex(AssetPackWorkflowError, "Clean A-roll Alignment"):
                build_production_asset_pack(roots, spans(), plan(), [], episode_root=Path(raw), created_at=NOW)

    def test_map_contains_keep_and_actual_ready_asset_row(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); asset = ready_asset(root / "source.mp4")
            result = build_production_asset_pack(accepted_roots(), spans(), plan(), [asset], episode_root=root / "episode", created_at=NOW)
            rows = result.machine_map["rows"]
            self.assertEqual(rows[0]["decision"], "KEEP_A_ROLL")
            self.assertEqual(rows[0]["actual_start_seconds"], "0.0")
            self.assertEqual(rows[1]["decision"], "MG_MOTION")
            self.assertEqual(rows[1]["actual_start_seconds"], "12.4")
            self.assertEqual(rows[1]["asset_filename"], "MG_01_票房反差.mp4")
            self.assertTrue(result.markdown_path.is_file())
            self.assertTrue(result.csv_path.is_file())
            self.assertTrue(result.json_path.is_file())

    def test_missing_or_failed_nonkeep_asset_falls_back_without_broken_instruction(self):
        with tempfile.TemporaryDirectory() as raw:
            result = build_production_asset_pack(accepted_roots(), spans(), plan(), [], episode_root=Path(raw), created_at=NOW)
            row = result.machine_map["rows"][1]
            self.assertEqual(row["decision"], "KEEP_A_ROLL")
            self.assertEqual(row["asset_filename"], "")
            self.assertEqual(row["fallback_outcome"], "KEEP_A_ROLL")

    def test_no_final_video_or_nle_project_is_default_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); asset = ready_asset(root / "source.mp4")
            result = build_production_asset_pack(accepted_roots(), spans(), plan(), [asset], episode_root=root / "episode", created_at=NOW)
            self.assertEqual(result.delivery_mode, "asset_pack")
            self.assertFalse((root / "episode" / "10_成片" / "final_video.mp4").exists())
            self.assertFalse(any(path.suffix in {".fcpxml", ".xml"} for path in (root / "episode").rglob("*")))

    def test_machine_map_is_digest_bound_and_human_map_hides_machine_hashes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); asset = ready_asset(root / "source.mp4")
            result = build_production_asset_pack(accepted_roots(), spans(), plan(), [asset], episode_root=root / "episode", created_at=NOW)
            stored = json.loads(result.json_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["artifact_version"], "edit-map/1")
            self.assertEqual(len(stored["map_digest"]), 64)
            self.assertNotIn("sha256", result.markdown_path.read_text(encoding="utf-8").lower())


class AssetPackDocumentationTests(unittest.TestCase):
    def test_primary_docs_make_asset_pack_default_and_prohibit_auto_final_edit(self):
        repo = Path(__file__).resolve().parents[1]
        corpus = "\n".join((repo / path).read_text(encoding="utf-8") for path in (
            "README.md", "PRD.md", "ROADMAP.md", "AGENTS.md", "docs/EDIT_BRIDGE_CONTRACT.md",
        ))
        self.assertIn("Asset Pack + Edit Map", corpus)
        self.assertIn("不替用户剪辑最终视频", corpus)
        self.assertNotIn("V1.0 目标输出是 `reviewed Script + Clean A-roll + Real Material + Original Motion + Basic Subtitle → 完整可观看粗剪`", corpus)


if __name__ == "__main__":
    unittest.main()
