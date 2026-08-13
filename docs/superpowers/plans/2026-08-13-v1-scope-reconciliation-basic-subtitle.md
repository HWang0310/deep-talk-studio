# V1 Scope Reconciliation + Basic Subtitle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Hook-aware Script review hardening and burned-in Basic Subtitle V1 to the existing canonical Clean A-roll rough-cut path.

**Architecture:** Keep Script/Research/Material and the reviewed alignment architecture unchanged. Derive one immutable subtitle artifact from Timed Transcript, bind it through Edit Bridge and Preview Manifest, render it in the existing Remotion composition, and rederive every safety conclusion in repository-owned QA.

**Tech Stack:** Python 3.9+, strict JSON contracts, unittest, Remotion 4.0.507, TypeScript, ffmpeg/ffprobe.

## Global Constraints

- Continue on `agent/audio-alignment-edit-bridge` from `20da05231520aafe1b4d89fb2c95b9143521c9df`.
- Do not modify canonical `main`, `v0.6.1`, reviewed Script/Research/Material history, tags or Releases.
- Clean A-roll remains the canonical timeline and only primary audio.
- Subtitle timing comes only from real Timed Transcript boundaries; segment timing never becomes word precision.
- Do not implement A-roll cleanup, BGM/SFX, title/cover, publishing, karaoke, retention scoring or NLE-specific export.
- Use TDD, immutable revisions, digest binding, real renderer verification and fail-closed canonical QA.

---

### Task 1: Reconcile the Hook-aware Script contract

**Files:** Modify `config/script-profile.json`, `src/deeptalk_studio/script_prompt.py`, `src/deeptalk_studio/script_review.py`, `src/deeptalk_studio/schema.py`, `.agents/skills/write-script/SKILL.md`, `docs/SCRIPT_CONTRACT.md`; modify `tests/test_script_review.py`.

**Interfaces:** Existing Script Draft schema stays `0.4`; new reviews emit consistency `0.4.2`; `narrative_structure=fail` plus `hook_structure` becomes blocking while old reviewed `0.4.1` artifacts remain valid.

- [x] Add a failing review test showing a missing opening/value/re-hook/payoff finding cannot become reviewed.
- [x] Add a failing compatibility test showing existing `0.4.1` linkage remains readable after the new mapping.
- [x] Add `hook_structure` to the typed issue contract and deterministic blocking mapping.
- [x] Update Writer/Profile/Reviewer instructions without adding duplicate Script fields.
- [x] Run Script review, validation, storage and workflow tests.

### Task 2: Build deterministic subtitle profile and artifact

**Files:** Create `config/subtitle-profile.json`, `src/deeptalk_studio/subtitle_profile.py`, `src/deeptalk_studio/subtitle_builder.py`, `src/deeptalk_studio/subtitle_storage.py`; create `tests/test_subtitle_profile.py`, `tests/test_subtitle_builder.py`, `tests/test_subtitle_storage.py`.

**Interfaces:** `build_subtitle_artifact(transcript, media, profile, subtitle_id, created_at) -> dict`; `validate_subtitle_artifact(...)`; `render_srt(...)`; immutable storage returns JSON/SRT paths.

- [x] Add failing profile validation tests for version, geometry, two-line capacity and digest.
- [x] Add failing word-level tests with hand-derived cue IN/OUT and display text.
- [x] Add failing segment-only tests proving coarse one-segment cues and no fabricated word timing.
- [x] Add failing tests for empty text, overlap/out-of-bounds, transcript revision/digest changes and artifact tampering.
- [x] Implement minimal deterministic grouping, safe normalization, schema validation, digest and SRT.
- [x] Add immutable save/load tests and run the targeted suite.

### Task 3: Bind subtitle roots into Edit Bridge and Preview

**Files:** Modify `src/deeptalk_studio/edit_bridge_schema.py`, `src/deeptalk_studio/edit_bridge_planner.py`, `src/deeptalk_studio/edit_bridge_qa.py`, `src/deeptalk_studio/aligned_preview/base.py`, `src/deeptalk_studio/aligned_preview/remotion.py`; modify relevant fixtures and tests.

**Interfaces:** Edit Bridge root bindings add `subtitle_artifact_digest` and `subtitle_profile_digest`; renderer project records subtitle-enabled state and artifact digest; Preview Manifest binds current Subtitle/Transcript/Profile.

