import json
import unittest
from urllib.error import HTTPError

from deeptalk_studio.providers.openai import OpenAIProviderError, OpenAIResponsesProvider
from deeptalk_studio.schema import REPORT_JSON_SCHEMA
from tests.fixtures import valid_report_data


class OpenAIProviderTests(unittest.TestCase):
    def test_provider_uses_web_search_and_structured_output(self):
        captured = {}

        def transport(url, headers, body, timeout):
            captured.update(url=url, headers=headers, body=body, timeout=timeout)
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(valid_report_data(), ensure_ascii=False),
                            }
                        ],
                    }
                ]
            }

        provider = OpenAIResponsesProvider(api_key="secret-value", transport=transport)
        result = provider.research("示例公共事件", REPORT_JSON_SCHEMA)

        payload = captured["body"]
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(payload["tools"], [{"type": "web_search"}])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertNotIn("secret-value", json.dumps(payload))
        self.assertEqual(result["topic"], "示例公共事件")

    def test_api_errors_do_not_leak_key(self):
        def failing_transport(url, headers, body, timeout):
            raise HTTPError(url, 401, "bad secret-value", {}, None)

        provider = OpenAIResponsesProvider(api_key="secret-value", transport=failing_transport)

        with self.assertRaises(OpenAIProviderError) as raised:
            provider.research("示例公共事件", REPORT_JSON_SCHEMA)

        self.assertNotIn("secret-value", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

