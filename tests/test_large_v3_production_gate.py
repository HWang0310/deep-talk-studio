import unittest
import subprocess
import sys
from pathlib import Path

from evaluations.local_asr_selection.run_large_v3_production_gate import (
    build_overlap_report,
    monitor_snapshot,
)


class LargeV3ProductionGateTests(unittest.TestCase):
    def test_runner_is_directly_executable_from_the_repository_root(self):
        runner = Path(__file__).resolve().parents[1] / "evaluations" / "local_asr_selection" / "run_large_v3_production_gate.py"
        result = subprocess.run([sys.executable, str(runner), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("full-session", result.stdout)

    def test_overlap_report_requires_every_raw_audit_field(self):
        overlap = {
            "chunk_id": "chunk-0000",
            "chunk_index": 0,
            "previous_segment_index": 1,
            "current_segment_index": 1,
            "same_segment": True,
            "previous_raw_token_index": 2,
            "current_raw_token_index": 3,
            "previous_provider_order": 2,
            "current_provider_order": 3,
            "previous_token_text": "前",
            "current_token_text": "后",
            "previous_raw_start_seconds": "0",
            "previous_raw_end_seconds": "0.2",
            "current_raw_start_seconds": "0.19",
            "current_raw_end_seconds": "0.3",
            "overlap_duration_seconds": "0.01",
            "previous_is_control_token": False,
            "current_is_control_token": False,
            "is_chunk_boundary": False,
            "model": "large-v3",
            "dtw_preset": "large.v3",
            "runtime_version": "1.9.2",
            "raw_response_digest": "a" * 64,
        }
        report = build_overlap_report([overlap], audio_sha256="b" * 64)
        self.assertEqual(report["artifact_version"], "local-whisper-large-v3-overlap-evidence/1")
        self.assertEqual(report["overlap_count"], 1)
        self.assertEqual(report["overlaps"][0], overlap)

    def test_liveness_snapshot_keeps_live_renderer_running(self):
        record = monitor_snapshot(
            pid=123,
            elapsed_seconds=120.0,
            alive=True,
            output_bytes=4096,
            stage="remotion_render",
        )
        self.assertEqual(record["state"], "running")
        self.assertEqual(record["pid"], 123)
        self.assertEqual(record["stage"], "remotion_render")
        self.assertEqual(record["output_bytes"], 4096)


if __name__ == "__main__":
    unittest.main()
