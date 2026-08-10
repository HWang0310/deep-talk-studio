"""Immutable local storage for Script Draft and Script Review artifacts."""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping

from .models import ResearchReport, ScriptDraft
from .script_renderer import render_editor_markdown, render_teleprompter_markdown
from .script_validation import validate_script_draft


class ScriptStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScriptPaths:
    json: Path
    editor: Path
    teleprompter: Path


@dataclass(frozen=True)
class ScriptReviewPaths:
    json: Path


def _safe_identifier(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    safe = re.sub(r"[^0-9A-Za-z._-]+", "-", normalized).strip("-.")
    return safe[:120] or "artifact"


def _created_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ScriptStorageError("created_at 必须是 ISO 8601 日期时间") from exc


def _script_directory(script: ScriptDraft, output_root: Path) -> Path:
    created = _created_date(script.created_at)
    return (
        Path(output_root)
        / f"{created.year:04d}"
        / f"{created.month:02d}"
        / f"{created.day:02d}"
        / _safe_identifier(script.report_id)
        / _safe_identifier(script.script_id)
    )


def save_script(
    script: ScriptDraft,
    report: ResearchReport,
    profile: Mapping[str, object],
    output_root: Path,
) -> ScriptPaths:
    validate_script_draft(script, report, profile)
    directory = _script_directory(script, output_root)
    stem = directory / f"script-draft-r{script.revision:04d}"
    paths = ScriptPaths(
        json=stem.with_suffix(".json"),
        editor=stem.with_name(stem.name + ".editor.md"),
        teleprompter=stem.with_name(stem.name + ".teleprompter.md"),
    )
    if any(path.exists() for path in (paths.json, paths.editor, paths.teleprompter)):
        raise ScriptStorageError(
            f"稿件 {script.script_id} 修订版 {script.revision} 已存在，不能静默覆盖"
        )
    directory.mkdir(parents=True, exist_ok=True)
    paths.json.write_text(
        json.dumps(script.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    paths.editor.write_text(
        render_editor_markdown(script, report, profile), encoding="utf-8"
    )
    paths.teleprompter.write_text(
        render_teleprompter_markdown(script), encoding="utf-8"
    )
    latest = {
        "script_id": script.script_id,
        "revision": script.revision,
        "report_id": script.report_id,
        "report_revision": script.report_revision,
        "json": str(paths.json.resolve()),
        "editor": str(paths.editor.resolve()),
        "teleprompter": str(paths.teleprompter.resolve()),
    }
    (Path(output_root) / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return paths


def load_script(
    path: Path, report: ResearchReport, profile: Mapping[str, object]
) -> ScriptDraft:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScriptStorageError(f"无法读取 Script Draft：{path}") from exc
    return ScriptDraft.from_dict(data, report, dict(profile))


def save_script_review_artifact(
    artifact: dict, script: ScriptDraft, output_root: Path
) -> ScriptReviewPaths:
    directory = _script_directory(script, output_root)
    path = directory / (
        f"script-review-for-r{script.revision:04d}-"
        f"{_safe_identifier(artifact['review_id'])}.json"
    )
    if path.exists():
        raise ScriptStorageError(f"Script Review Artifact 已经存在：{path}")
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ScriptReviewPaths(json=path)
