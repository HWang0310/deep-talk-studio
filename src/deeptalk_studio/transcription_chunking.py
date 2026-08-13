"""Deterministic PCM natural-pause transcription request chunk planning."""

import hashlib
import json
import math
import os
import struct
import wave
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .audio_timestamp_mapping import map_extracted_seconds
from .narration_media import canonical_digest, sha256_file
from .schema import _enum, _integer, _object


PROFILE_PATH = Path(__file__).resolve().parents[2] / "config" / "transcription-chunk-profile.json"


class TranscriptionChunkingError(ValueError):
    """The chunk profile, PCM evidence, or derived plan is invalid."""


TRANSCRIPTION_CHUNK_PROFILE_SCHEMA = _object(
    {
        "profile_version": _enum(["transcription-chunk-profile/1"]),
        "provider_hard_limit_bytes": _integer(1),
        "request_cap_bytes": _integer(45),
        "wav_header_bytes": _integer(44),
        "search_window_ms": _integer(1),
        "analysis_window_ms": _integer(1),
        "hop_ms": _integer(1),
        "safe_pause_min_ms": _integer(1),
        "safe_pause_threshold_dbfs": {"type": "integer"},
        "safe_pause_threshold_mean_square": _integer(),
        "fallback_interval_ms": _integer(1),
        "risk_guard_ms": _integer(1),
        "overlap_ms": _integer(),
        "use_previous_chunk_prompt": {"type": "boolean"},
        "rounding_mode": _enum(["half_up"]),
    }
)


@dataclass(frozen=True)
class TranscriptionChunk:
    chunk_index: int
    start_sample: int
    end_sample: int
    sample_rate: int
    extracted_start_seconds: Decimal
    extracted_end_seconds: Decimal
    media_start_seconds: Decimal
    media_end_seconds: Decimal
    selection_mode: str
    search_start_sample: int
    search_end_sample: int
    boundary_score: str
    boundary_evidence_digest: str
    chunk_digest: str
    profile_digest: str
    path: Path


@dataclass(frozen=True)
class TranscriptionBoundary:
    boundary_index: int
    boundary_sample: int
    selection_mode: str
    boundary_risk: str
    reason: str
    guard_start_seconds: Optional[Decimal]
    guard_end_seconds: Optional[Decimal]
    evidence_digest: str

    @property
    def guard_duration_seconds(self) -> Decimal:
        if self.guard_start_seconds is None or self.guard_end_seconds is None:
            return Decimal(0)
        return self.guard_end_seconds - self.guard_start_seconds


@dataclass(frozen=True)
class TranscriptionChunkPlan:
    profile_version: str
    profile_digest: str
    extracted_audio_digest: str
    mapping_digest: str
    chunks: Tuple[TranscriptionChunk, ...]
    boundaries: Tuple[TranscriptionBoundary, ...]
    digest: str


def _profile_digest(profile: Mapping[str, Any]) -> str:
    return canonical_digest(dict(profile))


def load_transcription_chunk_profile(path: Path = PROFILE_PATH) -> Dict[str, Any]:
    try:
        profile = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TranscriptionChunkingError("无法读取 transcription chunk profile") from exc
    _validate_profile(profile)
    profile["profile_digest"] = _profile_digest(profile)
    return profile


def profile_with_overrides(profile: Mapping[str, Any], **overrides: Any) -> Dict[str, Any]:
    value = deepcopy(dict(profile))
    value.pop("profile_digest", None)
    value.update(overrides)
    _validate_profile(value)
    value["profile_digest"] = _profile_digest(value)
    return value


def _validate_profile(profile: Mapping[str, Any]) -> None:
    base = {key: value for key, value in profile.items() if key != "profile_digest"}
    from .validation import ReportValidationError, validate_json_schema

    try:
        validate_json_schema(base, TRANSCRIPTION_CHUNK_PROFILE_SCHEMA, "chunk_profile")
    except ReportValidationError as exc:
        raise TranscriptionChunkingError(str(exc)) from exc
    if base["wav_header_bytes"] != 44:
        raise TranscriptionChunkingError("首版只支持 canonical 44-byte PCM WAV header")
    if base["overlap_ms"] != 0 or base["use_previous_chunk_prompt"]:
        raise TranscriptionChunkingError("Profile 1 不使用 overlap 或 previous-chunk prompt")
    if base["request_cap_bytes"] > 24 * 1024 * 1024:
        raise TranscriptionChunkingError("request cap 不能超过 24 MiB")
    if base["provider_hard_limit_bytes"] != 25 * 1024 * 1024:
        raise TranscriptionChunkingError("Profile 1 将 provider 25 MB 上限精确记录为 25 MiB")
    if base["request_cap_bytes"] >= base["provider_hard_limit_bytes"]:
        raise TranscriptionChunkingError("request cap 必须小于 provider hard limit")