- [x] Add failing Bridge validation tests for missing or changed subtitle roots.
- [x] Add failing renderer staging tests proving subtitle payload is required on the formal path.
- [x] Add failing Manifest/QA tests for subtitle tamper, transcript mismatch and renderer disabled.
- [x] Implement root binding, renderer project metadata, Manifest binding and canonical revalidation.
- [x] Run Bridge, renderer, Manifest and QA targeted tests.

### Task 4: Render Basic Subtitle V1 with a global safe area

**Files:** Create `renderer_templates/aligned_preview_remotion/src/BasicSubtitles.tsx`; modify `AlignedPreview.tsx`, `Root.tsx`, `index.css`; modify `tests/test_aligned_preview_remotion.py` and renderer TypeScript checks.

**Interfaces:** Remotion props contain controlled subtitle cues/profile. The active cue is selected by current frame; visual overlays use one content-safe region; subtitles occupy one reserved lower region for every source kind.

- [x] Add a failing renderer contract test for actual cue rendering and no karaoke behavior.
- [x] Add a failing safe-area test proving Motion/visual overlays cannot occupy the subtitle region.
- [x] Implement a separate frame-driven subtitle component with at most two lines and a high-contrast plate.
- [x] Run ESLint and TypeScript typecheck.

### Task 5: Integrate the single production entrypoint and revisions

**Files:** Modify `src/deeptalk_studio/edit_bridge_session.py`, `src/deeptalk_studio/narration_storage.py`, `.agents/skills/align-video/SKILL.md`; modify `tests/test_real_edit_bridge_session.py`, `tests/test_preview_adjustments.py`, `tests/test_audio_alignment_integrated_e2e.py`.

**Interfaces:** Formal run creates Subtitle after Transcript, saves JSON/SRT, passes it into Bridge/renderer/QA; load/revise rehydrates and revalidates the same subtitle and produces a new burned-in Preview revision.

- [x] Add failing exact-entrypoint tests for subtitle creation, storage and root binding.
- [x] Add failing natural-language revision test showing the new Preview still binds and enables current subtitles.
- [x] Add regression assertions for image/video/Motion Placement and unchanged Clean A-roll audio.
- [x] Implement orchestration with no new stage lambdas or caller-owned QA.
- [x] Run session, revision, audio and integrated tests.

### Task 6: Verify real synthetic Remotion E2E

**Files:** Modify `tests/test_audio_alignment_integrated_e2e.py` and evaluation summaries only if behavior requires it.

**Interfaces:** The existing exact `run_real_edit_bridge_session` test renders one actual 1920x1080/30fps Preview with image, ranged video, unranged-video gap, Motion, burned subtitles and one Clean A-roll audio stream.

- [x] Run the exact-entrypoint test with real Remotion enabled.
- [x] Inspect ffprobe, output digest/size, Manifest bindings and canonical QA.
- [x] Verify subtitle cues continue over A-roll/image/Motion periods and overlay safe area is deterministic.
- [x] Record real provider as unavailable unless an authorized key/media is present; do not fake it.

### Task 7: Synchronize project records and push Unreleased branch

**Files:** Modify `README.md`, `PRD.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md`, `HANDOFF.md`, `docs/ARCHITECTURE.md`, `docs/EDIT_BRIDGE_CONTRACT.md`, and production docs whose subtitle exclusions are now obsolete.

**Interfaces:** User handoff is self-contained; official Release remains v0.6.1.

- [x] Run full unittest, subtitle targeted suite, renderer lint/typecheck, Skill validation, scope scan and sensitive-data scan.
- [x] Update docs with exact capability, limitations, warnings, provider status and real-user E2E pending status.
- [x] Inspect Git diff, commit scoped changes and push `agent/audio-alignment-edit-bridge`.
- [x] Verify remote branch, main/tag/Release unchanged and stop before real-user video.

## Self-review

- Every product requirement A–J has an executable owner in Tasks 2–6.
- Hook hardening reuses the existing Script representation and review dimension.
- Subtitle generation, rendering and QA all consume the same artifact; no renderer reinterprets transcript text.
- Segment precision is explicitly coarse and cannot pass as word precision.
- Natural-language visual revisions preserve the subtitle binding while producing immutable new video revisions.
- The exact formal production entrypoint, not a fixture-only shortcut, owns the integrated verification.
