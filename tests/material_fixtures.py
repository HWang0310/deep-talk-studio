from copy import deepcopy

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_review import prepare_script_review
from deeptalk_studio.script_validation import prepare_script_draft
from tests.fixtures import (
    approved_report_data,
    valid_script_content,
    valid_script_review_content,
)


def reviewed_inputs():
    report = ResearchReport.from_dict(approved_report_data())
    profile = load_script_profile()
    draft = prepare_script_draft(
        valid_script_content(),
        report,
        profile,
        created_at="2026-08-10T13:00:00+08:00",
        script_id="SCR-material-test",
    )
    review = prepare_script_review(
        valid_script_review_content(),
        report,
        draft,
        profile,
        created_at="2026-08-10T14:00:00+08:00",
        review_id="SRV-material-test",
        review_mode="fixture",
    )
    return report, review.script, review.artifact


def valid_material_content():
    anchor = "事件发生在八月九日"
    return {
        "cue_sheet": [
            {
                "beat_id": "B001",
                "placement_anchor": anchor,
                "visual_role": "evidence",
                "suggested_duration_seconds": 6,
                "preferred_asset_type": "official_document",
                "priority": "high",
                "reason": "用公开文件确认发生日期。",
            },
            {
                "beat_id": "B003",
                "placement_anchor": "第三种选择",
                "visual_role": "illustration",
                "suggested_duration_seconds": 8,
                "preferred_asset_type": "generated_timeline",
                "priority": "medium",
                "reason": "把事实、解释与猜测的关系可视化。",
            },
        ],
        "materials": [
            {
                "title": "示例机构公开文件",
                "source_url": "https://example.com/official.pdf",
                "page_url": "https://example.com/official",
                "publisher_creator": "示例机构",
                "asset_type": "official_document",
                "published_at": "2026-08-09",
                "intended_role": "evidence",
                "cue_numbers": [1],
                "claim_ids": ["C1"],
                "evidence_link_ids": ["E1"],
                "suggested_usage": "在日期口播时展示文件标题和日期。",
                "caption": "示例机构于 8 月 9 日发布的公开文件。",
                "illustrative_only": False,
                "claimed_rights_status": "official_press_asset",
                "claimed_rights_basis": "页面明确列为媒体资料。",
                "claimed_license_url": "https://example.com/press-terms",
                "relevance": 5,
                "grounding_strength": 5,
                "visual_clarity": 4,
                "reuse_safety": 5,
                "acquisition_effort": 2,
                "ranking_reason": "直接对应日期事实，且有清楚公开文件画面。",
                "capture": {
                    "page_number": 1,
                    "capture_region": "标题与发布日期区域",
                    "source_context": "公开文件第一页",
                    "what_it_proves": "文件在页面所示日期公开。",
                    "what_it_does_not_prove": "不证明机构给出的原因正确。",
                },
                "video_reference": {
                    "title": "",
                    "start_seconds": 0,
                    "end_seconds": 0,
                    "usage_reason": "",
                },
            }
        ],
        "visual_specs": [
            {
                "beat_id": "B003",
                "visual_type": "timeline",
                "purpose": "context",
                "title": "事件、解释与核查",
                "subtitle": "只展示 Research 已批准的信息",
                "events": [
                    {
                        "date": "2026-08-09",
                        "label": "事件发生并由机构发布首次说明。",
                        "claim_ids": ["C1", "C2"],
                        "evidence_link_ids": ["E1", "E2", "E3"],
                    }
                ],
                "data_points": [],
                "comparison_items": [],
                "nodes": [],
                "edges": [],
                "claim_ids": ["C1", "C2"],
                "evidence_link_ids": ["E1", "E2", "E3"],
                "attribution": "DeepTalk Studio，数据来自已批准 Research Report",
                "aspect_ratio": "16:9",
                "safe_area": "5%",
                "suggested_duration_seconds": 8,
                "animation_intent": "按日期顺序淡入，静态输出保持完整可读。",
                "style_tokens": ["clean", "high-contrast", "dense"],
                "on_screen_text": ["事实", "解释", "仍待核查"],
                "render_target_hints": ["static", "remotion_candidate", "hyperframes_candidate"],
            }
        ],
        "gaps": ["没有为网络传言找到适合作证据的可用画面。"],
        "research_update_signals": [],
        "warnings": [],
    }


def inspection_manifest():
    return {
        "entries": [
            {
                "url": "https://example.com/official.pdf",
                "inspected_at": "2026-08-11T09:00:00+08:00",
                "inspection_method": "codex_web_open",
                "tool_reference": "open:official-pdf",
            },
            {
                "url": "https://example.com/press-terms",
                "inspected_at": "2026-08-11T09:05:00+08:00",
                "inspection_method": "codex_web_open",
                "tool_reference": "open:press-terms",
            }
        ]
    }


def rights_manifest():
    return {
        "entries": [
            {
                "url": "https://example.com/official.pdf",
                "rights_status": "official_press_asset",
                "rights_basis": "媒体资料页明确允许新闻报道使用。",
                "rights_evidence_url": "https://example.com/press-terms",
                "license_url": "https://example.com/press-terms",
                "verified_at": "2026-08-11T09:05:00+08:00",
                "tool_reference": "open:press-terms",
            }
        ]
    }


def copy_content():
    return deepcopy(valid_material_content())
