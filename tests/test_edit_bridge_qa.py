import copy,unittest
from deeptalk_studio.edit_bridge_qa import EditBridgeQAInputs,QACheck,run_edit_bridge_qa,validate_edit_bridge_qa
class EditBridgeQATests(unittest.TestCase):
 def inputs(self):
  checks=[QACheck("root","root_artifacts_revalidated",lambda:None,"invalid_root_binding"),QACheck("transcript","mapping_chunk_transcript_rederived",lambda:None,"invalid_transcript_chain"),QACheck("alignment","normalization_status_risk_rederived",lambda:None,"alignment_false_ready"),QACheck("placement","placement_files_and_timing_rederived",lambda:None,"invalid_placement_chain"),QACheck("preview","preview_manifest_and_audio_rederived",lambda:None,"preview_audio_presentation_mismatch")]
  return EditBridgeQAInputs(checks=checks,placements=[{"placement_id":"VP1","placement_status":"ready"},{"placement_id":"VP2","placement_status":"missing_asset"}],preview_used_placement_ids=["VP1"])
 def test_partial_success_is_warning_and_validates(self):
  inputs=self.inputs();qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"warnings");validate_edit_bridge_qa(qa,inputs)
 def test_unready_asset_used_by_preview_is_package_fail(self):
  inputs=self.inputs();inputs.preview_used_placement_ids=["VP2"];qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"fail");self.assertIn("preview_used_unready_asset",{i["issue_type"] for i in qa["issues"]})
 def test_same_duration_but_audio_reset_to_zero_is_sync_fail(self):
  inputs=self.inputs();inputs.checks[-1]=QACheck("preview","preview_manifest_and_audio_rederived",lambda:(_ for _ in ()).throw(ValueError("audio reset")),"preview_audio_presentation_mismatch");qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"fail");self.assertIn("preview_audio_presentation_mismatch",{i["issue_type"] for i in qa["issues"]})
 def test_missing_required_group_fails_closed(self):
  inputs=self.inputs();inputs.checks.pop()
  qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"fail");self.assertIn("missing_required_qa_group",{i["issue_type"] for i in qa["issues"]})
if __name__=="__main__":unittest.main()
