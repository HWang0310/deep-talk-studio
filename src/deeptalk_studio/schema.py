"""Executable JSON contracts for DeepTalk Studio artifacts."""


def _string(allow_empty=False):
    schema = {"type": "string"}
    if not allow_empty:
        schema["minLength"] = 1
    return schema


def _string_array():
    return {"type": "array", "items": _string(), "uniqueItems": True}


def _array(items):
    return {"type": "array", "items": items}


def _enum(values):
    return {"type": "string", "enum": values}


def _integer(minimum=0):
    return {"type": "integer", "minimum": minimum}


def _ratio():
    return {"type": "number", "minimum": 0, "maximum": 1}


def _number(minimum=0, maximum=None):
    schema = {"type": "number", "minimum": minimum}
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _object(properties, optional=()):
    return {
        "type": "object",
        "properties": properties,
        "required": [key for key in properties if key not in optional],
        "additionalProperties": False,
    }


SOURCE_SCHEMA = _object(
    {
        "id": _string(),
        "title": _string(),
        "url": _string(),
        "normalized_url": _string(),
        "publisher": _string(),
        "published_at": _string(allow_empty=True),
        "accessed_at": _string(),
        "source_type": _enum(
            [
                "official",
                "primary",
                "media",
                "academic",
                "expert",
                "creator",
                "social",
                "other",
            ]
        ),
        "stance_summary": _string(),
        "credibility_notes": _string(),
        "inspection_method": _enum(
            ["openai_web_search_tool", "codex_web_open", "manual_open", "not_inspected"]
        ),
        "provenance_method": _enum(
            [
                "web_search_action_source",
                "url_citation",
                "codex_tool_result",
                "user_supplied",
                "migration",
            ]
        ),
        "provenance_status": _enum(["matched", "partial", "unmatched"]),
        "provenance_refs": _string_array(),
        "independence_group": _string(),
        "independence_status": _enum(
            ["independent", "related", "syndicated", "duplicate", "unknown"]
        ),
        "syndication_of": _string(allow_empty=True),
    }
)


CLAIM_SCHEMA = _object(
    {
        "id": _string(),
        "claim": _string(),
        "classification": _enum(
            [
                "confirmed_fact",
                "media_report",
                "party_statement",
                "commentary",
                "unverified",
            ]
        ),
        "confidence": _enum(["high", "medium", "low"]),
        "importance": _enum(["background", "key", "core"]),
        "risk_level": _enum(["low", "medium", "high", "critical"]),
        "risk_factors": {
            "type": "array",
            "items": _enum(
                [
                    "contested",
                    "attribution",
                    "reputation",
                    "fast_changing",
                    "responsibility",
                    "causal",
                    "legal",
                    "financial",
                    "safety",
                ]
            ),
            "uniqueItems": True,
        },
        "verification_status": _enum(
            ["not_checked", "verified", "partially_verified", "disputed", "unverified"]
        ),
        "notes": _string(allow_empty=True),
    }
)


EVIDENCE_LINK_SCHEMA = _object(
    {
        "id": _string(),
        "claim_id": _string(),
        "source_id": _string(),
        "relation": _enum(["supports", "contradicts", "attributes", "context"]),
        "evidence_summary": _string(),
        "evidence_locator": _string(),
        "independence_group": _string(),
        "verification_notes": _string(allow_empty=True),
        "verified_in_review": {"type": "boolean"},
    }
)


QUALITY_SUMMARY_SCHEMA = _object(
    {
        "claim_count": _integer(),
        "sourced_claim_count": _integer(),
        "claim_source_coverage": _ratio(),
        "high_risk_claim_count": _integer(),
        "high_risk_checked_count": _integer(),
        "high_risk_fact_check_coverage": _ratio(),
        "confirmed_fact_count": _integer(),
        "confirmed_fact_independent_count": _integer(),
        "confirmed_fact_independent_coverage": _ratio(),
        "source_type_diversity_count": _integer(),
        "duplicate_source_count": _integer(),
        "syndicated_source_count": _integer(),
        "unresolved_high_risk_count": _integer(),
        "unsourced_attribution_count": _integer(),
        "provenance_matched_source_count": _integer(),
        "provenance_match_rate": _ratio(),
        "gate_status": _enum(["pass", "fail"]),
        "gate_reasons": _string_array(),
    }
)


