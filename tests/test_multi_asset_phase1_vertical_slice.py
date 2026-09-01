import sys
import subprocess
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_portfolio import build_candidate_portfolio, ready_candidates
from deeptalk_studio.candidate_portfolio_storage import save_candidate_portfolio
from deeptalk_studio.visual_opportunity import build_visual_opportunity_plan
from deeptalk_studio.visual_opportunity_storage import load_visual_opportunity_plan, save_visual_opportunity_plan
from deeptalk_studio.visual_plugin_adapter import run_visual_plugin

ROOT=Path(__file__).resolve().parents[1]
CORE_SHA=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,check=True,text=True,capture_output=True).stdout.strip()
T={"artifact_version":"semantic-timeline/1","timeline_id":"ST-01","timing_provenance":"actual_aroll_alignment","alignment_digest":"c"*64,"transcript_digest":"d"*64,"spans":[{"span_id":"ST001","actual_start_seconds":"0.000","actual_end_seconds":"2.000","summary":"Synthetic semantics.","visual_eligibility":"safe","reason":"safe_real_alignment"}]}
T["timeline_digest"]=hashlib.sha256(json.dumps(T,ensure_ascii=False,sort_keys=True,separators=(",",":" )).encode("utf-8")).hexdigest()
D={"artifact_version":"visual-opportunity-directives/1","directives_id":"VOD-01","revision":1,"semantic_timeline_digest":T["timeline_digest"],"reviewed_script_digest":"b"*64,"directives":[{"directive_id":"D-01","span_id":"ST001","visual_purpose":"Explain.","why_opportunity":"Useful.","semantic_context_selector":{"include_neighboring_spans":0},"factual_context_refs":[]}]}
DEFAULTS={"language":"zh-CN","canvas":{"width":1920,"height":1080},"target_duration_ms":1500}
def plugin(scenario): return {"plugin_id":"fake-visual-plugin","plugin_version":"fake-1","plugin_root":str(ROOT),"argv_prefix":[sys.executable,"tests/visual_asset_plugin_fakes.py","--scenario",scenario],"timeout_seconds":2,"environment":{},"enabled":True,"plugin_version_command":[sys.executable,"tests/visual_asset_plugin_fakes.py","--version"],"expected_source_revision":CORE_SHA,"require_clean_worktree":False}

class Phase1VerticalSliceTests(unittest.TestCase):
 def test_synthetic_safe_opportunity_reaches_immutable_accepted_ready_portfolio(self):
  with tempfile.TemporaryDirectory() as root:
   plan=build_visual_opportunity_plan(T,D,defaults=DEFAULTS); self.assertEqual(load_visual_opportunity_plan(save_visual_opportunity_plan(plan,Path(root))),plan); opportunity=plan["opportunities"][0]
   suitability=run_visual_plugin(plugin("suitable"),operation="suitability",opportunity=opportunity,job_root=Path(root)); generation=run_visual_plugin(plugin("ready"),operation="generation",opportunity=opportunity,proposal_id=suitability["raw_response"]["proposal_id"],job_root=Path(root))
   portfolio=build_candidate_portfolio(opportunity,suitability,generation,core_status="ACCEPTED"); save_candidate_portfolio(portfolio,Path(root)); self.assertEqual(len(ready_candidates([portfolio])),1); self.assertEqual(portfolio["suitability_execution"]["job_locator"],suitability["execution"]["job_locator"]); self.assertEqual(portfolio["generation_execution"]["job_locator"],generation["execution"]["job_locator"])
 def test_abstain_never_creates_generation_request_or_candidate(self):
  with tempfile.TemporaryDirectory() as root:
   opportunity=build_visual_opportunity_plan(T,D,defaults=DEFAULTS)["opportunities"][0]; suitability=run_visual_plugin(plugin("abstain"),operation="suitability",opportunity=opportunity,job_root=Path(root)); portfolio=build_candidate_portfolio(opportunity,suitability,None)
   self.assertEqual(portfolio["generation_call"],"NOT_REQUESTED"); self.assertIsNone(portfolio["plugin_candidate"]); self.assertEqual(portfolio["suitability_execution"]["job_locator"],suitability["execution"]["job_locator"]); self.assertNotIn("generation_execution",portfolio)

if __name__=="__main__": unittest.main()
