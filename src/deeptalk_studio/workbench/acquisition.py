"""Reference-video local acquisition, transcription and narrative analysis.

Compliance model (Owner direction 2026-10-21, Issue #23):
- Acquisition happens ONLY behind an explicit per-batch authorization text the
  creator supplies; the attestation is stored verbatim with the artifact.
- Downloads use the machine's ``yt-dlp`` with no cookies, no login and no
  risk-control bypass; a platform denial (HTTP 403/412/429, captcha, login
  wall) fails closed with an honest message.
- Media files go to the user-specified downloads folder.  Transcripts and
  study cards live inside the workbench session (gitignored) and are used for
  narrative analysis only — never as facts, never as production footage.
- Transcription is the pinned local whisper.cpp runtime (large-v3), the same
  bootstrap used by the production ASR chain.
"""

import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence


class WorkbenchAcquisitionError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess]

PLATFORM_BLOCK_MARKERS = (
    "412",
    "403",
    "429",
    "captcha",
    "verify",
    "risk",
    "login",
    "cookie",
    "Precondition Failed",
    "Forbidden",
    "Too Many Requests",
)


def _proxy_refusal_message(stderr: str) -> Optional[str]:
    lowered = str(stderr or "").lower()
    refused = any(token in lowered for token in ("connection refused", "actively refused", "cannot connect to proxy", "failed to connect to proxy"))
    local_proxy = "127.0.0.1" in lowered and re.search(r"(?:port\s*[=:,]?\s*)?7897\b", lowered)
    if not refused or not ("proxy" in lowered or local_proxy):
        return None
    endpoint = "127.0.0.1:7897" if local_proxy else "已配置代理"
    return (
        f"本机代理连接失败：yt-dlp 无法连接到代理服务 {endpoint}（拒绝连接）。"
        "请检查本机代理程序是否正在运行，以及代理类型和端口是否正确。"
        "DeepTalk 不会自动关闭或绕过代理。"
    )

DEFAULT_AUDIO_SAMPLE_RATE = 16000


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_filename(value: str, limit: int = 60) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "_", value).strip(" ._-")
    cleaned = re.sub(r"_+", "_", cleaned)
    # Reserve UTF-8 bytes for BVID, collision suffix and play-count/export markers.
    # A character limit alone lets emoji exceed the filesystem 255-byte limit.
    return (cleaned or "reference")[:limit].encode("utf-8")[:160].decode("utf-8", "ignore")


def authorize(authorization_text: str) -> str:
    cleaned = (authorization_text or "").strip()
    if len(cleaned) < 8 or "授权" not in cleaned:
        raise WorkbenchAcquisitionError(
            "缺少有效授权声明：请确认你拥有这些参考视频的合法使用权限（至少 8 个字且包含「授权」）"
        )
    return cleaned


