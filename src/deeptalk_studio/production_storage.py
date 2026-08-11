"""Immutable local storage helpers for Production 0.6 artifacts and outputs."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


class ProductionStorageError(RuntimeError):
    pass


SAFE_ID = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,119}$")


def _safe_id(value: str) -> str:
    if not SAFE_ID.fullmatch(str(value)):
        raise ProductionStorageError("Production 输出 ID 无效，拒绝路径越界")
    return str(value)


def save_production_plan(plan: Mapping[str, Any], output_root: Path) -> Path:
    try:
        created = datetime.fromisoformat(str(plan["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductionStorageError("Production Plan created_at 无效") from exc
    production_id = _safe_id(str(plan["production_id"]))
    revision = int(plan["revision"])
    directory = (
        Path(output_root).resolve() / f"{created.year:04d}" / f"{created.month:02d}"
        / f"{created.day:02d}" / production_id
    )
    path = directory / f"production-plan-r{revision:04d}.json"
    if path.exists():
        raise ProductionStorageError("Production Plan 已存在，拒绝静默覆盖")
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(plan), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def production_output_path(
    output_root: Path, production_id: str, motion_asset_id: str, extension: str
) -> Path:
    root = Path(output_root).resolve()
    production = _safe_id(production_id)
    asset = _safe_id(motion_asset_id)
    ext = str(extension).casefold().lstrip(".")
    if ext not in {"mp4", "webm", "png"}:
        raise ProductionStorageError("Production 输出格式无效")
    path = (root / production / "assets" / f"{asset}.{ext}").resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ProductionStorageError("Production 输出路径越界") from None
    if path.exists():
        raise ProductionStorageError("Production 输出已存在，拒绝覆盖")
    return path
