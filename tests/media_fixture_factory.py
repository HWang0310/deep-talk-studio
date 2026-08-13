"""Generate tiny deterministic real-media fixtures without committed binaries."""

import json
import re
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class MediaFixtureSpec:
    name: str
    suffix: str = ".mp4"
    video: bool = True
    audio: bool = True
    duration: str = "2.0"
    audio_offset: str = "0"
    internal_gap: bool = False
    vfr: bool = False
    audio_sample_rate: int = 48000


def _run(command: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def _video_filter(spec: MediaFixtureSpec) -> str:
    if spec.vfr:
        return (
            "testsrc2=size=320x180:rate=30:duration="
            + spec.duration
            + ",select='if(lt(t,1),not(mod(n,2)),1)'"
        )
    return f"testsrc2=size=320x180:rate=30:duration={spec.duration}"


def _audio_filter(spec: MediaFixtureSpec) -> str:
    if spec.internal_gap:
        return (
            f"sine=frequency=1000:sample_rate={spec.audio_sample_rate}:duration={spec.duration},"
            "volume=enable='between(t,0.7,1.1)':volume=0"
        )
    return f"sine=frequency=1000:sample_rate={spec.audio_sample_rate}:duration={spec.duration}"


def build_media_fixture(root: Path, spec: MediaFixtureSpec) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{spec.name}{spec.suffix.lower()}"
    if target.exists():
        raise FileExistsError(str(target))
    if not spec.video and not spec.audio:
        raise ValueError("fixture 至少需要一条音频或视频流")

    command = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    if spec.video:
        command.extend(["-f", "lavfi", "-i", _video_filter(spec)])
    if spec.audio:
        if Decimal(spec.audio_offset) != 0:
            command.extend(["-itsoffset", spec.audio_offset])
        command.extend(["-f", "lavfi", "-i", _audio_filter(spec)])

    video_index = 0 if spec.video else None
    audio_index = 1 if spec.video and spec.audio else (0 if spec.audio else None)
    if video_index is not None:
        command.extend(["-map", f"{video_index}:v:0"])
    if audio_index is not None:
        command.extend(["-map", f"{audio_index}:a:0"])

    suffix = spec.suffix.lower()
    if spec.video:
        command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])
        if spec.vfr:
            command.extend(["-fps_mode", "vfr"])
    if spec.audio:
        if suffix in {".wav"}:
            command.extend(["-c:a", "pcm_s16le"])
        elif suffix == ".flac":
            command.extend(["-c:a", "flac"])
        elif suffix == ".mp3":
            command.extend(["-c:a", "libmp3lame"])
        else:
            command.extend(["-c:a", "aac"])
    if spec.video and spec.audio:
        command.extend(["-shortest"])
    if suffix in {".mp4", ".mov", ".m4v", ".m4a"}:
        command.extend(["-movflags", "+faststart"])
    command.append(str(target))
    _run(command)
    if not target.is_file() or target.stat().st_size <= 0:
        raise RuntimeError("ffmpeg 未生成 fixture")
    return target


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def probe_fixture(path: Path) -> Dict[str, object]:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-show_packets",
            "-of",
            "json",
            str(path),
        ]
    )
    raw = json.loads(result.stdout)
    streams = raw.get("streams", [])
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    packets = [p for p in raw.get("packets", []) if p.get("codec_type") == "audio"]
    gaps = []
    previous_end = None
    for packet in packets:
        start = _float(packet.get("pts_time"))
        end = start + _float(packet.get("duration_time"))
        if previous_end is not None and start - previous_end > 0.05:
            gaps.append([round(previous_end, 6), round(start, 6)])
        previous_end = max(previous_end or end, end)
    if audio_stream is not None:
        silence = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "info",
                "-nostdin",
                "-i",
                str(path),
                "-map",
                "0:a:0",
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
        starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", silence.stderr)]
        ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", silence.stderr)]
        gaps.extend([round(start, 6), round(end, 6)] for start, end in zip(starts, ends))
    _run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-f", "null", "-"])
    return {
        "has_video": any(s.get("codec_type") == "video" for s in streams),
        "has_audio": audio_stream is not None,
        "audio_start_time": _float((audio_stream or {}).get("start_time")),
        "audio_gaps": gaps,
        "decodable": True,
    }
