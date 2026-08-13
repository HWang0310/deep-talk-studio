import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.transcription.openai import (
    OpenAISDKTranscriptionTransport,
    OpenAITranscriptionProvider,
    TranscriptionCapabilityError,
    TranscriptionEnvironmentError,
)
from deeptalk_studio.transcription_chunking import (
    load_transcription_chunk_profile,
    plan_transcription_chunks,
    profile_with_overrides,
)
from tests.test_transcription_chunking import mapping, write_pcm


class FakeTransport:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def create(self, file_path, model, response_format, timestamp_granularities):
        self.calls.append(
            {
                "file_path": file_path,
                "model": model,
                "response_format": response_format,
                "timestamp_granularities": timestamp_granularities,
            }
        )
        if self.error:
            raise RuntimeError(self.error)
        return self.responses.pop(0)


class OpenAITranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audio = write_pcm(Path(self.temp.name) / "audio.wav", [12000] * 1400)
        self.profile = profile_with_overrides(
            load_transcription_chunk_profile(), request_cap_bytes=1244, search_window_ms=600
        )
        self.plan = plan_transcription_chunks(self.audio, mapping(), self.profile)

    def tearDown(self):
        self.temp.cleanup()

    def _responses(self):
        responses = []
        for index, chunk in enumerate(self.plan.chunks):
            duration = chunk.extracted_end_seconds - chunk.extracted_start_seconds
            responses.append(
                {
                    "task": "transcribe",
                    "language": "zh",
                    "duration": float(duration),
                    "words": [
                        {
                            "word": f"第{index}段",
                            "start": 0.0,
                            "end": float(min(duration, Decimal("0.2"))),
                        }
                    ],
                    "request_id": f"req-{index}",
                }
            )
        return responses

    def test_whisper_word_response_normalizes_without_provider_owned_status(self):
        transport = FakeTransport(self._responses())
        provider = OpenAITranscriptionProvider(api_key="test", transport=transport)
        result = provider.transcribe(self.audio, self.plan, "zh", "whisper-1")
        self.assertEqual(result.timestamp_granularity, "word")
        self.assertNotIn("alignment_status", result.raw_metadata)
        self.assertEqual(len(transport.calls), len(self.plan.chunks))
        self.assertTrue(all(call["response_format"] == "verbose_json" for call in transport.calls))
        self.assertTrue(all(call["timestamp_granularities"] == ["word"] for call in transport.calls))

    def test_real_segments_fall_back_to_coarse_provider_units(self):
        responses = []
        for index, chunk in enumerate(self.plan.chunks):
            duration = chunk.extracted_end_seconds - chunk.extracted_start_seconds
            responses.append({
                "segments": [{
                    "text": f"第{index}段完整话语",
                    "start": 0,
                    "end": float(min(duration, Decimal("0.2"))),
                }],
                "request_id": f"req-segment-{index}",
            })
        result = OpenAITranscriptionProvider(
            api_key="test", transport=FakeTransport(responses)
        ).transcribe(self.audio, self.plan, "zh", "whisper-1")
        self.assertEqual(result.timestamp_granularity, "segment")
        self.assertTrue(all(unit.spoken_text.endswith("完整话语") for unit in result.units))
        self.assertEqual(result.raw_metadata["selected_timestamp_granularity"], "segment")

    def test_words_are_preferred_when_response_also_contains_segments(self):
        responses = self._responses()
        for response in responses:
            response["segments"] = [{"text": "不得选我", "start": 0, "end": 0.1}]
        result = OpenAITranscriptionProvider(
            api_key="test", transport=FakeTransport(responses)
        ).transcribe(self.audio, self.plan, "zh", "whisper-1")
        self.assertEqual(result.timestamp_granularity, "word")
        self.assertTrue(all(unit.spoken_text != "不得选我" for unit in result.units))

    def test_response_without_words_or_segments_fails_closed(self):
        malformed = FakeTransport([{"text": "没有真实时间戳"}] * len(self.plan.chunks))
        with self.assertRaisesRegex(TranscriptionCapabilityError, "word 或 segment"):
            OpenAITranscriptionProvider(api_key="test", transport=malformed).transcribe(
                self.audio, self.plan, "zh", "whisper-1"
            )

    def test_model_without_timestamps_fails_instead_of_fabricating_precision(self):
        provider = OpenAITranscriptionProvider(api_key="test", transport=FakeTransport())
        with self.assertRaisesRegex(TranscriptionCapabilityError, "时间戳"):
            provider.transcribe(self.audio, self.plan, "zh", "gpt-transcribe")

    def test_default_sdk_transport_converts_typed_response_without_leaking_key(self):
        class Response:
            def model_dump(self):
                return {"words": [{"word": "测试", "start": 0, "end": 0.2}], "request_id": "req-real-shape"}
        class Transcriptions:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return Response()
        transport = OpenAISDKTranscriptionTransport(api_key="secret", client_factory=lambda **_: type("Client", (), {"audio": type("Audio", (), {"transcriptions": Transcriptions()})()})())
        with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
            result = transport.create(handle.name, "whisper-1", "verbose_json", ["word"])
        self.assertEqual(result["request_id"], "req-real-shape")

    def test_chunk_local_time_is_preserved_and_risk_is_projected_only_once(self):
        result = OpenAITranscriptionProvider(
            api_key="test", transport=FakeTransport(self._responses())
        ).transcribe(self.audio, self.plan, "zh", "whisper-1")
        self.assertEqual(result.units[0].local_start_seconds, Decimal("0.0"))
        if len(result.units) > 1:
            self.assertEqual(result.units[1].local_start_seconds, Decimal("0.0"))
            self.assertGreater(self.plan.chunks[1].extracted_start_seconds, 0)
        known = {risk.risk_id for risk in result.boundary_risks}
        self.assertTrue(all(set(unit.boundary_risk_ids).issubset(known) for unit in result.units))

    def test_malformed_response_and_api_error_are_cleanly_distinguished_and_redacted(self):
        malformed = FakeTransport([{"text": "no timestamps"}] * len(self.plan.chunks))
        with self.assertRaises(TranscriptionCapabilityError):
            OpenAITranscriptionProvider(api_key="secret", transport=malformed).transcribe(
                self.audio, self.plan, "zh", "whisper-1"
            )
        failing = FakeTransport(error="authorization secret")
        with self.assertRaises(TranscriptionEnvironmentError) as context:
            OpenAITranscriptionProvider(api_key="secret", transport=failing).transcribe(
                self.audio, self.plan, "zh", "whisper-1"
            )
        self.assertNotIn("secret", str(context.exception))


if __name__ == "__main__":
    unittest.main()
