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
- 参考视频的对比材料分两层：叙事手法（结构/钩子/节奏）可用于启发角度与结构；各条「可归因观点」是对参考创作者立场的概括描述，只能作为差异化定位的参照——两者都绝不能作为事实来源或证据链，也绝不能拼凑或复述其表达。
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
    insights_text = ""
    if reference_insights:
        comparison_block = render_reference_comparison(reference_insights)
        if comparison_block:
            insights_text = "\n\n" + comparison_block
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
    """Enriched per-reference insights for the Owner's five-way comparison
    (Issue #23 B3): narrative craft *and* an attributable viewpoint summary,
    never facts, never copied expression."""
    insights = []
    for study in studies:
        summary = study.get("narrative_summary")
        if not summary:
            continue
        insights.append(
            {
                "bvid": str(study.get("bvid", "") or ""),
                "title": study.get("title", ""),
                "view_count": study.get("view_count"),
                "duration_seconds": study.get("duration_seconds", 0),
                "cps": study.get("cps"),
                "question_count": study.get("question_count"),
                "narrative_summary": summary,
                "creator_viewpoint": str(study.get("creator_viewpoint", "") or ""),
                "hook_style": str(study.get("hook_style", "") or ""),
                "pacing": str(study.get("pacing", "") or ""),
                "struct_patterns": [
                    str(pattern) for pattern in (study.get("struct_patterns") or [])
                ],
                "takeaways": [
                    str(item) for item in (study.get("takeaways") or [])
                ],
            }
        )
    return insights


def render_reference_comparison(insights: List[Mapping[str, Any]]) -> str:
    """Deterministic per-reference viewpoints + N-way comparison block.

    Attribution only — summarizes each reference creator's stance and
    narrative craft from the local analysis, computes cross-comparison
    statistics deterministically (no LLM), and hard-labels the block as
    never-a-fact-source, never-copyable expression.
    """
    if not insights:
        return ""
    lines = []
    for insight in insights:
        viewpoint = str(insight.get("creator_viewpoint", "") or "").strip()
        lines.append(
            "- {title}（{views} 播放，{dur:.0f} 秒）：{summary}\n"
            "  可归因观点：{viewpoint}\n"
            "  开场钩子：{hook}；节奏：{pacing}；结构手法：{patterns}".format(
                title=str(insight.get("title", ""))[:60],
                views=insight.get("view_count") if insight.get("view_count") is not None else "—",
                dur=float(insight.get("duration_seconds", 0) or 0),
                summary=str(insight.get("narrative_summary", ""))[:200],
                viewpoint=viewpoint or "（本次未提取到观点立场，仅可作结构/节奏参考）",
                hook=str(insight.get("hook_style", "") or "—"),
                pacing=str(insight.get("pacing", "") or "—"),
                patterns="、".join(insight.get("struct_patterns") or []) or "—",
            )
        )
    total = len(insights)
    pattern_counter: Dict[str, int] = {}
    for insight in insights:
        for pattern in insight.get("struct_patterns") or []:
            key = str(pattern).strip()
            if key:
                pattern_counter[key] = pattern_counter.get(key, 0) + 1
    shared_patterns = "、".join(
        f"{name}（{count}/{total} 条）"
        for name, count in sorted(
            pattern_counter.items(), key=lambda item: (-item[1], item[0])
        )
        if count >= 2
    ) or "（各条结构手法描述均不同）"
    hook_counter: Dict[str, int] = {}
    for insight in insights:
        hook = str(insight.get("hook_style", "") or "").strip()
        if hook:
            hook_counter[hook] = hook_counter.get(hook, 0) + 1
    hooks_text = "、".join(
        f"{name}×{count}" if count > 1 else name
        for name, count in sorted(
            hook_counter.items(), key=lambda item: (-item[1], item[0])
        )
    ) or "（钩子手法各异）"
    cps_values = [
        float(insight.get("cps") or 0)
        for insight in insights
        if insight.get("cps")
    ]
    question_counts = [
        int(insight.get("question_count") or 0) for insight in insights
    ]
    stats = [
        f"- 高频/共同结构手法：{shared_patterns}",
        f"- 开场钩子取向：{hooks_text}",
        f"- 语速区间：{min(cps_values):.1f}–{max(cps_values):.1f} 字/秒（提取到 {len(cps_values)}/{total} 条）" if cps_values else "- 语速区间：（未提取到语速数据）",
        f"- 反问句数量分布：{min(question_counts)}–{max(question_counts)} 个（均值 {sum(question_counts) / total:.1f}）",
    ]
    with_viewpoints = sum(1 for insight in insights if insight.get("creator_viewpoint"))
    header = (
        f"参考视频叙事与观点对比（{total} 条，其中 {with_viewpoints} 条提取到可归因观点；"
        "只描述叙事手法与各创作者的立场概括，绝不作为事实来源或证据链，禁止拼凑或复述其表达）："
    )
    return (
        header
        + "\n"
        + "\n".join(lines)
        + "\n"
        + f"N 方对比小结（确定性统计）：\n"
        + "\n".join(stats)
    )
