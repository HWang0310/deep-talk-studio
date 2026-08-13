import tempfile,unittest
from pathlib import Path
from deeptalk_studio.edit_bridge_storage import EditBridgeStorageError,load_edit_bridge,save_edit_bridge
from deeptalk_studio.edit_bridge_planner import build_edit_bridge
from tests.test_edit_bridge_validation import bindings

class EditBridgeStorageTests(unittest.TestCase):
 def test_json_md_csv_save_exclusively(self):
  bridge=build_edit_bridge(bindings(),[],(),(),(),bridge_id="EB1",created_at="2026-08-13T12:00:00+08:00")
  with tempfile.TemporaryDirectory() as temp:
   paths=save_edit_bridge(bridge,Path(temp)); self.assertTrue(paths.csv_path.is_file()); self.assertEqual(load_edit_bridge(paths.json_path),bridge)
   with self.assertRaises(EditBridgeStorageError): save_edit_bridge(bridge,Path(temp))

if __name__=="__main__": unittest.main()
