# Research Workflow 0.2 Contract

The executable schemas live in `src/deeptalk_studio/schema.py`. This reference explains what each artifact means. All IDs must be unique and every reference must exist.

## Two separate artifacts and two passes

```text
Codex Draft Input
→ Research Report r1 (`fact_check_pending`)
→ FactCheck Artifact 0.2 from new searches
→ Research Report r2 (`reviewed` or `draft`)
→ one explicit user confirmation
→ `ready_for_script`
```

Research and Fact Check may use the same underlying model, but they must be separate work steps. The FactCheck Artifact must preserve new search provenance and cannot be created by rephrasing r1.

## Codex Draft Input

Use `examples/sample-codex-draft-input.json` as the exact structural example. Include:

- `topic`, `research_question`, `scope_summary`, `executive_summary`;
- `sources`, `claims`, `evidence_links`, `timeline`, `perspectives`, `conflicts`;
- `open_questions`, `angles`, `limitations`, `handoff_to_script_agent`.

Do not add machine-owned metadata. `prepare-draft` creates `report_id`, revision fields, timestamps, status, Fact Check state, quality metrics, approval state, normalized URLs, independence groups and review flags.

## Source

Each source input includes:

- identity/content: `id`, `title`, `url`, `publisher`, `published_at`, `accessed_at`, `source_type`, `stance_summary`, `credibility_notes`;
- inspection: `inspection_method` = `codex_web_open`, `manual_open`, or `not_inspected`;
- provenance: `provenance_method` = `codex_tool_result` or `user_supplied`, `provenance_status` = `matched`, `partial`, or `unmatched`, plus `provenance_refs`;
- independence hints: `independence_status` and `syndication_of`.

Allowed source types: `official`, `primary`, `media`, `academic`, `expert`, `creator`, `social`, `other`.

The core removes tracking parameters and groups identical URLs, same-publisher pages and declared/likely syndications. Use `unknown` when independence cannot be established. Only `independent` sources with matched provenance and different groups can contribute to the confirmed-fact independent coverage metric.

## Claim

Every claim is atomic and includes:

- classification: `confirmed_fact`, `media_report`, `party_statement`, `commentary`, `unverified`;
- confidence: `high`, `medium`, `low`;
- importance: `background`, `key`, `core`;
- risk: `low`, `medium`, `high`, `critical`;
- risk factors chosen from `contested`, `attribution`, `reputation`, `fast_changing`, `responsibility`, `causal`, `legal`, `financial`, `safety`.

High and critical claims automatically enter Fact Check. `confirmed_fact` requires at least one `supports` link; the quality Gate separately requires independent corroboration coverage.

## Evidence Link

IDs use `E1`, `E2`, ... and include:

- `claim_id`, `source_id`;
- `relation`: `supports`, `contradicts`, `attributes`, or `context`;
- `evidence_summary`, `evidence_locator`, `verification_notes`.

`prepare-draft` fills `independence_group` and `verified_in_review=false`. `review-report` updates review flags and applies new evidence.

## FactCheck Artifact 0.2

Required top-level fields:

- identity: `artifact_version=0.2`, `review_id`, `report_id`, `report_revision`, `created_at`, `research_mode`, `status`;
- real second-pass trace: `tool_provenance.search_call_ids`, `search_queries`, `consulted_urls`, `citation_urls`;
- work: `queued_claim_ids`, `new_sources`, `evidence_links`, `checks`, `overall_notes`.

Each check includes `claim_id`, `outcome`, original and recommended classification, `searched_new_sources`, counterevidence summary, source IDs, independence assessment and verification notes. Outcomes: `verified`, `partially_verified`, `disputed`, `unverified`.

Every queued high-risk claim needs a check and a real new source search. New sources use the full 0.2 Source object at the Artifact boundary. Before trust or storage, the core combines them with the r1 sources and deterministically overwrites normalized URL, duplicate/syndication status, independence group and Evidence Link groups.

## API Research Draft

The Responses API uses a separate content-only schema. The model supplies research judgments, but it does not supply report identity, revisions, timestamps, report status, Fact Check state, provenance-derived source fields, quality metrics, approval state, claim verification status, or Evidence review flags. The workflow injects those fields and rejects extra model-owned metadata before creating r1.

## Quality Gate

The core calculates and verifies every metric; do not invent them:

- claim source coverage ≥ 80%;
- high-risk Fact Check coverage = 100%;
- confirmed-fact independent source coverage ≥ 80%;
- provenance match rate ≥ 80%;
- at least two source types;
- unresolved high-risk claims = 0;
- unsourced attributions = 0.

Duplicate and syndicated source counts remain visible. A failed Gate can be saved only as `draft`. `reviewed` requires a completed independent Fact Check. `ready_for_script` additionally requires explicit user confirmation, and all high-risk claim IDs must be shown to the user.

## Revisions and corrections

`report_id` stays stable; `revision` increments and `previous_revision` points to the immediately prior version. `created_at` stays stable, while `generated_at`, `change_summary` and `corrections` describe the new revision. Existing revision files are never overwritten.

## Copyright and originality

Record short evidence summaries and precise locators. Quote only when necessary and keep quotes short. Never save full articles, build from another creator's script, imitate distinctive expression, or erase uncertainty for narrative effect.
