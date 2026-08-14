# Real E2E Preflight Material Captures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let actual webpage/document captures from the already reviewed Material Package enter the production projection without rewriting the reviewed historical package or treating rights/reuse as a production gate.

**Architecture:** Keep Material r1/r2 immutable. Store a separate immutable capture manifest beside the runtime assets, bind it to the exact reviewed Material Package digest and its inspected source metadata, and let the production view replay package plus manifest. The pre-existing renderer and Edit Bridge then consume only the revalidated file record.

**Tech Stack:** Python 3.9+, standard-library JSON/SHA-256, unittest, existing static-capture boundary.

## Global Constraints

- Work only on `agent/audio-alignment-edit-bridge`; do not alter `main`, `v0.6.1`, tags or Releases.
- Do not modify approved Research, reviewed Script or reviewed Material Package history.
- Capture only existing inspected sources; do not bypass access controls or turn a web URL into a file.
- Rights/reuse remains historical metadata, not the production-file gate; provenance, binding, capture metadata, path, MIME, size and SHA remain strict.
- One real screenshot/image/document capture is sufficient for the first user E2E. Real video remains optional and requires an explicit clip range.
- Use no deterministic transcription provider for real user E2E.

---

### Task 1: Make capture manifests an immutable production input

**Files:**
- Create: `src/deeptalk_studio/material_capture_manifest.py`
- Test: `tests/test_material_capture_manifest.py`

**Interfaces:** `build_material_capture_manifest(package, records, created_at) -> dict`; `save_material_capture_manifest(manifest, asset_root) -> Path`; `load_material_capture_manifest(asset_root, package) -> dict`.

- [x] Write a failing test proving a capture record is bound to the exact reviewed package/material/source/capture metadata and rejects file or binding tampering.
- [x] Run the test and confirm it fails because the module does not exist.
- [x] Implement the smallest versioned, immutable JSON manifest and its replay validation.
- [x] Re-run the test until it passes.

### Task 2: Project validated captures without changing Material history

**Files:**
- Modify: `src/deeptalk_studio/material_bridge.py`
- Test: `tests/test_material_bridge.py`

**Interfaces:** `build_material_production_view(..., asset_root)` automatically loads the exact package capture manifest when present; a valid reference-only capture projects to `production_status=ready` while a missing manifest remains `missing_asset`.

- [x] Write a failing canonical r2 regression: save the reviewed package untouched, save a capture manifest, then require a ready real-image projection.
- [x] Run the regression and confirm it fails because the production view ignores the manifest.
- [x] Implement only manifest-based local-record substitution before the existing file/SHA/MIME checks.
- [x] Re-run the bridge and manifest tests until they pass.

### Task 3: Acquire current approved screenshots and prove readiness

**Files:**
- Runtime-only: `material_assets/MAT-c29080b0554d4c49959b58f5fcc3174d/captures/`
- Modify: `HANDOFF.md`, `CHANGELOG.md`

**Interfaces:** Existing `register_local_capture(...)` produces immutable PNG/JPEG/WebP records; the new manifest is saved only after opening and capturing the approved source page.

- [x] Open an existing approved official source through an available safe page-access path; if the page cannot be opened, record a missing asset rather than fabricate a capture.
- [x] Register at least one actual static capture with its source URL, source title, capture region/page, file MIME/size/SHA and Cue binding.
- [x] Run canonical material projection, capture-manifest integrity and targeted tests.
- [x] Record transcription and material Preflight state honestly in HANDOFF/CHANGELOG.

### Task 4: Validate, commit and push the Unreleased branch

**Files:** `HANDOFF.md`, `CHANGELOG.md`, affected source/tests.

- [x] Verify SDK installation/import without exposing a secret.
- [ ] Run targeted material tests, provider tests, existing production-session regression, diff check and secret scan.
- [ ] Commit scoped code/docs changes and push `agent/audio-alignment-edit-bridge`.
- [ ] Verify main/tag/Release remain unchanged and stop before any real user video.

## Self-review

- Reviewed Material history remains immutable and canonical replay still rejects hand-edited r2.
- A capture has a file-level SHA and immutable exact package binding before it can become ready.
- A missing or tampered capture remains fail-closed.
- This plan does not add a new product feature beyond the approved production-file preflight fix.
