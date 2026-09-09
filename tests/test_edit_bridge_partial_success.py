import tempfile,unittest
from pathlib import Path
from deeptalk_studio.edit_bridge_workflow import EditBridgeWorkflowInputs,run_edit_bridge_workflow
class EditBridgePartialSuccessTests(unittest.TestCase):
 def test_audio_only_keeps_marker_package_and_no_full_preview(self):
  with tempfile.TemporaryDirectory() as temp:
   result=run_edit_bridge_workflow(EditBridgeWorkflowInputs("audio",[{"placement_id":"VP0000","placement_status":"ready"}],{"chain":"valid"}),Path(temp));self.assertIsNone(result.preview_path);self.assertEqual(result.qa["package_gate_status"],"warnings")
if __name__=="__main__":unittest.main()
