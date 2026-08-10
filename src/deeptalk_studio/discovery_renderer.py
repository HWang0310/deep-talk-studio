"""Small, ordinary-language Topic Discovery cards for a human editor."""

from .models import TopicCandidateSet
from .discovery_validation import validate_candidate_set


CATEGORY_LABELS = {
    "social": "社会",
    "business": "商业",
    "technology": "科技",
    "internet_culture": "网络文化",
    "public_affairs": "公共议题",
}
RISK_LABELS = {"low": "低", "medium": "中", "high": "高", "critical": "极高"}
SHELF_LIFE_LABELS = {
    "urgent": "紧急：今天优先",
    "short": "短：适合尽快做",
    "medium": "中：三五天内仍适合",
    "evergreen": "长：可持续讨论",
}


def render_discovery_markdown(candidate_set: TopicCandidateSet) -> str:
    validate_candidate_set(candidate_set)
    candidates = {item["candidate_id"]: item for item in candidate_set.candidates}
    lines = [
        "# 今天可以讲什么",
        "",
        "下面是经过轻量资料预检后的候选题。只需回复编号，例如“1”或“研究 1”，我就会直接开始深度研究，不需要你再复制标题。",
        "",
    ]
    for position, candidate_id in enumerate(candidate_set.display_candidate_ids, 1):
        candidate = candidates[candidate_id]
        primary = "【首选】" if candidate["is_primary"] else ""
        lines.extend(
            [
                f"## {position}. {primary}{candidate['title']}",
                "",
                f"- 分类：{CATEGORY_LABELS[candidate['category']]}；总分：{candidate['total_score']}",
                f"- 为什么现在值得讲：{candidate['why_now']}",
                f"- 核心冲突：{candidate['core_tension']}",
                f"- 为什么适合做成长视频：{candidate['score_breakdown']['channel_fit']['reason']}",
                f"- 风险：{RISK_LABELS[candidate['risk_level']]}。{candidate['risk_notes']}",
                f"- 时效：{SHELF_LIFE_LABELS[candidate['shelf_life']]}",
                "",
            ]
        )
    if candidate_set.watch_candidate_count:
        lines.extend(
            [
                f"> 另外有 {candidate_set.watch_candidate_count} 个热点值得观察，但目前资料基础不足，没有放进上面的推荐列表。",
                "",
            ]
        )
    if not candidate_set.display_candidate_ids:
        lines.extend(["> 这次没有找到资料基础足够的候选题。可以稍后再试，或换一个分类。", ""])
    lines.append("你现在只需回复一个编号；回复“换一批”会重新寻找，回复“只看科技”等会带着过滤条件重新寻找。")
    return "\n".join(lines).rstrip() + "\n"
