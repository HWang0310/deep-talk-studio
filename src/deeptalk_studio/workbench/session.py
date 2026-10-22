"""Workbench session store: durable per-episode flow state.

Sessions live under ``workbench/sessions/<WBX-id>/`` (gitignored, private).
``session.json`` records the full flow state (topic, reference candidates,
studies, sources, research/thesis/script progress).  Writes are atomic and
serialized; artifacts themselves stay in the canonical engine trees
(``reports/`` / ``content_theses/`` / ``script_drafts/``, also gitignored).
"""

import json
import os
import secrets
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional


SESSION_FILENAME = "session.json"


class WorkbenchSessionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_session_id() -> str:
    return f"WBX-{secrets.token_hex(8)}"


class SessionStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._lock = threading.Lock()

    # -- paths ---------------------------------------------------------------

    def sessions_root(self) -> Path:
        return self.root / "sessions"

    def session_dir(self, session_id: str) -> Path:
        if not session_id or "/" in session_id or ".." in session_id:
            raise WorkbenchSessionError("会话 ID 无效")
        return self.sessions_root() / session_id

    def session_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / SESSION_FILENAME

    def references_dir(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "references"

    def sources_dir(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "sources"

    # -- lifecycle -----------------------------------------------------------

    def create(
        self,
        topic: str,
        candidates: List[Mapping[str, Any]],
        discovery_json_path: Optional[Path],
    ) -> Dict[str, Any]:
        with self._lock:
            session_id = new_session_id()
            directory = self.sessions_root() / session_id
            directory.mkdir(parents=True, exist_ok=False)
            (directory / "references").mkdir()
            (directory / "sources").mkdir()
            session = {
                "session_id": session_id,
                "topic": topic,
                "created_at": _now(),
                "status": "references",
                "discovery": {
                    "json_path": str(discovery_json_path) if discovery_json_path else "",
                    "candidates": list(candidates),
                },
                "references": {},  # bvid -> {"status": ..., "study_path": ...}
                "sources": [],  # [{"sid","url","title","kind","path","fetched_at"}]
                # DeepSeek Search/Fetch is an explicit, per-session budgeted
                # action.  Keep the budget and redacted provenance in the
                # durable session so a browser refresh cannot silently reset
                # the cap or make a paid request appear to be free.
                "search_budget": {
                    "opt_in": False,
                    "max_requests": 0,
                    "used": 0,
                    "results": [],
                    "records": [],
                    "last_error": "",
                },
                "research": {
                    "status": "not_started",
                    "draft_path": "",
                    "reviewed_path": "",
                    "approved_path": "",
                    "report_id": "",
                    "revision": 0,
                },
                "thesis": {
                    "status": "not_started",
                    "card_id": "",
                    "draft_path": "",
                    "review_path": "",
                    "approved_path": "",
                },
                "script": {
                    "status": "not_started",
                    "script_id": "",
                    "revision": 0,
                    "reviewed_path": "",
                    "gate_status": "",
                },
                "audio": {
                    "status": "not_imported",
                    "path": "",
                    "filename": "",
                    "origin": "",
                    "byte_size": 0,
                    "sha256": "",
                    "imported_at": "",
                },
                "audio_delivery": {
                    "status": "not_started",
                    "error": "",
                    "runner_kind": "real",
                    "started_at": "",
                    "completed_at": "",
                    "timeline": [],
                    "gaps": [],
                    "qa_status": "",
                    "paths": {},
                    "preview_path": "",
                },
            }
            self._write(session)
            return session

    def load(self, session_id: str) -> Dict[str, Any]:
        path = self.session_path(session_id)
        if not path.is_file():
            raise WorkbenchSessionError("会话不存在，请从输入选题重新开始")
        try:
            session = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise WorkbenchSessionError("会话文件损坏") from None
        if not isinstance(session, dict) or session.get("session_id") != session_id:
            raise WorkbenchSessionError("会话文件损坏")
        return session

    def load_latest(self) -> Optional[Dict[str, Any]]:
        root = self.sessions_root()
        if not root.is_dir():
            return None
        candidates = []
        for directory in root.iterdir():
            path = directory / SESSION_FILENAME
            if path.is_file():
                try:
                    candidates.append((path.stat().st_mtime_ns, directory.name))
                except OSError:
                    continue
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return self.load(candidates[0][1])

    def update(self, session_id: str, mutate: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        with self._lock:
            session = self.load(session_id)
            mutate(session)
            self._write(session)
            return session

    # -- storage helpers -----------------------------------------------------

    def _write(self, session: Dict[str, Any]) -> None:
        directory = self.session_dir(session["session_id"])
        fd, tmp = tempfile.mkstemp(dir=str(directory), prefix=".session-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(session, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp, self.session_path(session["session_id"]))
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def store_json(self, session_id: str, subdir: str, filename: str, payload: Mapping[str, Any]) -> Path:
        directory = self.session_dir(session_id) / subdir
        directory.mkdir(parents=True, exist_ok=True)
        if "/" in filename or filename.startswith("."):
            raise WorkbenchSessionError("文件名无效")
        path = directory / filename
        if path.exists():
            raise WorkbenchSessionError(f"工件已存在，不覆盖：{filename}")
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return path

    def load_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))
