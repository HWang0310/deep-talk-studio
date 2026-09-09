import copy,unittest
from deeptalk_studio.edit_bridge_storage import create_bridge_revision,resolve_adjustment_target

class EditBridgeRevisionTests(unittest.TestCase):
 def setUp(self): self.bridge={"bridge_id":"EB1","revision":1,"previous_revision":0,"created_at":"old","root_bindings":{"alignment_digest":"a"*64},"visual_placements":[{"placement_id":"VP1","safe_filename":"监管文件.png","source_kind":"real_image","placement_status":"ready","preview_effective_in_seconds":"2","preview_effective_out_seconds":"9"},{"placement_id":"VP2","safe_filename":"关系图.mp4","source_kind":"original_motion","placement_status":"ready","preview_effective_in_seconds":"10","preview_effective_out_seconds":"16"}],"preview_adjustments":[],"package_digest":"x"}
 def test_shorter_screenshot_creates_bridge_revision_only(self):
  resolution=resolve_adjustment_target(self.bridge,"这张监管文件截图时间短一点")
  revised=create_bridge_revision(self.bridge,resolution.adjustment,created_at="new")
  self.assertEqual(revised["revision"],2); self.assertEqual(revised["root_bindings"]["alignment_digest"],self.bridge["root_bindings"]["alignment_digest"]); self.assertEqual(self.bridge["revision"],1)
  self.assertLess(float(revised["visual_placements"][0]["preview_effective_out_seconds"]),9)
  self.assertEqual(revised["visual_placements"][0].get("semantic_out_seconds",""),self.bridge["visual_placements"][0].get("semantic_out_seconds",""))
 def test_keep_aroll_suppresses_only_preview_overlay(self):
  resolution=resolve_adjustment_target(self.bridge,"监管文件这里一直留真人")
  revised=create_bridge_revision(self.bridge,resolution.adjustment,created_at="new")
  self.assertFalse(revised["visual_placements"][0]["preview_enabled"])
  self.assertEqual(revised["visual_placements"][0]["placement_status"],"ready")
 def test_later_changes_effective_in_without_changing_semantic_window(self):
  resolution=resolve_adjustment_target(self.bridge,"关系图晚一点")
  revised=create_bridge_revision(self.bridge,resolution.adjustment,created_at="new")
  self.assertGreater(float(revised["visual_placements"][1]["preview_effective_in_seconds"]),10)
 def test_ambiguous_feedback_returns_readable_candidates_without_ids(self):
  bridge=copy.deepcopy(self.bridge); bridge["visual_placements"][1]["safe_filename"]="监管关系图.png"
  result=resolve_adjustment_target(bridge,"监管画面短一点")
  self.assertFalse(result.unique); self.assertEqual(len(result.candidates),2); self.assertNotIn("VP",str(result.candidates))

if __name__=="__main__": unittest.main()
