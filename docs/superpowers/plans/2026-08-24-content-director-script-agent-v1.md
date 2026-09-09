# Content Director + Script Agent V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a review-gated Content Director and Thesis Card before Script generation, then make Script review fail closed when factual safety or audio-only retention quality is insufficient.

**Architecture:** Keep approved Research and Fact Check as the sole factual authority. Add immutable `content-thesis-card/1` and independent Thesis Review artifacts that bind a selected content angle to exact Research lineage. Upgrade the existing Script Draft/Review lineage rather than replacing it: new scripts bind the approved Thesis Card, preserve typed beat/evidence grounding, store only estimated duration range, and use an expanded deterministic review contract for retention and content value.

**Tech Stack:** Python 3 standard library, existing DeepTalk JSON-schema validation, immutable filesystem artifacts, unittest.

**Spec:** `/Users/hwang/.codex/attachments/91351eb3-8a36-454d-9f94-488207f81336/pasted-text.txt`

## Global Constraints

- A Thesis Card may only consume `ready_for_script` Research with a passing Fact Check and explicit Research approval.
- A long Script may only consume an independently approved Thesis Card; no self-approval and no direct Research-to-Script bypass in the V1 path.
- Competitive research may inform angles, structure and audience insight, but never promotes a competitor claim into a factual Beat.
- Final factual Beats continue to bind only `verified confirmed_fact` Research Claims; analysis/inference/question remain explicitly typed.
- The Script stage stores an estimated speaking-duration range only. It never creates final A-roll, visual, motion or edit timings.
- Script Review treats factual safety and missing counter-evidence as blocking; an audio-only retention failure is `NEEDS_REVISION`, not a reviewed Script.
- Do not alter approved Research, reviewed Material, production history, `main`, `v0.6.1`, or GitHub Releases.

---

### Task 1: Versioned Content Thesis Card core

**Files:**
- Create: `src/deeptalk_studio/content_director.py`
- Create: `src/deeptalk_studio/content_thesis_storage.py`
- Modify: `src/deeptalk_studio/schema.py`
- Modify: `src/deeptalk_studio/models.py`
- Test: `tests/test_content_director.py`

**Interfaces:**
- Consumes: `ResearchReport`, a content-only Thesis proposal, and a versioned Content Director profile.
- Produces: `ContentThesisCard` with exact report ID/revision/digest, computed identity/revision/status, strongest-evidence Claim IDs, counter-evidence Claim IDs, audience-value fields, and no final timing fields.

