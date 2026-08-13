import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class EditBridgeCLITests(unittest.TestCase):
 def test_missing_real_aroll_stops_at_one_simple_user_action(self):
  with tempfile.TemporaryDirectory() as temp:
   p=subprocess.run([str(ROOT/"scripts/deeptalk"),"align-video","--session",temp],capture_output=True,text=True)
   self.assertEqual(p.returncode,0);self.assertIn("把已经剪好口气的正式真人口播视频拖进来",p.stdout);self.assertNotIn("provider",p.stdout.casefold());self.assertNotIn("JSON",p.stdout)
if __name__=="__main__":unittest.main()
