"""Workbench LLM boundary: one uniform interface over two provider modes.

- ``responses``: the product's existing ``OpenAIResponsesProvider`` (Responses
  API + optional built-in web_search provenance), pointed at the user's own
  endpoint.
- ``chat``: a minimal, dependency-free OpenAI-compatible ``chat/completions``
  client for generic providers; JSON is parsed locally and every answer is
  schema-validated before it reaches any engine (no silent leniency).

Neither mode ever logs the API key; errors carry model-answer tails only.
"""

import json
import re
import socket
from typing import Any, Callable, Dict, List, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..providers.base import ProviderResult
from ..providers.openai import OpenAIProviderError, OpenAIResponsesProvider
from ..prompt import FACT_CHECK_SYSTEM_PROMPT, SYSTEM_PROMPT
from ..schema import (
    API_RESEARCH_DRAFT_JSON_SCHEMA,
    FACT_CHECK_JSON_SCHEMA,
)
from ..thesis_prompt import (
    REFERENCE_SUMMARY_SYSTEM_PROMPT as _REF_SUMMARY_PROMPT,
    build_reference_summary_prompt,
    build_thesis_review_prompt,
    build_thesis_writer_prompt,
)
from ..thesis_prompt import (
    THESIS_REVIEWER_SYSTEM_PROMPT,
    THESIS_WRITER_SYSTEM_PROMPT,
)
from ..validation import ReportValidationError, validate_json_schema
from .prompts import (
    WORKBENCH_RESEARCH_SYSTEM_PROMPT,
    build_workbench_fact_check_user_prompt,
    build_workbench_research_user_prompt,
)
from ..provenance import ProviderProvenance

ChatTransport = Callable[[str, Dict[str, str], Dict[str, Any], int], Dict[str, Any]]


