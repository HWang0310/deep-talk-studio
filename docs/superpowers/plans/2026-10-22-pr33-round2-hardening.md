# PR #33 Round-2 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Nexus round-2 gaps in PR #33 without losing authorized acquisition failures, allowing adjacent-topic false positives, or relying on real network sockets in security tests.

**Architecture:** Keep the workbench orchestration and canonical engines unchanged. Persist each valid authorization attempt in the session and latest acquisition artifact, treat a failed authorized acquisition as an unresolved eligible reference, and expose that state through the existing readiness/partial-override path. Strengthen the deterministic topic guard with non-generic entity anchors and exclude server-controlled topic metadata from evidence scoring. Keep netfetch's pinned production path, replacing only test I/O with injected fakes while exercising redirect validation.

**Tech Stack:** Python 3.9+, `unittest`, `urllib.request`/`http.client`, vanilla workbench HTML, atomic JSON session storage.

**Spec:** `docs/WORKBENCH_CONTRACT.md` and Nexus round-2 review on PR #33 (`7a51022eabe3a616ad4e5cfe3da2c5b080537121`).

## Global Constraints

- Preserve all user-created/untracked workspace content and existing committed behavior outside PR #33.
- Never treat reference-video narration as factual evidence or claim mock LLM creative quality is accepted.
- Failed but validly authorized acquisitions remain visible as unresolved and block research unless the user supplies the existing explicit reason-bearing partial-analysis override.
- Public-source fetching remains HTTP(S)-only, public-unicast-only, pinned, redirect-capped, and proxy-disabled.
- Use failing regression tests before production changes; run focused tests after each task and the full suite before completion.
- Keep PR #33 open; commit and push only to its existing head branch.

## Review Focus

- A valid authorization followed by four download failures must remain `eligible=5`, `pending=4`, and block research after refresh; retry success must clear the failure without changing unrelated references.
- A report whose `topic` metadata matches the session but whose body is `大学留学生考试事件` must still fail, while the existing `莫斯科国立大学…旭日旗…` paraphrase passes.
- Redirects to literal loopback/private destinations must be rejected before a private socket is attempted, while a public HTTP(S) redirect remains accepted; no test may open a real socket.

---

### Task 1: Persist acquisition failures and enforce unresolved readiness

**Files:**
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Modify: `src/deeptalk_studio/webui_static/index.html`
- Test: `tests/test_workbench.py`
- Test: `tests/test_webui.py` (state/error visibility if the existing harness permits)
- Modify: `docs/WORKBENCH_CONTRACT.md`

**Interfaces:**
- `WorkbenchFlow.acquire_references(...)` records `status=failed`, `failure_stage=acquisition`, `failure_reason`, authorization text/timestamps, and retry count for valid authorization attempts; successful retry returns `status=downloaded` and clears the current failure fields.
- `_reference_readiness()` returns analyzed/eligible plus unresolved/pending and failed identifiers; failed authorized references are included in `eligible` and `pending_bvids`.
- `view()` and the HTML renderers expose the persisted failure reason and distinguish downloaded-pending from failed-retry states.

- [x] **Step 1: Write the failing regression tests**

  Add a flow test that simulates one successful acquisition and four `WorkbenchAcquisitionError`s, reloads the session, asserts all four failures and reasons are persisted/visible, asserts `eligible=5`, `analyzed=1`, and asserts research is blocked without an override but proceeds with a >=10-character reason while recording failed IDs. Add a retry assertion that a later successful attempt clears the failure. Add the smallest route/static assertion needed to prove the refreshed UI state carries the failed badge/reason and partial override remains visible.

- [x] **Step 2: Run the focused tests and verify RED**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench.ReferenceSynthesisTests tests.test_webui -v`

  Expected: the new failure-persistence/readiness assertions fail because `session.json` is unchanged on acquisition errors and failed references are omitted from readiness.

- [x] **Step 3: Implement the minimal persistence/readiness/UI change**

  In the acquisition loop, validate that the authorization text is valid before recording an attempted candidate, persist a latest `acquisition.json` failure record plus session state atomically on `WorkbenchAcquisitionError`, retain candidate metadata, increment attempt count, and clear failure fields on success. Count `failed` alongside `downloaded` as authorized unresolved references; include typed counts/reason fields in the comparison snapshot. Update analysis/research status copy and retry controls to show failed reasons without changing never-authorized candidates.

- [x] **Step 4: Run focused tests and verify GREEN**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench.ReferenceSynthesisTests tests.test_webui -v`

  Expected: all named regressions and existing focused tests pass; the persisted state survives a fresh `view()` call and the partial override is the only bypass.

