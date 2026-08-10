import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import ResearchReport
from .renderer import render_markdown
from .validation import validate_report


@dataclass(frozen=True)
class ReportPaths:
    markdown: Path
    json: Path


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"[^0-9a-z\u3400-\u9fff]+", "-", normalized)
    slug = normalized.strip("-")
    return slug[:80] or "research-report"


def _report_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("generated_at 必须是 ISO 8601 日期时间") from exc


def save_report(report: ResearchReport, output_root: Path) -> ReportPaths:
    validate_report(report)
    report_date = _report_date(report.generated_at)
    directory = (
        Path(output_root)
        / f"{report_date.year:04d}"
        / f"{report_date.month:02d}"
        / f"{report_date.day:02d}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / slugify(report.topic)
    json_path = base.with_suffix(".json")
    markdown_path = base.with_suffix(".md")
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return ReportPaths(markdown=markdown_path, json=json_path)

