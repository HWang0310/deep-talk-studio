# Unified Save Folder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save new transcript batches under one user-selected root folder with original media and complete ASR artifacts, while preserving and explicitly copy-archiving historical work.

**Architecture:** Reuse user-level `downloads_dir` setting storage and validation, expose a native folder picker on macOS, and attach a collision-safe batch directory to each transcript session. A focused archive helper writes source files exclusively, updates only its own previously generated merge file, and supports explicit copy-only archival for legacy sessions.

**Tech Stack:** Python 3.9+, `http.server`, standard-library filesystem/subprocess APIs, existing unittest/pytest suites, vanilla HTML/JavaScript, Playwright CLI.

**Spec:** `docs/superpowers/specs/2026-10-24-unified-save-folder-design.md`

## Global Constraints

- Preserve API Key, conversation history, session files, and existing artifacts.
- No extra LLM requests or Bilibili requests during browser fixture acceptance.
- Bilibili downloads still require explicit per-batch consent.
- Never silently disable or bypass a configured proxy.
- Do not merge or publish; deliver to the existing open PR #48.

## Review Focus

- Unicode labels, path traversal, duplicate titles, and symlinked archive paths must not escape the chosen root or overwrite prior files (Task 2).
- Missing, read-only, or replaced save roots and interrupted writes must fail safely while preserving session-local artifacts (Task 1 and Task 2).
- A failed third item followed by retry must keep successful original media/transcripts byte-identical and update only its own files plus the merged output (Task 2).
- Historical sessions whose original media lives outside the configured root must be copied only when the source is a valid existing artifact; retrying archival must not duplicate or overwrite output (Task 3).
- Proxy refusal on `127.0.0.1:7897` must be diagnosed as proxy connection failure, without altering proxy state or mislabeling it as Whisper failure (Task 3).

---

### Task 1: Save-folder setting and native chooser

**Files:**
- Modify: `src/deeptalk_studio/workbench/settings.py`
- Modify: `src/deeptalk_studio/workbench/flow.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/index.html`
- Test: `tests/test_workbench.py`
- Test: `tests/test_five_transcripts.py`

**Interfaces:**
- Consumes: existing `downloads_dir` persisted field and `/api/workbench/settings` route.
- Produces: validated existing writable root using `downloads_dir`; `POST /api/workbench/settings/folder-picker` returns `{path, cancelled}` or an actionable fallback error; settings page labels the single root **保存文件夹**.

- [x] **Step 1: Write failing tests** for save-root write validation and persistence, picker cancellation/unsupported-platform behavior, settings route and masked-key preservation.
- [x] **Step 2: Run focused tests and confirm expected failures.** Run: `PYTHONPATH=src python3 -m unittest tests.test_workbench tests.test_five_transcripts -v`. Expected: failures for missing writable-root validation and picker route/UI.
- [x] **Step 3: Implement settings validation, a shell-free macOS folder picker, same-origin JSON route/body cap, and the settings UI chooser/path display.** Keep the existing API Key untouched when only the directory changes.
- [x] **Step 4: Run the focused tests.** Expected: all focused tests pass; unset root still uses session-local behavior.
- [x] **Step 5: Commit** `feat: add a persistent unified save folder`.

### Task 2: Per-batch automatic archive and incremental retry

**Files:**
- Create: `src/deeptalk_studio/workbench/transcript_archive.py`
- Modify: `src/deeptalk_studio/workbench/five_transcripts.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/transcripts.html`
- Test: `tests/test_five_transcripts.py`

**Interfaces:**
- Consumes: validated `downloads_dir`, transcript source `references/{BVID}/transcript.json`, media path and SHA recorded by acquisition.
- Produces: session `save_batch_path`; batch subfolders `视频/` and `口播稿/`; each complete item returns exact media/TXT/JSON paths; batch-root `合并参考稿.txt` is complete and refreshed after each item.

- [ ] **Step 1: Write failing tests** for collision-safe task directory layout, direct media destination with play-count suffix, full TXT+JSON exports, immediate incomplete merge after item 1, preserved item 1/2 bytes after item 3 failure/retry, final exact merged contents, and temp WAV cleanup.
- [ ] **Step 2: Run the focused tests and confirm expected failures.** Expected: missing batch paths/exports and incremental merge assertions fail.
- [ ] **Step 3: Implement safe batch allocation, exclusive transcript/media artifact export, hash-tracked merge updates, restart-stable session paths, and an optional sanitized user batch label.** Keep canonical session artifacts as well as automatic root copies.
- [ ] **Step 4: Run the focused tests.** Expected: all retry and persistence assertions pass; no existing successful item is rewritten during a failed-item retry.
- [ ] **Step 5: Commit** `feat: autosave transcript batches incrementally`.

### Task 3: Historical copy archive, open-folder action, proxy guidance

**Files:**
- Modify: `src/deeptalk_studio/workbench/transcript_archive.py`
- Modify: `src/deeptalk_studio/workbench/five_transcripts.py`
- Modify: `src/deeptalk_studio/webui.py`
- Modify: `src/deeptalk_studio/webui_static/transcripts.html`
- Test: `tests/test_five_transcripts.py`
- Test: `docs/WORKBENCH_CONTRACT.md`

**Interfaces:**
- Consumes: existing session references plus stored source fingerprints and batch metadata.
- Produces: explicit copy-only `POST /api/workbench/transcripts/archive`, stored-destination `POST /api/workbench/transcripts/open-folder`, visible paths/open/archive controls, and actionable local-proxy-refused failure text.

- [ ] **Step 1: Write failing tests** for historical copy preservation/idempotence, missing or symlinked source rejection, open-folder stored-path validation, and proxy refusal classification with no settings mutation.
- [ ] **Step 2: Run tests and confirm expected failures.** Expected: missing archive/open actions and proxy diagnostics assertions fail.
- [ ] **Step 3: Implement explicit copy-only archival, platform folder opening of a session-owned destination, per-item path feedback, and proxy-specific actionable text.** Update the canonical Workbench contract to reflect root-folder behavior.
- [ ] **Step 4: Run focused tests.** Expected: old originals remain byte-identical; proxy settings remain unchanged.
- [ ] **Step 5: Commit** `feat: archive history safely and explain proxy failures`.

### Task 4: Full isolated regression and real browser acceptance

**Files:**
- Create/update: `evaluations/unified_save_folder/README.md`
- Create: desktop and mobile Playwright screenshots under `evaluations/unified_save_folder/screenshots/`

**Interfaces:**
- Consumes: Tasks 1–3 API/UI behavior.
- Produces: reproducible browser evidence for configured root, 3rd-item failure and retry, complete files, folder opening action, refresh recovery, explicit historical copy, and narrow/mobile layout.

- [ ] **Step 1: Run full pytest and unittest with temporary user settings/session roots.** Expected: no API Key/session/history access outside the temporary root; full suites pass or failures are reported by name.
- [ ] **Step 2: Use the Playwright CLI in headed Chromium** at desktop and mobile widths with only offline fixtures; verify actual path and files, byte identity, restart/refresh recovery, and no paid requests.
- [ ] **Step 3: Record exact commands, counts, fixture boundaries, screenshots, and any remaining limitation in `evaluations/unified_save_folder/README.md`**; update docs only to match observed behavior.
- [ ] **Step 4: Run `git diff --check`, sensitive-data scan, focused tests, and final diff review.** Expected: clean diff checks and no secrets/user artifacts.
- [ ] **Step 5: Commit** `test: verify unified save folder in isolated browsers`.
