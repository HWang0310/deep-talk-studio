import unittest
from deeptalk_studio.edit_bridge_planner import derive_placement_timing
from tests.test_duration_conflicts import placement, profiles

class PreviewAdjustmentTests(unittest.TestCase):
 def test_long_still_caps_preview_not_semantic_window(self):
  result=derive_placement_timing([placement("VP1","real_image",2,12)],profiles())
  p=result.placements[0]
  self.assertEqual(p["semantic_out_seconds"],"12")
  self.assertEqual(p["preview_effective_out_seconds"],"9")
  self.assertEqual(p["duration_status"],"long_still_warning")
 def test_next_overlay_takes_over_and_frames_ceil(self):
  result=derive_placement_timing([placement("VP1","real_image","2.001",8),placement("VP2","real_image","5.002",7)],profiles())
  self.assertEqual(result.placements[0]["preview_effective_out_seconds"],"5.002")
  self.assertEqual(result.placements[0]["preview_in_frame"],61)
  self.assertTrue(result.placements[0]["preview_in_frame_timecode"].startswith("Preview "))
 def test_user_override_is_structured_and_semantic_unchanged(self):
  result=derive_placement_timing([placement("VP1","real_image",2,12)],profiles(),user_adjustments=({"placement_id":"VP1","duration_seconds":"4","reason":"用户要求更短"},))
  self.assertEqual(result.placements[0]["preview_effective_out_seconds"],"6")
  self.assertEqual(result.placements[0]["semantic_out_seconds"],"12")

if __name__=="__main__": unittest.main()
