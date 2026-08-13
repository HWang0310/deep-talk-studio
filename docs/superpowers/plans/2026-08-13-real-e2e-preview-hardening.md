# Real E2E Preview Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复真实 Trial 的 diagram 和 comparison 可读性，同时正式保存 timeline safe-area 修复并生成新的 immutable Motion preview。

**Architecture:** Python Core 继续独占 Research 到 scene payload 的事实语义与 Display Text Gate；两个 renderer 只执行统一的卡片、节点和标签板布局。过长文字在 Core fail closed，不在 renderer 中截断或改写。

**Tech Stack:** Python 3 标准库、unittest、TypeScript/React、Remotion 4.0.507、HyperFrames 0.7.106、ffmpeg/ffprobe、Git/GitHub。

## Global Constraints

- 不修改 reviewed Script、approved Research 或 reviewed Material Package。
- 不实现音频对齐、字幕、BGM、SFX、标题、封面或发布。
- 不创建 tag 或 v0.6.2 Release。
- 保留旧 Production 工件，创建新的 Production ID 与输出。
- 所有事实 Display Text 必须保持既有 Claim/Evidence binding。

---

### Task 1: Core comparison heading and layout capacity Gate

**Files:**
- Modify: `src/deeptalk_studio/production_planner.py`
- Modify: `src/deeptalk_studio/production_validation.py`
- Test: `tests/test_production_planner.py`
- Test: `tests/test_production_validation.py`

**Interfaces:**
- Consumes: Material comparison/diagram fields and approved Research bindings.
- Produces: unchanged `scene_payload` shape with neutral heading and deterministic pre-render capacity checks.

- [x] Add failing tests for 3 comparison items, neutral heading, binding preservation and excessive diagram text rejection.
- [x] Run focused tests and confirm the new assertions fail for the intended old behavior.
- [x] Add “要点对照” to the controlled allowlist, select it in Planner, and reject text beyond fixed display capacities.
- [x] Run focused Planner/Validation tests and confirm pass.

### Task 2: Shared renderer card and safe diagram layouts

**Files:**
- Modify: `renderer_templates/remotion/src/ProductionComposition.tsx`
- Modify: `src/deeptalk_studio/production_renderers/hyperframes.py`
- Test: `tests/test_production_renderers.py`

**Interfaces:**
- Consumes: existing ordered comparison items and diagram nodes/edges.
- Produces: each comparison item as one card; wrapped node text and offset edge label plates in both renderers.

- [x] Add failing real-Chinese regressions for 3 cards, single mechanism labels, fact preservation, wrapped nodes and separated edge labels.
- [x] Run renderer tests and confirm failures describe the current two-column/one-line layouts.
- [x] Implement Remotion comparison cards and diagram foreignObject/label plates without altering payload text.
- [x] Implement the equivalent HyperFrames markup/CSS from the same payload.
- [x] Run renderer tests and template validation.

### Task 3: Real immutable Trial rerender and manual review

**Files:**
- Create ignored runtime files under `production_packages/`, `production_projects/`, `production_assets/`.
- Modify: `CHANGELOG.md`, `ROADMAP.md`, `HANDOFF.md`, production contract/evals/adapter docs as needed.

**Interfaces:**
- Consumes: the exact existing reviewed Script, approved Research and reviewed Material Package.
- Produces: new Production Plan, clips, preview, still, Manifest and Production QA.

- [x] Run the full test suite.
- [x] Run one real Remotion production from the exact Trial inputs without overwriting history.
- [x] Verify validation, preview, render, ffprobe, Manifest, QA, SHA and source bindings.
- [x] Extract and inspect frames for timeline, diagram and comparison; confirm reference-only sources remain unstaged.
- [x] Update project records with results and remaining gaps.
- [ ] Stage only scoped files, commit on `agent/real-e2e-preview-hardening`, push to GitHub, and verify remote branch/commit without tagging or releasing.
