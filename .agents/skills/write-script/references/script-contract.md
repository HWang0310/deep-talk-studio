# Original Script Workflow 0.4 Contract

## Gate and immutable approval

Script work requires all six conditions: Research status `ready_for_script`, Research quality `pass`, Fact Check `completed`, approval status `approved`, approval `ready_for_script=true`, and non-empty original user confirmation. Approval creates a new Research revision and changes no research content. Any later ordinary Research revision resets approval.

## Script Profile

Use `config/script-profile.json` version 0.4. Its default is approximately 12 minutes at a conservative configurable Chinese characters-per-minute rate. `character_count` and `estimated_duration_minutes` are program calculations, not model output and not measured playback.

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

The final JSON includes code-owned identity/revision/report binding, structured Beats with `B001`-style IDs, code-owned character/duration metrics, `must_keep` coverage, status, and content. JSON is the only machine interface.

Derived human views:

- Editor Markdown: structure, kinds, refs, risk, gaps, caveats, metrics;
- Teleprompter Markdown: narration and closing only.

## Script Review content and Artifact

Reviewer content contains `issues`, `checks`, and `overall_notes`. An issue supplies only type, affected Beat/Claim IDs, explanation, and suggested fix. The core assigns issue IDs and severity.

Blocking types include `unsupported_fact`, `attribution_error`, `avoid_claim_usage`, `unverified_as_fact`, `high_risk_overclaim`, `material_uncertainty_loss`, `analysis_as_fact`, `research_gap_filled`, and `perspective_distortion`. Any blocking issue makes the review Gate fail and the resulting Script revision remain `draft`. Editorial concerns are advisory and cannot override the Grounding Gate.

## Storage and revisions

Each revision saves immutable JSON, Editor Markdown, and Teleprompter Markdown under gitignored `script_drafts/`. A review artifact is separate immutable JSON. User edits create a new draft revision, keep the exact approved Research revision, and require a new Script Review. A changed Research revision must be separately approved and starts a new Script relationship.

## Originality and scope

Use Research summaries and evidence boundaries, not long source passages. Do not search for, download, imitate, or rewrite creator scripts. V0.4 does not create materials, visuals, editing, subtitles, thumbnails, publishing metadata, or publishing actions.
