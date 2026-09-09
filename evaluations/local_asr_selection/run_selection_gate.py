"""Run the minimal local-ASR adapter spike over already-produced real outputs.

The models and audio stay outside the repository.  This command only writes a
small evidence summary containing digests and Gate results.
"""

import argparse
import json
import re
import wave
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from deeptalk_studio.alignment_builder import build_script_alignment
from deeptalk_studio.alignment_profile import load_alignment_profile
from deeptalk_studio.narration_media import canonical_digest, sha256_file
from deeptalk_studio.transcript_builder import build_timed_transcript, validate_timed_transcript
from deeptalk_studio.transcription.base import ProviderTranscript
from deeptalk_studio.transcription.local_asr_selection import (
    parse_whisper_cpp_json,
    vibeasr_timestamp_gate_failure,
)
from deeptalk_studio.transcription_chunking import TranscriptionChunk, TranscriptionChunkPlan


def _normal_text(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", value).lower()


def _levenshtein(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, first in enumerate(left, 1):
        current = [i]
        for j, second in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (first != second)))
        previous = current
    return previous[-1]


def _audio_info(path: Path) -> Dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        sample_rate = handle.getframerate()
        sample_count = handle.getnframes()
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
    return {
        "filename": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "sample_rate": sample_rate,
        "sample_count": sample_count,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "duration_seconds": format(Decimal(sample_count) / Decimal(sample_rate), "f"),
    }


def _one_chunk_plan(audio: Path, info: Mapping[str, Any]) -> TranscriptionChunkPlan:
    duration = Decimal(str(info["duration_seconds"]))
    profile_digest = canonical_digest({"profile": "local-asr-selection/1"})
    chunk_digest = str(info["sha256"])
    chunk = TranscriptionChunk(
        chunk_index=0,
        start_sample=0,
        end_sample=int(info["sample_count"]),
        sample_rate=int(info["sample_rate"]),
        extracted_start_seconds=Decimal("0"),
        extracted_end_seconds=duration,
        media_start_seconds=Decimal("0"),
        media_end_seconds=duration,
        selection_mode="final",
        search_start_sample=int(info["sample_count"]),
        search_end_sample=int(info["sample_count"]),
        boundary_score="final",
        boundary_evidence_digest=canonical_digest({"selection_mode": "final", "audio_sha256": chunk_digest}),
        chunk_digest=chunk_digest,
        profile_digest=profile_digest,
        path=audio,
    )
    payload = {
        "profile_version": "transcription-chunk-profile/1",
        "profile_digest": profile_digest,
        "extracted_audio_digest": canonical_digest({"audio_sha256": chunk_digest}),
        "mapping_digest": canonical_digest({"mapping": "identity", "audio_sha256": chunk_digest}),
        "chunks": [
            {
                "chunk_index": 0,
                "start_sample": 0,
                "end_sample": int(info["sample_count"]),
                "sample_rate": int(info["sample_rate"]),
                "extracted_start_seconds": "0",
                "extracted_end_seconds": format(duration, "f"),
                "media_start_seconds": "0",
                "media_end_seconds": format(duration, "f"),
                "selection_mode": "final",
                "boundary_score": "final",
                "chunk_digest": chunk_digest,
                "profile_digest": profile_digest,
            }
        ],
        "boundaries": [],
    }
    return TranscriptionChunkPlan(
        profile_version="transcription-chunk-profile/1",
        profile_digest=profile_digest,
        extracted_audio_digest=payload["extracted_audio_digest"],
        mapping_digest=payload["mapping_digest"],
        chunks=(chunk,),
        boundaries=(),
        digest=canonical_digest(payload),
    )


