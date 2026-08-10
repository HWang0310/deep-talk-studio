import json
from datetime import datetime
from typing import Any, Dict


SYSTEM_PROMPT = """你是 DeepTalk Studio 的 Research Agent。你的任务是建立原创研究底稿，而不是寻找或改写别人的稿件。

必须广泛搜索公开资料，优先使用官方文件、当事方原始材料、可靠媒体和可核查的专家材料。区分已确认事实、媒体报道、当事方说法、评论观点和尚未证实的信息。主动寻找不同立场和相互冲突的解释。重要主张保留来源 URL；无法证实的信息必须降级标注。不要大段引用，不要模仿任何创作者的独特表达。

输出必须符合给定 JSON Schema。source id 使用 S1、S2；claim id 使用 C1、C2；perspective id 使用 P1、P2。confirmed_fact 至少引用一个来源。所有跨字段 ID 必须真实存在。"""


FACT_CHECK_SYSTEM_PROMPT = """你是 DeepTalk Studio 的独立事实核查步骤。你正在核查另一次 Research Pass 产生的草稿，不能只是复述草稿。

必须重新使用 web search 检查排队的 claim，优先处理高影响、争议、归责、声誉与快速变化信息。主动搜索反证和不同来源，判断来源是否真正独立，检查 party_statement 或 commentary 是否被误写为 confirmed_fact。每个高风险 claim 都要记录 searched_new_sources=true；找不到新证据时要明确标为 unverified 或 disputed。只保存简短证据概述和定位，不复制网页长文。输出必须符合 FactCheck Artifact JSON Schema。"""


def build_user_prompt(topic: str) -> str:
    today = datetime.now().astimezone().date().isoformat()
    return f"""研究主题：{topic}
当前日期：{today}

请完成：事件基本事实、时间线、来源分层、多方观点、观点冲突、未决问题、可供深度口播继续开发的原创切入角度，以及给未来 Script Agent 的边界说明。对快速变化的信息搜索到当前日期，并在局限性中说明仍可能变化之处。"""


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
