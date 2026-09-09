import unittest
from deeptalk_studio.edit_bridge_renderer import render_edit_bridge_csv,render_edit_bridge_markdown

class EditBridgeOutputTests(unittest.TestCase):
 def setUp(self):
  self.bridge={"visual_placements":[{"placement_id":"VP1","semantic_in_seconds":"2","semantic_out_seconds":"9","canonical_in_timecode":"00:00:02.000","canonical_out_timecode":"00:00:09.000","semantic_duration_seconds":"7","natural_duration_seconds":"","target_duration_seconds":"7","preview_effective_in_seconds":"2","preview_effective_out_seconds":"9","preview_in_frame":60,"preview_out_frame":270,"preview_in_frame_timecode":"Preview 00:00:02:00","preview_out_frame_timecode":"Preview 00:00:09:00","beat_id":"B1","cue_id":"VC1","scene_id":"","visual_role":"evidence","source_kind":"real_image","asset_type":"screenshot","safe_filename":"监管,文件.png","layout_mode":"full_screen_broll","placement_anchor":"日期","placement_status":"ready","timing_status":"clear","duration_status":"natural","confidence":"high","notes":[]}],"timing_conflicts":[],"alignment_gaps":[]}
 def test_csv_is_bom_rfc4180_and_marks_preview_columns(self):
  data=render_edit_bridge_csv(self.bridge)
  self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
  header=data.decode("utf-8-sig").splitlines()[0]
  self.assertIn("Preview IN frame",header); self.assertIn("canonical IN HH:MM:SS.mmm",header)
  self.assertIn('"监管,文件.png"',data.decode("utf-8-sig"))
 def test_markdown_is_readable_and_hides_paths_and_machine_matrices(self):
  text=render_edit_bridge_markdown(self.bridge)
  self.assertIn("可直接进入粗剪",text); self.assertNotIn("/Users/",text); self.assertNotIn("token",text.casefold())

if __name__=="__main__": unittest.main()
