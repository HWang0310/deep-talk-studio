# Audio Alignment Integration Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the approved media, transcript, alignment, material, placement, preview and QA modules through one repository-owned production entrypoint, then prove the same path with a real synthetic MP4/Remotion E2E.

**Architecture:** Preserve the existing deterministic modules and immutable artifacts. Add narrow orchestration/factory layers that own wiring, while providers, clocks and ID factories remain injectable test adapters. Repair upstream contracts rather than compensating in renderers.

**Tech Stack:** Python 3.9+, unittest, ffmpeg/ffprobe, Remotion 4.0.507, OpenAI official Python SDK adapter.

## Global Constraints

- Continue on `agent/audio-alignment-edit-bridge` from reviewed HEAD `67434d4b409ee078945100210970736179947f52`.
- Do not modify `main`, `v0.6.1`, reviewed Script/Research/Material history, tags or Releases.
- Keep Clean A-roll as canonical timeline and only primary audio; no cleanup, subtitles, BGM/SFX, publishing or automatic B-roll clip selection.
- Use failing tests first, immutable revisions, real file/SHA/probe validation and fail-closed Gates.
- Synthetic pass remains distinct from real-user E2E pass.

---

### Task 1: Preserve production-relevant Material fields

**Files:** Modify `src/deeptalk_studio/material_bridge.py`; modify `tests/test_material_bridge.py`; create `tests/test_material_projection_placement_integration.py`.

**Interfaces:** `build_material_production_view(...) -> dict` must preserve canonical `asset_type`, `capture` and `video_reference`; `build_visual_placements(...)` consumes them unchanged.

- [ ] Write a reviewed-package integration test proving image becomes `real_image`, ranged video becomes ready `real_video`, unranged video becomes `clip_selection_needed`, and `video_reference` survives projection.
- [ ] Run the test and confirm failure is missing projected fields.
- [ ] Copy only production-relevant canonical fields from Material Package; do not infer clip ranges or alter rights behavior.
- [ ] Run Material bridge, placement and new cross-module tests.
- [ ] Commit `fix: preserve material video placement metadata`.

### Task 2: Map complete Cue semantic windows and media duration

**Files:** Modify `src/deeptalk_studio/alignment_builder.py`, `src/deeptalk_studio/alignment_validation.py`, `src/deeptalk_studio/alignment_schema.py`; modify `tests/test_cue_timeline.py`, `tests/test_alignment_builder.py`, `tests/test_alignment_validation.py`.

**Interfaces:** `build_script_alignment(..., media=None)` consumes bound Media duration; each Cue maps anchor onset to the last uniquely matched unit before next Cue anchor or Beat end.

- [ ] Add failing tests for one long Cue, two Cues in one Beat, short anchor/long narration, segment/ambiguity downgrade and Media duration extending beyond final spoken unit.
- [ ] Confirm failures show anchor-only OUT and transcript-end duration.
- [ ] Derive semantic token indices after final char spans, require complete unique mapping, and set Cue unit IDs/times from full span while preserving anchor onset.
- [ ] Bind Alignment presentation duration to explicit Media or a new transcript root duration field and validate it by rederivation.
- [ ] Run alignment/cue/property tests and commit `fix: map full cue semantic windows`.

### Task 3: Support honest OpenAI segment timestamps

**Files:** Modify `src/deeptalk_studio/transcription/openai.py`; modify `tests/test_openai_transcription.py` and `tests/test_openai_transcription_smoke.py`.

**Interfaces:** `OpenAITranscriptionProvider.transcribe(...)` prefers real `words`; when absent, consumes real `segments[].start/end/text` and returns `timestamp_granularity="segment"`; neither present fails capability.

- [ ] Add failing word-preference, segment-fallback and no-timestamp tests.
- [ ] Confirm current adapter fails segment-only response.
- [ ] Normalize real segment boundaries without interpolation and retain boundary-risk intersection.
- [ ] Run provider/transcript/alignment coarse tests and commit `fix: preserve provider segment timestamps`.

### Task 4: Build canonical production QA factory

**Files:** Modify `src/deeptalk_studio/edit_bridge_qa.py`; create `tests/test_canonical_edit_bridge_qa.py`.

**Interfaces:** Add `CanonicalEditBridgeQAContext`; `build_canonical_edit_bridge_qa_inputs(context) -> EditBridgeQAInputs`; `run_canonical_edit_bridge_qa(context) -> dict`. The factory owns validators for roots, transcript, alignment, placement and preview.

