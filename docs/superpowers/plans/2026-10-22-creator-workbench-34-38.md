# Creator Workbench Issues #34–#38 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the merged Creator Workbench into a truthful, resumable local workflow from DeepSeek configuration and five-reference analysis through optional audio-first Edit Map delivery, with browser evidence and no hidden paid or mock claims.

**Architecture:** Keep `WorkbenchFlow` as the UI orchestration boundary and add narrowly scoped settings, provider, DeepSeek tools, reference-state, and audio-delivery adapters around existing canonical engines. Additive session fields and routes are backward-compatible; canonical research/script/material/ASR validators remain the source of truth.

**Tech Stack:** Python 3.9+ standard library, existing `unittest`, local `whisper.cpp`/ffmpeg providers, stdlib loopback HTTP server, vanilla HTML/JS, Playwright/Chrome only for QA evidence.

**Spec:** `docs/superpowers/specs/2026-10-22-creator-workbench-34-38-design.md`

## Global Constraints

- Never call DeepSeek Search/Fetch or creative endpoints without the owner’s private key and explicit budget/opt-in; absent key is `WAITING_FOR_OWNER_API_KEY`.
- Never log or return an API key; persist local settings only with mode `0600` and keep private media/artifacts gitignored.
- Authorized acquisition failures remain in the readiness denominator until a successful retry or a reasoned partial-analysis override.
- LLM-unavailable reference analysis is `UNVERIFIED`, not analyzed; fixture outputs are labeled and never evidence of real creative quality.
- Preserve existing topic/research/thesis/script/rights/ASR gates, immutable lineage, loopback SSRF defenses, and creator-controlled manual NLE editing.
- Each phase ends with its own commit/PR, test evidence, and `READY_FOR_NEXUS_REVIEW`; do not merge or release.

## Review Focus

- A blank key update must preserve the stored secret while an explicit clear removes it: settings tests in Task 1.
- A failed authorized download must remain eligible/pending after a restart and after a second failed retry: reference-state tests in Task 2.
- A model outage must not become a completed analysis, while a later retry reuses the transcript: Task 2 re-analysis test.
- Search/Fetch must spend no budget without opt-in and must never label snippets as evidence: Task 3 budget/provenance tests.
- An uploaded audio file must not create a human-frame or a rights-ready asset when canonical material evidence is absent: Task 4 fail-closed delivery test.

### Task 1: Issue #34 DeepSeek settings and truthful connection status

**Files:**
- Modify: `src/deeptalk_studio/workbench/settings.py`
- Modify: `src/deeptalk_studio/workbench/llm.py`
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/index.html`
- Test: `tests/test_workbench.py`, `tests/test_webui.py`

**Interfaces:**
- Produce `provider_mode=deepseek`, official preset defaults, `effective_chat_endpoint(settings)`, and masked `connection_status` fields.
- `ChatCompletionsProvider.ping()` raises a typed error containing category/status but never the key.
- `WorkbenchFlow.test_settings()` persists `not_tested|passed|failed` plus `connection_kind=real|fixture`.

- [ ] Write failing tests for preset defaults, one endpoint suffix, save/reload/mask/clear, provider switching preservation, 401/402/403/429/timeout messages, no-key status, and UI labels/status.
- [ ] Run focused tests and observe failures caused by missing deepseek mode/status behavior.
- [ ] Implement the smallest settings/provider/flow/API/UI changes; keep generic `chat` and `responses` behavior intact.
- [ ] Run focused tests and then the existing workbench/webui suite.
- [ ] Commit `feat: add first-class DeepSeek workbench settings`.
- [ ] Push branch `agent/issue34-deepseek-settings`, create PR against `main`, and comment redacted test evidence plus `WAITING_FOR_OWNER_API_KEY` if no key is present.

### Task 2: Issue #35 durable five-reference transcript and analysis state

**Files:**
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Modify: `src/deeptalk_studio/workbench/session.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/index.html`
- Test: `tests/test_workbench.py`, `tests/test_webui.py`

**Interfaces:**
- Add `WorkbenchFlow.reanalyze_reference(session_id, bvid)` that consumes a saved transcript and does not reacquire media.
- Study records expose `transcript_status`, `analysis_status`, `analysis_error`, `transcript_provenance`, `analysis_provenance`, and segment previews.
- Readiness counts `analyzed`, `eligible`, `failed`, and unresolved authorized references across reloads.

- [ ] Add tests for failed authorized acquisition persistence/restart, five-way readiness denominator, LLM outage → `unverified`, transcript persistence/provenance, reanalysis success, and UI retry/status text.
- [ ] Run those tests red.
- [ ] Implement durable state transitions, transcript digest/provenance, reanalysis route, and visible per-video transcript/analysis status.
- [ ] Run focused and full existing workbench/webui tests.
- [ ] Commit `feat: make reference analysis resumable and honest`.
- [ ] Create stacked PR #35 against the #34 branch and post evidence; keep real LLM status `WAITING_FOR_OWNER_API_KEY` when unconfigured.

### Task 3: Issue #36 budgeted official DeepSeek Search/Fetch and source provenance

**Files:**
- Create: `src/deeptalk_studio/workbench/deepseek_tools.py`
- Modify: `src/deeptalk_studio/workbench/session.py`
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/index.html`
- Test: `tests/test_workbench.py`, `tests/test_webui.py`, `tests/test_deepseek_tools.py`

