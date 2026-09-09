# Asset Pack + Edit Map Production UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the canonical V1 production outcome a QA-ready Asset Pack and human-editable Edit Map derived only from one accepted Clean A-roll, while retaining the historic full-preview renderer as a compatibility/QA adapter.

**Architecture:** Extend the existing alignment, Visual Director, Motion Spec, Asset Manifest, and Edit Bridge contracts instead of introducing a second timeline or renderer. A new production-facing package builder consumes accepted Clean A-roll lineage, alignment-derived semantic spans, and only QA-ready assets; it writes the human Markdown/CSV and machine JSON Edit Map. The existing Remotion full-preview remains callable only as a non-default compatibility preview and never edits the source A-roll.

**Tech Stack:** Python 3 standard library, existing DeepTalk artifact schemas and validators, local whisper.cpp/large-v3 provider, FFmpeg/ffprobe, existing local Remotion renderer.

**Spec:** User-provided product contract: `/Users/hwang/.codex/attachments/0642fb98-4f31-4303-9a7f-4073f6f4dc61/pasted-text.txt`; related baseline: `docs/superpowers/specs/2026-08-24-visual-asset-engine-mvp-design.md`.

## Global Constraints

- V1 default product UX is `Final Clean A-roll → ASR → global monotonic alignment → semantic timeline → Visual Director → QA-ready assets → Asset Pack + Edit Map → human NLE editing`.
- DeepTalk must never select takes, crop/re-cut/delete any A-roll portion, choose the user’s NLE timeline, make a final A-roll edit, or publish.
- Formal asset timing must only come from accepted Clean A-roll → Timed Transcript → Script Alignment. Estimated script timing, draft timing, and fixtures are forbidden.
- Facts remain bound to approved Research / Reviewed Script; transcript disagreement on high-risk facts must produce `FACT_CONFLICT` and must not generate a wrong display asset.
- The only normal decisions are `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, and `ADVANCED_MOTION`; `KEEP_A_ROLL` is the default. Advanced Motion requires a separate review; ordinary safe KEEP/REAL/MG decisions do not require per-row user approval.
- Every non-KEEP Edit Map row must bind a real existing `READY` asset with QA evidence. Failure falls back `ADVANCED → MG → REAL → KEEP_A_ROLL`; no broken map rows.
- Existing renderer/production bridge stays as a compatibility/preview/individual-asset/QA route, not the default final-product output.
- Never modify reviewed Script, approved Research, reviewed Material Package, historical production outputs, main, v0.6.1 tag, or GitHub Release. Episode content and output stay local/gitignored.
- Use TDD: each production behavior begins with an independently failing unittest and an observed expected failure before implementation.

---

### Task 1: Lock the Clean A-roll acceptance boundary

**Files:**
- Create: `src/deeptalk_studio/clean_aroll_gate.py`
- Create: `tests/test_clean_aroll_gate.py`
- Modify: `src/deeptalk_studio/edit_bridge_session.py`
- Modify: `.agents/skills/align-video/SKILL.md`

**Interfaces:**
- Produces `CleanARollGateResult` with `status` (`accepted` / `needs_manual_cleanup`), source identity, detected blocking patterns, and a plain-language next action.
- `require_clean_aroll(media, transcript=None)` must return only an accepted result or raise `CleanARollGateError`; it must never emit a cut list, take ranking, or rewritten media.
- `run_real_edit_bridge_session` must invoke this gate before any formal production package/Edit Map output.

- [ ] **Step 1: Write failing acceptance tests**

```python
def test_multiple_complete_take_markers_require_manual_cleanup():
    result = inspect_clean_aroll(media_fixture(), transcript_with_two_complete_take_markers())
    self.assertEqual(result.status, "needs_manual_cleanup")
    self.assertIn("人工清理", result.user_message)

def test_natural_pause_and_adlib_are_accepted_without_cut_instruction():
    result = inspect_clean_aroll(media_fixture(), transcript_with_pause_and_adlib())
    self.assertEqual(result.status, "accepted")
    self.assertNotIn("删除", result.user_message)

