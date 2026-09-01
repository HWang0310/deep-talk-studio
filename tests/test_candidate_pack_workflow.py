"""Tests for candidate_pack_workflow: Candidate Asset Pack + immutable staging.

Covers Phase 4 acceptance criteria:

* Zero candidates
* One candidate
* Multiple overlapping candidates
* Different durations
* Multiple families
* raw READY + Core ACCEPTED included
* raw READY + Core REJECTED excluded
* raw QA_REJECTED excluded
* failure / no-call excluded
* Portfolio unchanged
* Media staging copy / hash preservation
* Duplicate / non-overwrite
* Corrupted bytes fail closed
* Traversal rejection
* Symlink rejection
* Plugin internal metadata excluded
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from deeptalk_studio.candidate_pack_workflow import (
    CandidatePackError,
    build_candidate_asset_pack,
    save_candidate_asset_pack,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

OPP = {
    "opportunity_id": "opp-synthetic-market-shift-01",
    "spoken_semantics": "一个虚构市场指标从稳定转向收缩。",
    "visual_purpose": "用短结构动画帮助观众看清变化顺序。",
    "a_roll_window": {"start_ms": 12000, "end_ms": 19000},
    "target_duration_ms": 6000,
    "language": "zh-CN",
    "canvas": {"width": 1920, "height": 1080},
    "semantic_context": "前一段说明指标稳定，后一段解释收缩后果。",
    "factual_context": [{"claim_id": "claim-01", "evidence_id": "evidence-01"}],
}


def _media_bytes(candidate_id: str) -> bytes:
    """Deterministic tiny MP4-like bytes for testing."""
    return f"FAKE_MEDIA_{candidate_id}".encode("utf-8").ljust(64, b"\x00")


def _write_media(root: Path, candidate_id: str) -> tuple[Path, str]:
    media = root / f"{candidate_id}.mp4"
    media.write_bytes(_media_bytes(candidate_id))
    sha = hashlib.sha256(media.read_bytes()).hexdigest()
    return media, sha


def _candidate(
    candidate_id: str,
    *,
    status: str = "READY",
    family: str = "SYNTHETIC_MOTION",
    duration_ms: int = 6800,
    start_ms: int = 12500,
    end_ms: int = 18500,
    media_uri: str = "",
    media_sha: str = "",
    plugin_metadata: dict | None = None,
) -> dict:
    artifacts = [
        {
            "role": "PRIMARY_MEDIA",
            "uri": media_uri,
            "media_type": "video/mp4",
            "sha256": media_sha,
            "duration_ms": duration_ms,
        },
    ]
    return {
        "candidate_id": candidate_id,
        "asset_family": family,
        "candidate_status": status,
        "duration_ms": duration_ms,
        "suggested_placement": {"start_ms": start_ms, "end_ms": end_ms},
        "artifacts": artifacts,
        "qa": {"status": "PASSED", "summary": "合成检查通过。"} if status == "READY" else {"status": "FAILED", "summary": "合成检查未通过。"},
        "provenance": {"origin": "plugin-generated", "source_ref": "synthetic manifest v1"},
        **({"plugin_metadata": plugin_metadata} if plugin_metadata else {}),
    }


def _portfolio_entry(
    candidate: dict,
    *,
    core_status: str = "ACCEPTED",
    plugin_id: str = "org.example.synthetic-motion",
    suitability: str = "SUITABLE",
    proposal_id: str = "prop-01",
    review_order: int | None = 1,
) -> dict:
    entry: dict[str, Any] = {
        "plugin_id": plugin_id,
        "proposal_id": proposal_id,
        "suitability": suitability,
        "plugin_candidate": candidate,
        "core_acceptance": {"status": core_status},
    }
    if review_order is not None and core_status == "ACCEPTED" and candidate.get("candidate_status") == "READY":
        entry["suggested_review_order"] = review_order
    return entry


def _portfolio(opportunities: list[dict]) -> dict:
    """Build a minimal Phase 2 portfolio shape."""
    return {
        "artifact_version": "candidate-portfolio/1",
        "portfolio_id": "CP-" + "a" * 24,
        "portfolio_digest": "b" * 64,
        "opportunities": opportunities,
    }


def _opp_block(candidates: list[dict], *,opp: dict | None = None) -> dict:
    return {
        "opportunity": opp or OPP,
        "proposals": [],
        "policy_records": [],
        "generation_records": [],
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class ZeroCandidatesTests(unittest.TestCase):
    def test_zero_candidates_produces_empty_pack(self):
        portfolio = _portfolio([_opp_block([])])
        with tempfile.TemporaryDirectory() as raw:
            pack = build_candidate_asset_pack(
                portfolio,
                output_root=Path(raw),
                dest_root=Path(raw) / "staged",
            )
            self.assertEqual(pack["artifact_version"], "candidate-asset-pack/1")
            self.assertEqual(len(pack["opportunities"]), 1)
            self.assertEqual(pack["opportunities"][0]["candidates"], [])


class SingleCandidateTests(unittest.TestCase):
    def test_one_ready_accepted_candidate_is_included(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            media_path, media_sha = _write_media(root, "cand-01")
            candidate = _candidate(
                "cand-01",
                media_uri=f"local-runner://cand-01.mp4",
                media_sha=media_sha,
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            pack = build_candidate_asset_pack(
                portfolio,
                output_root=root,
                dest_root=root / "staged",
            )
            opp = pack["opportunities"][0]
            self.assertEqual(len(opp["candidates"]), 1)
            entry = opp["candidates"][0]
            self.assertEqual(entry["candidate_id"], "cand-01")
            self.assertEqual(entry["asset_family"], "SYNTHETIC_MOTION")
            self.assertEqual(entry["review_order"], 1)
            self.assertTrue(entry["primary_media"]["filename"])
            # Staged file exists
            staged = Path(entry["primary_media"]["staged_path"])
            self.assertTrue(staged.is_file())
            # SHA preserved
            self.assertEqual(entry["primary_media"]["sha256"], media_sha)


class MultipleOverlappingTests(unittest.TestCase):
    def test_multiple_overlapping_candidates_all_included(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m1, sha1 = _write_media(root, "cand-01")
            m2, sha2 = _write_media(root, "cand-02")
            c1 = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha1,
                            start_ms=12000, end_ms=16000, duration_ms=4000)
            c2 = _candidate("cand-02", media_uri="local-runner://cand-02.mp4", media_sha=sha2,
                            start_ms=14000, end_ms=19000, duration_ms=5000, family="SYNTHETIC_METAPHOR")
            portfolio = _portfolio([_opp_block([
                _portfolio_entry(c1, review_order=1),
                _portfolio_entry(c2, plugin_id="org.example.metaphor", proposal_id="prop-02", review_order=2),
            ])])

            pack = build_candidate_asset_pack(
                portfolio,
                output_root=root,
                dest_root=root / "staged",
            )
            candidates = pack["opportunities"][0]["candidates"]
            self.assertEqual(len(candidates), 2)
            # Both overlap and both are present — no resolution
            ids = {c["candidate_id"] for c in candidates}
            self.assertEqual(ids, {"cand-01", "cand-02"})
            # Different families
            families = {c["asset_family"] for c in candidates}
            self.assertEqual(families, {"SYNTHETIC_MOTION", "SYNTHETIC_METAPHOR"})
            # Different durations
            durations = {c["duration_ms"] for c in candidates}
            self.assertEqual(durations, {4000, 5000})


class ExclusionTests(unittest.TestCase):
    def test_core_rejected_excluded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-rej")
            candidate = _candidate("cand-rej", media_uri="local-runner://cand-rej.mp4", media_sha=sha)
            entry = _portfolio_entry(candidate, core_status="REJECTED")
            portfolio = _portfolio([_opp_block([entry])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            self.assertEqual(pack["opportunities"][0]["candidates"], [])

    def test_qa_rejected_excluded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-qa")
            candidate = _candidate("cand-qa", status="QA_REJECTED", media_uri="local-runner://cand-qa.mp4", media_sha=sha)
            entry = _portfolio_entry(candidate, core_status="ACCEPTED")
            portfolio = _portfolio([_opp_block([entry])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            self.assertEqual(pack["opportunities"][0]["candidates"], [])

    def test_failure_no_call_excluded(self):
        """A candidate entry with no plugin_candidate (failure/no-call) is excluded."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            entry = {
                "plugin_id": "org.example.dead",
                "proposal_id": "prop-fail",
                "suitability": "SUITABLE",
                "plugin_candidate": None,
                "core_acceptance": None,
            }
            portfolio = _portfolio([_opp_block([entry])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            self.assertEqual(pack["opportunities"][0]["candidates"], [])


class PortfolioUnchangedTests(unittest.TestCase):
    def test_portfolio_not_mutated(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])
            import copy
            snapshot = copy.deepcopy(portfolio)

            build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            self.assertEqual(portfolio, snapshot)


class StagingIntegrityTests(unittest.TestCase):
    def test_media_copy_and_hash_preserved(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            entry = pack["opportunities"][0]["candidates"][0]
            staged_path = Path(entry["primary_media"]["staged_path"])
            self.assertTrue(staged_path.is_file())
            self.assertEqual(entry["primary_media"]["sha256"], sha)
            self.assertEqual(hashlib.sha256(staged_path.read_bytes()).hexdigest(), sha)

    def test_duplicate_non_overwrite_same_bytes_ok(self):
        """Running build twice with same source: second time uses existing staged file with same bytes."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])
            dest = root / "staged"

            pack1 = build_candidate_asset_pack(portfolio, output_root=root, dest_root=dest)
            entry1 = pack1["opportunities"][0]["candidates"][0]
            staged1 = Path(entry1["primary_media"]["staged_path"])

            # Second build should find the existing file with same bytes and not error
            pack2 = build_candidate_asset_pack(portfolio, output_root=root, dest_root=dest)
            entry2 = pack2["opportunities"][0]["candidates"][0]
            staged2 = Path(entry2["primary_media"]["staged_path"])
            self.assertEqual(staged1, staged2)

    def test_different_bytes_same_filename_fail_closed(self):
        """If dest file exists with different bytes, fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])
            dest = root / "staged"
            dest.mkdir(parents=True, exist_ok=True)

            # Pre-create a file with the same deterministic name but different bytes
            safe_id = "cand-01"
            filename = f"{safe_id}_001.mp4"
            (dest / filename).write_bytes(b"DIFFERENT_BYTES")

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, output_root=root, dest_root=dest)

    def test_corrupted_bytes_fail_closed(self):
        """If staged copy SHA doesn't match expected, fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            # Pass a wrong SHA to trigger post-copy mismatch
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha="0" * 64)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")


class TraversalTests(unittest.TestCase):
    def test_traversal_uri_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = _candidate("cand-01", media_uri="local-runner://../../etc/passwd", media_sha="a" * 64)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")

    def test_absolute_uri_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = _candidate("cand-01", media_uri="local-runner:///etc/passwd", media_sha="a" * 64)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")


class SymlinkTests(unittest.TestCase):
    def test_symlink_media_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            real_media = root / "real.mp4"
            real_media.write_bytes(_media_bytes("cand-01"))
            sha = hashlib.sha256(real_media.read_bytes()).hexdigest()

            link = root / "link.mp4"
            os.symlink(real_media, link)

            candidate = _candidate("cand-01", media_uri="local-runner://link.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")

    def test_symlink_dest_rejected(self):
        """Staging destination with a symlink at the target path is rejected."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])
            dest = root / "staged"
            dest.mkdir(parents=True, exist_ok=True)
            safe_id = "cand-01"
            filename = f"{safe_id}_001.mp4"
            os.symlink(root / "other.mp4", dest / filename)

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, output_root=root, dest_root=dest)