- [ ] Add failing tests using real artifacts, then tamper Mapping, asset SHA and Preview audio/Manifest separately.
- [ ] Confirm generic `QACheck` alone cannot construct the canonical path.
- [ ] Assemble validators that call existing rederivation functions and real ffprobe/SHA checks; map failures to stable issues without caller booleans.
- [ ] Run generic and canonical QA/tamper tests.
- [ ] Commit `feat: wire canonical edit bridge qa`.

### Task 5: Implement real Bridge revision flow

**Files:** Modify `src/deeptalk_studio/edit_bridge_storage.py`, `src/deeptalk_studio/edit_bridge_workflow.py`, `src/deeptalk_studio/cli.py`, `.agents/skills/align-video/SKILL.md`; modify revision/CLI tests.

**Interfaces:** `resolve_adjustment_target(...)` uses filename/caption/readable name/Beat context/time neighborhood; `revise_real_edit_bridge_session(...)` applies real effective IN/OUT or overlay suppression, preserves semantic window, saves new Bridge/Preview/QA revision.

- [ ] Add failing tests for shorter/longer wording, earlier/later, keep-A-roll suppression, video later, ambiguity, and CLI calling the revision entrypoint.
- [ ] Confirm current empty adjustments and print-only CLI fail.
- [ ] Build structured adjustments with old/new effective times, provenance and reason; rerun validation/render/mux/QA for a new immutable revision.
- [ ] Run revision, timing, CLI and Skill tests.
- [ ] Commit `feat: apply natural language bridge revisions`.

### Task 6: Add one owner-controlled production session entrypoint

**Files:** Rewrite `src/deeptalk_studio/edit_bridge_workflow.py`; add `src/deeptalk_studio/edit_bridge_session.py`; modify `src/deeptalk_studio/cli.py`; modify `.agents/skills/align-video/SKILL.md`; create `tests/test_real_edit_bridge_session.py`, modify CLI tests.

**Interfaces:** `resolve_real_edit_bridge_session(session_root) -> RealEditBridgeSessionInputs`; `run_real_edit_bridge_session(inputs, provider, clock, id_factory, renderer=None) -> RealEditBridgeSessionResult`. This single owner calls concrete Tasks 3–26 modules and canonical QA.

- [ ] Add failing integration tests proving formal entrypoint calls real modules and CLI delegates to it after automatic canonical-root resolution.
- [ ] Confirm current stage-lambda harness/print-only CLI fail.
- [ ] Implement automatic latest approved Research/reviewed Script/reviewed Material/Production Plan/Manifest/QA/Clean A-roll resolution with ordinary ambiguity errors.
- [ ] Wire import, extraction, Mapping, Chunk Plan, provider, Transcript, Alignment, Material projection, Placement/timing, Bridge/storage, Remotion, audio mux, Manifest and canonical QA.
- [ ] Keep providers/clocks/IDs injectable but never require callers to assemble stages.
- [ ] Run workflow, CLI, Skill and immutable rerun tests.
- [ ] Commit `feat: run concrete aligned edit bridge sessions`.

### Task 7: Prove the exact production path with integrated synthetic E2E

**Files:** Create `tests/test_audio_alignment_integrated_e2e.py`; update `evaluations/audio-alignment-edit-bridge/run_full_eval.py`, `CHANGELOG.md`, `HANDOFF.md`, `README.md`, `ROADMAP.md`, `AGENTS.md`.

**Interfaces:** Use `run_real_edit_bridge_session` with deterministic timestamp provider and real MP4/image/video/Motion/Production roots; output a real `ALIGNED_PREVIEW.mp4` and canonical QA.

- [ ] Build a synthetic canonical reviewed root set containing real image, ranged real video, unranged real video, QA-ready Motion and real Clean A-roll with presentation offset/gap.
- [ ] Run the test red before production wiring is complete.
- [ ] Execute the exact production entrypoint and assert A-roll layer 0, image/Motion/ranged video staged, unranged video excluded, full semantic OUT, preserved audio presentation and truthful canonical QA.
- [ ] Run full unittest, A–AI/CB/CR/PA/property suites, real ffmpeg/Remotion E2E, renderer lint/typecheck, Skill validation, scope/sensitive/diff checks and provider smoke when authorized.
- [ ] Update documents with local-verification wording and real-user E2E pending status.
- [ ] Commit, push the development branch, verify main/tag/Release unchanged, and stop at the user upload Gate.

## Self-review

- Every Conditional Pass item 1–8 has one task and executable regression owner.
- Production workflow and QA each have one repository-owned factory/entrypoint; injected dependencies are adapters, not workflow lambdas.
- Material fields and Cue timing are fixed at their canonical producers.
- Segment fallback never interpolates word precision.
- Revision changes only Preview exposure and always produces new Bridge/Preview/QA revisions.
- Final E2E uses actual modules, ffmpeg/ffprobe and Remotion; no user media or secrets are committed.
