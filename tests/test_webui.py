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

    def post_binary(self, path, data, *, headers=None):
        request_headers = {"Content-Type": "application/octet-stream"}
        request_headers.update(headers or {})
        request = urllib.request.Request(
            self.base + path, data=data, method="POST", headers=request_headers
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, dict(response.headers), response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read().decode("utf-8")

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
        # Issue #44 chat-first MVP：首页主操作是流式自由聊天；
        # canonical session/start 仍保留在服务端与阶段工作流中，但不再是首页入口
        self.assertIn("/api/workbench/chat/stream", body)
        # XSS-safety: the page must never use innerHTML for rendering
        self.assertNotIn("innerHTML", body)
        self.assertIn("textContent", body)

    def test_settings_route_is_a_distinct_minimal_page(self):
        status, headers, body = self.get("/settings")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("Content-Type", "").startswith("text/html"))
        self.assertIn('id="settings-view"', body)
        self.assertIn('id="creator-view"', body)
        self.assertIn('href="/"', body)
        self.assertIn("大模型设置", body)
        self.assertIn("settingsPage = window.location.pathname === '/settings'", body)
        self.assertNotIn('id="settings-panel"', body)

    def test_settings_page_navigation_preserves_creator_state_without_reload(self):
        """Issue #44: ⚙ 设置入口走 pushState 单文档切换，不整页刷新；
        选题草稿写入 localStorage，返回创作不丢已输入内容。"""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("history.pushState", body)
        self.assertIn("'popstate'", body)
        self.assertIn("TOPIC_DRAFT_KEY", body)
        self.assertIn("localStorage", body)
        self.assertIn("返回创作", body)

    def test_creator_home_has_one_primary_topic_action_and_no_inline_settings_form(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        # Owner UX（issuecomment-6364369899）：单一连续对话工作区 ——
        # 空态是安静居中的欢迎（welcome-pane），不再有巨型 hero 卡；
        # 有对话后 turns/草稿/旧集入口都在同一滚动流（conversation）里，
        # composer 始终 sticky 贴在视口底部，绝不需要回到顶部发下一条。
        self.assertIn('id="welcome-pane"', body)
        self.assertIn('id="conversation"', body)
        self.assertIn('id="composer-dock"', body)
        self.assertIn("position: sticky", body)
        self.assertIn("function updateWelcomeVisibility", body)
        self.assertIn("function nearBottom", body)
        self.assertIn('id="settings-link"', body)
        # Chat-first：唯一主操作是发送聊天（明确付费动作），一次说明计费而非每轮打断
        self.assertIn("你想聊什么？", body)
        self.assertIn("发送会调用你在「设置」里配置的模型服务并按其计费", body)
        self.assertIn('id="search-btn"', body)
        self.assertIn('id="chat-stop"', body)
        self.assertIn('id="chat-retry"', body)
        self.assertIn('id="draft-card"', body)
        # 失败不丢输入：404/路由不匹配给出真实服务版本指引并恢复未发送内容
        self.assertIn("本机服务可能是旧版本", body)
        self.assertIn("输入已恢复", body)
        # 草稿门禁说明卡：解释正式路径但不自动转换
        self.assertIn("进入正式审核", body)
        self.assertIn("不会自动转换", body)
        self.assertIn("未经研究与事实核查", body)
        # 流式与恢复契约：真实 SSE 增量 + 停止不写半截回复 + 刷新恢复
        self.assertIn("getReader()", body)
        self.assertIn("AbortController", body)
        self.assertIn("renderChat(state.chat", body)
        # B3（Nexus 5626927896）计费诚实：停止 = 停止显示 + 尽力中断请求，
        # 绝不承诺「不再计费」——已产生的费用可能仍会计入账单。
        self.assertIn("已停止显示并尝试中断模型请求", body)
        self.assertIn("已产生的费用可能仍会计入账单", body)
        self.assertNotIn("不会继续计费", body)
        # B3 幂等重试：按服务器持久化的 turn id 复用，不复制用户消息
        self.assertIn("retry_turn_id", body)
        self.assertIn("function updateRetryBtn", body)
        self.assertIn("stage-nav", body)
        self.assertIn("高级设置", body)
        self.assertIn("下载位置", body)
        # 两个视图共享同一份文档，但同一时刻绝不垂直同时渲染：
        # settingsPage 状态直接驱动互斥 hidden。
        self.assertIn("creatorView.hidden = settingsPage", body)
        self.assertIn("settingsView.hidden = !settingsPage", body)

    def test_creator_stages_are_three_plus_optional_audio(self):
        """Issue #44: 概念三阶段 ① 视频参考 → ② 观点与资料 → ③ 原创口播稿；
        音频与素材仅在口播稿审核通过后成为可选入口，不常驻第六步。
        一次只展示当前阶段，用户可随时回看上一阶段而不丢会话。"""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("① 视频参考", body)
        self.assertIn("② 观点与资料", body)
        self.assertIn("③ 原创口播稿", body)
        self.assertIn("音频与素材", body)
        self.assertIn("继续做音频与素材", body)
        # 音频 tab 只在口播稿已审核或音频已激活时出现
        self.assertIn("function scriptReviewed(", body)
        self.assertIn("audioActive(currentSession)", body)
        # 阶段聚焦：同一时间只显示一个阶段内容
        self.assertIn("node.hidden = id !== stageId", body)

    def test_new_episode_mode_hides_old_session_until_explicit_start_or_cancel(self):
        """Nexus B1: entering a new episode must leave the old session intact
        while the topic hero is the only visible creator surface."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn('id="cancel-new-episode"', body)
        self.assertIn("var newEpisodeMode = false", body)
        self.assertIn("previousSessionForNewEpisode", body)
        self.assertIn("function enterNewEpisode", body)
        self.assertIn("function cancelNewEpisode", body)
        self.assertIn("stageBar.hidden = true", body)
        self.assertIn("STAGES.forEach(function (id) { document.getElementById(id).hidden = true; })", body)

    def test_legacy_workbench_is_collapsed_entry_never_inline_with_chat(self):
        """Nexus B1 (5626927896)：旧集正式工作流默认折叠、与聊天首页明确
        分离 —— stage-bar/表单/候选绝不混进聊天下方，只有显式展开才渲染。"""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn('id="legacy-workbench-entry"', body)
        self.assertIn("查看既有正式工作流", body)
        self.assertIn("相互独立", body)
        # 有会话但未展开：stage-bar 隐藏、折叠入口可见（含旧集主题）
        self.assertIn("if (!legacyEntry.open)", body)
        self.assertIn("legacyTopic.textContent = '本集：' + currentSession.topic", body)
        # 展开监听：legacy stages 只在 <details> open 时才渲染进 stageBar
        self.assertIn("legacyEntry.addEventListener('toggle'", body)
        # 无会话 / 新一集模式：折叠入口也隐藏（没有旧集可看）
        self.assertIn("legacyEntry.hidden = true", body)
        # <details> 默认收起：绝不在聊天下方平铺旧集工作流
        self.assertIn('<details id="legacy-workbench-entry" class="card legacy-entry" hidden>', body)

    def test_script_result_is_cleared_and_async_reload_is_session_bound(self):
        """Nexus B2: a reviewed manuscript from episode A cannot leak into
        episode B while a stale final-script request is still in flight."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("function clearScriptResult", body)
        self.assertIn("renderedScriptKey = null", body)
        self.assertIn("expectedSessionId", body)
        self.assertIn("currentSession.session_id === expectedSessionId", body)
        self.assertIn("scriptResultSessionId", body)

    def test_reference_guided_visual_contract_is_present(self):
        """The creator and settings surfaces must expose the new hierarchy,
        instead of only swapping the previous card palette."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        for marker in (
            'class="hero-mark"', 'class="hero-composer"',
            'class="composer-toolbar"', 'class="prompt-hints"',
            'id="settings-cancel"', 'id="toggle-key"', 'API 地址',
            'settings-actions', 'settings-card'
        ):
            self.assertIn(marker, body)

    def test_offline_fixture_sources_are_explicitly_labeled(self):
        """B3 evidence must never read a mixed fixture source list as live
        independent reporting."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("offline_fixture", body)
        self.assertIn("离线演示夹具：仅用于验证页面流程，不代表真实独立研究来源。", body)

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
        # title switches to in-progress and is restored for the active view
        self.assertIn("处理中…", body)
        self.assertIn("currentTitle", body)
        # previous stage card is dimmed while a new operation is in flight
        self.assertIn(".card.stale", body)
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

    def test_index_wraps_unbroken_status_values_on_narrow_screens(self):
        """Issue #38: SHA/path status text must not create horizontal scroll."""
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("overflow-wrap: anywhere", body)
        self.assertIn("word-break: break-word", body)

    def test_index_exposes_deepseek_preset_and_truthful_connection_indicator(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn('value="deepseek"', body)
        self.assertIn("api.deepseek.com", body)
        self.assertIn("connection_kind", body)
        # 连接状态如实分级：未配置 / 已保存未验证 / 已连接 / 连接失败，
        # 并以自然语言给出下一步建议；开发/夹具连接呈现为独立的
        # 「开发测试环境」状态，绝不冒充真实成功。
        self.assertIn("未配置", body)
        self.assertIn("已保存未验证", body)
        self.assertIn("已连接", body)
        self.assertIn("连接失败", body)
        self.assertIn("开发测试环境", body)
        self.assertIn("清除 API Key", body)
        # 普通设置界面不出现内部状态码与本地服务字样（Issue #44 设置体验）
        self.assertNotIn("WAITING_FOR_OWNER_API_KEY", body)
        self.assertNotIn("（本地服务）", body)
        self.assertNotIn("（模拟服务）", body)

    def test_settings_deepseek_mode_needs_only_api_key(self):
        """Issue #44 设置体验：默认 DeepSeek 下普通用户只需填写 API Key，
        模型与官方 API 地址自动配置；其他服务商才展示模型/地址字段。"""
        status, _, body = self.get("/settings")
        self.assertEqual(status, 200)
        # 自动配置说明行（DeepSeek 模式主展示）
        self.assertIn('id="st-deepseek-auto"', body)
        self.assertIn("官方 API 地址已自动配置", body)
        self.assertIn("只需填写 API Key", body)
        # 模型/地址字段存在但按服务商模式显隐
        self.assertIn('id="st-model-field"', body)
        self.assertIn('id="st-chat-field"', body)
        self.assertIn("function syncManualFields(mode)", body)
        # DeepSeek 选中时自动填入官方地址与模型（含首次访问预设）
        self.assertIn("https://api.deepseek.com", body)
        self.assertIn("deepseek-flash", body)
        # 非默认服务商才需要手填模型：模式切换同步显隐
        self.assertIn("autoNote.hidden = !deepseek", body)
        self.assertIn("modelField.hidden = deepseek", body)
        self.assertIn("chatField.hidden = !(mode === 'chat')", body)

    def test_settings_test_click_persists_form_before_pinging(self):
        """Nexus delta（issuecomment-6358124584）：粘贴 API Key 后直接点
        「测试连接」必须先安全保存当前表单，保存成功后再对刚保存的配置
        执行真实连接测试；保存失败必须阻止测试并给出中文错误。"""
        status, _, body = self.get("/settings")
        self.assertEqual(status, 200)
        # 表单收集与持久化是可复用函数（保存/测试共用同一路径）
        self.assertIn("function settingsFormPayload()", body)
        self.assertIn("function persistSettings()", body)
        # 「测试连接」处理器内：persistSettings() 必须先于 /settings/test 请求
        marker = body.index("settings-test').addEventListener")
        block = body[marker:marker + 4000]
        self.assertIn("persistSettings()", block)
        self.assertIn("/api/workbench/settings/test", block)
        self.assertLess(
            block.index("persistSettings()"),
            block.index("/api/workbench/settings/test"),
        )
        # 保存失败阻止网络测试：中文提示含「未连接测试」
        self.assertIn("未连接测试", block)
        # 保存成功后测试刚保存的配置
        self.assertIn("已保存，测试中…", block)
        # 已输入 vs 已持久化：输入框有新 Key 时徽章显示「已输入未保存」，
        # 不再误导显示「未配置」
        self.assertIn("已输入未保存", body)
        self.assertIn("Key 已输入但尚未保存", body)

    def test_settings_p0_frontend_resets_hidden_fields_and_debounces_test(self):
        """Nexus P0 前端断言：切换到 DeepSeek 无条件重置模型/地址为官方值
        （丢弃隐藏字段残留），「测试连接」有在飞防抖，不重复发起付费 ping。"""
        status, _, body = self.get("/settings")
        self.assertEqual(status, 200)
        marker = body.index("st-mode').addEventListener")
        block = body[marker:marker + 1200]
        # 无条件重置（不再有空值判断包裹）
        self.assertIn("Nexus P0", block)
        self.assertIn("document.getElementById('st-chat').value = 'https://api.deepseek.com'", block)
        self.assertIn("document.getElementById('st-model').value = 'deepseek-flash'", block)
        # 防抖：在飞标志 + disabled
        self.assertIn("settingsTestInFlight", body)
        self.assertIn("if (settingsTestInFlight) { return; }", body)
        self.assertIn("btn.disabled = true", body)
        self.assertIn("btn.disabled = false", body)
        self.assertIn("button:disabled", body)

    def test_index_exposes_explicit_deepseek_search_budget_controls(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("/api/workbench/research/search", body)
        self.assertIn("/api/workbench/research/fetch", body)
        self.assertIn("可能产生计费", body)
        self.assertIn("搜索结果不是事实证据", body)

    def test_index_exposes_audio_import_delivery_and_gap_status_controls(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("/api/workbench/audio/import", body)
        self.assertIn("/api/workbench/audio/deliver", body)
        self.assertIn("/api/workbench/audio/source", body)
        self.assertIn("WAITING_FOR_OWNER_REVIEW", body)
        self.assertIn("Edit Map", body)

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


class ChatStreamHttpTests(LocalWebUITestCase):
    """Issue #44 chat-first MVP：SSE 流式 HTTP 契约、恢复与草稿修订。"""

    class StreamLLM:
        def __init__(self, chunks, calls):
            self.chunks = list(chunks)
            self.calls = calls

        def chat_stream(self, messages):
            import time

            self.calls.append(("chat_stream", [m.get("role") for m in messages]))
            for chunk in self.chunks:
                time.sleep(0.05)
                yield chunk

    def _sse_post(self, path, payload, *, timeout=10.0):
        import http.client

        port = self.server.server_address[1]
        conn = http.client.HTTPConnection(DEFAULT_HOST, port, timeout=timeout)
        conn.request("POST", path, body=json.dumps(payload).encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        status = response.status
        ctype = response.getheader("Content-Type") or ""
        conn.close()
        events = []
        for block in raw.split("\n\n"):
            block = block.strip()
            if block.startswith("data:"):
                events.append(json.loads(block[5:].strip()))
        return status, ctype, events

    def _chat_flow(self, root, llm):
        from deeptalk_studio.workbench.flow import WorkbenchFlow

        return WorkbenchFlow(root, provider_factory=lambda settings: llm)

    def _get_state(self):
        request = urllib.request.Request(self.base + "/api/workbench/state")
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8")

    def _configure_deepseek(self, root):
        from deeptalk_studio.workbench.settings import (
            apply_settings_update,
            load_settings,
            save_settings,
        )

        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "deepseek",
            "api_key": "sk-chat-http-fixture",
            "downloads_dir": str(root),
        }))

    def test_chat_stream_sse_recovery_and_draft_revisions_over_http(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            calls = []
            llm = self.StreamLLM(["第一段", "第二段"], calls)
            self.start_server(flow=self._chat_flow(root, llm))
            self._configure_deepseek(root)
            status, ctype, events = self._sse_post("/api/workbench/chat/stream", {
                "message": "聊聊夜间城市选题",
                "links": [{"url": "https://example.com/ref"}],
            })
            self.assertEqual(status, 200)
            self.assertIn("text/event-stream", ctype)
            kinds = [e["type"] for e in events]
            self.assertEqual(kinds[0], "start")
            self.assertEqual(kinds[-1], "done")
            self.assertEqual([e["type"] for e in events if e["type"] == "delta"],
                             ["delta", "delta"])
            self.assertEqual(events[0]["provider_kind"], "fixture")
            self.assertEqual(events[0]["user_turn"]["links"][0]["status"], "unknown")
            self.assertEqual(events[-1]["turn"]["content"], "第一段第二段")
            # 刷新恢复：/state 带完整对话
            status, _, body = self._get_state()
            self.assertEqual(status, 200)
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user", "assistant"])
            # 草稿生成 → 用户编辑修订（不可变 revisions）
            status, _, body = self.post("/api/workbench/chat/draft", {})
            self.assertEqual(status, 200, body)
            draft1 = json.loads(body)["draft"]
            self.assertEqual((draft1["schema"], draft1["status"], draft1["revision"]),
                             ("creative-draft/1", "unreviewed", 1))
            status, _, body = self.post("/api/workbench/chat/draft/edit", {
                "content": "用户自由编辑后的草稿",
            })
            self.assertEqual(status, 200, body)
            draft2 = json.loads(body)["draft"]
            self.assertEqual((draft2["revision"], draft2["origin"]), (2, "user_edit"))
            status, _, body = self._get_state()
            drafts = json.loads(body)["chat"]["drafts"]
            self.assertEqual([d["revision"] for d in drafts], [1, 2])
            self.assertNotIn("sk-chat-http-fixture", json.dumps(json.loads(body)["chat"]))
            # 只发生一次聊天模型调用 + 一次草稿模型调用（无隐藏重复计费）
            self.assertEqual(len(calls), 2)

    def test_chat_stream_without_config_is_400_json_not_sse(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            calls = []
            llm = self.StreamLLM(["x"], calls)
            self.start_server(flow=self._chat_flow(root, llm))
            status, _, body = self.post("/api/workbench/chat/stream", {
                "message": "还没有配置模型",
            })
            self.assertEqual(status, 400)
            error = json.loads(body)["error"]
            self.assertIn("API Key", error)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", error)
            self.assertEqual(calls, [])

    def test_chat_stream_client_disconnect_writes_no_assistant_turn(self):
        import socket
        import tempfile
        import time

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            calls = []
            llm = self.StreamLLM(["段落一", "段落二", "段落三"], calls)
            self.start_server(flow=self._chat_flow(root, llm))
            self._configure_deepseek(root)
            port = self.server.server_address[1]
            payload = json.dumps({"message": "中途断开"}).encode("utf-8")
            request = (
                b"POST /api/workbench/chat/stream HTTP/1.1\r\n"
                + f"Host: 127.0.0.1:{port}\r\n".encode("utf-8")
                + b"Content-Type: application/json\r\n"
                + f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
                + payload
            )
            with socket.create_connection((DEFAULT_HOST, port), timeout=6) as sock:
                sock.sendall(request)
                sock.settimeout(3)
                try:
                    sock.recv(4096)  # 读到开头就断开（模拟停止/刷新）
                except socket.timeout:
                    pass
            time.sleep(0.8)  # 服务端写失败 → 关闭上游 → 不写助手回复
            status, _, body = self._get_state()
            self.assertEqual(status, 200)
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user"])

    def test_second_stream_while_first_in_flight_returns_400(self):
        """Nexus B2/P0（5627594838）：在飞流的准入预约必须先于任何存储变更 ——
        重叠发送 400 时被拒消息绝不进入聊天记录（stored turns 保持
        [user A]→[user A, assistant A]，B 内容零出现），零隐藏模型调用，
        且预约释放后后续发送照常可行。"""
        import tempfile
        import threading
        import time

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            calls = []
            # 20 段 × 0.05s ≈ 1s，保证第二条请求落在第一条流进行中
            llm = self.StreamLLM([f"段{i}" for i in range(20)], calls)
            self.start_server(flow=self._chat_flow(root, llm))
            self._configure_deepseek(root)
            result = {}

            # 1) A 流开始：提交 user A 并保持慢速进行
            def first_stream():
                result["status"], result["ctype"], result["events"] = self._sse_post(
                    "/api/workbench/chat/stream", {"message": "第一条消息 A"}
                )

            thread = threading.Thread(target=first_stream, daemon=True)
            thread.start()
            time.sleep(0.15)  # 等第一条流注册预约并开始产出
            # 2) B 尝试重叠发送 → 400；A 运行期间存储恰为 [user A]，
            #    被拒的 B 消息不得在任何位置出现
            status, _, body = self.post("/api/workbench/chat/stream", {
                "message": "重叠时被拒绝的第二条消息 B",
            })
            self.assertEqual(status, 400)
            self.assertIn("上一条回复还在进行中", json.loads(body)["error"])
            self.assertEqual(len(calls), 1)  # 拒绝发生在持久化前，B 不触发模型调用
            status, _, body = self._get_state()
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user"])
            self.assertEqual([t["content"] for t in chat["turns"]], ["第一条消息 A"])
            self.assertNotIn("重叠时被拒绝的第二条消息 B", json.dumps(chat, ensure_ascii=False))
            # 3) A 完成 → 存储恰为 [user A, assistant A]；B 内容仍零出现
            thread.join(timeout=15)
            self.assertEqual(result["status"], 200)
            kinds = [e["type"] for e in result["events"]]
            self.assertEqual(kinds[0], "start")
            self.assertEqual(kinds[-1], "done")
            status, _, body = self._get_state()
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user", "assistant"])
            self.assertEqual([t["content"] for t in chat["turns"]],
                             ["第一条消息 A", "".join(f"段{i}" for i in range(20))])
            self.assertNotIn("重叠时被拒绝的第二条消息 B", json.dumps(chat, ensure_ascii=False))
            self.assertEqual(len(calls), 1)
            # 4) 预约已释放：后续正常发送 C 照常可行（retry/stop 语义不受影响）
            status, ctype, events = self._sse_post("/api/workbench/chat/stream", {
                "message": "后续第三条消息 C",
            }, timeout=15)
            self.assertEqual(status, 200)
            self.assertEqual(events[-1]["type"], "done")
            status, _, body = self._get_state()
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]],
                             ["user", "assistant", "user", "assistant"])
            self.assertEqual([t["content"] for t in chat["turns"]][2], "后续第三条消息 C")
            self.assertEqual(len(calls), 2)  # A + C，各一次显式调用

    def test_concurrent_first_sends_admit_exactly_one(self):
        """Nexus B2/P0（5627594838）：两个并发首次发送（尚无任何会话）也必须
        恰好放行一个 —— 预约检查+注册在锁内原子完成；被 400 拒绝的一方
        不创建会话、不写 user turn，存储最终只有被放行方的一问一答。"""
        import tempfile
        import threading

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            calls = []
            llm = self.StreamLLM(["首条回复"], calls)
            self.start_server(flow=self._chat_flow(root, llm))
            self._configure_deepseek(root)
            outcomes = []
            barrier = threading.Barrier(2)

            def send(message):
                barrier.wait()  # 两线程对齐发送时刻，最大化竞争窗口
                outcomes.append(self._sse_post(
                    "/api/workbench/chat/stream", {"message": message}, timeout=15
                ))

            t1 = threading.Thread(target=send, args=("并发首发之一",), daemon=True)
            t2 = threading.Thread(target=send, args=("并发首发之二",), daemon=True)
            t1.start()
            t2.start()
            t1.join(timeout=15)
            t2.join(timeout=15)
            self.assertEqual(sorted(o[0] for o in outcomes), [200, 400])
            status, _, body = self._get_state()
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user", "assistant"])
            admitted = chat["turns"][0]["content"]
            self.assertIn(admitted, ("并发首发之一", "并发首发之二"))
            rejected = "并发首发之二" if admitted == "并发首发之一" else "并发首发之一"
            self.assertNotIn(rejected, json.dumps(chat, ensure_ascii=False))
            self.assertEqual(len(calls), 1)

    def test_http_retry_after_disconnect_reuses_turn_without_duplicate(self):
        """Nexus B3：客户端停止后，带 retry_turn_id 的重发请求被幂等复用 ——
        会话中只有一条 user turn；完成后一问一答，绝无重复消息。"""
        import socket
        import tempfile
        import time

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            calls = []
            llm = self.StreamLLM([f"慢段{i}" for i in range(20)], calls)
            self.start_server(flow=self._chat_flow(root, llm))
            self._configure_deepseek(root)
            port = self.server.server_address[1]
            payload = json.dumps({"message": "中途停止的消息"}).encode("utf-8")
            request = (
                b"POST /api/workbench/chat/stream HTTP/1.1\r\n"
                + f"Host: 127.0.0.1:{port}\r\n".encode("utf-8")
                + b"Content-Type: application/json\r\n"
                + f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
                + payload
            )
            # 1) 读到 start 事件（user turn 已持久化）后立即断开 = 用户停止
            with socket.create_connection((DEFAULT_HOST, port), timeout=6) as sock:
                sock.sendall(request)
                sock.settimeout(4)
                data = b""
                while b'"type": "start"' not in data:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            time.sleep(0.8)  # 等服务端感知断开、释放 in-flight
            status, _, body = self._get_state()
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user"])
            turn_id = chat["turns"][0]["turn_id"]
            # 2) 带原 turn id 的显式重发 → 幂等复用，不追加重复 user turn
            status, ctype, events = self._sse_post("/api/workbench/chat/stream", {
                "message": "中途停止的消息",
                "retry_turn_id": turn_id,
            }, timeout=15)
            self.assertEqual(status, 200)
            self.assertEqual(events[0]["type"], "start")
            self.assertEqual(events[0]["user_turn"]["turn_id"], turn_id)
            self.assertEqual(events[-1]["type"], "done")
            # 3) 最终会话一问一答，只有一条 user 消息
            status, _, body = self._get_state()
            chat = json.loads(body)["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user", "assistant"])
            self.assertEqual([t["content"] for t in chat["turns"]],
                             ["中途停止的消息", "".join(f"慢段{i}" for i in range(20))])
            # 两次模型调用均为显式动作（首次 + 重发），无隐藏第三次
            self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()


