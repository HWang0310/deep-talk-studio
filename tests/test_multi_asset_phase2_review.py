import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_portfolio import orchestrate_candidate_portfolio, ready_candidates
from deeptalk_studio.candidate_portfolio import core_accept_candidate
from deeptalk_studio.candidate_portfolio_storage import load_candidate_portfolio, save_candidate_portfolio
from deeptalk_studio.visual_generation_policy import load_candidate_generation_policy
from deeptalk_studio.visual_opportunity import build_visual_opportunity_plan
from deeptalk_studio.visual_opportunity_directive import author_visual_opportunity_directives
from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_validation import prepare_script_draft
from deeptalk_studio.script_review import prepare_script_review
from tests.fixtures import approved_report_data, valid_script_content, valid_script_review_content

ROOT = Path(__file__).resolve().parents[1]
O = {"opportunity_id":"VO-e2e", "spoken_semantics":"synthetic", "visual_purpose":"explain", "a_roll_window":{"start_ms":0,"end_ms":1000}, "target_duration_ms":1000, "language":"zh-CN", "canvas":{"width":16,"height":16}, "factual_context":[{"claim_id":"C1","evidence_id":"E1"}]}

def config(specs):
    plugins=[]
    for plugin_id, scenario, enabled in specs:
        plugins.append({"plugin_id":plugin_id,"plugin_root":str(ROOT),"argv_prefix":[sys.executable,"tests/visual_asset_plugin_fakes.py","--scenario",scenario],"timeout_seconds":3,"environment":{"FAKE_PLUGIN_ID":plugin_id,"FAKE_PLUGIN_VERSION":"fake-1","FAKE_CANDIDATE_ID":"CAN-"+plugin_id,"FAKE_WRITE_MEDIA":"1"},"enabled":enabled,"plugin_version_command":[sys.executable,"tests/visual_asset_plugin_fakes.py","--version"],"expected_source_revision":"fake-only","require_clean_worktree":False})
    return {"config_version":"visual-asset-plugin-config/1","plugins":plugins}