REPORT_JSON_SCHEMA = _object(
    {
        "schema_version": _enum(["0.2"]),
        "report_id": _string(),
        "revision": _integer(1),
        "previous_revision": _integer(),
        "created_at": _string(),
        "generated_at": _string(),
        "research_mode": _enum(["codex_skill", "openai_api", "manual", "migration", "fixture"]),
        "status": _enum(["draft", "fact_check_pending", "reviewed", "ready_for_script"]),
        "change_summary": _string(),
        "corrections": _array(
            _object(
                {
                    "claim_id": _string(),
                    "summary": _string(),
                    "reason": _string(),
                    "source_ids": _string_array(),
                }
            )
        ),
        "topic": _string(),
        "research_question": _string(),
        "scope_summary": _string(),
        "executive_summary": _string(),
        "sources": _array(SOURCE_SCHEMA),
        "claims": _array(CLAIM_SCHEMA),
        "evidence_links": _array(EVIDENCE_LINK_SCHEMA),
        "timeline": _array(
            _object(
                {
                    "date": _string(),
                    "event": _string(),
                    "claim_ids": _string_array(),
                    "evidence_link_ids": _string_array(),
                }
            )
        ),
        "perspectives": _array(
            _object(
                {
                    "id": _string(),
                    "actor": _string(),
                    "position": _string(),
                    "reasoning": _string(),
                    "claim_ids": _string_array(),
                    "evidence_link_ids": _string_array(),
                    "category": _enum(["party", "media", "expert", "creator", "public", "other"]),
                }
            )
        ),
        "conflicts": _array(
            _object(
                {
                    "question": _string(),
                    "side_a": _string(),
                    "side_b": _string(),
                    "evidence_state": _string(),
                    "claim_ids": _string_array(),
                    "evidence_link_ids": _string_array(),
                }
            )
        ),
        "open_questions": _array(
            _object(
                {
                    "question": _string(),
                    "why_it_matters": _string(),
                    "suggested_next_step": _string(),
                }
            )
        ),
        "angles": _array(
            _object(
                {
                    "title": _string(),
                    "core_question": _string(),
                    "why_now": _string(),
                    "audience_value": _string(),
                    "risks": _string(),
                    "required_claim_ids": _string_array(),
                }
            )
        ),
        "fact_check": _object(
            {
                "review_id": _string(allow_empty=True),
                "reviewed_at": _string(allow_empty=True),
                "status": _enum(["not_run", "completed", "needs_follow_up"]),
                "checked_claim_ids": _string_array(),
                "unresolved_claim_ids": _string_array(),
            }
        ),
        "quality_summary": QUALITY_SUMMARY_SCHEMA,
        "limitations": _string_array(),
        "approval_gate": _object(
            {
                "status": _enum(["pending", "approved", "rejected"]),
                "requires_user_confirmation": {"type": "boolean"},
                "high_risk_claim_ids": _string_array(),
                "user_confirmation": _string(allow_empty=True),
                "ready_for_script": {"type": "boolean"},
            }
        ),
        "handoff_to_script_agent": _object(
            {
                "recommended_angle": _string(),
                "central_tension": _string(),
                "must_keep_claim_ids": _string_array(),
                "avoid_claims": _string_array(),
                "follow_up_research": _string_array(),
            }
        ),
    }
)


CODEX_DRAFT_JSON_SCHEMA = _object(
    {
        "topic": REPORT_JSON_SCHEMA["properties"]["topic"],
        "research_question": REPORT_JSON_SCHEMA["properties"]["research_question"],
        "scope_summary": REPORT_JSON_SCHEMA["properties"]["scope_summary"],
        "executive_summary": REPORT_JSON_SCHEMA["properties"]["executive_summary"],
        "sources": _array(
            _object(
                {
                    key: value
                    for key, value in SOURCE_SCHEMA["properties"].items()
                    if key not in {"normalized_url", "independence_group"}
                }
            )
        ),
        "claims": _array(
            _object(
                {
                    key: value
                    for key, value in CLAIM_SCHEMA["properties"].items()
                    if key != "verification_status"
                }
            )
        ),
        "evidence_links": _array(
            _object(
                {
                    key: value
                    for key, value in EVIDENCE_LINK_SCHEMA["properties"].items()
                    if key not in {"independence_group", "verified_in_review"}
                }
            )
        ),
        "timeline": REPORT_JSON_SCHEMA["properties"]["timeline"],
        "perspectives": REPORT_JSON_SCHEMA["properties"]["perspectives"],
        "conflicts": REPORT_JSON_SCHEMA["properties"]["conflicts"],
        "open_questions": REPORT_JSON_SCHEMA["properties"]["open_questions"],
        "angles": REPORT_JSON_SCHEMA["properties"]["angles"],
        "limitations": REPORT_JSON_SCHEMA["properties"]["limitations"],
        "handoff_to_script_agent": REPORT_JSON_SCHEMA["properties"]["handoff_to_script_agent"],
    }
)


