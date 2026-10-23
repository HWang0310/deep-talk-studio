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
    "provider_mode": "responses",  # responses | chat | deepseek
    "base_url": "https://api.openai.com/v1/responses",
    "chat_base_url": "",  # e.g. https://host/v1  (endpoint = base + /chat/completions)
    "model": "",
    "api_key": "",
    "downloads_dir": "",  # user-specified folder for authorized reference media
    "timeout_seconds": 600,
    # Non-secret connection observations.  These are deliberately separate
    # from the credential so a failed test can be shown after a restart.
    "connection_status": "not_tested",
    "connection_kind": "real",
    "connection_tested_at": "",
    "connection_error": "",
    "connection_provider": "",
    "connection_model": "",
    "connection_endpoint": "",
}

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-flash"
DEEPSEEK_OPTIONAL_MODEL = "deepseek-v4-pro"
PROVIDER_MODES = {"responses", "chat", "deepseek"}
MIN_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 1800
MAX_API_KEY_CHARS = 4096
MAX_URL_CHARS = 512


class WorkbenchSettingsError(ValueError):
    """Invalid workbench settings payload."""


def settings_path(root: Path) -> Path:
    return Path(root) / "config" / "workbench.local.json"


# 用户级稳定配置目录（Owner Key 跨工作树/产品更新持久化，issuecomment-6364369899）。
# 测试通过注入临时目录隔离，绝不读写真实 ~/.deeptalk。
USER_SETTINGS_DIR: Optional[Path] = None


def user_settings_path() -> Path:
    base = USER_SETTINGS_DIR if USER_SETTINGS_DIR is not None else Path.home()
    return Path(base) / ".deeptalk" / "workbench.local.json"


def _read_settings_file(path: Path) -> Dict[str, Any]:
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise WorkbenchSettingsError("工作台设置文件损坏，请重新保存设置")
    if not isinstance(stored, dict):
        raise WorkbenchSettingsError("工作台设置文件损坏，请重新保存设置")
    data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in stored:
            data[key] = stored[key]
    return data


