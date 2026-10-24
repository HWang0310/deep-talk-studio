"""Creative chat sessions and Creative Draft storage (Issue #44 chat-first MVP).

``creative-draft/1`` is deliberately distinct from the canonical Reviewed
Script contract:

- A draft is always ``status: "unreviewed"`` and never writes
  ``research.approved_path``, ``thesis.approved_path``,
  ``script.reviewed_path`` or any quality-Gate field; it never unlocks
  canonical timed-asset production.
- Turns and draft revisions are immutable (append-only) so reload/refresh
  can recover the exact conversation.
- Files are written with 0600 permissions; no API keys, secrets or
  credentials are ever stored here, and no private content leaks into
  logs, GET parameters or Git.
"""

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

CHAT_SCHEMA = "creative-chat/1"
DRAFT_SCHEMA = "creative-draft/1"

MAX_TURNS = 400
MAX_MESSAGE_CHARS = 20000
MAX_DRAFT_CHARS = 60000

# 用户级稳定聊天历史目录（Owner 会话数据跨工作树/升级持久化，
# issuecomment-6366157284）：与 Key 同模式——测试/演示环境通过注入
# 隔离，绝不读写真实 ~/.deeptalk。
USER_CHAT_DIR: Optional[Path] = None


def user_chat_dir() -> Path:
    base = USER_CHAT_DIR if USER_CHAT_DIR is not None else Path.home()
    return Path(base) / ".deeptalk" / "chat"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class CreativeChatError(RuntimeError):
    """A creative-chat operation failed (never includes secrets)."""


