# Post-Alignment Full Visual Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe, natural-language-controlled episode visual planning and use it to produce a richer real-user visual preview.

**Architecture:** A new preference artifact resolves persistent default, episode override and human-preview revisions. A post-alignment plan projects grounded visual opportunities through existing global correspondence, then feeds optional digest bindings into the existing Production, Placement, Bridge and QA chains.

**Tech Stack:** Python 3.11, existing JSON-schema validator, Remotion, pytest, ffmpeg/ffprobe.

**Spec:** `docs/superpowers/specs/2026-08-22-post-alignment-full-visual-planning-design.md`

## Global Constraints

- Do not modify reviewed Script, approved Research, raw Transcript, Alignment core, thresholds, Basic Subtitle or V1 release state.
- Only real inspected capture or existing reviewed/generated asset can enter a Material placement.
- Every new Motion payload remains grounded in approved Research and passes current renderer/Production QA.
- All visual time is projected from the existing `script-alignment/2` global correspondence; B011 remains isolated and B018 trailing ad-lib remains A-roll.
- Persistent Default changes only for explicit long-term language; this episode remains an override.

---

### Task 1: Episode Visual Preference contract and parser

**Files:**
- Create: `src/deeptalk_studio/episode_visual_preference.py`
- Create: `src/deeptalk_studio/episode_visual_preference_schema.py`
- Create: `src/deeptalk_studio/episode_visual_preference_storage.py`
- Create: `config/episode-visual-default.json`
- Test: `tests/test_episode_visual_preference.py`

- [ ] Define `episode-visual-preference/1`, immutable digest, default balanced profile and resolver precedence.
- [ ] Add a deterministic Chinese parser for overall/material/motion/A-roll language and explicit “以后默认” persistence intent.
- [ ] Write failing tests for default behavior, episode isolation, persistent intent, preview precedence and unknown language.
- [ ] Implement and run the focused tests.

### Task 2: Post-alignment Visual Plan and coverage gates

**Files:**
- Create: `src/deeptalk_studio/post_alignment_visual_plan.py`
- Create: `src/deeptalk_studio/post_alignment_visual_plan_schema.py`
- Create: `src/deeptalk_studio/post_alignment_visual_plan_storage.py`
- Test: `tests/test_post_alignment_visual_plan.py`

- [ ] Define complete Beat audit and opportunity schemas, including A-roll/Material/Motion/Hybrid rationale and exact safe time projection provenance.
- [ ] Implement correspondence-based span projection without calling Alignment builder or changing any Alignment status.
- [ ] Implement Visual / Material / Motion coverage derivation; reject ungrounded, B011-dependent, unsafe or decorative opportunities.
- [ ] Test 18-Beat audit completeness, multiple opportunities, HIGH preferences, hybrid, B011 isolation, B018 tail and fail-closed timing.

### Task 3: Bind preference and plan into Production, placement and Bridge QA

**Files:**
- Modify: `src/deeptalk_studio/production_schema.py`
- Modify: `src/deeptalk_studio/production_planner.py`
- Modify: `src/deeptalk_studio/edit_bridge_schema.py`
- Modify: `src/deeptalk_studio/edit_bridge_planner.py`
- Modify: `src/deeptalk_studio/edit_bridge_qa.py`
- Test: `tests/test_visual_preference_production_integration.py`
- Test: `tests/test_visual_plan_bridge_qa.py`

- [ ] Add optional digest bindings with backward-compatible validation for legacy artifacts.
- [ ] Add a plan placement adapter that reuses only Material View-ready files and Production QA-ready Motion, then runs current duration/conflict logic.
- [ ] Revalidate plan/preference/coverage in canonical QA before Preview.
- [ ] Test tampering, wrong roots, unready sources, rebind safety and unchanged legacy behavior.

### Task 4: UX and natural-language preview revision

**Files:**
- Modify: `.agents/skills/prepare-materials/SKILL.md`
- Modify: `.agents/skills/produce-video-assets/SKILL.md`
- Modify: `.agents/skills/align-video/SKILL.md`
- Modify: `src/deeptalk_studio/edit_bridge_storage.py`
- Test: `tests/test_visual_preference_preview_revision.py`

- [ ] Add a non-blocking ordinary-language visual-choice prompt before planning and after Preview.
- [ ] Resolve visual feedback to a preference revision before an optional placement adjustment.
- [ ] Require each revision to create a new preference/plan/Bridge/Preview lineage and preserve current subtitles/Transcript.
- [ ] Test “动画再多一点”, “真实截图收一点”, “前半段丰富一点”, “结尾多留真人” and persistent intent separation.

### Task 5: Real-episode audit, Material and Motion completion

**Files:**
- Create Git-ignored immutable Material, capture, Visual Plan, Production and Motion artifacts under existing dated roots.
- Test: existing Material / capture / Production / renderer / bridge regression suites.

- [ ] Audit all 18 real beats using the approved Script, Research and existing Alignment.
- [ ] Reuse valid captures; acquire only additional focused official/public pages with actual-open provenance and capture registration.
- [ ] Build grounded original Visual Specs for the approved mechanism/timeline/comparison/diagram opportunities; run independent Material Review and Material Gate.
- [ ] Create a new Production revision, render only the selected renderer, validate Motion assets, Manifest and Production QA.

### Task 6: Real full preview and handoff

**Files:**
- Modify: `README.md`, `PRD.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md`, `HANDOFF.md`
- Test: full project suite and selected real-production regressions.

- [ ] Build the new Plan-driven Bridge and full 620-second Preview without re-transcription or overwriting prior output.
- [ ] Run canonical QA, ffprobe, SHA/binding verification, visual frame checks, compileall, `git diff --check` and credential-shaped secret scan.
- [ ] Update user-facing UX and handoff documentation, commit/push the development branch, and stop at Human Preview Gate.
# 2026-08-24 — Real-user visual presentation and Output-Truth completion

- [x] Map the existing typed `layout_mode` to a controlled renderer presentation mode; do not create a second editorial interpretation path.
- [x] Make `primary_visual` use the complete 1920×1080 canvas, keep `supporting_overlay` inside the existing subtitle-safe region, and define an explicit PIP A-roll inset.
- [x] Add regression coverage for the three controlled modes and for final-output evidence integrity.
- [x] Add a canonical blocking Output-Truth check for a formal Full Visual preview and persist real encoded frame evidence.
- [x] Render real-user `ALIGNED_PREVIEW-r0003.mp4`, mux the immutable Clean A-roll audio, probe it, and run canonical QA.
- [x] Preserve B011 as an unplaced warning and keep B018 as A-roll; do not alter content roots or create a release.