class WorkbenchLLMError(RuntimeError):
    """A workbench LLM call failed (never includes the API key)."""

    def __init__(
        self,
        message: str,
        *,
        category: str = "provider_error",
        http_status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.http_status = http_status


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return cleaned


def _default_chat_transport(url, headers, body, timeout):
    request = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _default_chat_stream_transport(url, headers, body, timeout):
    """真实 SSE 流式传输：上游 stream:true，逐行解析 data: 增量。

    只产出文本增量（delta.content），错误由调用方映射；生成器被关闭时
    通过 finally 关闭上游响应，停止继续计费。
    """

    request = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    response = urlopen(request, timeout=timeout)
    try:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            text = delta.get("content")
            if text:
                yield text
    finally:
        response.close()


class ChatCompletionsProvider:
    """Minimal OpenAI-compatible client for generic chat providers."""

    def __init__(
        self,
        api_key: str,
        model: str,
        chat_base_url: str,
        timeout: int = 600,
        transport: Optional[ChatTransport] = None,
        stream_transport=None,
    ) -> None:
        if not api_key.strip():
            raise WorkbenchLLMError("API Key 不能为空")
        if not model.strip():
            raise WorkbenchLLMError("模型名不能为空")
        base = chat_base_url.rstrip("/")
        self.endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport or _default_chat_transport
        self.stream_transport = stream_transport or _default_chat_stream_transport

    def _complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.transport(self.endpoint, headers, payload, self.timeout)
        except HTTPError as exc:
            category = {
                401: "unauthorized",
                402: "payment_required",
                403: "forbidden",
                429: "rate_limited",
            }.get(exc.code, "http_error")
            hints = {
                "unauthorized": "API Key 无效或已过期，请在设置中替换",
                "payment_required": "账户余额或计费状态不允许本次请求，请检查预算",
                "forbidden": "服务拒绝访问，请检查模型权限或端点",
                "rate_limited": "请求过于频繁，请稍后重试或降低并发",
                "http_error": "请检查地址、Key 与模型名",
            }
            raise WorkbenchLLMError(
                f"模型服务返回 HTTP {exc.code}：{hints[category]}",
                category=category,
                http_status=exc.code,
            ) from None
        except (TimeoutError, socket.timeout):
            raise WorkbenchLLMError(
                "模型服务连接超时，请检查网络或调高超时设置", category="timeout"
            ) from None
        except URLError as exc:
            if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                raise WorkbenchLLMError(
                    "模型服务连接超时，请检查网络或调高超时设置", category="timeout"
                ) from None
            raise WorkbenchLLMError(
                "无法连接模型服务，请检查网络或服务地址", category="network"
            ) from None
        except (ValueError, KeyError, TypeError):
            raise WorkbenchLLMError(
                "模型服务返回了无法解析的响应", category="invalid_response"
            ) from None
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise WorkbenchLLMError(
                "模型服务响应缺少对话内容", category="invalid_response"
            ) from None
        if not isinstance(content, str) or not content.strip():
            raise WorkbenchLLMError("模型服务返回了空内容", category="empty_response")
        return content

    def ping(self) -> None:
        answer = self._complete("你是连通性测试助手。", "请只回复两个字：正常")
        if "正常" not in answer[:40]:
            raise WorkbenchLLMError(
                "模型连通性测试未返回预期内容", category="unexpected_response"
            )

    def chat_stream(self, messages):
        """真实流式对话：上游 stream:true，yield 文本增量。

        这是真实 provider 流式（非打字机模拟）；生成器提前关闭（用户停止）
        会关闭上游响应，不继续产生费用。
        """

        payload = {
            "model": self.model,
            "messages": [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
            "stream": True,
            "temperature": 0.7,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        return self._stream_request(headers, payload)

    def _stream_request(self, headers, payload):
        try:
            for delta in self.stream_transport(self.endpoint, headers, payload, self.timeout):
                yield delta
        except HTTPError as exc:
            category = {
                401: "unauthorized",
                402: "payment_required",
                403: "forbidden",
                429: "rate_limited",
            }.get(exc.code, "http_error")
            hints = {
                "unauthorized": "API Key 无效或已过期，请在设置中替换",
                "payment_required": "账户余额或计费状态不允许本次请求，请检查预算",
                "forbidden": "服务拒绝访问，请检查模型权限或端点",
                "rate_limited": "请求过于频繁，请稍后重试或降低并发",
                "http_error": "请检查地址、Key 与模型名",
            }
            raise WorkbenchLLMError(
                f"模型服务返回 HTTP {exc.code}：{hints[category]}",
                category=category,
                http_status=exc.code,
            ) from None
        except (TimeoutError, socket.timeout):
            raise WorkbenchLLMError(
                "模型服务连接超时，请检查网络或调高超时设置", category="timeout"
            ) from None
        except URLError as exc:
            if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                raise WorkbenchLLMError(
                    "模型服务连接超时，请检查网络或调高超时设置", category="timeout"
                ) from None
            raise WorkbenchLLMError(
                "无法连接模型服务，请检查网络或服务地址", category="network"
            ) from None
        except WorkbenchLLMError:
            raise
        except (ValueError, KeyError, TypeError):
            raise WorkbenchLLMError(
                "模型服务返回了无法解析的流式响应", category="invalid_response"
            ) from None

    @staticmethod
    def _validated(text: str, schema: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        try:
            data = json.loads(_strip_code_fence(text))
        except ValueError:
            raise WorkbenchLLMError(
                f"模型没有返回合法 JSON（{schema_name}），请重试或更换模型"
            ) from None
        try:
            validate_json_schema(data, schema, schema_name)
        except ReportValidationError as exc:
            raise WorkbenchLLMError(f"模型输出不符合 {schema_name} 结构：{exc}") from None
        return data

    def _generation(self, system_prompt, user_prompt, schema, schema_name):
        text = self._complete(system_prompt, user_prompt)
        return ProviderResult(
            data=self._validated(text, schema, schema_name),
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )


class WorkbenchLLM:
    """Uniform boundary used by ``workbench.flow`` for both modes."""

    def __init__(self, settings: Mapping[str, Any], *, chat_transport=None, chat_stream_transport=None) -> None:
        self.mode = settings["provider_mode"]
        self.timeout = int(settings["timeout_seconds"])
        self._settings = dict(settings)
        if self.mode == "responses":
            self._responses = OpenAIResponsesProvider(
                api_key=settings["api_key"],
                model=settings["model"],
                timeout=self.timeout,
                endpoint=settings["base_url"],
            )
            self._chat = None
        else:
            self._responses = None
            self._chat = ChatCompletionsProvider(
                api_key=settings["api_key"],
                model=settings["model"],
                chat_base_url=settings["chat_base_url"],
                timeout=self.timeout,
                transport=chat_transport,
                stream_transport=chat_stream_transport,
            )

    def chat_stream(self, messages):
        """真实 provider 流式自由聊天（stream:true SSE），逐段产出文本增量。

        responses 模式暂不支持聊天流式（MVP 基于 chat/completions）；
        用户需要自由聊天时引导切换到 DeepSeek 或通用 Chat 模式。
        """

        if self.mode == "responses" or self._chat is None:
            raise WorkbenchLLMError(
                "Responses 模式暂不支持自由聊天，请在「大模型设置」切换到 DeepSeek 或通用 Chat",
                category="unsupported_mode",
            )
        return self._chat.chat_stream(messages)

    # -- research / fact check (may search the web in responses mode) -------

    def research(
        self,
        topic: str,
        research_question: str,
        sources: List[Mapping[str, Any]],
        reference_insights: Optional[List[Mapping[str, Any]]] = None,
    ) -> ProviderResult:
        user_prompt = build_workbench_research_user_prompt(
            topic, research_question, sources, reference_insights
        )
        if self.mode == "responses":
            return self._run(
                WORKBENCH_RESEARCH_SYSTEM_PROMPT,
                user_prompt,
                API_RESEARCH_DRAFT_JSON_SCHEMA,
                "api_research_draft",
                web_search=True,
            )
        return self._chat._generation(
            WORKBENCH_RESEARCH_SYSTEM_PROMPT,
            user_prompt,
            API_RESEARCH_DRAFT_JSON_SCHEMA,
            "api_research_draft",
        )

    def fact_check(self, report: Mapping[str, Any], sources: List[Mapping[str, Any]]) -> ProviderResult:
        user_prompt = build_workbench_fact_check_user_prompt(report, sources)
        if self.mode == "responses":
            return self._run(
                FACT_CHECK_SYSTEM_PROMPT,
                user_prompt,
                FACT_CHECK_JSON_SCHEMA,
                "deep_talk_fact_check_artifact",
                web_search=True,
            )
        return self._chat._generation(
            FACT_CHECK_SYSTEM_PROMPT,
            user_prompt,
            FACT_CHECK_JSON_SCHEMA,
            "deep_talk_fact_check_artifact",
        )

    # -- script steps (no web search, originality preserved) ----------------

    def write_script(
        self,
        report: Mapping[str, Any],
        profile: Mapping[str, Any],
        target_duration_minutes: Optional[float],
        schema: Dict[str, Any],
    ) -> ProviderResult:
        from ..script_prompt import (
            SCRIPT_WRITER_SYSTEM_PROMPT,
            build_script_writer_prompt,
        )

        return self._run(
            SCRIPT_WRITER_SYSTEM_PROMPT,
            build_script_writer_prompt(report, profile, target_duration_minutes),
            schema,
            "deep_talk_script_draft",
        )

    def review_script(
        self, report: Mapping[str, Any], script: Mapping[str, Any], schema: Dict[str, Any]
    ) -> ProviderResult:
        from ..script_prompt import (
            SCRIPT_REVIEWER_SYSTEM_PROMPT,
            build_script_review_prompt,
        )

        return self._run(
            SCRIPT_REVIEWER_SYSTEM_PROMPT,
            build_script_review_prompt(report, script),
            schema,
            "deep_talk_script_review",
        )

    def write_thesis(
        self, report: Mapping[str, Any], narrative_insights: Optional[List[Mapping[str, Any]]]
    ) -> ProviderResult:
        from ..schema import THESIS_CONTENT_JSON_SCHEMA

        return self._run(
            THESIS_WRITER_SYSTEM_PROMPT,
            build_thesis_writer_prompt(report, narrative_insights),
            THESIS_CONTENT_JSON_SCHEMA,
            "deep_talk_thesis_content",
        )

    def review_thesis(
        self, report: Mapping[str, Any], card_content: Mapping[str, Any], check_names: List[str]
    ) -> ProviderResult:
        from ..schema import THESIS_REVIEW_CONTENT_JSON_SCHEMA

        return self._run(
            THESIS_REVIEWER_SYSTEM_PROMPT,
            build_thesis_review_prompt(report, card_content, check_names),
            THESIS_REVIEW_CONTENT_JSON_SCHEMA,
            "deep_talk_thesis_review",
        )

    def summarize_reference(
        self,
        transcript_text: str,
        metrics: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> ProviderResult:
        from ..schema import REFERENCE_NARRATIVE_JSON_SCHEMA

        return self._run(
            _REF_SUMMARY_PROMPT,
            build_reference_summary_prompt(transcript_text, metrics, metadata),
            REFERENCE_NARRATIVE_JSON_SCHEMA,
            "deep_talk_reference_summary",
        )

    # -- connection test -----------------------------------------------------

    def ping(self) -> None:
        if self.mode in {"chat", "deepseek"}:
            self._chat.ping()
            return
        try:
            result = self._responses.run_structured(
                "你是连通性测试助手。",
                "请只返回 JSON：{\"status\":\"正常\"}",
                {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"], "additionalProperties": False},
                "deep_talk_ping",
            )
        except OpenAIProviderError as exc:
            raise WorkbenchLLMError(str(exc)) from None
        if not isinstance(result.data, dict) or not result.data:
            raise WorkbenchLLMError("模型连通性测试未返回有效内容")

    # -- internals -----------------------------------------------------------

    def _run(self, system_prompt, user_prompt, schema, schema_name, *, web_search=False):
        if self.mode == "responses":
            try:
                return self._responses.run_structured(
                    system_prompt, user_prompt, schema, schema_name, web_search=web_search
                )
            except OpenAIProviderError as exc:
                raise WorkbenchLLMError(str(exc)) from None
        return self._chat._generation(system_prompt, user_prompt, schema, schema_name)


def build_llm(
    settings: Mapping[str, Any],
    *,
    chat_transport=None,
    chat_stream_transport=None,
) -> WorkbenchLLM:
    return WorkbenchLLM(
        settings,
        chat_transport=chat_transport,
        chat_stream_transport=chat_stream_transport,
    )
