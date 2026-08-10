---
name: research-topic
description: Use when a user wants to research a current event, social issue, business or technology story, online controversy, public incident, or any topic that needs a source-backed Research Report before original long-form commentary or script writing.
---

# Research Topic

## Overview

Build an original evidence ledger before offering a content angle. Treat facts, reports, statements, commentary, and rumors as different objects; never use another creator's script as source material to rewrite.

## Workflow

1. Read `references/report-contract.md` completely.
2. Restate the research question and scope internally. Ask the user only when the topic cannot be identified safely; otherwise proceed.
3. Search broadly, then open and inspect candidate pages. Prioritize primary documents and official records, add reliable media, then collect relevant expert, commentator, and creator perspectives. A search snippet alone cannot support a confirmed fact.
4. Build a claim ledger with source IDs. Seek independent corroboration for consequential facts. Record what each party says without treating the statement as independently verified.
5. Seek materially different positions, including the strongest credible challenge to the leading explanation. Describe the evidence behind each side and where the evidence stops.
6. Separate unresolved or rapidly changing claims into `unverified`, open questions, limitations, and follow-up research. Do not fill gaps with inference.
7. Create JSON matching the contract. Use real, opened HTTP(S) source URLs; never invent a citation. Paraphrase source material and keep any necessary quotation short.
8. Save the draft JSON in a temporary location, then run from the repository root:

   ```bash
   ./scripts/deeptalk build-report <draft.json> --output reports
   ```

9. If validation fails, fix the research data rather than weakening the validator. Re-run until both Markdown and JSON are created.
10. Return the two report paths, a two- or three-sentence finding summary, and the most important remaining uncertainty. Do not generate a finished口播稿 in this workflow.

## Source and Evidence Rules

| Situation | Required treatment |
|---|---|
| Official or primary source describes its own action | Cite it, but note the source's institutional interest |
| Reliable media reports a detail not independently available | Use `media_report`, not `confirmed_fact` |
| A party explains motive, cause, or responsibility | Use `party_statement` |
| Expert or creator interprets events | Use `commentary` and name the speaker |
| Claim lacks inspectable evidence | Use `unverified`; never repeat it as a hook without the label |
| Sources conflict | Preserve both accounts and write a conflict entry |

## Quality Gate

Before saving, confirm:

- Every important factual sentence maps to one or more source IDs.
- Every source URL was opened or otherwise inspected beyond a result snippet.
- Source types and meaningful positions are diverse enough for the topic.
- The report identifies conflicts, unanswered questions, limitations, and content risks.
- The Script Agent handoff names facts to preserve and claims to avoid.
- The report is a new research foundation, not an imitation or rewrite of a creator.

## Common Mistakes

- Counting repeated syndications as independent confirmation.
- Treating an official statement as neutral proof of its disputed explanation.
- Calling a popular post “public opinion” without evidence.
- Hiding uncertainty in soft wording instead of using the explicit classifications.
- Saving Markdown by hand and skipping the JSON contract or validator.

