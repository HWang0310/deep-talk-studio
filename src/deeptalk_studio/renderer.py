from typing import Dict, Iterable, List

from .models import ResearchReport
from .validation import validate_report


CLASSIFICATION_LABELS = {
    "confirmed_fact": "已确认事实",
    "media_report": "媒体报道",
    "party_statement": "当事人 / 当事机构说法",
    "commentary": "评论与观点",
    "unverified": "尚未证实",
}
CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低"}
FACT_CHECK_LABELS = {
    "verified": "已核实",
    "partially_verified": "部分核实",
    "unverified": "未核实",
    "disputed": "存在争议",
}


def _refs(ids: Iterable[str]) -> str:
    values = list(ids)
    return "、".join(f"[{item}]" for item in values) if values else "无可核验来源"


def _bullets(values: Iterable[str], empty: str = "暂无") -> List[str]:
    values = list(values)
    return [f"- {value}" for value in values] if values else [f"- {empty}"]


def render_markdown(report: ResearchReport) -> str:
    validate_report(report)
    data = report.data
    source_map: Dict[str, dict] = {item["id"]: item for item in data["sources"]}
    lines = [
        f"# Research Report：{data['topic']}",
        "",
        f"- 报告版本：{data['schema_version']}",
        f"- 生成时间：{data['generated_at']}",
        f"- 核心问题：{data['research_question']}",
        "",
        "> 本报告是原创研究底稿，不是口播稿。分类标签表示证据状态，不代表对任何一方作最终裁决。",
        "",
        "## 研究范围",
        "",
        data["scope_summary"],
        "",
        "## 执行摘要",
        "",
        data["executive_summary"],
        "",
        "## 事件时间线",
        "",
    ]
    for item in data["timeline"]:
        lines.append(
            f"- **{item['date']}**：{item['event']}（主张 {_refs(item['claim_ids'])}；来源 {_refs(item['source_ids'])}）"
        )

    lines.extend(["", "## 信息分层", ""])
    for classification, label in CLASSIFICATION_LABELS.items():
        lines.extend([f"### {label}", ""])
        matches = [
            item for item in data["claims"] if item["classification"] == classification
        ]
        if not matches:
            lines.append("- 暂无")
        for claim in matches:
            lines.append(
                f"- **[{claim['id']}]** {claim['claim']}（置信度：{CONFIDENCE_LABELS[claim['confidence']]}；来源：{_refs(claim['source_ids'])}）"
            )
            if claim["notes"]:
                lines.append(f"  - 说明：{claim['notes']}")
        lines.append("")

    lines.extend(["## 不同立场与观点", ""])
    for item in data["perspectives"]:
        lines.extend(
            [
                f"### {item['actor']}（{item['category']}）",
                "",
                f"- 立场：{item['position']}",
                f"- 理由：{item['reasoning']}",
                f"- 来源：{_refs(item['source_ids'])}",
                "",
            ]
        )

    lines.extend(["## 观点冲突", ""])
    for index, item in enumerate(data["conflicts"], 1):
        lines.extend(
            [
                f"### 冲突 {index}：{item['question']}",
                "",
                f"- 观点 A：{item['side_a']}",
                f"- 观点 B：{item['side_b']}",
                f"- 当前证据状态：{item['evidence_state']}",
                f"- 来源：{_refs(item['source_ids'])}",
                "",
            ]
        )

    lines.extend(["## 值得继续追问的问题", ""])
    for item in data["open_questions"]:
        lines.extend(
            [
                f"- **{item['question']}**",
                f"  - 为什么重要：{item['why_it_matters']}",
                f"  - 下一步：{item['suggested_next_step']}",
            ]
        )

    lines.extend(["", "## 可选内容切入角度", ""])
    for index, item in enumerate(data["angles"], 1):
        lines.extend(
            [
                f"### 角度 {index}：{item['title']}",
                "",
                f"- 核心问题：{item['core_question']}",
                f"- 为什么是现在：{item['why_now']}",
                f"- 对观众的价值：{item['audience_value']}",
                f"- 表达风险：{item['risks']}",
                f"- 必须保留的主张：{_refs(item['required_claim_ids'])}",
                "",
            ]
        )

    lines.extend(["## 事实核查记录", ""])
    for item in data["fact_check_notes"]:
        lines.append(
            f"- **[{item['claim_id']}] {FACT_CHECK_LABELS[item['status']]}**：{item['explanation']}"
        )

    lines.extend(["", "## 局限性", "", *_bullets(data["limitations"]), ""])
    handoff = data["handoff_to_script_agent"]
    lines.extend(
        [
            "## 给 Script Agent 的交接",
            "",
            f"- 推荐角度：{handoff['recommended_angle']}",
            f"- 中心张力：{handoff['central_tension']}",
            f"- 必须保留的主张：{_refs(handoff['must_keep_claim_ids'])}",
            "- 禁止写成事实的内容：",
            *_bullets(handoff["avoid_claims"]),
            "- 仍需补充的研究：",
            *_bullets(handoff["follow_up_research"]),
            "",
            "## 来源清单",
            "",
        ]
    )
    for source_id in sorted(source_map):
        source = source_map[source_id]
        lines.extend(
            [
                f"### [{source_id}] [{source['title']}]({source['url']})",
                "",
                f"- 发布者：{source['publisher']}",
                f"- 发布时间：{source['published_at'] or '未注明'}",
                f"- 访问时间：{source['accessed_at']}",
                f"- 来源类型：{source['source_type']}",
                f"- 立场摘要：{source['stance_summary']}",
                f"- 可信度说明：{source['credibility_notes']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"

