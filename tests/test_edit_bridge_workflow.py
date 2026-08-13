import tempfile,unittest
from pathlib import Path
from deeptalk_studio.edit_bridge_workflow import EditBridgeWorkflowInputs,run_edit_bridge_workflow,run_full_edit_bridge_workflow
from deeptalk_studio.edit_bridge_planner import build_base_aroll_placement
from tests.edit_bridge_fixtures import media

class EditBridgeWorkflowTests(unittest.TestCase):
 def test_video_aroll_writes_marker_outputs_with_partial_success(self):
  inputs=EditBridgeWorkflowInputs(media_kind="video",placements=[{"placement_id":"VP0000","placement_status":"ready"},{"placement_id":"VP0001","placement_status":"missing_asset"}],root_bindings={"chain":"valid"})
  with tempfile.TemporaryDirectory() as temp:
   result=run_edit_bridge_workflow(inputs,Path(temp));self.assertEqual(result.qa["package_gate_status"],"warnings");self.assertTrue(result.marker_csv_path.is_file());self.assertEqual(result.summary.ready_count,1)
 def test_full_workflow_delegates_only_to_concrete_session_owner(self):
  from unittest.mock import patch
  with patch("deeptalk_studio.edit_bridge_session.run_real_edit_bridge_session",return_value="done") as owner:
   result=run_full_edit_bridge_workflow("inputs","provider",clock="clock",id_factory="ids",renderer="renderer")
  self.assertEqual(result,"done");owner.assert_called_once_with("inputs","provider",clock="clock",id_factory="ids",renderer="renderer")
if __name__=="__main__":unittest.main()
