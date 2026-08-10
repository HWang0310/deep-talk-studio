import json
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..prompt import SYSTEM_PROMPT, build_user_prompt


Transport = Callable[[str, Dict[str, str], Dict[str, Any], int], Dict[str, Any]]


class OpenAIProviderError(RuntimeError):
    pass


def _default_transport(
    url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: int
) -> Dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OpenAIResponsesProvider:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.5",
        timeout: int = 600,
        transport: Optional[Transport] = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key 不能为空")
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport or _default_transport

    def research(self, topic: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "reasoning": {"effort": "high"},
            "tools": [{"type": "web_search"}],
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(topic)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "deep_talk_research_report",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.transport(self.endpoint, headers, payload, self.timeout)
            output_text = self._extract_output_text(response)
            return json.loads(output_text)
        except HTTPError as exc:
            raise OpenAIProviderError(f"OpenAI API 请求失败（HTTP {exc.code}）") from None
        except URLError as exc:
            raise OpenAIProviderError("无法连接 OpenAI API，请检查网络后重试") from None
        except json.JSONDecodeError:
            raise OpenAIProviderError("OpenAI 返回了无法解析的结构化报告") from None
        except (KeyError, TypeError, ValueError):
            raise OpenAIProviderError("OpenAI 返回结果缺少 Research Report 内容") from None

    @staticmethod
    def _extract_output_text(response: Dict[str, Any]) -> str:
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return content["text"]
        raise ValueError("missing output_text")

