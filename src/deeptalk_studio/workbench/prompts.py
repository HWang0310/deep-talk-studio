"""Workbench-specific prompt builders (research with fetched sources).

The canonical product prompts live in ``prompt.py`` / ``thesis_prompt.py``;
this module only adds the workbench composition: a research/fact-check call
that carries the creator's fetched source texts so the model drafts claims
grounded in real pages (chat-compatible providers have no built-in web
search; responses providers still search additionally).  Reference-video
narrative summaries may only inspire structure, never facts.
"""

import json
from typing import Any, Dict, List, Mapping, Optional


WORKBENCH_RESEARCH_SYSTEM_PROMPT = """你是 DeepTalk Studio 的 Research Agent。你正在为本期视频准备原创研究底稿。

材料边界：
- 「本地抓取的来源材料」是已知真实抓取的网页文本；请优先基于它们形成主张与证据链接（evidence link 的 source_id 必须引用这些来源的 S 编号）。
- 如果你能联网搜索，可以补充新来源与新事实；无法证实时必须降级标注，不得编造。
- 参考视频的叙事分析只允许启发角度与结构，绝不能作为事实来源。
- 区分已确认事实、媒体报道、当事方说法与评论观点；高风险主张（归责、声誉、法律、快速变化）要如实标 risk_level。
- 来源不得写成 duplicate/syndicated，除非你确定它们同源；独立性不确定时用 unknown。
- 输出必须是符合给定 JSON Schema 的单个 JSON 对象，不得输出解释文字。"""


def _source_block(sources: List[Mapping[str, Any]], *, excerpt_chars: int) -> str:
    lines = []
    for source in sources:
        text = str(source.get("text", "")).strip()
        lines.append(
            "来源 {sid}（{url}）\n标题：{title}\n文本节选：\n{excerpt}".format(
                sid=source.get("sid", ""),
                url=source.get("url", ""),
                title=str(source.get("title", ""))[:160],
                excerpt=text[:excerpt_chars] if text else "（抓取文本为空，仅可作为占位，不得据此生成主张）",
            )
        )
    return "\n\n".join(lines)


def build_workbench_research_user_prompt(
    topic: str,
    research_question: str,
    sources: List[Mapping[str, Any]],
    reference_insights: Optional[List[Mapping[str, Any]]] = None,
) -> str:
    from datetime import datetime

    today = datetime.now().astimezone().date().isoformat()
    insight_lines = []
    for insight in (reference_insights or [])[:5]:
        insight_lines.append(
            "- {title}：{summary}".format(
                title=str(insight.get("title", ""))[:60],
                summary=str(insight.get("narrative_summary", ""))[:200],
            )
        )
    insights_text = (
        "\n\n参考视频叙事分析（只可启发结构与角度，禁止作为事实来源）：\n"
        + "\n".join(insight_lines)
        if insight_lines
        else ""
    )
    question_text = research_question.strip() if isinstance(research_question, str) else ""
    return (
        f"研究主题：{topic}\n当前日期：{today}\n"
        + (f"研究问题（用户关注方向）：{question_text}\n" if question_text else "")
        + f"\n本地抓取的来源材料（source id 见每段开头，主张请优先绑定它们）：\n"
        + _source_block(sources, excerpt_chars=6000)
        + insights_text
        + "\n\n请完成：研究问题、范围说明、执行摘要、来源清单（沿用给定 S 编号，可按同一 URL 补全字段）、"
        "主张（C 编号）、证据链接（E 编号）、时间线、多方观点、观点冲突、未决问题、"
        "可开发的原创切入角度（required_claim_ids 必须引用真实存在的 C 编号）、局限性说明，"
        "以及 handoff_to_script_agent 的推荐角度、核心张力、必须保留的主张、必须避免使用的主张和后续研究建议。"
    )


def build_workbench_fact_check_user_prompt(
    report: Mapping[str, Any],
    sources: List[Mapping[str, Any]],
) -> str:
    from ..prompt import build_fact_check_prompt

    return (
        build_fact_check_prompt(dict(report))
        + "\n\n本地重新抓取的来源原文（核查必须优先逐字对照它们）：\n"
        + _source_block(sources, excerpt_chars=6000)
        + "\n\n对 outcome=verified 或 partially_verified 的检查，verification_notes 必须包含至少一段"
        "来自来源原文的原文引用（用「」括起，至少 12 个字），且 new_sources 留空（本工作台核查不引入新来源，"
        "只重新核对现有来源原文）。"
    )


def serialize_reference_insights(studies: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    insights = []
    for study in studies:
        summary = study.get("narrative_summary")
        if not summary:
            continue
        insights.append(
            {
                "title": study.get("title", ""),
                "view_count": study.get("view_count"),
                "duration_seconds": study.get("duration_seconds", 0),
                "narrative_summary": summary,
            }
        )
    return insights
