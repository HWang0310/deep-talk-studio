"""Conservative acquisition of reusable static material assets."""

import hashlib
import ipaddress
import mimetypes
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class AcquisitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResponse:
    status: int
    final_url: str
    mime_type: str
    content: bytes


Fetcher = Callable[[str, int], FetchResponse]


def _public_url(url: str, *, resolve_dns: bool = False) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
            return False
        host = parsed.hostname.casefold().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            if not resolve_dns:
                return True
            addresses = [
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
            ]
        return bool(addresses) and all(
            address.is_global and not address.is_multicast for address in addresses
        )
    except (OSError, TypeError, ValueError):
        return False


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, newurl)
        if not _public_url(target, resolve_dns=True):
            raise AcquisitionError("下载重定向目标不是公开 HTTP(S) 地址")
        return super().redirect_request(req, fp, code, msg, headers, target)


def _default_fetcher(url: str, max_bytes: int) -> FetchResponse:
    if not _public_url(url, resolve_dns=True):
        raise AcquisitionError("素材 URL 不是可安全访问的公开 HTTP(S) 地址")
    request = Request(url, headers={"User-Agent": "DeepTalk-Studio/0.5"})
    with build_opener(_SafeRedirectHandler()).open(request, timeout=30) as response:
        data = response.read(max_bytes + 1)
        return FetchResponse(
            status=int(response.status),
            final_url=response.geturl(),
            mime_type=response.headers.get_content_type(),
            content=data,
        )


def _extension(mime_type: str) -> str:
    fixed = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
        "image/svg+xml": ".svg", "application/pdf": ".pdf", "text/plain": ".txt",
    }
    return fixed.get(mime_type, mimetypes.guess_extension(mime_type) or "")


def _ensure_static_svg(content: bytes) -> None:
    lowered = content[:2_000_000].decode("utf-8", errors="ignore").casefold()
    forbidden = ("<script", "javascript:", "onload=", "onerror=", "<foreignobject", "http://", "https://")
    if any(token in lowered for token in forbidden):
        raise AcquisitionError("SVG 包含脚本、事件处理器或外部资源，拒绝保存")


def safe_download_material(
    item: Mapping[str, object],
    output_root: Path,
    profile: Mapping[str, object],
    *,
    fetcher: Optional[Fetcher] = None,
) -> Dict[str, object]:
    if item.get("eligibility_status") != "ready_to_use":
        raise AcquisitionError("只有 rights/provenance Gate 为 ready_to_use 的素材才可自动下载")
    url = str(item.get("source_url", ""))
    if not _public_url(url):
        raise AcquisitionError("素材 URL 不是公开 HTTP(S) 地址")
    maximum = int(profile["max_download_bytes"])
    response = (fetcher or _default_fetcher)(url, maximum)
    if response.status < 200 or response.status >= 300:
        raise AcquisitionError(f"素材下载 HTTP 状态异常：{response.status}")
    if not _public_url(response.final_url):
        raise AcquisitionError("素材最终 URL 不是公开 HTTP(S) 地址")
    mime = response.mime_type.split(";", 1)[0].strip().casefold()
    if mime not in set(profile["allowed_download_mime_types"]):
        raise AcquisitionError(f"素材 MIME 不在安全允许列表：{mime}")
    if len(response.content) > maximum:
        raise AcquisitionError("素材大小超过 Profile 限制")
    if not response.content:
        raise AcquisitionError("素材文件为空")
    if mime == "image/svg+xml":
        _ensure_static_svg(response.content)
    extension = _extension(mime)
    if not extension:
        raise AcquisitionError("无法为素材确定安全扩展名")
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / f"{item['material_id']}{extension}").resolve()
    if target.parent != root:
        raise AcquisitionError("素材目标路径越界")
    if target.exists():
        raise AcquisitionError(f"素材文件已经存在，拒绝覆盖：{target}")
    target.write_bytes(response.content)
    return {
        "local_path": str(target), "byte_size": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest(), "mime_type": mime,
        "final_url": response.final_url,
    }


def register_local_capture(
    item: Mapping[str, object], source_path: Path, output_root: Path
) -> Dict[str, object]:
    source = Path(source_path).resolve()
    if not source.is_file() or source.suffix.casefold() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise AcquisitionError("网页/PDF 截图必须是现有的静态 PNG、JPEG 或 WebP")
    capture = item.get("capture")
    if not isinstance(capture, dict) or not capture.get("source_context"):
        raise AcquisitionError("截图缺少页面上下文和证明边界")
    if not capture.get("what_it_proves") or not capture.get("what_it_does_not_prove"):
        raise AcquisitionError("截图必须记录能证明什么和不能证明什么")
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    suffix = ".jpg" if source.suffix.casefold() in {".jpg", ".jpeg"} else source.suffix.casefold()
    target = (root / f"{item['material_id']}-capture{suffix}").resolve()
    if target.parent != root or target.exists():
        raise AcquisitionError("截图目标越界或已存在，拒绝覆盖")
    size = source.stat().st_size
    shutil.copyfile(source, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "local_path": str(target), "byte_size": size, "sha256": digest,
        "mime_type": {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}[suffix],
        "source_url": item["page_url"], "capture": dict(capture),
    }

