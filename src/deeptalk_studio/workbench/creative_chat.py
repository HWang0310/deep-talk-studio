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
        self.directory = self.root / "workbench" / "chat"
        self._lock = threading.RLock()

    # -- paths ----------------------------------------------------------

    def _session_path(self, session_id: str) -> Path:
        raw = str(session_id or "")
        if not raw or len(raw) > 64 or any(c not in "0123456789abcdef" for c in raw):
            raise CreativeChatError("会话标识无效")
        return self.directory / f"{raw}.json"

    # -- load / save ----------------------------------------------------

    def _load_path(self, path: Path) -> Optional[Dict[str, Any]]:
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

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._load_path(self._session_path(session_id))

    def load_latest(self) -> Optional[Dict[str, Any]]:
        if not self.directory.is_dir():
            return None
        candidates = sorted(
            (p for p in self.directory.glob("*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
        for path in reversed(candidates):
            data = self._load_path(path)
            if data:
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

    # -- mutation (append-only) ----------------------------------------

    def _touch(self, session: Dict[str, Any]) -> None:
        session["updated_at"] = _now()
        self.save(session)

    # -- 并发安全（Nexus B2）：锁内 re-load latest + append + save --------
    # 所有跨请求的持久化变更都走这里：绝不把内存里的旧快照整体写回，
    # 否则重叠请求（A 流式完成覆盖 B 已保存的 turn/draft）会永久丢数据。

    def start_user_turn(
        self,
        message: str,
        links: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Atomically open (or reuse) the latest session and append a user turn."""

        with self._lock:
            session = self.load_latest()
            if session is None:
                session = self.new_session()
            turn = self.append_turn(session, "user", message, links=links)
            return {"session": session, "turn": turn}

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
        }
