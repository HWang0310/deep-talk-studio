# DeepTalk Nexus Session Handoff — 2026-09-01

> Purpose: durable GitHub-native transfer artifact for a new ChatGPT/Nexus project-manager session.
>
> This file is an immutable **handoff snapshot**, not the live source of truth. After reading it, the new Nexus MUST independently verify current GitHub state before making decisions. The canonical DeepTalk project truth remains the current remote repositories, especially `HWang0310/deep-talk-studio` branch `agent/multi-asset-studio`, plus the exact accepted plugin commits recorded below.

## 1. Recovery contract for the next Nexus

The next ChatGPT session must NOT ask the Owner to restate project history and must NOT rely on old ChatGPT conversation memory.

Recovery order:

1. Read the GitHub Recovery Issue that links to this handoff.
2. Read this handoff file at its exact immutable commit permalink.
3. Independently fetch current `HWang0310/deep-talk-studio` branch `agent/multi-asset-studio` and determine its current exact HEAD.
4. Read current `PROJECT_STATE.md` from that exact HEAD.
5. Read the relevant current section of `HANDOFF.md`, `CHANGELOG.md`, and `docs/plans/2026-08-28-multi-asset-implementation-plan.md`.
6. Compare current Core HEAD with the handoff snapshot SHA recorded below.
7. Inspect the exact current code/diff/tests for any new `DT-CORE-4-001` commit before accepting or correcting it.
8. Independently verify plugin exact revisions when they matter to the next gate.
9. Report to Owner: current project step, completed work, current task, active Agent, whether Owner needs to send a prompt, and next recommended action.
10. Write a `PROJECT_RECOVERED` ACK comment to the Recovery Issue with the recovered Core exact SHA and current task state.

GitHub facts override this snapshot if the canonical branch advanced after this file was written.

---

## 2. Roles and collaboration model

DeepTalk project-local roles:

- **Owner**: user / product owner. Decides product goals, priority, content direction, and final creator choices. The Owner should NOT be forced to make routine technical implementation decisions or act as a long-form relay between Agents and Nexus.
- **Nexus**: ChatGPT. Project manager, architecture coordinator, task decomposer, technical decision-maker, senior reviewer, merge/release governor. Nexus independently reviews GitHub exact SHA before PASS / NEEDS_CORRECTION / HOLD.
- **Atlas (C1)**: Codex / GPT-5.6 Sol specialist. Use for high-risk Core architecture, cross-repo integration, hard bugs, contract/security boundaries, exact-SHA integration work. Do not waste Atlas on mechanical work.
- **Forge (T1)**: TeleAgent implementation engineer. Primary implementation worker for clear scoped tasks.
- **Scribe (T2)**: TeleAgent implementation engineer. Secondary implementation worker; often suitable for independent plugin work, docs-only state recording, or another safely isolated task.

Generic engineering-journal role names must not replace these DeepTalk project-local names.

### GitHub-native handoff rule

When Nexus can access GitHub:

1. Agent implements/tests/commits/pushes.
2. Owner only needs to say something like `Forge 跑完了`.
3. Nexus directly inspects remote branch, exact SHA, diff, source, tests and GitHub CI/status.
4. Agent self-reported PASS is never Nexus acceptance.

Normal Agent completion signal should be minimal:

```text
DONE
TASK_ID: ...
BRANCH: ...
REMOTE_SHA: <full SHA>
PUSHED: YES
VALIDATION: PASS
BLOCKER: NONE
```

Do not make the Owner carry a long technical handoff unless critical evidence exists only locally and is not represented in GitHub.

### Parallelism rule

Default behavior: **actively look for safe parallel opportunities**, but never parallelize just for speed.

Parallel writers are allowed only if there is no shared mutable state, no overlapping file writes, no dependency on unfinished work, no shared worktree writing, and merge order cannot affect correctness.

Choose engineer count from the dependency graph, not from a fixed staffing target.

---

## 3. Product intent and hard boundaries

DeepTalk Studio is a creator-oriented system for human-led deep spoken videos.

Accepted V2 target:

