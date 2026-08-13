import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AlignmentMediaEvalTests(unittest.TestCase):
 def test_every_approved_case_has_one_owned_test_group(self):
  manifest=json.loads((ROOT/"evaluations/audio-alignment-edit-bridge/case-manifest.json").read_text());expected=[chr(65+i) for i in range(26)]+["A"+chr(65+i) for i in range(9)];self.assertEqual(set(manifest),set(expected));self.assertTrue(all(manifest.values()))
if __name__=="__main__":unittest.main()