def acquire_reference(
    reference: Mapping[str, Any],
    downloads_dir: Path,
    authorization_text: str,
    *,
    runner: Runner = subprocess.run,
    timeout_seconds: int = 900,
) -> Dict[str, Any]:
    """Download one authorized reference video to the specified folder."""

    attestation = authorize(authorization_text)
    target_dir = Path(downloads_dir).expanduser()
    if not target_dir.is_dir():
        raise WorkbenchAcquisitionError("下载目录不存在，请先在设置中配置已存在的文件夹")
    bvid = str(reference.get("bvid", "")).strip()
    url = str(reference.get("url", "")).strip()
    if not re.fullmatch(r"BV[A-Za-z0-9]+", bvid) or url != f"https://www.bilibili.com/video/{bvid}":
        raise WorkbenchAcquisitionError("参考条目缺少 BVID 或链接")
    verified = (reference.get("view_count_status") == "verified"
                and reference.get("view_count_source") == "per_video_api"
                and type(reference.get("view_count")) is int
                and reference["view_count"] >= 0)
    marker = f"{reference['view_count']}播放" if verified else "播放量未知"
    title = sanitize_filename(str(reference.get("title") or bvid)).replace("%", "_")
    stem = f"{title}-{bvid}-{marker}"
    # Keep preexisting downloads intact, including interrupted sidecars.
    if any(p.name.startswith(stem + ".") for p in target_dir.iterdir()):
        import uuid
        stem = f"{title}-{uuid.uuid4().hex[:8]}-{bvid}-{marker}"
    out_template = str(target_dir / (stem + ".%(ext)s"))
    command = [
        "yt-dlp",
        "--no-playlist",
        "--no-overwrites",
        "--no-cookies",
        "--no-warnings",
        "-f",
        "bv*[height<=720]+ba/b",
        "--merge-output-format",
        "mp4",
        "--no-simulate",
        "--print-json",
        "-o",
        out_template,
        url,
    ]
    try:
        process = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        raise WorkbenchAcquisitionError("本机未找到 yt-dlp，无法下载") from None
    except subprocess.TimeoutExpired:
        raise WorkbenchAcquisitionError("下载超时，请稍后重试或选择更短的参考视频") from None
    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        proxy_error = _proxy_refusal_message(stderr)
        if proxy_error:
            raise WorkbenchAcquisitionError(proxy_error)
        marker = next((m for m in PLATFORM_BLOCK_MARKERS if m.lower() in stderr.lower()), None)
        if marker:
            raise WorkbenchAcquisitionError(
                "平台拒绝访问（风控/验证/登录墙），已停止，不绕过平台限制"
            )
        raise WorkbenchAcquisitionError(
            "下载失败：" + (stderr[-300:] or f"退出码 {process.returncode}")
        )
    info = _parse_ytdlp_json(process.stdout or "")
    if not info:
        raise WorkbenchAcquisitionError("下载完成但未能取得文件信息")
    media_path = info.get("_filename_downloaded") or info.get("_filename")
    if not media_path:
        raise WorkbenchAcquisitionError("下载完成但未能定位媒体文件")
    path = Path(media_path)
    if not path.is_file():  # merged containers rename the template's extension
        matches = sorted(p for p in target_dir.iterdir() if p.name.startswith(stem + "."))
        matches = [m for m in matches if m.suffix.lower() in {".mp4", ".mkv", ".webm", ".m4a", ".mp3"} and not m.name.endswith(".part")]
        if not matches:
            raise WorkbenchAcquisitionError("下载完成但未找到媒体文件，请检查下载目录")
        path = matches[-1]
    if path.is_symlink() or path.resolve().parent != target_dir.resolve() or path.stem != stem or path.suffix.lower() not in {".mp4", ".mkv", ".webm", ".m4a", ".mp3"}:
        raise WorkbenchAcquisitionError("下载返回了非预期媒体路径，已停止")
    return {
        "view_count": reference.get("view_count") if verified else None,
        "view_count_status": "verified" if verified else "unavailable",
        "view_count_source": "per_video_api" if verified else "none",
        "view_count_fetched_at": reference.get("fetched_at", ""),
        "bvid": bvid,
        "url": url,
        "title": str(reference.get("title", "")),
        "authorization_text": attestation,
        "authorized_at": _now(),
        "media_path": str(path),
        "media_bytes": path.stat().st_size,
        "media_sha256": _sha256_file(path),
        "duration_seconds": info.get("duration"),
        "tool": "yt-dlp",
        "status": "downloaded",
    }


