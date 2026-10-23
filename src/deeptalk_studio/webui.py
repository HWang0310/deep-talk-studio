"""Mac-local Web UI server for the Phase 1B reference discovery (Issue #26).

A deliberately small, dependency-free loopback Web server (Python standard
library only) that serves the Chinese creator page and exposes exactly one
business endpoint: ``POST /api/discover``. The endpoint calls the accepted
Phase 1 discovery service directly (:func:`build_reference_candidate_set`
with a fresh :class:`BilibiliReferenceProvider` per request), so every run is
a new bounded run with the run-level risk-control latch semantics preserved.
No filtering, ordering or validation is duplicated in JavaScript and no CLI
output is ever parsed.

Security posture (matches Issue #26 hard boundaries and the Nexus review):

- Binds ``127.0.0.1`` only; no external exposure. Beyond the bind address,
  every request must pass loopback request-boundary checks: a narrow
  ``Host`` allowlist matching the actually listened port (``127.0.0.1`` /
  ``localhost``), same-origin ``Origin`` when present (cross-site / ``null``
  browser origins are rejected — CORS failure alone would not stop the
  request from reaching the server), and — for the JSON API — an explicit
  ``Content-Type: application/json``. No preflight (``OPTIONS``) support:
  cross-origin browser JSON posts fail before delivery.
- Request bodies are read only after ``Content-Length`` is validated to be a
  single well-formed non-negative integer within the size cap
  (missing/duplicate/non-numeric → 411, negative → 400, too large → 413,
  unsupported ``Transfer-Encoding`` → 411 + close). No unbounded reads; the
  handler also enforces a socket timeout.
- Responses are JSON with ``X-Content-Type-Options: nosniff``; the static
  page never reflects request data and the client renders everything through
  ``textContent`` (no ``innerHTML``). Rejection errors never echo request
  headers or raw URLs.
- No arbitrary fetch/proxy endpoint, no command execution, no user-supplied
  output paths. Artifacts persist to a fixed local directory using their
  unique ``REF-`` ids with exclusive-create (``O_EXCL``) semantics: an
  existing artifact is never overwritten; a conflicting id surfaces a safe
  error to the caller.
- Access logs record method/path/status/size only — request bodies (which may
  contain user URLs with tracking parameters) are never logged.
- Discovery runs are serialized with a lock so at most one bounded network
  run executes at a time; repeated clicks queue as new bounded runs.
"""

import json
import mimetypes
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Optional

from .bilibili_reference_provider import BilibiliReferenceProvider
from .content_director import ContentDirectorValidationError
from .reference_discovery import (
    ReferenceDiscoveryError,
    build_reference_candidate_set,
)
from .script_validation import ScriptValidationError
from .validation import ReportValidationError
from .workbench.creative_chat import CreativeChatError
from .workbench.flow import WorkbenchFlowError
from .workbench.llm import WorkbenchLLMError

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8321
MAX_REQUEST_BYTES = 8192
MAX_TOPIC_CHARS = 200
MAX_URL_COUNT = 5
MAX_URL_CHARS = 300
SOCKET_TIMEOUT_SECONDS = 10
MAX_AUDIO_UPLOAD_BYTES = 512 * 1024 * 1024
# Workbench route body caps (bytes): settings may carry a long key; pasted
# source text is intentionally generous; long-running operations stay small.
WORKBENCH_ROUTE_CAPS = {
    "/api/workbench/settings": 32 * 1024,
    "/api/workbench/settings/test": 2048,
    "/api/workbench/chat/stream": 64 * 1024,
    "/api/workbench/chat/draft": 2048,
    "/api/workbench/chat/draft/edit": 128 * 1024,
    "/api/workbench/session/start": 32 * 1024,
    "/api/workbench/references/acquire": 64 * 1024,
    "/api/workbench/references/analyze": 2048,
    "/api/workbench/references/reanalyze": 2048,
    "/api/workbench/sources/url": 4096,
    "/api/workbench/sources/text": 420 * 1024,
    "/api/workbench/research/search": 16 * 1024,
    "/api/workbench/research/fetch": 8 * 1024,
    "/api/workbench/research/generate": 16 * 1024,
    "/api/workbench/fact-check/run": 2048,
    "/api/workbench/research/approve": 16 * 1024,
    "/api/workbench/thesis/generate": 2048,
    "/api/workbench/thesis/review": 2048,
    "/api/workbench/thesis/approve": 16 * 1024,
    "/api/workbench/script/generate": 2048,
    "/api/workbench/audio/import": MAX_AUDIO_UPLOAD_BYTES,
    "/api/workbench/audio/deliver": 4096,
}

