"""Small, explicit client for DeepSeek's billed Search and Fetch tools.

The workbench never calls this client implicitly from research generation.  A
flow must first record a user opt-in and a per-run request cap.  Transport is
injectable so all repository tests stay offline.
"""

import json
import socket
from typing import Any, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


ToolTransport = Callable[[str, Dict[str, str], Dict[str, Any], int], Dict[str, Any]]
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class DeepSeekToolError(RuntimeError):
    def __init__(self, message: str, *, category: str = "provider_error", http_status: Optional[int] = None):
        super().__init__(message)
        self.category = category
        self.http_status = http_status


def _default_transport(url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("response too large")
        return json.loads(raw.decode("utf-8"))


class DeepSeekSearchFetchClient:
    SEARCH_PATH = "/v1/tools/search"
    FETCH_PATH = "/v1/tools/fetch"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.deepseek.com",
        timeout: int = 600,
        transport: Optional[ToolTransport] = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise DeepSeekToolError("DeepSeek API Key 不能为空", category="missing_key")
        base = str(base_url or "").strip().rstrip("/")
        parsed_base = urlparse(base)
        if parsed_base.scheme not in {"https", "http"} or not parsed_base.netloc or parsed_base.username or parsed_base.password:
            raise DeepSeekToolError("DeepSeek 服务地址必须是 http(s)", category="invalid_endpoint")
        self._api_key = api_key.strip()
        self.base_url = base
        self.timeout = int(timeout)
        self.transport = transport or _default_transport

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = self.base_url + path
        headers = {
            "Authorization": "Bearer " + self._api_key,
            "Content-Type": "application/json",
        }
        try:
            response = self.transport(endpoint, headers, payload, self.timeout)
        except HTTPError as exc:
            category = {
                401: "unauthorized",
                402: "payment_required",
                403: "forbidden",
                429: "rate_limited",
            }.get(exc.code, "http_error")
            hints = {
                "unauthorized": "API Key 无效或已过期",
                "payment_required": "账户余额或计费状态不允许本次请求",
                "forbidden": "服务拒绝访问，请检查权限",
                "rate_limited": "请求过于频繁，请稍后重试",
                "http_error": "请检查 DeepSeek 服务状态和请求参数",
            }
            raise DeepSeekToolError(
                f"DeepSeek 工具返回 HTTP {exc.code}：{hints[category]}",
                category=category,
                http_status=exc.code,
            ) from None
        except (TimeoutError, socket.timeout):
            raise DeepSeekToolError("DeepSeek 工具请求超时，请检查网络或预算", category="timeout") from None
        except URLError as exc:
            if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                raise DeepSeekToolError("DeepSeek 工具请求超时，请检查网络或预算", category="timeout") from None
            raise DeepSeekToolError("无法连接 DeepSeek 工具服务", category="network") from None
        except (ValueError, TypeError):
            raise DeepSeekToolError("DeepSeek 工具返回了无法解析的响应", category="invalid_response") from None
        if not isinstance(response, dict):
            raise DeepSeekToolError("DeepSeek 工具响应不是 JSON 对象", category="invalid_response")
        return response

    @staticmethod
    def _request_id(response: Dict[str, Any]) -> str:
        value = response.get("id") or response.get("request_id") or ""
        return str(value)[:200]

    def search(self, query: str, count: int = 5, need_content: bool = False) -> Dict[str, Any]:
        query = str(query or "").strip()
        if not query or len(query) > 500:
            raise DeepSeekToolError("检索问题不能为空且不能超过 500 字", category="invalid_request")
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 50:
            raise DeepSeekToolError("Search 返回数量必须在 1–50 之间", category="invalid_request")
        response = self._post(
            self.SEARCH_PATH,
            {"query": query, "count": count, "need_content": bool(need_content)},
        )
        raw_results = response.get("data", response.get("results"))
        if not isinstance(raw_results, list):
            raise DeepSeekToolError("DeepSeek Search 响应缺少结果列表", category="invalid_response")
        results: List[Dict[str, Any]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
                continue
            results.append(
                {
                    "title": str(item.get("title", ""))[:300],
                    "url": url,
                    "content": str(item.get("content", "")),
                    "published_at": str(item.get("publication_date", item.get("published_at", "")))[:80],
                    "icon": str(item.get("icon", ""))[:500],
                }
            )
        return {"request_id": self._request_id(response), "results": results}

    def fetch(self, url: str) -> Dict[str, Any]:
        url = str(url or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise DeepSeekToolError("Fetch 只接受不含凭据的 http(s) 原文链接", category="invalid_request")
        response = self._post(self.FETCH_PATH, {"url": url})
        raw = response.get("data", response)
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        if not isinstance(raw, dict):
            raise DeepSeekToolError("DeepSeek Fetch 响应缺少正文", category="invalid_response")
        content = raw.get("content", raw.get("text", ""))
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekToolError("DeepSeek Fetch 未返回可核验正文", category="invalid_response")
        return {
            "request_id": self._request_id(response),
            "url": str(raw.get("url", url)),
            "title": str(raw.get("title", url))[:300],
            "content": content,
            "published_at": str(raw.get("publication_date", raw.get("published_at", "")))[:80],
        }
