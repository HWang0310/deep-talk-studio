"""Tests for candidate_edit_map: JSON, CSV, Markdown creator delivery.

Covers Phase 4 acceptance criteria:

* JSON opportunity arrays
* Repeated CSV opportunity rows
* Markdown grouping
* Visible real A-roll time / reason / family / preview / duration / QA / review order
* Clear "none/one/multiple" creator language
* No winner semantics
* Plugin-internal metadata excluded from all outputs
* Zero candidates
"""
from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from deeptalk_studio.candidate_edit_map import (
    CandidateEditMapError,
    build_edit_map_csv,
    build_edit_map_json,
    build_edit_map_markdown,
    write_candidate_edit_map,
    CSV_FIELDS,
)
from deeptalk_studio.candidate_pack_workflow import (
    build_candidate_asset_pack,
)
import hashlib
from tests.test_candidate_pack_workflow import (
    OPP,
    _candidate,
    _portfolio,
    _portfolio_entry,
    _opp_block,
    _write_media,
)


# ---------------------------------------------------------------------------
# Helper: build a pack for testing
# ---------------------------------------------------------------------------

def _build_pack(root: Path, candidates_data: list[tuple[str, str, int, int, int]]) -> dict:
    """Build a candidate asset pack from (candidate_id, family, duration_ms, start_ms, end_ms)."""
    entries = []
    for i, (cid, family, dur, start, end) in enumerate(candidates_data, 1):
        m, sha = _write_media(root, cid)
        c = _candidate(cid, family=family, duration_ms=dur, start_ms=start, end_ms=end,
                       media_uri=f"local-runner://{cid}.mp4", media_sha=sha)
        entries.append(_portfolio_entry(c, plugin_id=f"org.example.p{i}", proposal_id=f"prop-{i}", review_order=i))
    portfolio = _portfolio([_opp_block(entries)])
    return build_candidate_asset_pack(portfolio, output_root=root, dest_root=root / "staged")


# ---------------------------------------------------------------------------
# JSON tests
# ---------------------------------------------------------------------------