def test_gate_never_returns_selection_or_edit_instructions():
    result = inspect_clean_aroll(media_fixture(), transcript_with_two_complete_take_markers())
    self.assertFalse(any(key in result.to_dict() for key in ("keep_take", "cut_ranges", "crop", "selection")))
```

- [ ] **Step 2: Run the focused test file and verify expected RED failures**

Run: `PYTHONPATH=src python3 -m unittest tests.test_clean_aroll_gate -v`

Expected: Import failure for `deeptalk_studio.clean_aroll_gate`.

- [ ] **Step 3: Implement the minimal immutable Clean A-roll gate**

Implement a deterministic gate that treats more than one complete script-run marker or explicit full retake marker as `needs_manual_cleanup`, allows normal pauses/ad-libs, and returns only the single ordinary manual-cleanup message. Call it after the real Transcript exists if transcript evidence is needed, but before semantic planning, asset generation, Asset Pack, or Edit Map. Do not alter media bytes or construct any selection proposal.

- [ ] **Step 4: Run focused tests and legacy real-session tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_clean_aroll_gate tests.test_real_edit_bridge_session -v`

Expected: PASS.

- [ ] **Step 5: Commit the isolated gate**

```bash
git add src/deeptalk_studio/clean_aroll_gate.py src/deeptalk_studio/edit_bridge_session.py tests/test_clean_aroll_gate.py .agents/skills/align-video/SKILL.md
git commit -m "feat: gate production on final clean a-roll"
```

### Task 2: Make Visual Director and Motion timing explicitly real-span only

**Files:**
- Modify: `src/deeptalk_studio/visual_director.py`
- Modify: `src/deeptalk_studio/motion_spec.py`
- Create: `tests/test_asset_pack_timing_contract.py`
- Modify: `tests/test_visual_director.py`
- Modify: `tests/test_motion_spec.py`

**Interfaces:**
- `build_visual_director_plan` accepts only alignment-derived ranges whose provenance is `actual_aroll_alignment`; no estimated range may reach an opportunity.
- `build_motion_spec` includes `semantic_beats` whose absolute times are within the director’s real source range and a deterministic `relative_timing` derived from that range.
- `recompute_motion_timing(spec, source_time_range)` recalculates each primitive’s relative time from absolute semantic beats; it never stretches a fixed animation clock.

- [ ] **Step 1: Write failing real-timing tests**

```python
def test_director_rejects_estimated_script_timing():
    with self.assertRaisesRegex(VisualDirectorError, "真实 A-roll"):
        build_visual_director_plan(estimated_roots(), [proposal() ], plan_id="VD-1", created_at=NOW)

def test_motion_semantic_beats_must_stay_inside_actual_span():
    with self.assertRaisesRegex(MotionSpecError, "真实语义窗口"):
        build_motion_spec(real_opportunity(), content_with_outside_beat(), spec_id="MS-1")

def test_duration_change_recomputes_relative_primitive_timing():
    short = build_motion_spec(real_opportunity("10", "16"), beat_content(), spec_id="MS-1")
    long = recompute_motion_timing(short, {"start_seconds": "10", "end_seconds": "22"})
    self.assertNotEqual(short["relative_timing"], long["relative_timing"])
    self.assertEqual(long["semantic_beats"][0]["absolute_seconds"], "10")
```

- [ ] **Step 2: Run the targeted tests and verify RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_timing_contract tests.test_visual_director tests.test_motion_spec -v`

Expected: failures because provenance/semantic-beat contracts do not exist yet.

- [ ] **Step 3: Implement the smallest contract extension**

Use only the existing alignment digest and alignment-projected ranges. Reject old/estimated clocks for formal asset-pack runs. Store absolute semantic beats and derive normalized primitive reveal intervals from actual span length; retain old `motion-spec/1` readers only when a legacy compatibility caller does not request formal asset-pack output.

- [ ] **Step 4: Run targeted tests and all Visual Director/Motion tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_timing_contract tests.test_visual_director tests.test_motion_spec tests.test_visual_asset_renderer -v`

Expected: PASS.

- [ ] **Step 5: Commit the real-time contract**

