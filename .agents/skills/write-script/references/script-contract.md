# Original Script Workflow — V1 and 0.4 Compatibility

## Gate and immutable approval

Script work requires all six conditions: Research status `ready_for_script`, Research quality `pass`, Fact Check `completed`, approval status `approved`, approval `ready_for_script=true`, and non-empty original user confirmation. Approval creates a new Research revision and changes no research content. Any later ordinary Research revision resets approval.

## Script Profile

Current Thesis-bound V1 uses `config/script-profile-v1.json` with `duration_policy=content_driven` and no default minute goal. Pass `target_duration_minutes=None` when unspecified; an explicit finite positive number is a soft preference, not a quota. Use `parse_target_duration(text, default=None)` when parsing a V1 preference. Do not fill, force compression, or silently return to legacy 0.4.

The product computes `character_count` and `estimated_duration_minutes` from actual narration using the configured rate; these are not measured A-roll times. The Editor view reports preference/actual deviation. Explain material deviations by content needs in the handback.

New V1 artifacts add code-owned `duration_mode`: `content_driven` stores the derived estimate in the existing numeric `target_duration_minutes` field (a planning observation, not a user target); `preference` stores the explicit request. Content-driven targets must match the actual estimate. Both fields enter the new review digest. Review content alone never supplies the mode or metrics.

No editorial output minute floor/ceiling remains. Empty spoken content, invalid/non-finite preferences and more than 100,000 raw narration-plus-closing characters fail closed as technical input/processing limits. Provider timeout/budget failures remain explicit; a preference does not override them.

Old V1 artifacts without `duration_mode` remain readable under their original 5–6 rules and unchanged content digests. Old profiles with `[5,6]` remain loadable. Legacy 0.4 retains its own 3–30 target contract and does not gain Thesis binding. Old artifacts are never rewritten to the new policy. A new content revision uses the current V1 policy and requires a new Review.

## Writer content input

Writer content contains only:

- `working_title`, `thesis`, `audience_promise`;
- `beats` with `purpose`, `content_kind`, `narration`, `claim_ids`, `evidence_link_ids`, `analysis_basis_claim_ids`, and `risk_notes`;
- `closing`, `research_caveats`, `research_gaps`;
- `must_keep_omission_reasons` with `claim_id` and explanation.

Do not supply artifact identity, revision, timestamps, report binding, mode, status, profile version, duration metrics, beat IDs, Claim coverage, or change summary. The core generates them.

## Grounding

- `fact`: requires one or more existing verified `confirmed_fact` Claims. A high/critical Claim must be checked and resolved by the approved report.
- `attribution`: use for `party_statement`, `media_report`, `commentary`, or carefully bounded `unverified` material. Narration must naturally say who said or reported it and preserve uncertainty.
- `analysis`: requires `analysis_basis_claim_ids`. It may infer, compare, explain, question, or judge, but may not introduce a new factual premise.
- `transition` and `question`: organize oral flow; any references still must exist.

Every Evidence Link must exist and point to a Claim used by the same Beat. Spoken text never contains machine IDs. The validator blocks direct forbidden-claim reuse; the independent Reviewer checks semantic paraphrases and uncertainty loss.

## Script Draft Artifact 0.4

The final JSON includes code-owned identity/revision/report binding, structured Beats with stable `B001`-style IDs, code-owned character/duration metrics, `must_keep` coverage, status, review linkage and content. V1 also binds the approved Thesis Card ID/revision/digest. JSON is the only machine interface. A new Beat gets a monotonic new ID; a deleted ID is never reused. Do not ask normal users to manage IDs.

Derived human views:

- Editor Markdown: structure, kinds, refs, risk, gaps, caveats, metrics;
- Teleprompter Markdown: narration and closing only.

## Script Review content and Artifact

Reviewer content contains `issues`, `checks`, and `overall_notes`. An issue supplies only type, affected Beat/Claim IDs, explanation, and suggested fix. The core assigns issue IDs and severity.

V1 preserves all 15 preexisting checks plus all 17 quality checks; any V1 quality failure is blocking. A target-minute deviation is not itself a quality failure: judge evidence, completeness, pacing, repetition and filler.

Blocking types include `unsupported_fact`, `attribution_error`, `avoid_claim_usage`, `unverified_as_fact`, `high_risk_overclaim`, `material_uncertainty_loss`, `analysis_as_fact`, `research_gap_filled`, and `perspective_distortion`. Any blocking issue makes the review Gate fail and the resulting Script revision remain `draft`. Every failed check must have its typed issue; the eight factual safety checks must have their mapped blocking issue. `not_applicable` cannot bypass safety checks. Passing review creates a r2 linkage to the exact r1 Artifact and content digest; content revisions clear it and require a new review.

## Storage and revisions

Each revision saves immutable JSON, Editor Markdown, and Teleprompter Markdown under gitignored `script_drafts/`. A review artifact is separate immutable JSON. User edits create a new draft revision, keep the exact approved Research revision, and require a new Script Review. A changed Research revision must be separately approved and starts a new Script relationship.

## Originality and scope

Use Research summaries and evidence boundaries, not long source passages. Do not search for, download, imitate, or rewrite creator scripts. V0.4 does not create materials, visuals, editing, subtitles, thumbnails, publishing metadata, or publishing actions.
