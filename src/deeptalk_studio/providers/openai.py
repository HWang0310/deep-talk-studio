import json
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..prompt import (
    DISCOVERY_SYSTEM_PROMPT,
    FACT_CHECK_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_discovery_prompt,
    build_fact_check_prompt,
    build_user_prompt,
)
from ..provenance import extract_provenance
from ..provenance import ProviderProvenance
from ..material_prompt import (
    MATERIAL_REVIEW_SYSTEM_PROMPT,
    MATERIAL_SEARCH_SYSTEM_PROMPT,
    build_material_review_prompt,
    build_material_search_prompt,
)
from ..script_prompt import (
    SCRIPT_REVIEWER_SYSTEM_PROMPT,
    SCRIPT_WRITER_SYSTEM_PROMPT,
    build_script_review_prompt,
    build_script_writer_prompt,
)
from .base import ProviderResult


Transport = Callable[[str, Dict[str, str], Dict[str, Any], int], Dict[str, Any]]


class OpenAIProviderError(RuntimeError):
    pass


def _structured_output_schema(value: Any) -> Any:
    """Return the OpenAI-supported subset without weakening local validation.

    Structured Outputs does not support JSON Schema's ``uniqueItems`` keyword.
    The complete project schema is still executed locally after model output.
    """

    if isinstance(value, dict):
        return {
            key: _structured_output_schema(item)
            for key, item in value.items()
            if key != "uniqueItems"
        }
    if isinstance(value, list):
        return [_structured_output_schema(item) for item in value]
    return value


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
        model: str = "gpt-5.6",
        timeout: int = 600,
        transport: Optional[Transport] = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key 不能为空")
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport or _default_transport

    def research(
        self, topic: str, schema: Dict[str, Any], research_handoff: Optional[Dict[str, Any]] = None
    ) -> ProviderResult:
        return self._run_structured_search(
            SYSTEM_PROMPT,
            build_user_prompt(topic, research_handoff),
            schema,
            "deep_talk_research_report",
        )

    def discover(self, query: str, schema: Dict[str, Any]) -> ProviderResult:
        return self._run_structured_search(
            DISCOVERY_SYSTEM_PROMPT,
            build_discovery_prompt(query),
            schema,
            "deep_talk_topic_discovery",
        )

    def fact_check(self, report: Dict[str, Any], schema: Dict[str, Any]) -> ProviderResult:
        return self._run_structured_search(
            FACT_CHECK_SYSTEM_PROMPT,
            build_fact_check_prompt(report),
            schema,
            "deep_talk_fact_check_artifact",
        )

    def write_script(
        self,
        report: Dict[str, Any],
        profile: Dict[str, Any],
        target_duration_minutes: float,
        schema: Dict[str, Any],
    ) -> ProviderResult:
        return self._run_structured_generation(
            SCRIPT_WRITER_SYSTEM_PROMPT,
            build_script_writer_prompt(report, profile, target_duration_minutes),
            schema,
            "deep_talk_script_draft",
        )

    def review_script(
        self,
        report: Dict[str, Any],
        script: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> ProviderResult:
        return self._run_structured_generation(
            SCRIPT_REVIEWER_SYSTEM_PROMPT,
            build_script_review_prompt(report, script),
            schema,
            "deep_talk_script_review",
        )

    def search_materials(
        self, script: Dict[str, Any], report: Dict[str, Any],
        profile: Dict[str, Any], schema: Dict[str, Any],
    ) -> ProviderResult:
        return self._run_structured_search(
            MATERIAL_SEARCH_SYSTEM_PROMPT,
            build_material_search_prompt(script, report, profile),
            schema,
            "deep_talk_material_search",
        )

    def review_materials(
        self, package: Dict[str, Any], script: Dict[str, Any],
        report: Dict[str, Any], schema: Dict[str, Any],
    ) -> ProviderResult:
        return self._run_structured_generation(
            MATERIAL_REVIEW_SYSTEM_PROMPT,
            build_material_review_prompt(package, script, report),
            schema,
            "deep_talk_material_review",
        )

    def _run_structured_generation(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        schema_name: str,
    ) -> ProviderResult:
        payload = {
            "model": self.model,
            "reasoning": {"effort": "high"},
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": _structured_output_schema(schema),
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.transport(self.endpoint, headers, payload, self.timeout)
            return ProviderResult(
                data=json.loads(self._extract_output_text(response)),
                provenance=ProviderProvenance(search_calls=(), citations=()),
            )
        except HTTPError as exc:
            raise OpenAIProviderError(f"OpenAI API 请求失败（HTTP {exc.code}）") from None
        except URLError:
            raise OpenAIProviderError("无法连接 OpenAI API，请检查网络后重试") from None
        except json.JSONDecodeError:
            raise OpenAIProviderError("OpenAI 返回了无法解析的结构化稿件") from None
        except (KeyError, TypeError, ValueError):
            raise OpenAIProviderError("OpenAI 返回结果缺少 Script 内容") from None

    def _run_structured_search(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        schema_name: str,
    ) -> ProviderResult:
        payload = {
            "model": self.model,
            "reasoning": {"effort": "high"},
            "tools": [{"type": "web_search"}],
            "include": ["web_search_call.action.sources"],
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": _structured_output_schema(schema),
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
            return ProviderResult(
                data=json.loads(output_text),
                provenance=extract_provenance(response),
            )
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
