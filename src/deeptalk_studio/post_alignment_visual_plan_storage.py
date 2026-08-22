"""Immutable storage for a post-alignment visual plan."""

import json
import re
from pathlib import Path
from typing import Mapping

from .post_alignment_visual_plan import validate_post_alignment_visual_plan


class PostAlignmentVisualPlanStorageError(ValueError):
    pass


def _safe_id(value: object) -> str:
    text = str(value)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", text):
        raise PostAlignmentVisualPlanStorageError("Post-Alignment Visual Plan ID 不安全")
    return text


def save_post_alignment_visual_plan(plan: Mapping, root: Path) -> Path:
    directory = Path(root) / _safe_id(plan["plan_id"])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"post-alignment-visual-plan-r{int(plan['revision']):04d}.json"
    if path.exists():
        raise PostAlignmentVisualPlanStorageError("Post-Alignment Visual Plan 已存在，拒绝覆盖")
    path.write_text(json.dumps(dict(plan), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_post_alignment_visual_plan(path: Path, script: Mapping, transcript: Mapping, alignment: Mapping, preference: Mapping) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError
        validate_post_alignment_visual_plan(value, script, transcript, alignment, preference)
        return value
    except Exception as exc:
        raise PostAlignmentVisualPlanStorageError("Post-Alignment Visual Plan 工件无效") from exc