```text
Semantic Timeline
→ Visual Opportunity
→ non-exclusive Candidate Portfolio
→ family-specific generation
→ Candidate QA
→ Candidate Asset Pack
→ Multi-option Edit Map
→ creator manual NLE selection
```

Core product principles:

- A-roll is always the base layer.
- DeepTalk may prepare multiple visual options for the same semantic opportunity.
- Candidates are intentionally non-exclusive.
- Candidates may overlap.
- Candidate durations may differ.
- Candidate families may differ.
- Creator may use none, one, or multiple candidates.
- DeepTalk must NOT automatically select a visual winner.
- DeepTalk must NOT automatically resolve candidate overlap.
- DeepTalk must NOT create an NLE project.
- DeepTalk must NOT alter A-roll automatically.
- DeepTalk must NOT assemble a final finished cut automatically.
- DeepTalk must NOT publish automatically.
- New V2 planning must not fabricate a `KEEP_A_ROLL` candidate; no Visual Opportunity is the V2 representation of no extra visual need.
- Generated explanatory assets must not impersonate `REAL_MATERIAL` documentary/evidence provenance.

Product positioning: DeepTalk is closer to a research team + director assistant + visual production team than an automatic video editor. Final creative judgment remains with the creator.

---

## 4. Repository topology

Workspace root used by engineering Agents:

`/Users/hwang/Movies/Program/DeepTalk/`

Repositories:

### Core

- Local: `/Users/hwang/Movies/Program/DeepTalk/deep-talk-studio`
- GitHub: `HWang0310/deep-talk-studio`
- Canonical development branch: `agent/multi-asset-studio`

### MG

- Local: `/Users/hwang/Movies/Program/DeepTalk/deeptalk-mg`
- GitHub: `HWang0310/deeptalk-mg`

### Illustrated Metaphor

- Local: `/Users/hwang/Movies/Program/DeepTalk/deeptalk-illustrated-metaphor`
- GitHub: `HWang0310/deeptalk-illustrated-metaphor`

### Hand-drawn Animation

- Local: `/Users/hwang/Movies/Program/DeepTalk/deeptalk-handdrawn-animation`
- GitHub: `HWang0310/deeptalk-handdrawn-animation`

These are separate repositories, not a monorepo.

---

## 5. Status semantics

Use these distinctions strictly:

- `PROPOSED`
- `ACCEPTED`
- `IMPLEMENTED`
- `IMPLEMENTED_UNRELEASED`
- `PINNED`
- `RELEASED`

A plan/spec existing does not mean accepted.

Agent implementation does not mean Nexus accepted.

Implemented does not mean released.

Latest formal product release remains `v0.6.1`; current multi-asset work is `V1.0 Candidate — Unreleased`.

Project rule: **History is preserved. Current truth is centralized.**

---

## 6. Contract V1 invariants

Contract version:

`visual-asset-plugin-contract/1`

Suitability completed outcomes:

- `SUITABLE`
- `BORDERLINE`
- `ABSTAIN`

ABSTAIN is normal, not a plugin health failure.

Generation operation statuses:

- `COMPLETED`
- `FAILED`
- `BLOCKED`
- `UNAVAILABLE`

Produced Candidate statuses:

- `READY`
- `QA_REJECTED`

Important invariants:

- `COMPLETED` yields exactly one Candidate.
- `FAILED / BLOCKED / UNAVAILABLE` must not fabricate a Candidate.
- Raw plugin `candidate_status` is immutable evidence.
- Core independently records `core_acceptance: ACCEPTED | REJECTED`.
- Core never rewrites plugin `READY` into `QA_REJECTED`.
- Creator-facing Phase 4 delivery may include only raw `READY` + Core `ACCEPTED` candidates.
- All machine failure/no-call/rejection evidence remains in `candidate-portfolio/1` and must not disappear from machine history.

Current policy semantics:

- LEAN: all completed SUITABLE
- STANDARD: all completed SUITABLE; if zero SUITABLE, all completed BORDERLINE
- RICH: all completed SUITABLE + BORDERLINE
- never generate ABSTAIN / failure / disabled entries
- no winner selection

---

## 7. Accepted exact plugin revisions

### MG — accepted and pinned

