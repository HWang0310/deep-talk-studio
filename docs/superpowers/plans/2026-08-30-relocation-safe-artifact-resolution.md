# Relocation-Safe Artifact Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve immutable historical artifact paths while safely resolving their current runtime files after a canonical workspace relocation.

**Architecture:** A strict Core resolver maps consumer-derived artifact-relative identities from explicitly trusted historical roots into one configured canonical repository root. Historical JSON and digests remain untouched; Motion, Material, Capture, Edit Bridge, and production staging consume separate verified runtime observations.

**Tech Stack:** Python 3.9+ standard library, immutable JSON artifacts, SHA-256, `pathlib`, `unittest`, existing DeepTalk Core validators.

**Spec:** `docs/superpowers/specs/2026-08-30-relocation-safe-artifact-resolution-design.md`

## Global Constraints

- Do not rewrite or regenerate historical Production, Motion, Material, Capture, Script, or Research JSON.
- Do not perform arbitrary absolute-path prefix replacement.
- Reject traversal, unknown roots, identity mismatches, symlink escape, missing files, size mismatch, SHA mismatch, and artifact tampering.
- Keep MG plugin, Illustrated, Hand-drawn, `main`, tags, and releases untouched.
- Do not commit private Episode data or user-specific runtime configuration.

---

### Task 1: Core runtime resolver and strict local configuration

**Files:**
- Create: `src/deeptalk_studio/artifact_runtime.py`
- Create: `tests/test_artifact_runtime.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `ArtifactRuntimeConfig`, `RuntimeArtifactResolver`, `RuntimeArtifactObservation`, `load_artifact_runtime_config()`, and lineage-specific resolution methods.
- Consumes: an explicit canonical root, strict local JSON configuration, historical recorded path, consumer-derived identity, expected byte size, and SHA-256.

- [ ] **Step 1: Write failing resolver tests**

  Add sanitized temp-root cases for successful relocation and every required negative condition. Preserve the historical JSON bytes before and after successful resolution.

- [ ] **Step 2: Run the resolver tests and verify RED**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_artifact_runtime -v`

  Expected: import/API failures because the resolver does not exist.

- [ ] **Step 3: Implement the minimal resolver**

  Validate exact config fields and absolute roots. Derive exact Motion/generated/capture/acquired relative identities, reject unsafe paths and symlink components, then verify the canonical file's existence, size, and SHA-256.

- [ ] **Step 4: Run the resolver tests and verify GREEN**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_artifact_runtime -v`

- [ ] **Step 5: Refactor without changing behavior**

  Keep path classification, canonical containment, identity derivation, and file verification as small independent helpers; rerun the same tests.

### Task 2: Motion Manifest and current-production selection

**Files:**
- Modify: `src/deeptalk_studio/production_qa.py`
- Modify: `src/deeptalk_studio/edit_bridge_session.py`
- Modify: `src/deeptalk_studio/edit_bridge_planner.py`
- Modify: `src/deeptalk_studio/edit_bridge_qa.py`
- Modify: `tests/test_production_qa.py`
- Modify: `tests/test_real_edit_bridge_session.py`
- Modify: `tests/integrated_upstream_factory.py`

**Interfaces:**
- Consumes: optional `RuntimeArtifactResolver` in Motion validation, placement, and canonical QA.
- Produces: exact explicit-current selection when configured; deterministic artifact-field fallback otherwise.

- [ ] **Step 1: Write failing Motion relocation and sanitized current-session tests**

  Cover historical Motion Manifest bytes/digest preservation, explicit current ID independent of mtime, and exact report/script/material/production bindings after a temp-root move.

- [ ] **Step 2: Run focused tests and verify RED**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_production_qa tests.test_real_edit_bridge_session -v`

- [ ] **Step 3: Thread the resolver through Motion validation and Edit Bridge**

  Return verified runtime observations from Motion validation and use only their canonical paths in placements. Pass the same resolver into canonical QA revalidation.

