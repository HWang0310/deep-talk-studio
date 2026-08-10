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
RELATION_LABELS = {
    "supports": "支持",
    "contradicts": "反驳",
    "attributes": "归因",
    "context": "背景",
}
RISK_LABELS = {"low": "低", "medium": "中", "high": "高风险", "critical": "极高风险"}


def _refs(ids: Iterable[str]) -> str:
    values = list(ids)
    return "、".join(f"[{item}]" for item in values) if values else "无"


def _bullets(values: Iterable[str], empty: str = "暂无") -> List[str]:
    values = list(values)
    return [f"- {value}" for value in values] if values else [f"- {empty}"]


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: ResearchReport) -> str:
    validate_report(report)
    data = report.data
    evidence_by_claim: Dict[str, List[dict]] = {}
    for link in data["evidence_links"]:
        evidence_by_claim.setdefault(link["claim_id"], []).append(link)

    lines = [
        f"# Research Report：{data['topic']}",
        "",
        f"- Schema：{data['schema_version']}",
        f"- 报告 ID：{data['report_id']}",
        f"- 修订版：{data['revision']}（上一版：{data['previous_revision']}）",
        f"- 创建时间：{data['created_at']}",
        f"- 本版时间：{data['generated_at']}",
        f"- 研究模式：{data['research_mode']}",
        f"- 当前状态：{data['status']}",
        f"- 核心问题：{data['research_question']}",
        "",
        "> 本报告是原创研究底稿，不是口播稿。事实标签、来源匹配和质量 Gate 均可机器复查。",
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
            f"- **{item['date']}**：{item['event']}（主张 {_refs(item['claim_ids'])}；证据 {_refs(item['evidence_link_ids'])}）"
        )

    lines.extend(["", "## 信息分层", ""])
    for classification, label in CLASSIFICATION_LABELS.items():
        lines.extend([f"### {label}", ""])
        matches = [claim for claim in data["claims"] if claim["classification"] == classification]
        if not matches:
            lines.append("- 暂无")
        for claim in matches:
            links = evidence_by_claim.get(claim["id"], [])
            lines.append(
                f"- **[{claim['id']}]** {claim['claim']}（重要性：{claim['importance']}；风险：{RISK_LABELS[claim['risk_level']]}；核查：{claim['verification_status']}；证据：{_refs(link['id'] for link in links)}）"
            )
            if claim["notes"]:
                lines.append(f"  - 说明：{claim['notes']}")
        lines.append("")

    lines.extend(["## Evidence Ledger", ""])
    for link in data["evidence_links"]:
        lines.extend(
            [
                f"- **[{link['id']}] {RELATION_LABELS[link['relation']]}**：[{link['source_id']}] → [{link['claim_id']}]",
                f"  - 概述：{link['evidence_summary']}",
                f"  - 定位：{link['evidence_locator']}",
                f"  - 独立性组：{link['independence_group']}；复核：{'是' if link['verified_in_review'] else '否'}",
                f"  - 核查说明：{link['verification_notes'] or '无'}",
            ]
        )

    lines.extend(["", "## 不同立场与观点", ""])
    for item in data["perspectives"]:
        lines.extend(
            [
                f"### {item['actor']}（{item['category']}）",
                "",
                f"- 立场：{item['position']}",
                f"- 理由：{item['reasoning']}",
                f"- 主张：{_refs(item['claim_ids'])}",
                f"- 证据：{_refs(item['evidence_link_ids'])}",
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
                f"- 主张：{_refs(item['claim_ids'])}；证据：{_refs(item['evidence_link_ids'])}",
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

    fact_check = data["fact_check"]
    lines.extend(
        [
            "## 独立事实核查",
            "",
            f"- Review ID：{fact_check['review_id'] or '尚未运行'}",
            f"- 状态：{fact_check['status']}",
            f"- 已检查：{_refs(fact_check['checked_claim_ids'])}",
            f"- 未解决：{_refs(fact_check['unresolved_claim_ids'])}",
            "",
            "## 研究质量 Gate",
            "",
        ]
    )
    quality = data["quality_summary"]
    lines.extend(
        [
            f"- Gate：{quality['gate_status']}",
            f"- 主张来源覆盖率：{_percent(quality['claim_source_coverage'])}",
            f"- 高风险核查覆盖率：{_percent(quality['high_risk_fact_check_coverage'])}",
            f"- confirmed_fact 独立来源覆盖率：{_percent(quality['confirmed_fact_independent_coverage'])}",
            f"- 来源类型数：{quality['source_type_diversity_count']}",
            f"- 重复 / 转载：{quality['duplicate_source_count']} / {quality['syndicated_source_count']}",
            f"- 未解决高风险：{quality['unresolved_high_risk_count']}",
            f"- 无来源归因：{quality['unsourced_attribution_count']}",
            f"- Provenance 匹配率：{_percent(quality['provenance_match_rate'])}",
            "- 未通过原因：",
            *_bullets(quality["gate_reasons"], "无"),
            "",
            "## 用户审批 Gate",
            "",
        ]
    )
    approval = data["approval_gate"]
    lines.extend(
        [
            f"- 状态：{approval['status']}",
            f"- 进入未来 Script Agent 前需要用户确认：{'是' if approval['requires_user_confirmation'] else '否'}",
            f"- 必须向用户暴露的高风险 claim：{_refs(approval['high_risk_claim_ids'])}",
            f"- 是否已可进入 Script Agent：{'是' if approval['ready_for_script'] else '否'}",
            "",
            "## 局限性",
            "",
            *_bullets(data["limitations"]),
            "",
        ]
    )

    handoff = data["handoff_to_script_agent"]
    lines.extend(
        [
            "## 给未来 Script Agent 的交接",
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
    for source in data["sources"]:
        lines.extend(
            [
                f"### [{source['id']}] [{source['title']}]({source['url']})",
                "",
                f"- 发布者：{source['publisher']}；类型：{source['source_type']}",
                f"- 发布时间：{source['published_at'] or '未注明'}；访问：{source['accessed_at']}",
                f"- 检查方式：{source['inspection_method']}；provenance：{source['provenance_status']} / {source['provenance_method']}",
                f"- 独立性：{source['independence_group']} / {source['independence_status']}",
                f"- 内容贡献：{source['stance_summary']}",
                f"- 可信度说明：{source['credibility_notes']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
