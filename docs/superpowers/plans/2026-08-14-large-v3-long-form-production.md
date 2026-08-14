# Large-v3 Long-form Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make full-precision whisper.cpp large-v3 with `--dtw large.v3` the no-key V1 default, record truthful overlap evidence when necessary, and run the full 272-second production chain.

**Architecture:** Keep the existing local provider and downstream production entrypoint. Change only the provider's pinned model specification and exact DTW preset, then add a raw-evidence overlap error that is serializable by a repository evaluation runner without changing or canonicalizing runtime timestamps. The evaluator uses the formal provider and formal edit-bridge entrypoint; it records liveness while a full Remotion render runs.

**Tech Stack:** Python 3.9+ standard library, whisper.cpp v1.9.2 / Apple Silicon Metal, ggerganov Hugging Face model files, ffmpeg/ffprobe, Remotion, existing unittest suite.

## Global Constraints

- V1 production default is only full `ggml-large-v3.bin`, SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, exact bytes `3095033483`, and DTW preset `large.v3`.
- Never silently use medium, turbo, quantized models, cloud providers, API keys, VibeASR, a forced aligner, a dictionary, LLM transcript correction, or a second ASR.
- Existing medium Selection Gate artifacts and medium cache are immutable history; production-only assumptions change to large-v3.
- Raw whisper.cpp token offsets remain evidence. Missing, out-of-range, non-monotonic or overlapping timing fails closed; no clipping, interpolation, averaging, sorting, deleting, or segment fallback.
- Overlap canonicalization is out of scope unless a later independent ChatGPT Review approves a versioned/recomputable raw-versus-derived contract.
- Use the existing 272-second non-private audio and non-private synthetic Clean A-roll. Do not ask the user for video or upload private media.
- Keep `agent/audio-alignment-edit-bridge`, main, v0.6.1 and GitHub Releases unchanged; status stays `V1.0 Candidate — Unreleased`.

---

### Task 1: Make large-v3 the verified production default

**Files:**
- Modify: `src/deeptalk_studio/transcription/local_whisper_cpp.py`
- Modify: `tests/test_local_whisper_bootstrap.py`
- Modify: `tests/test_local_whisper_cpp_provider.py`
- Modify: `tests/test_edit_bridge_cli.py`

**Interfaces:**
- `WhisperCppRuntimeSpec` gains `dtw_preset: str`.
- `WhisperCppInstallation` carries `dtw_preset` and bootstrap provenance writes it.
- `LocalWhisperCppTranscriptionProvider.default_configured_model == "large-v3"` and its runtime command contains `--dtw large.v3`.

- [x] **Step 1: Write failing default and command regressions.**

```python
def test_v1_default_is_full_large_v3_with_matching_dtw():
    provider = LocalWhisperCppTranscriptionProvider()
    self.assertEqual(provider.default_configured_model, "large-v3")
    self.assertEqual(provider.default_dtw_preset, "large.v3")

def test_provider_command_uses_large_v3_dtw_preset():
    result = provider.transcribe(audio, plan, "zh", "large-v3")
    self.assertIn("large.v3", captured_command)
    self.assertNotIn("medium", captured_command)
```

- [x] **Step 2: Run the focused tests and confirm they fail because the default is currently medium.**

Run: `.venv/bin/python -m pytest -q tests/test_local_whisper_bootstrap.py tests/test_local_whisper_cpp_provider.py tests/test_edit_bridge_cli.py`

Expected: failure showing `medium` where `large-v3` or `large.v3` is required.

- [x] **Step 3: Change only the pinned production spec and provider metadata.**

```python
WHISPER_CPP_MODEL_NAME = "large-v3"
WHISPER_CPP_MODEL_SHA256 = "64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2"
WHISPER_CPP_MODEL_BYTES = 3095033483
WHISPER_CPP_DTW_PRESET = "large.v3"
```

Add `dtw_preset` to `WhisperCppRuntimeSpec`, `WhisperCppInstallation`, provenance and provider metadata. Build commands from the installation's preset. Replace medium-specific error text with the pinned model name. Keep the medium constants only if explicitly namespaced as historical evidence; no default path may reference them.

- [x] **Step 4: Run focused production-provider tests and confirm they pass.**

Run: `.venv/bin/python -m pytest -q tests/test_local_whisper_bootstrap.py tests/test_local_whisper_cpp_provider.py tests/test_edit_bridge_cli.py`

Expected: all pass; test fake models use explicit test specs rather than production medium assumptions.

### Task 2: Preserve raw overlap evidence while retaining the fail-closed provider Gate

**Files:**
- Modify: `src/deeptalk_studio/transcription/local_asr_selection.py`
- Modify: `src/deeptalk_studio/transcription/local_whisper_cpp.py`
- Modify: `tests/test_local_asr_selection.py`
- Modify: `tests/test_local_whisper_cpp_provider.py`

