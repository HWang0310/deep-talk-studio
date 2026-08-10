from pathlib import Path

from .models import ResearchReport
from .providers.base import ResearchProvider
from .schema import REPORT_JSON_SCHEMA
from .storage import ReportPaths, save_report
from .validation import validate_report


def run_research(
    topic: str, provider: ResearchProvider, output_root: Path
) -> ReportPaths:
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("主题不能为空")
    data = provider.research(clean_topic, REPORT_JSON_SCHEMA)
    report = ResearchReport.from_dict(data)
    validate_report(report)
    return save_report(report, output_root)

