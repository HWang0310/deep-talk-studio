import json
import subprocess
import sys
import unittest
from pathlib import Path

from deeptalk_studio.alignment_profile import load_alignment_profile
from evaluations.audio_alignment_edit_bridge.run_alignment_calibration import run_alignment_calibration


ROOT = Path(__file__).resolve().parents[1]


class AlignmentCalibrationTests(unittest.TestCase):
    def test_candidate_cannot_be_accepted_without_false_precision_suite(self):
        result = run_alignment_calibration(load_alignment_profile())
        self.assertTrue(result.case("A").all_beats_aligned)
        self.assertTrue(result.case("C").later_beats_recovered)
        self.assertEqual(result.false_ready_cases, ())

    def test_required_cases_and_boundary_guards_are_evidenced(self):
        result = run_alignment_calibration(load_alignment_profile())
        self.assertEqual(
            {case.case_id for case in result.cases},
            {"A", "B", "C", "D", "E", "F", "S", "T", "U", "AH", "CR1", "CR2", "CR3"},
        )
        self.assertTrue(result.case("CR2").boundary_risk_protected)
        self.assertTrue(result.case("CR3").later_beats_recovered)
        self.assertEqual(result.calibration_status, "accepted")

    def test_evidence_is_bound_and_repeat_is_identical(self):
        profile = load_alignment_profile()
        evidence = json.loads((ROOT / "evaluations/audio-alignment-edit-bridge/alignment-profile-evidence.json").read_text())
        self.assertEqual(evidence["accepted_profile_digest"], profile["profile_digest"])
        process = subprocess.run(
            [sys.executable, str(ROOT / "evaluations/audio-alignment-edit-bridge/run_alignment_calibration.py"), "--verify-repeat"],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("repeat: identical", process.stdout)


if __name__ == "__main__":
    unittest.main()
