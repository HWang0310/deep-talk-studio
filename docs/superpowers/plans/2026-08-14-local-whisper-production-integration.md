# Local Whisper Production Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make whisper.cpp multilingual medium the V1 default local transcription provider, with repository-owned bootstrap/discovery, verified runtime token timestamps, and no API-key requirement in the formal Clean A-roll production path.

**Architecture:** Keep `TranscriptionProvider` and `ProviderTranscript` provider-neutral. Evolve the existing evidence-only whisper.cpp JSON parser into a reusable token parser, add a separate production bootstrap/runtime module under the user cache, and let `LocalWhisperCppTranscriptionProvider` execute one verified whisper.cpp process per existing `TranscriptionChunkPlan` chunk. The CLI resolves this local provider first; the OpenAI adapter remains an explicitly optional compatibility provider and is never consulted during V1 default resolution.

**Tech Stack:** Python 3.9+, standard-library subprocess/pathlib/hashlib/json/wave, whisper.cpp v1.9.2 with Metal on Apple Silicon, existing ffmpeg/ffprobe/Remotion pipeline, unittest/pytest-compatible test suite.

## Global Constraints

- V1 default is `whisper.cpp multilingual medium`; do not downgrade to small or add a second ASR/forced-aligner path.
- No model API key is required for the V1 default path; never check `OPENAI_API_KEY` before local provider resolution.
- Preserve `evaluations/local_asr_selection/` and its existing report/result/history unchanged.
- Only runtime-emitted whisper.cpp token offsets are accepted; no segment averaging, interpolation, script-position timing, LLM inference, or fixture fallback.
- Runtime/model binaries remain outside Git in `~/.cache/deep-talk-studio/transcription/...`; digest mismatch fails closed.
- Do not modify reviewed Script, approved Research, reviewed Material Package, Motion, Audio Alignment, Subtitle, or Edit Bridge semantics beyond wiring the real provider into the existing entrypoint.
- Keep canonical `main`, v0.6.1 tag, and GitHub Release unchanged; this work remains `V1.0 Candidate — Unreleased` on `agent/audio-alignment-edit-bridge`.

---

### Task 1: Evolve the whisper.cpp token parser into a provider-neutral reusable parser

**Files:**
- Modify: `src/deeptalk_studio/transcription/local_asr_selection.py`
- Modify: `tests/test_local_asr_selection.py`
- Test: `tests/test_local_whisper_cpp_provider.py`

**Interfaces:**
- Produce `parse_whisper_cpp_json(path, *, chunk_index, model_version, chunk_plan=None, provider_order_start=0, provider_request_id="local-whisper-cpp") -> ProviderTranscript`.
- Preserve the old selection-test call shape and evidence metadata while allowing production chunks to receive globally continuous provider order values.

- [x] **Step 1: Write failing parser regression tests** for non-zero `provider_order_start`, production request identity, and missing/invalid offsets.
- [x] **Step 2: Run the focused tests** and confirm they fail because the parser does not yet accept the production arguments.
- [x] **Step 3: Implement the smallest parser extension**; keep all offset validation and control-token filtering unchanged.
- [x] **Step 4: Run selection and parser tests** and confirm they pass without changing selection report/result files.

### Task 2: Add verified production cache and whisper.cpp bootstrap/discovery

**Files:**
- Create: `src/deeptalk_studio/transcription/local_whisper_cpp.py`
- Create: `tests/test_local_whisper_bootstrap.py`
- Modify: `.gitignore`

**Interfaces:**
- Produce `WhisperCppRuntimeSpec`, `WhisperCppInstallation`, `WhisperCppBootstrap`, and `production_transcription_cache_root()`.
- `WhisperCppBootstrap.ensure()` must detect a verified installation, otherwise acquire/build the pinned v1.9.2 runtime and download/verify the pinned medium model; it must write a provenance record and raise a clear fail-closed error on digest/version mismatch.

- [x] **Step 1: Write failing tests** for stable production cache separation, missing runtime/model preparation hooks, digest mismatch rejection, and provenance fields.
- [x] **Step 2: Run the focused bootstrap tests** and confirm they fail because the production bootstrap module is absent.
- [x] **Step 3: Implement cache/discovery/bootstrap** with injectable command/download functions for deterministic tests; use official pinned source/model URLs, Apple Silicon Metal build flags, SHA-256 verification, and no repository binaries.
- [x] **Step 4: Run the bootstrap tests** and confirm they pass, including the fail-closed digest case.

