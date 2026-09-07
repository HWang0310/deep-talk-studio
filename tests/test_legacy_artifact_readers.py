"""Phase A tests: read-only compatibility readers for legacy artifacts.

Readers must:
  - be versioned (fail closed on unknown versions);
  - verify digests **only when the artifact actually carries one**;
  - never write anything back to the artifact;
  - return a deep copy so callers cannot mutate the source via nested objects.

The Edit Map V1 reader is driven by the **real** ``build_edit_map()`` producer
to avoid synthetic schema invention.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.edit_map import build_edit_map
from deeptalk_studio.legacy_artifact_readers import (
    LegacyArtifactReadError,
    LegacyEditMapV1Reader,
    VisualDirectorPlanV1Reader,
)


# ---------------------------------------------------------------------------
# Visual Director Plan V1 fixtures (this producer DOES emit plan_digest)
# ---------------------------------------------------------------------------

def _digest_without(data: dict, field: str) -> str:
    copy_data = {k: v for k, v in data.items() if k != field}
    return hashlib.sha256(
        json.dumps(copy_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _visual_director_plan() -> dict:
    data = {
        "artifact_version": "visual-director-plan/1",
        "plan_id": "VD-PLAN-001",
        "revision": 1,
        "previous_revision": 0,
        "created_at": "2026-08-24T00:00:00+00:00",
        "alignment_digest": "a" * 64,
        "opportunities": [
            {
                "opportunity_id": "VO001",
                "cue_id": "C001",
                "source_time_range": {"start_seconds": "12.0", "end_seconds": "18.0"},
                "visual_intent": "保留情绪",
                "why_visual": "情绪表演更重要",
                "decision": "KEEP_A_ROLL",
                "importance": "supporting",
                "review_requirement": "not_needed",
                "risk_flags": [],
                "alignment_digest": "a" * 64,
                "status": "keep",
            }
        ],
    }
    data["plan_digest"] = _digest_without(data, "plan_digest")
    return data


# ---------------------------------------------------------------------------
# Edit Map V1 fixtures — driven by the REAL producer
# ---------------------------------------------------------------------------

def _manifest_for_edit_map() -> dict:
    return {
        "assets": [
            {
                "filename": "MG_01_时间线.mp4",
                "qa_status": "ready",
                "sha256": "a" * 64,
                "duration_seconds": "8",
                "time_range": {"start_seconds": "12", "end_seconds": "20"},
                "purpose": "解释",
                "why": "清楚",
                "fallback": "保留真人",
            },
        ]
    }


def _real_edit_map() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        edit_map = build_edit_map(_manifest_for_edit_map(), tmp)
    return edit_map


# ===========================================================================
# VisualDirectorPlanV1Reader
# ===========================================================================

class VisualDirectorPlanV1ReaderTests(unittest.TestCase):
    def test_reads_visual_director_plan_v1(self):
        loaded = VisualDirectorPlanV1Reader().read(_visual_director_plan())
        self.assertEqual(loaded["artifact_version"], "visual-director-plan/1")
        self.assertEqual(loaded["plan_id"], "VD-PLAN-001")
        self.assertEqual(loaded["opportunities"][0]["decision"], "KEEP_A_ROLL")

    def test_read_does_not_mutate_input(self):
        data = _visual_director_plan()
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        VisualDirectorPlanV1Reader().read(data)
        after = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_modifying_output_does_not_mutate_source(self):
        data = _visual_director_plan()
        loaded = VisualDirectorPlanV1Reader().read(data)
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        loaded["opportunities"][0]["decision"] = "MG_MOTION"
        after = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_unsupported_version_fails_closed(self):
        data = _visual_director_plan()
        data["artifact_version"] = "visual-director-plan/2"
        with self.assertRaisesRegex(LegacyArtifactReadError, "unsupported"):
            VisualDirectorPlanV1Reader().read(data)

    def test_tampered_plan_digest_fails_closed(self):
        data = _visual_director_plan()
        data["plan_digest"] = "f" * 64
        with self.assertRaisesRegex(LegacyArtifactReadError, "digest"):
            VisualDirectorPlanV1Reader().read(data)

    # --- plan_digest mandatory (BLOCKER 1) ---

    def test_missing_plan_digest_fails_closed(self):
        data = _visual_director_plan()
        del data["plan_digest"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "plan_digest"):
            VisualDirectorPlanV1Reader().read(data)

    # --- canonical schema validation (BLOCKER 1b) ---

    def test_missing_plan_id_fails_closed(self):
        data = _visual_director_plan()
        del data["plan_id"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "plan_id"):
            VisualDirectorPlanV1Reader().read(data)

    def test_missing_revision_fails_closed(self):
        data = _visual_director_plan()
        del data["revision"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "revision"):
            VisualDirectorPlanV1Reader().read(data)

    def test_missing_previous_revision_fails_closed(self):
        data = _visual_director_plan()
        del data["previous_revision"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "previous_revision"):
            VisualDirectorPlanV1Reader().read(data)

    def test_missing_created_at_fails_closed(self):
        data = _visual_director_plan()
        del data["created_at"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "created_at"):
            VisualDirectorPlanV1Reader().read(data)

    def test_missing_alignment_digest_fails_closed(self):
        data = _visual_director_plan()
        del data["alignment_digest"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "alignment_digest"):
            VisualDirectorPlanV1Reader().read(data)

    def test_missing_opportunities_fails_closed(self):
        data = _visual_director_plan()
        del data["opportunities"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "opportunities"):
            VisualDirectorPlanV1Reader().read(data)

    def test_plan_id_not_text_fails_closed(self):
        data = _visual_director_plan()
        data["plan_id"] = 123
        with self.assertRaisesRegex(LegacyArtifactReadError, "plan_id"):
            VisualDirectorPlanV1Reader().read(data)

    def test_revision_not_integer_fails_closed(self):
        data = _visual_director_plan()
        data["revision"] = "not-int"
        with self.assertRaisesRegex(LegacyArtifactReadError, "revision"):
            VisualDirectorPlanV1Reader().read(data)

    def test_opportunities_not_list_fails_closed(self):
        data = _visual_director_plan()
        data["opportunities"] = "not-a-list"
        with self.assertRaisesRegex(LegacyArtifactReadError, "opportunities"):
            VisualDirectorPlanV1Reader().read(data)


# ===========================================================================
# LegacyEditMapV1Reader — driven by real build_edit_map()
# ===========================================================================

class LegacyEditMapV1ReaderTests(unittest.TestCase):
    def test_reads_real_edit_map_v1_from_producer(self):
        edit_map = _real_edit_map()
        loaded = LegacyEditMapV1Reader().read(edit_map)
        self.assertEqual(loaded["artifact_version"], "edit-map/1")
        self.assertIn("markdown", loaded)
        self.assertIn("csv_text", loaded)
        self.assertIn("rows", loaded)
        self.assertEqual(loaded["rows"][0]["素材"], "MG_01_时间线.mp4")

    def test_read_does_not_mutate_input(self):
        edit_map = _real_edit_map()
        before = json.dumps(edit_map, ensure_ascii=False, sort_keys=True)
        LegacyEditMapV1Reader().read(edit_map)
        after = json.dumps(edit_map, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_modifying_output_does_not_mutate_source(self):
        edit_map = _real_edit_map()
        loaded = LegacyEditMapV1Reader().read(edit_map)
        before = json.dumps(edit_map, ensure_ascii=False, sort_keys=True)
        loaded["rows"][0]["素材"] = "changed"
        loaded["markdown"] = "changed"
        after = json.dumps(edit_map, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_unsupported_version_fails_closed(self):
        edit_map = _real_edit_map()
        edit_map["artifact_version"] = "edit-map/2"
        with self.assertRaisesRegex(LegacyArtifactReadError, "unsupported"):
            LegacyEditMapV1Reader().read(edit_map)

    # --- field type validation (BLOCKER: EditMap row schema) ---

    def test_markdown_not_str_fails_closed(self):
        edit_map = _real_edit_map()
        edit_map["markdown"] = 123
        with self.assertRaisesRegex(LegacyArtifactReadError, "markdown"):
            LegacyEditMapV1Reader().read(edit_map)

    def test_csv_text_not_str_fails_closed(self):
        edit_map = _real_edit_map()
        edit_map["csv_text"] = 123
        with self.assertRaisesRegex(LegacyArtifactReadError, "csv_text"):
            LegacyEditMapV1Reader().read(edit_map)

    def test_rows_not_list_fails_closed(self):
        edit_map = _real_edit_map()
        edit_map["rows"] = "not-a-list"
        with self.assertRaisesRegex(LegacyArtifactReadError, "rows"):
            LegacyEditMapV1Reader().read(edit_map)

    def test_row_not_mapping_fails_closed(self):
        edit_map = _real_edit_map()
        edit_map["rows"][0] = "not-a-mapping"
        with self.assertRaisesRegex(LegacyArtifactReadError, "row"):
            LegacyEditMapV1Reader().read(edit_map)

    def test_row_missing_canonical_key_fails_closed(self):
        edit_map = _real_edit_map()
        del edit_map["rows"][0]["素材"]
        with self.assertRaisesRegex(LegacyArtifactReadError, "素材"):
            LegacyEditMapV1Reader().read(edit_map)

    def test_row_value_not_str_fails_closed(self):
        edit_map = _real_edit_map()
        edit_map["rows"][0]["素材"] = 123
        with self.assertRaisesRegex(LegacyArtifactReadError, "素材"):
            LegacyEditMapV1Reader().read(edit_map)


if __name__ == "__main__":
    unittest.main()