**Interfaces:**
- `inspect_whisper_cpp_token_overlaps(path, *, chunk_index, provider_order_start, model, dtw_preset, runtime_version, chunk_boundary) -> tuple[dict, ...]` reads only raw JSON and produces audit mappings.
- `WhisperCppTokenOverlapError(WhisperCppBootstrapError)` exposes `overlaps: tuple[dict, ...]` and `raw_response_digests: tuple[str, ...]`.

- [x] **Step 1: Write a failing raw-evidence regression.**

```python
def test_overlap_error_preserves_raw_pair_evidence_without_canonicalizing():
    with self.assertRaises(WhisperCppTokenOverlapError) as raised:
        provider.transcribe(audio, plan, "zh", "large-v3")
    item = raised.exception.overlaps[0]
    self.assertEqual(item["previous_raw_start_seconds"], "0")
    self.assertEqual(item["current_raw_start_seconds"], "0.19")
    self.assertEqual(item["overlap_duration_seconds"], "0.01")
    self.assertEqual(item["dtw_preset"], "large.v3")
```

- [x] **Step 2: Run the overlap regression and confirm it fails because the current error has no serializable raw evidence.**

Run: `.venv/bin/python -m pytest -q tests/test_local_whisper_cpp_provider.py::LocalWhisperCppProviderTests::test_overlap_error_preserves_raw_pair_evidence_without_canonicalizing`

Expected: failure because `WhisperCppTokenOverlapError` does not exist or lacks `overlaps`.

- [x] **Step 3: Implement raw JSON inspection without altering ProviderTimedUnit timestamps.**

```python
if raw_current_start < raw_previous_end:
    overlaps.append({
        "chunk_index": chunk_index,
        "previous_token_text": previous_text,
        "current_token_text": current_text,
        "previous_raw_start_seconds": format(previous_start, "f"),
        "previous_raw_end_seconds": format(previous_end, "f"),
        "current_raw_start_seconds": format(current_start, "f"),
        "current_raw_end_seconds": format(current_end, "f"),
        "overlap_duration_seconds": format(previous_end - current_start, "f"),
    })
```

Also record segment IDs, token/raw/provider order, control-token flags, chunk-boundary status, model, DTW preset, runtime version and raw JSON digest. Raise the structured error before Timed Transcript construction. Do not modify raw JSON, text, token order or offsets.

- [x] **Step 4: Run parser/provider regressions and confirm they pass.**

Run: `.venv/bin/python -m pytest -q tests/test_local_asr_selection.py tests/test_local_whisper_cpp_provider.py`

Expected: direct raw timing is preserved; overlap still blocks downstream work; the structured evidence contains all required audit fields.

### Task 3: Add a reproducible large-v3 long-form evidence runner

**Files:**
- Create: `evaluations/local_asr_selection/run_large_v3_production_gate.py`
- Create: `tests/test_large_v3_production_gate.py`

**Interfaces:**
- `run_large_v3_smoke(audio_path, reference_path, evidence_path) -> dict` invokes the formal local Provider without API keys and writes a versioned external evidence JSON.
- `run_full_large_v3_session(session_root, repo_root, monitor_path) -> dict` invokes `resolve_real_edit_bridge_session` and `run_real_edit_bridge_session` once; it records elapsed time, PID/liveness checks, output growth and terminal stage.

- [x] **Step 1: Write failing report-contract tests.**

```python
def test_overlap_report_requires_every_raw_audit_field():
    report = build_overlap_report([overlap])
    self.assertEqual(report["artifact_version"], "local-whisper-large-v3-overlap-evidence/1")
    self.assertIn("previous_raw_end_seconds", report["overlaps"][0])
    self.assertIn("raw_response_digest", report["overlaps"][0])

def test_liveness_record_does_not_mark_a_live_renderer_as_hung():
    record = monitor_snapshot(pid=123, elapsed_seconds=120, alive=True, output_bytes=4096)
    self.assertEqual(record["state"], "running")
```

- [x] **Step 2: Run the new evaluator tests and confirm they fail because the runner does not exist.**

Run: `.venv/bin/python -m pytest -q tests/test_large_v3_production_gate.py`

Expected: import failure for `run_large_v3_production_gate`.

- [x] **Step 3: Implement the evaluator with external-cache-only outputs.**

```python
result = provider.transcribe(extracted_audio, plan, "zh", "large-v3")
evidence = {
    "artifact_version": "local-whisper-large-v3-smoke/1",
    "api_keys": {"OPENAI_API_KEY": False, "ANTHROPIC_API_KEY": False, "GOOGLE_API_KEY": False},
    "provider": provider_summary(result),
}
```

Catch only `WhisperCppTokenOverlapError` to write its exact raw evidence and return `BLOCKED`; re-raise other failures. Use `subprocess.Popen` only for the outer full-session monitor. Sample parent/child liveness and output-file growth at a fixed interval, never terminate a live process merely for elapsed time. Persist monitor/evidence beneath `~/.cache/deep-talk-studio/transcription/evidence/` and `.../e2e/`, not Git.

- [x] **Step 4: Run evaluator unit tests and the focused provider suite.**

Run: `.venv/bin/python -m pytest -q tests/test_large_v3_production_gate.py tests/test_local_whisper_cpp_provider.py tests/test_local_whisper_bootstrap.py`

