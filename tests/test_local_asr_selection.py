import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.transcription.local_asr_selection import (
    LocalASRSelectionError,
    parse_whisper_cpp_json,
    vibeasr_timestamp_gate_failure,
)


class LocalASRSelectionTests(unittest.TestCase):
    def write_json(self, value):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "whisper.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_whisper_parser_preserves_real_token_offsets(self):
        path = self.write_json(
            {
                "model": {"type": "medium"},
                "result": {"language": "zh"},
                "transcription": [
                    {
                        "tokens": [
                            {"text": "[_BEG_]", "offsets": {"from": 0, "to": 0}},
                            {"text": "今天", "offsets": {"from": 50, "to": 170}, "p": 0.9},
                            {"text": "我们", "offsets": {"from": 250, "to": 500}, "p": 0.8},
                        ]
                    }
                ],
            }
        )
        result = parse_whisper_cpp_json(path, model_version="test-commit")
        self.assertEqual(result.timestamp_granularity, "token")
        self.assertEqual([unit.spoken_text for unit in result.units], ["今天", "我们"])
        self.assertEqual(result.units[0].local_start_seconds, Decimal("0.05"))
        self.assertEqual(result.units[1].local_end_seconds, Decimal("0.5"))

    def test_whisper_parser_supports_production_chunk_order_and_request_identity(self):
        path = self.write_json(
            {
                "model": {"type": "medium"},
                "result": {"language": "zh"},
                "transcription": [
                    {"tokens": [{"text": "真实", "offsets": {"from": 50, "to": 170}}]}
                ],
            }
        )
        result = parse_whisper_cpp_json(
            path,
            chunk_index=1,
            model_version="1.9.2+commit",
            provider_order_start=7,
            provider_request_id="local-whisper-cpp-run",
        )
        self.assertEqual(result.units[0].provider_order, 7)
        self.assertEqual(result.units[0].chunk_index, 1)
        self.assertEqual(result.provider_request_id, "local-whisper-cpp-run")

    def test_parser_rejects_missing_token_offsets(self):
        path = self.write_json(
            {"transcription": [{"text": "只有段落"}], "result": {"language": "zh"}}
        )
        with self.assertRaises(LocalASRSelectionError):
            parse_whisper_cpp_json(path, model_version="test-commit")

    def test_vibe_timestamp_reason_never_accepts_prompt_generated_times(self):
        reason = vibeasr_timestamp_gate_failure()
        self.assertIn("machine-owned media timestamp", reason)
        self.assertIn("language-model prompt/output", reason)


if __name__ == "__main__":
    unittest.main()
