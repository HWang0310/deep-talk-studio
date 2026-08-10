import json
import unittest
from urllib.error import HTTPError

from deeptalk_studio.providers.openai import OpenAIProviderError, OpenAIResponsesProvider
from deeptalk_studio.schema import (
    API_RESEARCH_DRAFT_JSON_SCHEMA,
    FACT_CHECK_JSON_SCHEMA,
    REPORT_JSON_SCHEMA,
)
from tests.fixtures import valid_api_research_draft_input, valid_fact_check_data, valid_report_data


def api_response():
    return {
        "output": [
            {
                "type": "web_search_call",
                "id": "ws_123",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ["示例公共事件"],
                    "sources": [
                        {"type": "url", "url": "https://example.com/official"},
                        {"type": "url", "url": "https://example.org/report"},
                    ],
                },
            },
            {
                "type": "message",
                "id": "msg_123",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(valid_api_research_draft_input(), ensure_ascii=False),
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://example.org/report",
                                "title": "媒体核查报道",
                                "start_index": 12,
                                "end_index": 30,
                            }
                        ],
                    }
                ],
            },
        ]
    }


class OpenAIProviderTests(unittest.TestCase):
    def test_provider_preserves_web_search_calls_sources_and_annotations(self):
        captured = {}

        def transport(url, headers, body, timeout):
            captured.update(url=url, headers=headers, body=body, timeout=timeout)
            return api_response()

        provider = OpenAIResponsesProvider(api_key="secret-value", transport=transport)
        result = provider.research("示例公共事件", API_RESEARCH_DRAFT_JSON_SCHEMA)

        payload = captured["body"]
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(payload["tools"], [{"type": "web_search"}])
        self.assertEqual(payload["include"], ["web_search_call.action.sources"])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertNotIn("secret-value", json.dumps(payload))
        self.assertEqual(result.data["topic"], "示例公共事件")
        self.assertEqual(result.provenance.search_calls[0].call_id, "ws_123")
        self.assertEqual(
            result.provenance.search_calls[0].source_urls,
            ("https://example.com/official", "https://example.org/report"),
        )
        self.assertEqual(result.provenance.citations[0].url, "https://example.org/report")

    def test_fact_check_is_a_separate_web_search_call_with_its_own_schema(self):
        captured = []

        def transport(url, headers, body, timeout):
            captured.append(body)
            response = api_response()
            response["output"][1]["content"][0]["text"] = json.dumps(
                valid_fact_check_data(), ensure_ascii=False
            )
            return response

        provider = OpenAIResponsesProvider(api_key="secret-value", transport=transport)
        result = provider.fact_check(valid_report_data(), FACT_CHECK_JSON_SCHEMA)

        self.assertEqual(len(captured), 1)
        self.assertEqual(
            captured[0]["text"]["format"]["name"], "deep_talk_fact_check_artifact"
        )
        self.assertIn("独立事实核查", captured[0]["input"][0]["content"])
        self.assertEqual(captured[0]["include"], ["web_search_call.action.sources"])
        self.assertEqual(result.data["artifact_version"], "0.2")

    def test_api_payload_removes_schema_keywords_unsupported_by_structured_outputs(self):
        captured = {}

        def transport(url, headers, body, timeout):
            captured["body"] = body
            return api_response()

        provider = OpenAIResponsesProvider(api_key="secret-value", transport=transport)
        provider.research("示例公共事件", REPORT_JSON_SCHEMA)

        self.assertIn("uniqueItems", json.dumps(REPORT_JSON_SCHEMA))
        self.assertNotIn(
            "uniqueItems", json.dumps(captured["body"]["text"]["format"]["schema"])
        )

    def test_api_research_schema_excludes_machine_owned_metadata(self):
        top_level = API_RESEARCH_DRAFT_JSON_SCHEMA["properties"]
        for field in (
            "report_id",
            "revision",
            "previous_revision",
            "created_at",
            "generated_at",
            "status",
            "fact_check",
            "quality_summary",
            "approval_gate",
        ):
            self.assertNotIn(field, top_level)

        source = top_level["sources"]["items"]["properties"]
        for field in (
            "normalized_url",
            "inspection_method",
            "provenance_method",
            "provenance_status",
            "provenance_refs",
            "independence_group",
        ):
            self.assertNotIn(field, source)
        self.assertNotIn(
            "verification_status", top_level["claims"]["items"]["properties"]
        )
        evidence = top_level["evidence_links"]["items"]["properties"]
        self.assertNotIn("independence_group", evidence)
        self.assertNotIn("verified_in_review", evidence)

    def test_api_errors_do_not_leak_key(self):
        def failing_transport(url, headers, body, timeout):
            raise HTTPError(url, 401, "bad secret-value", {}, None)

        provider = OpenAIResponsesProvider(api_key="secret-value", transport=failing_transport)

        with self.assertRaises(OpenAIProviderError) as raised:
            provider.research("示例公共事件", REPORT_JSON_SCHEMA)

        self.assertNotIn("secret-value", str(raised.exception))

    def test_malformed_api_output_has_user_readable_error(self):
        provider = OpenAIResponsesProvider(
            api_key="secret-value", transport=lambda *args: {"output": [{"type": "message"}]}
        )

        with self.assertRaisesRegex(OpenAIProviderError, "Research Report"):
            provider.research("示例公共事件", REPORT_JSON_SCHEMA)


if __name__ == "__main__":
    unittest.main()
