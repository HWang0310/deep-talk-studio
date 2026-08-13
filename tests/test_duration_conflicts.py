import copy, unittest
from deeptalk_studio.edit_bridge_planner import derive_placement_timing
from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.rough_cut_profile import load_aligned_preview_profile, load_rough_cut_profile

def profiles(): return (load_rough_cut_profile(load_material_profile()),load_aligned_preview_profile(),"20")
def placement(pid,kind,start,end,natural=""):
 return {"placement_id":pid,"source_kind":kind,"placement_status":"ready","semantic_in_seconds":str(start),"semantic_out_seconds":str(end),"natural_duration_seconds":str(natural),"timing_status":"clear","timing_conflict_ids":[],"duration_status":"natural","notes":[],"preview_adjustment_id":""}

class DurationConflictTests(unittest.TestCase):
 def test_reliable_motion_mismatch_warns_without_cancelling_ready(self):
  result=derive_placement_timing([placement("VP1","original_motion",2,5,6)],profiles())
  self.assertEqual(result.placements[0]["placement_status"],"ready")
  self.assertEqual(result.placements[0]["timing_status"],"warning")
  self.assertEqual(result.conflicts[0]["conflict_class"],"timing_warning")
 def test_same_start_is_selection_blocker_not_id_tiebreak(self):
  result=derive_placement_timing([placement("VP1","real_image",2,5),placement("VP2","original_motion",2,5,3)],profiles())
  self.assertTrue(all(p["placement_status"]=="needs_review" for p in result.placements))
  self.assertEqual(result.conflicts[0]["conflict_type"],"same_start_selection_ambiguity")
 def test_out_of_bounds_rejects_instead_of_clamping(self):
  result=derive_placement_timing([placement("VP1","real_image",19,21)],profiles())
  self.assertEqual(result.placements[0]["placement_status"],"rejected")
  self.assertEqual(result.placements[0]["timing_status"],"blocking")

if __name__=="__main__": unittest.main()
