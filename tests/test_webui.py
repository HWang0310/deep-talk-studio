"""Deterministic offline tests for the Phase 1B Mac-local Web UI (Issue #26).

All provider interaction is faked via injected providers; no test touches
the real Bilibili network. The HTTP server runs on an ephemeral loopback
port exactly like production (127.0.0.1 only).
"""

import json
import socket
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from deeptalk_studio.webui import (
    DEFAULT_HOST,
    ArtifactWriteConflict,
    WebUIRequestError,
    _persist_artifact,
    make_server,
    validate_discover_payload,
)
from tests.test_reference_discovery import (
    MOSCOW_TOPIC,
    FakeProvider,
    SearchOutcome,
    ok_search,
    search_item,
)


class LocalWebUITestCase(unittest.TestCase):
    """Starts a real loopback server per test with an injected fake provider."""

    def start_server(self, provider=None, flow=None):
        provider = provider or FakeProvider(
            default_search=ok_search(
                search_item("BV1hi000000A", "莫斯科大学留学生旭日旗事件进展", views=900),
                search_item("BV1hi000000B", "莫斯科大学留学生旭日旗事件回应", views=500),
            )
        )
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.provider = provider
        server = make_server(
            0,
            output_dir=Path(tmp.name),
            provider_factory=lambda: provider,
            flow=flow,
        )
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.base = f"http://{DEFAULT_HOST}:{server.server_address[1]}"
        self.server = server
        self.output_dir = Path(tmp.name)

    def get(self, path, raw=False):
        request = urllib.request.Request(self.base + path)
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers), body

    def post(self, path, payload, *, json_body=None, content_length=None):
        body = (
            json.dumps(payload).encode("utf-8")
            if json_body is None else json_body
        )
        request = urllib.request.Request(
            self.base + path, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                text = response.read().decode("utf-8")
                return response.status, dict(response.headers), text
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8")
            return exc.code, dict(exc.headers), text

    def raw(self, payload: bytes, *, timeout: float = 6.0) -> bytes:
        """Send a raw HTTP request over a fresh socket with a hard deadline.

        A hung server (the bug these tests guard against) fails the test
        either by socket timeout (empty response) or by never reaching EOF.
        """

        port = self.server.server_address[1]
        with socket.create_connection((DEFAULT_HOST, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(payload)
            chunks = []
            try:
                while True:
                    part = sock.recv(65536)
                    if not part:
                        break
                    chunks.append(part)
            except socket.timeout:
                pass
            except ConnectionResetError:
                # server rejected the request and closed with unread data in
                # flight — exactly the intended fail-closed behavior
                pass
            return b"".join(chunks)

    @staticmethod
    def status_of(response: bytes) -> int:
        first = response.split(b"\r\n", 1)[0]
        return int(first.split(b" ")[1])

    def no_discovery_ran(self):
        self.assertEqual(self.provider.search_calls, [])
        self.assertEqual(list(self.output_dir.glob("reference-candidate-set-*.json")), [])


# ---------------------------------------------------------------------------
# payload validation (pure, offline)
# ---------------------------------------------------------------------------


class ValidatePayloadTests(unittest.TestCase):
    def test_valid_minimal(self):
        result = validate_discover_payload({"topic": "  某主题  ", "urls": []})
        self.assertEqual(result, {"topic": "某主题", "urls": []})

    def test_urls_optional(self):
        result = validate_discover_payload({"topic": "某主题"})
        self.assertEqual(result["urls"], [])

    def test_urls_trimmed_and_kept(self):
        result = validate_discover_payload(
            {"topic": "某主题", "urls": ["  BV1SvJd6sEEZ  ", "https://www.bilibili.com/video/BV1waJi6dEXe/"]}
        )
        self.assertEqual(result["urls"], ["BV1SvJd6sEEZ", "https://www.bilibili.com/video/BV1waJi6dEXe/"])

    def test_rejects_non_object(self):
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload(["topic"])
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload("话题")

    def test_rejects_unknown_fields(self):
        with self.assertRaisesRegex(WebUIRequestError, "topic 与 urls"):
            validate_discover_payload({"topic": "x", "aliases": ["y"]})

    def test_rejects_bad_topic(self):
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": 123})
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "   "})
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "长" * 201})
        self.assertTrue(validate_discover_payload({"topic": "长" * 200}))

    def test_rejects_bad_urls(self):
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "x", "urls": "BV1SvJd6sEEZ"})
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "x", "urls": [f"BV{i}" for i in range(6)]})
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "x", "urls": [None]})
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "x", "urls": ["  "]})
        with self.assertRaises(WebUIRequestError):
            validate_discover_payload({"topic": "x", "urls": ["h" * 301]})


