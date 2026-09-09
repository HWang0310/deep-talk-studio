import copy,unittest
from deeptalk_studio.edit_bridge_qa import EditBridgeQAError,validate_edit_bridge_qa
from tests.test_edit_bridge_qa import EditBridgeQATests
class EditBridgeQATamperTests(unittest.TestCase):
 def test_issue_gate_or_check_tamper_fails(self):
  helper=EditBridgeQATests();inputs=helper.inputs()
  from deeptalk_studio.edit_bridge_qa import run_edit_bridge_qa
  qa=run_edit_bridge_qa(inputs)
  for field,value in (("package_gate_status","pass"),("qa_digest","x"*64)):
   forged=copy.deepcopy(qa);forged[field]=value
   with self.assertRaises(EditBridgeQAError):validate_edit_bridge_qa(forged,inputs)
if __name__=="__main__":unittest.main()