API_RESEARCH_DRAFT_JSON_SCHEMA = _object(
    {
        "topic": REPORT_JSON_SCHEMA["properties"]["topic"],
        "research_question": REPORT_JSON_SCHEMA["properties"]["research_question"],
        "scope_summary": REPORT_JSON_SCHEMA["properties"]["scope_summary"],
        "executive_summary": REPORT_JSON_SCHEMA["properties"]["executive_summary"],
        "sources": _array(
            _object(
                {
                    key: value
                    for key, value in SOURCE_SCHEMA["properties"].items()
                    if key
                    not in {
                        "normalized_url",
                        "inspection_method",
                        "provenance_method",
                        "provenance_status",
                        "provenance_refs",
                        "independence_group",
                    }
                }
            )
        ),
        "claims": _array(
            _object(
                {
                    key: value
                    for key, value in CLAIM_SCHEMA["properties"].items()
                    if key != "verification_status"
                }
            )
        ),
        "evidence_links": _array(
            _object(
                {
                    key: value
                    for key, value in EVIDENCE_LINK_SCHEMA["properties"].items()
                    if key not in {"independence_group", "verified_in_review"}
                }
            )
        ),
        "timeline": REPORT_JSON_SCHEMA["properties"]["timeline"],
        "perspectives": REPORT_JSON_SCHEMA["properties"]["perspectives"],
        "conflicts": REPORT_JSON_SCHEMA["properties"]["conflicts"],
        "open_questions": REPORT_JSON_SCHEMA["properties"]["open_questions"],
        "angles": REPORT_JSON_SCHEMA["properties"]["angles"],
        "limitations": REPORT_JSON_SCHEMA["properties"]["limitations"],
        "handoff_to_script_agent": REPORT_JSON_SCHEMA["properties"]["handoff_to_script_agent"],
    }
)


FACT_CHECK_JSON_SCHEMA = _object(
    {
        "artifact_version": _enum(["0.2"]),
        "review_id": _string(),
        "report_id": _string(),
        "report_revision": _integer(1),
        "created_at": _string(),
        "research_mode": _enum(["codex_skill", "openai_api", "manual", "fixture"]),
        "status": _enum(["completed", "needs_follow_up"]),
        "tool_provenance": _object(
            {
                "search_call_ids": _string_array(),
                "search_queries": _string_array(),
                "consulted_urls": _string_array(),
                "citation_urls": _string_array(),
            }
        ),
        "queued_claim_ids": _string_array(),
        "new_sources": _array(SOURCE_SCHEMA),
        "evidence_links": _array(EVIDENCE_LINK_SCHEMA),
        "checks": _array(
            _object(
                {
                    "claim_id": _string(),
                    "outcome": _enum(["verified", "partially_verified", "disputed", "unverified"]),
                    "original_classification": CLAIM_SCHEMA["properties"]["classification"],
                    "recommended_classification": CLAIM_SCHEMA["properties"]["classification"],
                    "searched_new_sources": {"type": "boolean"},
                    "counterevidence_summary": _string(),
                    "source_ids": _string_array(),
                    "independence_assessment": _enum(
                        ["independent", "correlated", "unknown", "not_applicable"]
                    ),
                    "verification_notes": _string(),
                }
            )
        ),
        "overall_notes": _string(),
    }
)


# Topic Discovery is intentionally a separate upstream artifact.  The raw schema
# is the limited judgment surface allowed to an API model or the Codex Skill;
# identity, preflight result, label, total score and ordering are code-owned.
DISCOVERY_SCORE_SCHEMA = _object({"score": _integer(), "reason": _string()})