Expected: report schemas and liveness rules pass; no test invokes network/model inference.

### Task 4: Execute the actual large-v3 smoke and full-length formal E2E

**Files:**
- External only: `~/.cache/deep-talk-studio/transcription/evidence/large-v3-production-smoke.json`
- External only when blocked: `~/.cache/deep-talk-studio/transcription/evidence/large-v3-overlap-evidence.json`
- External only: `~/.cache/deep-talk-studio/transcription/e2e/formal-large-v3-session/`

**Interfaces:**
- Use `ggml-large-v3.bin` through `WhisperCppBootstrap.ensure()` and `LocalWhisperCppTranscriptionProvider`.
- Use the same 272.367-second audio SHA `c1b08fe694eb59d598af2fb06b29f165ee341afc82048e999ddb362dceeba601`.

- [x] **Step 1: Bootstrap/download large-v3 and verify runtime/model provenance.**

Run: `.venv/bin/python -c 'from deeptalk_studio.transcription.local_whisper_cpp import WhisperCppBootstrap; print(WhisperCppBootstrap().ensure())'`

Expected: external large-v3 cache exists, SHA and exact bytes match, runtime is v1.9.2 and acceleration is Apple Silicon Metal.

- [x] **Step 2: Run the real no-key 272-second large-v3 smoke.**

Run: `.venv/bin/python evaluations/local_asr_selection/run_large_v3_production_gate.py smoke --audio /Users/hwang/.cache/deep-talk-studio/asr-selection/eval/eval_cn_single_speaker_24k_mono.wav --reference /Users/hwang/.cache/deep-talk-studio/asr-selection/eval/reference.txt --evidence-root /Users/hwang/.cache/deep-talk-studio/transcription/evidence`

Expected: either a token-level ProviderTranscript/Timed Transcript/Alignment evidence report or a structured overlap evidence report. Never substitute medium or cloud output.

- [x] **Step 3: If smoke timing passes, run the full-length session under the liveness monitor.**

Run: `.venv/bin/python evaluations/local_asr_selection/run_large_v3_production_gate.py full-session --session-root /Users/hwang/.cache/deep-talk-studio/transcription/e2e/formal-large-v3-session --source-video /Users/hwang/.cache/deep-talk-studio/transcription/e2e/synthetic-selection-clean-aroll.mov --repo-root .`

Expected: full local large-v3 transcription, Timed Transcript, Alignment, reviewed Material, Motion, subtitle, Bridge, full Remotion preview, ffprobe/Manifest and canonical QA. A live renderer remains running; a genuine failure records stage and monitor evidence.

- [x] **Step 4: Inspect evidence and state the Gate truthfully.**

Run: `jq . /Users/hwang/.cache/deep-talk-studio/transcription/evidence/large-v3-production-smoke.json`

Expected: report includes model/DTW/runtime/RTF/token count/proper-noun comparison/overlap count. If overlap or a full E2E stage fails, retain `REAL USER CLEAN A-ROLL GATE = BLOCKED`.

### Task 5: Update contracts, verify, commit and push

**Files:**
- Modify: `README.md`
- Modify: `PRD.md`
- Modify: `ROADMAP.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`
- Modify: `.agents/skills/align-video/SKILL.md`
- Modify: `docs/superpowers/plans/2026-08-14-large-v3-long-form-production.md`

- [x] **Step 1: Update user and agent documentation with the quality-first large-v3 decision.**

Document that medium remains historical Selection evidence, large-v3 is the only V1 default, correct DTW is `large.v3`, cache remains external and no API key is needed. Record the actual smoke/E2E outcome and unresolved overlap/render facts without calling a blocked Gate ready.

- [x] **Step 2: Run all repository verification.**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m compileall -q src tests && git diff --check`

Expected: zero test failures, compile success and no whitespace errors.

- [ ] **Step 3: Run a credential-shaped secret scan and inspect the scoped diff.**

Run: `git grep -Il -E 'sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}' -- .`

Expected: no credential-shaped value; only model checksums, source URLs, tests, evaluator, docs and contract changes are staged.

- [ ] **Step 4: Commit and push only this scoped work.**

```bash
git add docs/superpowers/specs/2026-08-14-large-v3-long-form-design.md docs/superpowers/plans/2026-08-14-large-v3-long-form-production.md src/deeptalk_studio/transcription tests evaluations README.md PRD.md ROADMAP.md AGENTS.md CHANGELOG.md HANDOFF.md .agents/skills/align-video/SKILL.md
git commit -m "feat: validate large-v3 long-form transcription"
git push origin agent/audio-alignment-edit-bridge
```

- [ ] **Step 5: Verify GitHub branch/main/tag/release and provide the self-contained ChatGPT handoff.**

Run: `gh api repos/HWang0310/deep-talk-studio/compare/main...agent/audio-alignment-edit-bridge`

Expected: branch is comparable, main and v0.6.1 unchanged, no Release is created, and the final handoff accurately reports whether the real-user Gate remains blocked or is ready.
