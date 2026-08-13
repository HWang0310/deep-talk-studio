"""Immutable Script Alignment JSON/Markdown revision storage."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

from .alignment_schema import SCRIPT_ALIGNMENT_SCHEMA
from .validation import ReportValidationError, validate_json_schema


class AlignmentStorageError(ValueError):
    """Alignment storage path/content is unsafe or already exists."""


@dataclass(frozen=True)
class AlignmentPaths:
    json_path: Path
    markdown_path: Path


def _safe(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise AlignmentStorageError("对齐工件 ID 不安全")
    return value


def _markdown(artifact: Mapping[str, Any]) -> str:
    lines = [
        "# Script Alignment", "",
        f"- 对齐状态：{sum(b['alignment_status'] == 'aligned' for b in artifact['beat_timeline'])} 个可直接对齐",
        f"- 需要检查：{sum(b['alignment_status'] != 'aligned' for b in artifact['beat_timeline'])} 个",
        "", "## Beat", "",
    ]
    for beat in artifact["beat_timeline"]:
        lines.append(f"- {beat['beat_id']}：{beat['alignment_status']}（{beat['actual_start_seconds'] or '未定位'}）")
    if artifact["gaps"]:
        lines.extend(["", "## 已保留的差异与边界风险", ""])
        for gap in artifact["gaps"]:
            lines.append(f"- {gap['gap_type']}：{gap['reason_code']}")
    return "\n".join(lines) + "\n"


def save_script_alignment(artifact: Mapping[str, Any], root: Path) -> AlignmentPaths:
    try:
        validate_json_schema(dict(artifact), SCRIPT_ALIGNMENT_SCHEMA)
    except (ReportValidationError, RuntimeError) as exc:
        raise AlignmentStorageError(f"Script Alignment 不可保存：{exc}") from exc
    directory = Path(root) / _safe(artifact["script_id"]) / _safe(artifact["narration_media_id"]) / _safe(artifact["alignment_id"])
    directory.mkdir(parents=True, exist_ok=True)
    revision = int(artifact["revision"])
    json_path = directory / f"script-alignment-r{revision:04d}.json"
    markdown_path = directory / f"script-alignment-r{revision:04d}.md"
    if json_path.exists() or markdown_path.exists():
        raise AlignmentStorageError("该 Script Alignment 修订已存在，不能覆盖")
    try:
        with json_path.open("x", encoding="utf-8") as handle:
            json.dump(dict(artifact), handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        with markdown_path.open("x", encoding="utf-8") as handle:
            handle.write(_markdown(artifact))
    except OSError as exc:
        json_path.unlink(missing_ok=True)
        markdown_path.unlink(missing_ok=True)
        raise AlignmentStorageError("无法安全写入 Script Alignment") from exc
    return AlignmentPaths(json_path, markdown_path)


def load_script_alignment(path: Path) -> Dict[str, Any]:
    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
        validate_json_schema(artifact, SCRIPT_ALIGNMENT_SCHEMA)
    except (OSError, json.JSONDecodeError, ReportValidationError, RuntimeError) as exc:
        raise AlignmentStorageError("Script Alignment 文件无效或已损坏") from exc
    return artifact
