import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.candidate_portfolio import (
    apply_generation_policy,
    build_multi_candidate_portfolio,
    core_accept_candidate,
    ready_candidates,
)
from deeptalk_studio.candidate_portfolio_storage import (
    CandidatePortfolioStorageError,
    load_candidate_portfolio,
    save_candidate_portfolio,
)
from deeptalk_studio.visual_opportunity_directive import (
    author_visual_opportunity_directives,
    normalize_visual_opportunity_directives,
)
from deeptalk_studio.visual_opportunity_storage import (
    VisualOpportunityStorageError,
    load_visual_opportunity_plan,
    save_visual_opportunity_plan,
)
from deeptalk_studio.visual_opportunity import build_visual_opportunity_plan
from deeptalk_studio.script_validation import script_content_digest


O = {"opportunity_id": "VO-phase2", "spoken_semantics": "Synthetic.", "visual_purpose": "Explain.",
     "a_roll_window": {"start_ms": 0, "end_ms": 2000}, "target_duration_ms": 1000,
     "language": "zh-CN", "canvas": {"width": 1920, "height": 1080},
     "factual_context": [{"claim_id": "C1", "evidence_id": "E1"}]}


def plugin(plugin_id, enabled=True):
    return {"plugin_id": plugin_id, "enabled": enabled, "plugin_version": "fake-1"}


def suitability(plugin_id, value="SUITABLE", status="COMPLETED"):
    base = {"contract_version": "visual-asset-plugin-contract/1", "request_id": "REQ-" + plugin_id,
            "opportunity_id": O["opportunity_id"], "plugin_id": plugin_id, "plugin_version": "fake-1",
            "operation_status": status}
    if status == "COMPLETED":
        base.update({"proposal_id": "PROP-" + plugin_id, "suitability": value, "reason": "synthetic"})
    else:
        base["problem"] = {"code": "UNAVAILABLE", "message": "synthetic"}
    return base


def media_candidate(plugin_id, uri="local-runner://media.mp4", candidate_id=None):
    return {"contract_version": "visual-asset-plugin-contract/1", "request_id": "GEN-" + plugin_id,
            "opportunity_id": O["opportunity_id"], "proposal_id": "PROP-" + plugin_id,
            "plugin_id": plugin_id, "plugin_version": "fake-1", "operation_status": "COMPLETED",
            "candidate": {"candidate_id": candidate_id or "CAN-" + plugin_id, "asset_family": "SYNTHETIC",
                "candidate_status": "READY", "duration_ms": 1000,
                "suggested_placement": {"start_ms": 0, "end_ms": 1000},
                "artifacts": [{"role": "PRIMARY_MEDIA", "uri": uri, "media_type": "video/mp4",
                               "sha256": "", "duration_ms": 1000}],
                "qa": {"status": "PASSED"},
                "provenance": {"origin": "plugin-generated", "generated_as": "illustration"}}}


