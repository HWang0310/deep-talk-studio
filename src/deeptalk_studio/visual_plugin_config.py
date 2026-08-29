"""Strict static configuration for subprocess-only visual plugins."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping


CONFIG_VERSION = "visual-asset-plugin-config/1"
_ROOT_FIELDS = frozenset({"config_version", "plugins"})
_PLUGIN_FIELDS = frozenset({
    "plugin_id", "plugin_root", "argv_prefix", "timeout_seconds", "environment", "enabled",
    "plugin_version_command", "expected_source_revision", "require_clean_worktree",
})


class VisualPluginConfigError(ValueError):
    pass


def config_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(normalize_visual_plugin_config(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def normalize_visual_plugin_config(value: Any) -> dict:
    if not isinstance(value, Mapping) or set(value) != _ROOT_FIELDS:
        raise VisualPluginConfigError("plugin config 字段无效")
    if value.get("config_version") != CONFIG_VERSION or not isinstance(value.get("plugins"), list):
        raise VisualPluginConfigError("plugin config 版本或 plugins 无效")
    seen = set(); plugins = []
    for item in value["plugins"]:
        if not isinstance(item, Mapping) or set(item) != _PLUGIN_FIELDS:
            raise VisualPluginConfigError("plugin 字段无效")
        plugin = copy.deepcopy(dict(item)); plugin_id = _identifier(plugin["plugin_id"], "plugin_id")
        if plugin_id in seen: raise VisualPluginConfigError("plugin_id 不可重复")
        seen.add(plugin_id)
        if not isinstance(plugin["plugin_root"], str) or not plugin["plugin_root"].strip(): raise VisualPluginConfigError("plugin_root 无效")
        _argv(plugin["argv_prefix"], "argv_prefix"); _argv(plugin["plugin_version_command"], "plugin_version_command")
        if not isinstance(plugin["timeout_seconds"], (int, float)) or isinstance(plugin["timeout_seconds"], bool) or plugin["timeout_seconds"] <= 0: raise VisualPluginConfigError("timeout_seconds 必须为正数")
        if not isinstance(plugin["environment"], Mapping) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in plugin["environment"].items()): raise VisualPluginConfigError("environment 无效")
        if not isinstance(plugin["enabled"], bool) or not isinstance(plugin["require_clean_worktree"], bool): raise VisualPluginConfigError("enabled 或 require_clean_worktree 无效")
        if not isinstance(plugin["expected_source_revision"], str) or not plugin["expected_source_revision"]: raise VisualPluginConfigError("expected_source_revision 无效")
        plugins.append(plugin)
    return {"config_version": CONFIG_VERSION, "plugins": plugins}


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", value): raise VisualPluginConfigError(f"{label} 无效")
    return value


def _argv(value: Any, label: str) -> None:
    if not isinstance(value, list) or not value or any(not isinstance(part, str) or not part for part in value): raise VisualPluginConfigError(f"{label} 必须是非空 argv list")
