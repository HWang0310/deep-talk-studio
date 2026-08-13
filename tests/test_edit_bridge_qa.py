import copy,unittest
from deeptalk_studio.edit_bridge_qa import EditBridgeQAInputs,run_edit_bridge_qa,validate_edit_bridge_qa
class EditBridgeQATests(unittest.TestCase):
 def inputs(self):return EditBridgeQAInputs(root_valid=True,transcript_valid=True,alignment_valid=True,placements=[{"placement_id":"VP1","placement_status":"ready"},{"placement_id":"VP2","placement_status":"missing_asset"}],preview_used_placement_ids=["VP1"],audio_presentation_valid=True)
 def test_partial_success_is_warning_and_validates(self):
  inputs=self.inputs();qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"warnings");validate_edit_bridge_qa(qa,inputs)
 def test_unready_asset_used_by_preview_is_package_fail(self):
  inputs=self.inputs();inputs.preview_used_placement_ids=["VP2"];qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"fail");self.assertIn("preview_used_unready_asset",{i["issue_type"] for i in qa["issues"]})
 def test_same_duration_but_audio_reset_to_zero_is_sync_fail(self):
  inputs=self.inputs();inputs.audio_presentation_valid=False;qa=run_edit_bridge_qa(inputs);self.assertEqual(qa["package_gate_status"],"fail");self.assertIn("preview_audio_presentation_mismatch",{i["issue_type"] for i in qa["issues"]})
if __name__=="__main__":unittest.main()
