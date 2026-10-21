"""Public-internet-only source fetching for the Creator Workbench (Issue #23 B2).

The Mac-local workbench UI fetches user-supplied source URLs server-side.
This module guarantees such a fetch can only reach **publicly routable
HTTP(S) destinations**:

* only http/https with an explicit hostname (no userinfo, no other schemes);
* every connection resolves the hostname first (A/AAAA) and requires **all**
  resolved addresses to be public unicast — loopback, private, link-local,
  reserved, multicast, documentation and shared address space are rejected;
  failed/empty resolution fails closed;
* the connection is **pinned** to exactly the validated addresses, so the
  DNS answer observed at validation time is the *only* thing the server can
  dial — a DNS-rebinding between validation and connect has no window;
* redirects are only followed to http(s) targets, capped at
  ``MAX_REDIRECTS`` hops, and every hop goes through the same validating,
  pinned connection path (so a redirect to any private/loopback target is
  rejected before any socket is opened);
* response handling keeps the pre-existing contract: ≤2MB body, text/plain
  or HTML text extraction, ≥50 chars of content, typed Chinese errors with
  the paste-text fallback suggestion.

Legitimate public sources keep working exactly as before.  Anything local,
private or ambiguous is refused with a typed error — never silently
attempted.

``resolver`` is injectable for deterministic offline tests.
"""

import hashlib
import http.client
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

AddressList = List[Tuple[int, int, int, Tuple[Any, ...]]]
Resolver = Callable[[str, int], Sequence[Tuple[int, int, int, str, Tuple[Any, ...]]]]

MAX_FETCH_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 25
MAX_REDIRECTS = 4

# Address blocks that are not "publicly routable web destinations" even when
# some heuristics consider them globally visible (CGNAT, benchmarking,
# documentation, IPv6 unique-local, link-local, ...).
_NON_PUBLIC_NETS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "100.64.0.0/10",      # shared / CGNAT
        "192.0.0.0/24",       # IETF protocol assignments
        "198.18.0.0/15",      # benchmarking
        "192.0.2.0/24",       # TEST-NET-1 (documentation)
        "198.51.100.0/24",    # TEST-NET-2
        "203.0.113.0/24",     # TEST-NET-3
        "fc00::/7",           # IPv6 unique-local
        "fe80::/10",          # IPv6 link-local
        "2001:db8::/32",      # IPv6 documentation
    )
)


class WorkbenchSourceFetchError(RuntimeError):
    """A requested source URL is not a valid public HTTP(S) target."""