# ---------------------------------------------------------------------------
# static pages & hardening
# ---------------------------------------------------------------------------


class StaticPageTests(LocalWebUITestCase):
    def setUp(self):
        self.start_server()

    def test_server_binds_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_index_served_with_chinese_ui_and_nosniff(self):
        status, headers, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("text/html"))
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn('lang="zh-CN"', body)
        self.assertIn('id="topic"', body)
        # Issue #23 unified workbench: the page drives the same canonical
        # discovery service through the session-start endpoint
        self.assertIn("/api/workbench/session/start", body)
        # XSS-safety: the page must never use innerHTML for rendering
        self.assertNotIn("innerHTML", body)
        self.assertIn("textContent", body)

    def test_index_ui_trial_progress_and_staleness_contract(self):
        """Issue #29 UI-trial invariants: slow-action feedback must keep an
        elapsed timer with a do-not-resubmit reassurance, previous sections
        are dimmed while a new operation runs (stale class), and the busy
        interval is always cleared when the operation finishes."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        # live elapsed timer + expected-duration reassurance during operation
        self.assertIn("已用", body)
        self.assertIn("请勿重复提交", body)
        # title switches to in-progress and is restored from a saved base title
        self.assertIn("处理中…", body)
        self.assertIn("baseTitle", body)
        # previous result card is dimmed while a new operation is in flight
        self.assertIn("#result.stale", body)
        self.assertIn("classList.add('stale')", body)
        self.assertIn("classList.remove('stale')", body)
        # the busy interval must be cleared on completion (no leaking timers)
        self.assertIn("clearInterval(busyTimer)", body)

    def test_index_ui_trial_responsive_layout_contract(self):
        """Issue #29 UI-trial responsive invariants: on narrow screens the
        reference-link input wraps to a full row with a tappable remove
        button, and the search button spans the full width."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("@media (max-width: 600px)", body)
        self.assertIn(".ref-row { flex-wrap: wrap; }", body)
        self.assertIn("min-height: 40px", body)
        self.assertIn("#search-btn { width: 100%; }", body)

    def test_index_exposes_deepseek_preset_and_truthful_connection_indicator(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn('value="deepseek"', body)
        self.assertIn("api.deepseek.com", body)
        self.assertIn("connection_kind", body)
        self.assertIn("真实连接", body)
        self.assertIn("清除 API Key", body)

    def test_index_exposes_explicit_deepseek_search_budget_controls(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("/api/workbench/research/search", body)
        self.assertIn("/api/workbench/research/fetch", body)
        self.assertIn("可能产生计费", body)
        self.assertIn("搜索结果不是事实证据", body)

    def test_healthz(self):
        status, headers, body = self.get("/healthz")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertTrue(payload["ok"])

    def test_unknown_path_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/no-such-path")
        self.assertEqual(ctx.exception.code, 404)

    def test_no_arbitrary_fetch_or_proxy_endpoint(self):
        # only / and /healthz and /api/discover exist; a POST to any other
        # path must be 404, never forwarded anywhere
        status, _, body = self.post("/api/proxy", {"url": "https://example.com"})
        self.assertEqual(status, 404)


class DiscoverEndpointTests(LocalWebUITestCase):
    def setUp(self):
        self.start_server()

    def test_successful_run_returns_artifact_json(self):
        status, headers, body = self.post("/api/discover", {"topic": MOSCOW_TOPIC, "urls": []})
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("application/json"))
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        artifact = json.loads(body)
        self.assertEqual(artifact["artifact_version"], "1")
        self.assertEqual(artifact["status"], "ok")
        self.assertEqual(
            [c["bvid"] for c in artifact["candidates"]],
            ["BV1hi000000A", "BV1hi000000B"],
        )
        self.assertIn("coverage_note", artifact["search"])

    def test_user_supplied_reference_ranks_first(self):
        provider = FakeProvider(
            default_search=ok_search(
                search_item("BV1hi000000A", "莫斯科大学留学生旭日旗事件进展", views=900),
            )
        )
        self.start_server(provider=provider)
        status, _, body = self.post(
            "/api/discover",
            {"topic": MOSCOW_TOPIC, "urls": ["https://www.bilibili.com/video/BV1SvJd6sEEZ/?spm=x"]},
        )
        self.assertEqual(status, 200)
        artifact = json.loads(body)
        self.assertTrue(artifact["candidates"][0]["user_supplied"])
        self.assertEqual(artifact["candidates"][0]["bvid"], "BV1SvJd6sEEZ")
        # privacy: the stored/served form never carries the query parameter
        self.assertEqual(
            artifact["user_supplied_urls"],
            ["https://www.bilibili.com/video/BV1SvJd6sEEZ"],
        )

    def test_artifact_persisted_with_unique_names(self):
        status, _, _ = self.post("/api/discover", {"topic": MOSCOW_TOPIC, "urls": []})
        self.assertEqual(status, 200)
        status2, _, _ = self.post("/api/discover", {"topic": MOSCOW_TOPIC, "urls": []})
        self.assertEqual(status2, 200)
        written = sorted(self.output_dir.glob("reference-candidate-set-REF-*.json"))
        self.assertEqual(len(written), 2)
        for path in written:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_version"], "1")

    def test_blocked_provider_returns_honest_blocked_artifact(self):
        provider = FakeProvider(
            default_search=SearchOutcome(
                status="blocked", items=(), http_status=412, api_code=None, message=""
            )
        )
        self.start_server(provider=provider)
        status, _, body = self.post("/api/discover", {"topic": MOSCOW_TOPIC, "urls": []})
        self.assertEqual(status, 200)  # honest state, not an HTTP error
        artifact = json.loads(body)
        self.assertEqual(artifact["status"], "blocked")
        self.assertEqual(artifact["candidates"], [])
        self.assertIn("--url", artifact["action_note"])

    def test_xss_topic_round_trips_as_json_only(self):
        evil = "<script>alert('xss')</script>"
        status, headers, body = self.post(
            "/api/discover", {"topic": f"{evil}事件", "urls": []}
        )
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("application/json"))
        artifact = json.loads(body)
        self.assertIn(evil, artifact["topic"])

    def test_provider_crash_keeps_server_alive_with_500(self):
        class ExplodingProvider(FakeProvider):
            def search_videos(self, query, page=1):
                raise RuntimeError("boom")

        self.start_server(provider=ExplodingProvider())
        status, _, body = self.post("/api/discover", {"topic": MOSCOW_TOPIC, "urls": []})
        self.assertEqual(status, 500)
        self.assertIn("error", json.loads(body))
        # server recovers for the next request
        status, _, body = self.get("/healthz")
        self.assertEqual(status, 200)


