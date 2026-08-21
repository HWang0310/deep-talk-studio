# Global Monotonic Alignment Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-Beat full-transcript fallback alignment with one deterministic global Script→Transcript correspondence, then project truthful local Beat and Cue evidence from that single ordered mapping.

**Architecture:** Reuse `sequence_alignment.align_sequences()` exactly once over all reviewed Script lexical tokens and all Timed Transcript lexical tokens. A projection layer derives each Beat's owned operations, local transcript interval, gaps and status; Cues consume the same global correspondence directly, so a parent Beat's unrelated review item cannot erase a safe anchor. The Timed Transcript remains the sole timing source and the existing Profile thresholds remain unchanged.

**Tech Stack:** Python 3.9+ standard library, existing deterministic dynamic-programming sequence alignment, unittest, existing immutable JSON artifacts and external real-user session cache.

**Spec:** `/Users/hwang/.codex/attachments/71997d4c-9c54-43df-9681-31916d7a3e0a/pasted-text.txt`

## Global Constraints

- Do not alter the reviewed Script, approved Research, reviewed Material Package, raw Timed Transcript, raw timings, ASR provider, subtitle implementation, thresholds, canonical QA contract, canonical `main`, `v0.6.1`, tags or Releases.
- One full Script and full Timed Transcript alignment per Script Alignment artifact; no Beat may independently scan the full Transcript.
- Preserve the existing operation vocabulary: `primary_match`, `numeric_match`, `substitution`, `script_deletion`, `transcript_insertion`.
- Preserve lexical and timestamp truth: no text rewriting, timestamp interpolation, fake timing, LLM correction, forced aligner or secondary ASR.
- An actual ambiguous anchor, discontinuous local mapping, boundary risk, or unresolved large deletion remains fail-closed.
- Keep all real user media/transcripts/previews external and gitignored. Work on `agent/audio-alignment-edit-bridge` from `0103d4b5881425aa5f6b9013ef8ad9757a7d60cc`.

---

### Task 1: Define global correspondence and local projection regressions

**Files:**
- Create: `tests/test_global_alignment_projection.py`
- Modify: `tests/alignment_fixtures.py`
- Modify: `tests/test_cue_timeline.py`

**Interfaces:**
- Fixture provides four ordered Beats and one ordered timed Transcript containing a substitution, a one-unit deletion, a local filler insertion, one long local omission and a post-Script trailing ad-lib.
- `build_script_alignment(...)` will expose one whole-script `operations` sequence and project its `beat_timeline` / `cue_timeline` records from it.

- [ ] **Step 1: Write failing global-localization tests.**

```python
def test_global_projection_keeps_insertions_local_and_preserves_trailing_tail():
    artifact = build_global_fixture()
    beats = {beat["beat_id"]: beat for beat in artifact["beat_timeline"]}
    self.assertEqual(len(artifact["global_mapping"]["script_tokens"]), 16)
    self.assertNotIn("ad_lib_transcript_span", beats["B001"]["deviation_codes"])
    self.assertIn("ad_lib_transcript_span", beats["B002"]["deviation_codes"])
    self.assertIn("trailing_ad_lib_transcript_span", [gap["gap_type"] for gap in artifact["gaps"]])
    self.assertEqual(beats["B004"]["alignment_status"], "aligned")
```

