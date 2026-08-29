import sys
import tempfile
import unittest
from pathlib import Path
from deeptalk_studio.candidate_portfolio import build_candidate_portfolio, ready_candidates
from deeptalk_studio.visual_plugin_adapter import run_visual_plugin

ROOT=Path(__file__).resolve().parents[1]
O={"opportunity_id":"VO-01","spoken_semantics":"Synthetic.","visual_purpose":"Explain.","a_roll_window":{"start_ms":0,"end_ms":2000},"target_duration_ms":1500,"language":"zh-CN","canvas":{"width":1920,"height":1080}}
def plugin(s): return {"plugin_id":"fake-visual-plugin","plugin_root":str(ROOT),"argv_prefix":[sys.executable,"tests/visual_asset_plugin_fakes.py","--scenario",s],"timeout_seconds":2,"environment":{},"enabled":True,"plugin_version_command":[sys.executable,"tests/visual_asset_plugin_fakes.py","--version"],"expected_source_revision":"fake-only","require_clean_worktree":False}
def responses(scenario="ready"):
 root=tempfile.TemporaryDirectory(); p=Path(root.name); s=run_visual_plugin(plugin("suitable"),operation="suitability",opportunity=O,job_root=p); g=run_visual_plugin(plugin(scenario),operation="generation",opportunity=O,proposal_id=s["raw_response"]["proposal_id"],job_root=p); return root,s,g
class CandidatePortfolioTests(unittest.TestCase):
 def test_ready_requires_explicit_core_and_projection_preserves_raw(self):
  root,s,g=responses()
  with root:
   with self.assertRaisesRegex(ValueError,"core_status"): build_candidate_portfolio(O,s,g)
   ok=build_candidate_portfolio(O,s,g,core_status="ACCEPTED"); no=build_candidate_portfolio(O,s,g,core_status="REJECTED",core_problem={"code":"SYNTHETIC"})
   self.assertEqual(ok["plugin_candidate"]["candidate_status"],"READY"); self.assertEqual(len(ready_candidates([ok,no])),1); self.assertEqual(no["plugin_candidate"]["candidate_status"],"READY")
 def test_abstain_and_qa_rejected_are_retained_without_ready_projection(self):
  with tempfile.TemporaryDirectory() as root:
   s=run_visual_plugin(plugin("abstain"),operation="suitability",opportunity=O,job_root=Path(root)); abstain=build_candidate_portfolio(O,s,None)
  root,s,g=responses("qa-rejected")
  with root:
   rejected=build_candidate_portfolio(O,s,g,core_status="REJECTED")
   self.assertEqual(abstain["generation_call"],"NOT_REQUESTED"); self.assertEqual(rejected["plugin_candidate"]["candidate_status"],"QA_REJECTED"); self.assertEqual(ready_candidates([rejected]),[])
 def test_cross_stage_identity_mismatch_fails_closed(self):
  root,s,g=responses()
  with root:
   g["raw_response"]["proposal_id"]="wrong"
   with self.assertRaisesRegex(ValueError,"lineage"): build_candidate_portfolio(O,s,g,core_status="ACCEPTED")
if __name__=="__main__": unittest.main()
