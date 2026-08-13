import copy,unittest
from deeptalk_studio.edit_bridge_planner import EditBridgePlanningError,build_edit_bridge
from deeptalk_studio.edit_bridge_validation import EditBridgeValidationError,validate_edit_bridge

def bindings(): return {k:k[0]*64 for k in ("narration_media_digest","extracted_audio_digest","timestamp_mapping_digest","chunk_plan_digest","transcript_digest","script_content_digest","research_digest","material_package_digest","material_view_digest","production_plan_digest","motion_manifest_digest","production_qa_digest","alignment_digest","alignment_profile_digest","rough_cut_profile_digest","aligned_preview_profile_digest","subtitle_artifact_digest","subtitle_profile_digest")}

class EditBridgeValidationTests(unittest.TestCase):
 def setUp(self):
  self.p={"artifact_version":"visual-placement/1","placement_id":"VP0000","track_order":0,"source_kind":"clean_aroll","source_id":"NM1","safe_filename":"a.mp4","beat_id":"","cue_id":"","scene_id":"","visual_role":"base","asset_type":"clean_aroll","placement_anchor":"","semantic_in_seconds":"0","semantic_out_seconds":"20","semantic_duration_seconds":"20","canonical_in_timecode":"00:00:00.000","canonical_out_timecode":"00:00:20.000","natural_duration_seconds":"20","target_duration_seconds":"20","source_clip_in_seconds":"","source_clip_out_seconds":"","preview_effective_in_seconds":"0","preview_effective_out_seconds":"20","preview_in_frame":0,"preview_out_frame":600,"preview_in_frame_timecode":"Preview 00:00:00:00","preview_out_frame_timecode":"Preview 00:00:20:00","preview_adjustment_id":"","preview_enabled":True,"layout_mode":"full_screen_aroll","layout_source":"profile_default","audio_policy":"clean_aroll_primary","placement_status":"ready","timing_status":"clear","duration_status":"natural","confidence":"high","notes":[],"timing_conflict_ids":[],"local_path":"/safe/a.mp4","byte_size":1,"sha256":"a"*64}
  self.bridge=build_edit_bridge(bindings(),[self.p],(),(),(),bridge_id="EB1",created_at="2026-08-13T12:00:00+08:00")
 def test_valid_bridge_and_digest_pass(self): validate_edit_bridge(self.bridge,bindings(),[self.p],(),(),())
 def test_status_time_profile_and_digest_tamper_fail(self):
  for path,value in (("qa_state","pass"),("package_digest","x"*64)):
   forged=copy.deepcopy(self.bridge); forged[path]=value
   with self.assertRaises(EditBridgeValidationError): validate_edit_bridge(forged,bindings(),[self.p],(),(),())
 def test_unready_placement_cannot_carry_preview_frames(self):
  p=copy.deepcopy(self.p); p["placement_status"]="unplaced"
  with self.assertRaises(EditBridgePlanningError): build_edit_bridge(bindings(),[p],(),(),(),bridge_id="EB2",created_at="x")

if __name__=="__main__": unittest.main()
