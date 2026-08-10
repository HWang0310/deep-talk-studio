---
name: research-topic
description: Use when a current event, social issue, business or technology story, online controversy, or public incident needs a source-backed Research Draft followed by an independent Fact Check before long-form commentary or script writing.
---

# Research Topic

## Overview

Build an original evidence ledger, then challenge it in a separate research pass. Never use another creator's script as source material, and never let one pass certify its own claims.

## Required contract

Read `references/report-contract.md` completely before starting. Use `examples/sample-codex-draft-input.json` as the input shape; do not copy its fictional conclusions.

## Phase A: Research Draft

1. Identify the question and scope. If `discover-topics` supplied a Research Handoff Brief, use its title, research question, core tension, risk notes and Source Seeds directly; do not ask the user to repeat the title. Seeds are only starting points, not evidence. Ask only when the topic itself is unsafe or genuinely ambiguous.
2. Search broadly, then open candidate pages. A snippet cannot support a claim.
3. Prefer primary documents and official records, add reliable media, then relevant expert, commentator, and creator perspectives.
4. Record each opened URL with `inspection_method=codex_web_open`, `provenance_method=codex_tool_result`, a truthful `provenance_status`, and a traceable URL/tool reference. Unopened or unmatched sources stay `unmatched`.
5. Create atomic claims and Evidence Links. Use `attributes` for what a party or commentator said, `supports` for supporting evidence, `contradicts` for counterevidence, and `context` only for background.
6. Treat source independence conservatively. Only use `independent` when it is established; keep uncertain cases `unknown`. A different group ID never proves independence.
7. Mark claim importance and risk. Responsibility, accusation, reputation, legal, safety, financial, disputed, and fast-changing claims require conservative risk labels.
8. Save only the content input JSON, then run:

   ```bash
   ./scripts/deeptalk prepare-draft <codex-draft-input.json> --output reports
   ```

9. Keep the generated r1 JSON path. Do not describe it as reviewed.

## Phase B: Independent Fact Check

1. Start a distinct verification pass after r1 exists. Run new searches for every `high` or `critical` claim, seek counterevidence, and inspect source independence. Do not merely reread or paraphrase the Draft.
2. Check whether `party_statement` or `commentary` was mislabeled as fact and whether every `confirmed_fact` has enough independent support.
3. Create a `FactCheck Artifact 0.2` using the contract. Record the new search IDs/queries and consulted URLs under `tool_provenance`; `searched_new_sources=true` means a real new search occurred.
4. Do not trust a Fact Check source's self-declared normalized URL or group. The core must regroup every new source together with the r1 sources before saving.
5. Save short evidence summaries and locators, not long copyrighted passages.
6. Apply the independent artifact:

   ```bash
   ./scripts/deeptalk review-report <r1-report.json> <fact-check.json> --output reports
   ```

7. If validation fails, repair the research data. Never weaken the validator.

## Return to the user

Return the r1 Draft, FactCheck Artifact, and r2 report paths; the final `status`; quality Gate reasons; high-risk claim IDs; and the most important remaining uncertainty. A `reviewed` report still requires one explicit user confirmation before any future Script Agent. Do not generate a finished口播稿.

## Failure rules

- Five reposts are not five independent sources.
- `unknown`, `related`, `duplicate`, and `syndicated` never count as independent confirmation.
- A `context` link provides background but does not count as sourced support for Gate coverage.
- An official statement can prove what the institution said, not automatically prove its disputed explanation.
- Missing provenance, unresolved high risk, unsourced attribution, or incomplete Fact Check keeps the report as `draft`.
- Never invent a URL, tool reference, search call, citation, source inspection, or user approval.
