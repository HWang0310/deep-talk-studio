---
name: discover-topics
description: Use when the user asks “今天讲什么？”, wants a few recent deep-commentary topic ideas, asks what social, business, technology, public-affairs or online topics are worth covering, wants a replacement batch, or replies with a numbered Topic Discovery choice before source-backed research.
---

# Discover Topics

Find a small, evidence-aware set of original long-form commentary topics. This is an editorial preflight, not a Research Report, Fact Check, script, material search, or imitation workflow.

## Required contract

Read `references/candidate-contract.md` before producing a Candidate Set. Use the versioned Channel Profile at `config/channel-profile.json`; do not ask a normal user to edit it.

## Discovery pass

1. Interpret the user request. Default to five candidates and the latest 72 hours. Treat “只看科技”“只看商业”“少一点社会新闻” as a new filtered discovery request. Treat “换一批” as a fresh search, not a rearrangement of the old list.
2. Search public sources. Check recent events and continuing stories from the last 14 days that have a major update in the last 72 hours. Open the source pages used as Seeds; never turn a search snippet into a confirmed fact.
3. Propose at least seven raw candidates so deterministic de-duplication and category diversity can retain up to five. For each recommendable candidate, record two to four Source Seeds from separate research directions and explain why each Seed matters.
4. Keep only topics with public research footing. Anonymous rumors, unsupported accusations, pure emotion, pure gossip, copied-creator premises, and high-risk weak-evidence events are `watch` or `rejected`, not Top 5.
5. Use the five 0–5 score assessments with concrete reasons. Never supply a total score, rank, label, Discovery ID, timestamp, provenance status, engagement count, playback count, or search-index number. The Python core owns those fields.
6. If public creator titles/descriptions are accessible without bypassing platform limits, they may explain a `creator_attention_signal`. Do not collect scripts, subtitles, long quotations, distinctive wording, or use one creator as factual evidence. Missing creator signal is normal.
7. Save the raw candidate input and run:

   ```bash
   ./scripts/deeptalk prepare-discovery <discovery-input.json> --output discoveries
   ```

8. Read the generated Markdown and show the user only its short numbered cards. Do not paste the JSON Artifact into conversation.

## User selection

When the user replies `1` or `研究 1`, load the latest Candidate Set:

```bash
./scripts/deeptalk select-topic "1" --output discoveries
```

Use the resulting Research Handoff Brief internally. Immediately continue with `research-topic` using its title, research question, core tension, risk notes and Source Seeds. Do not ask the user to copy the title again. The Source Seeds are merely starting points: start the full V0.2 research and independent Fact Check normally.

For API automation only, this is available:

```bash
./scripts/deeptalk research-selected "1" --discoveries discoveries --output reports
```

If the user supplied a direct topic instead of a numbered selection, do not invoke this Skill; invoke `research-topic` directly. Keep mode A unchanged.

## Return to the user

Return up to five cards, one explicit `【首选】`, why now, core tension, fit for long video, risk, shelf life and total score. Say: “只需回复编号，例如 1；回复‘换一批’会重新寻找。” Mention a watch count only if one exists. Do not expose JSON, commands, schemas, paths or raw research notes to a normal user.

## Non-negotiable boundaries

- Discovery Source Seeds are not confirmed facts and are not the V0.2 Evidence Ledger.
- Do not fabricate attention metrics, URL, page opening, source inspection or creator signal.
- Do not bypass login, rate limits, anti-bot controls or platform restrictions.
- Do not create a script, thumbnail, edit plan, video or publishing action.
- Do not use another creator’s content as a source for imitation or rewriting.
