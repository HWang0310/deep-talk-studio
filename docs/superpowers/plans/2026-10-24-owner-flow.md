# Owner flow consolidation — PR #48

Spec: Nexus issuecomment-6383823863. Owner explicitly delegated implementation and sole execution; retain the existing UI and PR, no new design approval loop.

- [x] Reproduce pre-analysis generation and overlay defects. Add backend regressions: zero paid generation before analysis; explicit topic-only basis; selected-reference complete-ASR/analysis guard; honest phases; existing drafts/data unchanged.
- [x] Add one scoped creation SSE action using existing acquisition/analysis/draft methods. Emit actual download/extract/transcribe/analyze/generate phases. Scoped checkbox consent; no invented license, no automatic paid retries. Keep per-session flight guard through worker completion.
- [x] Replace nested reference entry/modal with one conversation card: 4 steps, prominent selection CTA, inline top-ranked choices/consent, retry and explicit free-creation shortcut. Full transcript remains accessible. Three completed scripts read in chat; editor collapsed until explicitly opened, all revisions retained.
- [x] Put legacy flow behind Settings > Advanced. Keep canonical gates/data. Remove sticky composer overlay, grow draft editor to its content, one document scroll and no editing auto-scroll.
- [x] Isolated desktop1280/mobile375x812/short-height browser journey, including failed/slow reference processing, free shortcut, no-results, refresh, versions/export and bottom controls above composer. No third-party downloads or new paid calls needed; deterministic fixtures visibly labeled.
- [x] Full pytest and bare unittest, user-file digest/key check, final commit/push to same PR, restart existing8321 and post exact SHA + READY_FOR_NEXUS_OWNER_FLOW_REREVIEW.

## Ledger

- RED→GREEN: premature paid scripts, missing explicit topic-only path, missing scoped source/ASR guard, live phase reporting, bare-topic persistence and HTTP flight/consent behavior.
- Kept existing theme and one page. Static document-flow composer and auto-height draft editor replace overlay; no new dashboard/dependency or paid service.
- Browser verified source journey, no-results/free/timeout/failure/retry, v1→v6/reopen/export, advanced opt-in, desktop/mobile/short-height geometry. Fixed visual CTA contrast and hidden legacy-entry activation after actual browser failures; no editing auto-scroll and ASR modal wheel reading verified.
- Prior tests were evolved only where Owner explicitly superseded automatic pre-analysis long generation. Source isolation, artifacts, flight protection, history and canonical gates remain exercised.
- Owner privacy: private before/after digests, isolated fixtures; no additional paid calls or third-party download. Final command counts, push and 8321 exact SHA recorded in the delivery report/readiness comment.