_STATIC_DIR = Path(__file__).resolve().parent / "webui_static"
INDEX_HTML_PATH = _STATIC_DIR / "index.html"

SERVICE_NAME = "deeptalk-webui"


class WebUIRequestError(ValueError):
    """Invalid client input; the server maps this to HTTP 400."""


class ArtifactWriteConflict(Exception):
    """An artifact with the same id already exists; nothing was overwritten."""


def validate_discover_payload(payload: object) -> Dict[str, object]:
    """Strict client-input validation for ``POST /api/discover``."""
    if not isinstance(payload, dict):
        raise WebUIRequestError("请求体必须是 JSON 对象")
    unknown = set(payload) - {"topic", "urls"}
    if unknown:
        raise WebUIRequestError("仅支持 topic 与 urls 字段")
    topic = payload.get("topic")
    if not isinstance(topic, str):
        raise WebUIRequestError("topic 必须是字符串")
    topic = topic.strip()
    if not topic:
        raise WebUIRequestError("主题不能为空")
    if len(topic) > MAX_TOPIC_CHARS:
        raise WebUIRequestError(f"主题不能超过 {MAX_TOPIC_CHARS} 字")
    raw_urls = payload.get("urls", [])
    if not isinstance(raw_urls, list):
        raise WebUIRequestError("urls 必须是数组")
    if len(raw_urls) > MAX_URL_COUNT:
        raise WebUIRequestError(f"参考链接最多 {MAX_URL_COUNT} 条")
    urls = []
    for raw in raw_urls:
        if not isinstance(raw, str):
            raise WebUIRequestError("参考链接必须是字符串")
        cleaned = raw.strip()
        if not cleaned:
            raise WebUIRequestError("参考链接不能为空")
        if len(cleaned) > MAX_URL_CHARS:
            raise WebUIRequestError(f"单条链接不能超过 {MAX_URL_CHARS} 字符")
        urls.append(cleaned)
    return {"topic": topic, "urls": urls}


