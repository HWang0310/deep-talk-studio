"""Deterministic offline tests for the Phase 1B Mac-local Web UI (Issue #26).

All provider interaction is faked via injected providers; no test touches
the real Bilibili network. The HTTP server runs on an ephemeral loopback
port exactly like production (127.0.0.1 only).
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from deeptalk_studio.webui import (
    DEFAULT_HOST,
    WebUIRequestError,
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

    def start_server(self, provider=None):
        provider = provider or FakeProvider(
            default_search=ok_search(
                search_item("BV1hi000000A", "莫斯科大学留学生旭日旗事件进展", views=900),
                search_item("BV1hi000000B", "莫斯科大学留学生旭日旗事件回应", views=500),
            )
        )
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        server = make_server(
            0,
            output_dir=Path(tmp.name),
            provider_factory=lambda: provider,
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
        self.assertIn("/api/discover", body)  # the only business endpoint
        # XSS-safety: the page must never use innerHTML for rendering
        self.assertNotIn("innerHTML", body)
        self.assertIn("textContent", body)

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


if __name__ == "__main__":
    unittest.main()
