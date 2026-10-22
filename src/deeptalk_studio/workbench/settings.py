"""Creator Workbench Session — settings store (Issue #23 unified flow).

Design rules:
- The file lives at ``config/workbench.local.json`` and is gitignored; no
  secret is ever written to a log or echoed back in full (masked view only).
- Updates are partial: an omitted ``api_key`` keeps the stored key; an empty
  string clears it.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


DEFAULT_SETTINGS: Dict[str, Any] = {
    "settings_version": 1,
    "provider_mode": "responses",  # responses | chat
    "base_url": "https://api.openai.com/v1/responses",
    "chat_base_url": "",  # e.g. https://host/v1  (endpoint = base + /chat/completions)
    "model": "",
    "api_key": "",
    "downloads_dir": "",  # user-specified folder for authorized reference media
    "timeout_seconds": 600,
}

PROVIDER_MODES = {"responses", "chat"}
MIN_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 1800
MAX_API_KEY_CHARS = 4096
MAX_URL_CHARS = 512


class WorkbenchSettingsError(ValueError):
    """Invalid workbench settings payload."""


def settings_path(root: Path) -> Path:
    return Path(root) / "config" / "workbench.local.json"


def load_settings(root: Path) -> Dict[str, Any]:
    path = settings_path(root)
    data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
    if path.is_file():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise WorkbenchSettingsError("工作台设置文件损坏，请重新保存设置")
        if not isinstance(stored, dict):
            raise WorkbenchSettingsError("工作台设置文件损坏，请重新保存设置")
        for key in DEFAULT_SETTINGS:
            if key in stored:
                data[key] = stored[key]
    return data


def _clean_url(value: Any, field: str, *, allow_empty: bool = True) -> str:
    if allow_empty and (value is None or value == ""):
        return ""
    if not isinstance(value, str):
        raise WorkbenchSettingsError(f"{field} 必须是文本")
    cleaned = value.strip()
    if len(cleaned) > MAX_URL_CHARS:
        raise WorkbenchSettingsError(f"{field} 过长")
    if cleaned and not (cleaned.startswith("https://") or cleaned.startswith("http://")):
        raise WorkbenchSettingsError(f"{field} 必须是有效的 http(s) 地址")
    return cleaned.rstrip("/")


def apply_settings_update(current: Dict[str, Any], payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate a partial settings update and return the new full settings."""

    if not isinstance(payload, Mapping):
        raise WorkbenchSettingsError("设置请求体必须是 JSON 对象")
    unknown = set(payload) - {
        "provider_mode",
        "base_url",
        "chat_base_url",
        "model",
        "api_key",
        "downloads_dir",
        "timeout_seconds",
    }
    if unknown:
        raise WorkbenchSettingsError("设置包含未知字段")
    data = dict(current)
    if "provider_mode" in payload:
        mode = payload["provider_mode"]
        if mode not in PROVIDER_MODES:
            raise WorkbenchSettingsError("提供方式只支持 responses 或 chat")
        data["provider_mode"] = mode
    if "base_url" in payload:
        data["base_url"] = _clean_url(payload["base_url"], "Responses 端点")
    if "chat_base_url" in payload:
        data["chat_base_url"] = _clean_url(payload["chat_base_url"], "Chat 兼容地址")
    if "model" in payload:
        model = payload["model"]
        if not isinstance(model, str) or len(model) > 200:
            raise WorkbenchSettingsError("模型名必须是文本")
        data["model"] = model.strip()
    if "api_key" in payload:
        key = payload["api_key"]
        if not isinstance(key, str) or len(key) > MAX_API_KEY_CHARS:
            raise WorkbenchSettingsError("API Key 必须是文本")
        data["api_key"] = key.strip()
    if "downloads_dir" in payload:
        raw = payload["downloads_dir"]
        if not isinstance(raw, str) or len(raw) > 2048:
            raise WorkbenchSettingsError("下载目录必须是文本")
        data["downloads_dir"] = raw.strip()
    if "timeout_seconds" in payload:
        timeout = payload["timeout_seconds"]
        if not isinstance(timeout, int) or isinstance(timeout, bool):
            raise WorkbenchSettingsError("超时必须是整数秒")
        if not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
            raise WorkbenchSettingsError(
                f"超时需在 {MIN_TIMEOUT_SECONDS}–{MAX_TIMEOUT_SECONDS} 秒之间"
            )
        data["timeout_seconds"] = timeout
    validate_settings(data)
    return data


def validate_settings(data: Dict[str, Any]) -> None:
    if data["provider_mode"] not in PROVIDER_MODES:
        raise WorkbenchSettingsError("提供方式只支持 responses 或 chat")
    _clean_url(data["base_url"], "Responses 端点")
    if data["provider_mode"] == "responses" and not data["base_url"]:
        raise WorkbenchSettingsError("responses 模式需要 Responses 端点")
    if data["provider_mode"] == "chat" and not data["chat_base_url"]:
        raise WorkbenchSettingsError("chat 模式需要 Chat 兼容地址")
    if data["downloads_dir"]:
        path = Path(data["downloads_dir"]).expanduser()
        if not path.is_absolute():
            raise WorkbenchSettingsError("下载目录必须是绝对路径")
        if not path.is_dir():
            raise WorkbenchSettingsError("下载目录不存在，请先在本机创建该文件夹")


def is_configured(data: Dict[str, Any]) -> bool:
    if not data["model"] or not data["api_key"]:
        return False
    if data["provider_mode"] == "chat":
        return bool(data["chat_base_url"])
    return bool(data["base_url"])


def save_settings(root: Path, data: Dict[str, Any]) -> None:
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_settings(data)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=".workbench-settings-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def masked_view(data: Dict[str, Any]) -> Dict[str, Any]:
    key = data["api_key"]
    if not key:
        masked = ""
    elif len(key) <= 8:
        masked = "****"
    else:
        masked = f"{key[:4]}…{key[-4:]}"
    return {
        "provider_mode": data["provider_mode"],
        "base_url": data["base_url"],
        "chat_base_url": data["chat_base_url"],
        "model": data["model"],
        "api_key_masked": masked,
        "downloads_dir": data["downloads_dir"],
        "timeout_seconds": data["timeout_seconds"],
        "configured": is_configured(data),
    }


def resolve_downloads_dir(data: Dict[str, Any]) -> Optional[Path]:
    if not data["downloads_dir"]:
        return None
    path = Path(data["downloads_dir"]).expanduser()
    return path if path.is_dir() else None