- [ ] **Step 4: Replace mtime current selection**

  Select `current_production_id` exactly when configured. Otherwise sort only by artifact-owned created/generated time, revision, identity, and lexical path.

- [ ] **Step 5: Run focused tests and verify GREEN**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_production_qa tests.test_real_edit_bridge_session -v`

### Task 3: Material Package, Capture, and production staging

**Files:**
- Modify: `src/deeptalk_studio/material_capture_manifest.py`
- Modify: `src/deeptalk_studio/material_bridge.py`
- Modify: `src/deeptalk_studio/production_validation.py`
- Modify: `src/deeptalk_studio/production_planner.py`
- Modify: `src/deeptalk_studio/production_renderers/base.py`
- Modify: `src/deeptalk_studio/production_renderers/remotion.py`
- Modify: `src/deeptalk_studio/production_renderers/hyperframes.py`
- Modify: `src/deeptalk_studio/production_workflow.py`
- Modify: `tests/test_material_capture_manifest.py`
- Modify: `tests/test_material_bridge.py`
- Modify: `tests/test_production_validation.py`
- Modify: `tests/test_production_workflow.py`

**Interfaces:**
- Consumes: the same optional resolver for capture replay, material production views, plan validation, and renderer staging.
- Produces: ephemeral runtime paths with separately retained recorded paths; historical Material and Capture artifacts remain byte-identical.

- [ ] **Step 1: Write failing Material/Capture relocation tests**

  Move sanitized captured and generated files from a trusted historical root into the canonical root, delete the old root, and assert successful consumer replay without changing package/capture bytes or digests.

- [ ] **Step 2: Run focused tests and verify RED**

  Run: `PYTHONPATH=src python3 -m unittest tests.test_material_capture_manifest tests.test_material_bridge tests.test_production_validation tests.test_production_workflow -v`

- [ ] **Step 3: Implement resolver-backed Material consumption**

  Keep the historical loader normalized against historical values. Build runtime views and staging paths only from verified resolver observations; preserve existing MIME, eligibility, and review gates.

- [ ] **Step 4: Run focused tests and verify GREEN**

  Run the same command and confirm all cases pass.

### Task 4: Canonical docs and current local recovery evidence

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PRODUCTION_CONTRACT.md`
- Modify: `docs/MATERIAL_CONTRACT.md`
- Modify: `docs/EDIT_BRIDGE_CONTRACT.md`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Documents: immutable history versus runtime observation, configuration, containment/security, explicit-current behavior, deterministic fallback limitation, and unreleased status.

- [ ] **Step 1: Create ignored local runtime configuration**

  Configure this machine's canonical root, trusted historical root, and current production ID without committing the file.

- [ ] **Step 2: Replay the current production chain locally**

  Resolve Motion, Material Package, and Capture records; verify all current canonical files by size/SHA and record only de-contented evidence.

- [ ] **Step 3: Update canonical documentation**

  State that relocation never rewrites historical evidence and document the exact runtime/security/current-selection semantics and limitation.

### Task 5: Final verification, commit, push, and remote equality

**Files:** all files changed above.

- [ ] **Step 1: Run focused relocation regressions**

  Run all Task 1–3 test modules with `PYTHONPATH=src python3 -m unittest ... -v`.

- [ ] **Step 2: Run the complete Core suite**

  Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

- [ ] **Step 3: Run repository validation**

  Run the canonical sample/validation commands, renderer lint/typecheck, `python3 -m compileall -q src tests`, and `git diff --check`.

- [ ] **Step 4: Audit scope and history preservation**

  Confirm no ignored production artifact, Episode media, local config, plugin runner, Illustrated, Hand-drawn, release, tag, or `main` change is staged. Compare protected local historical artifact checksums captured before implementation.

- [ ] **Step 5: Commit and push the review branch**

  Commit only reviewed source/tests/docs changes, push `agent/relocation-safe-artifact-resolution`, fetch the exact remote ref, and verify local HEAD equals remote HEAD with a clean working tree.
