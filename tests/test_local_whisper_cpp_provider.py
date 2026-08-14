import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from deeptalk_studio.transcription.local_whisper_cpp import (
    LocalWhisperCppTranscriptionProvider,
    WhisperCppBootstrapError,
    WhisperCppInstallation,
)
from deeptalk_studio.transcription_chunking import (
    TranscriptionChunk,
    TranscriptionChunkPlan,
    load_local_whisper_chunk_profile,
)


class FakeBootstrap:
    def __init__(self, root):
        self.root = root
        runtime = root / "bin" / "whisper-cli"
        model = root / "model" / "ggml-medium.bin"
        runtime.parent.mkdir(parents=True)
        model.parent.mkdir(parents=True)
        runtime.write_text("runtime", encoding="utf-8")
        model.write_bytes(b"medium")
        self.installation = WhisperCppInstallation(
            runtime_path=runtime,
            model_path=model,
            provenance_path=root / "provenance.json",
            cache_root=root,
            runtime_version="1.9.2",
            source_commit="source-commit",
            build_identity="1.9.2+runtime-sha256:test",
            model_name="medium",
            model_sha256=hashlib.sha256(b"medium").hexdigest(),
            model_bytes=6,
            acceleration="Apple Silicon Metal",
            bootstrap_status="verified",
        )

    def ensure(self):
        return self.installation


def build_plan(root):
    chunks = []
    for index in range(2):
        path = root / f"chunk-{index}.wav"
        path.write_bytes(b"pcm")
        chunks.append(
            TranscriptionChunk(
                chunk_index=index,
                start_sample=index * 100,
                end_sample=(index + 1) * 100,
                sample_rate=100,
                extracted_start_seconds=Decimal(index),
                extracted_end_seconds=Decimal(index + 1),
                media_start_seconds=Decimal(index),
                media_end_seconds=Decimal(index + 1),
                selection_mode="safe_pause",
                search_start_sample=0,
                search_end_sample=100,
                boundary_score="score",
                boundary_evidence_digest="e" * 64,
                chunk_digest="c" * 64,
                profile_digest="p" * 64,
                path=path,
            )
        )
    return TranscriptionChunkPlan(
        profile_version="transcription-chunk-profile/1",
        profile_digest="p" * 64,
        extracted_audio_digest="a" * 64,
        mapping_digest="m" * 64,
        chunks=tuple(chunks),
        boundaries=(),
        digest="plan-digest",
    )


class LocalWhisperCppProviderTests(unittest.TestCase):
    def test_local_provider_declares_a_long_form_chunk_profile(self):
        profile = load_local_whisper_chunk_profile()
        self.assertEqual(profile["profile_version"], "transcription-chunk-profile/local-whisper-cpp/1")
        self.assertGreater(profile["request_cap_bytes"], 24 * 1024 * 1024)
        self.assertEqual(LocalWhisperCppTranscriptionProvider.preferred_sample_rate, 24000)

    def test_real_runtime_token_offsets_are_preserved_across_chunks_without_api_key(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = build_plan(root)
            bootstrap = FakeBootstrap(root / "install")

            def runner(command, **_kwargs):
                chunk = int(Path(command[command.index("--file") + 1]).stem.rsplit("-", 1)[1])
                output = Path(command[command.index("--output-file") + 1]).with_suffix(".json")
                output.write_text(
                    json.dumps(
                        {
                            "model": {"type": "medium"},
                            "result": {"language": "zh"},
                            "transcription": [
                                {
                                    "tokens": [
                                        {
                                            "text": "第一" if chunk == 0 else "第二",
                                            "offsets": {"from": 125, "to": 250},
                                            "p": 0.8,
                                        }
                                    ]
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return SimpleNamespace(stdout="", stderr="M4 Metal")

            with patch.dict("os.environ", {}, clear=True):
                result = LocalWhisperCppTranscriptionProvider(
                    bootstrap=bootstrap, runner=runner, clock=iter([0.0, 2.0]).__next__
                ).transcribe(
                    {"artifact_digest": "audio-digest", "duration_seconds": "2"},
                    plan,
                    "zh",
                    "medium",
                )

            self.assertEqual(result.timestamp_granularity, "token")
            self.assertEqual([unit.provider_order for unit in result.units], [0, 1])
            self.assertEqual([unit.local_start_seconds for unit in result.units], [Decimal("0.125")] * 2)
            self.assertEqual(result.raw_metadata["timestamp_provenance"], "whisper.cpp runtime token offsets from full JSON")
            self.assertEqual(result.raw_metadata["runtime_seconds"], 2.0)
            self.assertEqual(result.provider_model_version, "1.9.2+source-commit")

    def test_missing_token_timing_fails_closed_without_segment_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = build_plan(root)
            bootstrap = FakeBootstrap(root / "install")

            def runner(command, **_kwargs):
                output = Path(command[command.index("--output-file") + 1]).with_suffix(".json")
                output.write_text(
                    json.dumps({"transcription": [{"text": "只有段落"}]}), encoding="utf-8"
                )

            with self.assertRaisesRegex(WhisperCppBootstrapError, "缺少真实 token 时间戳"):
                LocalWhisperCppTranscriptionProvider(bootstrap=bootstrap, runner=runner).transcribe(
                    {"artifact_digest": "audio-digest", "duration_seconds": "2"},
                    plan,
                    "zh",
                    "medium",
                )

    def test_overlapping_runtime_tokens_fail_closed_before_timed_transcript(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = build_plan(root)
            bootstrap = FakeBootstrap(root / "install")

            def runner(command, **_kwargs):
                output = Path(command[command.index("--output-file") + 1]).with_suffix(".json")
                output.write_text(
                    json.dumps(
                        {
                            "model": {"type": "medium"},
                            "result": {"language": "zh"},
                            "transcription": [
                                {
                                    "tokens": [
                                        {"text": "前", "offsets": {"from": 0, "to": 200}},
                                        {"text": "后", "offsets": {"from": 190, "to": 300}},
                                    ]
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return SimpleNamespace(stdout="", stderr="")

            with self.assertRaisesRegex(WhisperCppBootstrapError, "overlap"):
                LocalWhisperCppTranscriptionProvider(bootstrap=bootstrap, runner=runner).transcribe(
                    {"artifact_digest": "audio-digest", "duration_seconds": "2"},
                    plan,
                    "zh",
                    "medium",
                )


if __name__ == "__main__":
    unittest.main()