class DiscoverValidationOverHttpTests(LocalWebUITestCase):
    def setUp(self):
        self.start_server()

    def _expect_400(self, payload, fragment=""):
        status, _, body = self.post("/api/discover", payload)
        self.assertEqual(status, 400)
        error = json.loads(body)["error"]
        self.assertIn(fragment, error)

    def test_empty_topic(self):
        self._expect_400({"topic": "   ", "urls": []}, "主题")

    def test_topic_too_long(self):
        self._expect_400({"topic": "长" * 201, "urls": []}, "200")

    def test_six_urls(self):
        self._expect_400(
            {"topic": "x", "urls": [f"BV{i}" for i in range(6)]}, "5"
        )

    def test_url_too_long(self):
        self._expect_400({"topic": "x", "urls": ["h" * 301]}, "300")

    def test_malformed_json(self):
        status, _, body = self.post("/api/discover", None, json_body=b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_json_array_body(self):
        status, _, body = self.post("/api/discover", None, json_body=b"[1,2]")
        self.assertEqual(status, 400)

    def test_oversized_body_rejected(self):
        status, _, body = self.post(
            "/api/discover", None,
            json_body=("x" * 9000).encode("utf-8"),
        )
        self.assertEqual(status, 413)

    def test_unknown_field(self):
        self._expect_400({"topic": "x", "urls": [], "evil": 1}, "topic 与 urls")


# ---------------------------------------------------------------------------
# Blocking 1 — loopback Host / Origin / Content-Type boundaries (raw sockets)
# ---------------------------------------------------------------------------


class HttpBoundaryTests(LocalWebUITestCase):
    """The JSON API must be unreachable from cross-site browser contexts:
    narrow Host allowlist, same-origin Origin (incl. ``null``), JSON-only
    Content-Type. Rejections happen before body read and before the
    discovery service is touched."""

    def setUp(self):
        self.start_server()

    def _request(
        self, *, method=b"POST", path=b"/api/discover", host=None, origin=None,
        content_type=b"application/json", body=b"{}",
    ):
        port = self.server.server_address[1]
        host = host if host is not None else f"127.0.0.1:{port}".encode()
        lines = [f"{method.decode()} {path.decode()} HTTP/1.1", f"Host: {host.decode()}"]
        if origin is not None:
            lines.append(f"Origin: {origin}")
        if content_type is not None:
            lines.append(f"Content-Type: {content_type.decode()}")
        if body is not None:
            lines.append(f"Content-Length: {len(body)}")
        lines.append("Connection: close")
        head = ("\r\n".join(lines) + "\r\n\r\n").encode()
        return self.raw(head + body)

    def test_same_origin_post_succeeds(self):
        port = self.server.server_address[1]
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(origin=f"http://127.0.0.1:{port}", body=body)
        self.assertEqual(self.status_of(response), 200)
        self.assertTrue(self.provider.search_calls)

    def test_localhost_host_and_origin_succeed(self):
        port = self.server.server_address[1]
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(
            host=f"localhost:{port}".encode(),
            origin=f"http://localhost:{port}",
            body=body,
        )
        self.assertEqual(self.status_of(response), 200)

    def test_cross_site_origin_rejected(self):
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(origin="https://evil.example", body=body)
        self.assertEqual(self.status_of(response), 403)
        self.assertIn("error", json.loads(response.split(b"\r\n\r\n", 1)[1]))
        self.no_discovery_ran()

    def test_null_origin_rejected(self):
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(origin="null", body=body)
        self.assertEqual(self.status_of(response), 403)
        self.no_discovery_ran()

    def test_malicious_host_rejected_on_post(self):
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(host=b"evil.example:8321", origin=None, body=body)
        self.assertEqual(self.status_of(response), 403)
        self.no_discovery_ran()

    def test_malicious_host_rejected_on_get(self):
        response = self._request(
            method=b"GET", path=b"/", host=b"rebound.example", content_type=None, body=b"",
        )
        self.assertEqual(self.status_of(response), 403)
        # the page body itself must not be served to a rebound host
        self.assertNotIn(b"<html", response)
        self.assertNotIn(b"text/html", response)

    def test_text_plain_json_body_rejected(self):
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(content_type=b"text/plain", body=body)
        self.assertEqual(self.status_of(response), 415)
        self.no_discovery_ran()

    def test_rejection_never_echoes_headers(self):
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._request(
            host=b"evil.example", origin="https://evil.example", body=body
        )
        self.assertNotIn(b"evil.example", response)


# ---------------------------------------------------------------------------
# Blocking 2 — Content-Length framing hardening (raw sockets, no hangs)
# ---------------------------------------------------------------------------


class ContentLengthHardeningTests(LocalWebUITestCase):
    def setUp(self):
        self.start_server()

    def _post_with_headers(self, extra_headers: str, body: bytes = b"") -> bytes:
        port = self.server.server_address[1]
        head = (
            "POST /api/discover HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            f"Content-Type: application/json\r\n"
            f"{extra_headers}"
            "Connection: close\r\n\r\n"
        ).encode()
        return self.raw(head + body)

    def test_missing_content_length_rejected_without_hang(self):
        response = self._post_with_headers("")
        self.assertEqual(self.status_of(response), 411)

    def test_non_numeric_content_length_rejected(self):
        response = self._post_with_headers("Content-Length: abc\r\n", b"{}")
        self.assertEqual(self.status_of(response), 411)

    def test_negative_content_length_rejected_without_blocking_read(self):
        # previously read(-1) would block waiting for EOF on keep-alive
        response = self._post_with_headers("Content-Length: -1\r\n", b"{}")
        self.assertEqual(self.status_of(response), 400)
        self.no_discovery_ran()

    def test_duplicate_conflicting_content_length_rejected(self):
        response = self._post_with_headers(
            "Content-Length: 2\r\nContent-Length: 9000\r\n", b"{}"
        )
        self.assertEqual(self.status_of(response), 411)

    def test_transfer_encoding_chunked_rejected_and_closed(self):
        response = self._post_with_headers("Transfer-Encoding: chunked\r\n", b"0\r\n\r\n")
        self.assertEqual(self.status_of(response), 411)
        self.no_discovery_ran()

    def test_oversized_content_length_rejected_fast(self):
        response = self._post_with_headers(
            f"Content-Length: {8192 + 1}\r\n", b"x" * (8192 + 1)
        )
        self.assertEqual(self.status_of(response), 413)
        self.no_discovery_ran()

    def test_normal_content_length_still_works(self):
        body = json.dumps({"topic": MOSCOW_TOPIC, "urls": []}).encode()
        response = self._post_with_headers(f"Content-Length: {len(body)}\r\n", body)
        self.assertEqual(self.status_of(response), 200)
        self.assertTrue(self.provider.search_calls)


# ---------------------------------------------------------------------------
# Blocking 3 — artifact exclusivity (never overwrite)
# ---------------------------------------------------------------------------


class ArtifactExclusivityTests(LocalWebUITestCase):
    def setUp(self):
        self.start_server()

    def test_persist_helper_refuses_to_overwrite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "reference-candidate-set-REF-conflict00.json"
            target.write_bytes(b"SENTINEL")
            with self.assertRaises(ArtifactWriteConflict):
                _persist_artifact(Path(tmp), {"candidate_set_id": "REF-conflict00"})
            self.assertEqual(target.read_bytes(), b"SENTINEL")

    def test_same_candidate_id_never_overwrites_on_server(self):
        """Two runs forced to produce the same candidate_set_id: the second
        persistence must fail loudly without touching the first artifact."""

        fake_uuid = mock.Mock()
        fake_uuid.hex = "deadbeefcafe"
        with mock.patch(
            "deeptalk_studio.reference_discovery.uuid.uuid4", return_value=fake_uuid
        ):
            status1, _, body1 = self.post("/api/discover", {"topic": MOSCOW_TOPIC})
            status2, _, body2 = self.post("/api/discover", {"topic": MOSCOW_TOPIC})
        self.assertEqual(status1, 200)
        self.assertEqual(status2, 500)
        self.assertIn("未覆盖", json.loads(body2)["error"])
        written = list(self.output_dir.glob("reference-candidate-set-*.json"))
        self.assertEqual(len(written), 1)
        persisted = json.loads(written[0].read_text(encoding="utf-8"))
        self.assertEqual(persisted, json.loads(body1))

    def test_unique_runs_keep_persisting_normally(self):
        status1, _, _ = self.post("/api/discover", {"topic": MOSCOW_TOPIC})
        status2, _, _ = self.post("/api/discover", {"topic": MOSCOW_TOPIC})
        self.assertEqual((status1, status2), (200, 200))
        self.assertEqual(len(list(self.output_dir.glob("reference-candidate-set-*.json"))), 2)


if __name__ == "__main__":
    unittest.main()


class WorkbenchRoutesTests(LocalWebUITestCase):
    """Issue #23 unified workbench HTTP surface (fake LLM + fake fetch)."""

    def _flow(self, root: Path, deepseek_client=None):
        from tests.test_workbench import (
            FakeWorkbenchLLM,
            _fake_discovery,
            _fake_fetcher,
        )

        from deeptalk_studio.workbench.flow import WorkbenchFlow

        kwargs = {}
        if deepseek_client is not None:
            kwargs["deepseek_client_factory"] = lambda settings: deepseek_client
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery,
            provider_factory=lambda settings: FakeWorkbenchLLM(settings),
            fetcher=_fake_fetcher,
            **kwargs,
        )

    def test_deepseek_search_and_fetch_routes_require_opt_in_and_persist_budget(self):
        import tempfile

        class Client:
            def __init__(self):
                self.calls = []

            def search(self, query, count=5, need_content=False):
                self.calls.append(("search", query))
                return {"request_id": "web-search", "results": [{
                    "title": "公告", "url": "https://example.gov/notice",
                    "content": "摘要", "published_at": "2026-10-21",
                }]}

            def fetch(self, url):
                self.calls.append(("fetch", url))
                return {"request_id": "web-fetch", "url": url, "title": "公告",
                        "content": "这是一段可核验的公告正文，足以作为测试来源。",
                        "published_at": "2026-10-21"}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            client = Client()
            flow = self._flow(root, client)
            self.start_server(flow=flow)
            status, _, _ = self.post("/api/workbench/settings", {
                "provider_mode": "deepseek", "api_key": "sk-http-fixture",
            })
            self.assertEqual(status, 200)
            status, _, body = self.post("/api/workbench/session/start", {
                "topic": "本市图书馆夜间开放试点", "urls": [],
            })
            self.assertEqual(status, 200, body)
            sid = json.loads(body)["session"]["session_id"]
            status, _, body = self.post("/api/workbench/research/search", {
                "session_id": sid, "query": "预算", "opt_in": False,
                "max_requests": 2,
            })
            self.assertEqual(status, 400)
            self.assertIn("明确勾选", json.loads(body)["error"])
            self.assertEqual(client.calls, [])
            status, _, body = self.post("/api/workbench/research/search", {
                "session_id": sid, "query": "预算", "opt_in": True,
                "max_requests": 2, "count": 3, "need_content": True,
            })
            self.assertEqual(status, 200, body)
            searched = json.loads(body)
            self.assertEqual(searched["search_budget"]["used"], 1)
            status, _, body = self.post("/api/workbench/research/fetch", {
                "session_id": sid, "url": "https://example.gov/notice",
                "opt_in": True, "max_requests": 2,
            })
            self.assertEqual(status, 200, body)
            fetched = json.loads(body)
            self.assertEqual(fetched["kind"], "deepseek_fetched")
            self.assertEqual(fetched["search_budget"]["used"], 2)
            status, _, body = self._get_state()
            self.assertEqual(status, 200)
            state = json.loads(body)["session"]
            self.assertEqual(state["search_budget"]["used"], 2)
            self.assertEqual(state["sources"][0]["kind"], "deepseek_fetched")

    def test_settings_roundtrip_over_http_and_masked_echo(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.start_server(flow=self._flow(root))
            status, _, body = self.post("/api/workbench/settings", {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "test-model",
                "api_key": "sk-aaaaaaaaaaaaaaaaaaaaaaaa",
                "downloads_dir": str(root),
            })
            self.assertEqual(status, 200)
            payload = json.loads(body)
            self.assertNotIn("sk-aaaaaaaaaaaaaaaaaaaaaaaa", body)
            self.assertIn("…", payload["api_key_masked"])
            self.assertTrue(payload["configured"])
            status, _, body = self.get("/api/workbench/state?" ) if False else (0, None, None)
            # (state GET covered by the full-loop test below)

    def test_workbench_unknown_route_is_404_and_settings_test_requires_config(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.start_server(flow=self._flow(root))
            status, _, _ = self.post("/api/workbench/no-such-step", {})
            self.assertEqual(status, 404)
            status, _, body = self.post("/api/workbench/settings/test", {})
            self.assertEqual(status, 400)
            self.assertIn("设置尚未完成", json.loads(body)["error"])

    def test_full_creation_loop_over_http_local_user_path(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            library_provider = FakeProvider(
                default_search=ok_search(
                    search_item("BV1li000000A", "本市图书馆夜间开放试点来了 夜间阅览室", views=900),
                    search_item("BV1li000000B", "本市图书馆夜间开放至二十三点 有回应", views=500),
                )
            )
            self.start_server(provider=library_provider, flow=self._flow(root))
            # settings (chat mode against the scripted provider)
            status, _, body = self.post("/api/workbench/settings", {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "test-model",
                "api_key": "sk-test",
                "downloads_dir": str(root),
            })
            self.assertEqual(status, 200, body)
            # state
            status, _, body = self._get_state()
            self.assertEqual(status, 200)
            self.assertIsNone(json.loads(body)["session"])
            # session start (discovery through the injected fake provider) —
            # topic must be topical-consistent with the scripted fixtures
            # (Issue #23 B1 guards off-topic output fail-closed)
            status, _, body = self.post("/api/workbench/session/start", {
                "topic": "本市图书馆夜间开放试点",
                "urls": [],
            })
            self.assertEqual(status, 200, body)
            session = json.loads(body)
            sid = session["session"]["session_id"]
            self.assertGreaterEqual(len(session["session"]["references"]), 1)
            # pasted research source (fetcher rejects generic urls in fixture)
            status, _, body = self.post("/api/workbench/sources/text", {
                "session_id": sid,
                "title": "示例新闻社：图书馆明年起夜间开放",
                "text": (
                    "示例新闻社2026年10月20日报道，该市图书馆宣布自明年起将开放夜间阅览室，"
                    "每周三和周五延长开放至二十三点，首年预算大约为一百二十万元。"
                    "馆长说明夜间开放主要是为了服务备考学生和加班人群，馆方将与志愿者组织合作安排值班。"
                ),
                "url": "https://example.com/news/night-library",
            })
            self.assertEqual(status, 200, body)
            status, _, body = self.post("/api/workbench/sources/text", {
                "session_id": sid,
                "title": "市财政局：2027年度公共文化支出预算说明",
                "text": (
                    "市财政局官网2026年10月21日发布预算说明，2027年度公共文化支出拟增长百分之八，"
                    "其中图书馆系统新增夜间开放专项经费一百二十万元，用于安保、照明与志愿服务补贴。"
                    "说明同时指出，该专项经费为试点性质，有效期一年，期满后由市图书馆提交评估报告再定去留。"
                ),
                "url": "https://example.gov.cn/budget/2027-culture",
            })
            self.assertEqual(status, 200, body)
            # research draft → fact check → approval
            status, _, body = self.post("/api/workbench/research/generate", {
                "session_id": sid, "research_question": "钱怎么花？",
            })
            self.assertEqual(status, 200, body)
            self.assertIn("fact_check_pending", body)
            status, _, body = self.post("/api/workbench/fact-check/run", {"session_id": sid})
            self.assertEqual(status, 200, body)
            fc = json.loads(body)
            self.assertEqual(fc["gate_status"], "pass", body)
            status, _, body = self.post("/api/workbench/research/approve", {
                "session_id": sid, "confirmation": "我确认研究结论，批准进入写稿。",
            })
            self.assertEqual(status, 200, body)
            self.assertTrue(json.loads(body)["ready_for_script"])
            # thesis → review → approve
            status, _, body = self.post("/api/workbench/thesis/generate", {"session_id": sid})
            self.assertEqual(status, 200, body)
            status, _, body = self.post("/api/workbench/thesis/review", {"session_id": sid})
            self.assertEqual(status, 200, body)
            self.assertEqual(json.loads(body)["gate_decision"], "pass", body)
            status, _, body = self.post("/api/workbench/thesis/approve", {
                "session_id": sid,
                "confirmation": "我确认本期内容方向与选题卡一致，确认进入写稿。",
            })
            self.assertEqual(status, 200, body)
            # script + review + final
            status, _, body = self.post("/api/workbench/script/generate", {"session_id": sid})
            self.assertEqual(status, 200, body)
            script = json.loads(body)
            self.assertEqual(script["status"], "reviewed", body)
            status, _, body = self._get_final()
            self.assertEqual(status, 200)
            final = json.loads(body)
            self.assertIn("夜间图书馆", final["teleprompter_text"])

    def _get_state(self):
        return self._get_json("/api/workbench/state")

    def _get_final(self):
        return self._get_json("/api/workbench/script/final")

    def test_topic_mismatch_research_rejected_over_http(self):
        """Issue #23 B1 (observed E2E mismatch): Moscow session topic +
        library-themed scripted payload → research generation must 400 with
        the typed mismatch error, nothing saved."""
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            library_provider = FakeProvider(
                default_search=ok_search(
                    search_item("BV1li000000A", "本市图书馆夜间开放试点来了 夜间阅览室", views=900),
                )
            )
            self.start_server(provider=library_provider, flow=self._flow(root))
            self.post("/api/workbench/settings", {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "test-model",
                "api_key": "sk-test",
                "downloads_dir": str(root),
            })
            status, _, body = self.post("/api/workbench/session/start", {
                "topic": "莫斯科大学留学生旭日旗事件", "urls": [],
            })
            self.assertEqual(status, 200, body)
            sid = json.loads(body)["session"]["session_id"]
            self.post("/api/workbench/sources/text", {
                "session_id": sid,
                "title": "示例新闻社：图书馆夜间开放",
                "text": (
                    "示例新闻社2026年10月20日报道，该市图书馆宣布自明年起将开放夜间阅览室，"
                    "每周三和周五延长开放至二十三点，首年预算大约为一百二十万元。"
                ),
                "url": "https://example.com/news/night-library",
            })
            self.post("/api/workbench/sources/text", {
                "session_id": sid,
                "title": "市财政局预算说明",
                "text": (
                    "市财政局官网2026年10月21日发布预算说明，2027年度公共文化支出拟增长百分之八，"
                    "其中图书馆系统新增夜间开放专项经费一百二十万元。说明同时指出该专项经费为试点性质。"
                ),
                "url": "https://example.gov.cn/budget/2027-culture",
            })
            status, _, body = self.post("/api/workbench/research/generate", {
                "session_id": sid, "research_question": "",
            })
            self.assertEqual(status, 400, body)
            self.assertIn("选题主题明显不符", json.loads(body)["error"])
            # nothing was saved — the mismatch negative regression is complete
            status, _, body = self._get_state()
            research = json.loads(body)["session"]["research"]
            self.assertEqual(research["status"], "not_started")
            self.assertFalse(research["draft_path"])

    def test_partial_analysis_override_plumbing_over_http(self):
        """Issue #23 B3: with a downloaded-but-unanalyzed reference, research
        without the override is a typed 400; with explicit override + reason
        the server records the honest partial comparison."""
        import tempfile

        from tests.test_workbench import _fake_discovery

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.start_server(flow=self._flow(root))
            flow = self.server.flow
            # seed a session directly through the real store (test fixture)
            session = flow.store.create(
                "本市图书馆夜间开放试点",
                _fake_discovery("本市图书馆夜间开放试点", [])["candidates"],
                None,
            )
            sid = session["session_id"]

            def _mark(state):
                for bvid in ("BV1test1", "BV1test2"):
                    state["references"].setdefault(bvid, {})
                    state["references"][bvid]["status"] = (
                        "analyzed" if bvid == "BV1test1" else "downloaded"
                    )
                    state["references"][bvid]["media_path"] = "/tmp/fake.mp4"

            flow.store.update(sid, _mark)
            self.post("/api/workbench/settings", {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "test-model",
                "api_key": "sk-test",
                "downloads_dir": str(root),
            })
            self.post("/api/workbench/sources/text", {
                "session_id": sid,
                "title": "示例新闻社：图书馆夜间开放",
                "text": (
                    "示例新闻社2026年10月20日报道，该市图书馆宣布自明年起将开放夜间阅览室，"
                    "每周三和周五延长开放至二十三点，首年预算大约为一百二十万元。"
                    "馆长说明夜间开放主要是为了服务备考学生和加班人群，馆方将与志愿者组织合作安排值班。"
                ),
                "url": "https://example.com/news/night-library",
            })
            self.post("/api/workbench/sources/text", {
                "session_id": sid,
                "title": "市财政局预算说明",
                "text": (
                    "市财政局官网2026年10月21日发布预算说明，2027年度公共文化支出拟增长百分之八，"
                    "其中图书馆系统新增夜间开放专项经费一百二十万元，用于安保、照明与志愿服务补贴。"
                    "说明同时指出，该专项经费为试点性质，有效期一年，期满后由市图书馆提交评估报告再定去留。"
                ),
                "url": "https://example.gov.cn/budget/2027-culture",
            })
            status, _, body = self.post("/api/workbench/research/generate", {
                "session_id": sid, "research_question": "",
            })
            self.assertEqual(status, 400, body)
            self.assertIn("参考分析尚未完成", json.loads(body)["error"])
            self.assertIn("1/2", json.loads(body)["error"])

            status, _, body = self.post("/api/workbench/research/generate", {
                "session_id": sid,
                "research_question": "",
                "partial_override": True,
                "partial_reason": "本地转写耗时过长，先基于已完成的 1 条参考继续研究",
            })
            self.assertEqual(status, 200, body)
            comparison = json.loads(body)["reference_comparison"]
            self.assertEqual((comparison["analyzed"], comparison["eligible"]), (1, 2))
            self.assertTrue(comparison["partial"])
            status, _, body = self._get_state()
            stored = json.loads(body)["session"]["research"]["reference_comparison"]
            self.assertTrue(stored["partial"])
            self.assertIn("1 条参考", stored["partial_reason"])

    def _get_json(self, path):
        request = urllib.request.Request(self.base + path)
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8")
