"""V2 Phase C tests: candidate-placement-plan/1 storage.

Proves the artifact is immutable, digest-bound and fail-closed:
  - save -> load round-trip equivalence
  - duplicate save fails (no overwrite)
  - digest tamper fails
  - unknown field fails
  - duplicate candidate_id fails
  - UNPLACEABLE never carries a fabricated final_placement
  - out-of-window / duration-mismatched final_placement fails
  - unsafe path fails
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.placement_planner import build_candidate_placement_plan
from deeptalk_studio.placement_storage import (
    PlacementStorageError,
    load_candidate_placement_plan,
    save_candidate_placement_plan,
)


def _opportunity() -> dict:
    return {
        "opportunity_id": "VO-storage-01",
        "spoken_semantics": "Storage span.",
        "visual_purpose": "Illustrate storage.",
        "a_roll_window": {"start_ms": 10000, "end_ms": 20000},
        "target_duration_ms": 3000,
        "language": "zh-CN",
        "canvas": {"width": 1920, "height": 1080},
        "factual_context": [],
    }


def _plan() -> dict:
    return build_candidate_placement_plan(
        _opportunity(),
        [
            {
                "candidate_id": "cand-a",
                "candidate_status": "READY",
                "duration_ms": 4000,
                "intrinsic_placement_hint": {"start_ms": 11000, "end_ms": 15000},
            },
            {
                "candidate_id": "cand-b",
                "candidate_status": "READY",
                "duration_ms": 20000,
            },
        ],
    )


def _digest(value: dict) -> str:
    payload = {key: item for key, item in value.items() if key != "placement_plan_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class RoundTripTests(unittest.TestCase):
    def test_save_then_load_is_equivalent(self):
        plan = _plan()
        with tempfile.TemporaryDirectory() as root:
            path = save_candidate_placement_plan(plan, Path(root))
            self.assertEqual(path.name, "candidate-placement-plan.json")
            self.assertEqual(path.parent.name, plan["placement_plan_id"])
            loaded = load_candidate_placement_plan(path)
        self.assertEqual(loaded, plan)

    def test_saved_json_is_sorted_and_digest_bound(self):
        plan = _plan()
        with tempfile.TemporaryDirectory() as root:
            path = save_candidate_placement_plan(plan, Path(root))
            raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(raw, plan)
        self.assertEqual(raw["placement_plan_digest"], _digest(raw))

    def test_duplicate_save_fails_closed(self):
        plan = _plan()
        with tempfile.TemporaryDirectory() as root:
            save_candidate_placement_plan(plan, Path(root))
            with self.assertRaises(PlacementStorageError):
                save_candidate_placement_plan(plan, Path(root))


class TamperTests(unittest.TestCase):
    def test_digest_tamper_fails(self):
        plan = _plan()
        mutated = copy.deepcopy(plan)
        mutated["placement_plan_digest"] = "f" * 64
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PlacementStorageError):
                save_candidate_placement_plan(mutated, Path(root))

    def test_digest_mismatch_after_field_change_fails(self):
        plan = _plan()
        mutated = copy.deepcopy(plan)
        mutated["opportunity_id"] = "VO-tampered"
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PlacementStorageError):
                save_candidate_placement_plan(mutated, Path(root))

    def test_file_level_tamper_fails_on_load(self):
        plan = _plan()
        with tempfile.TemporaryDirectory() as root:
            path = save_candidate_placement_plan(plan, Path(root))
            tampered = json.loads(path.read_text(encoding="utf-8"))
            tampered["placements"][0]["final_placement"]["start_ms"] = 0
            os.remove(path)
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(PlacementStorageError):
                load_candidate_placement_plan(path)


class SchemaRejectionTests(unittest.TestCase):
    def _reject(self, mutate):
        plan = _plan()
        mutate(plan)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PlacementStorageError):
                save_candidate_placement_plan(plan, Path(root))

    def test_unknown_top_level_field_fails(self):
        self._reject(lambda plan: plan.update({"winner_candidate_id": "cand-a"}))

    def test_unknown_placement_field_fails(self):
        self._reject(lambda plan: plan["placements"][0].update({"rank": 1}))

    def test_duplicate_candidate_id_fails(self):
        def mutate(plan):
            clone = copy.deepcopy(plan["placements"][0])
            clone["candidate_id"] = plan["placements"][1]["candidate_id"]
            plan["placements"].append(clone)
        self._reject(mutate)

    def test_unplaceable_with_fabricated_placement_fails(self):
        def mutate(plan):
            for entry in plan["placements"]:
                if entry["status"] == "UNPLACEABLE":
                    entry["final_placement"] = {"start_ms": 10000, "end_ms": 20000}
        self._reject(mutate)

    def test_placed_out_of_window_fails(self):
        def mutate(plan):
            for entry in plan["placements"]:
                if entry["status"] == "PLACED":
                    entry["final_placement"] = {"start_ms": 0, "end_ms": 4000}
            plan["placement_plan_digest"] = _digest(plan)
        self._reject(mutate)

    def test_placement_duration_mismatch_fails(self):
        def mutate(plan):
            for entry in plan["placements"]:
                if entry["status"] == "PLACED":
                    entry["final_placement"] = {"start_ms": 10000, "end_ms": 10001}
            plan["placement_plan_digest"] = _digest(plan)
        self._reject(mutate)

    def test_bad_artifact_version_fails(self):
        def mutate(plan):
            plan["artifact_version"] = "candidate-placement-plan/2"
            plan["placement_plan_digest"] = _digest(plan)
        self._reject(mutate)

    def test_bad_plan_id_fails(self):
        def mutate(plan):
            plan["placement_plan_id"] = "NOT-A-PLAN"
            plan["placement_plan_digest"] = _digest(plan)
        self._reject(mutate)

    def test_invalid_status_fails(self):
        def mutate(plan):
            plan["placements"][0]["status"] = "PENDING"
            plan["placement_plan_digest"] = _digest(plan)
        self._reject(mutate)

    def test_non_mapping_fails(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PlacementStorageError):
                save_candidate_placement_plan(["not", "a", "plan"], Path(root))


class PathSafetyTests(unittest.TestCase):
    def test_load_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / ("CPP-" + "0" * 24) / "candidate-placement-plan.json"
            with self.assertRaises(PlacementStorageError):
                load_candidate_placement_plan(missing)

    def test_load_wrong_filename_fails(self):
        plan = _plan()
        with tempfile.TemporaryDirectory() as root:
            path = save_candidate_placement_plan(plan, Path(root))
            moved = path.parent / "placement.json"
            path.rename(moved)
            with self.assertRaises(PlacementStorageError):
                load_candidate_placement_plan(moved)

    def test_load_directory_mismatch_fails(self):
        plan = _plan()
        with tempfile.TemporaryDirectory() as root:
            path = save_candidate_placement_plan(plan, Path(root))
            target = Path(root) / ("CPP-" + "0" * 24)
            target.mkdir()
            moved = target / "candidate-placement-plan.json"
            path.rename(moved)
            with self.assertRaises(PlacementStorageError):
                load_candidate_placement_plan(moved)


if __name__ == "__main__":
    unittest.main()
