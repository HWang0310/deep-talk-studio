"""Phase A tests: read-only compatibility readers for legacy artifacts.

Readers must be versioned, fail closed on unknown versions or tampered
digests, and never write anything back to the artifact.
"""
from __future__ import annotations

import copy
import hashlib
import json
import unittest

from deeptalk_studio.legacy_artifact_readers import (
    LegacyArtifactReadError,
    LegacyEditMapV1Reader,
    VisualDirectorPlanV1Reader,
)


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


def _digest_without(data: dict, field: str) -> str:
    copy_data = dict(data)
    copy_data.pop(field, None)
    return hashlib.sha256(
        json.dumps(copy_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _edit_map() -> dict:
    data = {
        "artifact_version": "edit-map/1",
        "map_digest": "",
        "asset_manifest_digest": "c" * 64,
        "rows": [
            {
                "sequence": 1,
                "span_id": "ST001",
                "actual_start_seconds": "10.0",
                "actual_end_seconds": "20.0",
                "decision": "MG_MOTION",
                "asset_filename": "MG_01_时间线.mp4",
                "spoken_summary": "用结构动画解释时间变化。",
                "placement_advice": "全屏覆盖，结束后回到人物。",
            }
        ],
    }
    data["map_digest"] = _digest_without(data, "map_digest")
    return data


class VisualDirectorPlanV1ReaderTests(unittest.TestCase):
    def test_reads_visual_director_plan_v1(self):
        reader = VisualDirectorPlanV1Reader()
        loaded = reader.read(_visual_director_plan())
        self.assertEqual(loaded["artifact_version"], "visual-director-plan/1")
        self.assertEqual(loaded["plan_id"], "VD-PLAN-001")
        self.assertEqual(loaded["opportunities"][0]["decision"], "KEEP_A_ROLL")

    def test_reads_does_not_mutate_input(self):
        data = _visual_director_plan()
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        VisualDirectorPlanV1Reader().read(data)
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


class LegacyEditMapV1ReaderTests(unittest.TestCase):
    def test_reads_edit_map_v1(self):
        reader = LegacyEditMapV1Reader()
        loaded = reader.read(_edit_map())
        self.assertEqual(loaded["artifact_version"], "edit-map/1")
        self.assertEqual(loaded["rows"][0]["asset_filename"], "MG_01_时间线.mp4")

    def test_read_does_not_mutate_input(self):
        data = _edit_map()
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        LegacyEditMapV1Reader().read(data)
        after = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertEqual(before, after)

    def test_unsupported_version_fails_closed(self):
        data = _edit_map()
        data["artifact_version"] = "edit-map/2"
        with self.assertRaisesRegex(LegacyArtifactReadError, "unsupported"):
            LegacyEditMapV1Reader().read(data)

    def test_tampered_map_digest_fails_closed(self):
        data = _edit_map()
        data["map_digest"] = "e" * 64
        with self.assertRaisesRegex(LegacyArtifactReadError, "digest"):
            LegacyEditMapV1Reader().read(data)


if __name__ == "__main__":
    unittest.main()