**Interfaces:**
- `DeepSeekSearchFetchClient.search(query, count, need_content)` and `.fetch(url)` use injected transport and official paths.
- Session `search_budget` is `{opt_in, max_requests, used}`; explicit `search` and `fetch` flow methods update it atomically.
- Stored sources include `kind=deepseek_fetched`, original URL, request ID, retrieval time, and content digest.

- [ ] Write offline transport tests for request shape, error mapping, missing opt-in, cap exhaustion, response validation, and provenance; add UI route tests.
- [ ] Run tests red.
- [ ] Implement client, budget, routes, and UI search-result selection without changing manual source fallback.
- [ ] Run focused/full suites and security tests.
- [ ] Commit `feat: add opt-in DeepSeek source search and fetch`.
- [ ] Create stacked PR #36 against #35 and document that no paid call ran.

### Task 4: Issue #37 audio import, real alignment status, and Edit Map UI

**Files:**
- Modify: `src/deeptalk_studio/workbench/session.py`
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/index.html`
- Test: `tests/test_workbench.py`, `tests/test_webui.py`, `tests/test_audio_only_delivery.py`

**Interfaces:**
- `WorkbenchFlow.import_audio(session_id, filename, data_stream, origin)` atomically stores a validated local file and records SHA/size/origin.
- `WorkbenchFlow.run_audio_delivery(session_id)` delegates to existing canonical audio/edit-bridge code; it returns typed `WAITING_FOR_OWNER_REVIEW` when reviewed material inputs are absent.
- Add binary `POST /api/workbench/audio/import` and JSON `POST /api/workbench/audio/deliver` plus state rendering/export links.

- [ ] Add tests first for safe binary import/traversal/size rejection, origin persistence, synthetic local-ASR timeline, rights-missing gap, and no-human-frame/no-finished-cut invariants.
- [ ] Run red.
- [ ] Implement bounded upload streaming, resolver adapter, routes, progress/state, and UI file chooser/timeline/gap display.
- [ ] Run focused audio/workbench/webui suites and existing alignment tests.
- [ ] Commit `feat: expose audio-first alignment and edit-map delivery in UI`.
- [ ] Create stacked PR #37 against #36 and record owner-review blockers honestly.

### Task 5: Issue #38 browser QA, evidence, and handoff

**Files:**
- Create: `evaluations/issue38_workbench/README.md`
- Create: `evaluations/issue38_workbench/smoke_playwright.py` (or equivalent local runner)
- Modify: `CHANGELOG.md`, `HANDOFF.md`, and canonical current-state docs only if behavior/status changed

- [ ] Read the Playwright skill and create offline smoke tests for desktop/375px, keyboard, settings masking, retry/resume, and server health.
- [ ] Start the UI with the documented one-command launcher and run the browser smoke against the actual loopback URL; save redacted screenshots/timings.
- [ ] Run full unittest discovery, `git diff --check`, and security regressions; fix only reproducible failures with red-green tests.
- [ ] Record tier A/B evidence and final status (`WAITING_FOR_OWNER_API_KEY` plus any owner-review blocker) without claiming real-model quality.
- [ ] Commit `test: add Creator Workbench browser acceptance evidence`.
- [ ] Create stacked PR #38 against #37, comment Issue #23 with links/evidence, and leave all PRs unmerged for Nexus.

### Final review and handoff

- [ ] Generate the SDD review package, dispatch one fresh reviewer, and address Critical/Important findings with new red-green tests.
- [ ] Verify branch/working tree, PR heads, no secret/media staging, full tests, startup URL, and final `READY_FOR_NEXUS_REVIEW` status.