- plugin_id: `org.deeptalk.mg`
- plugin_version: `1.0.0-contract-v1`
- runner: `node scripts/contract-runner.js`
- version command: `node scripts/contract-runner.js --version`
- accepted/pinned SHA: `7ae59f1115da8a011113c81f31d320783b0ce8a4`
- require_clean_worktree: `true`
- state: `ACCEPTED / PINNED / IMPLEMENTED_UNRELEASED`

### Illustrated Metaphor — accepted runner readiness

- plugin_id: `org.deeptalk.illustrated-metaphor`
- plugin_version: `0.2.0-contract-runner`
- runner: `python3 scripts/contract_runner.py`
- version command: `python3 scripts/contract_runner.py --version`
- accepted exact SHA: `48848affe018fc2cff8ee15bad7a09bb002776e4`
- require_clean_worktree: `true`
- state: runner implementation accepted; Core Phase 3B readiness record exact-pinned but disabled

Key accepted correction facts:

- Candidate duration reports actual final MP4 duration, not requested duration when FFmpeg quantization differs.
- 1920x1080 real integration verified.
- Final QA runs after final rendering/postprocess.
- ABSTAIN generation fails closed instead of producing a Candidate.

### Hand-drawn Animation — accepted runner readiness

- plugin_id: `org.deeptalk.handdrawn-animation`
- plugin_version: `handdrawn-animation-contract/0.1.0`
- runner: `node src/contract-runner.js`
- version command: `node src/contract-runner.js --version`
- accepted exact SHA: `67698fd8ea09109ff91c912f51e4c2d4f0b8482f`
- require_clean_worktree: `true`
- state: runner implementation accepted; Core Phase 3B readiness record exact-pinned but disabled

Key accepted correction facts:

- artifact URIs are Core-compatible relative `local-runner://...` locators
- proposal tampering fails closed
- generation UNAVAILABLE preserves proposal_id
- candidate identity binds full internal scene/render state
- deterministic MP4 proof exists
- filesystem-safe internal `scene_<sha>` identity prevents opportunity_id path traversal
- output-dir containment is checked before renderer writes
- traversal regressions cover Unix, Windows-style and drive-like malicious IDs

---

## 8. Accepted Core milestones and exact SHAs

### Phase 0–2

Accepted / implemented-unreleased foundations include:

- Contract V1 validation
- sanitized fake-only vertical slice
- Visual Opportunity/directive foundations
- fake subprocess orchestration
- deterministic LEAN/STANDARD/RICH policy
- Core acceptance separate from raw plugin status
- hardened immutable candidate portfolio storage
- production directive authoring boundary
- relocation-safe artifact resolution

### Core Phase 3A-2

Task: `DT-CORE-3A2-001`

Accepted exact Core SHA:

`990fc03922e527bef64b819cf898e4266d5669c1`

State:

`ACCEPTED / IMPLEMENTED_UNRELEASED`

Purpose: prove one real exact-pinned MG runner through Core suitability/generation/artifact acceptance.

Important security correction accepted at this SHA:

- Core artifact resolution rejects lexical output-root, ancestor, or final-artifact symlinks before containment/existence/SHA/duration checks.

### Core Phase 3B

Task: `DT-CORE-3B-001`

Accepted implementation SHA:

`ec595587a378d54bd2a18270ded504707b04ddea`

State:

`ACCEPTED / IMPLEMENTED_UNRELEASED`

Purpose: record the independently reviewed Illustrated and Hand-drawn exact runner revisions in Core static readiness configuration.

All three static Core plugin config entries remain:

`enabled: false`

Phase 3B acceptance explicitly does NOT mean three-plugin integration.

### Acceptance-record docs commit

Task: `DT-CORE-3B-ACCEPT-001`

Canonical Core snapshot immediately before current Phase 4 work:

`6ef4cde7afaad369b65ee3b2668869fb68884c1f`

This docs-only commit records Phase 3A-2 and Phase 3B as accepted and cleans stale `awaiting review` current-truth language.

At handoff creation time, GitHub `agent/multi-asset-studio` was independently verified at exactly this SHA.

---

## 9. Current active task at handoff time