class PluginMetadataExcludedTests(unittest.TestCase):
    def test_plugin_metadata_not_in_creator_pack(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://cand-01.mp4",
                media_sha=sha,
                plugin_metadata={"runner_argv": ["secret"], "debug": "internal"},
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            entry = pack["opportunities"][0]["candidates"][0]
            pack_json = json.dumps(entry, ensure_ascii=False)
            self.assertNotIn("plugin_metadata", pack_json)
            self.assertNotIn("runner_argv", pack_json)
            self.assertNotIn("debug", pack_json)


class NoWinnerSemanticsTests(unittest.TestCase):
    def test_review_order_not_winner(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m1, sha1 = _write_media(root, "cand-01")
            m2, sha2 = _write_media(root, "cand-02")
            c1 = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha1)
            c2 = _candidate("cand-02", media_uri="local-runner://cand-02.mp4", media_sha=sha2)
            portfolio = _portfolio([_opp_block([
                _portfolio_entry(c1, review_order=1),
                _portfolio_entry(c2, plugin_id="org.example.b", proposal_id="prop-02", review_order=2),
            ])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            pack_json = json.dumps(pack, ensure_ascii=False)
            self.assertNotIn("winner", pack_json.lower())
            self.assertNotIn("best", pack_json.lower())
            self.assertNotIn("recommended", pack_json.lower())
            # review_order present
            orders = [c["review_order"] for c in pack["opportunities"][0]["candidates"]]
            self.assertEqual(orders, [1, 2])


class SavePackTests(unittest.TestCase):
    def test_save_pack_non_overwriting(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            dest = root / "packs"
            path1 = save_candidate_asset_pack(pack, dest)
            self.assertTrue(path1.is_file())
            # Same digest → same filename → second save fails
            with self.assertRaises(CandidatePackError):
                save_candidate_asset_pack(pack, dest)


class ArollWindowTests(unittest.TestCase):
    def test_a_roll_window_visible_in_pack(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            opp = pack["opportunities"][0]
            self.assertIn("a_roll_window", opp)
            self.assertEqual(opp["a_roll_window"]["start_ms"], 12000)
            self.assertEqual(opp["a_roll_window"]["end_ms"], 19000)
            self.assertIn("start_timecode", opp["a_roll_window"])
            self.assertIn("end_timecode", opp["a_roll_window"])

    def test_purpose_and_reason_visible(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            m, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            pack = build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")
            opp = pack["opportunities"][0]
            self.assertEqual(opp["visual_purpose"], "用短结构动画帮助观众看清变化顺序。")
            self.assertEqual(opp["semantic_context"], "前一段说明指标稳定，后一段解释收缩后果。")


if __name__ == "__main__":
    unittest.main()