def write_video(root):
    path = Path(root) / "media.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=1", "-an",
                    "-c:v", "mpeg4", str(path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


class ProductionDirectiveTests(unittest.TestCase):
    def test_authoring_derives_canonical_versions_and_only_accepts_clock_free_editorial_fields(self):
        timeline = {"artifact_version": "semantic-timeline/1", "timing_provenance": "actual_aroll_alignment", "spans": []}
        timeline["timeline_digest"] = hashlib.sha256(json.dumps(timeline, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        script = {"status": "reviewed", "working_title": "Synthetic", "thesis": "Synthetic", "audience_promise": "Synthetic",
                  "beats": [], "closing": "Synthetic", "research_caveats": [], "research_gaps": [], "must_keep_omission_reasons": {}}
        script["reviewed_content_digest"] = script_content_digest(script)
        factual = [{"claim_id": "C1", "evidence_id": "E1"}]
        with self.assertRaises(ValueError):
            author_visual_opportunity_directives(timeline, script, factual, [], directives_id="bad", revision=1)


class PolicyTests(unittest.TestCase):
    def test_policy_is_deterministic_and_never_selects_a_winner(self):
        suitable = suitability("A", "SUITABLE"); borderline = suitability("B", "BORDERLINE"); abstain = suitability("C", "ABSTAIN")
        self.assertEqual(apply_generation_policy("LEAN", [suitable, borderline, abstain]), ["REQUESTED", "NOT_REQUESTED", "NOT_REQUESTED"])
        self.assertEqual(apply_generation_policy("STANDARD", [suitable, borderline, abstain]), ["REQUESTED", "NOT_REQUESTED", "NOT_REQUESTED"])
        self.assertEqual(apply_generation_policy("STANDARD", [borderline, suitability("C", "BORDERLINE")]), ["REQUESTED", "REQUESTED"])
        self.assertEqual(apply_generation_policy("RICH", [suitable, borderline, abstain]), ["REQUESTED", "REQUESTED", "NOT_REQUESTED"])
        self.assertEqual(apply_generation_policy("RICH", [suitable], enabled=[False]), ["NOT_REQUESTED"])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires local ffmpeg/ffprobe")
class CoreQATests(unittest.TestCase):
    def test_valid_synthetic_mp4_passes_ffprobe_and_bad_media_stays_raw_ready_but_core_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_video(temporary); result = media_candidate("A")
            result["candidate"]["artifacts"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            accepted = core_accept_candidate(O, suitability("A"), result, plugin("A"), Path(temporary))
            self.assertEqual(accepted["status"], "ACCEPTED")
            self.assertTrue(accepted["core_locator"].startswith("local-plugin-artifact://"))
            bad = media_candidate("B", "local-runner://not-video.mp4")
            (Path(temporary) / "not-video.mp4").write_text("not video")
            bad["candidate"]["artifacts"][0]["sha256"] = hashlib.sha256((Path(temporary) / "not-video.mp4").read_bytes()).hexdigest()
            rejected = core_accept_candidate(O, suitability("B"), bad, plugin("B"), Path(temporary))
            self.assertEqual(rejected["status"], "REJECTED")
            self.assertTrue(any(problem["code"] == "FFPROBE_UNREADABLE" for problem in rejected["problems"]))

    def test_core_rejects_traversal_duplicate_ids_and_real_material_without_mutating_raw(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = media_candidate("A", "local-runner://../escape.mp4")
            raw = copy.deepcopy(result)
            accepted = core_accept_candidate(O, suitability("A"), result, plugin("A"), Path(temporary), seen_candidate_ids={"CAN-A"})
            self.assertEqual(result, raw)
            self.assertEqual(accepted["status"], "REJECTED")
            codes = {problem["code"] for problem in accepted["problems"]}
            self.assertIn("DUPLICATE_CANDIDATE_ID", codes); self.assertIn("ARTIFACT_URI_UNSAFE", codes)

    def test_core_qa_binds_raw_responses_to_core_recorded_request_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_video(temporary); result = media_candidate("A")
            result["candidate"]["artifacts"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            acceptance = core_accept_candidate(O, suitability("A"), result, plugin("A"), Path(temporary), suitability_execution={"request_id": "wrong"}, generation_execution={"request_id": result["request_id"]})
            self.assertIn("REQUEST_RESPONSE_CORRELATION_MISMATCH", {problem["code"] for problem in acceptance["problems"]})

    def test_core_qa_reports_each_lineage_placement_artifact_and_provenance_problem(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_video(temporary); digest = hashlib.sha256(path.read_bytes()).hexdigest()
            cases = {
                "OPPORTUNITY_LINEAGE_MISMATCH": lambda g, s: g.update({"opportunity_id": "wrong"}),
                "PROPOSAL_LINEAGE_MISMATCH": lambda g, s: g.update({"proposal_id": "wrong"}),
                "PLUGIN_ID_MISMATCH": lambda g, s: g.update({"plugin_id": "wrong"}),
                "PLUGIN_VERSION_MISMATCH": lambda g, s: g.update({"plugin_version": "wrong"}),
                "PLACEMENT_OUTSIDE_OPPORTUNITY": lambda g, s: g["candidate"].update({"suggested_placement": {"start_ms": 0, "end_ms": 3000}}),
                "MISSING_PRIMARY_MEDIA": lambda g, s: g["candidate"].update({"artifacts": []}),
                "ARTIFACT_SHA256_MISMATCH": lambda g, s: g["candidate"]["artifacts"][0].update({"sha256": "0" * 64}),
                "GENERATED_AS_REAL_MATERIAL": lambda g, s: g["candidate"]["provenance"].update({"generated_as": "REAL_MATERIAL"}),
            }
            for code, mutate in cases.items():
                with self.subTest(code=code):
                    generation, suit = media_candidate("A"), suitability("A")
                    generation["candidate"]["artifacts"][0]["sha256"] = digest
                    mutate(generation, suit)
                    acceptance = core_accept_candidate(O, suit, generation, plugin("A"), Path(temporary))
                    self.assertEqual(acceptance["status"], "REJECTED")
                    self.assertIn(code, {problem["code"] for problem in acceptance["problems"]})


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires local ffmpeg/ffprobe")
class MultiPluginPortfolioTests(unittest.TestCase):
    def test_rich_retains_multiple_accepted_candidates_and_failure_isolation_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_video(temporary); digest = hashlib.sha256(path.read_bytes()).hexdigest()
            a = media_candidate("MG"); a["candidate"]["artifacts"][0]["sha256"] = digest
            b = media_candidate("B"); b["candidate"]["artifacts"][0]["sha256"] = digest
            c = media_candidate("C"); c["candidate"]["artifacts"][0]["sha256"] = digest
            portfolio = build_multi_candidate_portfolio(O, [
                {"plugin": plugin("MG"), "suitability": suitability("MG"), "generation": a},
                {"plugin": plugin("Illustrated"), "suitability": suitability("Illustrated", status="UNAVAILABLE")},
                {"plugin": plugin("Hand"), "suitability": suitability("Hand", "ABSTAIN")},
                {"plugin": plugin("B"), "suitability": suitability("B"), "generation": b},
                {"plugin": plugin("C"), "suitability": suitability("C", "BORDERLINE"), "generation": c},
            ], profile="RICH", output_root=Path(temporary))
            self.assertEqual(len(ready_candidates([portfolio])), 3)
            self.assertNotIn("selected_candidate", portfolio); self.assertNotIn("winner", portfolio)
            histories = {item["plugin_id"]: item for item in portfolio["plugin_records"]}
            self.assertEqual(histories["Illustrated"]["generation_call"], "NOT_REQUESTED")
            self.assertEqual(histories["Hand"]["generation_call"], "NOT_REQUESTED")
            self.assertEqual(histories["Hand"]["generation_no_call_reason"], "ABSTAIN")
            self.assertEqual(portfolio["suggested_review_order"], ["CAN-MG", "CAN-B", "CAN-C"])

    def test_duplicate_candidate_ids_reject_deterministically_even_if_first_candidate_failed_other_qa(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_video(temporary); digest = hashlib.sha256(path.read_bytes()).hexdigest()
            first = media_candidate("A", candidate_id="DUP"); first["candidate"]["artifacts"][0]["sha256"] = "0" * 64
            second = media_candidate("B", candidate_id="DUP"); second["candidate"]["artifacts"][0]["sha256"] = digest
            portfolio = build_multi_candidate_portfolio(O, [{"plugin": plugin("A"), "suitability": suitability("A"), "generation": first}, {"plugin": plugin("B"), "suitability": suitability("B"), "generation": second}], profile="RICH", output_root=Path(temporary))
            second_qa = portfolio["plugin_records"][1]["core_acceptance"]
            self.assertIn("DUPLICATE_CANDIDATE_ID", {problem["code"] for problem in second_qa["problems"]})


class StorageHardeningTests(unittest.TestCase):
    def test_malformed_plan_and_portfolio_fail_closed_even_with_recomputed_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            bad_plan = {"artifact_version": "visual-opportunity-plan/1", "plan_id": "VOP-" + "a" * 24,
                        "opportunities": "not-list", "span_audit": [], "plan_digest": "x" * 64}
            p = Path(temporary) / bad_plan["plan_id"] / "visual-opportunity-plan.json"; p.parent.mkdir(); p.write_text(json.dumps(bad_plan))
            with self.assertRaises(VisualOpportunityStorageError): load_visual_opportunity_plan(p)
            bad_portfolio = {"artifact_version": "candidate-portfolio/1", "portfolio_id": "CP-" + "a" * 24,
                             "opportunity_id": "VO", "generation_call": "REQUESTED", "proposal": {}, "portfolio_digest": "x" * 64}
            q = Path(temporary) / bad_portfolio["portfolio_id"] / "candidate-portfolio.json"; q.parent.mkdir(); q.write_text(json.dumps(bad_portfolio))
            with self.assertRaises(CandidatePortfolioStorageError): load_candidate_portfolio(q)

    def test_recomputed_plan_digest_cannot_bypass_nested_storage_shape(self):
        timeline = {"artifact_version": "semantic-timeline/1", "timeline_id": "ST", "timing_provenance": "actual_aroll_alignment", "alignment_digest": "c" * 64, "transcript_digest": "d" * 64, "spans": [{"span_id": "ST001", "actual_start_seconds": "0.000", "actual_end_seconds": "1.000", "summary": "safe", "visual_eligibility": "safe", "reason": "safe_real_alignment"}]}
        timeline["timeline_digest"] = hashlib.sha256(json.dumps(timeline, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        directives = {"artifact_version": "visual-opportunity-directives/1", "directives_id": "D", "revision": 1, "semantic_timeline_digest": timeline["timeline_digest"], "reviewed_script_digest": "e" * 64, "directives": [{"directive_id": "D1", "span_id": "ST001", "visual_purpose": "explain", "why_opportunity": "useful", "semantic_context_selector": {"include_neighboring_spans": 0}, "factual_context_refs": []}]}
        plan = build_visual_opportunity_plan(timeline, directives, defaults={"language": "zh-CN", "canvas": {"width": 16, "height": 16}, "target_duration_ms": 1000})
        with tempfile.TemporaryDirectory() as temporary:
            path = save_visual_opportunity_plan(plan, Path(temporary)); plan["unexpected"] = True; payload = dict(plan); payload.pop("plan_digest"); plan["plan_digest"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(); path.write_text(json.dumps(plan))
            with self.assertRaises(VisualOpportunityStorageError): load_visual_opportunity_plan(path)

    def test_recomputed_digest_cannot_bypass_unknown_fields_or_invalid_nested_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            portfolio = {"artifact_version": "candidate-portfolio/1", "portfolio_id": "CP-" + "b" * 24,
                "opportunity_id": "VO", "policy_profile": "LEAN", "policy_digest": "a" * 64,
                "config_digest": "b" * 64, "plugin_records": [{"plugin_id": "P", "resolved_plugin_version": "1",
                "enabled": True, "suitability_raw": {"contract_version": "visual-asset-plugin-contract/1", "request_id": "R", "opportunity_id": "VO", "plugin_id": "P", "plugin_version": "1", "operation_status": "COMPLETED", "proposal_id": "PR", "suitability": "ABSTAIN", "reason": "test"}, "generation_call": "NOT_REQUESTED",
                "generation_no_call_reason": "ABSTAIN"}], "suggested_review_order": [], "audit_records": [{"opportunity_id": "VO"}]}
            payload = dict(portfolio); portfolio["portfolio_digest"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            path = Path(temporary) / portfolio["portfolio_id"] / "candidate-portfolio.json"; path.parent.mkdir(); path.write_text(json.dumps(portfolio))
            with self.assertRaises(CandidatePortfolioStorageError): load_candidate_portfolio(path)
            portfolio["unexpected"] = True; payload = dict(portfolio); payload.pop("portfolio_digest"); portfolio["portfolio_digest"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(); path.write_text(json.dumps(portfolio))
            with self.assertRaises(CandidatePortfolioStorageError): load_candidate_portfolio(path)
