"""Canonical input, render-time asset and display-text gates for Production 0.6."""

import hashlib
import re
import xml.etree.ElementTree as ElementTree
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from .material_storage import MaterialStorageError, load_material_package
from .models import MaterialPackage, ResearchReport
from .production_profile import ProductionValidationError


ALLOWED_PRODUCTION_MIME_EXTENSIONS = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".svg": "image/svg+xml", ".pdf": "application/pdf",
}


def validate_production_input(
    package_path: Path,
    script: Any,
    report: Any,
    material_profile: Mapping[str, Any],
) -> MaterialPackage:
    """Load through V0.5.1's replaying loader before production is allowed."""

    try:
        package = load_material_package(
            Path(package_path), script, report, material_profile
        )
    except MaterialStorageError as exc:
        raise ProductionValidationError(f"Material Package canonical validation 失败：{exc}") from None
    if package.status not in {"reviewed", "reviewed_with_warnings"}:
        if package.status == "research_update_required" or package.research_update_required["required"]:
            raise ProductionValidationError("Material Package 要求先返回 Research，不能开始制作")
        raise ProductionValidationError(
            f"只有 reviewed / reviewed_with_warnings Material Package 才能制作，当前为 {package.status}"
        )
    if package.research_update_required["required"]:
        raise ProductionValidationError("Material Package 要求先返回 Research，不能开始制作")
    if package.review_state["state"] != "reviewed" or not package.review_state["review_id"]:
        raise ProductionValidationError("Material Package 缺少真实 Material Review linkage")
    return package


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_file_type(path: Path) -> None:
    suffix = path.suffix.casefold()
    if suffix not in ALLOWED_PRODUCTION_MIME_EXTENSIONS:
        raise ProductionValidationError(f"素材扩展名不在 Production 允许列表：{suffix}")
    header = path.read_bytes()[:64]
    if suffix in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8\xff"):
        raise ProductionValidationError("素材扩展名与真实 JPEG MIME 不一致")
    if suffix == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ProductionValidationError("素材扩展名与真实 PNG MIME 不一致")
    if suffix == ".webp" and not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
        raise ProductionValidationError("素材扩展名与真实 WebP MIME 不一致")
    if suffix == ".pdf" and not header.startswith(b"%PDF-"):
        raise ProductionValidationError("素材扩展名与真实 PDF MIME 不一致")
    if suffix == ".svg":
        try:
            root = ElementTree.parse(str(path)).getroot()
        except (ElementTree.ParseError, OSError) as exc:
            raise ProductionValidationError("SVG 文件无法安全解析") from exc
        if root.tag.rsplit("}", 1)[-1].casefold() != "svg":
            raise ProductionValidationError("SVG 文件根元素无效")


def validate_render_asset(
    asset: Mapping[str, Any], allowed_root: Path, *, generated_visual: bool = False
) -> Path:
    status = str(asset.get("eligibility_status", ""))
    if status != "ready_to_use":
        raise ProductionValidationError(
            f"{status or 'unknown'} 素材不能进入 Composition"
        )
    if generated_visual and asset.get("render_status") != "rendered":
        raise ProductionValidationError("Generated Visual 必须已经 rendered 才能进入 Composition")
    raw_path = str(asset.get("local_path", "")).strip()
    if not raw_path:
        raise ProductionValidationError("可渲染素材缺少 local_path")
    path = Path(raw_path).resolve()
    root = Path(allowed_root).resolve()
    if not _inside(path, root):
        raise ProductionValidationError("素材文件不在允许的素材目录")
    if not path.is_file():
        raise ProductionValidationError("素材本地文件不存在")
    expected_size = int(asset.get("byte_size", -1))
    actual_size = path.stat().st_size
    if expected_size != actual_size or actual_size <= 0:
        raise ProductionValidationError("素材 byte 大小与 Material Package 不一致")
    actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if str(asset.get("sha256", "")) != actual_digest:
        raise ProductionValidationError("素材 SHA-256 与 Material Package 不一致")
    _validate_file_type(path)
    return path


def _number_tokens(text: str) -> Sequence[str]:
    result = []
    for token in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text):
        try:
            normalized = format(Decimal(token).normalize(), "f")
        except InvalidOperation:
            normalized = token
        result.append(normalized)
    return tuple(result)


def validate_display_text(
    entry: Mapping[str, Any], report: Any, *,
    additional_grounded_texts: Sequence[str] = (),
) -> None:
    """Conservatively prove visible numbers/dates from bound approved Claims."""

    text = str(entry.get("text", "")).strip()
    kind = entry.get("text_kind")
    claim_ids = list(entry.get("claim_ids", []))
    evidence_ids = list(entry.get("evidence_link_ids", []))
    if not text or kind not in {"editorial", "factual", "attribution"}:
        raise ProductionValidationError("屏幕文字结构无效")
    if kind == "editorial":
        if claim_ids or evidence_ids or _number_tokens(text):
            raise ProductionValidationError("编辑性屏幕标题不能携带事实数字或 Research binding")
        return
    report_obj = report if isinstance(report, ResearchReport) else ResearchReport.from_dict(report)
    claims = {claim["id"]: claim for claim in report_obj.claims}
    links = {link["id"]: link for link in report_obj.evidence_links}
    if not claim_ids or any(claim_id not in claims for claim_id in claim_ids):
        raise ProductionValidationError("事实性屏幕文字必须绑定有效 Research Claim")
    for evidence_id in evidence_ids:
        link = links.get(evidence_id)
        if link is None or link["claim_id"] not in claim_ids:
            raise ProductionValidationError("屏幕文字 Evidence 与 Claim binding 无效")
    approved_text = " ".join(
        [claims[claim_id]["claim"] for claim_id in claim_ids]
        + [str(value) for value in additional_grounded_texts]
    )
    approved_tokens = set(_number_tokens(approved_text))
    for token in _number_tokens(text):
        if token not in approved_tokens:
            raise ProductionValidationError(
                f"屏幕文字包含无法从绑定 Claim 回查的数字或日期：{token}"
            )
