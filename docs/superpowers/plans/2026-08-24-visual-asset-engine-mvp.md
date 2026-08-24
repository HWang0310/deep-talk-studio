# Visual Asset Engine MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe, deterministic V1 foundation that turns approved content and real A-roll alignment into a reviewed visual plan, five fixture assets at most, and an editor-friendly asset pack/Edit Map.

**Architecture:** Add a versioned Visual Director plan and Motion Spec family above the existing Script/Research/Material/Alignment roots. Reuse the current production binding and QA concepts while adding a small shared SVG/Remotion primitive payload for three MG grammars, path drawing, and controlled metaphor. Package only QA-ready assets into a machine manifest plus human Markdown/CSV Edit Map.

**Tech Stack:** Python 3.9 standard library, existing immutable JSON artifact pattern and unittest suite, existing Remotion template/FFmpeg/ffprobe, CSV/Markdown derived outputs.

**Spec:** `docs/superpowers/specs/2026-08-24-visual-asset-engine-mvp-design.md`

## Global Constraints

- Work only on `agent/audio-alignment-edit-bridge`; never merge main, change `v0.6.1`, tag, or release.
- A-roll is the default. No safe/valuable reason means `KEEP_A_ROLL`.
- All candidate time ranges originate from the existing approved Alignment; LLM/content input cannot supply a usable start/end time.
- All displayed factual text, names, organizations, dates and numbers require an existing Fact/Display Text binding.
- The core path has no OpenAI/Anthropic/Google/RunningHub or image-generation API requirement.
- Advanced Motion requires a separate human approval state before it can render.
- Fixture success is engineering proof only; it is not real-episode product validation.
- Do not implement non-approved grammars, NLE project files, auto full-video editing, video models, complex character animation, 2.5D, 3D, or publishing.

---

### Task 1: Preserve approved design and define machine contracts

**Files:**
- Create: `src/deeptalk_studio/visual_asset_schema.py`
- Create: `src/deeptalk_studio/visual_director.py`
- Create: `src/deeptalk_studio/visual_asset_storage.py`
- Create: `tests/test_visual_director.py`
- Modify: `CHANGELOG.md`, `HANDOFF.md`

**Interfaces:**
- Consumes: reviewed Script, Research, Material view, Alignment, Episode preference.
- Produces: `build_visual_director_plan(...) -> dict`, `validate_visual_director_plan(...) -> None`, immutable save/load functions.

- [ ] **Step 1: Write failing contract tests**

```python
def test_director_projects_time_only_from_alignment():
    plan = build_visual_director_plan(roots(), [proposal("KEEP_A_ROLL")])
    assert plan["opportunities"][0]["source_time_range"] == {"start_seconds": "12.0", "end_seconds": "18.0"}

def test_director_rejects_content_supplied_time():
    with self.assertRaises(VisualDirectorError):
        build_visual_director_plan(roots(), [proposal("MG_MOTION", start_seconds="1")])
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_director -v`

Expected: import/attribute failure because the Visual Director module does not exist.

- [ ] **Step 3: Implement minimum contracts**

```python
DECISIONS = {"KEEP_A_ROLL", "REAL_MATERIAL", "MG_MOTION", "ADVANCED_MOTION"}
def build_visual_director_plan(roots, proposals, *, plan_id, created_at, revision=1, previous_revision=0):
    # project an approved cue/alignment span; reject proposal-supplied clock values
    # compute risk and review requirement deterministically; digest the immutable artifact
    return plan
```

Add canonical root/digest replay, sorted non-overlap validation, default `KEEP_A_ROLL`, immutable storage and revision linkage.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_director -v`

Expected: all new Director contract, revision and default/fail-closed tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-08-24-visual-asset-engine-mvp-design.md docs/superpowers/plans/2026-08-24-visual-asset-engine-mvp.md CHANGELOG.md HANDOFF.md src/deeptalk_studio/visual_asset_schema.py src/deeptalk_studio/visual_director.py src/deeptalk_studio/visual_asset_storage.py tests/test_visual_director.py
git commit -m "feat: add visual director contracts"
```