- [x] **Step 5: Record task completion**

  Commit later with the consolidated PR fix commit after Tasks 2–3; do not stage unrelated untracked user artifacts.

### Task 2: Require a distinctive topic anchor and ignore spoofable metadata

**Files:**
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Test: `tests/test_workbench.py`

**Interfaces:**
- `ensure_topic_consistency(topic, texts, what=...)` preserves the existing coverage floor and additionally requires at least one non-generic CJK entity phrase (or meaningful ASCII term) from the topic to occur in model-authored body text.
- `_report_topic_texts()` no longer lets the server-overwritable `topic` metadata satisfy the body consistency check.

- [x] **Step 1: Write the failing tests**

  Add the exact negative case `莫斯科大学留学生旭日旗事件` vs `大学留学生考试事件`, a negative case with a matching topic metadata string but the same wrong body, and retain the positive semantic paraphrase test.

- [x] **Step 2: Run the topic tests and verify RED**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench.TopicConsistencyTests -v`

  Expected: the adjacent-topic and metadata-spoof tests fail under the current generic-bigram-only guard.

- [x] **Step 3: Implement the minimal anchor-aware guard**

  Derive anchor phrases by removing a small documented set of generic topic terms from contiguous CJK runs (and filtering ASCII stopwords), require an anchor hit in the combined body, and keep the existing coverage threshold for compatibility. Exclude `data.topic` from `_report_topic_texts()` while retaining it for display/storage.

- [x] **Step 4: Run topic tests and the workbench focused suite**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench.TopicConsistencyTests tests.test_workbench.ReferenceSynthesisTests -v`

  Expected: both new negatives fail closed and all existing Moscow-paraphrase and library workflow tests remain green.

### Task 3: Make netfetch security regressions completely offline

**Files:**
- Modify: `tests/test_workbench.py`
- Modify: `src/deeptalk_studio/workbench/netfetch.py` only if a small injectable hook is required to exercise the existing pinned path (no policy relaxation).

**Interfaces:**
- The pinned connection test uses a fake socket and asserts the only attempted sockaddr is the validated public address and DNS is resolved once.
- Redirect tests exercise HTTP(S) redirect handling with fake responses/resolvers, reject loopback/private targets before any private socket attempt, and accept a public redirect without external I/O.

- [x] **Step 1: Replace the real-socket test and add redirect regressions**

  Build deterministic fake socket/response objects in the test module. Cover a public-first/private-second DNS answer, a literal `127.0.0.1`/private redirect rejection, and a public redirect success path.

- [x] **Step 2: Run the netfetch tests and verify RED for the missing redirect assertion**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench.NetFetchTests -v`

  Expected: the old test no longer opens a socket; the new redirect-private assertion fails until the test harness exercises the real rejection path correctly.

- [x] **Step 3: Make only the smallest production hook correction, if needed**

  Preserve `_PinnedHTTPConnection` validation/pinning, redirect cap, and proxy disabling. Do not weaken checks or add an external dependency.

- [x] **Step 4: Run netfetch and workbench suites GREEN**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench.NetFetchTests tests.test_workbench -v`

  Expected: no test performs real DNS or socket I/O, all existing public/private/scheme checks pass, and the fake public redirect remains valid.

### Task 4: Documentation, verification, and handoff

**Files:**
- Modify: `docs/WORKBENCH_CONTRACT.md`
- Modify: `CHANGELOG.md`
- Create/maintain: `.superpowers/sdd/.../progress.md` (gitignored execution ledger only)

- [x] Update the contract's known limitation and B3 wording to say failed authorized acquisitions are unresolved/blocking until retry or explicit partial override.
- [x] Add a concise unreleased changelog entry naming the three fixes and the honest mock-quality boundary.
- [x] Run focused tests, `tests/test_webui.py`, and the full suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [x] Inspect `git diff`, ensure only intended tracked files are staged, commit on `agent/issue23-workbench`, push to `origin/agent/issue23-workbench`, and verify PR #33 remains open at the pushed SHA.
