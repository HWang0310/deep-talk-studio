import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import ResearchReport
from .renderer import render_markdown
from .validation import validate_report


class ReportStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportPaths:
    markdown: Path
    json: Path


@dataclass(frozen=True)
class FactCheckPaths:
    json: Path


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"[^0-9a-z\u3400-\u9fff]+", "-", normalized)
    slug = normalized.strip("-")
    return slug[:80] or "research-report"


def _safe_identifier(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    safe = re.sub(r"[^0-9A-Za-z._-]+", "-", normalized).strip("-.")
    return safe[:120] or "report-id"


def _report_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ReportStorageError("generated_at 必须是 ISO 8601 日期时间") from exc


def save_report(report: ResearchReport, output_root: Path) -> ReportPaths:
    validate_report(report)
    report_date = _report_date(report.created_at)
    directory = (
        Path(output_root)
        / f"{report_date.year:04d}"
        / f"{report_date.month:02d}"
        / f"{report_date.day:02d}"
        / slugify(report.topic)
        / _safe_identifier(report.report_id)
    )
    base = directory / f"research-report-r{report.revision:04d}"
    json_path = base.with_suffix(".json")
    markdown_path = base.with_suffix(".md")
    if json_path.exists() or markdown_path.exists():
        raise ReportStorageError(
            f"报告 {report.report_id} 修订版 {report.revision} 已经存在，不能静默覆盖"
        )
    markdown = render_markdown(report)
    serialized = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"
    directory.mkdir(parents=True, exist_ok=True)
    json_path.write_text(serialized, encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return ReportPaths(markdown=markdown_path, json=json_path)


def save_fact_check_artifact(
    artifact: dict, report: ResearchReport, output_root: Path
) -> FactCheckPaths:
    from .fact_check import validate_fact_check_artifact

    validate_fact_check_artifact(artifact, report)
    report_date = _report_date(report.created_at)
    directory = (
        Path(output_root)
        / f"{report_date.year:04d}"
        / f"{report_date.month:02d}"
        / f"{report_date.day:02d}"
        / slugify(report.topic)
        / _safe_identifier(report.report_id)
    )
    filename = (
        f"fact-check-for-r{report.revision:04d}-"
        f"{_safe_identifier(artifact['review_id'])}.json"
    )
    path = directory / filename
    if path.exists():
        raise ReportStorageError(f"FactCheck Artifact 已经存在：{path}")
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return FactCheckPaths(json=path)