### Task 2: Add MG/Advanced specs, bindings, review and fallback gates

**Files:**
- Create: `src/deeptalk_studio/motion_spec.py`
- Create: `tests/test_motion_spec.py`
- Modify: `src/deeptalk_studio/visual_asset_schema.py`

**Interfaces:**
- Consumes: approved Visual Director opportunity and canonical Fact/Display Text bindings.
- Produces: `build_mg_motion_spec(...)`, `build_advanced_motion_spec(...)`, `approve_advanced_motion_spec(...)`, `derive_fallback(...)`.

- [ ] **Step 1: Write failing gate tests**

```python
def test_advanced_spec_cannot_render_before_human_approval():
    spec = build_advanced_motion_spec(approved_opportunity(), metaphor_content())
    with self.assertRaises(MotionSpecError):
        assert_renderable_motion_spec(spec)

def test_unbound_numeric_display_text_is_rejected():
    with self.assertRaises(MotionSpecError):
        build_mg_motion_spec(approved_opportunity(), numeric_unbound_payload())
```

- [ ] **Step 2: Run RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_motion_spec -v`

Expected: missing module failure.

- [ ] **Step 3: Implement minimum schema and policy**

Support only `timeline`, `causal_chain`, `comparison_mechanism`, `svg_path_drawing`, and `controlled_conceptual_metaphor`; enforce capacities, provenance, fact/display binding, local alignment range binding, separate Advanced approval, and exact fallback order `MG_MOTION → REAL_MATERIAL → KEEP_A_ROLL`.

- [ ] **Step 4: Run GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests.test_motion_spec -v`

Expected: all binding, Review, capacity and fallback tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/motion_spec.py src/deeptalk_studio/visual_asset_schema.py tests/test_motion_spec.py
git commit -m "feat: enforce visual motion spec gates"
```

### Task 3: Implement shared deterministic primitives and MG/Advanced renderer payloads

**Files:**
- Create: `src/deeptalk_studio/visual_motion_primitives.py`
- Create: `src/deeptalk_studio/visual_asset_renderer.py`
- Create: `renderer_templates/visual_asset_remotion/` project files
- Create: `tests/test_visual_motion_primitives.py`
- Create: `tests/test_visual_asset_renderer.py`

**Interfaces:**
- Consumes: only renderable MG/Advanced specs.
- Produces: deterministic shared primitive payload and MP4/manifest candidate output.

- [ ] **Step 1: Write failing primitive and renderer tests**

```python
def test_path_payload_reveals_nodes_in_semantic_order():
    payload = compile_visual_motion(path_spec())
    assert [node["reveal_order"] for node in payload["nodes"]] == [1, 2, 3]
    assert payload["path"]["growth"] == "directional"

def test_renderer_refuses_unapproved_advanced_spec():
    with self.assertRaises(VisualAssetRenderError):
        render_visual_asset(unapproved_advanced_spec(), output_root())
```

- [ ] **Step 2: Run RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_motion_primitives tests.test_visual_asset_renderer -v`

Expected: imports fail before implementation.

- [ ] **Step 3: Implement minimal common primitives and renderer**

Use shared `text`, `shape`, `line`, `arrow`, `node`, `card`, `path`, `mask`, `reveal`, `chart`, `group`, `transition` payload primitives. Add only five compiled scene families: timeline, causal chain, comparison/mechanism, SVG/path, controlled conceptual metaphor. Each must use 1920×1080, bound duration, frame-driven reveal, no later-element exposure, and Neutral Editorial style.

- [ ] **Step 4: Run focused GREEN and renderer checks**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_motion_primitives tests.test_visual_asset_renderer -v && npm --prefix renderer_templates/visual_asset_remotion run lint && npm --prefix renderer_templates/visual_asset_remotion run typecheck`

Expected: tests, lint and TypeScript checks pass.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/visual_motion_primitives.py src/deeptalk_studio/visual_asset_renderer.py renderer_templates/visual_asset_remotion tests/test_visual_motion_primitives.py tests/test_visual_asset_renderer.py
git commit -m "feat: render deterministic visual asset primitives"
```

