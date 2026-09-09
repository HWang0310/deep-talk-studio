"""Tests for candidate_pack_workflow: Candidate Asset Pack + immutable staging.

Covers Phase 4 acceptance criteria (post CORRECTION-1):

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
* Duplicate / non-overwrite (same bytes OK)
* Same filename different bytes fail closed
* Source SHA ≠ observed_sha256 fail closed
* Missing observed_sha256 fail closed
* Raw sha256 ≠ observed_sha256 fail closed
* Traversal rejection
* Absolute URI rejection
* Symlink media rejection
* Symlink dest target rejection
* Dest root itself symlink rejection
* Dest root ancestor symlink rejection
* Per-request output root: two candidates, same URI, different request dirs
* PREVIEW staging locator points to real file
* Plugin internal metadata excluded
* No winner semantics
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

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

DEFAULT_REQUEST_ID = "req-001"


def _media_bytes(candidate_id: str) -> bytes:
    """Deterministic tiny MP4-like bytes for testing."""
    return f"FAKE_MEDIA_{candidate_id}".encode("utf-8").ljust(64, b"\x00")


def _write_file(
    job_root: Path,
    filename: str,
    content: bytes,
    request_id: str = DEFAULT_REQUEST_ID,
) -> tuple[Path, str]:
    """Write *content* to ``job_root/<request_id>/output/<filename>``."""
    output_dir = job_root / request_id / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    return path, sha


def _write_media(
    job_root: Path,
    candidate_id: str,
    request_id: str = DEFAULT_REQUEST_ID,
) -> tuple[Path, str]:
    """Write deterministic media to ``job_root/<request_id>/output/<candidate_id>.mp4``."""
    return _write_file(job_root, f"{candidate_id}.mp4", _media_bytes(candidate_id), request_id)


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
    preview_uri: str = "",
    preview_sha: str = "",
) -> dict:
    artifacts: list[dict[str, Any]] = [
        {
            "role": "PRIMARY_MEDIA",
            "uri": media_uri,
            "media_type": "video/mp4",
            "sha256": media_sha,
            "duration_ms": duration_ms,
        },
    ]
    if preview_uri:
        artifacts.append({
            "role": "PREVIEW",
            "uri": preview_uri,
            "media_type": "image/jpeg",
            "sha256": preview_sha,
        })
    return {
        "candidate_id": candidate_id,
        "asset_family": family,
        "candidate_status": status,
        "duration_ms": duration_ms,
        "suggested_placement": {"start_ms": start_ms, "end_ms": end_ms},
        "artifacts": artifacts,
        "qa": (
            {"status": "PASSED", "summary": "合成检查通过。"}
            if status == "READY"
            else {"status": "FAILED", "summary": "合成检查未通过。"}
        ),
        "provenance": {"origin": "plugin-generated", "source_ref": "synthetic manifest v1"},
        **({"plugin_metadata": plugin_metadata} if plugin_metadata else {}),
    }


def _portfolio_entry(
    candidate: dict,
    *,
    core_status: str = "ACCEPTED",
    observed_sha: str = "",
    plugin_id: str = "org.example.synthetic-motion",
    request_id: str = DEFAULT_REQUEST_ID,
    suitability: str = "SUITABLE",
    proposal_id: str = "prop-01",
    review_order: int | None = 1,
) -> dict:
    acceptance: dict[str, Any] = {"status": core_status}
    if core_status == "ACCEPTED" and observed_sha:
        acceptance["observed_sha256"] = observed_sha
    entry: dict[str, Any] = {
        "plugin_id": plugin_id,
        "proposal_id": proposal_id,
        "suitability": suitability,
        "plugin_candidate": candidate,
        "core_acceptance": acceptance,
        "_test_request_id": request_id,
    }
    if (
        review_order is not None
        and core_status == "ACCEPTED"
        and candidate.get("candidate_status") == "READY"
    ):
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


def _opp_block(candidates: list[dict], *, opp: dict | None = None) -> dict:
    """Build an opportunity block, auto-generating generation_records from entries."""
    gen_records: list[dict[str, Any]] = []
    for c in candidates:
        req_id = c.pop("_test_request_id", DEFAULT_REQUEST_ID)
        gen_records.append({
            "plugin_id": c.get("plugin_id", ""),
            "generation_execution": {"request_id": req_id},
        })
    return {
        "opportunity": opp or OPP,
        "proposals": [],
        "policy_records": [],
        "generation_records": gen_records,
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Tests — basic inclusion / exclusion
# ---------------------------------------------------------------------------

class ZeroCandidatesTests(unittest.TestCase):
    def test_zero_candidates_produces_empty_pack(self):
        portfolio = _portfolio([_opp_block([])])
        with tempfile.TemporaryDirectory() as raw:
            pack = build_candidate_asset_pack(
                portfolio,
                job_root=Path(raw),
                dest_root=Path(raw) / "staged",
            )
            self.assertEqual(pack["artifact_version"], "candidate-asset-pack/1")
            self.assertEqual(len(pack["opportunities"]), 1)
            self.assertEqual(pack["opportunities"][0]["candidates"], [])


class SingleCandidateTests(unittest.TestCase):
    def test_one_ready_accepted_candidate_is_included(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, media_sha = _write_media(root, "cand-01")
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://cand-01.mp4",
                media_sha=media_sha,
            )
            portfolio = _portfolio([
                _opp_block([_portfolio_entry(candidate, observed_sha=media_sha)]),
            ])

            pack = build_candidate_asset_pack(
                portfolio, job_root=root, dest_root=root / "staged",
            )
            opp = pack["opportunities"][0]
            self.assertEqual(len(opp["candidates"]), 1)
            entry = opp["candidates"][0]
            self.assertEqual(entry["candidate_id"], "cand-01")
            self.assertEqual(entry["asset_family"], "SYNTHETIC_MOTION")
            self.assertEqual(entry["review_order"], 1)
            self.assertTrue(entry["primary_media"]["filename"])
            staged = Path(entry["primary_media"]["staged_path"])
            self.assertTrue(staged.is_file())
            self.assertEqual(entry["primary_media"]["sha256"], media_sha)


class MultipleOverlappingTests(unittest.TestCase):
    def test_multiple_overlapping_candidates_all_included(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha1 = _write_media(root, "cand-01")
            _, sha2 = _write_media(root, "cand-02")
            c1 = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha1,
                            start_ms=12000, end_ms=16000, duration_ms=4000)
            c2 = _candidate("cand-02", media_uri="local-runner://cand-02.mp4", media_sha=sha2,
                            start_ms=14000, end_ms=19000, duration_ms=5000,
                            family="SYNTHETIC_METAPHOR")
            portfolio = _portfolio([_opp_block([
                _portfolio_entry(c1, review_order=1, observed_sha=sha1),
                _portfolio_entry(c2, plugin_id="org.example.metaphor", proposal_id="prop-02",
                                 review_order=2, observed_sha=sha2),
            ])])

            pack = build_candidate_asset_pack(
                portfolio, job_root=root, dest_root=root / "staged",
            )
            candidates = pack["opportunities"][0]["candidates"]
            self.assertEqual(len(candidates), 2)
            ids = {c["candidate_id"] for c in candidates}
            self.assertEqual(ids, {"cand-01", "cand-02"})
            families = {c["asset_family"] for c in candidates}
            self.assertEqual(families, {"SYNTHETIC_MOTION", "SYNTHETIC_METAPHOR"})
            durations = {c["duration_ms"] for c in candidates}
            self.assertEqual(durations, {4000, 5000})


class ExclusionTests(unittest.TestCase):
    def test_core_rejected_excluded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-rej")
            candidate = _candidate("cand-rej", media_uri="local-runner://cand-rej.mp4", media_sha=sha)
            entry = _portfolio_entry(candidate, core_status="REJECTED", observed_sha=sha)
            portfolio = _portfolio([_opp_block([entry])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            self.assertEqual(pack["opportunities"][0]["candidates"], [])

    def test_qa_rejected_excluded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-qa")
            candidate = _candidate("cand-qa", status="QA_REJECTED",
                                   media_uri="local-runner://cand-qa.mp4", media_sha=sha)
            entry = _portfolio_entry(candidate, core_status="ACCEPTED", observed_sha=sha)
            portfolio = _portfolio([_opp_block([entry])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            self.assertEqual(pack["opportunities"][0]["candidates"], [])

    def test_failure_no_call_excluded(self):
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

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            self.assertEqual(pack["opportunities"][0]["candidates"], [])


# ---------------------------------------------------------------------------
# Tests — integrity
# ---------------------------------------------------------------------------

class PortfolioUnchangedTests(unittest.TestCase):
    def test_portfolio_not_mutated(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])
            snapshot = copy.deepcopy(portfolio)

            build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            self.assertEqual(portfolio, snapshot)


class StagingIntegrityTests(unittest.TestCase):
    def test_media_copy_and_hash_preserved(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            entry = pack["opportunities"][0]["candidates"][0]
            staged_path = Path(entry["primary_media"]["staged_path"])
            self.assertTrue(staged_path.is_file())
            self.assertEqual(entry["primary_media"]["sha256"], sha)
            self.assertEqual(hashlib.sha256(staged_path.read_bytes()).hexdigest(), sha)

    def test_duplicate_non_overwrite_same_bytes_ok(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])
            dest = root / "staged"

            pack1 = build_candidate_asset_pack(portfolio, job_root=root, dest_root=dest)
            staged1 = Path(pack1["opportunities"][0]["candidates"][0]["primary_media"]["staged_path"])

            pack2 = build_candidate_asset_pack(portfolio, job_root=root, dest_root=dest)
            staged2 = Path(pack2["opportunities"][0]["candidates"][0]["primary_media"]["staged_path"])
            self.assertEqual(staged1, staged2)

    def test_different_bytes_same_filename_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])
            dest = root / "staged"
            dest.mkdir(parents=True, exist_ok=True)

            filename = "cand-01_001.mp4"
            (dest / filename).write_bytes(b"DIFFERENT_BYTES")

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=dest)

    def test_source_sha_mismatch_fail_closed(self):
        """Source file SHA doesn't match observed_sha256 → fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _write_media(root, "cand-01")
            wrong_sha = "b" * 64
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://cand-01.mp4",
                media_sha=wrong_sha,
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=wrong_sha)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")

    def test_missing_observed_sha_fail_closed(self):
        """core_acceptance lacks observed_sha256 → fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            # No observed_sha → core_acceptance has no observed_sha256
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")

    def test_raw_sha_mismatch_observed_fail_closed(self):
        """Raw artifact sha256 ≠ observed_sha256 → fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://cand-01.mp4",
                media_sha="0" * 64,
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")


