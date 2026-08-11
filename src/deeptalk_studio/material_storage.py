"""Immutable local storage for Material Packages, Reviews and reading views."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .material_renderer import render_material_markdown
from .material_review import validate_material_review_artifact
from .material_validation import validate_material_package_integrity
from .models import MaterialPackage


class MaterialStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class MaterialPaths:
    json: Path
    markdown: Path


def _safe(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "-", value).strip("-.")[:120] or "artifact"


def _directory(package: MaterialPackage, root: Path) -> Path:
    try:
        created = datetime.fromisoformat(package.created_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise MaterialStorageError("Material created_at 无效") from exc
    return Path(root) / f"{created.year:04d}" / f"{created.month:02d}" / f"{created.day:02d}" / _safe(package.report_id) / _safe(package.script_id) / _safe(package.package_id)


def save_material_package(package: MaterialPackage, output_root: Path) -> MaterialPaths:
    directory = _directory(package, output_root)
    stem = directory / f"material-package-r{package.revision:04d}"
    paths = MaterialPaths(stem.with_suffix(".json"), stem.with_suffix(".md"))
    if paths.json.exists() or paths.markdown.exists():
        raise MaterialStorageError("Material Package 已存在，拒绝静默覆盖")
    directory.mkdir(parents=True, exist_ok=True)
    paths.json.write_text(json.dumps(package.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths.markdown.write_text(render_material_markdown(package), encoding="utf-8")
    return paths


def save_material_review_artifact(artifact: Mapping[str, Any], package: MaterialPackage, output_root: Path) -> Path:
    directory = _directory(package, output_root)
    path = directory / f"material-review-for-r{package.revision:04d}-{_safe(str(artifact['review_id']))}.json"
    if path.exists():
        raise MaterialStorageError("Material Review Artifact 已存在，拒绝覆盖")
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(artifact), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_material_package(path: Path, script: Any, report: Any, profile: Mapping[str, Any]) -> MaterialPackage:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterialStorageError(f"无法读取 Material Package：{path}") from exc
    package = validate_material_package_integrity(data, script, report, profile)
    if package.status in {"reviewed", "reviewed_with_warnings", "blocked", "research_update_required"} and package.review_state["state"] == "reviewed":
        review_path = Path(path).parent / (
            f"material-review-for-r{package.review_state['reviewed_from_revision']:04d}-"
            f"{_safe(package.review_state['review_id'])}.json"
        )
        try:
            artifact = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MaterialStorageError(f"Material Package 缺少可验证的 Review Artifact：{review_path}") from exc
        validate_material_review_artifact(artifact, package)
    return package

