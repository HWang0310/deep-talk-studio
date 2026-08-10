"""Research Report revision history helpers."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from .models import ResearchReport


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
