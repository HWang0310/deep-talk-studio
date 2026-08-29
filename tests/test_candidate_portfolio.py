import copy
import unittest

from deeptalk_studio.candidate_portfolio import build_candidate_portfolio, ready_candidates


OPPORTUNITY = {"opportunity_id": "VO-01"}
SUITABLE = {"operation_status": "COMPLETED", "proposal_id": "PROP-01", "suitability": "SUITABLE", "reason": "Synthetic."}
ABSTAIN = {"operation_status": "COMPLETED", "proposal_id": "PROP-02", "suitability": "ABSTAIN", "reason": "No useful visual."}
READY = {"operation_status": "COMPLETED", "proposal_id": "PROP-01", "candidate": {"candidate_id": "CAND-01", "candidate_status": "READY"}}
REJECTED = {"operation_status": "COMPLETED", "proposal_id": "PROP-01", "candidate": {"candidate_id": "CAND-02", "candidate_status": "QA_REJECTED"}}


class CandidatePortfolioTests(unittest.TestCase):
    def test_abstain_retains_proposal_without_generation_or_candidate(self):
        portfolio = build_candidate_portfolio(OPPORTUNITY, ABSTAIN, None)
        self.assertEqual(portfolio["proposal"]["proposal_id"], "PROP-02")
        self.assertEqual(portfolio["generation_call"], "NOT_REQUESTED")
        self.assertEqual(portfolio["plugin_candidate"], None)

    def test_ready_projection_requires_raw_ready_and_core_accepted_without_mutation(self):
        accepted = build_candidate_portfolio(OPPORTUNITY, SUITABLE, READY, core_status="ACCEPTED")
        rejected = build_candidate_portfolio(OPPORTUNITY, SUITABLE, READY, core_status="REJECTED", core_problem={"code": "SYNTHETIC_REJECT"})
        self.assertEqual(accepted["plugin_candidate"]["candidate_status"], "READY")
        self.assertEqual(accepted["core_acceptance"]["status"], "ACCEPTED")
        self.assertEqual(len(ready_candidates([accepted, rejected])), 1)
        self.assertEqual(rejected["plugin_candidate"]["candidate_status"], "READY")
        self.assertNotIn("selected_candidate", accepted)

    def test_qa_rejected_is_retained_but_never_ready(self):
        portfolio = build_candidate_portfolio(OPPORTUNITY, SUITABLE, REJECTED)
        self.assertEqual(portfolio["plugin_candidate"]["candidate_status"], "QA_REJECTED")
        self.assertEqual(ready_candidates([portfolio]), [])


if __name__ == "__main__":
    unittest.main()