```bash
git add src/deeptalk_studio/visual_director.py src/deeptalk_studio/motion_spec.py tests/test_asset_pack_timing_contract.py tests/test_visual_director.py tests/test_motion_spec.py
git commit -m "feat: bind visual timing to actual a-roll spans"
```

### Task 3: Add fact-conflict protection and a semantic timeline artifact

**Files:**
- Create: `src/deeptalk_studio/semantic_timeline.py`
- Create: `src/deeptalk_studio/fact_conflict.py`
- Create: `tests/test_semantic_timeline.py`
- Create: `tests/test_fact_conflict.py`
- Modify: `src/deeptalk_studio/edit_bridge_session.py`

**Interfaces:**
- `build_semantic_timeline(script, transcript, alignment, fact_conflicts, *, timeline_id, created_at)` produces non-overlapping real-A-roll spans with readable summaries, source transcript units, alignment lineage, and safe visual eligibility.
- `detect_fact_conflicts(script, transcript, alignment, approved_facts)` produces `FACT_CONFLICT` records carrying actual start/end and an explicit blocked display binding.
- Both artifacts fail closed without an accepted Clean A-roll alignment and never rewrite actual transcript/audio.

- [ ] **Step 1: Write failing semantic/fact tests**

```python
def test_semantic_timeline_requires_accepted_actual_alignment():
    with self.assertRaisesRegex(SemanticTimelineError, "Clean A-roll Alignment"):
        build_semantic_timeline(script(), transcript(), estimated_alignment(), [], timeline_id="ST-1", created_at=NOW)

def test_fact_conflict_records_actual_time_and_blocks_wrong_display():
    conflicts = detect_fact_conflicts(script_with_7000(), transcript_saying_70000(), alignment(), approved_facts())
    self.assertEqual(conflicts[0]["conflict_type"], "FACT_CONFLICT")
    self.assertEqual(conflicts[0]["actual_start_seconds"], "12.4")
    self.assertTrue(conflicts[0]["display_blocked"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_semantic_timeline tests.test_fact_conflict -v`

Expected: Import failures for the new modules.

- [ ] **Step 3: Implement deterministic semantic and fact-conflict artifacts**

Use exact reviewed Script/approved fact bindings and the existing global monotonic projection. Distinguish factual disagreement from ordinary paraphrase; block numeric, date, named person/organization/work, policy, and explicit-causality display content when actual spoken wording conflicts. Build each semantic span from contiguous safe aligned units only; unresolved segments stay `KEEP_A_ROLL` with a recorded reason.

- [ ] **Step 4: Run focused tests plus alignment regressions**

Run: `PYTHONPATH=src python3 -m unittest tests.test_semantic_timeline tests.test_fact_conflict tests.test_global_alignment_projection tests.test_alignment_validation -v`

Expected: PASS.

- [ ] **Step 5: Commit semantic/fact gates**

```bash
git add src/deeptalk_studio/semantic_timeline.py src/deeptalk_studio/fact_conflict.py src/deeptalk_studio/edit_bridge_session.py tests/test_semantic_timeline.py tests/test_fact_conflict.py
git commit -m "feat: add real semantic timeline and fact conflict gate"
```

### Task 4: Build the default Asset Pack and complete Edit Map contract

**Files:**
- Create: `src/deeptalk_studio/asset_pack_workflow.py`
- Modify: `src/deeptalk_studio/visual_asset_pack.py`
- Modify: `src/deeptalk_studio/edit_map.py`
- Create: `tests/test_asset_pack_workflow.py`
- Modify: `tests/test_visual_asset_pack.py`

**Interfaces:**
- `build_production_asset_pack(accepted_roots, semantic_timeline, visual_director_plan, asset_candidates, *, episode_root, created_at)` returns a manifest and machine `edit-map/1.json` plus human Markdown/CSV paths.
- The map includes every semantic span, including `KEEP_A_ROLL`, actual start/end, spoken-content summary, decision, filename (when applicable), placement advice, reason, provenance, QA, and fallback outcome.
- Output uses only `05_A-roll`, `06_真实素材`, `07_MG动画`, `08_高级动画`, `09_剪辑表`, and `_DeepTalk记录`; it must not create a `final_video.mp4`.

