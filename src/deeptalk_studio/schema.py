def _string():
    return {"type": "string"}


def _string_array():
    return {"type": "array", "items": _string()}


def _object(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


REPORT_JSON_SCHEMA = _object(
    {
        "schema_version": {"type": "string", "enum": ["0.1"]},
        "topic": _string(),
        "research_question": _string(),
        "generated_at": _string(),
        "scope_summary": _string(),
        "executive_summary": _string(),
        "sources": {
            "type": "array",
            "items": _object(
                {
                    "id": _string(),
                    "title": _string(),
                    "url": _string(),
                    "publisher": _string(),
                    "published_at": _string(),
                    "accessed_at": _string(),
                    "source_type": {
                        "type": "string",
                        "enum": [
                            "official",
                            "primary",
                            "media",
                            "academic",
                            "expert",
                            "creator",
                            "social",
                            "other",
                        ],
                    },
                    "stance_summary": _string(),
                    "credibility_notes": _string(),
                }
            ),
        },
        "claims": {
            "type": "array",
            "items": _object(
                {
                    "id": _string(),
                    "claim": _string(),
                    "classification": {
                        "type": "string",
                        "enum": [
                            "confirmed_fact",
                            "media_report",
                            "party_statement",
                            "commentary",
                            "unverified",
                        ],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "source_ids": _string_array(),
                    "notes": _string(),
                }
            ),
        },
        "timeline": {
            "type": "array",
            "items": _object(
                {
                    "date": _string(),
                    "event": _string(),
                    "claim_ids": _string_array(),
                    "source_ids": _string_array(),
                }
            ),
        },
        "perspectives": {
            "type": "array",
            "items": _object(
                {
                    "id": _string(),
                    "actor": _string(),
                    "position": _string(),
                    "reasoning": _string(),
                    "source_ids": _string_array(),
                    "category": {
                        "type": "string",
                        "enum": [
                            "party",
                            "media",
                            "expert",
                            "creator",
                            "public",
                            "other",
                        ],
                    },
                }
            ),
        },
        "conflicts": {
            "type": "array",
            "items": _object(
                {
                    "question": _string(),
                    "side_a": _string(),
                    "side_b": _string(),
                    "evidence_state": _string(),
                    "source_ids": _string_array(),
                }
            ),
        },
        "open_questions": {
            "type": "array",
            "items": _object(
                {
                    "question": _string(),
                    "why_it_matters": _string(),
                    "suggested_next_step": _string(),
                }
            ),
        },
        "angles": {
            "type": "array",
            "items": _object(
                {
                    "title": _string(),
                    "core_question": _string(),
                    "why_now": _string(),
                    "audience_value": _string(),
                    "risks": _string(),
                    "required_claim_ids": _string_array(),
                }
            ),
        },
        "fact_check_notes": {
            "type": "array",
            "items": _object(
                {
                    "claim_id": _string(),
                    "status": {
                        "type": "string",
                        "enum": [
                            "verified",
                            "partially_verified",
                            "unverified",
                            "disputed",
                        ],
                    },
                    "explanation": _string(),
                }
            ),
        },
        "limitations": _string_array(),
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