### Task 4: Create Asset Pack and user-facing Edit Map

**Files:**
- Create: `src/deeptalk_studio/visual_asset_pack.py`
- Create: `src/deeptalk_studio/edit_map.py`
- Create: `tests/test_visual_asset_pack.py`
- Create: `tests/test_edit_map.py`

**Interfaces:**
- Consumes: QA-ready visual asset records and approved Director/Motion roots.
- Produces: `visual-asset-manifest/1`, fixed episode folders, `edit-map/1.json`, `剪辑表.md`, `剪辑表.csv`.

- [ ] **Step 1: Write failing pack/map tests**

```python
def test_failed_asset_is_not_exported_to_edit_map():
    outputs = build_edit_map(manifest_with_failed_asset(), episode_root())
    assert "失败素材.mp4" not in outputs.markdown

def test_user_edit_map_never_exposes_machine_ids_or_sha():
    outputs = build_edit_map(ready_manifest(), episode_root())
    assert "SHA" not in outputs.markdown
    assert "asset_id" not in outputs.csv_text
```

- [ ] **Step 2: Run RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_asset_pack tests.test_edit_map -v`

Expected: module imports fail.

- [ ] **Step 3: Implement packing and derived views**

Create only user-readable folders `06_真实素材` through `09_剪辑表` plus `_DeepTalk记录`; write machine manifest/JSON only under the technical directory. Export readable filenames, exact A-roll timecodes, use/why/fallback prose, and Markdown/CSV. Reject absent/failed/SHA-mismatched assets.

- [ ] **Step 4: Run GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_asset_pack tests.test_edit_map -v`

Expected: all pack integrity and user-view privacy tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/visual_asset_pack.py src/deeptalk_studio/edit_map.py tests/test_visual_asset_pack.py tests/test_edit_map.py
git commit -m "feat: export visual asset packs and edit maps"
```

### Task 5: Build one safe fixture workflow and verify five real MP4 outputs

**Files:**
- Create: `evaluations/visual_asset_engine/fixture_episode.py`
- Create: `evaluations/visual_asset_engine/run_fixture_eval.py`
- Create: `tests/test_visual_asset_engine_fixture.py`
- Modify: `README.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md`, `HANDOFF.md`

**Interfaces:**
- Consumes: deterministic synthetic alignment and bound fixture facts.
- Produces: one timeline, causal chain, comparison/mechanism, path and controlled-metaphor MP4; QA-ready manifest and human Edit Map.

- [ ] **Step 1: Write failing end-to-end fixture test**

```python
def test_fixture_exports_five_bound_assets_and_edit_map(tmp_path):
    result = run_fixture_episode(tmp_path)
    assert result.manifest["asset_count"] == 5
    assert result.edit_map_markdown.exists()
    assert all(asset["qa_status"] == "ready" for asset in result.manifest["assets"])
```

- [ ] **Step 2: Run RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_asset_engine_fixture -v`

Expected: missing fixture runner failure.

- [ ] **Step 3: Implement fixture workflow and QA**

Use synthetic but schema-valid reviewed roots and fixed local SVG/icon inputs. Create no real topic research or user episode asset. Render five independent MP4s; verify ffprobe dimensions/fps/duration, SHA/binding, manifest integrity and Edit Map consistency.

- [ ] **Step 4: Run focused GREEN plus actual fixture eval**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_asset_engine_fixture -v && PYTHONPATH=src:. python3 evaluations/visual_asset_engine/run_fixture_eval.py --output /tmp/deeptalk-visual-asset-fixture`

Expected: five MP4s, manifest, Markdown and CSV exist; fixture report marks engineering-only success.

- [ ] **Step 5: Run full verification, update docs, commit**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Then update only factual documentation/HANDOFF/CHANGELOG and commit all remaining changes:

```bash
git add README.md ROADMAP.md AGENTS.md CHANGELOG.md HANDOFF.md evaluations/visual_asset_engine tests/test_visual_asset_engine_fixture.py
git commit -m "feat: validate visual asset engine fixture workflow"
```
