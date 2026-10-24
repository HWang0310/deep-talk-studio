"""Safe per-batch filesystem archives for complete local ASR transcripts."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .acquisition import sanitize_filename
from .settings import WorkbenchSettingsError, validate_existing_directory


class TranscriptArchiveError(ValueError):
    """An archive path or artifact cannot be written without clobbering data."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_label(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\\/:*?\"<>|]+", "_", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._-")
    if not cleaned or cleaned in {".", ".."}:
        raise TranscriptArchiveError("任务名称不能为空或仅包含路径符号")
    return sanitize_filename(cleaned, limit=60)


def create_batch(root: Path, label: str = "") -> Dict[str, str]:
    """Create a unique batch directory and its two owned child folders."""

    try:
        resolved_root = validate_existing_directory(str(root)).resolve(strict=True)
    except WorkbenchSettingsError as exc:
        raise TranscriptArchiveError(str(exc)) from None
    if not os.access(str(resolved_root), os.W_OK | os.X_OK):
        raise TranscriptArchiveError("保存文件夹不可写，请检查目录权限")
    safe_label = _safe_label(label) if label else "口播提取"
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S")
    stem = f"{timestamp}_{safe_label}"
    for suffix in range(1, 10000):
        name = stem if suffix == 1 else f"{stem}-{suffix:02d}"
        batch = resolved_root / name
        try:
            batch.mkdir(mode=0o700, exist_ok=False)
        except FileExistsError:
            continue
        try:
            (batch / "视频").mkdir(mode=0o700)
            (batch / "口播稿").mkdir(mode=0o700)
        except OSError as exc:
            raise TranscriptArchiveError(
                f"无法建立批次目录结构：{exc.strerror or type(exc).__name__}"
            ) from None
        return {"save_root": str(resolved_root), "save_batch_path": str(batch), "save_batch_label": safe_label}
    raise TranscriptArchiveError("无法分配不冲突的任务文件夹，请更换任务名称后重试")


def batch_paths(session: Mapping[str, Any]) -> Optional[Dict[str, Path]]:
    """Resolve a stored batch only when it remains an immediate child of its root."""

    root_text = str(session.get("save_root", "") or "")
    batch_text = str(session.get("save_batch_path", "") or "")
    if not root_text or not batch_text:
        return None
    try:
        root = validate_existing_directory(root_text).resolve(strict=True)
        batch = Path(batch_text).expanduser()
        if not batch.is_absolute() or batch.is_symlink():
            raise TranscriptArchiveError("不允许符号链接或非绝对批次路径")
        resolved_batch = batch.resolve(strict=True)
    except WorkbenchSettingsError as exc:
        raise TranscriptArchiveError(str(exc)) from None
    except (OSError, RuntimeError):
        raise TranscriptArchiveError("保存批次不存在或无法访问，原会话文件仍保留") from None
    if resolved_batch.parent != root or not resolved_batch.is_dir():
        raise TranscriptArchiveError("保存批次路径不在所选保存文件夹内，已停止写入")
    video = resolved_batch / "视频"
    transcripts = resolved_batch / "口播稿"
    for child in (video, transcripts):
        if child.is_symlink() or not child.is_dir() or child.resolve(strict=True).parent != resolved_batch:
            raise TranscriptArchiveError("批次目录结构已改变或包含符号链接，已停止写入")
    return {"root": root, "batch": resolved_batch, "video": video, "transcripts": transcripts}


def item_stem(index: int, title: str, bvid: str) -> str:
    return f"{index:02d}-{sanitize_filename(title or bvid)}-{bvid}"


