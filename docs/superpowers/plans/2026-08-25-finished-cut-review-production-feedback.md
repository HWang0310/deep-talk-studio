# Finished Cut Review + Production Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Finished Cut Review and episode-bound Production Feedback Loop that learns from a creator's manually assembled NLE cut without editing it.

**Architecture:** A pure comparison core validates immutable Edit Map, Asset Manifest, Finished Cut media evidence and conservative asset-match observations. It emits `finished-cut-review/1` and `production-feedback/1`; Markdown is a rendering of those records. The visual inspector only decodes frames and reports `used` when concrete evidence clears its threshold; uncertainty remains `UNKNOWN`.

**Tech Stack:** Python standard library, existing ffprobe/ffmpeg runtime, unittest, JSON/Markdown artifacts.

**Spec:** `/Users/hwang/.codex/attachments/7d5a3ef8-8f5d-4783-ac80-e98c4bbfdfc1/pasted-text.txt`

## Global Constraints

- The Finished Cut is immutable input: never write, move, render, replace, trim, or mux it.
- Never create an NLE project or a further final video.
- Actual timing comes only from Finished Cut media time; Edit Map timing is planned time.
- Ambiguous asset use, timing, or presentation remains `UNKNOWN`.
- Episode observations create only `CANDIDATE_PRODUCT_RULE`; no function applies global defaults.
- Product code/docs may enter the branch; episode media and review artifacts stay local and gitignored.
- Do not predict views, virality, creator quality, or enter a second production pass.

---

### Task 1: Define read-only review and feedback contracts

**Files:**

- Create: `src/deeptalk_studio/finished_cut_review.py`
- Create: `tests/test_finished_cut_review.py`

**Interfaces:**

- `build_finished_cut_review(edit_map, manifest, finished_cut, observations) -> Mapping`
- `build_production_feedback(review) -> Mapping`

- [x] Write failing tests: unknown observation stays `UNKNOWN`; an episode observation produces only a `CANDIDATE_PRODUCT_RULE`; missing lineage is rejected; a creator override is not an error.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.test_finished_cut_review -v` and verify import failure (RED).
- [x] Implement the minimum pure validation/comparison contract: planned start/end/asset, actual status/start/end/presentation, offset only when actual timing is known, and binding digests.
- [x] Re-run the test module and verify all contract assertions pass (GREEN).

### Task 2: Add conservative read-only media inspection

**Files:**

- Modify: `src/deeptalk_studio/finished_cut_review.py`
- Modify: `tests/test_finished_cut_review.py`

**Interfaces:**

- `inspect_finished_cut_media(path: Path) -> Mapping`
- `match_manifest_assets(finished_cut: Path, manifest: Mapping) -> list[Mapping]`

- [x] Write failing tests: probing does not change video SHA; no confident match stays `UNKNOWN`; no NLE or new final media is produced.
- [x] Run the focused inspection tests and verify failure because APIs are absent (RED).
- [x] Implement ffprobe/SHA and low-resolution ffmpeg pipe fingerprints. Only accept a match over a documented threshold; otherwise emit `UNKNOWN`.
- [x] Re-run all finished-cut tests and verify GREEN.

### Task 3: Write local review artifacts

**Files:**

- Modify: `src/deeptalk_studio/finished_cut_review.py`
- Modify: `tests/test_finished_cut_review.py`

**Interfaces:**

- `write_finished_cut_feedback(episode_root, review, feedback) -> paths`

- [x] Write failing tests: machine JSON is stored under `_DeepTalk记录/`, Markdown under `10_成片/`, and no new `.mp4`, `.fcpxml`, or `.xml` is created.
- [x] Run the writer test and verify missing API failure (RED).
- [x] Implement JSON + ordinary-language Markdown writer only.
- [x] Re-run finished-cut tests and verify GREEN.

### Task 4: Document and run the real episode review

**Files:**

- Create: `docs/FINISHED_CUT_REVIEW_CONTRACT.md`
- Modify: `README.md`, `PRD.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md`, `HANDOFF.md`
- Create local only: `10_成片/《牛来》第一版成片复盘.md`, `10_成片/《牛来》Asset Pack 使用复盘.md`, `_DeepTalk记录/finished-cut-review-r0001.json`, `_DeepTalk记录/production-feedback-r0001.json`

- [x] Write failing documentation tests requiring `Finished Cut Review`, `Production Feedback Loop`, and `不修改成片` in the formal documentation.
- [x] Run the documentation test and verify RED.
- [x] Add the contract/docs. Run the local episode runner: probe/decode Finished Cut, conservatively match assets, bind to existing map/manifest/media SHA, and write only local JSON/Markdown.
- [x] Run focused tests: `PYTHONPATH=src python3 -m unittest tests.test_finished_cut_review tests.test_asset_pack_workflow tests.test_visual_asset_pack -v`.
- [x] Run full tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`; run `git diff --check`; verify no episode output is staged.
- [ ] Commit/push only product code/docs to `agent/audio-alignment-edit-bridge`; do not merge, tag, or release.

## Plan Review

- Covers read-only analysis, planned-vs-actual, UNKNOWN safety, lineage-bound feedback, candidate-only rules, local artifacts, docs, all required test boundaries, and a real episode validation.
- Excludes auto re-editing, NLE integration, final video generation, global strategy mutation, or virality scoring.
