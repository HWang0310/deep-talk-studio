"""Story-led audit and safe opportunity definitions for the real user episode.

This is episode data, not a new interpretation of Research: phrase boundaries
only select portions of the reviewed Script, and their actual timing is always
projected later from the approved global alignment.
"""

from typing import Mapping

from .post_alignment_visual_plan import PostAlignmentVisualPlanError


REAL_TRIAL_AUDIT_NOTES = {
    "B001": ("用真人建立问题与不确定性，不以模拟入侵画面抢占事实判断。", ["真人口播"], []),
    "B002": ("交代已确认事件；先给时间线，再给 Hugging Face 技术复盘页面。", ["V001", "M002"], []),
    "B003": ("解释高层越界路径；用原创结构图并保留技术细节尚未完全公开的边界。", ["V002", "M002"], []),
    "B004": ("保留真人说明受影响方说法与外部审计边界，避免把公司自查画成结论。", ["真人口播"], []),
    "B005": ("把拟人化叙事转成权限、网络、工具和人工停止等可修复控制。", ["V004"], []),
    "B006": ("用 AISI 官方研究图帮助解释测试条件与日常环境不能直接外推。", ["M003"], []),
    "B007": ("把连续行动放回已确认的多重信任边界，不夸张为虚构攻击现场。", ["V005"], []),
    "B008": ("保留真人呈现行业实践观点及其非普遍结论的限定。", ["真人口播"], []),
    "B009": ("由原创报告闭环解释为何单个沙箱修复不足以形成行业学习。", ["V006"], []),
    "B010": ("用 SAFE 原始草案页面证明报告触发条件与记录要求，明确它仍是草案。", ["M004"], []),
    "B011": ("候选轨迹图有解释价值，但本 Beat 仍需人工复核；不安全 span 不进入预览。", ["V007（候选）"], ["B011 全段存在对齐不确定性"]),
    "B012": ("保留真人讨论透明、保护与受影响方知情之间的张力。", ["真人口播"], []),
    "B013": ("用原创激励缺口图说明 SAFE 仍是提案且尚无正式安全港。", ["V008"], []),
    "B014": ("用 NASA 官方制度说明给出自愿、保密、去标识化与有限豁免的原始证据。", ["M005"], []),
    "B015": ("用 NASA 限制条件页面校正“主动说就免责”的误解。", ["M006"], []),
    "B016": ("用加州 SB-53 官方摘录核对法定报告时限与适用边界。", ["M007"], []),
    "B017": ("用已审查的三机制对照图解释分层，而不是把它们假装成两个阵营。", ["V003"], []),
    "B018": ("回到真人完成克制结论；只在已对齐的 Script 段落短暂展示控制闭环，尾部即兴口播保持真人。", ["V009", "真人尾段"], []),
}


_OPPORTUNITIES = (
    ("B002", "二零二六年七月，OpenAI在一次内部网络能力评估中，关闭了部分生产环境会使用的防护。", "original_motion", "context", "事件时间线", {"visual_id": "V001"}),
    ("B002", "场原本用于测量模型最大攻击能力的评估", "real_material", "evidence", "Hugging Face 技术复盘", {"material_id": "M002"}),
    ("B003", "目前公开出来的高层攻击链，大致分成三步。", "original_motion", "explanation", "高层越界路径", {"visual_id": "V002"}),
    ("B003", "一份第三方完整调查彻底还原", "real_material", "context", "技术复盘的公开边界", {"material_id": "M002"}),
    ("B005", "什么异常动作没有更早触发人工停止", "original_motion", "explanation", "可修复控制", {"visual_id": "V004"}),
    ("B006", "一次测试里出现的行为，不能原封不动地推导成日常产品里一定会发生的结果。", "real_material", "evidence", "AISI 环境因素研究", {"material_id": "M003"}),
    ("B007", "串成一条跨机构攻击链。", "original_motion", "explanation", "跨越多重信任边界", {"visual_id": "V005"}),
    ("B009", "场险些造成更大后果的事件", "original_motion", "explanation", "事故学习闭环", {"visual_id": "V006"}),
    ("B010", "尽量保存提示词", "real_material", "evidence", "SAFE 草案原文", {"material_id": "M004"}),
    ("B011", "它收到过什么目标，调用了哪些工具，权限在哪一步扩大，系统在什么时候出现异常信号，人工又在什么时候介入。", "original_motion", "explanation", "可复盘轨迹（待人工复核）", {"visual_id": "V007"}),
    ("B013", "SAFE目前只是提案，不是已经运行的强制制度。", "original_motion", "explanation", "报告激励缺口", {"visual_id": "V008"}),
    ("B014", "掉能够识别个人的信息", "real_material", "evidence", "NASA ASRS 制度说明", {"material_id": "M005"}),
    ("B015", "事故、犯罪、故意违规不在保护范围内，处罚豁免还受到报告时限和既往违规记录等条件限制。", "real_material", "evidence", "NASA ASRS 限制条件", {"material_id": "M006"}),
    ("B016", "一般要在十五天内报告；如果存在迫在眉睫的死亡或重伤风险，则要在二十四小时内向适当机构披露。", "real_material", "evidence", "SB-53 官方法条", {"material_id": "M007"}),
    ("B017", "发现它们不是三选一", "original_motion", "explanation", "三种事故报告机制", {"visual_id": "V003"}),
    ("B018", "把权限收紧，把行动留痕，把异常及时上报，把别人踩过的坑变成全行业都能使用的安全知识。", "original_motion", "conclusion", "控制与学习闭环", {"visual_id": "V009"}),
)


def build_real_trial_opportunities(script: Mapping, alignment: Mapping) -> list[dict]:
    """Locate exact approved phrases; no phrase means fail closed before timing."""

    beats = {beat.get("beat_id"): beat for beat in script.get("beats", [])}
    offsets = {
        item.get("beat_id"): int(item.get("intended_char_start"))
        for item in alignment.get("beat_timeline", [])
        if item.get("beat_id") and str(item.get("intended_char_start", "")).isdigit()
    }
    result = []
    for index, (beat_id, phrase, visual_kind, role, target, source_binding) in enumerate(_OPPORTUNITIES, 1):
        narration = str(beats.get(beat_id, {}).get("narration", "")); found = narration.find(phrase)
        if found < 0 or beat_id not in offsets:
            raise PostAlignmentVisualPlanError(f"已审查 Script 中找不到 Visual Plan 短语：{beat_id}")
        result.append({
            "opportunity_id": f"OP{index:03d}", "beat_id": beat_id,
            "semantic_char_start": offsets[beat_id] + found,
            "semantic_char_end": offsets[beat_id] + found + len(phrase),
            "visual_kind": visual_kind, "visual_role": role, "semantic_target": target,
            "source_binding": dict(source_binding),
        })
    return result


def build_real_trial_audit_notes() -> dict:
    return {
        beat_id: {"semantic_purpose": purpose, "a_roll_rationale": purpose,
                  "existing_assets": existing, "missing_assets": missing}
        for beat_id, (purpose, existing, missing) in REAL_TRIAL_AUDIT_NOTES.items()
    }