### `DT-CORE-4-001` — Phase 4 Candidate Asset Pack + Multi-option Edit Map

Assigned to:

**Forge (T1)**

Status at handoff snapshot:

**RUNNING locally / no new remote commit visible yet at the last verification**

Canonical starting SHA:

`6ef4cde7afaad369b65ee3b2668869fb68884c1f`

Forge's first attempt did NOT implement Phase 4. It drifted into a global project-summary/task-selection mode, mixed unrelated project context into the session, and asked the Owner to select A/B/C. Nexus independently verified that GitHub remained unchanged at `6ef4cde...`; no rollback was required.

Forge then received an `EXECUTION_RECOVERY` instruction telling it to resume ONLY `DT-CORE-4-001`, isolate the DeepTalk project, stop asking the Owner to choose another task, and execute the original Phase 4 scope.

The Owner reported that Forge is currently still running that recovered Phase 4 task while this session handoff is being created.

### Phase 4 product goal

Create creator-facing additive V2 delivery:

- `candidate-asset-pack/1`
- `candidate-edit-map/1`

from existing `candidate-portfolio/1` machine truth.

Only candidates satisfying:

`raw candidate_status == READY` **AND** `core_acceptance == ACCEPTED`

may appear in creator-facing delivery.

Machine history must retain excluded READY/Core-REJECTED, QA_REJECTED, FAILED, BLOCKED, UNAVAILABLE, ABSTAIN/no-call, disabled and policy-gated evidence.

### Expected Phase 4 modules

- `src/deeptalk_studio/candidate_pack_workflow.py`
- `src/deeptalk_studio/candidate_edit_map.py`

Do not modify/replace V1 `asset_pack_workflow.py`, `visual-asset-manifest/1`, `edit-map/1`, or `finished-cut-review/1` semantics.

### Expected Phase 4 behaviors

- opportunity-centred JSON
- repeated opportunity rows allowed in CSV
- Markdown grouped by Visual Opportunity
- show real A-roll window, visual purpose/reason, family, duration, suggested placement, preview/media reference, QA, review order
- review order is only browse/review order, never a winner rank
- explicit creator language: use none / one / multiple
- overlapping candidates legal
- different durations legal
- multiple families legal
- zero deliverable candidates legal; do not fabricate KEEP_A_ROLL
- creator outputs exclude plugin-internal implementation/debug metadata
- immutable media staging preserves bytes and SHA
- no overwrite, traversal, containment or symlink weakening

### Phase 4 forbidden scope

- Phase 5
- enabling all three real plugins
- three-plugin generation
- real Episode
- automatic winner selection
- cross-family scoring
- overlap resolution
- NLE project generation
- A-roll modification
- finished video generation
- release/tag/main merge

### Phase 4 acceptance workflow for the next Nexus

If current Core branch has advanced beyond `6ef4cde...`:

1. Confirm new HEAD descends from `6ef4cde...` without unexpected history rewrite.
2. Identify the exact `DT-CORE-4-001` implementation commit(s).
3. Compare `6ef4cde...` to exact head.
4. Inspect new modules, tests, docs and `.gitignore` if changed.
5. Verify no plugin repo was modified by this Core task.
6. Verify creator projection includes only raw READY + Core ACCEPTED.
7. Verify machine portfolio history is preserved.
8. Verify zero/one/many, overlap, duration and multi-family semantics.
9. Verify immutable staging, SHA preservation, no overwrite, traversal and symlink safety.
10. Verify Markdown/CSV/JSON contain no winner semantics.
11. Verify V1 Asset Pack/Edit Map/Finished Cut Review compatibility tests remain green.
12. Check GitHub combined CI/status separately from Agent-local test claims.
13. If clean: `DT-CORE-4-001 → PASS / ACCEPTED / IMPLEMENTED_UNRELEASED` at exact reviewed SHA.
14. If important defect exists: issue a narrow `CORRECTION-1` prompt to Forge; do not ask Owner to choose a technical solution.

If the branch is still `6ef4cde...`, then Forge has not pushed Phase 4 yet. Do not invent completion; wait for the Owner's completion signal or use a minimal status probe only if needed.

---

## 10. What comes after Phase 4

