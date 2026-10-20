"""Anonymous Bilibili search/metadata provider for Phase 1 reference discovery.

Design constraints (Issue #24):

- Transport is injectable so every offline test is deterministic; the default
  transport is a plain, cookie-jar-free ``urllib`` call.
- The optional visitor identity comes from Bilibili's own public
  visitor-initialization endpoint (the same call a fresh, non-logged-in
  browser performs on first visit). It is an anonymous, account-unlinked
  identifier: kept in memory only, never logged, never persisted into
  artifacts or files. Reading the user's browser profile or cookies is not
  supported. If the bootstrap call itself is risk-controlled, the provider
  latches and the run stops before any search or metadata request; benign
  bootstrap failures degrade silently and the run continues without an
  identity.
- HTTP 412 / 403 / 429 and non-JSON HTML error pages are reported as
  ``blocked``. Blocked outcomes are never retried and never bypassed — no
  signing, no captcha solving, no credential use.
- Only genuine transient failures (transport errors, 5xx) are retried a
  bounded number of times with backoff; every request is rate-limited by
  ``request_interval``.
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Tuple

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

SEARCH_ENDPOINT = "https://api.bilibili.com/x/web-interface/search/type"
VIEW_ENDPOINT = "https://api.bilibili.com/x/web-interface/view"
VISITOR_SPI_ENDPOINT = "https://api.bilibili.com/x/frontend/finger/spi"

SEARCH_REFERER = "https://search.bilibili.com/"
VIDEO_REFERER = "https://www.bilibili.com/"

BLOCKING_HTTP_STATUSES = frozenset({403, 412, 429})

# Known Bilibili API-level risk-control codes (returned with HTTP 200) that
# are treated as platform blocks, not transient failures. Deliberately
# narrow: unknown non-zero codes stay ``failed`` and are never guessed into
# ``blocked``. No bypass is attempted either way.
API_RISK_CONTROL_CODES = frozenset({-412})

_TAG_RE = re.compile(r"<[^>]+>")


class TransportError(Exception):
    """Raised by a transport when the request could not be performed."""


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    body: str


def default_transport(url: str, headers: Dict[str, str], timeout: float) -> TransportResponse:
    """Cookie-jar-free HTTPS GET with an explicit timeout."""

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return TransportResponse(int(response.status), body)
    except urllib.error.HTTPError as exc:  # 4xx/5xx arrive here
        return TransportResponse(int(exc.code), "")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TransportError(str(exc)) from exc


@dataclass(frozen=True)
class SearchItem:
    bvid: str
    title: str
    uploader: str
    published_at: str
    snippet_view_count: Optional[int]
    description: str = ""
    duration: str = ""


@dataclass(frozen=True)
class SearchOutcome:
    status: str  # ok | blocked | failed
    items: Tuple[SearchItem, ...] = ()
    http_status: Optional[int] = None
    api_code: Optional[int] = None
    message: str = ""


@dataclass(frozen=True)
class VideoMetadataOutcome:
    status: str  # ok | invalid | unavailable | restricted | blocked | failed
    title: str = ""
    uploader: str = ""
    published_at: str = ""
    view_count: Optional[int] = None
    duration_sec: Optional[int] = None
    api_code: Optional[int] = None
    http_status: Optional[int] = None
    message: str = ""


@dataclass
class _VisitorIdentity:
    value: Optional[str] = None
    initialized: bool = False
    mode: str = "disabled"  # disabled | anonymous | preset


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _iso_from_unix(seconds) -> str:
    try:
        moment = datetime.fromtimestamp(int(seconds), tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return ""
    return moment.isoformat()


class BilibiliReferenceProvider:
    """Anonymous search + per-video metadata access with bounded, fail-closed behavior.

    Risk-control circuit latch: the first time a genuine platform block is
    observed during this provider's lifetime (HTTP 403/412/429, an HTML
    interception page, or API-level risk-control code ``-412``), the
    provider latches ``blocked`` state and performs **no further network
    requests**; every subsequent ``search_videos`` / ``fetch_video_metadata``
    call returns ``blocked`` without touching the network. This includes the
    anonymous visitor-initialization bootstrap: if that call is itself
    risk-controlled, the run stops before any search or per-video request
    is issued. Ordinary timeouts and 5xx failures do not latch (they remain
    retryable failures, and a failed bootstrap simply degrades silently).
    No bypass mechanism exists or may be added.
    """

    def __init__(
        self,
        *,
        transport: Optional[Callable[[str, Dict[str, str], float], TransportResponse]] = None,
        timeout: float = 15.0,
        request_interval: float = 1.0,
        max_retries: int = 2,
        retry_backoff: float = 1.0,
        sleep: Optional[Callable[[float], None]] = None,
        use_visitor_identity: bool = True,
        visitor_identity: Optional[str] = None,
    ):
        self._transport = transport or default_transport
        self._timeout = float(timeout)
        self._request_interval = max(0.0, float(request_interval))
        self._max_retries = max(0, int(max_retries))
        self._retry_backoff = max(0.0, float(retry_backoff))
        self._sleep = sleep if sleep is not None else time.sleep
        self._last_request_made = False
        self._blocked_latch = False
        self._visitor = _VisitorIdentity()
        if visitor_identity is not None:
            self._visitor.value = visitor_identity
            self._visitor.initialized = True
            self._visitor.mode = "preset"
        elif use_visitor_identity:
            self._visitor.mode = "anonymous"
        else:
            self._visitor.mode = "disabled"

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    @property
    def visitor_identity_mode(self) -> str:
        return self._visitor.mode

    @property
    def request_interval(self) -> float:
        return self._request_interval

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    @property
    def risk_control_latched(self) -> bool:
        """True once a genuine platform block stopped all further requests."""
        return self._blocked_latch

    def search_videos(self, query: str, *, page: int = 1) -> SearchOutcome:
        params = urllib.parse.urlencode({
            "search_type": "video",
            "keyword": query,
            "page": max(1, int(page)),
        })
        url = f"{SEARCH_ENDPOINT}?{params}"
        payload = self._request_json(url, SEARCH_REFERER)
        if payload["status"] == "ok":
            body = payload["body"]
            code = body.get("code")
            if code != 0:
                status = "blocked" if code in API_RISK_CONTROL_CODES else "failed"
                return SearchOutcome(
                    status=status,
                    http_status=payload["http_status"],
                    api_code=code,
                    message=str(body.get("message", "接口返回异常")),
                )
            items = self._parse_search_items(body)
            return SearchOutcome(
                status="ok", items=tuple(items),
                http_status=payload["http_status"], api_code=0,
            )
        return SearchOutcome(
            status=payload["status"],
            http_status=payload["http_status"],
            api_code=payload["api_code"],
            message=payload["message"],
        )

    def fetch_video_metadata(self, bvid: str) -> VideoMetadataOutcome:
        url = f"{VIEW_ENDPOINT}?bvid={urllib.parse.quote(bvid)}"
        payload = self._request_json(url, VIDEO_REFERER)
        status = payload["status"]
        if status == "blocked":
            return VideoMetadataOutcome(
                status="blocked", http_status=payload["http_status"],
                api_code=payload["api_code"], message=payload["message"],
            )
        if status == "failed":
            return VideoMetadataOutcome(
                status="failed", api_code=payload["api_code"], message=payload["message"]
            )
        body = payload["body"]
        code = body.get("code")
        if code != 0:
            mapped, api_message = self._map_video_api_error(
                code, str(body.get("message", ""))
            )
            return VideoMetadataOutcome(
                status=mapped, api_code=code, http_status=payload["http_status"],
                message=api_message,
            )
        data = body.get("data", {})
        stat = data.get("stat", {}) or {}
        view = stat.get("view")
        return VideoMetadataOutcome(
            status="ok",
            title=_strip_tags(str(data.get("title", ""))),
            uploader=str((data.get("owner") or {}).get("name", "")),
            published_at=_iso_from_unix(data.get("pubdate")),
            view_count=int(view) if isinstance(view, (int, float)) and view >= 0 else None,
            duration_sec=int(data["duration"]) if isinstance(data.get("duration"), (int, float)) else None,
            api_code=0,
            http_status=payload["http_status"],
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _map_video_api_error(code, message):
        if code == -400:
            return "invalid", message
        if code in (-404, 62002, 62012):
            return "unavailable", message
        if code == -403:
            return "restricted", message
        if code in API_RISK_CONTROL_CODES:
            return "blocked", message
        return "failed", message

    @staticmethod
    def _parse_search_items(body: Dict[str, object]) -> list:
        results = (body.get("data") or {}).get("result") or []
        items = []
        for entry in results:
            bvid = str(entry.get("bvid") or "").strip()
            if not bvid:
                continue
            play = entry.get("play")
            snippet_views = None
            if isinstance(play, bool):
                snippet_views = None
            elif isinstance(play, (int, float)):
                snippet_views = int(play) if play >= 0 else None
            elif isinstance(play, str) and play.isdigit():
                snippet_views = int(play) if int(play) >= 0 else None
            items.append(SearchItem(
                bvid=bvid,
                title=_strip_tags(str(entry.get("title", ""))),
                uploader=str(entry.get("author", "")),
                published_at=_iso_from_unix(entry.get("pubdate")),
                snippet_view_count=snippet_views,
                description=_strip_tags(str(entry.get("description", "")))[:200],
                duration=str(entry.get("duration", "")),
            ))
        return items

    def _request_json(self, url: str, referer: str) -> Dict[str, object]:
        """One logical JSON request with bounded retry.

        The envelope only reports transport/authentication state; the caller
        interprets API-level ``code`` values because they mean different
        things for search vs per-video metadata — except the uniform
        risk-control codes, which latch here. When the risk-control latch is
        set (either before this call or by the visitor bootstrap it just
        performed), no network request is issued at all.
        """

        if self._blocked_latch:
            return {"status": "blocked", "http_status": None, "api_code": None,
                    "message": "平台风控阻断已触发，本次运行不再发起后续请求",
                    "body": None}
        attempts = self._max_retries + 1
        last_error: Dict[str, object] = {"status": "failed", "http_status": None,
                                         "api_code": None, "message": ""}
        for attempt in range(1, attempts + 1):
            self._ensure_visitor_identity()
            if self._blocked_latch:
                # the visitor bootstrap itself was risk-controlled: stop
                # before issuing any search / metadata request
                return {"status": "blocked", "http_status": None, "api_code": None,
                        "message": "平台风控阻断已触发，本次运行不再发起后续请求",
                        "body": None}
            headers = {"User-Agent": USER_AGENT, "Referer": referer}
            identity = self._visitor.value
            if identity:
                headers["Cookie"] = f"buvid3={identity}"
            try:
                response = self._paced_transport(url, headers)
            except TransportError as exc:
                last_error = {"status": "failed", "http_status": None,
                              "api_code": None, "message": str(exc)}
            else:
                if response.status_code in BLOCKING_HTTP_STATUSES:
                    self._blocked_latch = True
                    return {"status": "blocked", "http_status": response.status_code,
                            "api_code": None, "message": "平台访问受限", "body": None}
                if 500 <= response.status_code < 600:
                    last_error = {"status": "failed", "http_status": response.status_code,
                                  "api_code": None,
                                  "message": f"服务端错误 HTTP {response.status_code}"}
                else:
                    try:
                        body = json.loads(response.body)
                    except (json.JSONDecodeError, TypeError):
                        self._blocked_latch = True
                        return {"status": "blocked", "http_status": response.status_code,
                                "api_code": None, "message": "非 JSON 响应（疑似拦截页）",
                                "body": None}
                    if body.get("code") in API_RISK_CONTROL_CODES:
                        self._blocked_latch = True
                        return {"status": "blocked", "http_status": response.status_code,
                                "api_code": body.get("code"),
                                "message": str(body.get("message", "接口风控拦截")),
                                "body": None}
                    return {"status": "ok", "http_status": response.status_code,
                            "api_code": None, "message": "", "body": body}
            if attempt < attempts:
                self._sleep(self._retry_backoff * attempt)
        return last_error

    def _paced_transport(self, url: str, headers: Dict[str, str]) -> TransportResponse:
        if self._last_request_made and self._request_interval > 0:
            self._sleep(self._request_interval)
        try:
            return self._transport(url, headers, self._timeout)
        finally:
            self._last_request_made = True

    def _ensure_visitor_identity(self) -> None:
        """Anonymous visitor bootstrap with fail-closed risk handling.

        Benign failures (transport error, HTTP 5xx, unexpected-but-JSON
        payloads) degrade silently and the run continues without a visitor
        identity. A genuine risk-control answer on the bootstrap call
        itself — HTTP 403/412/429, a non-JSON interception/challenge page,
        or an API-level risk-control code like ``-412`` — latches the
        provider so the run stops before any search or per-video request.
        """

        visitor = self._visitor
        if visitor.mode != "anonymous" or visitor.initialized:
            return
        visitor.initialized = True
        headers = {"User-Agent": USER_AGENT, "Referer": VIDEO_REFERER}
        try:
            response = self._paced_transport(VISITOR_SPI_ENDPOINT, headers)
        except TransportError:
            return
        if response.status_code in BLOCKING_HTTP_STATUSES:
            self._blocked_latch = True
            return
        if response.status_code != 200:
            return
        try:
            payload = json.loads(response.body)
        except (json.JSONDecodeError, TypeError):
            # a JSON endpoint answering with an HTML challenge page is a
            # genuine risk-control signal, not a transient failure
            self._blocked_latch = True
            return
        if not isinstance(payload, dict):
            return
        if payload.get("code") in API_RISK_CONTROL_CODES:
            self._blocked_latch = True
            return
        value = (payload.get("data") or {}).get("b_3")
        if isinstance(value, str) and value:
            visitor.value = value