- [ ] **Step 2: Run the focused new tests and confirm they fail because `global_mapping` and local ownership do not exist.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_global_alignment_projection -v`

Expected: failures identifying missing global projection data or old full-transcript fallback behavior.

### Task 2: Implement one global mapping plus Beat-local ownership

**Files:**
- Modify: `src/deeptalk_studio/alignment_builder.py`
- Modify: `src/deeptalk_studio/alignment_schema.py`
- Modify: `src/deeptalk_studio/alignment_storage.py`
- Test: `tests/test_global_alignment_projection.py`
- Test: `tests/test_alignment_builder.py`
- Test: `tests/test_alignment_validation.py`

**Interfaces:**
- `_global_script_tokens(beats, profile) -> tuple[NormalizedToken, ...]` offsets each Beat's reversible character spans into Script-global coordinates without changing lexical content.
- `_build_global_mapping(script_tokens, transcript_tokens, profile) -> Mapping[str, Any]` runs `align_sequences` once, then records every Script token's operation and transcript index/time plus every transcript insertion's left/right Script boundary and ownership class.
- `_project_beat_records(...) -> list[dict]` accepts the global mapping and never calls `align_sequences`.

- [ ] **Step 1: Add a minimal global projection implementation.**

Build one complete Script stream in exact Beat order using `dataclasses.replace(token, original_start_char=..., original_end_char=...)`. Reuse the existing deterministic trace. Build explicit Script-index correspondence records for exact/numeric/substitution/deletion and insertion records for all transcript-only operations. Classify insertion ownership only by neighboring globally mapped Script indices: leading, a Beat-local interval, a Beat boundary, or a trailing tail.

For a Beat, select only operations with Script indices inside its global range plus insertions deterministically owned by that range or its explicit boundary. Compute coverage from primary/numeric pairs; compute substitution-aware similarity from primary/numeric/substitution pairs. Retain the accepted/review floors. A Beat becomes `aligned/high` when its local mapping is ordered, accepts the unchanged floors, has token/word timestamps, no boundary risk and no blocking local ambiguity or long structural omission; ordinary substitutions, small deletions and local fillers remain diagnostics rather than automatic failure.

- [ ] **Step 2: Expand immutable schema and re-derivation safety.**

Upgrade only Script Alignment to `script-alignment/2`. Add versioned `global_mapping` evidence containing non-secret normalized Script/Transcript index references, operation linkage, transcript unit IDs and only existing provider timing values. Add `trailing_ad_lib_transcript_span` to accepted gap types. Keep all public Beat/Cue fields compatible with downstream placement and QA. Update the Markdown reading view to describe global projection and trailing ad-lib where present.

- [ ] **Step 3: Run Task 1/2 focused tests, existing Alignment builder/validator tests, and verify re-derivation rejects tampering.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_global_alignment_projection tests.test_alignment_builder tests.test_alignment_validation -v`

Expected: all pass, and a recomputed digest cannot bless altered correspondence, timing or status.

### Task 3: Project Cue anchors independently and preserve fail-closed ambiguity

**Files:**
- Modify: `src/deeptalk_studio/alignment_builder.py`
- Modify: `src/deeptalk_studio/alignment_schema.py`
- Modify: `tests/test_cue_timeline.py`
- Modify: `tests/test_global_alignment_projection.py`

**Interfaces:**
- `_cue_records(...)` takes global mapping rather than Beat-local fallback pairs.
- Cue anchor start/end are selected from direct mapped anchor/semantic Script token indices; emitted times are exact existing transcript unit times only.

- [ ] **Step 1: Write/complete failing Cue tests for exact, substitution, duplicate and deletion cases.**

```python
def test_safe_anchor_is_aligned_when_parent_has_unrelated_long_omission():
    cue = build_fixture_with_parent_omission_and_safe_late_anchor()["cue_timeline"][0]
    self.assertEqual(cue["placement_status"], "aligned")
    self.assertEqual(cue["confidence"], "high")
```

```python
def test_anchor_crossing_long_deletion_remains_unplaced():
    cue = build_fixture_with_anchor_deletion()["cue_timeline"][0]
    self.assertEqual(cue["placement_status"], "unplaced")
    self.assertIn("semantic_span_unmatched", cue["deviation_codes"])
```

- [ ] **Step 2: Implement global Cue projection.**

Resolve an anchor's Script-global token range once. Permit a nonempty, unique, monotonic, locally continuous correspondence containing exact/numeric/substitution evidence when it meets existing review/accepted floors for the semantic span and has no boundary risk. A duplicated anchor remains `unplaced`; a deletion crossing the anchor/semantic range remains `unplaced`; segment timestamps remain `coarse`; affected boundary risk remains `needs_review`. Never downgrade a safe Cue merely because its parent Beat has an unrelated review diagnostic.

