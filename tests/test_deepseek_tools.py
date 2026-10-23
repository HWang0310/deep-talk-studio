import json
import unittest
from urllib.error import HTTPError

from deeptalk_studio.workbench.deepseek_tools import (
    DeepSeekSearchFetchClient,
    DeepSeekToolError,
)


class DeepSeekToolClientTests(unittest.TestCase):
    def test_search_uses_official_path_and_normalizes_results_without_key_leak(self):
        calls = []

        def transport(url, headers, body, timeout):
            calls.append((url, headers, body, timeout))
            return {
                "id": "req-search-1",
                "data": [
                    {
                        "title": "独立报道",
                        "url": "https://news.example/report",
                        "content": "原文内容",
                        "publication_date": "2026-10-20",
                    }
                ],
            }

        secret = "sk-never-return"
        client = DeepSeekSearchFetchClient(
            secret, base_url="https://api.deepseek.com", transport=transport
        )
        result = client.search("测试问题", count=3, need_content=True)
        self.assertEqual(calls[0][0], "https://api.deepseek.com/v1/tools/search")
        self.assertEqual(calls[0][1]["Authorization"], "Bearer " + secret)
        self.assertEqual(calls[0][2], {"query": "测试问题", "count": 3, "need_content": True})
        self.assertEqual(result["request_id"], "req-search-1")
        self.assertEqual(result["results"][0]["url"], "https://news.example/report")
        self.assertNotIn(secret, json.dumps(result))

    def test_fetch_uses_official_path_and_requires_http_url(self):
        calls = []

        def transport(url, headers, body, timeout):
            calls.append((url, body))
            return {"id": "req-fetch-1", "data": {"title": "标题", "url": body["url"], "content": "正文"}}

        client = DeepSeekSearchFetchClient("sk-test", transport=transport)
        result = client.fetch("https://news.example/report")
        self.assertEqual(calls[0][0], "https://api.deepseek.com/v1/tools/fetch")
        self.assertEqual(calls[0][1], {"url": "https://news.example/report"})
        self.assertEqual(result["content"], "正文")
        with self.assertRaises(DeepSeekToolError):
            client.fetch("file:///etc/passwd")

    def test_http_and_timeout_errors_are_typed_and_secret_free(self):
        secret = "sk-secret"

        def denied(url, headers, body, timeout):
            raise HTTPError(url, 402, "payment", {}, None)

        client = DeepSeekSearchFetchClient(secret, transport=denied)
        with self.assertRaises(DeepSeekToolError) as ctx:
            client.search("问题")
        self.assertEqual(ctx.exception.http_status, 402)
        self.assertEqual(ctx.exception.category, "payment_required")
        self.assertNotIn(secret, str(ctx.exception))

        def timed_out(url, headers, body, timeout):
            raise TimeoutError("timeout")

        client = DeepSeekSearchFetchClient(secret, transport=timed_out)
        with self.assertRaises(DeepSeekToolError) as ctx:
            client.fetch("https://news.example/report")
        self.assertEqual(ctx.exception.category, "timeout")

    def test_malformed_response_is_rejected(self):
        client = DeepSeekSearchFetchClient(
            "sk-test", transport=lambda url, headers, body, timeout: {"data": "not-a-list"}
        )
        with self.assertRaises(DeepSeekToolError) as ctx:
            client.search("问题")
        self.assertEqual(ctx.exception.category, "invalid_response")


if __name__ == "__main__":
    unittest.main()
