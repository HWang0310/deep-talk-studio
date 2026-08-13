"""Safe Clean A-roll import, media probing, and transcription-audio extraction."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import unicodedata
import wave
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from .narration_schema import NARRATION_MEDIA_SCHEMA
from .validation import validate_json_schema


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".flac"}


class NarrationMediaError(ValueError):
    """A user-readable import/probe/extraction error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _decimal_text(value: Any, default: str = "0") -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        number = Decimal(default)
    if not number.is_finite():
        number = Decimal(default)
    return format(number, "f")


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fraction(value: str) -> Decimal:
    try:
        numerator, denominator = value.split("/", 1)
        if Decimal(denominator) == 0:
            return Decimal(0)
        return Decimal(numerator) / Decimal(denominator)
    except (AttributeError, InvalidOperation, ValueError):
        return Decimal(0)


def _ffprobe_json(path: Path, *extra: str) -> Dict[str, Any]:
    command = ["ffprobe", "-v", "error", *extra, "-of", "json", str(path)]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        raw = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise NarrationMediaError("无法读取真人口播媒体") from exc
    if not isinstance(raw, dict):
        raise NarrationMediaError("ffprobe 返回无效媒体证据")
    return raw


def _stream_side_data(stream: Mapping[str, Any]) -> Tuple[int, int, int, int]:
    initial = _int(stream.get("initial_padding"))
    trailing = _int(stream.get("trailing_padding"))
    skip = 0
    discard = 0
    for entry in stream.get("side_data_list", []) or []:
        if not isinstance(entry, Mapping):
            continue
        skip = max(skip, _int(entry.get("skip_samples")))
        discard = max(discard, _int(entry.get("discard_padding")))
    return initial, trailing, skip, discard