- [ ] **Step 3: Run Cue and Edit Bridge regressions.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cue_timeline tests.test_alignment_placement_eval tests.test_audio_alignment_integrated_e2e -v`

Expected: existing exact Cue semantics and placement contracts remain valid, new global Cue safety cases pass.

### Task 4: Replay the immutable real-user transcript and resume downstream only when safe

**Files:**
- Create externally only: a new alignment ID/revision under the existing real-user session `alignment/`
- Create externally only when any Cue is ready: a new immutable Bridge/Preview/Manifest/QA revision under the existing real-user session
- Modify: `evaluations/` only if a reusable, non-private replay helper is necessary

**Interfaces:**
- Reuse Transcript `TRANSCRIPT-e3e949a79e744a3d90aa8a02b9366742`, original Mapping, Media, approved Script, reviewed Material Package, approved Motion, and existing Material view.
- Do not invoke Whisper or modify the original r0001 artifacts.

- [ ] **Step 1: Build and validate the new alignment from the existing transcript.**

Use canonical loaders and `build_script_alignment` with a new immutable alignment ID and revision. Validate with `validate_script_alignment`, save via `save_script_alignment`, and capture before/after Beat/Cue/gap distributions. Verify Script, Transcript, Mapping, Material and Production roots remain bound to existing reviewed identities.

- [ ] **Step 2: If at least one placement is ready, derive a new Bridge and full-length Preview.**

Reuse only approved Material and Motion assets. Build visual placements, derive placement timing, render a new full 620-second-class preview with the current bound Subtitle Artifact, mux original Clean A-roll audio, create an immutable new Bridge/Manifest/QA output and run canonical QA. Do not stage reference-only sources, guess uncertain ranges or place material for B011/B018 without a safe Cue.

- [ ] **Step 3: Inspect actual output and state every Gate from evidence.**

Record full preview duration, SHA-256, renderer runtime, ready image/Motion placement counts, warnings and blocking count. If no Cue is safe or canonical QA blocks, stop before the Human Preview Gate and report evidence rather than forcing a preview.

### Task 5: Document, verify, commit and push without Release

**Files:**
- Modify: `docs/superpowers/plans/2026-08-21-global-monotonic-alignment-projection.md`
- Modify: `README.md`
- Modify: `PRD.md`
- Modify: `ROADMAP.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`

- [ ] **Step 1: Update documentation with `script-alignment/2` global mapping and actual real-user Gate outcomes.**

Record B011 only as unresolved textual evidence requiring audio confirmation if still present; record B018 as real trailing ad-lib outside the Script rather than as Script content. Keep ASR runtime/RTF persistence as a non-blocking observability gap.

- [ ] **Step 2: Run required verification.**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 -m compileall -q src tests`, `git diff --check`, and a credential-shaped secret scan.

Expected: all non-skipped tests pass; compileall and diff check exit zero; secret scan returns no credential-shaped values.

- [ ] **Step 3: Commit and push scoped source/tests/docs changes.**

Commit message: `fix: project alignment from global monotonic mapping`; push only `agent/audio-alignment-edit-bridge`.

- [ ] **Step 4: Verify canonical history is unchanged.**

Confirm branch comparability with canonical `main`; `main` stays `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`; `v0.6.1` remains attached to that canonical history; no tag or GitHub Release is created.

## Plan Self-Review

- Global mapping, insertion ownership, local Beat metrics, Cue decoupling, B011/B018 treatment, lexical/timestamp invariants, pre-existing regressions, real replay and downstream resume are each covered by Tasks 1–4.
- No task lowers Profile floors, changes raw transcript evidence, uses a second ASR, modifies reviewed roots, or broadens V1 scope.
- The interface names in later tasks are defined in Task 2/3; any real-user output remains external and immutable.

## Execution Result

- Tasks 1–3 completed with `tests/test_global_alignment_projection.py`: six deterministic regressions cover one global
  pass, local insertion ownership, trailing tail, input immutability, a safe Cue under an unrelated long omission, an
  unsafe deletion-crossing Cue, and an 18/20 substitution Cue that receives only real Transcript timing.
- Task 4 completed through immutable alignment replay. The existing real Transcript produced 17 aligned Beats, B011 as
  the sole needs-review Beat, two safe Cues and one preserved trailing ad-lib. No downstream Bridge/Preview was created:
  none of the safe Cues has an eligible existing real image or Motion asset, so a render would add no approved visual.
- Task 5 completed with docs updates and full regression. Commit/push fields are completed only after the final Git
  verification recorded in `HANDOFF.md`.
