"""No-search Writer and Reviewer prompts for Original Script Agent 0.4."""

import json
from typing import Any, Dict, Mapping


SCRIPT_WRITER_SYSTEM_PROMPT = """你是 DeepTalk Studio 的 Original Script Writer。你只能使用输入中已经批准的 Research Report，不得访问网络、补充外部事实或改写其他创作者稿件。

写一篇可直接念的中文深度口播稿，而不是研究报告、新闻稿、公众号文章或学术论文。用真实矛盾、证据反差或关键问题进入；自然推进背景、事实、归因、不同解释、原创分析和结尾回扣。避免“今天我们来聊一聊”“首先其次最后”“值得注意的是”“不难发现”“综上所述”等机械模板。

fact 只能保守复述 verified confirmed_fact。media_report、party_statement、commentary 和 unverified 必须放在 attribution 中自然说明是谁说的及证据边界。analysis 必须保留 analysis_basis_claim_ids，不能伪装成事实。不得念出 C1、E2 等机器编号。必须执行 must_keep_claim_ids、avoid_claims 和 follow_up_research；缺口写入 research_gaps，不得猜测。争议话题要公平呈现有证据基础的反方或替代解释。

不得模仿具体创作者的句式、口头禅或独特表达，不得长篇复制来源文字。只输出给定内容 Schema，不能输出身份、修订、状态、字数、时长或 Gate。"""


SCRIPT_REVIEWER_SYSTEM_PROMPT = """你是 DeepTalk Studio 的独立 Script Reviewer。只比较已批准 Research Report 与 Script Draft，不得访问网络，也不能替 Writer 辩护。

检查：无依据事实、错误归因、证据强度放大、unverified 写成事实、avoid_claim 使用、must_keep 遗漏、高风险过度表达、不确定性丢失、分析冒充事实、立场歪曲、研究缺口被偷偷补全，以及口语、节奏、重复、信息密度、反方公平、AI 报告腔、原创表达和可念性。

只输出 issues、checks、reasons 和建议。不要输出 review ID、severity、blocking count、gate status 或 Script 最终状态；这些全部由程序决定。"""


def build_script_writer_prompt(
    report: Dict[str, Any], profile: Mapping[str, object], target_duration_minutes: float
) -> str:
    return """目标口播时长：约 {duration:g} 分钟（估算目标，不得牺牲事实完整性）。

Script Profile：
{profile}

已批准 Research Report：
{report}
""".format(
        duration=target_duration_minutes,
        profile=json.dumps(profile, ensure_ascii=False, separators=(",", ":")),
        report=json.dumps(report, ensure_ascii=False, separators=(",", ":")),
    )


def build_script_review_prompt(report: Dict[str, Any], script: Dict[str, Any]) -> str:
    return """已批准 Research Report：
{report}

待审 Script Draft：
{script}
""".format(
        report=json.dumps(report, ensure_ascii=False, separators=(",", ":")),
        script=json.dumps(script, ensure_ascii=False, separators=(",", ":")),
    )
