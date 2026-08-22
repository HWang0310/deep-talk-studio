import hashlib
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.edit_bridge_planner import build_visual_plan_placements, derive_placement_timing


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VisualPlanPlacementTests(unittest.TestCase):
    def test_ready_material_and_motion_use_only_plan_projected_real_times(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "official.png"; image.write_bytes(b"material")
            motion = root / "motion.mp4"; motion.write_bytes(b"motion")
            visual_plan = {"plan_digest": "p" * 64, "opportunities": [
                {"opportunity_id": "OP1", "beat_id": "B002", "visual_kind": "real_material", "visual_role": "evidence", "semantic_target": "官方页面", "source_binding": {"material_id": "M001"}, "timing_status": "ready", "placement_status": "ready", "actual_in_seconds": "10.0", "actual_out_seconds": "14.0", "duration_seconds": "4.0", "confidence": "high"},
                {"opportunity_id": "OP2", "beat_id": "B003", "visual_kind": "original_motion", "visual_role": "context", "semantic_target": "攻击链", "source_binding": {"scene_id": "S002"}, "timing_status": "ready", "placement_status": "ready", "actual_in_seconds": "20.0", "actual_out_seconds": "27.0", "duration_seconds": "7.0", "confidence": "high"},
            ]}
            material_view = {"items": [{"source_id": "M001", "title": "官方页面", "asset_type": "webpage", "local_path": str(image), "byte_size": image.stat().st_size, "sha256": digest(image), "production_status": "ready"}]}
            plan = {"scenes": [{"scene_id": "S002", "beat_id": "B003", "cue_id": "VC002", "source_visual_ids": ["V002"]}]}
            manifest = {"qa_status": "ready", "assets": [{"asset_kind": "motion_clip", "scene_id": "S002", "duration_seconds": 7, "output_path": str(motion), "byte_size": motion.stat().st_size, "sha256": digest(motion), "qa_status": "ready"}]}
            placements = build_visual_plan_placements(visual_plan, material_view, plan, manifest, [root])
            self.assertEqual([(p["source_kind"], p["semantic_in_seconds"], p["semantic_out_seconds"]) for p in placements], [
                ("real_image", "10.0", "14.0"), ("original_motion", "20.0", "27.0"),
            ])
            derived = derive_placement_timing(placements, ({"still_exposure_seconds": 7}, {"fps": 30}, "40"))
            self.assertTrue(all(item["placement_status"] == "ready" for item in derived.placements))

    def test_unplaced_plan_opportunity_cannot_be_promoted_by_a_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); image = root / "official.png"; image.write_bytes(b"material")
            visual_plan = {"plan_digest": "p" * 64, "opportunities": [
                {"opportunity_id": "OP1", "beat_id": "B011", "visual_kind": "real_material", "visual_role": "evidence", "semantic_target": "不安全 span", "source_binding": {"material_id": "M001"}, "timing_status": "unplaced", "placement_status": "unplaced", "actual_in_seconds": "", "actual_out_seconds": "", "duration_seconds": "", "confidence": "none"},
            ]}
            view = {"items": [{"source_id": "M001", "title": "官方页面", "asset_type": "webpage", "local_path": str(image), "byte_size": image.stat().st_size, "sha256": digest(image), "production_status": "ready"}]}
            placement = build_visual_plan_placements(visual_plan, view, {}, {}, [root])[0]
            self.assertEqual((placement["placement_status"], placement["timing_status"]), ("unplaced", "clear"))


if __name__ == "__main__":
    unittest.main()
