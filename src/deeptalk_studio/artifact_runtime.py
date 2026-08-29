"""Resolve immutable recorded artifact paths into verified runtime locations.

Historical artifacts keep the absolute path that was true when they were
created.  This module owns the separate, configured observation of where the
same identity exists now.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


CONFIG_VERSION = "artifact-runtime/1"
LOCAL_CONFIG_NAME = "artifact-runtime.local.json"
_CONFIG_FIELDS = frozenset({
    "config_version",
    "canonical_repository_root",
    "trusted_historical_repository_roots",
    "current_production_id",
})
_SAFE_ID = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,119}$")
_MATERIAL_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".svg", ".pdf", ".mp4", ".mov", ".m4v"})
_CAPTURE_SUFFIX_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


class ArtifactRuntimeError(ValueError):
    """A recorded artifact cannot be mapped to current runtime truth safely."""


@dataclass(frozen=True)
class ArtifactRuntimeConfig:
    canonical_repository_root: Path
    trusted_historical_repository_roots: Sequence[Path]
    current_production_id: str = ""

    @property
    def recorded_repository_roots(self) -> tuple[Path, ...]:
        return (self.canonical_repository_root, *self.trusted_historical_repository_roots)


@dataclass(frozen=True)
class RuntimeArtifactObservation:
    lineage: str
    recorded_path: Path
    artifact_relative_path: Path
    resolved_path: Path
    byte_size: int
    sha256: str


def _unsafe_components(value: object) -> bool:
    text = str(value)
    return any(part in {".", ".."} for part in text.split("/"))


def _configured_root(
    value: object, label: str, *, must_exist: bool, resolve_symlinks: bool = True
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactRuntimeError(f"{label} root is missing")
    raw = Path(value)
    if not raw.is_absolute():
        raise ArtifactRuntimeError(f"{label} root must be absolute")
    if _unsafe_components(value):
        raise ArtifactRuntimeError(f"{label} root contains traversal")
    if raw.is_symlink():
        raise ArtifactRuntimeError(f"{label} root cannot be a symlink")
    resolved = raw.resolve(strict=False) if resolve_symlinks else raw.absolute()
    if must_exist and not resolved.is_dir():
        raise ArtifactRuntimeError(f"{label} root does not exist")
    return resolved


def load_artifact_runtime_config(
    canonical_repository_root: Path,
    config_path: Optional[Path] = None,
) -> ArtifactRuntimeConfig:
    """Load strict machine-local configuration for one explicit repository root."""

    expected_root = _configured_root(
        str(Path(canonical_repository_root).absolute()), "canonical repository", must_exist=True
    )
    selected_path = Path(config_path) if config_path is not None else expected_root / "config" / LOCAL_CONFIG_NAME
    if not selected_path.exists():
        return ArtifactRuntimeConfig(expected_root, (), "")
    if selected_path.is_symlink() or not selected_path.is_file():
        raise ArtifactRuntimeError("artifact runtime config must be a regular file")
    try:
        value = json.loads(selected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactRuntimeError("artifact runtime config is unreadable") from exc
    if not isinstance(value, Mapping) or set(value) != _CONFIG_FIELDS:
        raise ArtifactRuntimeError("artifact runtime config fields are invalid")
    if value.get("config_version") != CONFIG_VERSION:
        raise ArtifactRuntimeError("artifact runtime config version is invalid")
    configured_canonical = _configured_root(
        value.get("canonical_repository_root"), "configured canonical repository", must_exist=True
    )
    if configured_canonical != expected_root:
        raise ArtifactRuntimeError("configured canonical root does not match caller root")
    historical_values = value.get("trusted_historical_repository_roots")
    if not isinstance(historical_values, list):
        raise ArtifactRuntimeError("trusted historical roots must be a list")
    historical = tuple(
        _configured_root(
            item, "trusted historical repository", must_exist=False,
            resolve_symlinks=False,
        )
        for item in historical_values
    )
    if len(set(historical)) != len(historical) or configured_canonical in historical:
        raise ArtifactRuntimeError("artifact runtime roots must be distinct")
    current = value.get("current_production_id")
    if not isinstance(current, str) or (current and not _SAFE_ID.fullmatch(current)):
        raise ArtifactRuntimeError("current production id is invalid")
    return ArtifactRuntimeConfig(configured_canonical, historical, current)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_under(path: Path, roots: Sequence[Path]) -> Optional[Path]:
    for root in roots:
        try:
            return path.relative_to(root)
        except ValueError:
            continue
    return None


def _reject_symlink_components(root: Path, relative: Path) -> None:
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ArtifactRuntimeError("runtime artifact path contains a symlink")


class RuntimeArtifactResolver:
    """Fail-closed resolver for controlled Core artifact lineages."""

    def __init__(self, config: ArtifactRuntimeConfig):
        self.config = config

    def resolve_artifact(
        self,
        recorded_path: object,
        artifact_relative_path: object,
        byte_size: object,
        sha256: object,
        *,
        lineage: str,
    ) -> RuntimeArtifactObservation:
        raw_recorded = str(recorded_path)
        recorded = Path(raw_recorded)
        if not recorded.is_absolute():
            raise ArtifactRuntimeError("recorded artifact path must be absolute")
        if _unsafe_components(raw_recorded):
            raise ArtifactRuntimeError("recorded artifact path contains traversal")
        relative = Path(artifact_relative_path)
        if relative.is_absolute():
            raise ArtifactRuntimeError("artifact relative identity cannot be absolute")
        if not relative.parts or _unsafe_components(artifact_relative_path):
            raise ArtifactRuntimeError("artifact relative identity contains traversal")
        recorded_relative = _relative_under(recorded, self.config.recorded_repository_roots)
        if recorded_relative is None:
            raise ArtifactRuntimeError("recorded artifact root is not trusted")
        if recorded_relative != relative:
            raise ArtifactRuntimeError("recorded artifact-relative identity mismatch")
        canonical_root = self.config.canonical_repository_root
        lexical_target = canonical_root.joinpath(*relative.parts)
        _reject_symlink_components(canonical_root, relative)
        try:
            resolved = lexical_target.resolve(strict=True)
        except FileNotFoundError:
            raise ArtifactRuntimeError("resolved runtime artifact is missing") from None
        try:
            resolved.relative_to(canonical_root)
        except ValueError:
            raise ArtifactRuntimeError("resolved runtime artifact escapes canonical root") from None
        if not resolved.is_file():
            raise ArtifactRuntimeError("resolved runtime artifact is not a file")
        try:
            expected_size = int(byte_size)
        except (TypeError, ValueError):
            raise ArtifactRuntimeError("runtime artifact size is invalid") from None
        actual_size = resolved.stat().st_size
        if expected_size <= 0 or actual_size != expected_size:
            raise ArtifactRuntimeError("runtime artifact size mismatch")
        expected_sha = str(sha256)
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise ArtifactRuntimeError("runtime artifact SHA-256 is invalid")
        if _sha256_file(resolved) != expected_sha:
            raise ArtifactRuntimeError("runtime artifact SHA-256 mismatch")
        return RuntimeArtifactObservation(
            str(lineage), recorded, relative, resolved, actual_size, expected_sha
        )

    def resolve_motion_asset(
        self, plan: Mapping[str, Any], asset: Mapping[str, Any]
    ) -> RuntimeArtifactObservation:
        expected = next((
            item for item in plan.get("motion_assets", [])
            if item.get("motion_asset_id") == asset.get("motion_asset_id")
        ), None)
        if not isinstance(expected, Mapping):
            raise ArtifactRuntimeError("Motion artifact identity is not in the Production Plan")
        if (
            expected.get("scene_id") != asset.get("scene_id")
            or expected.get("asset_kind") != asset.get("asset_kind")
        ):
            raise ArtifactRuntimeError("Motion artifact-relative identity mismatch")
        extension = str(expected.get("requested_format", "")).casefold().lstrip(".")
        if not extension or asset.get("format") != extension:
            raise ArtifactRuntimeError("Motion artifact format identity mismatch")
        relative = Path(
            "production_assets", str(plan.get("production_id", "")), "assets",
            f'{asset.get("motion_asset_id", "")}.{extension}',
        )
        return self.resolve_artifact(
            asset.get("output_path", ""), relative,
            asset.get("byte_size"), asset.get("sha256"), lineage="motion_asset",
        )

    def resolve_generated_visual(
        self, package_id: str, visual: Mapping[str, Any]
    ) -> RuntimeArtifactObservation:
        recorded = Path(str(visual.get("local_path", "")))
        suffix = recorded.suffix.casefold()
        visual_id = str(visual.get("visual_id", ""))
        if not _SAFE_ID.fullmatch(str(package_id)) or not _SAFE_ID.fullmatch(visual_id):
            raise ArtifactRuntimeError("Material generated artifact identity is invalid")
        if suffix not in _MATERIAL_SUFFIXES or recorded.stem != visual_id:
            raise ArtifactRuntimeError("Material generated artifact-relative identity mismatch")
        relative = Path("material_assets", package_id, "generated", visual_id + suffix)
        return self.resolve_artifact(
            recorded, relative, visual.get("byte_size"), visual.get("sha256"),
            lineage="material_generated_visual",
        )

    def resolve_material_capture(
        self, package_id: str, record: Mapping[str, Any]
    ) -> RuntimeArtifactObservation:
        material_id = str(record.get("material_id", ""))
        suffix = _CAPTURE_SUFFIX_BY_MIME.get(str(record.get("mime_type", "")))
        recorded = Path(str(record.get("local_path", "")))
        if not _SAFE_ID.fullmatch(str(package_id)) or not _SAFE_ID.fullmatch(material_id):
            raise ArtifactRuntimeError("Material Capture identity is invalid")
        if suffix is None or recorded.suffix.casefold() not in {
            suffix, ".jpeg" if suffix == ".jpg" else suffix
        } or recorded.stem != f"{material_id}-capture":
            raise ArtifactRuntimeError("Material Capture artifact-relative identity mismatch")
        relative = Path(
            "material_assets", package_id, "captures", "registered",
            recorded.name,
        )
        return self.resolve_artifact(
            recorded, relative, record.get("byte_size"), record.get("sha256"),
            lineage="material_capture",
        )

    def resolve_acquired_material(
        self, package_id: str, item: Mapping[str, Any]
    ) -> RuntimeArtifactObservation:
        material_id = str(item.get("material_id", ""))
        recorded = Path(str(item.get("local_path", "")))
        suffix = recorded.suffix.casefold()
        if not _SAFE_ID.fullmatch(str(package_id)) or not _SAFE_ID.fullmatch(material_id):
            raise ArtifactRuntimeError("Material acquired artifact identity is invalid")
        if suffix not in _MATERIAL_SUFFIXES or recorded.stem != material_id:
            raise ArtifactRuntimeError("Material acquired artifact-relative identity mismatch")
        relative = Path("material_assets", package_id, "acquired", material_id + suffix)
        return self.resolve_artifact(
            recorded, relative, item.get("byte_size"), item.get("sha256"),
            lineage="material_acquired",
        )
