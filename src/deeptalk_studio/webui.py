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
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Optional

from .bilibili_reference_provider import BilibiliReferenceProvider
from .reference_discovery import (
    ReferenceDiscoveryError,
    build_reference_candidate_set,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8321
MAX_REQUEST_BYTES = 8192
MAX_TOPIC_CHARS = 200
MAX_URL_COUNT = 5
MAX_URL_CHARS = 300
SOCKET_TIMEOUT_SECONDS = 10

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

    def _content_length_state(self) -> str:
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
        if length > MAX_REQUEST_BYTES:
            return "length_too_large"
        return "ok"

    def _read_body(self) -> Optional[bytes]:
        """Read exactly Content-Length bytes; None means the request was rejected."""

        state = self._content_length_state()
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
            _send_json(self, 413, {"error": f"请求体超过 {MAX_REQUEST_BYTES} 字节上限"})
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
        if path == "/":
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
        _send_json(self, 404, {"error": "路径不存在"})

    def do_POST(self) -> None:
        rejection = self._boundary_rejection()
        if rejection:
            self.close_connection = True
            _send_json(self, 403, {"error": rejection})
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/discover":
            _send_json(self, 404, {"error": "路径不存在"})
            return
        rejection = self._content_type_rejection()
        if rejection:
            self.close_connection = True
            _send_json(self, 415, {"error": rejection})
            return
        raw = self._read_body()
        if raw is None:
            return
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            _send_json(self, 400, {"error": "请求体不是合法 JSON"})
            return
        try:
            request = validate_discover_payload(payload)
        except WebUIRequestError as exc:
            _send_json(self, 400, {"error": str(exc)})
            return
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
            return
        except ReferenceDiscoveryError as exc:
            _send_json(self, 400, {"error": f"参考视频发现失败：{exc}"})
            return
        except Exception as exc:  # provider/IO crash must not kill the server
            self.log_error("discovery run failed: %s", type(exc).__name__)
            _send_json(self, 500, {"error": "本次检索执行失败，请稍后重试"})
            return
        _send_json(self, 200, artifact)

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
    ):
        super().__init__(address, _DeepTalkWebUIHandler)
        self.output_dir = Path(output_dir)
        self.provider_factory = provider_factory
        self.discovery_lock = threading.Lock()


def make_server(
    port: int = 0,
    *,
    output_dir: Path,
    provider_factory: Callable[[], object],
    host: str = DEFAULT_HOST,
) -> _DeepTalkWebUIServer:
    """Build the loopback server. ``port=0`` picks an ephemeral port (tests)."""

    return _DeepTalkWebUIServer(
        (host, int(port)),
        output_dir=output_dir,
        provider_factory=provider_factory,
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
