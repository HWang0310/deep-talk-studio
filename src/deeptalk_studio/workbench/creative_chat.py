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
    """Append-only local storage for one chat session and its drafts."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.directory = self.root / "workbench" / "chat"

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
