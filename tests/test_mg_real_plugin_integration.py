import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_portfolio import orchestrate_candidate_portfolio, ready_candidates
from deeptalk_studio.candidate_portfolio_storage import load_candidate_portfolio, save_candidate_portfolio
from deeptalk_studio.visual_generation_policy import load_candidate_generation_policy


CORE_ROOT = Path(__file__).resolve().parents[1]
MG_ROOT = Path(os.environ.get("DEEPTALK_MG_PLUGIN_ROOT", CORE_ROOT.parent / "deeptalk-mg"))
MG_SHA = "7ae59f1115da8a011113c81f31d320783b0ce8a4"
TASK_ID = "DT-CORE-3A2-001"
OPPORTUNITY = {
    "opportunity_id": "VO-DT-CORE-3A2-001-causal",
    "spoken_semantics": "外部压力经由组织机制逐步传导，因此局部变化最终影响整个系统。",
    "visual_purpose": "用因果链解释压力传导机制。",
    "a_roll_window": {"start_ms": 12500, "end_ms": 21500},
    "target_duration_ms": 7000,
    "language": "zh-CN",
    "canvas": {"width": 1920, "height": 1080},
    "factual_context": [],
}


def real_mg_config() -> dict:
    value = json.loads((CORE_ROOT / "config/visual-asset-plugins.example.json").read_text(encoding="utf-8"))
    value = copy.deepcopy(value)
    for plugin in value["plugins"]:
        plugin["enabled"] = plugin["plugin_id"] == "org.deeptalk.mg"
        if plugin["enabled"]:
            plugin["plugin_root"] = str(MG_ROOT)
    return value


@unittest.skipUnless(
    os.environ.get("DEEPTALK_RUN_MG_INTEGRATION") == "1",
    "set DEEPTALK_RUN_MG_INTEGRATION=1 for the pinned real MG render",
)
class RealMgContractIntegrationTests(unittest.TestCase):
    def test_pinned_mg_suitability_generation_and_core_artifact_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            portfolio = orchestrate_candidate_portfolio(
                [OPPORTUNITY],
                real_mg_config(),
                production_profile="STANDARD",
                policy=load_candidate_generation_policy(CORE_ROOT / "config/candidate-generation-profile.json"),
                job_root=root / "jobs",
                visual_opportunity_plan_digest="3" * 64,
                task_id=TASK_ID,
            )
            block = portfolio["opportunities"][0]
            proposal = next(item for item in block["proposals"] if item["plugin_id"] == "org.deeptalk.mg")
            generation = next(item for item in block["generation_records"] if item["plugin_id"] == "org.deeptalk.mg")
            self.assertEqual(proposal["suitability_raw"]["operation_status"], "COMPLETED")
            self.assertEqual(proposal["suitability_raw"]["suitability"], "SUITABLE")
            self.assertEqual(generation["generation_raw"]["operation_status"], "COMPLETED")
            self.assertEqual(len(block["candidates"]), 1)
            candidate_record = block["candidates"][0]
            candidate = candidate_record["plugin_candidate"]
            self.assertEqual(candidate["candidate_status"], "READY")
            self.assertEqual(candidate["asset_family"], "MG")
            self.assertEqual(candidate["qa"]["status"], "PASSED")
            self.assertTrue(candidate["provenance"])
            self.assertTrue(proposal["suitability_raw"]["proposal_id"])
            self.assertTrue(candidate["candidate_id"])
            placement = candidate["suggested_placement"]
            window = OPPORTUNITY["a_roll_window"]
            self.assertGreaterEqual(placement["start_ms"], window["start_ms"])
            self.assertLessEqual(placement["end_ms"], window["end_ms"])
            self.assertEqual(placement["end_ms"] - placement["start_ms"], candidate["duration_ms"])
            self.assertEqual(candidate["duration_ms"], OPPORTUNITY["target_duration_ms"])
            self.assertEqual(candidate_record["core_acceptance"]["status"], "ACCEPTED")
            self.assertEqual(len(ready_candidates([portfolio])), 1)

            execution = generation["generation_execution"]
            self.assertEqual(execution["task_id"], TASK_ID)
            self.assertEqual(execution["resolved_plugin_version"], "1.0.0-contract-v1")
            self.assertEqual(execution["preflight"]["expected_source_revision"], MG_SHA)
            self.assertEqual(execution["preflight"]["actual_source_revision"], MG_SHA)
            self.assertTrue(execution["preflight"]["clean_worktree"])
            self.assertEqual(execution["configured_runner"], ["node", "scripts/contract-runner.js"])
            self.assertEqual(execution["configured_version_command"], ["node", "scripts/contract-runner.js", "--version"])

            primary = next(item for item in candidate["artifacts"] if item["role"] == "PRIMARY_MEDIA")
            output_root = Path(execution["resolved_argv"][-1])
            media_path = output_root / primary["uri"].removeprefix("local-runner://")
            self.assertTrue(media_path.is_file())
            self.assertEqual(hashlib.sha256(media_path.read_bytes()).hexdigest(), primary["sha256"])
            self.assertEqual(candidate_record["core_acceptance"]["observed_sha256"], primary["sha256"])
            observed_duration = candidate_record["core_acceptance"]["observed_duration_ms"]
            self.assertLessEqual(abs(observed_duration - candidate["duration_ms"]), 100)
            self.assertTrue(candidate_record["core_acceptance"]["core_locator"].startswith("local-plugin-artifact://"))
            self.assertTrue((output_root / "manifest.json").is_file())
            self.assertTrue((output_root / "qa.json").is_file())
            self.assertEqual(load_candidate_portfolio(save_candidate_portfolio(portfolio, root / "portfolios")), portfolio)
            print("MG_REAL_PLUGIN_PROOF=" + json.dumps({
                "proposal_id": proposal["suitability_raw"]["proposal_id"],
                "candidate_id": candidate["candidate_id"],
                "media_sha256": primary["sha256"],
                "duration_ms": candidate["duration_ms"],
                "observed_duration_ms": observed_duration,
                "placement": candidate["suggested_placement"],
                "qa_status": candidate["qa"]["status"],
                "core_acceptance": candidate_record["core_acceptance"]["status"],
                "runtime_duration_ms": execution["runtime_duration_ms"],
            }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
