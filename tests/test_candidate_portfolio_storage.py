import json, tempfile, unittest
from pathlib import Path
from deeptalk_studio.candidate_portfolio import build_candidate_portfolio
from deeptalk_studio.candidate_portfolio_storage import CandidatePortfolioStorageError, load_candidate_portfolio, save_candidate_portfolio
from tests.test_candidate_portfolio import O, responses
class CandidatePortfolioStorageTests(unittest.TestCase):
 def test_storage_roundtrip_overwrite_and_tamper_fail(self):
  root,s,g=responses()
  with root, tempfile.TemporaryDirectory() as directory:
   artifact=build_candidate_portfolio(O,s,g,core_status="ACCEPTED"); path=save_candidate_portfolio(artifact,Path(directory)); self.assertEqual(load_candidate_portfolio(path),artifact)
   with self.assertRaises(CandidatePortfolioStorageError): save_candidate_portfolio(artifact,Path(directory))
   data=json.loads(path.read_text()); data["core_acceptance"]["status"]="REJECTED"; path.write_text(json.dumps(data))
   with self.assertRaises(CandidatePortfolioStorageError): load_candidate_portfolio(path)
if __name__=="__main__": unittest.main()