- [ ] **Step 1: Write failing Asset Pack/Edit Map tests**

```python
def test_no_alignment_means_no_formal_edit_map():
    with self.assertRaisesRegex(AssetPackWorkflowError, "Clean A-roll Alignment"):
        build_production_asset_pack(unaccepted_roots(), [], [], [], episode_root=Path(self.tmp), created_at=NOW)

def test_map_contains_actual_keep_row_and_ready_mg_row():
    result = build_production_asset_pack(accepted_roots(), semantic_spans(), director_plan(), ready_assets(), episode_root=Path(self.tmp), created_at=NOW)
    self.assertEqual(result.machine_map["rows"][0]["decision"], "KEEP_A_ROLL")
    self.assertEqual(result.machine_map["rows"][1]["actual_start_seconds"], "12.4")
    self.assertEqual(result.machine_map["rows"][1]["asset_filename"], "MG_01_票房反差.mp4")

def test_nonkeep_row_without_existing_ready_asset_falls_back_to_keep():
    result = build_production_asset_pack(accepted_roots(), semantic_spans(), director_plan_with_failed_mg(), failed_assets(), episode_root=Path(self.tmp), created_at=NOW)
    self.assertEqual(result.machine_map["rows"][1]["decision"], "KEEP_A_ROLL")
    self.assertEqual(result.machine_map["rows"][1]["fallback_outcome"], "KEEP_A_ROLL")

def test_default_workflow_does_not_emit_final_video_or_nle_project():
    result = build_production_asset_pack(accepted_roots(), semantic_spans(), director_plan(), ready_assets(), episode_root=Path(self.tmp), created_at=NOW)
    self.assertFalse((Path(self.tmp) / "10_成片" / "final_video.mp4").exists())
    self.assertTrue(result.markdown_path.is_file() and result.csv_path.is_file() and result.json_path.is_file())
```

- [ ] **Step 2: Run Asset Pack tests and verify RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_workflow tests.test_visual_asset_pack -v`

Expected: Import failure for `asset_pack_workflow` and Edit Map schema assertions.

- [ ] **Step 3: Implement the default packaging workflow**

Write a machine JSON artifact, then derive Markdown/CSV from it. Include valid KEEP rows with no asset, retain only verified QA-ready Real/MG/Advanced files for non-KEEP rows, and deterministically downgrade unavailable candidates through the specified fallback chain. Do not invoke the full-video renderer, mutate source media, or generate an NLE project.

- [ ] **Step 4: Run Asset Pack, renderer, and fallback tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_workflow tests.test_visual_asset_pack tests.test_visual_asset_engine_fixture tests.test_edit_bridge_partial_success -v`

Expected: PASS.

- [ ] **Step 5: Commit the default user delivery**

```bash
git add src/deeptalk_studio/asset_pack_workflow.py src/deeptalk_studio/visual_asset_pack.py src/deeptalk_studio/edit_map.py tests/test_asset_pack_workflow.py tests/test_visual_asset_pack.py
git commit -m "feat: make asset pack and edit map the production output"
```

### Task 5: Wire the canonical default workflow without removing preview compatibility

**Files:**
- Modify: `src/deeptalk_studio/edit_bridge_session.py`
- Modify: `src/deeptalk_studio/edit_bridge_workflow.py`
- Modify: `src/deeptalk_studio/edit_bridge_qa.py`
- Create: `tests/test_asset_pack_production_workflow.py`
- Modify: `tests/test_real_edit_bridge_session.py`
- Modify: `tests/test_edit_bridge_workflow.py`

**Interfaces:**
- `run_real_edit_bridge_session(..., output_mode="asset_pack")` defaults to Asset Pack + Edit Map and returns no final edited video path.
- `output_mode="compatibility_preview"` retains historical Preview-only behavior and must not be treated as primary user delivery.
- Formal pack generation refuses without accepted Clean A-roll, transcript/alignment lineage, and semantic timeline; ordinary decisions do not require user confirmations; Advanced requires explicit approved spec.

- [ ] **Step 1: Write failing end-to-end orchestration tests**

