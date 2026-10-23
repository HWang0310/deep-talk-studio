# Creator Workbench Issues #34–#38 — Design Specification

## Purpose and accepted scope

This design extends the existing local Creator Workbench from the merged PR #33
flow into a resumable creator-facing workbench. The normal path remains

`topic → up to five relevant Bilibili references → explicitly authorized local
acquisition → local transcript/LLM viewpoint analysis → independent research and
fact check → human-approved thesis → independently reviewed script → optional
owner-provided final audio → real timecoded asset guidance/Edit Map`.

The user supplied the scope and order in Issue #23 comments and Issues #34–#38;
that scope is the approval to execute this design autonomously. The product
still never auto-edits, publishes, chooses a visual winner, bypasses a platform
restriction, or treats a reference video as evidence. A missing private key,
human approval, rights decision, or real media remains an explicit blocking
state.

## Boundaries and non-goals

* DeepSeek calls use the owner-entered key only. The key is stored locally with
  mode `0600`, is never returned in full, logged, or committed, and no paid
  Search/Fetch request is made without an explicit per-run opt-in and cap.
* “Fixture” is a test/development transport label, never a product default and
  never evidence of real creative quality.
* Reference acquisition preserves every authorized failure, reason, attempt,
  and authorization statement. A failed authorized reference remains in the
  readiness denominator and blocks full research until a successful retry or an
  explicitly reasoned partial-analysis override.
* Local ASR/transcript artifacts are immutable, timestamped, and carry runtime,
  model, and input digest provenance. A transcript without a successful LLM
  viewpoint is `UNVERIFIED`, not analyzed.
* Audio delivery consumes the existing `audio_delivery` and edit-bridge core.
  The UI imports owner-local audio, records its origin, runs the real local ASR
  path, and exposes asset gaps/rights status and Edit Map artifacts. It never
  fabricates a human frame or a finished cut.

## Component design

### Settings and model boundary (#34)

`workbench.settings` gains a first-class `deepseek` mode while retaining
`responses` and generic `chat`. The DeepSeek preset resolves the official base
`https://api.deepseek.com`, default model `deepseek-flash`, and one
`/chat/completions` suffix. An optional `deepseek-v4-pro` value is editable, not
assumed available. Settings persist only non-secret connection observations:
provider, model, endpoint, last test state/time, error category, and whether
the operation used the real provider or an explicit fixture transport.

`ChatCompletionsProvider` exposes typed connection failures for 401/402/403/429,
timeouts, URL errors, malformed responses, and successful tests. `WorkbenchFlow`
persists the observation atomically and returns a masked view. Blank key fields
preserve the stored key; an explicit empty string clears it. Product routes use
the real transport; tests inject a fixture transport and label it `fixture`.

### Reference analysis state (#35)

Each reference state is a durable state machine:

`not_authorized → failed|downloaded → transcribing → unverified|analyzed`.

`failed` is only entered after a valid authorization statement. The state keeps
`failure_stage`, `failure_reason`, `attempt_count`, and `last_attempt_at`; a
successful retry clears failure fields. A transcript is saved before LLM work
and includes segment timestamps, input SHA-256, ASR runtime/model provenance,
and `transcript_status`. LLM success adds `analysis_status=analyzed` and the
provider/model provenance. LLM unavailability leaves `analysis_status=unverified`
and a retryable error; `reference_insights` only uses analyzed studies. A
separate re-analysis method reuses the saved transcript rather than redownloading
or retranscribing.

### DeepSeek Search/Fetch (#36)

`workbench.deepseek_tools` is a small dependency-free client with an injected
transport. It calls the official `/v1/tools/search` and `/v1/tools/fetch`
paths, maps errors without secrets, and validates response shape. Session state
stores an explicit `search_budget` (`opt_in`, `max_requests`, `used`) and raw
provenance records. Search is a separate UI action; no research-generation call
implicitly spends the budget. Fetching a selected result is another explicit
action and only then stores inspected source text with `kind=deepseek_fetched`,
URL, request ID, and retrieval time. Budget exhaustion and missing opt-in fail
closed. Existing manual URL/paste and SSRF-safe fetching remain available.

### Audio delivery UI (#37)

The UI provides a file chooser and a binary local upload route. The server
validates a basename, supported audio/video suffix, bounded content length, and
session-local destination, writes atomically, and records origin (`owner_made`,
`external_voice_authorized`, or `unknown`). A delivery action invokes the
existing canonical resolver/runner with injected local providers in tests. The
session view exposes import status, ASR/alignment status, timeline rows, rights
gaps, and paths to the Asset Pack/Edit Map. Missing reviewed material packages
are shown as `WAITING_FOR_OWNER_REVIEW`, not silently replaced by fixtures.

### QA (#38)

The acceptance harness has two explicitly separate tiers: offline synthetic
tests and real local-media/ASR tests. A Playwright/Chrome smoke run covers
desktop and 375px layouts, keyboard focus, settings masking/status, retry and
resume. It never claims real DeepSeek creative quality without a private key and
owner budget. Evidence records commands, counts, elapsed time, screenshots,
and the honest final status (`WAITING_FOR_OWNER_API_KEY` and/or
`WAITING_FOR_OWNER_REVIEW` until the owner supplies the missing inputs).

## Data flow and compatibility

All additions are additive to the PR #33 session schema. Readers tolerate old
sessions by supplying defaults. Existing canonical report, thesis, script,
material, ASR, rights, and immutable storage validators remain authoritative.
New UI routes call `WorkbenchFlow`; no browser route writes canonical artifacts
directly. Every new artifact is written under gitignored session or canonical
artifact roots with atomic/exclusive semantics.

## Error and security policy

No API key, authorization token, request body, or private media bytes appear in
logs or error messages. Loopback host/origin/content-length guards remain in
force. Binary uploads do not accept transfer encoding, traversal, symlink
destinations, or unsupported MIME/suffixes. DeepSeek Search/Fetch is disabled by
default and never retries around a provider or platform denial.

## Verification strategy

Each issue has a red-green regression test before implementation. Settings and
DeepSeek clients use offline injected transports; netfetch redirect tests use
fake sockets. Reference tests use small local media/whisper fixtures and an
LLM that deliberately fails then succeeds. Audio tests use the existing
deterministic local provider and synthetic WAV. Browser tests use the local
server only. Full `unittest` discovery, `git diff --check`, and the documented
startup/health check run before each phase PR.