### Task 3: Implement `LocalWhisperCppTranscriptionProvider`

**Files:**
- Modify: `src/deeptalk_studio/transcription/local_whisper_cpp.py`
- Modify: `src/deeptalk_studio/transcription/__init__.py`
- Create: `tests/test_local_whisper_cpp_provider.py`

**Interfaces:**
- Produce `LocalWhisperCppTranscriptionProvider`, whose `transcribe(extracted_audio_artifact, chunk_plan, language, configured_model)` invokes the verified runtime for every chunk, parses direct token offsets, validates chunk-local bounds and global order, and returns `ProviderTranscript(timestamp_granularity="token")` with runtime/model/audio/chunk/raw-response provenance.

- [x] **Step 1: Write failing provider tests** for one-chunk execution, multi-chunk global order, direct token timestamp preservation, missing-token fail-closed behavior, and no API-key access.
- [x] **Step 2: Run the provider tests** and confirm they fail because the provider is absent.
- [x] **Step 3: Implement the provider** using an injectable runner/bootstrap for tests; never synthesize timestamps or catch errors into a cloud fallback.
- [x] **Step 4: Run provider tests plus existing transcript/chunk tests** and confirm all pass.

### Task 4: Make the formal production entrypoint local-first

**Files:**
- Modify: `src/deeptalk_studio/edit_bridge_session.py`
- Modify: `src/deeptalk_studio/cli.py`
- Modify: `.agents/skills/align-video/SKILL.md`
- Modify: `tests/test_edit_bridge_cli.py`
- Modify: `tests/test_align_video_skill.py`

**Interfaces:**
- Add `resolve_default_transcription_provider()` (local whisper.cpp medium) and use it in `deeptalk align-video` after the user supplies a Clean A-roll; missing model/runtime must report ordinary-language preparation/failure, never an API-key request.
- Preserve dependency injection for existing tests and optional OpenAI adapter compatibility.

- [x] **Step 1: Write failing CLI/skill regressions** asserting absent `OPENAI_API_KEY` does not block local resolution and user copy never asks for provider/model/API configuration.
- [x] **Step 2: Run focused CLI/skill tests** and confirm the current API-key gate fails them.
- [x] **Step 3: Implement local-first resolver and CLI wiring**; let the existing concrete session call the provider’s declared default model without changing downstream stages.
- [x] **Step 4: Run CLI/skill and full non-render test suites** and confirm no OpenAI adapter regressions.

### Task 5: Run real no-key smoke and production E2E evidence

**Files:**
- Create/update external evidence under the user cache only; never commit private audio or binaries.
- No deterministic smoke fixture was added; the no-key smoke and short E2E use real whisper.cpp and external, non-private evidence.

- [x] **Step 1: Run a real no-key local provider smoke** on the existing non-private synthetic audio, recording runtime/model/model SHA/audio SHA/token count/RTF/timestamp granularity/Timed Transcript digest.
- [x] **Step 2: Run the formal production E2E** with non-private synthetic Clean A-roll and the reviewed upstream roots, preserving previous artifacts and using the real local provider; run Remotion/ffprobe/Manifest/QA only if the environment and renderer are available.
- [x] **Step 3: If any real Gate fails, record the exact blocker and do not substitute deterministic or cloud output.**

### Task 6: Update project contracts and handoff

**Files:**
- Modify: `README.md`
- Modify: `PRD.md`
- Modify: `ROADMAP.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`
- Modify: `.agents/skills/align-video/SKILL.md` if final wording needs alignment with real evidence.

- [x] **Step 1: Document local-first V1, production cache/provenance, optional cloud adapter, and current Gate results.**
- [x] **Step 2: Run a secret scan and full test suite.**
- [ ] **Step 3: Commit and push only the scoped integration changes; do not tag or release.**
- [ ] **Step 4: Verify branch/main/tag/Release status and prepare the complete user-to-ChatGPT handoff as the final response.**
