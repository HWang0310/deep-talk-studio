from copy import deepcopy


def valid_report_data():
    data = {
        "schema_version": "0.2",
        "report_id": "RPT-20260810-example",
        "revision": 1,
        "previous_revision": 0,
        "created_at": "2026-08-10T10:00:00+08:00",
        "generated_at": "2026-08-10T10:00:00+08:00",
        "research_mode": "fixture",
        "status": "reviewed",
        "change_summary": "创建用于测试的 Research Report 0.2。",
        "corrections": [],
        "topic": "示例公共事件",
        "research_question": "这个事件的事实基础和主要争议是什么？",
        "scope_summary": "这是用于测试报告契约的虚构示例，不代表真实新闻。",
        "executive_summary": "现有材料确认了事件发生，但对原因存在两种解释。",
        "sources": [
            {
                "id": "S1",
                "title": "机构公告",
                "url": "https://example.com/official",
                "normalized_url": "https://example.com/official",
                "publisher": "示例机构",
                "published_at": "2026-08-09",
                "accessed_at": "2026-08-10",
                "source_type": "official",
                "stance_summary": "确认事件发生并解释处置措施。",
                "credibility_notes": "一手材料，但只代表发布机构立场。",
                "inspection_method": "codex_web_open",
                "provenance_method": "codex_tool_result",
                "provenance_status": "matched",
                "provenance_refs": ["https://example.com/official"],
                "independence_group": "IG1",
                "independence_status": "independent",
                "syndication_of": "",
            },
            {
                "id": "S2",
                "title": "媒体核查报道",
                "url": "https://example.org/report",
                "normalized_url": "https://example.org/report",
                "publisher": "示例媒体",
                "published_at": "2026-08-10",
                "accessed_at": "2026-08-10",
                "source_type": "media",
                "stance_summary": "采访多方并指出仍有信息缺口。",
                "credibility_notes": "包含多方采访，部分细节仍来自匿名信源。",
                "inspection_method": "codex_web_open",
                "provenance_method": "codex_tool_result",
                "provenance_status": "matched",
                "provenance_refs": ["https://example.org/report"],
                "independence_group": "IG2",
                "independence_status": "independent",
                "syndication_of": "",
            },
        ],
        "claims": [
            {
                "id": "C1",
                "claim": "事件在 2026 年 8 月 9 日发生。",
                "classification": "confirmed_fact",
                "confidence": "high",
                "importance": "core",
                "risk_level": "high",
                "risk_factors": ["fast_changing"],
                "verification_status": "verified",
                "notes": "两个相互独立的公开来源一致。",
            },
            {
                "id": "C2",
                "claim": "当事机构称原因是流程故障。",
                "classification": "party_statement",
                "confidence": "medium",
                "importance": "key",
                "risk_level": "medium",
                "risk_factors": ["attribution", "responsibility"],
                "verification_status": "verified",
                "notes": "这是当事方解释，不等于已独立证实。",
            },
            {
                "id": "C3",
                "claim": "网络流传事件由人为操纵造成。",
                "classification": "unverified",
                "confidence": "low",
                "importance": "background",
                "risk_level": "low",
                "risk_factors": ["contested"],
                "verification_status": "unverified",
                "notes": "未找到可核验的一手证据。",
            },
        ],
        "evidence_links": [
            {
                "id": "E1",
                "claim_id": "C1",
                "source_id": "S1",
                "relation": "supports",
                "evidence_summary": "公告记录了事件日期。",
                "evidence_locator": "公告首段",
                "independence_group": "IG1",
                "verification_notes": "已打开原始公告。",
                "verified_in_review": True,
            },
            {
                "id": "E2",
                "claim_id": "C1",
                "source_id": "S2",
                "relation": "supports",
                "evidence_summary": "媒体独立报道了同一日期。",
                "evidence_locator": "报道时间线",
                "independence_group": "IG2",
                "verification_notes": "已打开报道。",
                "verified_in_review": True,
            },
            {
                "id": "E3",
                "claim_id": "C2",
                "source_id": "S1",
                "relation": "attributes",
                "evidence_summary": "公告将流程故障作为机构解释。",
                "evidence_locator": "公告第二段",
                "independence_group": "IG1",
                "verification_notes": "只证明机构说过，不证明原因成立。",
                "verified_in_review": True,
            },
            {
                "id": "E4",
                "claim_id": "C3",
                "source_id": "S2",
                "relation": "context",
                "evidence_summary": "报道提到网络传言但未发现原始证据。",
                "evidence_locator": "报道核查部分",
                "independence_group": "IG2",
                "verification_notes": "只能作为传言存在的背景。",
                "verified_in_review": True,
            },
        ],
        "timeline": [
            {
                "date": "2026-08-09",
                "event": "事件发生并由机构发布首次说明。",
                "claim_ids": ["C1", "C2"],
                "evidence_link_ids": ["E1", "E2", "E3"],
            }
        ],
        "perspectives": [
            {
                "id": "P1",
                "actor": "当事机构",
                "position": "事件属于流程故障。",
                "reasoning": "机构引用内部检查结果。",
                "claim_ids": ["C2"],
                "evidence_link_ids": ["E3"],
                "category": "party",
            }
        ],
        "conflicts": [
            {
                "question": "这是偶发故障还是管理问题？",
                "side_a": "机构认为是单次流程故障。",
                "side_b": "评论者认为仍需追问制度责任。",
                "evidence_state": "目前只能确认事件和机构说法，责任归因证据不足。",
                "claim_ids": ["C1", "C2"],
                "evidence_link_ids": ["E1", "E2", "E3"],
            }
        ],
        "open_questions": [
            {
                "question": "内部检查是否会公开完整证据？",
                "why_it_matters": "决定原因判断能否被独立复核。",
                "suggested_next_step": "持续查看后续公告和监管文件。",
            }
        ],
        "angles": [
            {
                "title": "从一次事故看公开解释的证据边界",
                "core_question": "公众应如何区分事实、解释与推测？",
                "why_now": "事件正在形成相互冲突的网络叙事。",
                "audience_value": "提供一套判断热点信息的方法。",
                "risks": "不能在证据不足时归责个人。",
                "required_claim_ids": ["C1", "C2", "C3"],
            }
        ],
        "fact_check": {
            "review_id": "FCR-20260810-example",
            "reviewed_at": "2026-08-10T11:00:00+08:00",
            "status": "completed",
            "checked_claim_ids": ["C1", "C2"],
            "unresolved_claim_ids": [],
        },
        "quality_summary": {
            "claim_count": 3,
            "sourced_claim_count": 3,
            "claim_source_coverage": 1.0,
            "high_risk_claim_count": 1,
            "high_risk_checked_count": 1,
            "high_risk_fact_check_coverage": 1.0,
            "confirmed_fact_count": 1,
            "confirmed_fact_independent_count": 1,
            "confirmed_fact_independent_coverage": 1.0,
            "source_type_diversity_count": 2,
            "duplicate_source_count": 0,
            "syndicated_source_count": 0,
            "unresolved_high_risk_count": 0,
            "unsourced_attribution_count": 0,
            "provenance_matched_source_count": 2,
            "provenance_match_rate": 1.0,
            "gate_status": "pass",
            "gate_reasons": [],
        },
        "limitations": ["示例来源为虚构网址，仅用于测试格式。"],
        "approval_gate": {
            "status": "pending",
            "requires_user_confirmation": True,
            "high_risk_claim_ids": ["C1"],
            "user_confirmation": "",
            "ready_for_script": False,
        },
        "handoff_to_script_agent": {
            "recommended_angle": "从信息分层而不是责任定性切入。",
            "central_tension": "公众需要解释，但现有证据不足以完成归因。",
            "must_keep_claim_ids": ["C1", "C2", "C3"],
            "avoid_claims": ["不要断言人为操纵已经得到证实。"],
            "follow_up_research": ["检查后续监管通报。"],
        },
    }
    return deepcopy(data)


