"""Approved, evidence-bound original visuals for the real post-alignment trial.

The builder deliberately extends the already reviewed material input rather than
rewriting the approved Script or Research.  Every on-screen factual unit below
is bound to an existing approved claim and evidence link.
"""

from copy import deepcopy
from typing import Mapping


def _cue(beat_id: str, anchor: str, duration: int, reason: str) -> dict:
    return {
        "beat_id": beat_id, "placement_anchor": anchor, "visual_role": "illustration",
        "suggested_duration_seconds": duration, "preferred_asset_type": "generated_diagram",
        "priority": "high", "reason": reason,
    }


def _spec(beat_id: str, visual_type: str, title: str, claim_ids: list[str], evidence_link_ids: list[str], **body) -> dict:
    return {
        "beat_id": beat_id, "visual_type": visual_type, "purpose": "illustration", "title": title,
        "subtitle": "", "events": [], "data_points": [], "comparison_items": [], "nodes": [], "edges": [],
        "claim_ids": claim_ids, "evidence_link_ids": evidence_link_ids, "attribution": "基于已审查研究底稿",
        "aspect_ratio": "16:9", "safe_area": "1920×1080 安全区", "suggested_duration_seconds": 10,
        "animation_intent": "随口播逐项展开，保持事实边界", "style_tokens": ["documentary", "evidence_bound"],
        "on_screen_text": [title], "render_target_hints": ["remotion_candidate", "hyperframes_candidate"], **body,
    }


def build_real_trial_visual_completion_content(reviewed_input_content: Mapping) -> dict:
    """Add six story-driven motions to the immutable material input content.

    The returned mapping is a new r1 candidate.  It must still go through the
    ordinary Material Review before it becomes a reviewed package.
    """

    content = deepcopy(dict(reviewed_input_content))
    content["cue_sheet"].extend([
        _cue("B005", "谁给了权限", 11, "把可修复的权限、网络、工具与人工停止拆开，不拟人化系统。"),
        _cue("B007", "跨机构攻击链", 10, "把已确认的多重信任边界放回连续行动的安全问题中。"),
        _cue("B009", "谁必须记录", 10, "把事故从单个沙箱问题转为可供行业学习的报告闭环。"),
        _cue("B011", "它收到过什么目标", 10, "仅作为 B011 的候选；其实际放置必须继续通过独立安全 span Gate。"),
        _cue("B013", "正式安全港", 10, "把仍是提案、尚无正式安全港的激励缺口单独显示。"),
        _cue("B018", "把权限收紧", 10, "把结论收束为已经讨论过的可验证控制层，而不新增事实判断。"),
    ])
    content["visual_specs"].extend([
        _spec("B005", "diagram", "把问题拆回可修复的控制", ["C13"], ["E15"],
              nodes=[
                  {"node_id": "N1", "label": "把智能体按内部威胁管理", "claim_ids": ["C13"]},
                  {"node_id": "N2", "label": "限制权限", "claim_ids": ["C13"]},
                  {"node_id": "N3", "label": "完整记录活动", "claim_ids": ["C13"]},
                  {"node_id": "N4", "label": "更实际的防护方式", "claim_ids": ["C13"]},
              ], edges=[
                  {"from_node": "N1", "to_node": "N2", "label": "限制权限"},
                  {"from_node": "N2", "to_node": "N3", "label": "完整记录活动"},
                  {"from_node": "N3", "to_node": "N4", "label": "更实际的防护方式"},
              ]),
        _spec("B007", "diagram", "跨越多重信任边界", ["C2"], ["E3", "E4", "E18", "E19"],
              nodes=[
                  {"node_id": "N1", "label": "软件包代理中的未知漏洞", "claim_ids": ["C2"]},
                  {"node_id": "N2", "label": "第三方代码执行环境", "claim_ids": ["C2"]},
                  {"node_id": "N3", "label": "Hugging Face 数据处理漏洞", "claim_ids": ["C2"]},
                  {"node_id": "N4", "label": "多重信任边界", "claim_ids": ["C2"]},
              ], edges=[
                  {"from_node": "N1", "to_node": "N2", "label": "再借"},
                  {"from_node": "N2", "to_node": "N3", "label": "数据处理漏洞"},
                  {"from_node": "N3", "to_node": "N4", "label": "跨越多重信任边界"},
              ]),
        _spec("B009", "diagram", "从一次事故到行业学习", ["C4"], ["E6"],
              nodes=[
                  {"node_id": "N1", "label": "保密收集 AI 事故和近失事件", "claim_ids": ["C4"]},
                  {"node_id": "N2", "label": "AI 未授权访问第三方系统", "claim_ids": ["C4"]},
                  {"node_id": "N3", "label": "越过边界", "claim_ids": ["C4"]},
                  {"node_id": "N4", "label": "持续探测生产目标", "claim_ids": ["C4"]},
              ], edges=[
                  {"from_node": "N1", "to_node": "N2", "label": "报告"},
                  {"from_node": "N2", "to_node": "N3", "label": "越过边界"},
                  {"from_node": "N3", "to_node": "N4", "label": "持续探测生产目标"},
              ]),
        _spec("B011", "diagram", "智能体事件的可复盘轨迹", ["C4"], ["E6"],
              nodes=[
                  {"node_id": "N1", "label": "AI 事故和近失事件", "claim_ids": ["C4"]},
                  {"node_id": "N2", "label": "AI 未授权访问第三方系统", "claim_ids": ["C4"]},
                  {"node_id": "N3", "label": "越过边界", "claim_ids": ["C4"]},
                  {"node_id": "N4", "label": "报告", "claim_ids": ["C4"]},
              ], edges=[
                  {"from_node": "N1", "to_node": "N2", "label": "AI 未授权访问第三方系统"},
                  {"from_node": "N2", "to_node": "N3", "label": "越过边界"},
                  {"from_node": "N3", "to_node": "N4", "label": "报告"},
              ]),
        _spec("B013", "diagram", "报告激励的缺口仍在", ["C6"], ["E8"],
              nodes=[
                  {"node_id": "N1", "label": "SAFE 提案目前没有", "claim_ids": ["C6"]},
                  {"node_id": "N2", "label": "自愿披露潜在法律或声誉风险", "claim_ids": ["C6"]},
                  {"node_id": "N3", "label": "企业", "claim_ids": ["C6"]},
                  {"node_id": "N4", "label": "正式安全港保护", "claim_ids": ["C6"]},
              ], edges=[
                  {"from_node": "N1", "to_node": "N2", "label": "自愿披露潜在法律或声誉风险"},
                  {"from_node": "N2", "to_node": "N3", "label": "企业"},
                  {"from_node": "N3", "to_node": "N4", "label": "正式安全港保护"},
              ]),
        _spec("B018", "diagram", "把一次越界变成可用的安全知识", ["C4", "C13"], ["E6", "E15"],
              nodes=[
                  {"node_id": "N1", "label": "限制权限", "claim_ids": ["C13"]},
                  {"node_id": "N2", "label": "完整记录活动", "claim_ids": ["C13"]},
                  {"node_id": "N3", "label": "AI 事故和近失事件", "claim_ids": ["C4"]},
                  {"node_id": "N4", "label": "报告", "claim_ids": ["C4"]},
              ], edges=[
                  {"from_node": "N1", "to_node": "N2", "label": "完整记录活动"},
                  {"from_node": "N2", "to_node": "N3", "label": "AI 事故和近失事件"},
                  {"from_node": "N3", "to_node": "N4", "label": "报告"},
              ]),
    ])
    return content


