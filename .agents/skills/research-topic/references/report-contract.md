# Research Report 0.1 Contract

Read this file before constructing a report. The executable JSON Schema lives in `src/deeptalk_studio/schema.py`; this reference explains the intended meaning.

## ID conventions

- Sources: `S1`, `S2`, ...
- Claims: `C1`, `C2`, ...
- Perspectives: `P1`, `P2`, ...
- IDs must be unique within their collection.
- Every referenced ID must exist in the same report.

## Top-level fields

All fields are required, even when an array is empty:

| Field | Meaning |
|---|---|
| `schema_version` | Always `0.1` |
| `topic` | Clear topic title |
| `research_question` | The decision-driving question |
| `generated_at` | ISO 8601 time with timezone |
| `scope_summary` | Time range, geography, and deliberate exclusions |
| `executive_summary` | Short synthesis that preserves uncertainty |
| `sources` | Inspected sources and provenance notes |
| `claims` | Atomic evidence ledger |
| `timeline` | Dated sequence linked to claims and sources |
| `perspectives` | Named actors and their reasoning |
| `conflicts` | Material disagreements and current evidence state |
| `open_questions` | Questions that remain answerable with more work |
| `angles` | Original content directions, not draft scripts |
| `fact_check_notes` | Verification status for important claims |
| `limitations` | Coverage and evidence limits |
| `handoff_to_script_agent` | Safe input for future original script development |

## Claim classification

Use exactly one classification per atomic claim:

- `confirmed_fact`: supported by inspectable evidence; must have at least one source. Prefer independent corroboration for consequential or disputed facts.
- `media_report`: attributed reporting that has not been independently confirmed by this workflow.
- `party_statement`: a statement, explanation, denial, allegation, or estimate from an involved party.
- `commentary`: interpretation, judgment, prediction, or normative opinion from an expert, creator, media commentator, or member of the public.
- `unverified`: circulating information for which inspectable support is absent or insufficient.

Confidence is `high`, `medium`, or `low`. Confidence records the evidence quality and agreement, not how persuasive the prose sounds.

## Source object

Every source contains:

```json
{
  "id": "S1",
  "title": "Exact page title",
  "url": "https://example.com/page",
  "publisher": "Publisher or account",
  "published_at": "2026-08-10 or not stated",
  "accessed_at": "2026-08-10",
  "source_type": "official",
  "stance_summary": "What this source contributes or argues",
  "credibility_notes": "First-hand status, limitations, incentives, corrections"
}
```

Allowed `source_type`: `official`, `primary`, `media`, `academic`, `expert`, `creator`, `social`, `other`.

## Cross-reference fields

- `claims[].source_ids` → sources.
- `timeline[].claim_ids` → claims; `timeline[].source_ids` → sources.
- `perspectives[].source_ids` → sources.
- `conflicts[].source_ids` → sources.
- `angles[].required_claim_ids` → claims.
- `fact_check_notes[].claim_id` → one claim.
- `handoff_to_script_agent.must_keep_claim_ids` → claims.

Allowed fact-check status: `verified`, `partially_verified`, `unverified`, `disputed`.

## Script Agent boundary

The handoff must include:

- `recommended_angle`: the strongest evidence-supported direction.
- `central_tension`: the unresolved collision that gives the story depth.
- `must_keep_claim_ids`: claims a future script must preserve with their labels.
- `avoid_claims`: tempting assertions that must not be stated as fact.
- `follow_up_research`: concrete research needed before publication.

The Script Agent may create an original narrative later, but it may not erase classifications, uncertainty, attribution, or source provenance.

