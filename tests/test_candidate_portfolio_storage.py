import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_portfolio import build_candidate_portfolio
from deeptalk_studio.candidate_portfolio_storage import CandidatePortfolioStorageError, load_candidate_portfolio, save_candidate_portfolio


class CandidatePortfolioStorageTests(unittest.TestCase):
    def test_storage_is_immutable_and_reload_validates(self):
        artifact = build_candidate_portfolio({"opportunity_id": "VO-01"}, {"operation_status": "COMPLETED", "proposal_id": "P-01", "suitability": "ABSTAIN", "reason": "none"}, None)
        with tempfile.TemporaryDirectory() as root:
            path = save_candidate_portfolio(artifact, Path(root))
            self.assertEqual(load_candidate_portfolio(path), artifact)
            with self.assertRaises(CandidatePortfolioStorageError): save_candidate_portfolio(artifact, Path(root))


if __name__ == "__main__": unittest.main()
