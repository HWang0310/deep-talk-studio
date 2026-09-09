import unittest
from deeptalk_studio.material_bridge import _validate_local
class AlignmentMaterialEvalTests(unittest.TestCase):
 def test_missing_material_is_not_ready(self):self.assertEqual(_validate_local({"local_path":""},__import__("pathlib").Path(".")),"missing_asset")
if __name__=="__main__":unittest.main()
