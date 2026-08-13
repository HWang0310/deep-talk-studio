import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.edit_bridge_planner import EditBridgePlanningError, build_visual_placements
from tests.edit_bridge_fixtures import alignment, media, production_motion


class MotionPlacementTests(unittest.TestCase):
    def test_qa_ready_motion_reuses_scene_payload_without_research_reinterpretation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/"motion.mp4"; data=b"motion"; path.write_bytes(data)
            import hashlib
            plan,manifest=production_motion(path,len(data),hashlib.sha256(data).hexdigest())
            p=build_visual_placements(alignment(),{"items":[]},plan,manifest,media(),[root])[0]
            self.assertEqual((p["source_kind"],p["scene_id"]),("original_motion","SC001"))
            self.assertEqual(p["placement_status"],"ready")
            self.assertEqual(p["natural_duration_seconds"],"6")

    def test_manifest_sha_tamper_rejects_motion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/"motion.mp4"; path.write_bytes(b"motion")
            plan,manifest=production_motion(path,6,"x"*64)
            with self.assertRaises(EditBridgePlanningError):
                build_visual_placements(alignment(),{"items":[]},plan,manifest,media(),[root])


if __name__=="__main__": unittest.main()