def _is_public_ip(address: ipaddress._BaseAddress) -> bool:
    if (
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return False
    return not any(address in network for network in _NON_PUBLIC_NETS)


def resolve_public_addresses(
    host: str, port: int, resolver: Optional[Resolver] = None
) -> AddressList:
    """Resolve ``host`` and require *every* resolved address to be public.

    Fails closed on resolution failure, empty answers, non-IP results, and
    on any private/loopback/link-local/reserved address appearing in the
    answer (an ambiguous DNS answer must never reach the socket layer).
    """

    try:
        infos = (resolver or socket.getaddrinfo)(host, port, 0, socket.SOCK_STREAM)
    except (socket.gaierror, OSError, UnicodeError) as exc:
        raise WorkbenchSourceFetchError(
            f"无法解析该来源域名，已拒绝访问（不确定性即失败：{exc}）"
        ) from None
    allowed: AddressList = []
    for info in infos or []:
        try:
            af, socktype, proto, _canon, sockaddr = info
        except (TypeError, ValueError):
            raise WorkbenchSourceFetchError("来源域名解析结果无法识别，已拒绝访问") from None
        raw = sockaddr[0] if sockaddr else ""
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            raise WorkbenchSourceFetchError("来源地址不是有效 IP，已拒绝访问") from None
        if not _is_public_ip(address):
            raise WorkbenchSourceFetchError(
                f"来源地址不是公网地址（{address}），已拒绝访问"
            )
        allowed.append((af, socktype, proto, sockaddr))
    if not allowed:
        raise WorkbenchSourceFetchError("来源域名未解析出任何公网地址，已拒绝访问")
    return allowed


def validate_public_source_url(url: str) -> None:
    """Cheap pre-flight checks that need no DNS (fail closed, typed errors)."""

    if not isinstance(url, str) or not url.strip():
        raise WorkbenchSourceFetchError("只能抓取 http(s) 链接")
    try:
        parsed = urllib.parse.urlsplit(url.strip())
    except ValueError:
        raise WorkbenchSourceFetchError("链接格式无法解析，已拒绝访问") from None
    if parsed.scheme not in ("http", "https"):
        raise WorkbenchSourceFetchError("只能抓取 http(s) 链接（其他协议已拒绝）")
    host = parsed.hostname
    if not host:
        raise WorkbenchSourceFetchError("链接缺少主机名，已拒绝访问")
    if parsed.username or parsed.password:
        raise WorkbenchSourceFetchError("链接带登录信息（userinfo），已拒绝访问")
    if any(char.isspace() for char in host):
        raise WorkbenchSourceFetchError("链接主机名含空白字符，已拒绝访问")
    try:
        _ = parsed.port
    except ValueError:
        raise WorkbenchSourceFetchError("链接端口无效，已拒绝访问") from None


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that can only dial pre-validated public addresses.

    Instead of overriding ``connect()`` (which would drift from stdlib
    behavior on retries/TLS/NODELAY), we only replace ``_create_connection``
    — the exact hook ``HTTPConnection.connect`` already calls.  Resolution,
    validation and dialing stay atomic inside it: the DNS answer is
    validated, and *that exact list* is what gets dialed, so a rebinding
    between validation and connect has no window.
    """

    resolver: Optional[Resolver] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = self._pinned_create_connection

    def _pinned_create_connection(self, address, timeout=None, source_address=None):
        host, port = address
        allowed = resolve_public_addresses(host, port, self.resolver)
        last_error: Optional[OSError] = None
        for af, socktype, proto, sockaddr in allowed:
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                if timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    sock.settimeout(timeout)
                if source_address:
                    sock.bind(source_address)
                sock.connect(sockaddr)
                return sock
            except OSError as exc:  # unreachable/refused/timeout — try next
                if sock is not None:
                    sock.close()
                last_error = exc
        raise WorkbenchSourceFetchError(
            f"无法连接任何已验证的公网地址（{last_error}）"
        ) from last_error


class _PinnedHTTPSConnection(_PinnedHTTPConnection, http.client.HTTPSConnection):
    """HTTPS variant: pinned TCP dial + normal TLS handshake (SNI = host)."""


class _ValidatingHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, resolver: Optional[Resolver] = None):
        super().__init__()
        self.resolver = resolver

    def http_open(self, req):
        def factory(*args, **kwargs):
            connection = _PinnedHTTPConnection(*args, **kwargs)
            connection.resolver = self.resolver
            return connection

        return self.do_open(factory, req)


class _ValidatingHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, resolver: Optional[Resolver] = None):
        super().__init__()
        self.resolver = resolver

    def https_open(self, req):
        def factory(*args, **kwargs):
            connection = _PinnedHTTPSConnection(*args, **kwargs)
            connection.resolver = self.resolver
            return connection

        return self.do_open(factory, req, context=self._context)


class _StrictRedirectHandler(urllib.request.HTTPRedirectHandler):
    """http(s)-only redirects, capped hop count (every hop revalidated)."""

    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            scheme = urllib.parse.urlsplit(newurl).scheme
        except ValueError:
            raise WorkbenchSourceFetchError("重定向目标链接无法解析，已拒绝跟随") from None
        if scheme not in ("http", "https"):
            raise WorkbenchSourceFetchError(
                f"重定向目标不是 http(s) 链接（{scheme or '无协议'}），已拒绝跟随"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip_depth = 0
        self.title = ""
        self._title_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "title" and not self._skip_depth:
            self._title_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title" and self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data):
        if self._title_depth and data.strip():
            self.title += data.strip() + " "
        elif not self._skip_depth and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return re.sub(r"\s{2,}", " ", " ".join(self.parts))


def fetch_public_source(
    url: str,
    *,
    resolver: Optional[Resolver] = None,
    timeout: int = FETCH_TIMEOUT_SECONDS,
    max_bytes: int = MAX_FETCH_BYTES,
) -> Dict[str, Any]:
    """Fetch one user-supplied source URL — public HTTP(S) destinations only.

    Same result contract as the previous ``default_fetcher``: a dict with
    ``ok``/``url``/``error`` or ``ok``/``title``/``text``/``sha256``/... so
    the UI keeps its copy-paste fallback guidance on failure.
    """

    try:
        validate_public_source_url(url)
    except WorkbenchSourceFetchError as exc:
        return {"ok": False, "url": url, "error": f"已拒绝访问该链接（{exc}）"}
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DeepTalkWorkbench/1.0 (local personal tool)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(
        # Direct connections only: an OS/web proxy would dial the destination
        # itself (the proxy's own resolution), bypassing our public-IP
        # validation — so proxies are explicitly disabled here.
        urllib.request.ProxyHandler({}),
        _StrictRedirectHandler(),
        _ValidatingHTTPHandler(resolver),
        _ValidatingHTTPSHandler(resolver),
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status and status >= 400:
                return {"ok": False, "url": url, "error": f"来源返回 HTTP {status}"}
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(max_bytes + 1)
            final_url = response.geturl()
    except WorkbenchSourceFetchError as exc:
        return {"ok": False, "url": url, "error": str(exc)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "url": url, "error": f"来源返回 HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
        return {"ok": False, "url": url, "error": "无法访问该链接（网络错误或超时）"}
    if len(raw) > max_bytes:
        return {"ok": False, "url": url, "error": "页面过大（超过 2MB），请改用粘贴文本"}
    decoded = raw.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or "<html" in decoded[:512].lower():
        extractor = _TextExtractor()
        try:
            extractor.feed(decoded)
            extractor.close()
        except Exception:  # noqa: BLE001 - fall back to raw text on bad HTML
            pass
        text = extractor.text()
        title = extractor.title.strip()
    else:
        text = decoded
        title = ""
    if len(text.strip()) < 50:
        return {"ok": False, "url": url, "error": "页面正文过少（可能是动态渲染页），请改用粘贴文本"}
    return {
        "ok": True,
        "url": url,
        "final_url": final_url,
        "title": title or url,
        "text": text[:200000],
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