class JsonTests(unittest.TestCase):
    def test_opportunity_centred_json(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [
                ("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000),
                ("cand-02", "SYNTHETIC_METAPHOR", 5000, 14000, 19000),
            ])
            edit_map = build_edit_map_json(pack)
            self.assertEqual(edit_map["artifact_version"], "candidate-edit-map/1")
            self.assertIn("map_digest", edit_map)
            self.assertEqual(len(edit_map["opportunities"]), 1)
            opp = edit_map["opportunities"][0]
            self.assertEqual(opp["opportunity_id"], OPP["opportunity_id"])
            self.assertEqual(len(opp["candidates"]), 2)
            # Both candidates are in the array
            ids = {c["candidate_id"] for c in opp["candidates"]}
            self.assertEqual(ids, {"cand-01", "cand-02"})
            # A-roll window present
            self.assertIn("a_roll_window", opp)

    def test_zero_candidates_json(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [])
            # Manually create an empty-candidate pack
            empty_pack = {
                "artifact_version": "candidate-asset-pack/1",
                "source_portfolio_id": "CP-" + "a" * 24,
                "source_portfolio_digest": "b" * 64,
                "opportunities": [{
                    "opportunity_id": "opp-empty",
                    "a_roll_window": {"start_ms": 0, "end_ms": 1000, "start_timecode": "00:00:00.000", "end_timecode": "00:00:01.000"},
                    "visual_purpose": "test",
                    "semantic_context": "test",
                    "candidates": [],
                }],
                "pack_digest": "c" * 64,
            }
            edit_map = build_edit_map_json(empty_pack)
            self.assertEqual(len(edit_map["opportunities"]), 1)
            self.assertEqual(edit_map["opportunities"][0]["candidates"], [])

    def test_plugin_metadata_excluded_from_json(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            edit_map = build_edit_map_json(pack)
            edit_map_json = json.dumps(edit_map, ensure_ascii=False)
            self.assertNotIn("plugin_metadata", edit_map_json)
            self.assertNotIn("runner_argv", edit_map_json)
            self.assertNotIn("process_logs", edit_map_json)


# ---------------------------------------------------------------------------
# CSV tests
# ---------------------------------------------------------------------------

class CsvTests(unittest.TestCase):
    def test_repeated_opportunity_rows(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [
                ("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000),
                ("cand-02", "SYNTHETIC_METAPHOR", 5000, 14000, 19000),
                ("cand-03", "SYNTHETIC_HANDDRAWN", 3000, 12000, 15000),
            ])
            csv_text = build_edit_map_csv(pack)
            reader = csv.DictReader(io.StringIO(csv_text))
            rows = list(reader)
            self.assertEqual(len(rows), 3)
            # Same opportunity_id appears in all rows
            opp_ids = {r["opportunity_id"] for r in rows}
            self.assertEqual(opp_ids, {OPP["opportunity_id"]})
            # Candidate IDs are unique
            cand_ids = {r["candidate_id"] for r in rows}
            self.assertEqual(len(cand_ids), 3)

    def test_csv_fields_present(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            csv_text = build_edit_map_csv(pack)
            reader = csv.DictReader(io.StringIO(csv_text))
            row = next(reader)
            for field in CSV_FIELDS:
                self.assertIn(field, row)
            self.assertEqual(row["asset_family"], "SYNTHETIC_MOTION")
            self.assertTrue(row["a_roll_start_timecode"])
            self.assertTrue(row["a_roll_end_timecode"])

    def test_plugin_metadata_excluded_from_csv(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            csv_text = build_edit_map_csv(pack)
            self.assertNotIn("plugin_metadata", csv_text)
            self.assertNotIn("runner_argv", csv_text)
            self.assertNotIn("sha256", csv_text.lower())


# ---------------------------------------------------------------------------
# Markdown tests
# ---------------------------------------------------------------------------

class MarkdownTests(unittest.TestCase):
    def test_markdown_grouping_by_opportunity(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [
                ("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000),
                ("cand-02", "SYNTHETIC_METAPHOR", 5000, 14000, 19000),
            ])
            md = build_edit_map_markdown(pack)
            # Opportunity heading present
            self.assertIn("Opportunity", md)
            self.assertIn(OPP["opportunity_id"], md)
            # Both candidate headings present
            self.assertIn("cand-01", md)
            self.assertIn("cand-02", md)

    def test_visible_a_roll_time(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            md = build_edit_map_markdown(pack)
            self.assertIn("A-roll", md)
            # Timecode format present
            self.assertIn("00:00:12.000", md)
            self.assertIn("00:00:19.000", md)

    def test_visible_purpose_and_reason(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            md = build_edit_map_markdown(pack)
            self.assertIn("视觉目的", md)
            self.assertIn("用短结构动画帮助观众看清变化顺序。", md)

    def test_visible_family_duration_qa_review_order(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            md = build_edit_map_markdown(pack)
            self.assertIn("SYNTHETIC_MOTION", md)
            self.assertIn("4000", md)
            self.assertIn("QA", md)
            self.assertIn("查看顺序", md)

    def test_none_one_multiple_language(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            md = build_edit_map_markdown(pack)
            self.assertIn("不用", md)
            self.assertIn("一个", md)
            self.assertIn("多个", md)

    def test_no_winner_semantics(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [
                ("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000),
                ("cand-02", "SYNTHETIC_METAPHOR", 5000, 14000, 19000),
            ])
            md = build_edit_map_markdown(pack)
            md_lower = md.lower()
            for forbidden in ("winner", "最佳", "推荐", "必须使用", "系统已为你选择"):
                self.assertNotIn(forbidden.lower(), md_lower)

    def test_zero_candidates_markdown(self):
        empty_pack = {
            "artifact_version": "candidate-asset-pack/1",
            "source_portfolio_id": "CP-" + "a" * 24,
            "source_portfolio_digest": "b" * 64,
            "opportunities": [],
            "pack_digest": "c" * 64,
        }
        md = build_edit_map_markdown(empty_pack)
        self.assertIn("没有可用", md)

    def test_plugin_metadata_excluded_from_markdown(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            md = build_edit_map_markdown(pack)
            self.assertNotIn("plugin_metadata", md)
            self.assertNotIn("runner_argv", md)
            self.assertNotIn("sha256", md.lower())


# ---------------------------------------------------------------------------
# Write tests
# ---------------------------------------------------------------------------

class WriteTests(unittest.TestCase):
    def test_write_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = _build_pack(root, [("cand-01", "SYNTHETIC_MOTION", 4000, 12000, 16000)])
            edit_map = build_edit_map_json(pack)
            csv_text = build_edit_map_csv(pack)
            md_text = build_edit_map_markdown(pack)

            dest = root / "edit_map_out"
            paths = write_candidate_edit_map(edit_map, csv_text, md_text, dest)
            self.assertTrue(paths["json_path"].is_file())
            self.assertTrue(paths["csv_path"].is_file())
            self.assertTrue(paths["markdown_path"].is_file())

            # JSON is valid
            loaded = json.loads(paths["json_path"].read_text(encoding="utf-8"))
            self.assertEqual(loaded["artifact_version"], "candidate-edit-map/1")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class InputValidationTests(unittest.TestCase):
    def test_rejects_non_pack_json(self):
        with self.assertRaises(CandidateEditMapError):
            build_edit_map_json({"artifact_version": "wrong/1"})

    def test_rejects_non_pack_csv(self):
        with self.assertRaises(CandidateEditMapError):
            build_edit_map_csv({"artifact_version": "wrong/1"})

    def test_rejects_non_pack_markdown(self):
        with self.assertRaises(CandidateEditMapError):
            build_edit_map_markdown({"artifact_version": "wrong/1"})


if __name__ == "__main__":
    unittest.main()
