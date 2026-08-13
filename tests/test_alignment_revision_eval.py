import copy,unittest
from deeptalk_studio.edit_bridge_storage import create_bridge_revision
class AlignmentRevisionEvalTests(unittest.TestCase):
 def test_v_new_aroll_chain_binding_never_changes_in_bridge_revision(self):
  old={"revision":1,"created_at":"x","root_bindings":{"alignment_digest":"a"*64},"preview_adjustments":[],"package_digest":"x"};new=create_bridge_revision(old,{"placement_id":"VP1","adjustment_type":"shorter","reason":"short"},created_at="y");self.assertEqual(new["root_bindings"],old["root_bindings"])
if __name__=="__main__":unittest.main()