def _atomic_write_settings(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _migrate_repo_settings_to_user(repo_path: Path, user_path: Path) -> None:
    """一次性向后兼容迁移：把仓库级配置复制到用户级（0600），原文件保留。

    迁移是尽力而为：失败时本次回退读仓库级配置，下次加载再试；
    用户级文件一旦存在即优先，所有工作树共用同一份已保存 Key。
    """

    try:
        data = json.loads(repo_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        _atomic_write_settings(user_path, {
            key: data[key] for key in DEFAULT_SETTINGS if key in data
        })
    except (OSError, ValueError):
        return


def load_settings(root: Path) -> Dict[str, Any]:
    """Owner Key 持久化：用户级配置优先，任何工作树/产品更新共用同一份。

    首次发现仓库级 config 且用户级尚不存在时，一次性迁移到用户级
    （原文件保留作为旧版本 fallback），此后保存/清除都只写用户级。
    """

    user_path = user_settings_path()
    if user_path.is_file():
        return _read_settings_file(user_path)
    repo_path = settings_path(root)
    if repo_path.is_file():
        data = _read_settings_file(repo_path)
        _migrate_repo_settings_to_user(repo_path, user_path)
        return data
    return dict(DEFAULT_SETTINGS)


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
            raise WorkbenchSettingsError("提供方式只支持 responses、chat 或 deepseek")
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
    # Selecting the DeepSeek preset is an explicit user action.  Nexus P0
    # (PR #45 review 5625537364): while provider_mode is "deepseek" the
    # server unconditionally pins the official endpoint and model, so a
    # stale hidden custom chat URL/model can never survive a provider
    # switch and a newly entered DeepSeek key is never routed to the
    # previous custom endpoint.  There is no advanced override for this in
    # the UI; anyone needing a custom target must switch to "chat" mode.
    if data["provider_mode"] == "deepseek":
        data["chat_base_url"] = DEEPSEEK_BASE_URL
        data["model"] = DEEPSEEK_DEFAULT_MODEL
    # A changed provider/endpoint/model/key invalidates an older connection
    # observation.  Do this after normalization so equivalent URLs do not
    # cause a needless reset.
    observed_fields = ("provider_mode", "base_url", "chat_base_url", "model", "api_key")
    if any(data.get(field) != current.get(field) for field in observed_fields):
        data.update(
            {
                "connection_status": "not_tested",
                "connection_kind": "real",
                "connection_tested_at": "",
                "connection_error": "",
                "connection_provider": "",
                "connection_model": "",
                "connection_endpoint": "",
            }
        )
    validate_settings(data)
    return data


def validate_settings(data: Dict[str, Any]) -> None:
    if data["provider_mode"] not in PROVIDER_MODES:
        raise WorkbenchSettingsError("提供方式只支持 responses、chat 或 deepseek")
    _clean_url(data["base_url"], "Responses 端点")
    if data["provider_mode"] == "responses" and not data["base_url"]:
        raise WorkbenchSettingsError("responses 模式需要 Responses 端点")
    if data["provider_mode"] in {"chat", "deepseek"} and not data["chat_base_url"]:
        raise WorkbenchSettingsError("Chat 兼容模式需要 Chat 兼容地址")
    if data["downloads_dir"]:
        path = Path(data["downloads_dir"]).expanduser()
        if not path.is_absolute():
            raise WorkbenchSettingsError("下载目录必须是绝对路径")
        if not path.is_dir():
            raise WorkbenchSettingsError("下载目录不存在，请先在本机创建该文件夹")


def is_configured(data: Dict[str, Any]) -> bool:
    if not data["model"] or not data["api_key"]:
        return False
    if data["provider_mode"] in {"chat", "deepseek"}:
        return bool(data["chat_base_url"])
    return bool(data["base_url"])


def save_settings(root: Path, data: Dict[str, Any]) -> None:
    validate_settings(data)
    _atomic_write_settings(user_settings_path(), data)
    # 显式清除 Key 时同步清掉仓库级旧文件里的 Key：旧版本 fallback 不会
    # 让已清除的 Key 复活，也不在磁盘上残留明文（其余字段保留不动）。
    repo_path = settings_path(root)
    if not data.get("api_key") and repo_path.is_file():
        try:
            stored = json.loads(repo_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = None
        if isinstance(stored, dict) and stored.get("api_key"):
            stored["api_key"] = ""
            _atomic_write_settings(repo_path, stored)


def masked_view(data: Dict[str, Any]) -> Dict[str, Any]:
    key = data["api_key"]
    if not key:
        masked = ""
    elif len(key) <= 8:
        masked = "****"
    else:
        masked = f"{key[:4]}…{key[-4:]}"
    endpoint = effective_chat_endpoint(data) if data["provider_mode"] in {"chat", "deepseek"} else data["base_url"]
    provider_label = {
        "responses": "OpenAI Responses",
        "chat": "通用 Chat 兼容",
        "deepseek": "DeepSeek",
    }.get(data["provider_mode"], data["provider_mode"])
    return {
        "provider_mode": data["provider_mode"],
        "provider_label": provider_label,
        "base_url": data["base_url"],
        "chat_base_url": data["chat_base_url"],
        "endpoint": endpoint,
        "model": data["model"],
        "api_key_masked": masked,
        "downloads_dir": data["downloads_dir"],
        "timeout_seconds": data["timeout_seconds"],
        "configured": is_configured(data),
        "connection_status": data.get("connection_status", "not_tested"),
        "connection_kind": data.get("connection_kind", "real"),
        "connection_tested_at": data.get("connection_tested_at", ""),
        "connection_error": data.get("connection_error", ""),
        "connection_provider": data.get("connection_provider", ""),
        "connection_model": data.get("connection_model", ""),
        "connection_endpoint": data.get("connection_endpoint", ""),
    }


def effective_chat_endpoint(data: Mapping[str, Any]) -> str:
    """Compose an OpenAI-compatible endpoint exactly once."""

    base = str(data.get("chat_base_url", "") or "").strip().rstrip("/")
    return base if base.endswith("/chat/completions") else base + "/chat/completions"


def resolve_downloads_dir(data: Dict[str, Any]) -> Optional[Path]:
    if not data["downloads_dir"]:
        return None
    path = Path(data["downloads_dir"]).expanduser()
    return path if path.is_dir() else None
