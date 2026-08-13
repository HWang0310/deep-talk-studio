"""Immutable JSON and SRT storage for Basic Subtitle V1."""
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .subtitle_builder import validate_subtitle_artifact


class SubtitleStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubtitlePaths:
    json: Path
    srt: Path


def _srt_time(value):
    milliseconds = int((Decimal(str(value)) * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    hours, rest = divmod(milliseconds, 3600000); minutes, rest = divmod(rest, 60000); seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def render_srt(artifact):
    blocks = []
    for index, cue in enumerate(artifact["cues"], 1):
        blocks.append(f"{index}\n{_srt_time(cue['in_seconds'])} --> {_srt_time(cue['out_seconds'])}\n{cue['text']}")
    return "\n\n".join(blocks) + "\n"


def save_subtitle_artifact(artifact, output_root):
    root = Path(output_root); stem = root / f"subtitle-r{int(artifact['revision']):04d}"
    paths = SubtitlePaths(stem.with_suffix(".json"), stem.with_suffix(".srt"))
    if paths.json.exists() or paths.srt.exists():
        raise SubtitleStorageError("Subtitle Artifact 已存在，不能覆盖")
    root.mkdir(parents=True, exist_ok=True)
    paths.json.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths.srt.write_text(render_srt(artifact), encoding="utf-8")
    return paths


def load_subtitle_artifact(path, transcript, media, profile):
    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubtitleStorageError("无法读取 Subtitle Artifact") from exc
    validate_subtitle_artifact(artifact, transcript, media, profile)
    return artifact
