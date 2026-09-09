"""Human-readable, non-technical views for Content Director artifacts."""

from typing import Any, Mapping

from .content_director import validate_content_thesis_card
from .content_thesis_review import validate_content_thesis_review
from .models import ContentThesisCard, ResearchReport


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] or ["- 暂无"]


def render_content_thesis_card_markdown(
    card: ContentThesisCard,
    report: ResearchReport,
    profile: Mapping[str, Any],
    review_artifact: Mapping[str, Any] | None = None,
) -> str:
    validate_content_thesis_card(card, report, profile, review_artifact)
    content = card.to_dict()
    lines = [
        "# 本期内容方向",
        "",
        "这不是最终稿，而是写稿前先确认：这一期到底要替观众讲清什么。",
        "",
        "## 核心问题",
        "",
        content["core_question"],
        "",
        "## 一句话回答",
        "",
        content["one_sentence_answer"],
        "",
        "## 我们这期的判断",
        "",
        content["core_thesis"],
        "",
        "## 反常识点",
        "",
        content["counterintuitive_point"],
        "",
        "## 为什么观众会想听",
        "",
        f"- 情绪：{content['target_emotion']}",
        f"- 共鸣：{content['resonance']}",
        f"- 值得点赞的判断：{content['approval_point']}",
        f"- 容易引发讨论的地方：{content['comment_tension']}",
        f"- 它替观众说出的话：{content['spokesperson_value']}",
        f"- 它代表的价值认同：{content['value_identity']}",
        "",
        "## 开头要抓住什么",
        "",
        content["hook_promise"],
        "",
        "## 结尾要留下什么",
        "",
        content["ending_question_or_judgment"],
        "",
        "## 我们不越过的边界",
        "",
        *_bullets(content["uncertainty_limits"]),
        "",
        "## 和参考内容相比，我们自己的切口",
        "",
        content["differentiated_angle"],
        "",
    ]
    return "\n".join(lines)


def render_content_thesis_review_markdown(
    card: ContentThesisCard,
    review_artifact: Mapping[str, Any],
    report: ResearchReport,
    profile: Mapping[str, Any],
) -> str:
    validate_content_thesis_review(review_artifact, card, report, profile)
    page = render_content_thesis_card_markdown(card, report, profile).rstrip()
    review = review_artifact["content"]
    decision = review_artifact["gate"]["decision"]
    lines = [page, "", "## 方向检查", ""]
    for check in review["checks"]:
        mark = "通过" if check["outcome"] == "pass" else "需要调整"
        lines.append(f"- {mark}：{check['reason']}")
    if review["issues"]:
        lines.extend(["", "## 仍需处理", ""])
        lines.extend(f"- {issue['description']}" for issue in review["issues"])
    lines.extend(["", "## 结论", "", review["overall_summary"], ""])
    if decision == "pass":
        lines.extend([
            "## 需要你确认",
            "",
            "如果你认可以上方向，请直接回复：确认本期内容方向，进入写稿。",
            "",
        ])
    else:
        lines.extend([
            "## 现在不能进入写稿",
            "",
            "这份方向还需要先按上面的“仍需处理”调整；不会自动开始写稿。",
            "",
        ])
    return "\n".join(lines)