def _video_record(stream: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if stream is None:
        return {
            "present": False,
            "stream_index": 0,
            "codec": "",
            "width": 0,
            "height": 0,
            "nominal_fps": "",
            "average_fps": "",
            "is_vfr": False,
            "time_base": "",
            "start_pts": 0,
            "start_time_seconds": "0",
            "duration_ts": 0,
            "duration_seconds": "0",
        }
    nominal = str(stream.get("r_frame_rate") or "0/0")
    average = str(stream.get("avg_frame_rate") or "0/0")
    return {
        "present": True,
        "stream_index": _int(stream.get("index")),
        "codec": str(stream.get("codec_name") or ""),
        "width": _int(stream.get("width")),
        "height": _int(stream.get("height")),
        "nominal_fps": nominal,
        "average_fps": average,
        "is_vfr": _fraction(nominal) != _fraction(average),
        "time_base": str(stream.get("time_base") or ""),
        "start_pts": _int(stream.get("start_pts")),
        "start_time_seconds": _decimal_text(stream.get("start_time")),
        "duration_ts": _int(stream.get("duration_ts")),
        "duration_seconds": _decimal_text(stream.get("duration")),
    }


def _audio_record(stream: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if stream is None:
        return {
            "present": False,
            "stream_index": 0,
            "codec": "",
            "sample_rate": 0,
            "channels": 0,
            "channel_layout": "",
            "time_base": "",
            "start_pts": 0,
            "start_time_seconds": "0",
            "duration_ts": 0,
            "duration_seconds": "0",
            "codec_frame_samples": 0,
            "initial_padding_samples": 0,
            "trailing_padding_samples": 0,
            "skip_samples": 0,
            "discard_padding_samples": 0,
            "side_data_digest": canonical_digest([]),
        }
    initial, trailing, skip, discard = _stream_side_data(stream)
    codec = str(stream.get("codec_name") or "")
    codec_frame_samples = 1024 if codec == "aac" else (_int(stream.get("frame_size")))
    side_data = stream.get("side_data_list", []) or []
    return {
        "present": True,
        "stream_index": _int(stream.get("index")),
        "codec": codec,
        "sample_rate": _int(stream.get("sample_rate")),
        "channels": _int(stream.get("channels")),
        "channel_layout": str(stream.get("channel_layout") or ""),
        "time_base": str(stream.get("time_base") or ""),
        "start_pts": _int(stream.get("start_pts")),
        "start_time_seconds": _decimal_text(stream.get("start_time")),
        "duration_ts": _int(stream.get("duration_ts")),
        "duration_seconds": _decimal_text(stream.get("duration")),
        "codec_frame_samples": codec_frame_samples,
        "initial_padding_samples": initial,
        "trailing_padding_samples": trailing,
        "skip_samples": skip,
        "discard_padding_samples": discard,
        "side_data_digest": canonical_digest(side_data),
    }


def _packet_gap_evidence(packets: Sequence[Mapping[str, Any]]) -> Sequence[Dict[str, str]]:
    gaps = []
    previous_end: Optional[Decimal] = None
    for packet in packets:
        try:
            start = Decimal(str(packet["pts_time"]))
            duration = Decimal(str(packet.get("duration_time", "0")))
        except (KeyError, InvalidOperation):
            continue
        if previous_end is not None and start - previous_end > Decimal("0.05"):
            gaps.append(
                {"start_seconds": format(previous_end, "f"), "end_seconds": format(start, "f")}
            )
        previous_end = max(previous_end or start + duration, start + duration)
    return gaps


@dataclass(frozen=True)
class MediaProbeEvidence:
    container: str
    format_duration_seconds: Decimal
    format_start_time_seconds: Decimal
    presentation_origin_seconds: float
    presentation_end_seconds: float
    presentation_duration_seconds: Decimal
    audio_presentation_start_seconds: float
    audio_presentation_end_seconds: float
    video_stream: Dict[str, Any]
    audio_stream: Dict[str, Any]
    internal_audio_gaps: Sequence[Dict[str, str]]
    packet_probe_digest: str
    frame_probe_digest: str
    probe_tool: str
    probe_version: str
    probe_digest: str


@dataclass(frozen=True)
class NarrationMediaResult:
    artifact: Dict[str, Any]
    immutable_path: Path
    probe: MediaProbeEvidence


@dataclass(frozen=True)
class ExtractedAudioResult:
    artifact: Dict[str, Any]
    immutable_path: Path
    command_arguments: Tuple[str, ...]


def probe_narration_media(path: Path) -> MediaProbeEvidence:
    path = Path(path)
    streams_raw = _ffprobe_json(path, "-show_format", "-show_streams")
    packet_raw = _ffprobe_json(
        path,
        "-show_packets",
        "-show_entries",
        "packet=stream_index,codec_type,pts,dts,pts_time,dts_time,duration,duration_time,flags,side_data_list",
    )
    frame_raw = _ffprobe_json(
        path,
        "-show_frames",
        "-show_entries",
        "frame=stream_index,media_type,pts,best_effort_timestamp,pkt_duration,side_data_list",
    )
    streams = streams_raw.get("streams", [])
    video_raw = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio_raw = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video_raw is None and audio_raw is None:
        raise NarrationMediaError("媒体没有可识别的音频或视频流")
    video = _video_record(video_raw)
    audio = _audio_record(audio_raw)
    format_info = streams_raw.get("format", {})
    format_duration = Decimal(_decimal_text(format_info.get("duration")))
    format_start = Decimal(_decimal_text(format_info.get("start_time")))
    present_starts = [
        Decimal(record["start_time_seconds"])
        for record in (video, audio)
        if record["present"]
    ]
    origin = min(present_starts) if present_starts else Decimal(0)
    present_ends = [
        Decimal(record["start_time_seconds"]) + Decimal(record["duration_seconds"])
        for record in (video, audio)
        if record["present"]
    ]
    end = max(present_ends) if present_ends else format_duration
    if format_duration > 0:
        end = max(end, origin + format_duration)
    audio_start = Decimal(audio["start_time_seconds"]) - origin if audio["present"] else Decimal(0)
    audio_end = audio_start + Decimal(audio["duration_seconds"]) if audio["present"] else Decimal(0)
    audio_packets = [
        item
        for item in packet_raw.get("packets", [])
        if audio_raw is not None and _int(item.get("stream_index"), -1) == _int(audio_raw.get("index"))
    ]
    try:
        version = subprocess.run(
            ["ffprobe", "-version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0]
    except (OSError, subprocess.CalledProcessError, IndexError) as exc:
        raise NarrationMediaError("无法读取 ffprobe 版本") from exc
    packet_digest = canonical_digest(packet_raw)
    frame_digest = canonical_digest(frame_raw)
    digest_payload = {
        "streams": streams_raw,
        "packet_probe_digest": packet_digest,
        "frame_probe_digest": frame_digest,
        "presentation_origin": format(origin, "f"),
        "presentation_end": format(end - origin, "f"),
    }
    return MediaProbeEvidence(
        container=str(format_info.get("format_name") or path.suffix.lstrip(".")),
        format_duration_seconds=format_duration,
        format_start_time_seconds=format_start,
        presentation_origin_seconds=float(origin),
        presentation_end_seconds=float(end - origin),
        presentation_duration_seconds=end - origin,
        audio_presentation_start_seconds=float(audio_start),
        audio_presentation_end_seconds=float(audio_end),
        video_stream=video,
        audio_stream=audio,
        internal_audio_gaps=_packet_gap_evidence(audio_packets),
        packet_probe_digest=packet_digest,
        frame_probe_digest=frame_digest,
        probe_tool="ffprobe",
        probe_version=version,
        probe_digest=canonical_digest(digest_payload),
    )


def _safe_filename(path: Path) -> str:
    name = unicodedata.normalize("NFKC", path.name)
    name = re.sub(r"[\x00-\x1f\x7f]", "_", name)
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r"\s+", " ", name).strip().lstrip(".")
    return name or f"clean-aroll{path.suffix.lower()}"


def _exclusive_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise NarrationMediaError(f"不会覆盖已有媒体：{target.name}") from exc
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_handle:
            shutil.copyfileobj(input_handle, output)
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        raise


def import_narration_media(
    source: Path,
    media_root: Path,
    *,
    imported_at: str,
    id_factory: Callable[[str], str],
) -> NarrationMediaResult:
    source = Path(source)
    if source.is_symlink() or not source.is_file():
        raise NarrationMediaError("真人口播文件必须是普通文件，不能使用链接")
    suffix = source.suffix.lower()
    if suffix not in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS:
        raise NarrationMediaError("只接受 mp4、mov、m4v、m4a、mp3、wav、aac 或 flac")
    if source.stat().st_size <= 0:
        raise NarrationMediaError("真人口播文件为空")
    probe = probe_narration_media(source)
    media_id = str(id_factory("MEDIA"))
    if not media_id or not re.fullmatch(r"[A-Za-z0-9._-]+", media_id):
        raise NarrationMediaError("media_id 无效")
    safe_name = _safe_filename(source)
    target = Path(media_root) / media_id / "original" / safe_name
    _exclusive_copy(source, target)
    digest = sha256_file(target)
    if digest != sha256_file(source):
        raise NarrationMediaError("媒体复制后 SHA 不一致")
    evidence = {
        "presentation_origin_seconds": _decimal_text(probe.presentation_origin_seconds),
        "presentation_end_seconds": _decimal_text(probe.presentation_end_seconds),
        "audio_presentation_start_seconds": (
            _decimal_text(probe.audio_presentation_start_seconds)
            if probe.audio_stream["present"]
            else ""
        ),
        "audio_presentation_end_seconds": (
            _decimal_text(probe.audio_presentation_end_seconds)
            if probe.audio_stream["present"]
            else ""
        ),
        "edit_list_applied": probe.format_start_time_seconds != Decimal(0),
        "packet_probe_digest": probe.packet_probe_digest,
        "frame_probe_digest": probe.frame_probe_digest,
        "internal_audio_gaps": list(probe.internal_audio_gaps),
    }
    evidence["evidence_digest"] = canonical_digest(evidence)
    artifact = {
        "artifact_version": "narration-media/1",
        "media_id": media_id,
        "revision": 1,
        "previous_revision": 0,
        "imported_at": imported_at,
        "media_kind": "video" if probe.video_stream["present"] else "audio",
        "safe_original_filename": safe_name,
        "immutable_local_path": str(target.resolve()),
        "sha256": digest,
        "byte_size": target.stat().st_size,
        "container": probe.container,
        "presentation_duration_seconds": format(probe.presentation_duration_seconds, "f"),
        "format_duration_seconds": format(probe.format_duration_seconds, "f"),
        "format_start_time_seconds": format(probe.format_start_time_seconds, "f"),
        "video_stream": probe.video_stream,
        "audio_stream": probe.audio_stream,
        "presentation_evidence": evidence,
        "probe_tool": probe.probe_tool,
        "probe_version": probe.probe_version,
        "probe_digest": probe.probe_digest,
    }
    artifact["artifact_digest"] = canonical_digest(artifact)
    validate_json_schema(artifact, NARRATION_MEDIA_SCHEMA, "media")
    return NarrationMediaResult(artifact=artifact, immutable_path=target, probe=probe)


def audio_extraction_profile(*, sample_rate: int = 48000, channels: int = 1) -> Dict[str, Any]:
    if sample_rate <= 0 or channels <= 0:
        raise NarrationMediaError("音频提取采样率和声道数必须大于 0")
    profile = {
        "profile_version": "audio-extraction-profile/1",
        "output_codec": "pcm_s16le",
        "sample_rate": sample_rate,
        "channels": channels,
        "preserve_presentation_gaps": True,
        "editorial_filters": [],
    }
    profile["profile_digest"] = canonical_digest(profile)
    return profile


def _wav_metadata(path: Path) -> Tuple[int, int, int, int]:
    try:
        with wave.open(str(path), "rb") as handle:
            return (
                handle.getframerate(),
                handle.getnchannels(),
                handle.getsampwidth(),
                handle.getnframes(),
            )
    except (OSError, wave.Error) as exc:
        raise NarrationMediaError("派生音频不是有效 WAV/PCM") from exc


def _has_internal_silence(path: Path) -> bool:
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "info",
                "-nostdin",
                "-i",
                str(path),
                "-af",
                "silencedetect=noise=-60dB:d=0.05",
                "-f",
                "null",
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise NarrationMediaError("无法验证派生音频静音区") from exc
    starts = [Decimal(value) for value in re.findall(r"silence_start: ([0-9.]+)", result.stderr)]
    ends = [Decimal(value) for value in re.findall(r"silence_end: ([0-9.]+)", result.stderr)]
    duration = Decimal(_decimal_text(_ffprobe_json(path, "-show_entries", "format=duration").get("format", {}).get("duration")))
    return any(start > Decimal("0.02") and end < duration - Decimal("0.02") for start, end in zip(starts, ends))


def extract_transcription_audio(
    media: Mapping[str, Any],
    output_path: Path,
    *,
    profile: Mapping[str, Any],
    created_at: str,
) -> ExtractedAudioResult:
    from .narration_schema import EXTRACTED_AUDIO_SCHEMA

    validate_json_schema(dict(media), NARRATION_MEDIA_SCHEMA, "media")
    if profile.get("profile_version") != "audio-extraction-profile/1":
        raise NarrationMediaError("不支持的音频提取 Profile")
    expected_profile = audio_extraction_profile(
        sample_rate=_int(profile.get("sample_rate")), channels=_int(profile.get("channels"))
    )
    if dict(profile) != expected_profile:
        raise NarrationMediaError("音频提取 Profile 已被修改")
    audio_stream = media["audio_stream"]
    if not audio_stream["present"]:
        raise NarrationMediaError("这个视频没有音轨，无法进行对齐")
    source = Path(str(media["immutable_local_path"]))
    if source.is_symlink() or not source.is_file():
        raise NarrationMediaError("不可读取 immutable Clean A-roll")
    if sha256_file(source) != media["sha256"]:
        raise NarrationMediaError("Clean A-roll SHA 已变化")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise NarrationMediaError(f"不会覆盖已有派生音频：{output_path.name}")
    command = (
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-n",
        "-i",
        str(source),
        "-map",
        f"0:{audio_stream['stream_index']}",
        "-vn",
        "-ac",
        str(profile["channels"]),
        "-ar",
        str(profile["sample_rate"]),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    )
    try:
        subprocess.run(list(command), check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise NarrationMediaError("无法派生 lossless transcription audio") from exc
    sample_rate, channels, sample_width, sample_count = _wav_metadata(output_path)
    operations = ["presentation_decode"]
    if audio_stream["initial_padding_samples"] or audio_stream["skip_samples"]:
        operations.append("aac_priming_excluded")
    if audio_stream["trailing_padding_samples"] or audio_stream["discard_padding_samples"]:
        operations.append("trailing_padding_excluded")
    if _has_internal_silence(output_path):
        operations.append("internal_gap_preserved")
    if sample_rate != audio_stream["sample_rate"]:
        operations.append("deterministic_resample")
    if channels != audio_stream["channels"]:
        operations.append("deterministic_channel_conversion")
    source_start = str(media["presentation_evidence"]["audio_presentation_start_seconds"])
    source_end = str(media["presentation_evidence"]["audio_presentation_end_seconds"])
    first_pts = _int(audio_stream["start_pts"])
    last_pts = first_pts + _int(audio_stream["duration_ts"])
    artifact = {
        "artifact_version": "extracted-audio/1",
        "audio_id": f"AUDIO-{media['media_id']}",
        "revision": 1,
        "created_at": created_at,
        "narration_media_id": media["media_id"],
        "narration_media_sha256": media["sha256"],
        "source_stream_index": audio_stream["stream_index"],
        "immutable_local_path": str(output_path.resolve()),
        "sha256": sha256_file(output_path),
        "byte_size": output_path.stat().st_size,
        "codec": "pcm_s16le",
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_count": sample_count,
        "duration_seconds": format(Decimal(sample_count) / Decimal(sample_rate), "f"),
        "source_time_base": audio_stream["time_base"],
        "first_included_source_pts": first_pts,
        "last_included_source_pts": last_pts,
        "first_extracted_sample_index": 0,
        "last_extracted_sample_index": sample_count,
        "source_audio_presentation_start_seconds": source_start,
        "source_audio_presentation_end_seconds": source_end,
        "resampler_delay_samples": 0,
        "applied_timeline_operations": operations,
        "extraction_profile_version": profile["profile_version"],
        "extraction_profile_digest": profile["profile_digest"],
        "ffmpeg_version": subprocess.run(
            ["ffmpeg", "-version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0],
        "command_arguments_digest": canonical_digest(list(command[1:-1])),
    }
    artifact["artifact_digest"] = canonical_digest(artifact)
    validate_json_schema(artifact, EXTRACTED_AUDIO_SCHEMA, "audio")
    return ExtractedAudioResult(
        artifact=artifact,
        immutable_path=output_path,
        command_arguments=command,
    )