DISCOVERY_SOURCE_SEED_RAW_SCHEMA = _object(
    {
        "url": _string(),
        "publisher": _string(),
        "published_at": _string(allow_empty=True),
        "source_type": SOURCE_SCHEMA["properties"]["source_type"],
        "why_useful": _string(),
    }
)

DISCOVERY_SOURCE_SEED_SCHEMA = _object(
    {
        **DISCOVERY_SOURCE_SEED_RAW_SCHEMA["properties"],
        "provenance_status": _enum(["matched", "unmatched", "manual_open"]),
    }
)

DISCOVERY_INSPECTION_ENTRY_SCHEMA = _object(
    {
        "url": _string(),
        "tool_reference": _string(allow_empty=True),
        "inspected_at": _string(),
    },
    optional=("tool_reference",),
)

DISCOVERY_SEED_PROVENANCE_SCHEMA = _object(
    {
        "matched_urls": _string_array(),
        "codex_inspections": _array(DISCOVERY_INSPECTION_ENTRY_SCHEMA),
    }
)

DISCOVERY_SCORE_BREAKDOWN_RAW_SCHEMA = _object(
    {
        "researchability": DISCOVERY_SCORE_SCHEMA,
        "depth_conflict": DISCOVERY_SCORE_SCHEMA,
        "freshness": DISCOVERY_SCORE_SCHEMA,
        "channel_fit": DISCOVERY_SCORE_SCHEMA,
        "attention_signal": DISCOVERY_SCORE_SCHEMA,
    }
)

DISCOVERY_ELIGIBILITY_SIGNALS_SCHEMA = _object(
    {
        "anonymous_rumor_only": {"type": "boolean"},
        "public_evidence_available": {"type": "boolean"},
        "material_unverified_allegation": {"type": "boolean"},
        "emotion_only": {"type": "boolean"},
        "creator_imitation_dependency": {"type": "boolean"},
        "major_fast_event": {"type": "boolean"},
        "research_directions": _integer(),
    }
)

DISCOVERY_CANDIDATE_RAW_SCHEMA = _object(
    {
        "title": _string(),
        "category": _enum(
            ["social", "business", "technology", "internet_culture", "public_affairs"]
        ),
        "topic_summary": _string(),
        "why_now": _string(),
        "core_tension": _string(),
        "research_question": _string(),
        "event_started_at": _string(),
        "latest_update_at": _string(),
        "shelf_life": _enum(["urgent", "short", "medium", "evergreen"]),
        "risk_level": _enum(["low", "medium", "high", "critical"]),
        "risk_notes": _string(),
        "event_cluster_key": _string(),
        "eligibility_signals": DISCOVERY_ELIGIBILITY_SIGNALS_SCHEMA,
        "score_assessments": DISCOVERY_SCORE_BREAKDOWN_RAW_SCHEMA,
        "source_seeds": _array(DISCOVERY_SOURCE_SEED_RAW_SCHEMA),
        "warnings": _string_array(),
        "creator_attention_signal": _object(
            {"available": {"type": "boolean"}, "summary": _string(allow_empty=True)}
        ),
    }
)

DISCOVERY_RAW_JSON_SCHEMA = _object(
    {
        "query": _string(),
        "time_window_hours": _integer(1),
        "candidates": _array(DISCOVERY_CANDIDATE_RAW_SCHEMA),
    }
)

DISCOVERY_CANDIDATE_SCHEMA = _object(
    {
        "candidate_id": _string(),
        **DISCOVERY_CANDIDATE_RAW_SCHEMA["properties"],
        "source_seeds": _array(DISCOVERY_SOURCE_SEED_SCHEMA),
        "score_breakdown": DISCOVERY_SCORE_BREAKDOWN_RAW_SCHEMA,
        "total_score": _integer(),
        "eligibility_status": _enum(["eligible", "watch", "rejected"]),
        "eligibility_reasons": _string_array(),
        "recommendation": _enum(["recommend", "consider", "watch", "reject"]),
        "is_primary": {"type": "boolean"},
    }
)