def valid_v01_report_data():
    data = {
        "schema_version": "0.1",
        "topic": "示例公共事件",
        "research_question": "这个事件的事实基础和主要争议是什么？",
        "generated_at": "2026-08-10T10:00:00+08:00",
        "scope_summary": "V0.1 虚构示例。",
        "executive_summary": "事件发生，但原因仍有争议。",
        "sources": [
            {
                "id": "S1",
                "title": "机构公告",
                "url": "https://example.com/official?utm_source=test",
                "publisher": "示例机构",
                "published_at": "2026-08-09",
                "accessed_at": "2026-08-10",
                "source_type": "official",
                "stance_summary": "确认事件发生。",
                "credibility_notes": "一手材料但有机构立场。",
            }
        ],
        "claims": [
            {
                "id": "C1",
                "claim": "事件发生。",
                "classification": "confirmed_fact",
                "confidence": "high",
                "source_ids": ["S1"],
                "notes": "旧版主张。",
            }
        ],
        "timeline": [
            {
                "date": "2026-08-09",
                "event": "事件发生。",
                "claim_ids": ["C1"],
                "source_ids": ["S1"],
            }
        ],
        "perspectives": [],
        "conflicts": [],
        "open_questions": [],
        "angles": [
            {
                "title": "证据边界",
                "core_question": "事实是什么？",
                "why_now": "事件正在变化。",
                "audience_value": "帮助判断。",
                "risks": "不要过度归因。",
                "required_claim_ids": ["C1"],
            }
        ],
        "fact_check_notes": [
            {
                "claim_id": "C1",
                "status": "verified",
                "explanation": "旧版同一研究步骤自查。",
            }
        ],
        "limitations": ["尚未独立事实核查。"],
        "handoff_to_script_agent": {
            "recommended_angle": "信息分层。",
            "central_tension": "事实与解释。",
            "must_keep_claim_ids": ["C1"],
            "avoid_claims": [],
            "follow_up_research": ["独立核查。"],
        },
    }
    return deepcopy(data)