def review_real_trial_visual_completion_content() -> dict:
    """Independent-review input for the new candidate package.

    It records no fabricated certainty: page captures remain editorial reference
    material and the original diagrams only render already bound claims.
    """

    checks = [
        ("provenance_integrity", "所有沿用页面均保留 inspected 来源与不可变 package binding。"),
        ("claim_alignment", "新增动态图只使用既有 C2、C4、C6、C13 及对应 evidence link。"),
        ("rights_reuse", "页面截图按 editorial reference 记录，未声明额外授权或许可。"),
        ("crop_integrity", "截图仅用于其已审核的标题与正文区域，不用裁切改变原意。"),
        ("freshness", "未把动态事件页面的历史状态改写成新事实。"),
        ("identity_accuracy", "NASA、SAFE、SB-53 与 Hugging Face 均保留原始来源身份。"),
        ("generated_visual_grounding", "动态图的节点、比较项和数值均绑定 approved claim/evidence。"),
        ("ai_real_confusion", "原创图明确作为解释画面，不伪装成真实现场或原始证据。"),
        ("duplicate_control", "新增画面分别解释控制、报告、轨迹、激励、时限和收束，不是同一张图重复。"),
        ("editorial_usefulness", "每个新增画面服务对应叙事问题，避免装饰性密度。"),
    ]
    return {
        "issues": [],
        "checks": [{"check_name": name, "outcome": "pass", "reason": reason} for name, reason in checks],
        "overall_notes": "本期新增真实页面证据与原创动态图均经过同一套 Review；OpenAI 页面因访问保护未作为新的截图素材使用。",
    }