TOPIC_CANDIDATE_SET_JSON_SCHEMA = _object(
    {
        "artifact_version": _enum(["0.3"]),
        "discovery_id": _string(),
        "generated_at": _string(),
        "discovery_mode": _enum(["codex_skill", "openai_api", "fixture"]),
        "query": _string(),
        "time_window_hours": _integer(1),
        "channel_profile_version": _string(),
        "channel_profile_name": _string(),
        "seed_provenance": DISCOVERY_SEED_PROVENANCE_SCHEMA,
        "candidates": _array(DISCOVERY_CANDIDATE_SCHEMA),
        "display_candidate_ids": _string_array(),
        "watch_candidate_count": _integer(),
        "rejected_candidate_count": _integer(),
        "limitations": _string_array(),
    },
    optional=("seed_provenance",),
)

RESEARCH_HANDOFF_BRIEF_JSON_SCHEMA = _object(
    {
        "artifact_version": _enum(["0.3"]),
        "discovery_id": _string(),
        "selected_position": _integer(1),
        "candidate_id": _string(),
        "title": _string(),
        "research_question": _string(),
        "core_tension": _string(),
        "why_now": _string(),
        "risk_level": _enum(["low", "medium", "high", "critical"]),
        "risk_notes": _string(),
        "warnings": _string_array(),
        "source_seeds": _array(DISCOVERY_SOURCE_SEED_SCHEMA),
    }
)


# Script models only produce the content contract. Identity, revision, status,
# duration metrics, beat IDs and Claim coverage are owned by the Python core.
SCRIPT_CONTENT_BEAT_RAW_SCHEMA = _object(
    {
        "purpose": _string(),
        "content_kind": _enum(
            ["fact", "attribution", "analysis", "transition", "question"]
        ),
        "narration": _string(),
        "claim_ids": _string_array(),
        "evidence_link_ids": _string_array(),
        "analysis_basis_claim_ids": _string_array(),
        "risk_notes": _string(allow_empty=True),
    }
)

SCRIPT_MUST_KEEP_OMISSION_SCHEMA = _object(
    {"claim_id": _string(), "reason": _string()}
)

SCRIPT_DRAFT_CONTENT_JSON_SCHEMA = _object(
    {
        "working_title": _string(),
        "thesis": _string(),
        "audience_promise": _string(),
        "beats": _array(SCRIPT_CONTENT_BEAT_RAW_SCHEMA),
        "closing": _string(),
        "research_caveats": _string_array(),
        "research_gaps": _string_array(),
        "must_keep_omission_reasons": _array(SCRIPT_MUST_KEEP_OMISSION_SCHEMA),
    }
)

# Revision input may describe continuity, but it never owns the final beat_id.
SCRIPT_REVISION_CONTENT_BEAT_RAW_SCHEMA = _object(
    {
        **SCRIPT_CONTENT_BEAT_RAW_SCHEMA["properties"],
        "origin_beat_id": _string(allow_empty=True),
    },
    optional=("origin_beat_id",),
)

SCRIPT_REVISION_CONTENT_JSON_SCHEMA = _object(
    {
        **SCRIPT_DRAFT_CONTENT_JSON_SCHEMA["properties"],
        "beats": _array(SCRIPT_REVISION_CONTENT_BEAT_RAW_SCHEMA),
    }
)

SCRIPT_BEAT_SCHEMA = _object(
    {"beat_id": _string(), **SCRIPT_CONTENT_BEAT_RAW_SCHEMA["properties"]}
)

SCRIPT_REVIEW_STATE_SCHEMA = _object(
    {
        "state": _enum(["not_reviewed", "reviewed"]),
        "review_id": _string(allow_empty=True),
        "reviewed_from_revision": _integer(),
        "review_gate_status": _enum(["not_run", "pass"]),
        "reviewed_content_digest": _string(allow_empty=True),
    }
)

SCRIPT_BEAT_IDENTITY_SCHEMA = _object(
    {
        "next_beat_number": _integer(1),
        "retired_beat_ids": _string_array(),
    }
)