def _persist_artifact(output_dir: Path, artifact: Dict[str, object]) -> Path:
    """Write the run artifact with exclusive-create (never overwrite)."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"reference-candidate-set-{artifact['candidate_set_id']}.json"
    try:
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError:
        raise ArtifactWriteConflict(str(path)) from None
    return path


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: object) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_html(handler: BaseHTTPRequestHandler, status: int, body: bytes) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class _DeepTalkWebUIHandler(BaseHTTPRequestHandler):
    """Loopback-only handler; config is attached to the server object."""

    server_version = "DeepTalkWebUI/1"
    protocol_version = "HTTP/1.1"
    timeout = SOCKET_TIMEOUT_SECONDS

    # -- request boundary guards --------------------------------------

    def _allowed_hosts(self) -> tuple:
        port = self.server.server_address[1]
        return (f"127.0.0.1:{port}", f"localhost:{port}")

    def _same_origin_values(self) -> tuple:
        port = self.server.server_address[1]
        return (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

    def _boundary_rejection(self) -> Optional[str]:
        """Narrow-host + same-origin guard; None means the request may proceed.

        The check happens before any body is read and before the discovery
        service is touched. Rejection messages never echo the offending
        header value.
        """

        host = (self.headers.get("Host") or "").strip()
        if host not in self._allowed_hosts():
            return "本服务仅允许本机回环地址访问"
        origin = (self.headers.get("Origin") or "").strip()
        if origin and origin not in self._same_origin_values():
            return "本服务仅允许同源请求"
        return None

    def _content_type_rejection(self) -> Optional[str]:
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return "Content-Type 必须是 application/json"
        return None

    def _content_length_state(self, cap: int = MAX_REQUEST_BYTES) -> str:
        """Validate framing headers before any body read. Returns a state."""

        te_values = [value.strip().lower()
                     for value in (self.headers.get_all("Transfer-Encoding") or [])]
        if any(value and value != "identity" for value in te_values):
            return "transfer_encoding"
        length_values = self.headers.get_all("Content-Length") or []
        if len(length_values) != 1:
            return "length_invalid"
        try:
            length = int(length_values[0].strip())
        except ValueError:
            return "length_invalid"
        if length < 0:
            return "length_negative"
        if length > cap:
            return "length_too_large"
        return "ok"

    def _read_body(self, cap: int = MAX_REQUEST_BYTES) -> Optional[bytes]:
        """Read exactly Content-Length bytes; None means the request was rejected."""

        state = self._content_length_state(cap)
        if state == "transfer_encoding":
            self.close_connection = True
            _send_json(self, 411, {"error": "不支持 Transfer-Encoding 请求"})
            return None
        if state == "length_invalid":
            self.close_connection = True
            _send_json(self, 411, {"error": "Content-Length 缺失或无效"})
            return None
        if state == "length_negative":
            self.close_connection = True
            _send_json(self, 400, {"error": "Content-Length 不能为负数"})
            return None
        if state == "length_too_large":
            self.close_connection = True
            _send_json(self, 413, {"error": "请求体超过上限"})
            return None
        length = int((self.headers.get_all("Content-Length") or ["0"])[0].strip())
        return self.rfile.read(length) if length else b""

    # -- HTTP methods ---------------------------------------------------

    def do_GET(self) -> None:
        rejection = self._boundary_rejection()
        if rejection:
            _send_json(self, 403, {"error": rejection})
            return
        path = urllib.parse.urlparse(self.path).path
        if path in {"/", "/settings"}:
            try:
                body = INDEX_HTML_PATH.read_bytes()
            except OSError:
                _send_json(self, 500, {"error": "页面资源缺失"})
                return
            _send_html(self, 200, body)
            return
        if path == "/healthz":
            _send_json(self, 200, {"ok": True, "service": SERVICE_NAME})
            return
        if path == "/api/workbench/state":
            self._handle_workbench_get_state()
            return
        if path == "/api/workbench/script/final":
            self._handle_workbench_final_script()
            return
        if path == "/api/workbench/audio/artifact":
            self._handle_workbench_audio_artifact()
            return
        if path == "/api/workbench/audio/source":
            self._handle_workbench_audio_source()
            return
        _send_json(self, 404, {"error": "路径不存在"})

    def do_POST(self) -> None:
        rejection = self._boundary_rejection()
        if rejection:
            self.close_connection = True
            _send_json(self, 403, {"error": rejection})
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/discover":
            self._handle_discover_post()
            return
        if parsed.path == "/api/workbench/audio/import":
            self._handle_workbench_audio_import()
            return
        if parsed.path.startswith("/api/workbench/"):
            self._handle_workbench_post(parsed.path)
            return
        _send_json(self, 404, {"error": "路径不存在"})

    # -- discovery ------------------------------------------------------

    def _handle_discover_post(self) -> None:
        rejection = self._content_type_rejection()
        if rejection:
            self.close_connection = True
            _send_json(self, 415, {"error": rejection})
            return
        raw = self._read_body()
        if raw is None:
            return
        artifact = self._run_discovery(raw)
        if artifact is None:
            return
        _send_json(self, 200, artifact)

    def _run_discovery(self, raw: bytes):
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            _send_json(self, 400, {"error": "请求体不是合法 JSON"})
            return None
        try:
            request = validate_discover_payload(payload)
        except WebUIRequestError as exc:
            _send_json(self, 400, {"error": str(exc)})
            return None
        server: "_DeepTalkWebUIServer" = self.server  # type: ignore[assignment]
        try:
            # one bounded discovery run at a time; a repeated click queues as
            # a fresh run rather than bypassing anything in-flight
            with server.discovery_lock:
                provider = server.provider_factory()
                artifact = build_reference_candidate_set(
                    request["topic"], request["urls"], provider=provider
                )
                _persist_artifact(server.output_dir, artifact)
        except ArtifactWriteConflict:
            self.log_error("artifact write conflict for a run")
            _send_json(self, 500, {"error": "结果工件写入冲突，未覆盖已有文件，请重试检索"})
            return None
        except ReferenceDiscoveryError as exc:
            _send_json(self, 400, {"error": f"参考视频发现失败：{exc}"})
            return None
        except Exception:  # provider/IO crash must not kill the server
            self.log_error("discovery run failed: provider/IO")
            _send_json(self, 500, {"error": "本次检索执行失败，请稍后重试"})
            return None
        return artifact

    # -- workbench ------------------------------------------------------

    def _workbench_flow(self):
        server: "_DeepTalkWebUIServer" = self.server  # type: ignore[assignment]
        return server.flow

    def _workbench_json_body(self, path: str) -> Optional[Dict[str, object]]:
        rejection = self._content_type_rejection()
        if rejection:
            self.close_connection = True
            _send_json(self, 415, {"error": rejection})
            return None
        raw = self._read_body(WORKBENCH_ROUTE_CAPS.get(path, MAX_REQUEST_BYTES))
        if raw is None:
            return None
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            _send_json(self, 400, {"error": "请求体不是合法 JSON"})
            return None
        if not isinstance(payload, dict):
            _send_json(self, 400, {"error": "请求体必须是 JSON 对象"})
            return None
        return payload

    @staticmethod
    def _workbench_call(action):
        """Run one flow action and map its exceptions to typed JSON replies."""

        try:
            return action(), None
        except WorkbenchFlowError as exc:
            payload = {"error": str(exc)}
            payload.update(getattr(exc, "payload", {}) or {})
            return None, (400, payload)
        except WebUIRequestError as exc:
            return None, (400, {"error": str(exc)})
        except WorkbenchLLMError as exc:
            return None, (400, {"error": str(exc)})
        except (ReportValidationError, ScriptValidationError, ContentDirectorValidationError) as exc:
            return None, (400, {"error": f"引擎校验未通过：{exc}"})
        except Exception as exc:  # never kill the local server on one step
            return None, (500, {"error": f"这一步执行失败：{type(exc).__name__}：{str(exc)[:300]}"})

    def _handle_chat_stream(self, flow, payload: Dict[str, object]) -> None:
        """真实流式聊天：SSE 增量转发，用户停止/断开即中止上游请求。

        - 发送前先校验并持久化用户消息（失败返回 400 JSON）；
        - 助手回复只在流完成后写入，停止/断开不写半截回复；
        - 重试永远是用户显式动作，不自动重复计费调用。
        """

        try:
            context = flow.chat_send_start(
                str(payload.get("message", "")),
                payload.get("links", []) or [],
            )
        except WorkbenchFlowError as exc:
            body = {"error": str(exc)}
            body.update(getattr(exc, "payload", {}) or {})
            _send_json(self, 400, body)
            return
        except (WorkbenchLLMError, CreativeChatError) as exc:
            _send_json(self, 400, {"error": str(exc)})
            return
        except Exception as exc:  # never kill the local server
            _send_json(self, 500, {"error": f"发送失败：{type(exc).__name__}，请重试"})
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()

            def send_event(obj) -> None:
                data = json.dumps(obj, ensure_ascii=False)
                self.wfile.write(("data: " + data + "\n\n").encode("utf-8"))
                self.wfile.flush()

            send_event({
                "type": "start",
                "session_id": context["session"].get("session_id", ""),
                "user_turn": context["user_turn"],
                "provider_kind": context.get("provider_kind", ""),
                "model": context["settings"].get("model", ""),
            })
            events = flow.chat_stream_reply(context)
            try:
                for event in events:
                    send_event(event)
            except WorkbenchFlowError as exc:
                send_event({"type": "error", "error": str(exc)})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # 用户停止或浏览器断开：中止上游请求，不写助手回复
                events.close()
                return
            except Exception as exc:  # never kill the local server mid-stream
                send_event({"type": "error", "error": f"流式输出中断：{type(exc).__name__}，请重试"})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def _handle_workbench_get_state(self) -> None:
        flow = self._workbench_flow()

        def _read():
            settings = flow.get_settings()
            session = flow.store.load_latest()
            view = flow.view(session["session_id"]) if session else None
            chat = flow.chat_state()
            return {"settings": settings, "session": view, **chat}

        result, error = self._workbench_call(_read)
        if error:
            _send_json(self, error[0], error[1])
            return
        _send_json(self, 200, result)

    def _handle_workbench_final_script(self) -> None:
        flow = self._workbench_flow()

        def _read():
            session = flow.store.load_latest()
            if not session:
                raise WorkbenchFlowError("还没有创作会话，请从输入选题开始")
            return flow.final_script(session["session_id"])

        result, error = self._workbench_call(_read)
        if error:
            _send_json(self, error[0], error[1])
            return
        _send_json(self, 200, result)

    def _handle_workbench_audio_artifact(self) -> None:
        """Serve only allow-listed, session-local delivery artifacts."""

        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query, keep_blank_values=True)
        session_values = query.get("session_id", [])
        kind_values = query.get("kind", [])
        allowed = {"markdown", "csv", "json", "manifest", "qa", "alignment", "subtitle"}
        if len(session_values) != 1 or len(kind_values) != 1 or kind_values[0] not in allowed:
            _send_json(self, 400, {"error": "工件请求参数无效"})
            return
        flow = self._workbench_flow()
        try:
            session_dir = flow.store.session_dir(session_values[0]).resolve()
            session = flow.store.load(session_values[0])
        except Exception:
            _send_json(self, 404, {"error": "会话或工件不存在"})
            return
        delivery = session.get("audio_delivery") or {}
        if delivery.get("status") != "delivered":
            _send_json(self, 404, {"error": "交付尚未通过 QA"})
            return
        raw_path = (delivery.get("paths") or {}).get(kind_values[0])
        if not raw_path:
            _send_json(self, 404, {"error": "工件尚未生成"})
            return
        try:
            candidate = Path(str(raw_path))
            if candidate.is_symlink():
                raise ValueError
            artifact = candidate.resolve(strict=True)
            artifact.relative_to(session_dir)
            if not artifact.is_file():
                raise ValueError
            size = artifact.stat().st_size
            if size > 64 * 1024 * 1024:
                raise ValueError
            body = artifact.read_bytes()
        except (OSError, ValueError):
            _send_json(self, 404, {"error": "工件不存在或不在本集交付目录内"})
            return
        content_type = mimetypes.guess_type(artifact.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Disposition", "attachment; filename=artifact")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_workbench_audio_source(self) -> None:
        """Stream the imported owner-local file for an optional local preview."""

        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query, keep_blank_values=True)
        values = query.get("session_id", [])
        if len(values) != 1 or not re.fullmatch(r"WBX-[0-9a-fA-F]{16}", values[0]):
            _send_json(self, 400, {"error": "音频预览参数无效"})
            return
        flow = self._workbench_flow()
        try:
            session_dir = flow.store.session_dir(values[0]).resolve()
            session = flow.store.load(values[0])
            raw_path = ((session.get("audio") or {}).get("path") or "")
            candidate = Path(str(raw_path))
            if candidate.is_symlink():
                raise ValueError
            media = candidate.resolve(strict=True)
            media.relative_to(session_dir)
            if not media.is_file() or len(media.relative_to(session_dir).parts) != 1:
                raise ValueError
            size = media.stat().st_size
            if size <= 0 or size > MAX_AUDIO_UPLOAD_BYTES:
                raise ValueError
        except (OSError, ValueError):
            _send_json(self, 404, {"error": "本集口播文件不存在"})
            return
        content_type = mimetypes.guess_type(media.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", "inline")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            with media.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    class _ExactBodyReader:
        """Bounded reader that rejects a short Content-Length body."""

        def __init__(self, raw, length: int):
            self.raw = raw
            self.remaining = length

        def read(self, size: int = -1) -> bytes:
            if self.remaining <= 0:
                return b""
            requested = self.remaining if size is None or size < 0 else min(size, self.remaining)
            chunk = self.raw.read(requested)
            if not chunk:
                raise WebUIRequestError("上传内容不完整")
            self.remaining -= len(chunk)
            return chunk

    def _handle_workbench_audio_import(self) -> None:
        """Accept one bounded binary upload without reflecting header values."""

        content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/octet-stream" and not (
            content_type.startswith("audio/") or content_type.startswith("video/")
        ):
            self.close_connection = True
            _send_json(self, 415, {"error": "音频导入必须使用二进制音频或视频 Content-Type"})
            return
        state = self._content_length_state(MAX_AUDIO_UPLOAD_BYTES)
        if state == "transfer_encoding":
            self.close_connection = True
            _send_json(self, 411, {"error": "不支持 Transfer-Encoding 上传"})
            return
        if state == "length_invalid":
            self.close_connection = True
            _send_json(self, 411, {"error": "上传必须提供单一有效 Content-Length"})
            return
        if state == "length_negative":
            self.close_connection = True
            _send_json(self, 400, {"error": "Content-Length 不能为负数"})
            return
        if state == "length_too_large":
            self.close_connection = True
            _send_json(self, 413, {"error": "音频上传超过本地上限"})
            return
        length = int((self.headers.get_all("Content-Length") or ["0"])[0].strip())
        session_id = (self.headers.get("X-Workbench-Session") or "").strip()
        filename = (self.headers.get("X-Workbench-Filename") or "").strip()
        origin = (self.headers.get("X-Workbench-Origin") or "").strip()
        if (
            not session_id
            or not re.fullmatch(r"WBX-[0-9a-fA-F]{16}", session_id)
            or not filename
            or not origin
        ):
            self.close_connection = True
            _send_json(self, 400, {"error": "音频导入缺少必要的会话、文件名或来源标记"})
            return
        flow = self._workbench_flow()
        reader = self._ExactBodyReader(self.rfile, length)
        server: "_DeepTalkWebUIServer" = self.server  # type: ignore[assignment]
        result, error = self._workbench_call(
            lambda: self._import_audio_with_lock(
                flow, server, session_id, filename, reader, origin
            )
        )
        if error:
            _send_json(self, error[0], error[1])
            return
        _send_json(self, 200, result)

    @staticmethod
    def _import_audio_with_lock(flow, server, session_id, filename, reader, origin):
        with server.workbench_lock:
            return flow.import_audio(session_id, filename, reader, origin)

    def _handle_workbench_post(self, path: str) -> None:
        flow = self._workbench_flow()
        payload = self._workbench_json_body(path)
        if payload is None:
            return
        server: "_DeepTalkWebUIServer" = self.server  # type: ignore[assignment"]
        session_id = str(payload.get("session_id", "") or "")
        if path == "/api/workbench/chat/stream":
            # 流式聊天走专用 SSE 响应，不走统一 JSON 尾部
            self._handle_chat_stream(flow, payload)
            return
        if path == "/api/workbench/chat/draft":
            result, error = self._workbench_call(flow.chat_draft_generate)
        elif path == "/api/workbench/chat/draft/edit":
            result, error = self._workbench_call(
                lambda: flow.chat_draft_save(str(payload.get("content", "")))
            )
        elif path == "/api/workbench/settings":
            result, error = self._workbench_call(lambda: flow.save_settings(payload))
        elif path == "/api/workbench/settings/test":
            result, error = self._workbench_call(flow.test_settings)
        elif path == "/api/workbench/session/start":
            def _start():
                discovery = self._run_discovery(
                    json.dumps(
                        {
                            "topic": payload.get("topic", ""),
                            "urls": payload.get("urls", []),
                        }
                    ).encode("utf-8")
                )
                if discovery is None:
                    raise WorkbenchFlowError("参考检索失败，无法开启本集创作")
                candidates = discovery.get("candidates", [])
                session = flow.store.create(
                    str(payload.get("topic", "")).strip() or "（未命名选题）",
                    candidates,
                    None,
                )
                # Return the same complete state shape as /state so the
                # browser's single renderer cannot blank a previously saved
                # masked API-key/settings view after creating a session.
                return {
                    "settings": flow.get_settings(),
                    "session": flow.view(session["session_id"]),
                }

            result, error = self._workbench_call(_start)
        elif path == "/api/workbench/references/acquire":
            def _acquire():
                with server.workbench_lock:
                    return flow.acquire_references(
                        session_id,
                        payload.get("bvids", []),
                        str(payload.get("authorization_text", "")),
                    )

            result, error = self._workbench_call(_acquire)
        elif path == "/api/workbench/references/analyze":
            def _analyze():
                with server.workbench_lock:
                    return flow.analyze_reference(session_id, str(payload.get("bvid", "")))

            result, error = self._workbench_call(_analyze)
        elif path == "/api/workbench/references/reanalyze":
            def _reanalyze():
                with server.workbench_lock:
                    return flow.reanalyze_reference(session_id, str(payload.get("bvid", "")))

            result, error = self._workbench_call(_reanalyze)
        elif path == "/api/workbench/sources/url":
            def _source_url():
                with server.workbench_lock:
                    return flow.add_source_url(session_id, payload.get("url", ""))

            result, error = self._workbench_call(_source_url)
        elif path == "/api/workbench/sources/text":
            def _source_text():
                with server.workbench_lock:
                    return flow.add_source_text(
                        session_id,
                        payload.get("title", ""),
                        payload.get("text", ""),
                        payload.get("url", ""),
                    )

            result, error = self._workbench_call(_source_text)
        elif path == "/api/workbench/research/search":
            def _deepseek_search():
                with server.workbench_lock:
                    return flow.search_deepseek(
                        session_id,
                        str(payload.get("query", "")),
                        opt_in=payload.get("opt_in") is True,
                        max_requests=payload.get("max_requests"),
                        count=payload.get("count", 5),
                        need_content=payload.get("need_content") is True,
                    )

            result, error = self._workbench_call(_deepseek_search)
        elif path == "/api/workbench/research/fetch":
            def _deepseek_fetch():
                with server.workbench_lock:
                    return flow.fetch_deepseek_source(
                        session_id,
                        str(payload.get("url", "")),
                        opt_in=payload.get("opt_in") is True,
                        max_requests=payload.get("max_requests"),
                    )

            result, error = self._workbench_call(_deepseek_fetch)
        elif path == "/api/workbench/research/generate":
            def _research():
                with server.workbench_lock:
                    return flow.generate_research(
                        session_id,
                        str(payload.get("research_question", "")),
                        allow_partial=bool(payload.get("partial_override")),
                        partial_reason=str(payload.get("partial_reason", ""))[:500],
                    )

            result, error = self._workbench_call(_research)
        elif path == "/api/workbench/fact-check/run":
            def _fact_check():
                with server.workbench_lock:
                    return flow.run_fact_check(session_id)

            result, error = self._workbench_call(_fact_check)
        elif path == "/api/workbench/research/approve":
            def _approve_research():
                with server.workbench_lock:
                    return flow.approve_research(
                        session_id, str(payload.get("confirmation", ""))
                    )

            result, error = self._workbench_call(_approve_research)
        elif path == "/api/workbench/thesis/generate":
            def _thesis_generate():
                with server.workbench_lock:
                    return flow.generate_thesis(session_id)

            result, error = self._workbench_call(_thesis_generate)
        elif path == "/api/workbench/thesis/review":
            def _thesis_review():
                with server.workbench_lock:
                    return flow.review_thesis(session_id)

            result, error = self._workbench_call(_thesis_review)
        elif path == "/api/workbench/thesis/approve":
            def _thesis_approve():
                with server.workbench_lock:
                    return flow.approve_thesis(
                        session_id, str(payload.get("confirmation", ""))
                    )

            result, error = self._workbench_call(_thesis_approve)
        elif path == "/api/workbench/script/generate":
            def _script():
                with server.workbench_lock:
                    return flow.generate_script(session_id)

            result, error = self._workbench_call(_script)
        elif path == "/api/workbench/audio/deliver":
            def _audio_deliver():
                with server.workbench_lock:
                    return flow.run_audio_delivery(session_id)

            result, error = self._workbench_call(_audio_deliver)
        else:
            _send_json(self, 404, {"error": "路径不存在"})
            return
        if error:
            _send_json(self, error[0], error[1])
            return
        _send_json(self, 200, result)

    # -- logging (redacted) ---------------------------------------------

    def log_message(self, fmt: str, *args) -> None:
        # default format already excludes bodies; additionally strip any
        # query string so URLs can never leak into logs
        safe_path = self.path.split("?", 1)[0]
        code = args[1] if len(args) >= 2 else ""
        print(f"[webui] {self.address_string()} {self.command} {safe_path} {code}")

    def log_error(self, fmt: str, *args) -> None:
        # never log request bodies or exception details that may embed input
        print(f"[webui] error: {fmt % args if args else fmt}")


class _DeepTalkWebUIServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address,
        *,
        output_dir: Path,
        provider_factory: Callable[[], object],
        flow,
    ):
        super().__init__(address, _DeepTalkWebUIHandler)
        self.output_dir = Path(output_dir)
        self.provider_factory = provider_factory
        self.discovery_lock = threading.Lock()
        self.workbench_lock = threading.Lock()
        self.flow = flow


def _default_repo_root() -> Path:
    """Repository root that owns the canonical engine trees (not the CWD)."""

    return Path(__file__).resolve().parents[2]


def make_server(
    port: int = 0,
    *,
    output_dir: Path,
    provider_factory: Callable[[], object],
    host: str = DEFAULT_HOST,
    flow=None,
) -> _DeepTalkWebUIServer:
    """Build the loopback server. ``port=0`` picks an ephemeral port (tests)."""

    if flow is None:
        from .workbench.flow import WorkbenchFlow

        flow = WorkbenchFlow(_default_repo_root())
    return _DeepTalkWebUIServer(
        (host, int(port)),
        output_dir=output_dir,
        provider_factory=provider_factory,
        flow=flow,
    )


def run_webui(
    port: int = DEFAULT_PORT,
    *,
    output_dir: Path,
    use_visitor_identity: bool = True,
) -> int:
    """Start the local Web UI and serve until interrupted."""

    def factory():
        return BilibiliReferenceProvider(use_visitor_identity=use_visitor_identity)

    server = make_server(port, output_dir=output_dir, provider_factory=factory)
    actual_port = server.server_address[1]
    mode = "匿名访客模式" if use_visitor_identity else "已禁用访客标识（--no-visitor-identity）"
    print(f"DeepTalk 参考视频工作台：http://{DEFAULT_HOST}:{actual_port}/")
    print(f"访问模式：{mode}；产物目录：{Path(output_dir).resolve()}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
    return 0