def _write_exclusive_or_same(path: Path, data: bytes) -> str:
    """Atomically create a file, accepting an identical prior copy only."""

    expected = _digest(data)
    if path.is_symlink():
        raise TranscriptArchiveError(f"目标文件是符号链接，未覆盖：{path.name}")
    if path.exists():
        if path.is_file() and file_digest(path) == expected:
            return expected
        raise TranscriptArchiveError(f"目标文件已存在且内容不同，未覆盖：{path.name}")
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=".deeptalk-export-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_file() and not path.is_symlink() and file_digest(path) == expected:
                return expected
            raise TranscriptArchiveError(f"目标文件已存在且内容不同，未覆盖：{path.name}") from None
        return expected
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_item(
    paths: Mapping[str, Path],
    *,
    index: int,
    bvid: str,
    title: str,
    transcript: Mapping[str, Any],
    text: str,
    media_path: str = "",
    media_sha256: str = "",
) -> Dict[str, Any]:
    """Save one complete text/JSON pair and verify its original media path."""

    stem = item_stem(index, title, bvid)
    txt_path = paths["transcripts"] / f"{stem}.txt"
    json_path = paths["transcripts"] / f"{stem}.json"
    try:
        text_hash = _write_exclusive_or_same(txt_path, text.encode("utf-8"))
        json_bytes = (json.dumps(transcript, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        json_hash = _write_exclusive_or_same(json_path, json_bytes)
    except OSError as exc:
        raise TranscriptArchiveError(f"无法自动保存口播稿：{exc.strerror or type(exc).__name__}") from None

    media = ""
    media_error = ""
    if media_path:
        source = Path(media_path).expanduser()
        try:
            if source.is_symlink() or not source.is_file() or source.resolve(strict=True).parent != paths["video"].resolve(strict=True):
                media_error = "原视频未位于本任务的视频目录；会话中的既有文件仍保留"
            elif media_sha256 and file_digest(source) != media_sha256:
                media_error = "原视频指纹与下载记录不符，未归档"
            else:
                media = str(source)
        except (OSError, RuntimeError):
            media_error = "原视频当前不可用；口播稿仍已保存"
    return {
        "video": media,
        "transcript_txt": str(txt_path),
        "transcript_json": str(json_path),
        "transcript_txt_sha256": text_hash,
        "transcript_json_sha256": json_hash,
        "media_error": media_error,
    }


def write_merge(paths: Mapping[str, Path], text: str, previous_sha256: str = "") -> str:
    """Atomically update only the generated merged file still owned by this session."""

    target = paths["batch"] / "合并参考稿.txt"
    data = text.encode("utf-8")
    new_hash = _digest(data)
    if target.is_symlink():
        raise TranscriptArchiveError("合并参考稿路径是符号链接，未覆盖")
    if target.exists():
        if not target.is_file():
            raise TranscriptArchiveError("合并参考稿路径不是普通文件，未覆盖")
        existing_hash = file_digest(target)
        if existing_hash == new_hash:
            return new_hash
        if not previous_sha256 or existing_hash != previous_sha256:
            raise TranscriptArchiveError("合并参考稿已被外部修改，已保留原文件且未覆盖")
    fd, temporary = tempfile.mkstemp(dir=str(target.parent), prefix=".deeptalk-merge-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            if target.is_symlink() or file_digest(target) != previous_sha256:
                raise TranscriptArchiveError("合并参考稿已发生变化，已保留原文件且未覆盖")
            os.replace(temporary, target)
        else:
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.is_file() and not target.is_symlink() and file_digest(target) == new_hash:
                    return new_hash
                raise TranscriptArchiveError("合并参考稿已存在，未覆盖") from None
        return new_hash
    except OSError as exc:
        raise TranscriptArchiveError(f"无法保存合并参考稿：{exc.strerror or type(exc).__name__}") from None
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def copy_file_exclusive(source: Path, target: Path, expected_sha256: str = "") -> str:
    """Copy an existing regular file via a same-directory temporary, never overwrite."""

    source = Path(source)
    if source.is_symlink() or not source.is_file():
        raise TranscriptArchiveError(f"来源文件不存在或是符号链接：{source.name}")
    source_hash = file_digest(source)
    if expected_sha256 and source_hash != expected_sha256:
        raise TranscriptArchiveError(f"来源文件指纹不匹配，未复制：{source.name}")
    if target.is_symlink():
        raise TranscriptArchiveError(f"归档目标是符号链接，未覆盖：{target.name}")
    if target.exists():
        if target.is_file() and file_digest(target) == source_hash:
            return source_hash
        raise TranscriptArchiveError(f"归档目标已存在且内容不同，未覆盖：{target.name}")
    fd, temporary = tempfile.mkstemp(dir=str(target.parent), prefix=".deeptalk-copy-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as inp:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if file_digest(Path(temporary)) != source_hash:
            raise TranscriptArchiveError(f"复制后的指纹不匹配，未归档：{source.name}")
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.is_file() and not target.is_symlink() and file_digest(target) == source_hash:
                return source_hash
            raise TranscriptArchiveError(f"归档目标已存在且内容不同，未覆盖：{target.name}") from None
        return source_hash
    except OSError as exc:
        raise TranscriptArchiveError(f"复制文件失败：{exc.strerror or type(exc).__name__}") from None
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