def _parse_ytdlp_json(stdout: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            candidate = json.loads(line)
        except ValueError:
            continue
        if isinstance(candidate, dict):
            data = candidate
            break
    if data:
        requested = data.get("requested_downloads") or []
        if requested:
            filepath = requested[0].get("filepath")
            if filepath:
                data["_filename_downloaded"] = filepath
    return data


def extract_audio(
    media_path: Path,
    *,
    runner: Runner = subprocess.run,
    timeout_seconds: int = 600,
) -> Path:
    """Extract mono 16 kHz WAV for local whisper transcription."""

    if not Path(media_path).is_file():
        raise WorkbenchAcquisitionError("媒体文件不存在，无法提取音轨")
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os_fd = fd
    import os

    os.close(os_fd)
    wav = Path(tmp)
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(DEFAULT_AUDIO_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(wav),
    ]
    try:
        process = runner(command, capture_output=True, text=True, timeout=timeout_seconds)
    except FileNotFoundError:
        wav.unlink(missing_ok=True)
        raise WorkbenchAcquisitionError("本机未找到 ffmpeg，无法提取音轨") from None
    except subprocess.TimeoutExpired:
        wav.unlink(missing_ok=True)
        raise WorkbenchAcquisitionError("音轨提取超时") from None
    if process.returncode != 0 or not wav.is_file() or wav.stat().st_size <= 44:
        wav.unlink(missing_ok=True)
        raise WorkbenchAcquisitionError(
            "音轨提取失败：" + (process.stderr or "").strip()[-200:]
        )
    return wav


def transcribe_audio(
    wav_path: Path,
    *,
    runner: Runner = subprocess.run,
    bootstrap: Optional[Any] = None,
    timeout_seconds: int = 1800,
    language: str = "zh",
) -> Dict[str, Any]:
    """One-shot local whisper.cpp large-v3 transcription (analysis-only)."""

    from ..transcription.local_whisper_cpp import WhisperCppBootstrap, WhisperCppBootstrapError

    try:
        local = bootstrap or WhisperCppBootstrap()
        if bootstrap is None and (not local.runtime_path.is_file() or not local.model_path.is_file()):
            raise WorkbenchAcquisitionError(
                f"本地 Whisper 尚未安装完整运行时/large-v3 模型。需要 {local.runtime_path} 与 {local.model_path}；本次不会自动下载，可继续聊天创作。"
            )
        installation = local.ensure()
    except WhisperCppBootstrapError as exc:
        raise WorkbenchAcquisitionError(f"本地语音识别准备失败：{exc}") from None
    with tempfile.TemporaryDirectory(prefix="workbench-whisper-") as temp:
        output_base = Path(temp) / "reference"
        command = [
            str(installation.runtime_path),
            "--model",
            str(installation.model_path),
            "--file",
            str(wav_path),
            "--language",
            language,
            "--dtw",
            installation.dtw_preset,
            "--output-json-full",
            "--output-file",
            str(output_base),
            "--no-prints",
        ]
        try:
            process = runner(command, capture_output=True, text=True, timeout=timeout_seconds)
        except FileNotFoundError:
            raise WorkbenchAcquisitionError("本地 whisper 运行时不可用") from None
        except subprocess.TimeoutExpired:
            raise WorkbenchAcquisitionError("本地语音识别超时") from None
        json_path = output_base.with_suffix(".json")
        if process.returncode != 0 or not json_path.is_file():
            raise WorkbenchAcquisitionError(
                "本地语音识别失败：" + (process.stderr or "").strip()[-200:]
            )
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
        except ValueError:
            raise WorkbenchAcquisitionError("本地语音识别输出无法解析") from None
    segments_raw = raw.get("transcription") or []
    segments = []
    for item in segments_raw:
        offsets = item.get("offsets") or {}
        offset = float(offsets.get("from", item.get("offset", 0)) or 0) / 1000.0
        end = float(offsets.get("to", 0) or 0) / 1000.0
        duration = end - offset if offsets else float(item.get("duration", 0) or 0) / 1000.0
        text = str(item.get("text", "")).strip()
        if text:
            segments.append(
                {
                    "start_seconds": round(offset, 3),
                    "end_seconds": round(offset + duration, 3),
                    "text": text,
                }
            )
    if not segments:
        raise WorkbenchAcquisitionError("本地语音识别没有识别出有效语音")
    return {
        "text": "\n".join(seg["text"] for seg in segments),
        "segments": segments,
        "language": str((raw.get("result") or {}).get("language", language)),
        "model": installation.model_name,
        "runtime_version": installation.runtime_version,
        "audio_sha256": _sha256_file(wav_path),
        "transcribed_at": _now(),
    }


# --- deterministic narrative metrics ----------------------------------------

_STOP_WORDS = {
    "我们", "你们", "他们", "大家", "这个", "那个", "这样", "那样", "然后",
    "但是", "所以", "因为", "如果", "就是", "还是", "可以", "什么", "一个",
    "没有", "自己", "现在", "这里", "那里", "时候", "东西", "问题", "知道",
    "觉得", "其实", "可能", "非常", "特别", "真的", "很多", "所有", "以及",
}


def _ngrams(text: str, size: int, top: int) -> List[str]:
    counts: Dict[str, int] = {}
    for index in range(len(text) - size + 1):
        gram = text[index : index + size]
        if any(ch in "，。！？；：、,.!? \n" for ch in gram):
            continue
        if gram in _STOP_WORDS:
            continue
        counts[gram] = counts.get(gram, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [gram for gram, _ in ranked[:top]]


def analyze_transcript(
    transcript: Mapping[str, Any], metadata: Mapping[str, Any]
) -> Dict[str, Any]:
    segments = list(transcript.get("segments") or [])
    text = str(transcript.get("text", "")).replace("\n", "")
    total = 0.0
    boundaries: List[float] = []
    previous_end: Optional[float] = None
    for segment in segments:
        start = float(segment.get("start_seconds", 0))
        end = float(segment.get("end_seconds", max(start, start)))
        total = max(total, end)
        if previous_end is not None and start - previous_end > 2.5:
            boundaries.append(round(previous_end, 2))
        previous_end = end
    duration = total or float(metadata.get("duration_sec") or 0)
    question_count = text.count("？") + text.count("?")
    number_token_count = len(re.findall(r"\d+(?:\.\d+)?", text))
    return {
        "title": str(metadata.get("title", "")),
        "bvid": str(metadata.get("bvid", "")),
        "view_count": metadata.get("view_count"),
        "view_count_status": metadata.get("view_count_status", ""),
        "url": str(metadata.get("url", "")),
        "duration_seconds": round(duration, 1),
        "segment_count": len(segments),
        "avg_segment_seconds": round(total / len(segments), 2) if segments else 0.0,
        "char_count": len(text),
        "cps": round(len(text) / duration, 2) if duration else 0.0,
        "chapter_pause_count": len(boundaries),
        "question_count": question_count,
        "number_token_count": number_token_count,
        "top_terms": _ngrams(text, 2, 10),
        "top_phrases": _ngrams(text, 4, 6),
        "hook_text": " ".join(seg["text"] for seg in segments[:2]),
        "closing_text": " ".join(seg["text"] for seg in segments[-2:]) if len(segments) > 3 else "",
        "analyzed_at": _now(),
    }