```python
def test_default_real_session_returns_asset_pack_not_final_preview():
    result = run_real_edit_bridge_session(inputs(), fake_accepted_provider(), clock=clock, id_factory=ids)
    self.assertIn("edit_map", result.paths)
    self.assertNotIn("final_video", result.paths)
    self.assertEqual(result.artifacts["delivery_mode"], "asset_pack")

def test_ordinary_keep_real_mg_do_not_require_per_row_human_review():
    result = build_production_asset_pack(accepted_roots(), semantic_spans(), ordinary_director_plan(), ready_assets(), episode_root=Path(self.tmp), created_at=NOW)
    self.assertFalse(result.requires_human_review)

def test_advanced_motion_is_withheld_without_its_separate_review():
    result = build_production_asset_pack(accepted_roots(), semantic_spans(), advanced_plan_without_review(), ready_assets(), episode_root=Path(self.tmp), created_at=NOW)
    self.assertEqual(result.machine_map["rows"][0]["decision"], "KEEP_A_ROLL")
    self.assertTrue(result.requires_human_review)
```

- [ ] **Step 2: Run orchestration tests and verify RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_production_workflow tests.test_real_edit_bridge_session tests.test_edit_bridge_workflow -v`

Expected: default still invokes Preview rendering and lacks `delivery_mode`/Asset Pack output.

- [ ] **Step 3: Implement default output routing**

Keep the legacy renderer entrypoint intact behind a deliberate `compatibility_preview` mode. Default entrypoint builds accepted transcript/alignment, Clean A-roll gate result, semantic timeline, fact-conflict report, Visual Director plan, individual asset QA, manifest, and Asset Pack/Edit Map. Preserve `run_full_edit_bridge_workflow` as a compatibility alias only where tests require it; never write a final video.

- [ ] **Step 4: Run orchestration and canonical QA tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_production_workflow tests.test_real_edit_bridge_session tests.test_edit_bridge_workflow tests.test_canonical_edit_bridge_qa tests.test_edit_bridge_qa -v`

Expected: PASS.

- [ ] **Step 5: Commit the default routing**

```bash
git add src/deeptalk_studio/edit_bridge_session.py src/deeptalk_studio/edit_bridge_workflow.py src/deeptalk_studio/edit_bridge_qa.py tests/test_asset_pack_production_workflow.py tests/test_real_edit_bridge_session.py tests/test_edit_bridge_workflow.py
git commit -m "feat: route real production to asset pack delivery"
```

### Task 6: Update product documentation and Skills

**Files:**
- Modify: `README.md`
- Modify: `PRD.md`
- Modify: `ROADMAP.md`
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/EDIT_BRIDGE_CONTRACT.md`
- Modify: `.agents/skills/align-video/SKILL.md`
- Create: `docs/ASSET_PACK_EDIT_MAP_CONTRACT.md`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Documents describe Asset Pack + Edit Map as the primary UX and full preview as compatibility/QA only.
- `HANDOFF.md` ends with the required `## 给用户的下一步操作` and a copy-ready ChatGPT message.

- [ ] **Step 1: Write a failing documentation-contract test**

```python
def test_primary_docs_name_asset_pack_as_default_and_prohibit_auto_final_edit():
    corpus = "\n".join(Path(path).read_text(encoding="utf-8") for path in PRIMARY_DOCS)
    self.assertIn("Asset Pack + Edit Map", corpus)
    self.assertIn("不替用户剪辑最终视频", corpus)
    self.assertNotIn("V1.0 目标输出是 `reviewed Script + Clean A-roll + Real Material + Original Motion + Basic Subtitle → 完整可观看粗剪`", corpus)
```

