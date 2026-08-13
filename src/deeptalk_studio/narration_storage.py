"""Immutable, media-rooted narration artifact storage."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


class NarrationStorageError(ValueError):
    """Narration artifacts could not be stored or reloaded safely."""


@dataclass(frozen=True)
class NarrationBundle:
    media: Dict[str, Any]
    extracted_audio: Optional[Dict[str, Any]] = None
    mapping: Optional[Dict[str, Any]] = None
    transcript: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class NarrationPaths:
    media: Path
    extracted_audio: Optional[Path]
    mapping: Optional[Path]
    transcript: Optional[Path]


def _safe_id(value: Any, field: str) -> str:
    text = str(value)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", text) or text in {".", ".."}:
        raise NarrationStorageError(f"{field} 无效")
    return text


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise NarrationStorageError(f"不会覆盖已有工件：{path.name}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _artifact_path(
    base: Path, artifact: Optional[Mapping[str, Any]], key: str, prefix: str
) -> Optional[Path]:
    if artifact is None:
        return None
    identity = _safe_id(artifact.get(key), key)
    return base / f"{prefix}-{identity}.json"


def _validate_root_bindings(bundle: NarrationBundle) -> str:
    media_id = _safe_id(bundle.media.get("media_id"), "media_id")
    if not str(bundle.media.get("sha256", "")):
        raise NarrationStorageError("media.sha256 缺失")
    for label, artifact in (
        ("extracted_audio", bundle.extracted_audio),
        ("mapping", bundle.mapping),
        ("transcript", bundle.transcript),
    ):
        if artifact is not None and artifact.get("narration_media_id") != media_id:
            raise NarrationStorageError(f"{label} 绑定了错误的 media_id")
    return media_id


def save_narration_bundle(bundle: NarrationBundle, root: Path) -> NarrationPaths:
    media_id = _validate_root_bindings(bundle)
    base = Path(root) / media_id / "artifacts"
    paths = NarrationPaths(
        media=base / "narration-media.json",
        extracted_audio=_artifact_path(
            base, bundle.extracted_audio, "audio_id", "extracted-audio"
        ),
        mapping=_artifact_path(base, bundle.mapping, "mapping_id", "timestamp-mapping"),
        transcript=_artifact_path(
            base, bundle.transcript, "transcript_id", "timed-transcript"
        ),
    )
    pending = [
        (paths.media, bundle.media),
        (paths.extracted_audio, bundle.extracted_audio),
        (paths.mapping, bundle.mapping),
        (paths.transcript, bundle.transcript),
    ]
    if any(path is not None and path.exists() for path, value in pending if value is not None):
        raise NarrationStorageError("不会覆盖已有 Narration Bundle")
    for path, value in pending:
        if path is not None and value is not None:
            _write_json_exclusive(path, value)
    return paths


def _load_json(path: Path) -> Dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise NarrationStorageError(f"缺少工件：{path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NarrationStorageError(f"无法读取工件：{path.name}") from exc
    if not isinstance(value, dict) or not value:
        raise NarrationStorageError(f"工件内容无效：{path.name}")
    return value


def _load_optional(base: Path, pattern: str) -> Optional[Dict[str, Any]]:
    paths = list(base.glob(pattern))
    if not paths:
        return None
    if len(paths) != 1:
        raise NarrationStorageError(f"工件数量无效：{pattern}")
    return _load_json(paths[0])


def load_narration_bundle(media_path: Path) -> NarrationBundle:
    media_path = Path(media_path)
    if media_path.name != "narration-media.json":
        raise NarrationStorageError("必须从 narration-media.json 加载")
    base = media_path.parent
    bundle = NarrationBundle(
        media=_load_json(media_path),
        extracted_audio=_load_optional(base, "extracted-audio-*.json"),
        mapping=_load_optional(base, "timestamp-mapping-*.json"),
        transcript=_load_optional(base, "timed-transcript-*.json"),
    )
    media_id = _validate_root_bindings(bundle)
    if base.parent.name != media_id:
        raise NarrationStorageError("Narration Bundle 路径与 media_id 不一致")
    return bundle