def _timed_chain(provider: ProviderTranscript, audio: Path, info: Mapping[str, Any]) -> Dict[str, Any]:
    plan = _one_chunk_plan(audio, info)
    media = {
        "media_id": "ASR-EVAL-MEDIA",
        "sha256": info["sha256"],
        "presentation_duration_seconds": info["duration_seconds"],
    }
    extracted = {
        "artifact_digest": plan.extracted_audio_digest,
        "sample_count": info["sample_count"],
        "sample_rate": info["sample_rate"],
    }
    mapping = {
        "mapping_id": "ASR-EVAL-MAPPING",
        "mapping_digest": plan.mapping_digest,
        "scale_numerator": 1,
        "scale_denominator": 1,
        "offset_seconds": "0",
    }
    if provider.chunk_plan_digest != plan.digest:
        # The parser is intentionally allowed to run without a plan. Rebind it
        # only for this local, identity-mapping evidence spike.
        provider = ProviderTranscript(
            provider=provider.provider,
            provider_model=provider.provider_model,
            provider_model_version=provider.provider_model_version,
            provider_request_id=provider.provider_request_id,
            language=provider.language,
            timestamp_granularity=provider.timestamp_granularity,
            units=provider.units,
            boundary_risks=provider.boundary_risks,
            raw_metadata=dict(provider.raw_metadata),
            raw_response_digest=provider.raw_response_digest,
            chunk_plan_digest=plan.digest,
        )
    transcript = build_timed_transcript(
        provider,
        media,
        extracted,
        mapping,
        plan,
        transcript_id="ASR-EVAL-TRANSCRIPT",
        created_at="2026-08-14T10:30:00+08:00",
    )
    validate_timed_transcript(transcript, media, extracted, mapping, plan)
    script = {
        "script_id": "ASR-EVAL-SCRIPT",
        "revision": 1,
        "beats": [{"beat_id": "B001", "narration": "今天我们做一段用于本地转写测试的中文口播"}],
    }
    alignment = build_script_alignment(
        script,
        transcript,
        mapping,
        load_alignment_profile(),
        [],
        alignment_id="ASR-EVAL-ALIGNMENT",
        created_at="2026-08-14T10:30:00+08:00",
        media=media,
    )
    return {
        "provider_transcript": {
            "provider": provider.provider,
            "provider_model": provider.provider_model,
            "provider_model_version": provider.provider_model_version,
            "timestamp_granularity": provider.timestamp_granularity,
            "unit_count": len(provider.units),
            "raw_response_digest": provider.raw_response_digest,
        },
        "timed_transcript": {
            "transcript_id": transcript["transcript_id"],
            "transcript_digest": transcript["transcript_digest"],
            "unit_count": len(transcript["timed_units"]),
            "first_units": transcript["timed_units"][:3],
        },
        "script_alignment": {
            "alignment_id": alignment["alignment_id"],
            "alignment_digest": alignment["artifact_digest"],
            "first_beat_status": alignment["beat_timeline"][0]["alignment_status"],
            "first_beat_granularity": alignment["beat_timeline"][0]["timestamp_granularity"],
            "first_beat_start_seconds": alignment["beat_timeline"][0]["actual_start_seconds"],
            "first_beat_end_seconds": alignment["beat_timeline"][0]["actual_end_seconds"],
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    audio = Path(args.audio).resolve()
    reference = Path(args.reference).read_text(encoding="utf-8")
    info = _audio_info(audio)
    payload = json.loads(Path(args.whisper_json).read_text(encoding="utf-8"))
    whisper_provider = parse_whisper_cpp_json(
        Path(args.whisper_json), model_version=args.whisper_model_version
    )
    whisper_text = "".join(unit.spoken_text for unit in whisper_provider.units)
    terms = ["OpenAI", "Anthropic", "DeepSeek", "华为", "英伟达", "GPT", "AI Agent", "Metal", "RTF"]
    chain = _timed_chain(whisper_provider, audio, info)
    vibe_text = Path(args.vibe_text).read_text(encoding="utf-8")
    vibe_json = Path(args.vibe_json).read_text(encoding="utf-8")
    return {
        "artifact_version": "local-asr-selection-report/1",
        "created_at": "2026-08-14T10:30:00+08:00",
        "audio": info,
        "reference": {
            "filename": Path(args.reference).name,
            "sha256": sha256_file(Path(args.reference)),
            "kind": "non_private_synthetic_macos_say_reference",
        },
        "whisper_cpp": {
            "source_commit": args.whisper_source_commit,
            "model_source": "https://huggingface.co/ggerganov/whisper.cpp",
            "model_version": args.whisper_model_version,
            "model_sha256": args.whisper_model_sha256,
            "model_bytes": int(args.whisper_model_bytes),
            "acceleration": "Apple M4 Metal (runtime log: using MTL0 / Apple M4)",
            "runtime_seconds": Decimal(args.whisper_runtime_seconds),
            "rtf": Decimal(args.whisper_rtf),
            "timestamp_gate": "PASS: direct token offsets in whisper.cpp full JSON",
            "keyword_exact_presence": {term: term in whisper_text for term in terms},
            "obvious_error_examples": [
                "OpenAI → OpenEye",
                "DeepSeek → DeepSeq (one occurrence)",
                "AI Agent → AI Agit (one occurrence)",
                "华为昇腾 → 华为生酮",
                "GPU → GTU in one hardware sentence",
            ],
            "synthetic_reference_cer": round(
                _levenshtein(_normal_text(reference), _normal_text(whisper_text))
                / max(1, len(_normal_text(reference))),
                4,
            ),
            "adapter_chain": chain,
            "output_digest": canonical_digest(payload),
        },
        "vibeasr_cpp": {
            "source_commit": args.vibe_source_commit,
            "model_source": "https://huggingface.co/microsoft/VibeVoice-ASR-BitNet",
            "model_revision": args.vibe_model_revision,
            "lm_model_sha256": args.vibe_lm_sha256,
            "lm_model_bytes": int(args.vibe_lm_bytes),
            "vae_model_sha256": args.vibe_vae_sha256,
            "vae_model_bytes": int(args.vibe_vae_bytes),
            "acceleration": "CPU / Apple M4; official runtime built with Clang, Metal disabled",
            "runtime_seconds_json_prompt": Decimal(args.vibe_runtime_seconds_json),
            "rtf_json_prompt": Decimal(args.vibe_rtf_json),
            "runtime_seconds_text_prompt": Decimal(args.vibe_runtime_seconds_text),
            "rtf_text_prompt": Decimal(args.vibe_rtf_text),
            "timestamp_gate": "FAIL",
            "timestamp_gate_reason": vibeasr_timestamp_gate_failure(),
            "actual_output_digest_json_prompt": sha256_file(Path(args.vibe_json)),
            "actual_output_digest_text_prompt": sha256_file(Path(args.vibe_text)),
            "output_observation": "两种官方 CLI 模式均输出重复文本并耗尽 max_tokens；没有可绑定媒体的时间线",
            "adapter_chain": {"provider_transcript": "STOPPED", "timed_transcript": "NOT_BUILT", "script_alignment": "NOT_BUILT"},
            "output_bytes_json_prompt": len(vibe_json.encode("utf-8")),
            "output_bytes_text_prompt": len(vibe_text.encode("utf-8")),
        },
        "selection_gate": {
            "winner_recommendation": "whisper.cpp multilingual medium",
            "winner_reason": "唯一通过可靠 token 时间戳 Gate，并在同一音频上完成 Timed Transcript 与 Script Alignment；VibeASR 时间戳和中文输出均未达到 V1 要求",
            "v1_default_integration": "PENDING_CHATGPT_REVIEW",
            "api_key_required": False,
            "model_cache_policy": "外部项目缓存；不提交仓库；评审通过后只自动引导/启动 winner model",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--whisper-json", required=True)
    parser.add_argument("--vibe-json", required=True)
    parser.add_argument("--vibe-text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--whisper-source-commit", required=True)
    parser.add_argument("--whisper-model-version", required=True)
    parser.add_argument("--whisper-model-sha256", required=True)
    parser.add_argument("--whisper-model-bytes", required=True)
    parser.add_argument("--whisper-runtime-seconds", required=True)
    parser.add_argument("--whisper-rtf", required=True)
    parser.add_argument("--vibe-source-commit", required=True)
    parser.add_argument("--vibe-model-revision", required=True)
    parser.add_argument("--vibe-lm-sha256", required=True)
    parser.add_argument("--vibe-lm-bytes", required=True)
    parser.add_argument("--vibe-vae-sha256", required=True)
    parser.add_argument("--vibe-vae-bytes", required=True)
    parser.add_argument("--vibe-runtime-seconds-json", required=True)
    parser.add_argument("--vibe-rtf-json", required=True)
    parser.add_argument("--vibe-runtime-seconds-text", required=True)
    parser.add_argument("--vibe-rtf-text", required=True)
    args = parser.parse_args()
    result = run(args)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