class CreativeChatStore:
    """Append-only local storage for one chat session and its drafts.

    所有变更都在内部锁内 **重新加载最新会话** 后追加再保存
    （load-modify-save 原子化），保证并发/重叠请求（两个标签页、
    流式中途草稿编辑）不会用陈旧快照覆盖对方的 turns/drafts。
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        # 聊天历史存用户级稳定目录（跨工作树/升级不丢，与 Key 同模式）；
        # 仓库级 workbench/chat 仅作向后兼容 fallback：首次发现即一次性
        # 迁移到用户级（同 ID 不覆盖、原文件保留、幂等、0600）。
        self.repo_directory = self.root / "workbench" / "chat"
        self.directory = user_chat_dir()
        self._ensure_private_directory()
        self._migrate_repo_chat_to_user()
        self._lock = threading.RLock()

    def _ensure_private_directory(self) -> None:
        """B7（review 5630859051）：历史目录显式私有 0700（文件已 0600）。

        显式 chmod 而非依赖 umask —— 已存在/新建同样生效；失败尽力而为
        不阻断（后续 save 的 mkdir 会再尝试）。"""
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            os.chmod(self.directory, 0o700)
        except OSError:
            return

    def _migrate_repo_chat_to_user(self) -> None:
        """一次性向后兼容迁移：把仓库级聊天历史复制到用户级。

        - 同名会话绝不覆盖（用户级已是唯一真源，旧文件只作首次迁移输入）；
        - 仓库级原文件保留（安全回退），迁移幂等可重复执行；
        - B7（review 5630859051）：单个损坏/半截 JSON 只跳过该文件，
        绝不让迁移（进而整个聊天初始化）失败；损坏原件原地保留待人工
        恢复，错误绝不携带文件内容进任何日志；
        - 复制件 0600；失败静默回退仓库级语义（下次启动再试）。
        """

        try:
            if not self.repo_directory.is_dir():
                return
            existing = {p.name for p in self.directory.glob("*.json")}
            for path in self.repo_directory.glob("*.json"):
                if not path.is_file() or path.name in existing:
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue  # 损坏件跳过：原件保留，不影响其他会话迁移
                if not isinstance(data, dict) or data.get("schema") != CHAT_SCHEMA:
                    continue
                fd, tmp = tempfile.mkstemp(
                    dir=str(self.directory), prefix=".chat-migrate-", suffix=".tmp"
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        json.dump(data, handle, ensure_ascii=False, indent=2)
                    os.chmod(tmp, 0o600)
                    os.replace(tmp, self.directory / path.name)
                except OSError:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
        except OSError:
            return

    # -- paths ----------------------------------------------------------

    def _session_path(self, session_id: str) -> Path:
        raw = str(session_id or "")
        if not raw or len(raw) > 64 or any(c not in "0123456789abcdef" for c in raw):
            raise CreativeChatError("会话标识无效")
        return self.directory / f"{raw}.json"

    # -- load / save ----------------------------------------------------

    def _load_path(self, path: Path) -> Optional[Dict[str, Any]]:
        if path.is_symlink():
            raise CreativeChatError("不允许符号链接会话文件")
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise CreativeChatError("聊天会话文件损坏，无法恢复") from None
        if not isinstance(data, dict) or data.get("schema") != CHAT_SCHEMA:
            raise CreativeChatError("聊天会话文件损坏，无法恢复")
        return data

    def save(self, session: Dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._session_path(session.get("session_id", ""))
        fd, tmp = tempfile.mkstemp(dir=str(self.directory), prefix=".chat-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(session, handle, ensure_ascii=False, indent=2)
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise CreativeChatError("聊天会话保存失败，请重试") from None

    def load(self, session_id: str, *, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        data = self._load_path(self._session_path(session_id))
        if data and data.get("deleted_at") and not include_deleted:
            raise CreativeChatError("会话已移入回收站，请先恢复")
        return data

    def manage_session(self, session_id: str, action: str, title: str = "") -> None:
        with self._lock:
            session = self.load(session_id, include_deleted=True)
            if not session:
                raise CreativeChatError("聊天会话不存在")
            if action == "rename":
                title = str(title).strip()
                if not title or len(title) > 80 or any(ord(c) < 32 for c in title):
                    raise CreativeChatError("标题需为 1–80 个可见字符")
                session["custom_title"] = title
            elif action == "delete":
                session["deleted_at"] = _now()
            elif action == "restore":
                session.pop("deleted_at", None)
            else:
                raise CreativeChatError("未知会话操作")
            self._touch(session)

    def load_latest(self) -> Optional[Dict[str, Any]]:
        if not self.directory.is_dir():
            return None
        candidates = sorted(
            (p for p in self.directory.glob("*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
        for path in reversed(candidates):
            # B7（review 5630859051）：最近会话文件损坏时只跳过该件
            # （原件保留待人工恢复），返回最近的「有效」会话；绝不因单个
            # 损坏件让 latest 语义对其他健康会话失效。
            try:
                data = self._load_path(path)
            except (CreativeChatError, OSError):
                continue
            if data and not data.get("deleted_at"):
                return data
        return None

    def new_session(self) -> Dict[str, Any]:
        import uuid

        session = {
            "schema": CHAT_SCHEMA,
            "session_id": uuid.uuid4().hex,
            "created_at": _now(),
            "updated_at": _now(),
            "turns": [],
            "drafts": [],
        }
        self.save(session)
        return session

    def list_sessions(self, limit: int = 200, *, deleted: bool = False) -> List[Dict[str, Any]]:
        """会话元数据列表（按最近更新倒序）：ID、标题（首条用户消息截断）、
        更新时间、消息/草稿计数。标题绝不做额外模型调用。"""

        with self._lock:
            if not self.directory.is_dir():
                return []
            items: List[Dict[str, Any]] = []
            for path in self.directory.glob("*.json"):
                if not path.is_file():
                    continue
                # B7（review 5630859051）：损坏/半截文件只跳过该会话
                # （不出现在列表，原件保留待人工恢复），其他会话照常
                # 加载；错误绝不携带内容。
                try:
                    data = self._load_path(path)
                    mtime = path.stat().st_mtime
                except (CreativeChatError, OSError):
                    continue
                if not data or bool(data.get("deleted_at")) != deleted:
                    continue
                title = ""
                for turn in data.get("turns", []):
                    if turn.get("role") == "user" and str(turn.get("content", "")).strip():
                        title = str(turn.get("content", "")).strip()[:40]
                        break
                items.append({
                    "session_id": str(data.get("session_id", path.stem)),
                    "title": data.get("custom_title") or title or "新对话",
                    "updated_at": str(data.get("updated_at", "")),
                    "turns": len(data.get("turns", [])),
                    "drafts": len(data.get("drafts", [])),
                    # 排序辅助：updated_at 是秒级精度，同一秒内的更新用
                    # 文件 mtime（更高精度）作为次级键，保证最近更新者居前。
                    "_mtime": mtime,
                })
            items.sort(
                key=lambda item: (item["updated_at"], item["_mtime"]),
                reverse=True,
            )
            for item in items:
                item.pop("_mtime", None)
            return items[:limit]

    def start_user_turn(
        self,
        message: str,
        links: Optional[List[Dict[str, Any]]] = None,
        *,
        session_id: str = "",
        new_session: bool = False,
    ) -> Dict[str, Any]:
        """Atomically append a user turn to the selected conversation.

        解析优先级：new_session（显式新建）> session_id（指定会话，不存在
        即报错，绝不静默回落 latest）> latest（兼容旧调用，无则新建）。
        """

        with self._lock:
            if new_session:
                session = self.new_session()
            elif session_id:
                session = self.load(session_id)
                if session is None:
                    raise CreativeChatError("聊天会话不存在，请重新发送")
            else:
                session = self.load_latest()
                if session is None:
                    session = self.new_session()
            turn = self.append_turn(session, "user", message, links=links)
            return {"session": session, "turn": turn}

    # -- mutation (append-only) ----------------------------------------

    def _touch(self, session: Dict[str, Any]) -> None:
        session["updated_at"] = _now()
        self.save(session)

    # -- 并发安全（Nexus B2）：锁内 re-load latest + append + save --------
    # 所有跨请求的持久化变更都走这里：绝不把内存里的旧快照整体写回，
    # 否则重叠请求（A 流式完成覆盖 B 已保存的 turn/draft）会永久丢数据。

    def retry_user_turn(self, session_id: str, turn_id: str) -> Dict[str, Any]:
        """Idempotently reuse an existing pending user turn for an explicit retry.

        The turn must still be the latest turn and have no assistant reply;
        retry never appends a duplicate user turn into the conversation.
        """

        with self._lock:
            session = self.load(session_id)
            if session is None:
                raise CreativeChatError("聊天会话不存在，请重新发送")
            turns = session.get("turns", [])
            last = turns[-1] if turns else None
            if (
                not last
                or last.get("turn_id") != turn_id
                or last.get("role") != "user"
            ):
                raise CreativeChatError("上一条消息状态已变化，请直接重新发送")
            return {"session": session, "turn": last}

    def append_assistant_turn(
        self,
        session_id: str,
        content: str,
        *,
        model: str = "",
        provider_mode: str = "",
        provider_kind: str = "",
    ) -> Dict[str, Any]:
        """Atomically append the completed assistant turn to the LATEST session."""

        with self._lock:
            session = self.load(session_id)
            if session is None:
                raise CreativeChatError("聊天会话不存在，无法保存回复")
            return self.append_turn(
                session,
                "assistant",
                content,
                model=model,
                provider_mode=provider_mode,
                provider_kind=provider_kind,
            )

    def append_draft_latest(
        self,
        session_id: str,
        content: str,
        *,
        origin: str,
        origin_turn_id: str = "",
        model: str = "",
        provider_kind: str = "",
    ) -> Dict[str, Any]:
        """Atomically append a draft revision to the LATEST session."""

        with self._lock:
            session = self.load(session_id)
            if session is None:
                raise CreativeChatError("聊天会话不存在，无法保存草稿")
            return self.append_draft(
                session,
                content,
                origin=origin,
                origin_turn_id=origin_turn_id,
                model=model,
                provider_kind=provider_kind,
            )

    def latest_session_id(self) -> Optional[str]:
        with self._lock:
            session = self.load_latest()
            return str(session.get("session_id", "")) if session else None

    def set_discovery(
        self, session_id: str, discovery: Dict[str, Any]
    ) -> bool:
        """Persist each topic at its original turn; legacy singleton stays readable."""

        with self._lock:
            session = self.load(session_id)
            if session is None:
                raise CreativeChatError("聊天会话不存在，无法保存检索证据")
            records = self.discoveries(session)
            if any(d.get("query") == discovery.get("query") or
                   d.get("turn_id") == discovery.get("turn_id") for d in records):
                return False
            record = {
                "query": str(discovery.get("query", ""))[:200],
                "status": str(discovery.get("status", "unavailable")),
                "sources": [
                    {
                        **{key: item[key] for key in ("bvid", "view_count", "view_count_status", "view_count_source", "fetched_at", "duration_sec", "retrieval_note") if key in item},
                        "title": str(item.get("title", ""))[:500],
                        "uploader": str(item.get("uploader", ""))[:200],
                        "published_at": str(item.get("published_at", ""))[:100],
                        "url": str(item.get("url", ""))[:500],
                        "description": str(item.get("description", ""))[:500],
                    }
                    for item in (discovery.get("sources") or [])[:6]
                ],
                "note": str(discovery.get("note", ""))[:300],
                "turn_id": str(discovery.get("turn_id", ""))[:40],
                "created_at": _now(),
            }
            records.append(record)
            session["topic_discoveries"] = records
            session["topic_discovery"] = record
            self._touch(session)
            return True

    @staticmethod
    def discoveries(session):
        records = list(session.get("topic_discoveries") or [])
        legacy = session.get("topic_discovery")
        if legacy and not any(d.get("turn_id") == legacy.get("turn_id") for d in records):
            records.insert(0, dict(legacy))
        return records

    def bind_reference_session(self, session_id: str, turn_id: str, reference_id: str) -> str:
        with self._lock:
            session = self.load(session_id)
            if not session:
                raise CreativeChatError("聊天会话不存在")
            records = self.discoveries(session)
            record = next((d for d in records if d.get("turn_id") == turn_id), None)
            if not record:
                raise CreativeChatError("选题来源不存在")
            record.setdefault("reference_session_id", reference_id)
            session["topic_discoveries"] = records
            session["topic_discovery"] = records[-1]
            self._touch(session)
            return record["reference_session_id"]

    def append_turn(
        self,
        session: Dict[str, Any],
        role: str,
        content: str,
        *,
        links: Optional[List[Dict[str, Any]]] = None,
        model: str = "",
        provider_mode: str = "",
        provider_kind: str = "",
    ) -> Dict[str, Any]:
        with self._lock:
            return self._append_turn_locked(
                session, role, content,
                links=links, model=model,
                provider_mode=provider_mode, provider_kind=provider_kind,
            )

    def _append_turn_locked(
        self,
        session: Dict[str, Any],
        role: str,
        content: str,
        *,
        links: Optional[List[Dict[str, Any]]] = None,
        model: str = "",
        provider_mode: str = "",
        provider_kind: str = "",
    ) -> Dict[str, Any]:
        if role not in {"user", "assistant"}:
            raise CreativeChatError("消息角色无效")
        text = str(content or "")
        if not text.strip():
            raise CreativeChatError("消息内容不能为空")
        if len(text) > MAX_MESSAGE_CHARS:
            raise CreativeChatError("消息内容过长，请分段发送")
        if len(session.setdefault("turns", [])) >= MAX_TURNS:
            raise CreativeChatError("本会话消息数量已达上限，请新开会话")
        index = len(session["turns"])
        turn = {
            "turn_id": f"t{index + 1}",
            "role": role,
            "content": text,
            "created_at": _now(),
        }
        if links:
            turn["links"] = [
                {"url": str(item.get("url", ""))[:500], "status": "unknown"}
                for item in links
                if item.get("url")
            ]
        if role == "assistant":
            turn["model"] = str(model or "")
            turn["provider_mode"] = str(provider_mode or "")
            turn["provider_kind"] = str(provider_kind or "")
        session["turns"].append(turn)
        self._touch(session)
        return turn

    def append_draft(
        self,
        session: Dict[str, Any],
        content: str,
        *,
        origin: str,
        origin_turn_id: str = "",
        model: str = "",
        provider_kind: str = "",
    ) -> Dict[str, Any]:
        with self._lock:
            return self._append_draft_locked(
                session, content, origin=origin,
                origin_turn_id=origin_turn_id, model=model,
                provider_kind=provider_kind,
            )

    def _append_draft_locked(
        self,
        session: Dict[str, Any],
        content: str,
        *,
        origin: str,
        origin_turn_id: str = "",
        model: str = "",
        provider_kind: str = "",
    ) -> Dict[str, Any]:
        if origin not in {"model", "user_edit"}:
            raise CreativeChatError("草稿来源无效")
        text = str(content or "")
        if not text.strip():
            raise CreativeChatError("草稿内容不能为空")
        if len(text) > MAX_DRAFT_CHARS:
            raise CreativeChatError("草稿内容过长")
        drafts = session.setdefault("drafts", [])
        draft = {
            "schema": DRAFT_SCHEMA,
            "draft_id": f"d{len(drafts) + 1}",
            "revision": len(drafts) + 1,
            "content": text,
            "created_at": _now(),
            "origin": origin,
            "origin_turn_id": str(origin_turn_id or ""),
            "model": str(model or ""),
            # B4：模型来源标注持久化在 revision 内，重载后不丢，
            # 浏览器才能可靠区分本地夹具与真实模型。
            "provider_kind": str(provider_kind or ""),
            # 创作草稿永远是未审核：区别于 canonical Reviewed Script，
            # 不携带任何 approved/reviewed/quality-Gate 字段。
            "status": "unreviewed",
        }
        drafts.append(draft)
        self._touch(session)
        return draft

    # -- views ----------------------------------------------------------

    @staticmethod
    def view(session: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """A safe, secret-free view for the browser (turns + drafts)."""

        if not session:
            return None
        return {
            "schema": session.get("schema", CHAT_SCHEMA),
            "session_id": session.get("session_id", ""),
            "created_at": session.get("created_at", ""),
            "updated_at": session.get("updated_at", ""),
            "turns": list(session.get("turns", [])),
            "drafts": list(session.get("drafts", [])),
            # Issue #29：检索证据（或「未联网核实」声明）随会话恢复，
            # 浏览器刷新后来源小字不丢。
            "topic_discovery": dict(session.get("topic_discovery") or {}),
            "topic_discoveries": CreativeChatStore.discoveries(session),
        }