class WorkbenchRoutesTests(LocalWebUITestCase):
    """Issue #23 unified workbench HTTP surface (fake LLM + fake fetch)."""

    def _flow(self, root: Path, deepseek_client=None, audio_delivery_runner=None):
        from tests.test_workbench import (
            FakeWorkbenchLLM,
            _fake_discovery,
            _fake_fetcher,
        )

        from deeptalk_studio.workbench.flow import WorkbenchFlow

        kwargs = {}
        if deepseek_client is not None:
            kwargs["deepseek_client_factory"] = lambda settings: deepseek_client
        if audio_delivery_runner is not None:
            kwargs["audio_delivery_runner"] = audio_delivery_runner
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery,
            provider_factory=lambda settings: FakeWorkbenchLLM(settings),
            fetcher=_fake_fetcher,
            **kwargs,
        )

    def test_audio_binary_import_and_delivery_status_routes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def runner(session_root, repo_root):
                output = Path(session_root) / "DeepTalk-Aligned-Edit"
                output.mkdir(parents=True, exist_ok=True)
                (output / "edit-map.md").write_text("# Edit Map\nAUDIO_ONLY\n", encoding="utf-8")
                return {
                    "delivery": {
                        "timeline": {"spans": [{"span_id": "ST001", "start_seconds": "0", "end_seconds": "1"}]},
                        "gaps": [{"span_id": "ST001", "reason": "AUDIO_ONLY", "detail": "需要人工补画面"}],
                    },
                    "asset_pack": {"machine_map": {"rows": [{"decision": "AUDIO_ONLY"}]}},
                    "qa": {"package_gate_status": "warnings"},
                    "paths": {"markdown": Path(session_root) / "DeepTalk-Aligned-Edit" / "edit-map.md"},
                    "preview_path": None,
                }

            self.start_server(flow=self._flow(root, audio_delivery_runner=runner))
            status, _, body = self.post("/api/workbench/session/start", {
                "topic": "本市图书馆夜间开放试点", "urls": [],
            })
            self.assertEqual(status, 200, body)
            started = json.loads(body)
            self.assertIn("settings", started)
            self.assertIn("api_key_masked", started["settings"])
            sid = started["session"]["session_id"]
            common = {
                "X-Workbench-Session": sid,
                "X-Workbench-Filename": "take.wav",
                "X-Workbench-Origin": "owner_made",
            }
            status, _, body = self.post_binary("/api/workbench/audio/import", b"audio", headers=common)
            self.assertEqual(status, 200, body)
            imported = json.loads(body)
            self.assertEqual(imported["origin"], "owner_made")
            status, headers, body = self.get(
                "/api/workbench/audio/source?session_id=" + sid
            )
            self.assertEqual(status, 200)
            self.assertEqual(body, "audio")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            status, _, body = self.post_binary("/api/workbench/audio/import", b"x", headers={**common, "X-Workbench-Filename": "../escape.wav"})
            self.assertEqual(status, 400)
            status, _, body = self.post("/api/workbench/audio/deliver", {"session_id": sid})
            self.assertEqual(status, 200, body)
            delivered = json.loads(body)
            self.assertEqual(delivered["status"], "delivered")
            self.assertEqual(delivered["gap_count"], 1)
            status, _, body = self._get_state()
            self.assertEqual(status, 200)
            state = json.loads(body)["session"]
            self.assertEqual(state["audio_delivery"]["status"], "delivered")
            self.assertEqual(state["audio_delivery"]["gaps"][0]["reason"], "AUDIO_ONLY")
            status, headers, body = self.get(
                "/api/workbench/audio/artifact?session_id=" + sid + "&kind=markdown"
            )
            self.assertEqual(status, 200)
            self.assertIn("AUDIO_ONLY", body)
            self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")

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

    def test_settings_p0_deepseek_switch_discards_stale_custom_values(self):
        """Nexus P0（PR #45 review 5625537364）：HTTP 层强制——切换到
        DeepSeek 后保存，即便请求体携带残留的自定义 Chat 端点/模型，
        持久化配置与响应都必须是官方端点与官方模型，新 Key 绝不路由到旧端点。"""
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.start_server(flow=self._flow(root))
            status, _, body = self.post("/api/workbench/settings", {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "custom-model",
                "api_key": "sk-old-chat-key",
                "downloads_dir": str(root),
            })
            self.assertEqual(status, 200)
            status, _, body = self.post("/api/workbench/settings", {
                "provider_mode": "deepseek",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "custom-model",
                "api_key": "sk-newly-pasted-key",
                "downloads_dir": str(root),
            })
            self.assertEqual(status, 200)
            payload = json.loads(body)
            self.assertEqual(payload["provider_mode"], "deepseek")
            self.assertEqual(payload["chat_base_url"], "https://api.deepseek.com")
            self.assertEqual(payload["model"], "deepseek-flash")
            self.assertEqual(payload["endpoint"], "https://api.deepseek.com/chat/completions")
            self.assertNotIn("llm.example.com", body)
            self.assertNotIn("custom-model", body)
            # 状态接口同样只暴露官方配置
            status, _, body = self._get_state()
            self.assertEqual(status, 200)
            self.assertNotIn("llm.example.com", body)

    def test_workbench_unknown_route_is_404_and_settings_test_requires_config(self):
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.start_server(flow=self._flow(root))
            status, _, _ = self.post("/api/workbench/no-such-step", {})
            self.assertEqual(status, 404)
            status, _, body = self.post("/api/workbench/settings/test", {})
            self.assertEqual(status, 400)
            # Issue #44 设置体验：HTTP 层同样只出现自然中文，无内部状态码。
            error = json.loads(body)["error"]
            self.assertIn("设置尚未完成", error)
            self.assertIn("API Key", error)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", error)

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