SCRIPT_DRAFT_JSON_SCHEMA = _object(
    {
        "artifact_version": _enum(["0.4"]),
        "script_id": _string(),
        "revision": _integer(1),
        "previous_revision": _integer(),
        "created_at": _string(),
        "generated_at": _string(),
        "report_id": _string(),
        "report_revision": _integer(1),
        "script_mode": _enum(["codex_skill", "openai_api", "fixture"]),
        "status": _enum(["draft", "reviewed"]),
        "script_profile_version": _string(),
        "target_duration_minutes": _number(3, 30),
        "character_count": _integer(),
        "estimated_duration_minutes": _number(),
        "working_title": _string(),
        "thesis": _string(),
        "audience_promise": _string(),
        "beats": _array(SCRIPT_BEAT_SCHEMA),
        "closing": _string(),
        "research_caveats": _string_array(),
        "research_gaps": _string_array(),
        "must_keep_claim_ids": _string_array(),
        "covered_must_keep_claim_ids": _string_array(),
        "missing_must_keep_claim_ids": _string_array(),
        "must_keep_omission_reasons": _array(SCRIPT_MUST_KEEP_OMISSION_SCHEMA),
        "change_summary": _string(),
        "review_state": SCRIPT_REVIEW_STATE_SCHEMA,
        "beat_identity": SCRIPT_BEAT_IDENTITY_SCHEMA,
    },
    optional=("review_state", "beat_identity"),
)

SCRIPT_REVIEW_CHECK_NAMES = [
    "factual_grounding",
    "attribution_integrity",
    "uncertainty_preservation",
    "avoid_claim_compliance",
    "must_keep_coverage",
    "high_risk_boundary",
    "analysis_fact_separation",
    "perspective_fairness",
    "research_gap_integrity",
    "narrative_structure",
    "oral_naturalness",
    "information_density",
    "original_expression",
    "script_usability",
    "counterargument_fairness",
]

SCRIPT_REVIEW_ISSUE_TYPES = [
    "unsupported_fact",
    "attribution_error",
    "avoid_claim_usage",
    "unverified_as_fact",
    "high_risk_overclaim",
    "material_uncertainty_loss",
    "analysis_as_fact",
    "research_gap_filled",
    "perspective_distortion",
    "must_keep_omission",
    "counterargument_unfair",
    "oral_naturalness",
    "narrative_structure",
    "repetition",
    "information_density",
    "ai_report_tone",
    "originality_risk",
    "long_quote",
    "script_usability",
]

SCRIPT_REVIEW_CHECK_SCHEMA = _object(
    {
        "check_name": _enum(SCRIPT_REVIEW_CHECK_NAMES),
        "outcome": _enum(["pass", "fail", "not_applicable"]),
        "reason": _string(),
    }
)

SCRIPT_REVIEW_ISSUE_RAW_SCHEMA = _object(
    {
        "issue_type": _enum(SCRIPT_REVIEW_ISSUE_TYPES),
        "beat_ids": _string_array(),
        "claim_ids": _string_array(),
        "explanation": _string(),
        "suggested_fix": _string(),
    }
)

SCRIPT_REVIEW_CONTENT_JSON_SCHEMA = _object(
    {
        "issues": _array(SCRIPT_REVIEW_ISSUE_RAW_SCHEMA),
        "checks": _array(SCRIPT_REVIEW_CHECK_SCHEMA),
        "overall_notes": _string(),
    }
)

SCRIPT_REVIEW_ISSUE_SCHEMA = _object(
    {
        "issue_id": _string(),
        **SCRIPT_REVIEW_ISSUE_RAW_SCHEMA["properties"],
        "severity": _enum(["blocking", "advisory"]),
    }
)

SCRIPT_REVIEW_JSON_SCHEMA = _object(
    {
        "artifact_version": _enum(["0.4"]),
        "review_id": _string(),
        "script_id": _string(),
        "script_revision": _integer(1),
        "report_id": _string(),
        "report_revision": _integer(1),
        "created_at": _string(),
        "review_mode": _enum(["codex_skill", "openai_api", "fixture"]),
        "issues": _array(SCRIPT_REVIEW_ISSUE_SCHEMA),
        "checks": _array(SCRIPT_REVIEW_CHECK_SCHEMA),
        "overall_notes": _string(),
        "blocking_issue_count": _integer(),
        "gate_status": _enum(["pass", "fail"]),
        "reviewed_content_digest": _string(),
        "review_consistency_version": _enum(["0.4.1"]),
    },
    optional=("reviewed_content_digest", "review_consistency_version"),
)
