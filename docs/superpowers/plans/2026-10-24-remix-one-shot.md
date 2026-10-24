# 爆款二创 1.0 Implementation Plan

**Goal:** Deliver the final PR #48 Nexus contract (issuecomment-6383273699, with 6383140012 and 6383162084) in this branch, one executor, no merge/release.

**Architecture:** Extend existing Python stores/flow/loopback routes and Chat-first HTML. Retain legacy discovery singleton while adding per-topic records. Reuse canonical verified Bilibili discovery and authorized acquisition/Whisper. Keep full transcripts local, feed only concise narrative studies to creative writing. Soft-delete chats in place; block mutations during model operations.

**Constraints:** Preserve unrelated dirty files, user Key/history and formal gates. Max 4 new real model calls; automated tests use isolated stores. No model/media auto-install. CSS fallback is acceptable if Three.js does not justify its runtime cost. User explicitly delegated routine choices and sole execution, so no approval pauses or subagents.

## Tasks and verification

- [x] Reproduce A→B context contamination and timeout; implement per-topic/turn discovery with legacy read, same-turn/topic idempotence, scoped chat/draft context. Add immediate local pending UI and bounded free search. Test retry, failure, reload and separate sessions.
- [x] Verify download template ends with verified play count or unknown. Constrain paths, collisions and merged extension resolution, preserve old files. Test through runner.
- [x] Expose full persisted ASR via safe JSON/TXT export and searchable UI. Atomic UTF-8 study transcript with metadata; reanalysis idempotence. Test >200 segments, traversal and missing files.
- [x] Add compact reference workspace in chat from ranked discovery, opt-in authorized pipeline, summary-only source inspirations, three distinct complete entertainment drafts and normal conversational revisions. Test real orchestration with media/LLM fixtures; never feed full ASR to synthesis.
- [x] Add title/soft-delete/restore store + HTTP endpoints; safe IDs/symlinks; block in-flight stream/draft changes. Desktop/mobile keyboard menu, confirmation and recoverable trash. Test restart, cancellation, flight conflicts.
- [x] Browser trials (Playwright): slow/failure A→B, references authorization/transcript export/three drafts, rename/cancel/delete/restore, refresh, desktop/375px, graceful visual fallback and input/load measures.
- [x] Full pytest and bare unittest, diff/secrets review, before/after user-file digests, update control plane/docs and PR #48, commit/push and exact SHA report.

## Review focus

- Legacy chats/drafts remain readable; new topic never sees old context or old study links.
- Stopped streams/retries do not duplicate searches; timeouts cannot write late results.
- Unknown counts never become verified; collisions never overwrite user media.
- Trash never resurrects through stale SSE/draft completion or affects another chat.
- Fixture provenance stays explicit; real model quality is assessed separately from scripted fixture content.

## Execution ledger

- Same branch / same PR, sole executor as Owner requested; no worktree cleanup or subagent review.
- RED→GREEN regressions demonstrated wrong-topic drafts, unbounded wait, missing management/export APIs, missing filename suffix, missing real JSON offsets, unapproved Whisper bootstrap, missing current saved draft context, and repeated paid analysis. 14 new tests; old singleton test now asserts first-write-wins per topic.
- Browser RED→GREEN additionally corrected mobile close/backdrop/reopen. Final full pytest 1153 passed / 7 skipped; bare unittest 1160 tests OK / 7 skipped. Static JavaScript parse and diff check clean.
- Real anonymous Bilibili search returned five verified ranked candidates; four bounded real DeepSeek calls; real ffmpeg/Whisper on self-authored synthesized video. Third-party media acquisition remains fixture-only because download permission was not provided.
- Choice: optional Three.js not enabled; static CSS accent, zero active animations/canvas and 1–2ms observed input roundtrip. No claim of a Three.js A/B benchmark.
- Final author self-review retained Nexus as the independent acceptance reviewer. Existing Owner user-file digests and unrelated dirty files preserved. Final commit/push/runtime SHA and restart privacy check are recorded in the readiness comment, not embedded as a circular self-referential SHA in this file.

- Final filename boundary RED→GREEN: 80-emoji title previously produced a 270-byte media filename. UTF-8 byte-bound title now leaves room for BVID/play-count/TXT suffixes; targeted 89 passed. Full dual-entry results updated in delivery evidence after the final rerun.
