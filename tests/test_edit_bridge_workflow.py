import tempfile,unittest
from pathlib import Path
from deeptalk_studio.edit_bridge_workflow import EditBridgeWorkflowInputs,run_edit_bridge_workflow

class EditBridgeWorkflowTests(unittest.TestCase):
 def test_video_aroll_writes_marker_outputs_with_partial_success(self):
  inputs=EditBridgeWorkflowInputs(media_kind="video",placements=[{"placement_id":"VP0000","placement_status":"ready"},{"placement_id":"VP0001","placement_status":"missing_asset"}],root_bindings={"chain":"valid"})
  with tempfile.TemporaryDirectory() as temp:
   result=run_edit_bridge_workflow(inputs,Path(temp));self.assertEqual(result.qa["package_gate_status"],"warnings");self.assertTrue(result.marker_csv_path.is_file());self.assertEqual(result.summary.ready_count,1)
if __name__=="__main__":unittest.main()
