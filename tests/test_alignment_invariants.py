import copy,unittest
from deeptalk_studio.canonical_time import format_canonical_timecode
from deeptalk_studio.edit_bridge_planner import derive_placement_timing
from tests.test_duration_conflicts import placement,profiles
class AlignmentInvariantTests(unittest.TestCase):
 def test_fps_neutral_canonical_time_and_warning_readiness(self):
  self.assertEqual(format_canonical_timecode("90061.1234"),"25:01:01.123");r=derive_placement_timing([placement("VP1","original_motion",2,5,6)],profiles());self.assertEqual(r.placements[0]["placement_status"],"ready")
 def test_unplaced_preview_frame_forbidden_by_builder(self):
  from deeptalk_studio.edit_bridge_planner import EditBridgePlanningError,build_edit_bridge
  from tests.test_edit_bridge_validation import bindings
  p={"placement_id":"VP1","placement_status":"unplaced","preview_in_frame":0,"preview_out_frame":1}
  with self.assertRaises(EditBridgePlanningError):build_edit_bridge(bindings(),[p],(),(),(),bridge_id="EB",created_at="x")
if __name__=="__main__":unittest.main()