- [ ] **Step 2: Run the documentation test and verify RED**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_production_workflow.AssetPackDocumentationTests -v`

Expected: FAIL because current PRD presents full rough cut as the primary target.

- [ ] **Step 3: Apply minimal documentation/Skill revisions**

Describe the Clean A-roll manual-only boundary, actual-time-only contract, four decisions, fact conflict protection, QA/fallback, Asset Pack folders, and human Markdown/CSV/machine JSON Edit Map. State specifically that normal KEEP/REAL/MG decisions need no per-row approval and Advanced is separately reviewed. Do not promise automated NLE or publishing.

- [ ] **Step 4: Run the documentation test and Skill validation**

Run: `PYTHONPATH=src python3 -m unittest tests.test_asset_pack_production_workflow.AssetPackDocumentationTests -v && PYTHONPATH=src python3 /Users/hwang/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/align-video`

Expected: PASS.

- [ ] **Step 5: Commit docs**

```bash
git add README.md PRD.md ROADMAP.md AGENTS.md docs/ARCHITECTURE.md docs/EDIT_BRIDGE_CONTRACT.md docs/ASSET_PACK_EDIT_MAP_CONTRACT.md .agents/skills/align-video/SKILL.md CHANGELOG.md HANDOFF.md tests/test_asset_pack_production_workflow.py
git commit -m "docs: define asset pack as the primary production UX"
```

### Task 7: Validate the real 《牛来》 episode without changing content

**Files:**
- Create local/gitignored artifacts under `/Users/hwang/Movies/自媒体创意库/牛来_电影话语权反噬/05_A-roll/`
- Create local/gitignored artifacts under `/Users/hwang/Movies/自媒体创意库/牛来_电影话语权反噬/06_真实素材/`, `07_MG动画/`, `08_高级动画/`, `09_剪辑表/`, `_DeepTalk记录/`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Inputs: the canonical r4 script exactly at SHA-256 `5b8308dba915ae91b21f849ccc0ecd5da0a0181f8fa383bfb57385875cfe45ef`, its existing lineage, and `/Users/hwang/Movies/口播/牛来8月24日.mp4`.
- Outputs: only real ASR/transcript/alignment/fact conflict/semantic plan/asset manifest/QA/Edit Map products local to the episode; no Git commit includes these assets.

- [ ] **Step 1: Verify source identities and inspect the Clean A-roll Gate**

Run read-only SHA/ffprobe and the default gate. If it returns `needs_manual_cleanup`, stop before assets and report exactly one ordinary user action; do not offer a cut list or execute any media edit.

- [ ] **Step 2: If accepted, run the local production path**

Use local whisper.cpp multilingual `large-v3`, the existing global monotonic alignment, the new semantic/fact-conflict gates, Visual Director, individual REAL/MG generation, Asset QA, Asset Manifest, and Edit Map. Do not use estimated timings or the legacy full-preview output as the primary delivery.

- [ ] **Step 3: Validate real outputs**

Run ffprobe/SHA/binding QA on every non-KEEP asset; prove each map time comes from actual A-roll and every non-KEEP map filename is a real READY file. Check all artifact paths and ensure the video, script, research, and material histories were not modified.

- [ ] **Step 4: Run the full repository suite and production regressions**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Run focused: `PYTHONPATH=src python3 -m unittest tests.test_clean_aroll_gate tests.test_asset_pack_timing_contract tests.test_semantic_timeline tests.test_fact_conflict tests.test_asset_pack_workflow tests.test_asset_pack_production_workflow tests.test_visual_director tests.test_motion_spec -v`

Expected: PASS, with only existing explicit render/environment skips if reported.

- [ ] **Step 5: Final Git integrity check and push current branch**

Run: `git status --short`, `git log --oneline origin/agent/audio-alignment-edit-bridge..HEAD`, and `git push origin agent/audio-alignment-edit-bridge`. Confirm no user episode assets are staged; do not merge, tag, or release.

## Self-Review

- Spec coverage: Tasks 1–5 cover no auto edit/take selection, actual-time-only, fact conflict, semantic understanding, four decisions, QA-ready assets, fallback, no default full video, and Advanced review. Task 6 makes those rules durable. Task 7 verifies the real episode only after the safety gates pass.
- Placeholder scan: no `TODO`, `TBD`, or unspecified validation steps.
- Type consistency: `CleanARollGateResult`, semantic timeline, fact conflicts, Visual Director opportunities, Motion Specs, Asset Manifest, and `edit-map/1` are the only new cross-task artifacts; later tasks consume the exact names defined above.

## Execution Handoff

This plan is being executed inline in this session under the user’s explicit instruction. Follow each test-first task in order and leave all content assets outside Git.
