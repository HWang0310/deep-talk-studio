import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.edit_bridge_planner import build_visual_placements
from tests.edit_bridge_fixtures import alignment, material_view, media, write_png


class RealMaterialPlacementTests(unittest.TestCase):
    def test_ready_real_image_reuses_cue_and_contains(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,size,digest=write_png(root)
            placements=build_visual_placements(alignment(),material_view(path,size,digest),{}, {},media(),[root])
            p=placements[0]
            self.assertEqual((p["source_kind"],p["cue_id"]),("real_image","VC001"))
            self.assertEqual((p["placement_status"],p["layout_mode"]),("ready","full_screen_broll"))

    def test_video_without_source_range_keeps_narration_window_but_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,size,digest=write_png(root,"video.mp4")
            view=material_view(path,size,digest,"video")
            p=build_visual_placements(alignment(),view,{}, {},media(),[root])[0]
            self.assertEqual(p["placement_status"],"clip_selection_needed")
            self.assertEqual(p["semantic_in_seconds"],"2")
            self.assertEqual(p["source_clip_in_seconds"],"")
            self.assertEqual(p["audio_policy"],"mute_source_keep_aroll")

    def test_missing_asset_is_isolated(self):
        view={"items":[{"source_kind":"material","source_id":"M001","cue_ids":["VC001"],"title":"x","caption":"x","local_path":"","byte_size":0,"sha256":"","production_status":"missing_asset","asset_type":"document_screenshot","video_reference":{"start_seconds":0,"end_seconds":0}}]}
        p=build_visual_placements(alignment(),view,{}, {},media(),[])[0]
        self.assertEqual(p["placement_status"],"missing_asset")
        self.assertEqual(p["semantic_in_seconds"],"2")


if __name__=="__main__": unittest.main()
