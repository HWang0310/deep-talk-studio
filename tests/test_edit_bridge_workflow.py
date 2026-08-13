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
 def test_full_workflow_calls_owned_stages_and_persists_every_success(self):
  calls=[]
  def stage(name):
   return lambda previous: calls.append((name,previous)) or {"stage":name}
  stages={name:stage(name) for name in ("import_media","extract_audio","build_mapping","plan_chunks","transcribe","build_transcript","build_alignment","build_bridge","render_preview","run_qa")}
  with tempfile.TemporaryDirectory() as temp:
   result=run_full_edit_bridge_workflow(stages,Path(temp))
   self.assertEqual([name for name,_ in calls],list(stages));self.assertIsNone(calls[0][1]);self.assertEqual(calls[1][1],{"stage":"import_media"});self.assertEqual(set(result.artifact_paths),set(stages));self.assertTrue(all(path.is_file() for path in result.artifact_paths.values()))
if __name__=="__main__":unittest.main()
