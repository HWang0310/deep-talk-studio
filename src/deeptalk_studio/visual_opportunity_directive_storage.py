"""Immutable local storage for ``visual-opportunity-directives/1`` artifacts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from .visual_opportunity_directive import VisualOpportunityDirectiveError, normalize_visual_opportunity_directives


class VisualOpportunityDirectiveStorageError(ValueError):
    pass


def save_visual_opportunity_directives(value: Mapping[str, Any], root: Path) -> Path:
    try:
        artifact = normalize_visual_opportunity_directives(value)
    except VisualOpportunityDirectiveError as exc:
        raise VisualOpportunityDirectiveStorageError(str(exc)) from exc
    identity = _safe_id(artifact["directives_id"], "directives_id")
    path = Path(root) / identity / f"visual-opportunity-directives-r{artifact['revision']:04d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise VisualOpportunityDirectiveStorageError(f"不会覆盖已有工件：{path.name}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return path


def load_visual_opportunity_directives(path: Path) -> dict:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise VisualOpportunityDirectiveStorageError("指令工件不存在或不安全")
    try:
        artifact = json.loads(source.read_text(encoding="utf-8"))
        normalized = normalize_visual_opportunity_directives(artifact)
    except (OSError, json.JSONDecodeError, VisualOpportunityDirectiveError) as exc:
        raise VisualOpportunityDirectiveStorageError("指令工件无效") from exc
    expected = Path(_safe_id(normalized["directives_id"], "directives_id")) / f"visual-opportunity-directives-r{normalized['revision']:04d}.json"
    if source.parent.name != expected.parent.name or source.name != expected.name:
        raise VisualOpportunityDirectiveStorageError("指令工件路径与身份不匹配")
    return normalized


def _safe_id(value: Any, label: str) -> str:
    text = str(value)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", text) or text in {".", ".."}:
        raise VisualOpportunityDirectiveStorageError(f"{label} 无效")
    return text
