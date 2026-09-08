"""Fail-closed immutable storage for candidate-placement-plan/1 artifacts.

Storage guarantees:
  - **immutable**: ``O_EXCL`` create-only; an existing artifact is never
    overwritten or rewritten.
  - **digest-bound**: every save/load recomputes and verifies
    ``placement_plan_digest``; tampering fails closed.
  - **fail-closed**: unknown fields, malformed windows, out-of-window or
    duration-mismatched ``final_placement``, fabricated ``final_placement`` on
    an ``UNPLACEABLE`` entry, duplicate ``candidate_id`` and path/symlink
    anomalies all raise ``PlacementStorageError``.

Storage validates shape only.  It never plans, ranks, resolves overlap, or
trims anything.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping


class PlacementStorageError(ValueError):
    pass


_ARTIFACT_NAME = "candidate-placement-plan.json"
_PLAN_ID = re.compile(r"CPP-[0-9a-f]{24}")
_BASIS_FIELDS = frozenset({"intrinsic_hint_used", "center_source", "clamped"})
_CENTER_SOURCES = frozenset({"intrinsic_placement_hint", "opportunity_center"})
_UNPLACEABLE_REASONS = frozenset({"CANDIDATE_LONGER_THAN_OPPORTUNITY"})


def save_candidate_placement_plan(value: Mapping[str, Any], root: Path) -> Path:
    """Write a placement plan once.  Never overwrites an existing artifact."""
    _valid(value)
    path = Path(root) / str(value["placement_plan_id"]) / _ARTIFACT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PlacementStorageError("不会覆盖已有工件") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return path


def load_candidate_placement_plan(path: Path) -> dict[str, Any]:
    """Read and re-verify a placement plan.  Any tamper or drift fails closed."""
    source = Path(path)
    try:
        if source.is_symlink() or not source.is_file():
            raise PlacementStorageError("placement plan 路径不安全")
        value = json.loads(source.read_text(encoding="utf-8"))
        _valid(value)
    except (OSError, json.JSONDecodeError, PlacementStorageError) as exc:
        raise PlacementStorageError("placement plan 工件无效") from exc
    if source.parent.name != value["placement_plan_id"] or source.name != _ARTIFACT_NAME:
        raise PlacementStorageError("placement plan 路径无效")
    return value


def _valid(value: Any) -> None:
    allowed = {
        "artifact_version", "placement_plan_id", "opportunity_id", "a_roll_window",
        "placements", "placement_plan_digest",
    }
    if not isinstance(value, Mapping):
        raise PlacementStorageError("placement plan 必须是 JSON 对象")
    if set(value) != allowed or value.get("artifact_version") != "candidate-placement-plan/1":
        raise PlacementStorageError("placement plan schema 无效")
    if not _PLAN_ID.fullmatch(str(value.get("placement_plan_id", ""))):
        raise PlacementStorageError("placement_plan_id 无效")
    if not _identifier(value.get("opportunity_id")):
        raise PlacementStorageError("opportunity_id 无效")
    window = _window(value.get("a_roll_window"), "a_roll_window")
    placements = value.get("placements")
    if not isinstance(placements, list):
        raise PlacementStorageError("placements 必须是列表")
    seen: set[str] = set()
    for index, raw in enumerate(placements):
        _valid_placement(raw, window, index, seen)
    payload = dict(value)
    digest = payload.pop("placement_plan_digest", None)
    if not _sha256(digest) or digest != _digest(payload):
        raise PlacementStorageError("placement plan digest 无效")


def _valid_placement(raw: Any, window: Mapping[str, int], index: int, seen: set[str]) -> None:
    label = f"placements[{index}]"
    if not isinstance(raw, Mapping):
        raise PlacementStorageError("placement 必须是 JSON 对象")
    candidate_id = raw.get("candidate_id")
    if not _identifier(candidate_id):
        raise PlacementStorageError(f"{label}.candidate_id 无效")
    if candidate_id in seen:
        raise PlacementStorageError(f"{label}.candidate_id 重复")
    seen.add(candidate_id)
    duration = raw.get("duration_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise PlacementStorageError(f"{label}.duration_ms 必须是正整数")
    status = raw.get("status")
    if status == "PLACED":
        if set(raw) != {"candidate_id", "status", "final_placement", "duration_ms", "basis"}:
            raise PlacementStorageError(f"{label} PLACED 字段集无效")
        placement = _window(raw.get("final_placement"), f"{label}.final_placement")
        if placement["start_ms"] < window["start_ms"] or placement["end_ms"] > window["end_ms"]:
            raise PlacementStorageError(f"{label}.final_placement 越出 a_roll_window")
        if placement["end_ms"] - placement["start_ms"] != duration:
            raise PlacementStorageError(f"{label}.final_placement 必须精确保留 duration_ms")
        basis = raw.get("basis")
        if not isinstance(basis, Mapping) or set(basis) != _BASIS_FIELDS:
            raise PlacementStorageError(f"{label}.basis 字段集无效")
        if not isinstance(basis.get("intrinsic_hint_used"), bool):
            raise PlacementStorageError(f"{label}.basis.intrinsic_hint_used 必须是布尔值")
        if basis.get("center_source") not in _CENTER_SOURCES:
            raise PlacementStorageError(f"{label}.basis.center_source 无效")
        if not isinstance(basis.get("clamped"), bool):
            raise PlacementStorageError(f"{label}.basis.clamped 必须是布尔值")
    elif status == "UNPLACEABLE":
        # An unplaceable candidate must never carry a fabricated placement.
        if set(raw) != {"candidate_id", "status", "reason", "duration_ms"}:
            raise PlacementStorageError(f"{label} UNPLACEABLE 字段集无效")
        if raw.get("reason") not in _UNPLACEABLE_REASONS:
            raise PlacementStorageError(f"{label}.reason 无效")
    else:
        raise PlacementStorageError(f"{label}.status 无效")


def _window(value: Any, field: str) -> Mapping[str, int]:
    if not isinstance(value, Mapping) or set(value) != {"start_ms", "end_ms"}:
        raise PlacementStorageError(f"{field} 字段集无效")
    start, end = value["start_ms"], value["end_ms"]
    for name, item in (("start_ms", start), ("end_ms", end)):
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise PlacementStorageError(f"{field}.{name} 必须是非负整数")
    if start >= end:
        raise PlacementStorageError(f"{field} 必须满足 start_ms < end_ms")
    return value


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