Do NOT start this until Phase 4 has been independently Nexus-reviewed and accepted.

Accepted implementation plan next relevant gate:

### Phase 5 — Three-plugin synthetic integration and compatibility hardening

Goal: prove the accepted multi-repo non-exclusive model against all three configured real runners with sanitized synthetic opportunities.

Dependencies include accepted Phase 3A, accepted Phase 3B and completed creator Candidate Pack delivery.

Likely staffing recommendation after Phase 4 PASS:

- Atlas as primary single writer for high-risk Core/cross-repo integration.
- Forge/Scribe idle unless Nexus identifies a truly independent read-only or separate-repo task.
- Do not force parallelism.

Phase 5 should verify exact checkout/version/clean-tree configuration for all three plugins and then perform actual three-plugin synthetic integration without real Episode data.

No automatic winner semantics are allowed in Phase 5 either.

---

## 11. Canonical documents to read

On current exact Core HEAD, read in this order:

1. `PROJECT_STATE.md` — current canonical product/project truth
2. `docs/INDEX.md` — document ownership/reading order
3. `docs/plans/2026-08-28-multi-asset-implementation-plan.md` — accepted phased implementation plan
4. `docs/plans/2026-08-28-visual-asset-plugin-contract-v1.md` — accepted Contract V1 design
5. `HANDOFF.md` — chronological evidence/history, not canonical current truth
6. `CHANGELOG.md` — implementation history

Do not treat old plan baselines or historical handoff statements as current truth when they conflict with current `PROJECT_STATE.md` and current exact code.

---

## 12. Review discipline

For every Agent completion:

- review exact remote SHA, never `latest`
- verify parent/lineage
- compare against exact accepted base
- inspect source, not only commit message
- inspect tests, not only test count claims
- distinguish local test claims from GitHub CI/status
- use `PASS / NEEDS_CORRECTION / HOLD` as review result
- only Nexus may convert implementation into project-level acceptance
- no merge/tag/release unless explicitly in scope

Agent completion is not acceptance.

---

## 13. Prompt discipline

Formal engineering prompts should be one complete reusable block and normally include:

- Task ID
- Agent assignment
- exact repo/branch/base SHA
- unique objective
- confirmed facts
- allowed scope
- prohibited scope
- ordered implementation steps
- executable acceptance criteria
- validation commands
- commit/push requirements
- exact-SHA completion format

Do not fragment the prompt across multiple messages.

Do not ask the Owner to make default technical choices that Nexus should decide.

---

## 14. Snapshot summary

At the instant this handoff was authored:

- Core canonical branch last verified remote HEAD: `6ef4cde7afaad369b65ee3b2668869fb68884c1f`
- Phase 3A-2: ACCEPTED / IMPLEMENTED_UNRELEASED
- Phase 3B: ACCEPTED / IMPLEMENTED_UNRELEASED
- MG: ACCEPTED / PINNED / IMPLEMENTED_UNRELEASED at `7ae59f1115da8a011113c81f31d320783b0ce8a4`
- Illustrated runner accepted at `48848affe018fc2cff8ee15bad7a09bb002776e4`
- Hand-drawn runner accepted at `67698fd8ea09109ff91c912f51e4c2d4f0b8482f`
- all three Core plugin entries disabled
- Phase 4 `DT-CORE-4-001`: Forge actively executing after execution-recovery correction; no new remote Phase 4 commit had been observed at last verification
- next Nexus action: inspect latest GitHub state, then review Phase 4 if Forge has pushed it
- do not ask Owner to re-explain this history

---

## 15. Required recovery ACK

After recovery, the new Nexus must comment on the Recovery Issue using a concise record similar to:

```text
PROJECT_RECOVERED
ROLE: Nexus
CORE_BRANCH: agent/multi-asset-studio
CORE_HEAD: <current full SHA>
HANDOFF_BASE: 6ef4cde7afaad369b65ee3b2668869fb68884c1f
CURRENT_TASK: <task id/state>
NEXT_ACTION: <concise action>
GITHUB_VERIFIED: YES
```

This ACK is a session-transfer audit marker only. It is not a merge, release, or implementation acceptance by itself.