def _read_pcm(path: Path) -> Tuple[int, int, int, List[Tuple[int, ...]]]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            count = handle.getnframes()
            raw = handle.readframes(count)
    except (OSError, wave.Error) as exc:
        raise TranscriptionChunkingError("无法读取 PCM WAV") from exc
    if width != 2:
        raise TranscriptionChunkingError("Profile 1 只支持 pcm_s16le chunk planning")
    values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    frames = [tuple(values[i : i + channels]) for i in range(0, len(values), channels)]
    return rate, channels, width, frames


def _samples(milliseconds: int, rate: int) -> int:
    return int((Decimal(milliseconds) * Decimal(rate) / Decimal(1000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _window_energies(
    frames: Sequence[Tuple[int, ...]], start: int, end: int, window: int, hop: int
) -> List[Tuple[int, int]]:
    values = []
    position = start
    while position + window <= end:
        numerator = sum(sample * sample for frame in frames[position : position + window] for sample in frame)
        denominator = window * len(frames[position])
        values.append((position, numerator // max(1, denominator)))
        position += hop
    return values


def _choose_boundary(
    frames: Sequence[Tuple[int, ...]], nominal: int, rate: int, profile: Mapping[str, Any]
) -> Tuple[int, str, str, str, int, int]:
    search = _samples(profile["search_window_ms"], rate)
    start = max(0, nominal - search)
    end = nominal
    window = max(1, _samples(profile["analysis_window_ms"], rate))
    hop = max(1, _samples(profile["hop_ms"], rate))
    minimum = _samples(profile["safe_pause_min_ms"], rate)
    energies = _window_energies(frames, start, end, window, hop)
    # The approved dBFS label is human provenance; comparison uses its locked
    # integer mean-square equivalent so platform float math cannot move a cut.
    threshold = int(profile["safe_pause_threshold_mean_square"])
    qualifying = [(position, energy) for position, energy in energies if energy <= threshold]
    runs: List[List[Tuple[int, int]]] = []
    for item in qualifying:
        if not runs or item[0] - runs[-1][-1][0] > hop:
            runs.append([item])
        else:
            runs[-1].append(item)
    candidates = []
    for run in runs:
        run_start = run[0][0]
        run_end = run[-1][0] + window
        if run_end - run_start >= minimum:
            boundary = (run_start + run_end) // 2
            peak = max(value for _, value in run)
            candidates.append((abs(nominal - boundary), peak, boundary))
    if candidates:
        distance, peak, boundary = min(candidates)
        score = f"distance={distance};peak_energy={peak}"
        return boundary, "safe_pause", "none", "", start, end

    interval = _samples(profile["fallback_interval_ms"], rate)
    fallback = []
    for interval_start in range(start, max(start, end - interval) + 1, hop):
        interval_end = interval_start + interval
        values = [energy for position, energy in energies if interval_start <= position < interval_end]
        if not values:
            continue
        ordered = sorted(values)
        rank = max(1, math.ceil(0.95 * len(ordered)))
        p95 = ordered[rank - 1]
        boundary = interval_start + interval // 2
        fallback.append((p95, abs(nominal - boundary), boundary))
    if not fallback:
        boundary = nominal
        p95 = 32767 * 32767
    else:
        p95, _, boundary = min(fallback)
    score = f"p95_energy={p95};distance={abs(nominal-boundary)}"
    return boundary, "low_energy_fallback", "high", "no_safe_pause_fallback", start, end


def _write_chunk(
    source_frames: Sequence[Tuple[int, ...]],
    path: Path,
    start: int,
    end: int,
    rate: int,
    channels: int,
    width: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing_rate, existing_channels, existing_width, existing_frames = _read_pcm(path)
        expected_frames = list(source_frames[start:end])
        if (
            existing_rate == rate
            and existing_channels == channels
            and existing_width == width
            and existing_frames == expected_frames
        ):
            return
        raise TranscriptionChunkingError(f"不会覆盖内容不同的 chunk：{path.name}")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        flat = [sample for frame in source_frames[start:end] for sample in frame]
        handle.writeframes(struct.pack("<" + "h" * len(flat), *flat))


def _serializable_plan(plan: TranscriptionChunkPlan, include_digest=False) -> Dict[str, Any]:
    result = {
        "profile_version": plan.profile_version,
        "profile_digest": plan.profile_digest,
        "extracted_audio_digest": plan.extracted_audio_digest,
        "mapping_digest": plan.mapping_digest,
        "chunks": [
            {
                **{key: str(value) if isinstance(value, Decimal) else value for key, value in asdict(chunk).items() if key != "path"},
                "path": str(chunk.path),
            }
            for chunk in plan.chunks
        ],
        "boundaries": [
            {key: str(value) if isinstance(value, Decimal) else value for key, value in asdict(boundary).items()}
            for boundary in plan.boundaries
        ],
    }
    if include_digest:
        result["digest"] = plan.digest
    return result


def plan_transcription_chunks(
    extracted_audio: Mapping[str, Any],
    mapping: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> TranscriptionChunkPlan:
    _validate_profile(profile)
    profile_digest = str(profile.get("profile_digest") or _profile_digest(profile))
    source = Path(str(extracted_audio["immutable_local_path"]))
    rate, channels, width, frames = _read_pcm(source)
    if rate != int(extracted_audio["sample_rate"]) or channels != int(extracted_audio["channels"]):
        raise TranscriptionChunkingError("PCM metadata 与 Extracted Audio Artifact 不一致")
    if len(frames) != int(extracted_audio["sample_count"]):
        raise TranscriptionChunkingError("PCM sample count 与 Artifact 不一致")
    bytes_per_frame = channels * width
    nominal_capacity = (int(profile["request_cap_bytes"]) - int(profile["wav_header_bytes"])) // bytes_per_frame
    if nominal_capacity <= 0:
        raise TranscriptionChunkingError("request cap 无法容纳 PCM")
    chunk_root = source.parent / f"chunks-{profile_digest[:12]}"
    chunks: List[TranscriptionChunk] = []
    boundaries: List[TranscriptionBoundary] = []
    start_sample = 0
    index = 0
    while start_sample < len(frames):
        nominal = min(len(frames), start_sample + nominal_capacity)
        if nominal == len(frames):
            end_sample = nominal
            mode, risk, reason = "final", "none", ""
            search_start = search_end = nominal
            score = "final"
        else:
            end_sample, mode, risk, reason, search_start, search_end = _choose_boundary(
                frames, nominal, rate, profile
            )
            if end_sample <= start_sample:
                end_sample = nominal
                mode, risk, reason = "low_energy_fallback", "high", "no_safe_pause_fallback"
            score = f"nominal={nominal};chosen={end_sample};mode={mode}"
        path = chunk_root / f"chunk-{index:04d}.wav"
        _write_chunk(frames, path, start_sample, end_sample, rate, channels, width)
        if path.stat().st_size > int(profile["request_cap_bytes"]):
            raise TranscriptionChunkingError("request chunk 超过 24 MiB cap")
        extracted_start = Decimal(start_sample) / Decimal(rate)
        extracted_end = Decimal(end_sample) / Decimal(rate)
        evidence = {
            "nominal": nominal,
            "chosen": end_sample,
            "mode": mode,
            "risk": risk,
            "reason": reason,
            "search_start": search_start,
            "search_end": search_end,
            "profile_digest": profile_digest,
        }
        evidence_digest = canonical_digest(evidence)
        chunk = TranscriptionChunk(
            chunk_index=index,
            start_sample=start_sample,
            end_sample=end_sample,
            sample_rate=rate,
            extracted_start_seconds=extracted_start,
            extracted_end_seconds=extracted_end,
            media_start_seconds=map_extracted_seconds(mapping, extracted_start),
            media_end_seconds=map_extracted_seconds(mapping, extracted_end),
            selection_mode=mode,
            search_start_sample=search_start,
            search_end_sample=search_end,
            boundary_score=score,
            boundary_evidence_digest=evidence_digest,
            chunk_digest=sha256_file(path),
            profile_digest=profile_digest,
            path=path,
        )
        chunks.append(chunk)
        if end_sample < len(frames):
            guard = _samples(profile["risk_guard_ms"], rate)
            guard_start = Decimal(max(0, end_sample - guard)) / Decimal(rate) if risk == "high" else None
            guard_end = Decimal(min(len(frames), end_sample + guard)) / Decimal(rate) if risk == "high" else None
            boundaries.append(
                TranscriptionBoundary(
                    boundary_index=index,
                    boundary_sample=end_sample,
                    selection_mode=mode,
                    boundary_risk=risk,
                    reason=reason,
                    guard_start_seconds=guard_start,
                    guard_end_seconds=guard_end,
                    evidence_digest=evidence_digest,
                )
            )
        start_sample = end_sample
        index += 1
    draft = TranscriptionChunkPlan(
        profile_version=str(profile["profile_version"]),
        profile_digest=profile_digest,
        extracted_audio_digest=str(extracted_audio["artifact_digest"]),
        mapping_digest=str(mapping["mapping_digest"]),
        chunks=tuple(chunks),
        boundaries=tuple(boundaries),
        digest="",
    )
    plan = replace(draft, digest=canonical_digest(_serializable_plan(draft)))
    return plan


def validate_transcription_chunk_plan(
    plan: TranscriptionChunkPlan,
    extracted_audio: Mapping[str, Any],
    mapping: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> None:
    if plan.profile_digest != str(profile.get("profile_digest") or _profile_digest(profile)):
        raise TranscriptionChunkingError("Chunk Plan Profile digest 不一致")
    regenerated = plan_transcription_chunks(extracted_audio, mapping, profile)
    if _serializable_plan(plan, include_digest=True) != _serializable_plan(regenerated, include_digest=True):
        raise TranscriptionChunkingError("Chunk Plan 与 PCM/Profile 重推导结果不一致")