def redigest(artifact):
    payload=copy.deepcopy(artifact); payload.pop("portfolio_digest"); artifact["portfolio_digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

class Phase2ReviewOrchestrationTests(unittest.TestCase):
    def _assert_reload_rejects_tamper(self, mutate):
        with tempfile.TemporaryDirectory() as root:
            artifact=orchestrate_candidate_portfolio([O],config([("A","suitable",True)]),production_profile="RICH",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            path=save_candidate_portfolio(artifact,Path(root)); mutate(artifact); redigest(artifact); path.write_text(json.dumps(artifact),encoding="utf-8")
            with self.assertRaises(Exception): load_candidate_portfolio(path)

    def test_minimal_qa_rejected_is_core_rejected_without_ready_only_noise(self):
        suit={"contract_version":"visual-asset-plugin-contract/1","request_id":"S","opportunity_id":O["opportunity_id"],"plugin_id":"A","plugin_version":"fake-1","proposal_id":"P","operation_status":"COMPLETED","suitability":"SUITABLE","reason":"x"}
        result={"contract_version":"visual-asset-plugin-contract/1","request_id":"G","opportunity_id":O["opportunity_id"],"proposal_id":"P","plugin_id":"A","plugin_version":"fake-1","operation_status":"COMPLETED","candidate":{"candidate_id":"Q","asset_family":"x","candidate_status":"QA_REJECTED","qa":{"status":"FAILED"}}}
        acceptance=core_accept_candidate(O,suit,result,{"plugin_id":"A","plugin_version":"fake-1"},Path("/tmp"))
        codes={problem["code"] for problem in acceptance["problems"]}
        self.assertEqual(acceptance["status"],"REJECTED"); self.assertIn("PLUGIN_QA_REJECTED",codes); self.assertNotIn("MISSING_PRIMARY_MEDIA",codes)

    def test_all_disabled_reload_and_missing_plan_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            disabled=config([("A","suitable",False),("B","suitable",False)])
            artifact=orchestrate_candidate_portfolio([O],disabled,production_profile="LEAN",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            self.assertEqual(artifact["audit_records"],[]); self.assertEqual(ready_candidates([artifact]),[]); self.assertEqual(load_candidate_portfolio(save_candidate_portfolio(artifact,Path(root))),artifact)
            with self.assertRaises(ValueError): orchestrate_candidate_portfolio([O],disabled,production_profile="LEAN",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root))

    def test_failed_plugin_audit_without_a_raw_response_remains_reloadable(self):
        with tempfile.TemporaryDirectory() as root:
            artifact=orchestrate_candidate_portfolio([O],config([("A","non-zero",True)]),production_profile="LEAN",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            audit=artifact["audit_records"][0]
            self.assertEqual(audit["execution"]["status"],"FAILED"); self.assertIsNone(audit["raw_response"]); self.assertIsNone(audit["request_snapshot"])
            self.assertEqual(load_candidate_portfolio(save_candidate_portfolio(artifact,Path(root))),artifact)

    def test_duplicate_raw_candidate_ids_remain_reloadable_only_when_all_are_rejected_with_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            artifact=orchestrate_candidate_portfolio([O],config([("A","suitable",True),("B","suitable",True)]),production_profile="RICH",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            candidates=artifact["opportunities"][0]["candidates"]
            for item in candidates:
                item["plugin_candidate"]["candidate_id"]="DUP"; item["core_acceptance"]={"status":"REJECTED","problems":[{"code":"DUPLICATE_CANDIDATE_ID","message":"duplicate"}]}; item.pop("suggested_review_order",None)
            for record in artifact["opportunities"][0]["generation_records"]: record["generation_raw"]["candidate"]["candidate_id"]="DUP"
            for record in artifact["audit_records"]:
                if record["operation"] == "generation": record["raw_response"]["candidate"]["candidate_id"]="DUP"
            redigest(artifact)
            self.assertEqual(load_candidate_portfolio(save_candidate_portfolio(artifact,Path(root))),artifact)
            candidates[0]["core_acceptance"]["status"]="ACCEPTED"; redigest(artifact); path=Path(root)/artifact["portfolio_id"]/'candidate-portfolio.json'; path.write_text(json.dumps(artifact))
            with self.assertRaises(Exception): load_candidate_portfolio(path)
            candidates[0]["core_acceptance"]={"status":"REJECTED","problems":[{"code":"OTHER","message":"not duplicate evidence"}]}; redigest(artifact); path.write_text(json.dumps(artifact))
            with self.assertRaises(Exception): load_candidate_portfolio(path)

    def test_storage_rejects_recomputed_nested_lineage_tampering(self):
        cases={
            "proposal execution plugin":lambda a: a["opportunities"][0]["proposals"][0]["suitability_execution"].__setitem__("plugin_id","OTHER"),
            "suitability request id":lambda a: a["opportunities"][0]["proposals"][0]["suitability_raw"].__setitem__("request_id","REQ-tampered"),
            "generation proposal id":lambda a: a["opportunities"][0]["generation_records"][0]["generation_raw"].__setitem__("proposal_id","P-tampered"),
            "execution config digest":lambda a: a["opportunities"][0]["generation_records"][0]["generation_execution"].__setitem__("config_digest","0"*64),
            "requested without generation":lambda a: a["opportunities"][0].__setitem__("generation_records",[]),
            "no-call with generation":lambda a: a["opportunities"][0]["policy_records"][0].update({"generation_call":"NOT_REQUESTED","no_call_reason":"POLICY_NO_CALL"}),
            "candidate differs from raw":lambda a: a["opportunities"][0]["candidates"][0]["plugin_candidate"].__setitem__("asset_family","tampered"),
            "audit request snapshot":lambda a: a["audit_records"][0]["request_snapshot"].__setitem__("request_id","REQ-tampered"),
            "audit raw response":lambda a: a["audit_records"][1]["raw_response"].__setitem__("proposal_id","P-tampered"),
            "suggested review order":lambda a: a["opportunities"][0]["candidates"][0].__setitem__("suggested_review_order",2),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name): self._assert_reload_rejects_tamper(mutate)
    def test_review_order_is_stable_when_plugin_config_order_is_shuffled(self):
        specs=[("B","suitable",True),("A","suitable",True),("C","borderline",True)]
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            first=orchestrate_candidate_portfolio([O],config(specs),production_profile="RICH",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(one),visual_opportunity_plan_digest="f"*64)
            second=orchestrate_candidate_portfolio([O],config(list(reversed(specs))),production_profile="RICH",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(two),visual_opportunity_plan_digest="f"*64)
            def order(value): return [(x["plugin_id"],x["suggested_review_order"]) for x in sorted(value["opportunities"][0]["candidates"],key=lambda x:x["plugin_id"])]
            self.assertEqual(order(first),order(second))
    def test_full_canonical_directive_to_fake_subprocess_portfolio_e2e(self):
        report=ResearchReport.from_dict(approved_report_data()); profile=load_script_profile()
        draft=prepare_script_draft(valid_script_content(),report,profile,created_at="2026-08-29T00:00:00+00:00",script_id="SCR-e2e")
        reviewed=prepare_script_review(valid_script_review_content(),report,draft,profile,created_at="2026-08-29T00:01:00+00:00",review_id="SRV-e2e")
        timeline={"artifact_version":"semantic-timeline/1","timeline_id":"ST-e2e","timing_provenance":"actual_aroll_alignment","alignment_digest":"a"*64,"transcript_digest":"b"*64,"spans":[{"span_id":"ST001","actual_start_seconds":"0.000","actual_end_seconds":"1.000","summary":"synthetic","visual_eligibility":"safe","reason":"safe_real_alignment"}]}
        timeline["timeline_digest"]=hashlib.sha256(json.dumps(timeline,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        directives=author_visual_opportunity_directives(timeline,reviewed.script.to_dict(),[{"claim_id":"C1","evidence_id":"E1"},{"claim_id":"C1","evidence_id":"E2"}],[{"directive_id":"D1","span_id":"ST001","visual_intent":"Explain","why_visual":"Useful","factual_context_refs":[{"claim_id":"C1","evidence_id":"E1"}]}],directives_id="VOD-e2e",revision=1,review_artifact=reviewed.artifact,report=report,profile=profile)
        plan=build_visual_opportunity_plan(timeline,directives,defaults={"language":"zh-CN","canvas":{"width":16,"height":16},"target_duration_ms":1000})
        with tempfile.TemporaryDirectory() as root:
            portfolio=orchestrate_candidate_portfolio(plan["opportunities"],config([("MG","suitable",True),("Illustrated","unavailable",True),("Hand","abstain",True)]),production_profile="RICH",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest=plan["plan_digest"])
            self.assertEqual(portfolio["visual_opportunity_plan_digest"],plan["plan_digest"])
            self.assertEqual(len(ready_candidates([portfolio])),1)
            self.assertEqual(load_candidate_portfolio(save_candidate_portfolio(portfolio,Path(root))),portfolio)
    def test_real_fake_subprocess_failure_isolation_and_canonical_portfolio_shape(self):
        with tempfile.TemporaryDirectory() as root:
            artifact = orchestrate_candidate_portfolio([O], config([("MG","suitable",True),("Illustrated","unavailable",True),("Hand","abstain",True),("Disabled","suitable",False)]), production_profile="RICH", policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"), job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            self.assertEqual(set(artifact), {"artifact_version","portfolio_id","visual_opportunity_plan_digest","plugin_config_digest","generation_policy_digest","production_profile","opportunities","audit_records","portfolio_digest"})
            self.assertEqual(len(artifact["opportunities"]),1)
            opportunity=artifact["opportunities"][0]; policies={item["plugin_id"]:item for item in opportunity["policy_records"]}; proposals={item["plugin_id"]:item for item in opportunity["proposals"]}; candidates={item["plugin_id"]:item for item in opportunity["candidates"]}
            self.assertEqual(policies["MG"]["generation_call"],"REQUESTED")
            self.assertEqual(candidates["MG"]["core_acceptance"]["status"],"ACCEPTED")
            self.assertEqual(policies["Illustrated"]["generation_call"],"NOT_REQUESTED")
            self.assertIn("suitability_raw",proposals["Illustrated"])
            self.assertEqual(policies["Hand"]["no_call_reason"],"ABSTAIN")
            self.assertIsNone(proposals["Disabled"]["suitability_raw"])
            self.assertEqual(len(ready_candidates([artifact])),1)
            path=save_candidate_portfolio(artifact,Path(root)); self.assertEqual(load_candidate_portfolio(path),artifact)

    def test_rich_and_standard_no_suitable_run_real_generation_for_every_eligible_fake_plugin(self):
        with tempfile.TemporaryDirectory() as root:
            rich=orchestrate_candidate_portfolio([O],config([("A","suitable",True),("B","suitable",True),("C","borderline",True)]),production_profile="RICH",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            self.assertEqual(len(ready_candidates([rich])),3)
        with tempfile.TemporaryDirectory() as root:
            standard=orchestrate_candidate_portfolio([O],config([("B","borderline",True),("A","borderline",True)]),production_profile="STANDARD",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            records=standard["opportunities"][0]["generation_records"]; candidates=standard["opportunities"][0]["candidates"]
            self.assertTrue(all(item["generation_execution"]["operation"]=="generation" for item in records))
            self.assertEqual([item["suggested_review_order"] for item in sorted(candidates,key=lambda x:x["plugin_id"])],[1,2])

    def test_execution_evidence_has_runtime_version_config_digest_and_locators(self):
        with tempfile.TemporaryDirectory() as root:
            artifact=orchestrate_candidate_portfolio([O],config([("A","suitable",True)]),production_profile="LEAN",policy=load_candidate_generation_policy(ROOT / "config/candidate-generation-profile.json"),job_root=Path(root),visual_opportunity_plan_digest="f"*64)
            execution=artifact["opportunities"][0]["proposals"][0]["suitability_execution"]
            self.assertEqual(execution["resolved_plugin_version"],"fake-1")
            self.assertEqual(execution["config_digest"],artifact["plugin_config_digest"])
            self.assertTrue(all(key in execution for key in ("plugin_id","request_id","operation","job_locator","request_locator","result_locator","stdout_locator","stderr_locator","output_locator","started_at","finished_at","runtime_duration_ms")))

if __name__ == "__main__": unittest.main()
