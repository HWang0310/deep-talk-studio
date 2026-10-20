"""Deterministic offline tests for the Phase 1 Bilibili reference discovery capability.

All network access is faked via injected transports/providers. The opt-in live
smoke test lives in tests/test_reference_discovery_live.py and never runs in CI.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deeptalk_studio.bilibili_reference_provider import (
    BilibiliReferenceProvider,
    SearchItem,
    SearchOutcome,
    TransportResponse,
    VideoMetadataOutcome,
)
from deeptalk_studio.reference_discovery import (
    GENERIC_SUFFIXES,
    ReferenceDiscoveryError,
    assess_relevance,
    build_query_plan,
    build_reference_candidate_set,
    canonicalize_bilibili_reference,
    topic_anchor,
    validate_reference_candidate_set,
)


# ---------------------------------------------------------------------------
# fixtures / fakes
# ---------------------------------------------------------------------------


def search_item(bvid, title, *, uploader="UP", views=100, pubdate=1792456200,
                description=""):
    return SearchItem(
        bvid=bvid,
        title=title,
        uploader=uploader,
        published_at="2026-10-20T00:00:00+00:00",
        snippet_view_count=views,
        description=description,
    )


def ok_search(*items, status="ok", message=""):
    return SearchOutcome(status=status, items=tuple(items), http_status=200,
                         api_code=0, message=message)


def ok_metadata(bvid, *, title=None, views=12345):
    return VideoMetadataOutcome(
        status="ok",
        title=title or f"标题-{bvid}",
        uploader="UP主",
        published_at="2026-10-18T00:00:00+00:00",
        view_count=views,
        duration_sec=188,
        api_code=0,
        message="",
    )


def metadata_outcome(status, *, api_code=-404, message="啊叻？视频不见了诶"):
    return VideoMetadataOutcome(
        status=status,
        title="",
        uploader="",
        published_at="",
        view_count=None,
        duration_sec=None,
        api_code=api_code,
        message=message,
    )


class FakeProvider:
    """Drop-in provider double for service-level tests."""

    def __init__(self, search_by_query=None, default_search=None,
                 metadata_by_bvid=None, default_metadata=None):
        self.search_by_query = search_by_query or {}
        self.default_search = default_search or ok_search()
        self.metadata_by_bvid = metadata_by_bvid or {}
        self.default_metadata = default_metadata or ok_metadata("x")
        self.search_calls = []
        self.metadata_calls = []

    def search_videos(self, query, page=1):
        self.search_calls.append((query, page))
        return self.search_by_query.get(query, self.default_search)

    def fetch_video_metadata(self, bvid):
        self.metadata_calls.append(bvid)
        return self.metadata_by_bvid.get(bvid, self.default_metadata)


MOSCOW_TOPIC = "莫斯科大学留学生旭日旗事件"


# ---------------------------------------------------------------------------
# URL canonicalization
# ---------------------------------------------------------------------------


class CanonicalizationTests(unittest.TestCase):
    def test_bare_bvid(self):
        self.assertEqual(canonicalize_bilibili_reference("BV1SvJd6sEEZ")[0], "BV1SvJd6sEEZ")

    def test_full_url_with_params(self):
        url = "https://www.bilibili.com/video/BV1SvJd6sEEZ/?spm_id_from=333.788&vd_source=x"
        self.assertEqual(canonicalize_bilibili_reference(url)[0], "BV1SvJd6sEEZ")

    def test_mobile_and_bare_host(self):
        self.assertEqual(
            canonicalize_bilibili_reference("http://m.bilibili.com/video/BV1Phnc6eEvf")[0],
            "BV1Phnc6eEvf",
        )
        self.assertEqual(
            canonicalize_bilibili_reference("bilibili.com/video/BV1Phnc6eEvf/")[0],
            "BV1Phnc6eEvf",
        )

    def test_short_link_is_rejected_with_reason(self):
        bvid, reason = canonicalize_bilibili_reference("https://b23.tv/AbCdEf")
        self.assertIsNone(bvid)
        self.assertEqual(reason, "short_link_unsupported")

    def test_non_bilibili_url(self):
        bvid, reason = canonicalize_bilibili_reference("https://www.youtube.com/watch?v=abc")
        self.assertIsNone(bvid)
        self.assertEqual(reason, "not_bilibili_url")

    def test_malformed_inputs(self):
        for raw in ("BV123", "随便一段文字", "BV1xyz!!", "", "https://www.bilibili.com/"):
            bvid, reason = canonicalize_bilibili_reference(raw)
            self.assertIsNone(bvid, raw)
            self.assertEqual(reason, "malformed_reference", raw)


# ---------------------------------------------------------------------------
# query plan & relevance
# ---------------------------------------------------------------------------


class QueryPlanTests(unittest.TestCase):
    def test_generic_suffix_variant_is_added(self):
        plan = build_query_plan(MOSCOW_TOPIC, ())
        self.assertEqual(plan[0], MOSCOW_TOPIC)
        self.assertIn("莫斯科大学留学生旭日旗", plan)

    def test_plan_is_deduplicated_and_bounded(self):
        plan = build_query_plan(MOSCOW_TOPIC, ("莫斯科大学留学生旭日旗", "a", "b", "c", "d"))
        self.assertLessEqual(len(plan), 4)
        self.assertEqual(len(plan), len(set(plan)))
        self.assertEqual(plan[0], MOSCOW_TOPIC)

    def test_short_topic_has_no_strip_variant(self):
        plan = build_query_plan("旭日旗", ())
        self.assertEqual(plan, ["旭日旗"])

    def test_topic_anchor_strips_generic_suffix(self):
        self.assertEqual(topic_anchor(MOSCOW_TOPIC), "莫斯科大学留学生旭日旗")
        self.assertIn("事件", GENERIC_SUFFIXES)


class RelevanceTests(unittest.TestCase):
    def test_variant_wording_counts_as_relevant(self):
        title = "【没中国人去上课所以我才披】南京历史系留学生莫斯科披破旗惹众怒"
        result = assess_relevance(title, "", MOSCOW_TOPIC)
        self.assertEqual(result["decision"], "relevant")

    def test_generic_history_video_is_excluded(self):
        title = "为什么是太阳？旭日旗、日本国名的来龙去脉！"
        result = assess_relevance(title, "", MOSCOW_TOPIC)
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["reason"], "low_relevance")

    def test_required_term_must_be_present(self):
        title = "莫斯科大学留学生被开除遣返最新通报"
        result = assess_relevance(title, "", MOSCOW_TOPIC, required_terms=("旭日旗",))
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["reason"], "missing_required_term")

    def test_excluded_term_wins(self):
        result = assess_relevance(
            "莫斯科大学留学生旭日旗事件二创合集", "", MOSCOW_TOPIC, excluded_terms=("二创",)
        )
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["reason"], "excluded_term_match")

    def test_anchor_hit_is_relevant(self):
        result = assess_relevance(
            "关于莫斯科大学留学生旭日旗事件 你需要知道的三件事", "", MOSCOW_TOPIC
        )
        self.assertEqual(result["decision"], "relevant")
        self.assertTrue(result["anchor_hit"])
        self.assertEqual(result["reason"], "anchor_hit")

    def test_matched_terms_are_recorded(self):
        title = "中国留学生披旭日旗被遣返"
        result = assess_relevance(title, "", MOSCOW_TOPIC)
        self.assertEqual(result["decision"], "relevant")
        self.assertTrue(result["trigram_hits"])
        self.assertEqual(result["reason"], "trigram_hits")


# ---------------------------------------------------------------------------
# provider (real class, fake transport)
# ---------------------------------------------------------------------------


def bili_search_body(*items):
    return json.dumps({
        "code": 0, "message": "0", "data": {"result": [dict(
            bvid=it["bvid"],
            title=it.get("title", ""),
            author=it.get("author", "UP"),
            play=it.get("play", 100),
            pubdate=it.get("pubdate", 1792456200),
            duration=it.get("duration", "3:08"),
            description=it.get("description", ""),
        ) for it in items]},
    })


def bili_view_body(bvid="BV1aaaaaaaaa", view=4321, pubdate=1792456200):
    return json.dumps({
        "code": 0, "message": "0",
        "data": {
            "bvid": bvid, "title": f"标题-{bvid}",
            "owner": {"name": "UP主"},
            "pubdate": pubdate, "duration": 188,
            "stat": {"view": view},
        },
    })


class BilibiliProviderTests(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        self.transport_calls = []

    def _track_sleep(self, seconds):
        self.sleeps.append(seconds)

    def _provider(self, responder, **kwargs):
        def transport(url, headers, timeout):
            self.transport_calls.append({"url": url, "headers": dict(headers)})
            status, body = responder(url)
            return TransportResponse(status, body)

        kwargs.setdefault("sleep", self._track_sleep)
        kwargs.setdefault("request_interval", 0.0)
        kwargs.setdefault("use_visitor_identity", False)
        return BilibiliReferenceProvider(transport=transport, **kwargs)

    def test_search_parses_items_and_strips_html(self):
        provider = self._provider(lambda url: (200, bili_search_body(
            {"bvid": "BV1aaaaaaaaa", "title": "带<em class=\"keyword\">高亮</em>的标题", "play": "987"}
        )))
        outcome = provider.search_videos("查询词")
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(len(outcome.items), 1)
        item = outcome.items[0]
        self.assertEqual(item.title, "带高亮的标题")
        self.assertEqual(item.snippet_view_count, 987)
        self.assertEqual(item.bvid, "BV1aaaaaaaaa")

    def test_http_412_is_blocked_without_retry(self):
        attempts = []

        def responder(url):
            attempts.append(url)
            return 412, "Blocked"

        provider = self._provider(responder, max_retries=2)
        outcome = provider.search_videos("查询词")
        self.assertEqual(outcome.status, "blocked")
        self.assertEqual(outcome.http_status, 412)
        self.assertEqual(len(attempts), 1)

    def test_html_error_page_is_blocked(self):
        provider = self._provider(lambda url: (200, "<!DOCTYPE html><html>出错啦</html>"))
        outcome = provider.search_videos("查询词")
        self.assertEqual(outcome.status, "blocked")

    def test_api_error_code_is_failed(self):
        provider = self._provider(lambda url: (200, json.dumps({"code": -412, "message": "请求被拦截"})))
        outcome = provider.search_videos("查询词")
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.api_code, -412)

    def test_server_error_is_retried_with_backoff_then_recovers(self):
        calls = {"n": 0}

        def responder(url):
            calls["n"] += 1
            if calls["n"] == 1:
                return 503, "service unavailable"
            return 200, bili_view_body()

        provider = self._provider(responder, max_retries=2, retry_backoff=2.0,
                                  sleep=self._track_sleep)
        outcome = provider.fetch_video_metadata("BV1aaaaaaaaa")
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(calls["n"], 2)
        self.assertEqual(self.sleeps, [2.0])  # one backoff sleep before the retry

    def test_view_api_status_mapping(self):
        provider = self._provider(lambda url: (200, json.dumps({"code": -404, "message": "啊叻？"})))
        self.assertEqual(provider.fetch_video_metadata("BV1aaaaaaaaa").status, "unavailable")
        provider = self._provider(lambda url: (200, json.dumps({"code": -400, "message": "请求错误"})))
        self.assertEqual(provider.fetch_video_metadata("BV1aaaaaaaaa").status, "invalid")
        provider = self._provider(lambda url: (200, json.dumps({"code": -403, "message": "权限"})))
        self.assertEqual(provider.fetch_video_metadata("BV1aaaaaaaaa").status, "restricted")
        provider = self._provider(lambda url: (200, bili_view_body(view=777)))
        outcome = provider.fetch_video_metadata("BV1aaaaaaaaa")
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.view_count, 777)
        self.assertEqual(outcome.uploader, "UP主")

    def test_visitor_identity_is_fetched_once_and_used_as_cookie(self):
        def responder(url):
            if "finger/spi" in url:
                return 200, json.dumps({"code": 0, "data": {"b_3": "VISITOR-ID-1", "b_4": "x"}})
            if "search/type" in url:
                return 200, bili_search_body({"bvid": "BV1aaaaaaaaa"})
            return 200, bili_view_body()

        def transport(url, headers, timeout):
            self.transport_calls.append({"url": url, "headers": dict(headers)})
            status, body = responder(url)
            return TransportResponse(status, body)

        provider = BilibiliReferenceProvider(
            transport=transport, use_visitor_identity=True,
            request_interval=0.0, sleep=self._track_sleep,
        )
        provider.search_videos("查询词")
        provider.fetch_video_metadata("BV1aaaaaaaaa")
        spi_calls = [c for c in self.transport_calls if "finger/spi" in c["url"]]
        self.assertEqual(len(spi_calls), 1)
        api_calls = [c for c in self.transport_calls if "finger/spi" not in c["url"]]
        self.assertEqual(len(api_calls), 2)
        for call in api_calls:
            self.assertIn("buvid3=VISITOR-ID-1", call["headers"].get("Cookie", ""))

    def test_no_visitor_identity_when_disabled(self):
        provider = self._provider(lambda url: (200, bili_search_body()), use_visitor_identity=False)
        provider.search_videos("查询词")
        for call in self.transport_calls:
            self.assertNotIn("finger/spi", call["url"])
            self.assertNotIn("buvid3", call["headers"].get("Cookie", ""))

    def test_spi_failure_degrades_silently(self):
        def responder(url):
            if "finger/spi" in url:
                return 200, "not json"
            if "search/type" in url:
                return 200, bili_search_body({"bvid": "BV1aaaaaaaaa"})
            return 200, bili_view_body()

        def transport(url, headers, timeout):
            self.transport_calls.append({"url": url, "headers": dict(headers)})
            status, body = responder(url)
            return TransportResponse(status, body)

        provider = BilibiliReferenceProvider(
            transport=transport, use_visitor_identity=True,
            request_interval=0.0, sleep=self._track_sleep,
        )
        outcome = provider.search_videos("查询词")
        self.assertEqual(outcome.status, "ok")

    def test_request_interval_sleeps_between_calls(self):
        provider = self._provider(lambda url: (200, bili_search_body()), request_interval=1.5,
                                  sleep=self._track_sleep)
        provider.search_videos("一")
        provider.search_videos("二")
        self.assertEqual(self.sleeps, [1.5])  # not before the first call


# ---------------------------------------------------------------------------
# service (fake provider)
# ---------------------------------------------------------------------------


class ReferenceCandidateSetTests(unittest.TestCase):
    def _build(self, topic=MOSCOW_TOPIC, user_urls=(), provider=None, **kwargs):
        kwargs.setdefault("now", "2026-10-20T12:00:00+00:00")
        return build_reference_candidate_set(
            topic, user_urls, provider=provider or FakeProvider(), **kwargs
        )

    def test_rejects_empty_topic(self):
        with self.assertRaises(ReferenceDiscoveryError):
            self._build(topic="   ")

    def test_user_urls_are_kept_first_and_auto_fill_reaches_five(self):
        provider = FakeProvider(
            default_search=ok_search(*[
                search_item(f"BV1aaaaaaaa{i}", f"莫斯科大学留学生旭日旗事件解读{i}")
                for i in range(6)
            ]),
            default_metadata=ok_metadata("x", views=1000),
        )
        artifact = self._build(
            user_urls=["https://www.bilibili.com/video/BV1SvJd6sEEZ/?spm=1"],
            provider=provider,
        )
        self.assertEqual(artifact["status"], "ok")
        self.assertEqual(len(artifact["candidates"]), 5)
        first = artifact["candidates"][0]
        self.assertEqual(first["bvid"], "BV1SvJd6sEEZ")
        self.assertTrue(first["user_supplied"])
        self.assertEqual(first["found_via_queries"][0], "user_supplied")
        autos = artifact["candidates"][1:]
        self.assertTrue(all(not c["user_supplied"] for c in autos))

    def test_user_url_duplicated_in_search_is_merged(self):
        provider = FakeProvider(
            search_by_query={
                MOSCOW_TOPIC: ok_search(search_item("BV1SvJd6sEEZ", "莫斯科大学留学生旭日旗现场")),
                "莫斯科大学留学生旭日旗": ok_search(),
            },
        )
        artifact = self._build(user_urls=["BV1SvJd6sEEZ"], provider=provider)
        bvids = [c["bvid"] for c in artifact["candidates"]]
        self.assertEqual(bvids.count("BV1SvJd6sEEZ"), 1)
        candidate = artifact["candidates"][0]
        self.assertIn(MOSCOW_TOPIC, candidate["found_via_queries"])
        self.assertIn("user_supplied", candidate["found_via_queries"])

    def test_malformed_and_unavailable_user_urls_are_rejected_with_reasons(self):
        provider = FakeProvider(
            metadata_by_bvid={
                "BV1aaaaaaaaa": metadata_outcome("unavailable"),
                "BV2aaaaaaaaa": metadata_outcome("invalid", api_code=-400),
                "BV3aaaaaaaaa": metadata_outcome("restricted", api_code=-403),
            },
        )
        artifact = self._build(
            user_urls=[
                "https://b23.tv/xyz",
                "https://youtube.com/x",
                "BV1aaaaaaaaa",
                "BV2aaaaaaaaa",
                "BV3aaaaaaaaa",
                "BV1xxxxxxxxx",
                "BV1SvJd6sEEZ",
            ],
            provider=provider,
        )
        reasons = {r["input"]: r["reason"] for r in artifact["rejected_user_urls"]}
        self.assertEqual(reasons["https://b23.tv/xyz"], "short_link_unsupported")
        self.assertEqual(reasons["https://youtube.com/x"], "not_bilibili_url")
        self.assertEqual(reasons["BV1aaaaaaaaa"], "video_unavailable")
        self.assertEqual(reasons["BV2aaaaaaaaa"], "video_invalid")
        self.assertEqual(reasons["BV3aaaaaaaaa"], "video_restricted")
        self.assertEqual(
            [c["bvid"] for c in artifact["candidates"]],
            ["BV1xxxxxxxxx", "BV1SvJd6sEEZ"],
        )

    def test_blocked_metadata_fetch_keeps_user_candidate_unverified(self):
        provider = FakeProvider(default_metadata=metadata_outcome("blocked", api_code=412))
        artifact = self._build(user_urls=["BV1SvJd6sEEZ"], provider=provider)
        candidate = artifact["candidates"][0]
        self.assertIsNone(candidate["view_count"])
        self.assertEqual(candidate["view_count_status"], "unavailable")
        self.assertEqual(candidate["retrieval_note"], "metadata_fetch_blocked")
        self.assertEqual(artifact["status"], "degraded")

    def test_excess_user_urls_are_rejected_not_silently_dropped(self):
        provider = FakeProvider()
        urls = [f"BV{i:010d}" for i in range(7)]
        artifact = self._build(user_urls=urls, provider=provider)
        self.assertEqual(len(artifact["candidates"]), 5)
        overflow = [r for r in artifact["rejected_user_urls"] if r["reason"] == "exceeds_max_candidates"]
        self.assertEqual(len(overflow), 2)

    def test_relevance_filter_and_verified_view_sorting(self):
        provider = FakeProvider(
            default_search=ok_search(
                search_item("BV1lo0000000", "为什么是太阳？旭日旗日本国名来龙去脉", views=1000000),
                search_item("BV1hi000000B", "莫斯科大学留学生披旭日旗被遣返", views=300),
                search_item("BV1hi000000A", "莫斯科留学生旭日旗事件最新进展", views=900),
                search_item("BV1hi000000C", "留学生旭日旗事件官方回应", views=500),
            ),
            metadata_by_bvid={
                "BV1hi000000A": ok_metadata("BV1hi000000A", views=9000),
                "BV1hi000000B": ok_metadata("BV1hi000000B", views=8000),
                "BV1hi000000C": ok_metadata("BV1hi000000C", views=700),
            },
        )
        artifact = self._build(provider=provider)
        bvids = [c["bvid"] for c in artifact["candidates"]]
        self.assertNotIn("BV1lo0000000", bvids)
        self.assertEqual(bvids, ["BV1hi000000A", "BV1hi000000B", "BV1hi000000C"])
        excluded = {(e["bvid"], e["reason"]) for e in artifact["search"]["excluded_preview"]}
        self.assertIn(("BV1lo0000000", "low_relevance"), excluded)
        self.assertEqual(artifact["candidates"][0]["view_count_status"], "verified")
        self.assertEqual(artifact["candidates"][0]["view_count"], 9000)

    def test_per_video_count_wins_over_stale_snippet(self):
        provider = FakeProvider(
            default_search=ok_search(search_item("BV1hi000000A", "莫斯科大学留学生旭日旗事件进展", views=100)),
            metadata_by_bvid={"BV1hi000000A": ok_metadata("BV1hi000000A", views=150)},
        )
        artifact = self._build(provider=provider)
        candidate = artifact["candidates"][0]
        self.assertEqual(candidate["view_count"], 150)
        self.assertEqual(candidate["view_count_source"], "per_video_api")
        self.assertEqual(candidate["search_snippet_view_count"], 100)

    def test_unverified_views_are_never_copied_from_snippet(self):
        provider = FakeProvider(
            default_search=ok_search(
                search_item("BV1v0000000A", "莫斯科大学留学生旭日旗事件进展", views=100),
                search_item("BV1v0000000B", "莫斯科留学生旭日旗事件后续", views=None),
            ),
            metadata_by_bvid={
                "BV1v0000000A": ok_metadata("BV1v0000000A", views=10),
                "BV1v0000000B": metadata_outcome("blocked", api_code=412),
            },
        )
        artifact = self._build(provider=provider)
        by_bvid = {c["bvid"]: c for c in artifact["candidates"]}
        unverified = by_bvid["BV1v0000000B"]
        self.assertIsNone(unverified["view_count"])
        self.assertEqual(unverified["view_count_status"], "unverified")
        self.assertEqual(unverified["view_count_source"], "none")
        # verified candidate ranks ahead of the unverified one even with a huge snippet
        self.assertEqual(artifact["candidates"][0]["bvid"], "BV1v0000000A")

    def test_verification_budget_is_bounded_and_recorded(self):
        items = [
            search_item(f"BV1bud00000{i}", f"莫斯科大学留学生旭日旗事件追踪{i:02d}", views=50 - i)
            for i in range(16)
        ]
        provider = FakeProvider(default_search=ok_search(*items))
        artifact = self._build(provider=provider)
        self.assertEqual(artifact["search"]["verification_budget"], 15)
        self.assertEqual(artifact["search"]["verification_performed"], 15)
        budget_excluded = [e for e in artifact["search"]["excluded_preview"]
                           if e["reason"] == "beyond_verification_budget"]
        self.assertEqual(len(budget_excluded), 1)
        self.assertEqual(len(artifact["candidates"]), 5)

    def test_zero_relevant_results_is_ok_and_never_padded(self):
        provider = FakeProvider(
            default_search=ok_search(
                search_item("BV1un0000000", "完全无关的美食视频", views=999999)
            )
        )
        artifact = self._build(provider=provider)
        self.assertEqual(artifact["status"], "ok")
        self.assertEqual(artifact["candidates"], [])
        self.assertIn("未强行凑数", artifact["action_note"])

    def test_all_blocked_without_user_urls_is_blocked_with_fallback_note(self):
        provider = FakeProvider(default_search=SearchOutcome(
            status="blocked", items=(), http_status=412, api_code=None, message=""
        ))
        artifact = self._build(provider=provider)
        self.assertEqual(artifact["status"], "blocked")
        self.assertEqual(artifact["candidates"], [])
        self.assertIn("--url", artifact["action_note"])

    def test_all_blocked_with_user_urls_is_degraded(self):
        provider = FakeProvider(
            default_search=SearchOutcome(
                status="blocked", items=(), http_status=412, api_code=None, message=""
            )
        )
        artifact = self._build(user_urls=["BV1SvJd6sEEZ"], provider=provider)
        self.assertEqual(artifact["status"], "degraded")
        self.assertEqual(len(artifact["candidates"]), 1)

    def test_partial_query_failure_is_degraded_with_counts(self):
        provider = FakeProvider(
            search_by_query={
                MOSCOW_TOPIC: SearchOutcome(
                    status="failed", items=(), http_status=503, api_code=None, message="boom"
                ),
                "莫斯科大学留学生旭日旗": ok_search(
                    search_item("BV1ok0000000", "莫斯科大学留学生旭日旗事件进展")
                ),
            },
        )
        artifact = self._build(provider=provider)
        self.assertEqual(artifact["status"], "degraded")
        query_statuses = {q["query"]: q["status"] for q in artifact["search"]["queries"]}
        self.assertEqual(query_statuses[MOSCOW_TOPIC], "failed")
        self.assertEqual(artifact["search"]["raw_result_count"], 1)
        self.assertEqual(artifact["search"]["deduplicated_count"], 1)

    def test_unavailable_search_item_is_dropped_from_candidates(self):
        provider = FakeProvider(
            default_search=ok_search(search_item("BV1gone00000", "莫斯科大学留学生旭日旗事件现场")),
            metadata_by_bvid={"BV1gone00000": metadata_outcome("unavailable")},
        )
        artifact = self._build(provider=provider)
        bvids = [c["bvid"] for c in artifact["candidates"]]
        self.assertNotIn("BV1gone00000", bvids)
        excluded = {e["bvid"]: e["reason"] for e in artifact["search"]["excluded_preview"]}
        self.assertEqual(excluded.get("BV1gone00000"), "unavailable_video")

    def test_coverage_and_disclaimer_fields(self):
        provider = FakeProvider(
            default_search=ok_search(*[
                search_item(f"BV1cv000000{ch}", f"莫斯科大学留学生旭日旗事件解读{ch}")
                for ch in "ABC"
            ])
        )
        artifact = self._build(provider=provider)
        self.assertEqual(artifact["artifact_version"], "1")
        self.assertTrue(artifact["candidate_set_id"].startswith("REF-"))
        joined = json.dumps(artifact, ensure_ascii=False)
        self.assertNotIn("全站", joined)
        self.assertIn("已检索", artifact["search"]["coverage_note"])
        self.assertTrue(artifact["limitations"])
        self.assertIn(artifact["provider"]["name"], ("bilibili_web_search",))
        self.assertIn("visitor_identity", artifact["provider"])

    def test_validate_rejects_tampered_artifacts(self):
        provider = FakeProvider(
            default_search=ok_search(
                search_item("BV1va000000A", "莫斯科大学留学生旭日旗事件现场")
            )
        )
        artifact = self._build(provider=provider)
        validate_reference_candidate_set(artifact)
        bad = json.loads(json.dumps(artifact))
        bad["status"] = "exploded"
        with self.assertRaises(ReferenceDiscoveryError):
            validate_reference_candidate_set(bad)
        bad = json.loads(json.dumps(artifact))
        bad["candidates"] = [dict(bad["candidates"][0], view_count_status="verified", view_count="很多")]
        with self.assertRaises(ReferenceDiscoveryError):
            validate_reference_candidate_set(bad)
        bad = json.loads(json.dumps(artifact))
        bad.pop("search")
        with self.assertRaises(ReferenceDiscoveryError):
            validate_reference_candidate_set(bad)

    def test_aliases_and_required_terms_flow_into_provider(self):
        provider = FakeProvider(
            search_by_query={
                "莫斯科大学 旭日旗 遣返": ok_search(
                    search_item("BV1al0000000", "遣返之后莫斯科大学留学生旭日旗风波继续")
                ),
            },
        )
        artifact = self._build(
            provider=provider, aliases=("莫斯科大学 旭日旗 遣返",), required_terms=("旭日旗",)
        )
        self.assertIn("莫斯科大学 旭日旗 遣返", [q["query"] for q in artifact["search"]["queries"]])


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


class ReferenceCliTests(unittest.TestCase):
    def _run_with_artifact(self, artifact, *extra):
        with mock.patch(
            "deeptalk_studio.bilibili_reference_provider.BilibiliReferenceProvider"
        ), mock.patch(
            "deeptalk_studio.reference_discovery.build_reference_candidate_set",
            return_value=artifact,
        ) as build:
            from deeptalk_studio.cli import main
            with tempfile.TemporaryDirectory() as tmp:
                code = main([
                    "discover-references", MOSCOW_TOPIC,
                    "--url", "BV1SvJd6sEEZ",
                    "--output", tmp,
                    *extra,
                ])
                self.assertEqual(
                    build.call_args.args, (MOSCOW_TOPIC, ["BV1SvJd6sEEZ"])
                )
                written = sorted(Path(tmp).glob("reference-candidate-set-*.json"))
                self.assertEqual(len(written), 1)
                payload = json.loads(written[0].read_text(encoding="utf-8"))
                self.assertEqual(payload, artifact)
                return code

    def test_cli_writes_artifact_and_prints_json(self):
        provider = FakeProvider(
            default_search=ok_search(search_item("BV1hi000000A", "莫斯科大学留学生旭日旗事件进展")),
        )
        artifact = build_reference_candidate_set(
            MOSCOW_TOPIC, ("BV1SvJd6sEEZ",), provider=provider,
            now="2026-10-20T12:00:00+00:00",
        )
        self.assertEqual(self._run_with_artifact(artifact, "--print-json"), 0)

    def test_cli_exit_code_two_when_no_candidates(self):
        provider = FakeProvider(
            default_search=SearchOutcome(
                status="blocked", items=(), http_status=412, api_code=None, message=""
            )
        )
        artifact = build_reference_candidate_set(
            MOSCOW_TOPIC, (), provider=provider, now="2026-10-20T12:00:00+00:00"
        )
        with mock.patch(
            "deeptalk_studio.bilibili_reference_provider.BilibiliReferenceProvider"
        ), mock.patch(
            "deeptalk_studio.reference_discovery.build_reference_candidate_set",
            return_value=artifact,
        ):
            from deeptalk_studio.cli import main
            with tempfile.TemporaryDirectory() as tmp:
                code = main(["discover-references", "主题", "--output", tmp])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
