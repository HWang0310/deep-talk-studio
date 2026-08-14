"""Immutable, file-bound captures for an already reviewed Material Package.

The reviewed Material Package records research and rights history.  A capture
manifest deliberately lives beside runtime assets instead: it cannot rewrite
that history, but it can prove that a particular inspected page was captured
for a particular reviewed package revision.
"""

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


ARTIFACT_VERSION = "material-capture-manifest/1"
MANIFEST_FILENAME = "material-capture-manifest-r0001.json"
STATIC_MIME_BY_SUFFIX = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
}


class MaterialCaptureManifestError(ValueError):
    """A runtime capture cannot be proven to match reviewed Material history."""


class MaterialCaptureManifestNotFound(FileNotFoundError):
    """No capture projection was recorded for this Material asset root."""


def _data(package: Any) -> Dict[str, Any]:
    raw = package.to_dict() if hasattr(package, "to_dict") else package
    if not isinstance(raw, Mapping):
        raise MaterialCaptureManifestError("Material Package 结构无效")
    return deepcopy(dict(raw))


def _canonical_digest(value: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(value)); payload.pop("manifest_digest", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_iso8601(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MaterialCaptureManifestError(f"{label} 必须是 ISO 8601 日期时间")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MaterialCaptureManifestError(f"{label} 必须是 ISO 8601 日期时间") from exc
    return value


def _file_mime(path: Path) -> str:
    header = path.read_bytes()[:32]
    suffix = path.suffix.casefold()
    if suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if suffix in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if suffix == ".webp" and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    raise MaterialCaptureManifestError("Capture 必须是格式与扩展名一致的静态 PNG、JPEG 或 WebP")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _binding(package: Mapping[str, Any]) -> Dict[str, Any]:
    required = ("package_id", "revision", "package_digest")
    if any(not package.get(key) for key in required):
        raise MaterialCaptureManifestError("Material Package 缺少不可变 revision binding")
    return {
        "package_id": package["package_id"],
        "package_revision": package["revision"],
        "package_digest": package["package_digest"],
    }


def _validate_record(record: Mapping[str, Any], package: Mapping[str, Any], *, asset_root: Optional[Path]) -> Dict[str, Any]:
    materials = {item.get("material_id"): item for item in package.get("materials", [])}
    material_id = record.get("material_id")
    item = materials.get(material_id)
    if not isinstance(item, Mapping) or item.get("provenance_status") != "inspected":
        raise MaterialCaptureManifestError("Capture 必须绑定现有 inspected Material")
    capture = item.get("capture")
    if not isinstance(capture, Mapping):
        raise MaterialCaptureManifestError("Capture 缺少已审核的页面区域 binding")
    source_url = record.get("source_url")
    if source_url not in {item.get("source_url"), item.get("page_url")}:
        raise MaterialCaptureManifestError("Capture source URL 与 reviewed Material 不一致")
    expected = {
        "source_title": item.get("title"),
        "page_number": capture.get("page_number"),
        "capture_region": capture.get("capture_region"),
        "cue_ids": list(item.get("cue_ids", [])),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise MaterialCaptureManifestError(f"Capture {key} 与 reviewed Material binding 不一致")
    _parse_iso8601(record.get("captured_at"), "captured_at")
    raw = record.get("local_path")
    if not isinstance(raw, str) or not raw.strip():
        raise MaterialCaptureManifestError("Capture 缺少本地文件路径")
    path = Path(raw).resolve()
    if asset_root is not None and (not _inside(path, asset_root) or path.is_symlink()):
        raise MaterialCaptureManifestError("Capture 文件必须位于允许的素材目录且不能是符号链接")
    if not path.is_file() or path.stat().st_size <= 0:
        raise MaterialCaptureManifestError("Capture 文件不存在或为空")
    mime = _file_mime(path)
    if record.get("mime_type") != mime or record.get("mime_type") != STATIC_MIME_BY_SUFFIX.get(path.suffix.casefold()):
        raise MaterialCaptureManifestError("Capture MIME 与实际静态文件不一致")
    size = path.stat().st_size
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if record.get("byte_size") != size or record.get("sha256") != digest:
        raise MaterialCaptureManifestError("Capture 文件大小或 SHA-256 与记录不一致")
    return {
        "material_id": material_id, "source_url": source_url,
        "source_title": expected["source_title"], "page_number": expected["page_number"],
        "capture_region": expected["capture_region"], "local_path": str(path),
        "mime_type": mime, "byte_size": size, "sha256": digest,
        "cue_ids": expected["cue_ids"], "captured_at": record["captured_at"],
    }


def build_material_capture_manifest(package: Any, records: Iterable[Mapping[str, Any]], *, created_at: str) -> Dict[str, Any]:
    """Build a versioned capture projection bound to an exact package revision."""

    package_data = _data(package)
    normalized_records = [_validate_record(record, package_data, asset_root=None) for record in records]
    ids = [record["material_id"] for record in normalized_records]
    if not normalized_records or len(ids) != len(set(ids)):
        raise MaterialCaptureManifestError("Capture manifest 必须包含至少一个、且不重复的 Material capture")
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        **_binding(package_data),
        "created_at": _parse_iso8601(created_at, "created_at"),
        "records": normalized_records,
    }
    manifest["manifest_digest"] = _canonical_digest(manifest)
    return manifest


def _manifest_path(asset_root: Path) -> Path:
    return Path(asset_root).resolve() / "captures" / MANIFEST_FILENAME


def save_material_capture_manifest(manifest: Mapping[str, Any], asset_root: Path) -> Path:
    """Persist one immutable manifest; replays validate it again before use."""

    root = Path(asset_root).resolve()
    records = list(manifest.get("records", [])) if isinstance(manifest, Mapping) else []
    if not records:
        raise MaterialCaptureManifestError("Capture manifest 结构无效")
    target = _manifest_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise MaterialCaptureManifestError(f"Capture manifest 已存在，拒绝覆盖：{target}")
    payload = deepcopy(dict(manifest))
    if payload.get("artifact_version") != ARTIFACT_VERSION or payload.get("manifest_digest") != _canonical_digest(payload):
        raise MaterialCaptureManifestError("Capture manifest version 或 digest 无效")
    # Validate files and root containment once at write time, then write canonically.
    # Binding-to-material validation needs the real package and happens in load. Here
    # root/file validation still prevents creating an asset-root escaping manifest.
    for record in records:
        path = Path(str(record.get("local_path", ""))).resolve()
        if not _inside(path, root) or path.is_symlink() or not path.is_file():
            raise MaterialCaptureManifestError("Capture 文件必须位于允许的素材目录")
        _file_mime(path)
    target.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return target


def load_material_capture_manifest(asset_root: Path, package: Any) -> Dict[str, Any]:
    """Replay an immutable capture manifest and fail closed on any change."""

    target = _manifest_path(Path(asset_root))
    if not target.is_file():
        raise MaterialCaptureManifestNotFound(str(target))
    try:
        manifest = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterialCaptureManifestError("Capture manifest 无法读取") from exc
    if not isinstance(manifest, Mapping) or manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise MaterialCaptureManifestError("Capture manifest 版本无效")
    if manifest.get("manifest_digest") != _canonical_digest(manifest):
        raise MaterialCaptureManifestError("Capture manifest digest 无效")
    package_data = _data(package)
    if {key: manifest.get(key) for key in ("package_id", "package_digest")} != {
        key: _binding(package_data)[key] for key in ("package_id", "package_digest")
    } or manifest.get("package_revision") != package_data["revision"]:
        raise MaterialCaptureManifestError("Capture manifest 与 reviewed Material Package revision 不一致")
    _parse_iso8601(manifest.get("created_at"), "created_at")
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        raise MaterialCaptureManifestError("Capture manifest records 无效")
    normalized = [_validate_record(record, package_data, asset_root=Path(asset_root).resolve()) for record in records]
    ids = [record["material_id"] for record in normalized]
    if len(ids) != len(set(ids)):
        raise MaterialCaptureManifestError("Capture manifest 包含重复 Material capture")
    if normalized != records:
        raise MaterialCaptureManifestError("Capture manifest 记录不是规范化的不可变记录")
    return deepcopy(dict(manifest))
