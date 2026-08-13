import unittest
from deeptalk_studio.edit_bridge_planner import derive_placement_timing
from tests.test_duration_conflicts import placement,profiles
class AlignmentPlacementEvalTests(unittest.TestCase):
 def test_af_ag_ah_ai_policies(self):
  af=derive_placement_timing([placement("VP1","original_motion",2,5,6)],profiles());self.assertEqual(af.placements[0]["placement_status"],"ready");self.assertEqual(af.placements[0]["timing_status"],"warning")
  ah=derive_placement_timing([placement("VP1","real_image",2,5),placement("VP2","real_image",2,5)],profiles());self.assertTrue(all(p["placement_status"]=="needs_review" for p in ah.placements))
  ai=derive_placement_timing([placement("VP1","real_image",2,12)],profiles());self.assertEqual(ai.placements[0]["semantic_out_seconds"],"12")
if __name__=="__main__":unittest.main()
