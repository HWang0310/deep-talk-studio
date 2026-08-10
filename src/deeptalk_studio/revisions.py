"""Research Report revision history helpers."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from .models import ResearchReport
from .validation import ReportValidationError, validate_report


def create_approval_revision(
    report: ResearchReport,
    confirmation: str,
    generated_at: str,
) -> Dict[str, Any]:
    """Create an immutable approval-only revision without resetting its Gate."""

    validate_report(report)
    if (
        report.status != "reviewed"
        or report.quality_summary["gate_status"] != "pass"
        or report.fact_check["status"] != "completed"
    ):
        raise ReportValidationError(
            "只有完成独立核查并通过质量 Gate 的 reviewed 报告才能确认进入写稿"
        )
    clean_confirmation = confirmation.strip()
    if not clean_confirmation:
        raise ReportValidationError("确认进入写稿时必须保留用户的原始确认文本")
    result = report.to_dict()
    result["previous_revision"] = report.revision
    result["revision"] = report.revision + 1
    result["generated_at"] = generated_at
    result["change_summary"] = "记录用户明确确认，批准该研究修订进入原创写稿。"
    result["status"] = "ready_for_script"
    result["approval_gate"].update(
        status="approved",
        user_confirmation=clean_confirmation,
        ready_for_script=True,
    )
    ResearchReport.from_dict(result)
    return result


def create_revision(
    report: ResearchReport,
    generated_at: str,
    change_summary: str,
    corrections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    result = report.to_dict()
    result["previous_revision"] = report.revision
    result["revision"] = report.revision + 1
    result["generated_at"] = generated_at
    result["change_summary"] = change_summary.strip()
    result["corrections"] = list(result["corrections"]) + deepcopy(corrections or [])
    result["status"] = "draft"
    result["approval_gate"].update(
        status="pending", user_confirmation="", ready_for_script=False
    )
    ResearchReport.from_dict(result)
    return result
