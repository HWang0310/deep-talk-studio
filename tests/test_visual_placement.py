import unittest
from deeptalk_studio.edit_bridge_planner import build_base_aroll_placement
from tests.edit_bridge_fixtures import media

class VisualPlacementTests(unittest.TestCase):
 def test_clean_aroll_is_layer_zero_full_duration(self):
  p=build_base_aroll_placement(media())
  self.assertEqual((p["placement_id"],p["track_order"]),("VP0000",0))
  self.assertEqual((p["semantic_in_seconds"],p["semantic_out_seconds"]),("0","20"))
  self.assertEqual(p["audio_policy"],"clean_aroll_primary")

if __name__=="__main__": unittest.main()
