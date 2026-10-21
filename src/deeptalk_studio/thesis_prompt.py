"""LLM prompts for the Creator Workbench thesis + reference-analysis steps.

These prompts reuse the original-product pattern in ``prompt.py`` /
``script_prompt.py``: a strict system prompt naming the safety boundaries, a
user prompt carrying only approved artifacts, and local JSON Schema
validation on every model answer (see ``workbench.flow``).  Reference video
material is explicitly narrative-only here — it may never enter Research
claim space.
"""

import json
from typing import Any, Dict, List, Mapping, Optional


THESIS_WRITER_SYSTEM_PROMPT = """你是 DeepTalk Studio 的 Content Thesis 编辑。你将基于一份已获用户批准的 Research Report，起草本期的 Content Thesis Card 内容。

边界：
- 只能使用这份报告中已存在的主张（claims）与其证据，不得从记忆或网络补充新事实。
- ID（如 C1、C12）必须真实存在于报告 claims 中，不得编造。
- 参考视频的叙事分析只可用于启发结构、钩子与节奏的想法，绝不能作为事实来源，更不能模仿或复述任何具体表达。
- 报告的 limitations 与 open_questions 必须如实转化为 uncertainty_limits，不得弱化或删除。
- 输出必须是符合给定 JSON Schema 的单个 JSON 对象，不得输出解释文字。"""


THESIS_REVIEWER_SYSTEM_PROMPT = """你是 DeepTalk Studio 的独立 Thesis Review 步骤。你不能只是复述卡片内容，必须按固定检查项实际审查 Content Thesis 与其 Research 报告。

要求：
- checks 必须逐项给出 pass/fail 与具体理由；引用报告中的 claim id 或卡片中的原文片段支撑判断。
- 任何 fail 的检查项必须伴随 blocking issue；issues 只能使用允许的 issue_type。
- 不得放宽事实边界；报告 limitations 被弱化即 fail（fact_support / counter_evidence）。
- 输出必须是符合给定 JSON Schema 的单个 JSON 对象，不得输出解释文字。"""


REFERENCE_SUMMARY_SYSTEM_PROMPT = """你是 DeepTalk Studio 的参考视频叙事分析员。你只分析叙事手法与结构，绝不评价内容真实性。

硬边界：
- 参考视频不是事实来源：不得把其内容当作事实、证据或研究结论。
- 不得复述、模仿其具体表达或台词；只能用高度概括的中文描述手法。
- 不评价创作者个人，不引用其具体观点。
- 输出必须是符合给定 JSON Schema 的单个 JSON 对象。"""


THESIS_CONTENT_KEYS = [
    "core_question",
    "one_sentence_answer",
    "core_thesis",
    "counterintuitive_point",
    "target_emotion",
    "resonance",
    "approval_point",
    "comment_tension",
    "spokesperson_value",
    "value_identity",
    "strongest_evidence_claim_ids",
    "counter_evidence_claim_ids",
    "uncertainty_limits",
    "crowded_angles",
    "differentiated_angle",
    "hook_promise",
    "ending_question_or_judgment",
    "competitive_insight_notes",
]


def build_thesis_writer_prompt(
    report: Mapping[str, Any],
    narrative_insights: Optional[List[Mapping[str, Any]]] = None,
) -> str:
    insights_text = ""
    if narrative_insights:
        lines = []
        for insight in narrative_insights[:5]:
            lines.append(
                "- {title}（{views} 播放，{dur:.0f} 秒）：{summary}".format(
                    title=str(insight.get("title", ""))[:60],
                    views=insight.get("view_count", "—"),
                    dur=float(insight.get("duration_seconds", 0) or 0),
                    summary=str(insight.get("narrative_summary", ""))[:280],
                )
            )
        insights_text = (
            "\n\n参考视频叙事分析（仅供结构/节奏/钩子启发，禁止作为事实来源，禁止模仿表达）：\n"
            + "\n".join(lines)
        )
    claims = report.get("claims", [])
    claim_lines = [
        "{cid}（{cls}，{risk}）：{text}".format(
            cid=claim["id"],
            cls=claim.get("classification", ""),
            risk=claim.get("risk_level", ""),
            text=str(claim.get("claim", ""))[:160],
        )
        for claim in claims
    ]
    return (
        "已批准的 Research 报告 JSON（唯一事实来源）：\n"
        + json.dumps(report, ensure_ascii=False, separators=(",", ":"))
        + "\n\n可用主张清单：\n"
        + "\n".join(claim_lines)
        + insights_text
        + "\n\n请起草本期的 Content Thesis 内容字段："
        + "、".join(THESIS_CONTENT_KEYS)
        + "。其中 strongest_evidence_claim_ids / counter_evidence_claim_ids 只能从可用主张 ID 中选择。"
    )


def build_thesis_review_prompt(
    report: Mapping[str, Any],
    card_content: Mapping[str, Any],
    check_names: List[str],
) -> str:
    return (
        "Research 报告 JSON：\n"
        + json.dumps(report, ensure_ascii=False, separators=(",", ":"))
        + "\n\n待审查的 Content Thesis 内容 JSON：\n"
        + json.dumps(card_content, ensure_ascii=False, separators=(",", ":"))
        + "\n\n必须逐项覆盖的检查项（checks.check_name 只能用这些）：\n"
        + "、".join(check_names)
        + "\n\nissues 的 issue_type 只能是：thesis_unclear、unsupported_thesis、counter_evidence_ignored、"
        "audience_value_missing、competitive_imitation_risk、retention_promise_weak。"
        "\n整体输出 {checks, issues, overall_summary}。"
    )


def build_reference_summary_prompt(
    transcript_text: str,
    metrics: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> str:
    excerpt = transcript_text[:8000]
    return (
        "参考视频元数据（非事实来源，仅叙事分析对象）：\n"
        + json.dumps(
            {
                "title": str(metadata.get("title", ""))[:120],
                "view_count": metadata.get("view_count"),
                "duration_seconds": metrics.get("duration_seconds"),
            },
            ensure_ascii=False,
        )
        + "\n\n本地转写文本节选（仅用于结构分析）：\n"
        + excerpt
        + "\n\n确定性指标："
        + json.dumps(
            {
                key: metrics[key]
                for key in (
                    "char_count",
                    "cps",
                    "segment_count",
                    "avg_segment_seconds",
                    "question_count",
                    "number_token_count",
                )
                if key in metrics
            },
            ensure_ascii=False,
        )
        + "\n\n请输出该视频的叙事手法分析：narrative_summary（200字内，高度概括）、hook_style（开场钩子类型与效果）、"
        "pacing（节奏与信息密度特征）、struct_patterns（3-5个结构手法）、takeaways（2-3条可借鉴但没有抄袭风险的写作手法）。"
    )
