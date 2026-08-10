"""Human-readable Editor and clean Teleprompter views for Script Draft 0.4."""

from typing import Dict, Mapping

from .models import ResearchReport, ScriptDraft
from .script_validation import validate_script_draft


KIND_LABELS = {
    "fact": "事实",
    "attribution": "归因",
    "analysis": "分析",
    "transition": "转场",
    "question": "提问",
}


def render_editor_markdown(
    script: ScriptDraft, report: ResearchReport, profile: Mapping[str, object]
) -> str:
    validate_script_draft(script, report, profile)
    lines = [
        f"# Script Editor Version：{script.working_title}",
        "",
        f"- Script：{script.script_id} / r{script.revision}",
        f"- Research：{script.report_id} / r{script.report_revision}",
        f"- 状态：{script.status}",
        f"- 目标时长：约 {script.target_duration_minutes:g} 分钟",
        f"- 预计口播：约 {script.estimated_duration_minutes:g} 分钟（{script.character_count} 字符，估算值）",
        f"- 核心观点：{script.thesis}",
        f"- 给观众的承诺：{script.audience_promise}",
        "",
        "## Beats",
    ]
    for beat in script.beats:
        lines.extend(
            [
                "",
                f"### {beat['beat_id']} · {KIND_LABELS[beat['content_kind']]}",
                "",
                f"目的：{beat['purpose']}",
                "",
                beat["narration"],
                "",
                "Claim refs：" + (", ".join(beat["claim_ids"]) or "无"),
                "Evidence refs：" + (", ".join(beat["evidence_link_ids"]) or "无"),
                "Analysis basis："
                + (", ".join(beat["analysis_basis_claim_ids"]) or "无"),
                "风险：" + (beat["risk_notes"] or "无"),
            ]
        )
    lines.extend(["", "## Closing", "", script.closing])
    lines.extend(["", "## Research caveats"])
    lines.extend(f"- {item}" for item in script.research_caveats)
    lines.extend(["", "## Research gaps"])
    lines.extend(f"- {item}" for item in script.research_gaps)
    lines.extend(
        [
            "",
            "## Must-keep coverage",
            "",
            "已覆盖：" + (", ".join(script.covered_must_keep_claim_ids) or "无"),
            "缺失：" + (", ".join(script.missing_must_keep_claim_ids) or "无"),
            "",
        ]
    )
    return "\n".join(lines)


def render_teleprompter_markdown(script: ScriptDraft) -> str:
    spoken = [beat["narration"].strip() for beat in script.beats]
    spoken.append(script.closing.strip())
    return "\n\n".join(item for item in spoken if item) + "\n"