- [ ] Write failing tests for rejecting non-approved Research, rejecting unknown/non-verified evidence Claim IDs, and producing an immutable `draft` card with all user-facing fields.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.test_content_director -v` and confirm the failures are caused by the absent core.
- [ ] Implement only the schema, value object, validator, digest derivation and immutable storage necessary to satisfy those tests.
- [ ] Re-run the focused tests and commit `feat: add content thesis card contract`.

### Task 2: Thesis Gate, independent review, revision and user-readable surface

**Files:**
- Create: `src/deeptalk_studio/thesis_review.py`
- Create: `src/deeptalk_studio/content_thesis_renderer.py`
- Modify: `src/deeptalk_studio/content_director.py`
- Modify: `src/deeptalk_studio/content_thesis_storage.py`
- Modify: `src/deeptalk_studio/schema.py`
- Test: `tests/test_thesis_review.py`

**Interfaces:**
- Consumes: a draft card and independent review content containing all Thesis checks.
- Produces: an immutable Thesis Review Artifact and a new Card revision. Only a PASS review with an explicit human confirmation produces `approved_for_script`.

- [ ] Write failing tests for incomplete Gate checks, a weak/no-own-judgment card that cannot pass, a missing counter-evidence binding, tampered review linkage, and a readable review that contains no JSON/IDs.
- [ ] Run the focused tests and observe expected failures.
- [ ] Implement deterministic check/issue mapping, explicit confirmation revision, revision lineage and natural-language renderer.
- [ ] Re-run the focused tests and commit `feat: add thesis review gate`.

### Task 3: Script V1 Thesis, duration and competitive-insight binding

**Files:**
- Modify: `src/deeptalk_studio/script_validation.py`
- Modify: `src/deeptalk_studio/script_workflow.py`
- Modify: `src/deeptalk_studio/script_revisions.py`
- Modify: `src/deeptalk_studio/script_storage.py`
- Modify: `src/deeptalk_studio/script_renderer.py`
- Modify: `src/deeptalk_studio/schema.py`
- Modify: `src/deeptalk_studio/models.py`
- Test: `tests/test_script_validation.py`
- Test: `tests/test_script_workflow.py`
- Test: `tests/test_script_revisions.py`

**Interfaces:**
- Consumes: `ContentThesisCard` whose Thesis Review and human confirmation are both validated.
- Produces: a backward-readable Script artifact with Thesis Card digest/lineage, a requested duration range and estimated duration only.

- [ ] Write failing tests proving direct V1 script generation without an approved Thesis Card is rejected, a 5–6 minute request derives a range rather than defaulting to 12, and final A-roll/visual timing fields are rejected.
- [ ] Run the focused tests and observe expected failures.
- [ ] Implement the minimum Script V1 bindings while preserving old Script 0.4 loading and downstream compatibility.
- [ ] Re-run the focused tests and commit `feat: bind scripts to approved thesis cards`.

### Task 4: Content/retention Script Quality Gate

**Files:**
- Modify: `config/script-profile.json`
- Create: `config/content-director-profile.json`
- Modify: `src/deeptalk_studio/script_profile.py`
- Modify: `src/deeptalk_studio/script_review.py`
- Modify: `src/deeptalk_studio/script_prompt.py`
- Modify: `src/deeptalk_studio/schema.py`
- Test: `tests/test_script_review.py`
- Test: `tests/test_script_profile.py`

**Interfaces:**
- Consumes: exact approved Research, Thesis Card and Script Draft.
- Produces: expanded Script Review checks: hook, curiosity, conflict, emotion, resonance, approval point, comment tension, spokesperson value, value identity, cognitive shifts, humor/lightness, counter-evidence, spoken naturalness, repetition, density, duration fit and originality risk.

- [ ] Write failing tests proving a factually safe but retention-empty script cannot be `reviewed`, counter-evidence omission produces a blocking issue, reference-style imitation is surfaced, and the six audience-value indicators are required.
- [ ] Run the focused tests and observe expected failures.
- [ ] Add only typed checks/issues and deterministic fail/needs-revision behavior required by the tests; update prompts/profile with high-level original-expression rules.
- [ ] Re-run focused tests and commit `feat: harden script quality gate for retention`.

### Task 5: User workflow, CLI, skills and documentation

**Files:**
- Modify: `src/deeptalk_studio/cli.py`
- Modify: `.agents/skills/write-script/SKILL.md`
- Modify: `docs/SCRIPT_CONTRACT.md`
- Create: `docs/CONTENT_DIRECTOR_CONTRACT.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `README.md`, `PRD.md`, `ROADMAP.md`, `AGENTS.md`, `CHANGELOG.md`, `HANDOFF.md`
- Test: `tests/test_content_director.py`

**Interfaces:**
- Exposes `prepare-thesis`, `review-thesis`, `approve-thesis`, and `prepare-script`/`review-script` with the new exact Thesis binding.
- Renders a normal-user Thesis Review in Chinese without requiring users to manipulate JSON or artifact IDs.

- [ ] Write failing CLI/renderer tests for the natural-language Thesis Review, confirmation gate and no-final-timing boundary.
- [ ] Run focused tests and observe expected failures.
- [ ] Implement CLI wiring, skill instructions and contract/documentation updates.
- [ ] Re-run focused tests and commit `feat: expose content director workflow`.

### Task 6: Real 《牛来》 acceptance run and repository verification

**Files:**
- Create outside Git only: `/Users/hwang/Movies/自媒体创意库/牛来_电影话语权反噬/_DeepTalk记录/`
- Create outside Git only: user-readable Thesis Card and review under `04_口播稿/`
- Modify: `HANDOFF.md`, `CHANGELOG.md` only for the actual implementation and status.
- Test: full unit suite and Content/Script targeted regressions.

**Interfaces:**
- Uses the approved, fact-bound Research artifact chosen by the user and the existing episode research/Fact Check documents as competitive-insight input.
- Stops at the Human Thesis Review unless the user supplies an explicit plain-language “按这个方向继续” confirmation. It never fabricates this approval.

- [ ] Prepare a real Thesis Card for the 5–6 minute 《牛来》 episode, bind strongest/counter evidence to approved facts, and save a normal-user review surface.
- [ ] Run the exact Thesis Gate and show the user the resulting ordinary-language card.
- [ ] If the user explicitly confirms, generate the 5–6 minute Script Draft, run independent Script Quality Review, preserve revision lineage, and save the reviewed Teleprompter version outside Git.
- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `git diff --check`; inspect Git status before committing/pushing only repository code and documents.

## Plan self-review

- Covers all requested contracts: Content Director/Card/Gate/review, Script V1, six audience indicators, retention checks, evidence/competitive boundaries, counter-evidence, duration and real A-roll timing boundary.
- The only intentionally deferred item is human Thesis confirmation: the product requirement expressly forbids self-approval. The implementation and real Card can be completed now; real Reviewed Script awaits a user’s ordinary-language confirmation.
- No new visual, subtitles, A-roll cleanup, NLE, publishing or new competitor-download subsystem is included.