def valid_fact_check_data(report=None):
    report = report or valid_report_data()
    return {
        "artifact_version": "0.2",
        "review_id": "FCR-20260810-independent",
        "report_id": report["report_id"],
        "report_revision": report["revision"],
        "created_at": "2026-08-10T11:00:00+08:00",
        "research_mode": report["research_mode"],
        "status": "completed",
        "tool_provenance": {
            "search_call_ids": ["ws_fact_1"],
            "search_queries": ["示例公共事件 反证"],
            "consulted_urls": [
                "https://example.com/official",
                "https://example.org/report",
            ],
            "citation_urls": ["https://example.org/report"],
        },
        "queued_claim_ids": ["C1"],
        "new_sources": [],
        "evidence_links": [],
        "checks": [
            {
                "claim_id": "C1",
                "outcome": "verified",
                "original_classification": "confirmed_fact",
                "recommended_classification": "confirmed_fact",
                "searched_new_sources": True,
                "counterevidence_summary": "主动搜索但未发现足以推翻日期的反证。",
                "source_ids": ["S1", "S2"],
                "independence_assessment": "independent",
                "verification_notes": "复查了两个独立来源。",
            }
        ],
        "overall_notes": "关键事实通过独立复查。",
    }


def valid_codex_draft_input():
    report = valid_report_data()
    fields = (
        "topic",
        "research_question",
        "scope_summary",
        "executive_summary",
        "sources",
        "claims",
        "evidence_links",
        "timeline",
        "perspectives",
        "conflicts",
        "open_questions",
        "angles",
        "limitations",
        "handoff_to_script_agent",
    )
    data = {field: deepcopy(report[field]) for field in fields}
    for source in data["sources"]:
        source.pop("normalized_url")
        source.pop("independence_group")
    for claim in data["claims"]:
        claim.pop("verification_status")
    for link in data["evidence_links"]:
        link.pop("independence_group")
        link.pop("verified_in_review")
    return data