# ---------------------------------------------------------------------------
# Tests — traversal / symlink safety
# ---------------------------------------------------------------------------

class TraversalTests(unittest.TestCase):
    def test_traversal_uri_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / DEFAULT_REQUEST_ID / "output").mkdir(parents=True, exist_ok=True)
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://../../etc/passwd",
                media_sha="a" * 64,
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha="a" * 64)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")

    def test_absolute_uri_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / DEFAULT_REQUEST_ID / "output").mkdir(parents=True, exist_ok=True)
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner:///etc/passwd",
                media_sha="a" * 64,
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha="a" * 64)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")


class SymlinkTests(unittest.TestCase):
    def test_symlink_media_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output_dir = root / DEFAULT_REQUEST_ID / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            real_media = output_dir / "real.mp4"
            real_media.write_bytes(_media_bytes("cand-01"))
            sha = hashlib.sha256(real_media.read_bytes()).hexdigest()

            link = output_dir / "link.mp4"
            os.symlink(real_media, link)

            candidate = _candidate("cand-01", media_uri="local-runner://link.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")

    def test_symlink_dest_target_rejected(self):
        """Existing symlink at the destination filename → fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])
            dest = root / "staged"
            dest.mkdir(parents=True, exist_ok=True)
            os.symlink(root / "other.mp4", dest / "cand-01_001.mp4")

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=dest)

    def test_dest_root_itself_symlink_rejected(self):
        """dest_root is itself a symlink → fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            real_dest = root / "real_staged"
            real_dest.mkdir(parents=True, exist_ok=True)
            sym_dest = root / "sym_staged"
            os.symlink(real_dest, sym_dest)

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=sym_dest)

    def test_dest_root_ancestor_symlink_rejected(self):
        """An ancestor of dest_root is a symlink → fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            real_parent = root / "real_parent"
            real_parent.mkdir(parents=True, exist_ok=True)
            sym_parent = root / "sym_parent"
            os.symlink(real_parent, sym_parent)

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(
                    portfolio, job_root=root, dest_root=sym_parent / "staged",
                )

    def test_dest_root_exists_but_parent_is_symlink_rejected(self):
        """dest_root already exists and is a normal dir, but its parent is a
        symlink → must still be rejected (CORRECTION-2 regression).

        Setup:
            real_parent/staged/   (staged already exists as a real dir)
            sym_parent -> real_parent
            dest_root = sym_parent/staged

        dest_root.exists() == True and dest_root.is_symlink() == False,
        but sym_parent is a symlink so the lexical chain is unsafe.
        """
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            real_parent = root / "real_parent"
            staged = real_parent / "staged"
            staged.mkdir(parents=True, exist_ok=True)  # staged already exists
            sym_parent = root / "sym_parent"
            os.symlink(real_parent, sym_parent)

            # dest_root = sym_parent / "staged" — exists, not a symlink itself,
            # but parent (sym_parent) is a symlink
            dest_root = sym_parent / "staged"
            self.assertTrue(dest_root.exists())
            self.assertFalse(dest_root.is_symlink())

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=dest_root)

    def test_cross_parent_user_symlink_rejected(self):
        """User-created cross-directory symlink ancestor → reject (CORRECTION-3 regression).

        Setup:
            outside/real_parent/staged/   (staged already exists)
            inside/user_link -> outside/real_parent
            dest_root = inside/user_link/staged

        ``user_link`` is a cross-parent symlink (lexical_parent=inside,
        resolved_parent=outside).  The old heuristic would mistake this
        for a system redirect and allow it.  Must be rejected.
        """
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            outside = root / "outside"
            real_parent = outside / "real_parent"
            staged = real_parent / "staged"
            staged.mkdir(parents=True, exist_ok=True)

            inside = root / "inside"
            inside.mkdir(parents=True, exist_ok=True)
            user_link = inside / "user_link"
            os.symlink(real_parent, user_link)

            dest_root = user_link / "staged"
            self.assertTrue(dest_root.exists())
            self.assertFalse(dest_root.is_symlink())

            with self.assertRaises(CandidatePackError):
                build_candidate_asset_pack(portfolio, job_root=root, dest_root=dest_root)


# ---------------------------------------------------------------------------
# Tests — per-request output root regression
# ---------------------------------------------------------------------------

class PerRequestOutputRootTests(unittest.TestCase):
    """Two candidates with the same URI but different request output dirs."""

    def test_two_candidates_different_request_dirs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            content_a = _media_bytes("cand-a")
            content_b = _media_bytes("cand-b")
            _, sha_a = _write_file(root, "primary.mp4", content_a, request_id="req-001")
            _, sha_b = _write_file(root, "primary.mp4", content_b, request_id="req-002")
            self.assertNotEqual(sha_a, sha_b)

            c1 = _candidate(
                "cand-a", media_uri="local-runner://primary.mp4", media_sha=sha_a,
            )
            c2 = _candidate(
                "cand-b", media_uri="local-runner://primary.mp4", media_sha=sha_b,
                family="SYNTHETIC_METAPHOR",
            )
            portfolio = _portfolio([_opp_block([
                _portfolio_entry(c1, plugin_id="plugin-a", request_id="req-001",
                                 review_order=1, observed_sha=sha_a),
                _portfolio_entry(c2, plugin_id="plugin-b", request_id="req-002",
                                 review_order=2, observed_sha=sha_b),
            ])])

            pack = build_candidate_asset_pack(
                portfolio, job_root=root, dest_root=root / "staged",
            )
            candidates = pack["opportunities"][0]["candidates"]
            self.assertEqual(len(candidates), 2)

            entry_a = next(c for c in candidates if c["candidate_id"] == "cand-a")
            entry_b = next(c for c in candidates if c["candidate_id"] == "cand-b")
            self.assertEqual(entry_a["primary_media"]["sha256"], sha_a)
            self.assertEqual(entry_b["primary_media"]["sha256"], sha_b)

            staged_a = Path(entry_a["primary_media"]["staged_path"])
            staged_b = Path(entry_b["primary_media"]["staged_path"])
            self.assertEqual(hashlib.sha256(staged_a.read_bytes()).hexdigest(), sha_a)
            self.assertEqual(hashlib.sha256(staged_b.read_bytes()).hexdigest(), sha_b)


# ---------------------------------------------------------------------------
# Tests — PREVIEW staging regression
# ---------------------------------------------------------------------------

class PreviewStagingTests(unittest.TestCase):
    """PREVIEW staging locator must point to a real file."""

    def test_preview_locator_points_to_real_file(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, media_sha = _write_media(root, "cand-01")
            preview_content = b"PREVIEW_IMAGE_cand-01".ljust(32, b"\x00")
            _, preview_sha = _write_file(root, "cand-01_preview.jpg", preview_content)

            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://cand-01.mp4",
                media_sha=media_sha,
                preview_uri="local-runner://cand-01_preview.jpg",
                preview_sha=preview_sha,
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=media_sha)])])

            pack = build_candidate_asset_pack(
                portfolio, job_root=root, dest_root=root / "staged",
            )
            entry = pack["opportunities"][0]["candidates"][0]

            # Primary media staged
            self.assertTrue(Path(entry["primary_media"]["staged_path"]).is_file())

            # Preview media staged and locator is consistent
            self.assertIsNotNone(entry.get("preview_media"))
            self.assertIsNotNone(entry["preview_media"].get("locator"))
            locator = entry["preview_media"]["locator"]
            self.assertTrue(locator.startswith("local-candidate-artifact://"))
            preview_filename = locator[len("local-candidate-artifact://"):]
            preview_path = root / "staged" / preview_filename
            self.assertTrue(preview_path.is_file(), f"Preview file not found at {preview_path}")
            self.assertEqual(
                hashlib.sha256(preview_path.read_bytes()).hexdigest(), preview_sha,
            )


# ---------------------------------------------------------------------------
# Tests — creator-facing surface
# ---------------------------------------------------------------------------

class PluginMetadataExcludedTests(unittest.TestCase):
    def test_plugin_metadata_not_in_creator_pack(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate(
                "cand-01",
                media_uri="local-runner://cand-01.mp4",
                media_sha=sha,
                plugin_metadata={"runner_argv": ["secret"], "debug": "internal"},
            )
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            entry = pack["opportunities"][0]["candidates"][0]
            pack_json = json.dumps(entry, ensure_ascii=False)
            self.assertNotIn("plugin_metadata", pack_json)
            self.assertNotIn("runner_argv", pack_json)
            self.assertNotIn("debug", pack_json)


class NoWinnerSemanticsTests(unittest.TestCase):
    def test_review_order_not_winner(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha1 = _write_media(root, "cand-01")
            _, sha2 = _write_media(root, "cand-02")
            c1 = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha1)
            c2 = _candidate("cand-02", media_uri="local-runner://cand-02.mp4", media_sha=sha2)
            portfolio = _portfolio([_opp_block([
                _portfolio_entry(c1, review_order=1, observed_sha=sha1),
                _portfolio_entry(c2, plugin_id="org.example.b", proposal_id="prop-02",
                                 review_order=2, observed_sha=sha2),
            ])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            pack_json = json.dumps(pack, ensure_ascii=False)
            self.assertNotIn("winner", pack_json.lower())
            self.assertNotIn("best", pack_json.lower())
            self.assertNotIn("recommended", pack_json.lower())
            orders = [c["review_order"] for c in pack["opportunities"][0]["candidates"]]
            self.assertEqual(orders, [1, 2])


class SavePackTests(unittest.TestCase):
    def test_save_pack_non_overwriting(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            dest = root / "packs"
            path1 = save_candidate_asset_pack(pack, dest)
            self.assertTrue(path1.is_file())
            with self.assertRaises(CandidatePackError):
                save_candidate_asset_pack(pack, dest)


class ArollWindowTests(unittest.TestCase):
    def test_a_roll_window_visible_in_pack(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            opp = pack["opportunities"][0]
            self.assertIn("a_roll_window", opp)
            self.assertEqual(opp["a_roll_window"]["start_ms"], 12000)
            self.assertEqual(opp["a_roll_window"]["end_ms"], 19000)
            self.assertIn("start_timecode", opp["a_roll_window"])
            self.assertIn("end_timecode", opp["a_roll_window"])

    def test_purpose_and_reason_visible(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, sha = _write_media(root, "cand-01")
            candidate = _candidate("cand-01", media_uri="local-runner://cand-01.mp4", media_sha=sha)
            portfolio = _portfolio([_opp_block([_portfolio_entry(candidate, observed_sha=sha)])])

            pack = build_candidate_asset_pack(portfolio, job_root=root, dest_root=root / "staged")
            opp = pack["opportunities"][0]
            self.assertEqual(opp["visual_purpose"], "用短结构动画帮助观众看清变化顺序。")
            self.assertEqual(opp["semantic_context"], "前一段说明指标稳定，后一段解释收缩后果。")


if __name__ == "__main__":
    unittest.main()
