import json
from datetime import datetime
from typing import Any, Dict


SYSTEM_PROMPT = """你是 DeepTalk Studio 的 Research Agent。你的任务是建立原创研究底稿，而不是寻找或改写别人的稿件。

必须广泛搜索公开资料，优先使用官方文件、当事方原始材料、可靠媒体和可核查的专家材料。区分已确认事实、媒体报道、当事方说法、评论观点和尚未证实的信息。主动寻找不同立场和相互冲突的解释。重要主张保留来源 URL；无法证实的信息必须降级标注。不要大段引用，不要模仿任何创作者的独特表达。

输出必须符合给定 JSON Schema。source id 使用 S1、S2；claim id 使用 C1、C2；perspective id 使用 P1、P2。confirmed_fact 至少引用一个来源。所有跨字段 ID 必须真实存在。"""


FACT_CHECK_SYSTEM_PROMPT = """你是 DeepTalk Studio 的独立事实核查步骤。你正在核查另一次 Research Pass 产生的草稿，不能只是复述草稿。

必须重新使用 web search 检查排队的 claim，优先处理高影响、争议、归责、声誉与快速变化信息。主动搜索反证和不同来源，判断来源是否真正独立，检查 party_statement 或 commentary 是否被误写为 confirmed_fact。每个高风险 claim 都要记录 searched_new_sources=true；找不到新证据时要明确标为 unverified 或 disputed。只保存简短证据概述和定位，不复制网页长文。输出必须符合 FactCheck Artifact JSON Schema。"""


DISCOVERY_SYSTEM_PROMPT = """你是 DeepTalk Studio 的 Topic Discovery 编辑。你的任务不是追逐热搜，也不是学习或改写其他创作者的稿件，而是从近期公开信息中找出值得做成原创深度口播的候选题。

默认检查最近 72 小时，也可发现过去 14 天内发生、但最近 72 小时有关键新进展的持续事件。每个候选必须先做轻量资料预检：给出 2 到 4 个可打开的 Source Seeds，优先官方、原始文件、公司或监管公告、可靠媒体、研究机构或公开采访。Source Seeds 只是研究入口，不是已确认事实。不要把搜索摘要写成事实。

候选要说明为什么是现在、核心张力、可继续研究的问题、风险和五项评分理由。先产生至少 7 个 Raw Candidate，供程序保守过滤；Raw 数量多不代表最后必须有 5 个合格候选。不要输出总分、排序、推荐标签、播放量、搜索指数或任何无法追溯的热度数字。Creator 的公开标题或主题如可见，只能作为辅助讨论信号；绝不抓取稿件、字幕或独特表达，也不能把创作者观点当事实证据。匿名传言、纯情绪、未经证实的严重指控或高风险且没有可靠资料基础的题材应明确降级。输出必须符合给定 JSON Schema。"""


def build_user_prompt(topic: str, research_handoff: Dict[str, Any] = None) -> str:
    today = datetime.now().astimezone().date().isoformat()
    handoff_context = ""
    if research_handoff:
        seeds = "\n".join(
            f"- {seed.get('url', '')}：{seed.get('why_useful', '')}"
            for seed in research_handoff.get("source_seeds", [])
        )
        handoff_context = f"""

Topic Discovery 交接（仅为研究起点，不是已确认事实）：
- 研究问题：{research_handoff.get('research_question', '')}
- 核心张力：{research_handoff.get('core_tension', '')}
- 为什么现在：{research_handoff.get('why_now', '')}
- 风险：{research_handoff.get('risk_level', '')}；{research_handoff.get('risk_notes', '')}
- Source Seeds：
{seeds or '- 无'}
请重新搜索并核实这些入口；不要把它们直接写成事实。"""
    return f"""研究主题：{topic}
当前日期：{today}

请完成：事件基本事实、时间线、来源分层、多方观点、观点冲突、未决问题、可供深度口播继续开发的原创切入角度，以及给未来 Script Agent 的边界说明。对快速变化的信息搜索到当前日期，并在局限性中说明仍可能变化之处。{handoff_context}"""


def build_discovery_prompt(query: str, category: str = "") -> str:
    today = datetime.now().astimezone().date().isoformat()
    filter_text = f"分类偏好：{category}" if category else "分类偏好：不限，优先保持多样性"
    return f"""Topic Discovery 用户请求：{query}
当前日期：{today}
默认发现窗口：最近 72 小时；也检查过去 14 天内发生且最近 72 小时有关键新进展的持续事件。
{filter_text}

请先给出至少 7 个原始候选，帮助程序在去重和类别多样性后保留 5 个。每个 Source Seed 必须是你在本次公开 Web Search 中实际看见的 URL。不要伪造热度数字，不要把搜索摘要改成已确认事实。"""


def build_fact_check_prompt(report: Dict[str, Any]) -> str:
    queued = [
        claim["id"]
        for claim in report["claims"]
        if claim["risk_level"] in {"high", "critical"}
    ]
    return """独立核查下面这份 Research Draft。
自动排队的高风险 claim：{queued}

Research Draft JSON：
{report}
""".format(
        queued=", ".join(queued) or "无",
        report=json.dumps(report, ensure_ascii=False, separators=(",", ":")),
    )
