# Plugin Repository Governance Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize plugin repository governance so each plugin `main` exposes its latest accepted stable runtime and every future plugin Curator inherits shared engineering standards while preserving DeepTalk insertability.

**Architecture:** Keep DeepTalk Core release/development branch semantics unchanged. Treat each visual plugin as an independent repository whose `main` is plugin-local accepted runtime; perform optimization on task branches and require a separate DeepTalk Nexus integration gate before Core repin.

**Tech Stack:** Git/GitHub, Markdown governance docs, existing plugin runners, `HWang0310/engineering-journal` standards.

**Spec:** `docs/superpowers/specs/2026-09-02-plugin-repository-governance-design.md`

## Global Constraints

- Task ID: `DT-GOV-PLUGIN-001`.
- Engineering standards source: `HWang0310/engineering-journal`; governance baseline `35fc8ef9e4c09a86907efd6e14d772d306451ca7`.
- No renderer behavior changes.
- No plugin Contract semantic changes.
- No dependency upgrades.
- No DeepTalk Core runtime changes.
- No Phase 6 acceptance decision.
- No force push, tag, or release.
- Restricted-content hard gate applies to all newly written project-controlled content.

---

### Task 1: Normalize MG repository

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/DEEPTALK-INTEGRATION.md`
- Update durable state: repository Issue #1

**Interfaces:**
- Consumes: accepted MG SHA `7ae59f1115da8a011113c81f31d320783b0ce8a4`; runner `node scripts/contract-runner.js`.
- Produces: governed MG `main` exact SHA and Recovery Issue pointing to current `main`.

- [ ] Reconfirm `main..7ae59f...` is fast-forward only.
- [ ] Fast-forward MG `main` to `7ae59f...` with `force=false`.
- [ ] Create `governance/plugin-pm-bootstrap` from the new `main`.
- [ ] Update `AGENTS.md` to require engineering-journal bootstrap while retaining MG-specific deterministic rendering and visual-review rules.
- [ ] Add a visible `Current Accepted Runtime` section to `README.md`.
- [ ] Add `docs/DEEPTALK-INTEGRATION.md` defining Contract V1 compatibility and handback to DeepTalk Nexus.
- [ ] Review exact governance SHA and confirm only governance/docs changed.
- [ ] Fast-forward MG `main` to the governance SHA with `force=false`.
- [ ] Update MG Issue #1 to use governed `main` as the optimization base.

### Task 2: Normalize Illustrated Metaphor repository

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/DEEPTALK-INTEGRATION.md`
- Update durable state: repository Issue #1

**Interfaces:**
- Consumes: accepted Illustrated SHA `48848affe018fc2cff8ee15bad7a09bb002776e4`; runner `python3 scripts/contract_runner.py`.
- Produces: governed Illustrated `main` exact SHA and Recovery Issue pointing to current `main`.

- [ ] Reconfirm `main..48848af...` is fast-forward only.
- [ ] Fast-forward Illustrated `main` to `48848af...` with `force=false`.
- [ ] Create `governance/plugin-pm-bootstrap` from the new `main`.
- [ ] Update `AGENTS.md` to require engineering-journal bootstrap while retaining provenance, deterministic render, and metaphor-specific rules.
- [ ] Add a visible `Current Accepted Runtime` section to `README.md`.
- [ ] Add `docs/DEEPTALK-INTEGRATION.md` defining Contract V1 compatibility and handback to DeepTalk Nexus.
- [ ] Review exact governance SHA and confirm only governance/docs changed.
- [ ] Fast-forward Illustrated `main` to the governance SHA with `force=false`.
- [ ] Update Illustrated Issue #1 to use governed `main` as the optimization base.

### Task 3: Normalize Hand-drawn Animation repository

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/DEEPTALK-INTEGRATION.md`
- Update durable state: repository Issue #1

**Interfaces:**
- Consumes: accepted Hand-drawn SHA `853618bdf19ae66ec393211b77d970911f53f4bc`; runner `node src/contract-runner.js`.
- Produces: governed Hand-drawn `main` exact SHA, explicit real-generation blocker, and Recovery Issue pointing to current `main`.

- [ ] Reconfirm `main..853618b...` is fast-forward only.
- [ ] Fast-forward Hand-drawn `main` to `853618b...` with `force=false`.
- [ ] Create `governance/plugin-pm-bootstrap` from the new `main`.
- [ ] Update `AGENTS.md` to require engineering-journal bootstrap while retaining deterministic SVG-first and test-first rules.
- [ ] Add a visible `Current Accepted Runtime` section to `README.md` and explicitly surface the Phase 6 generation-completeness blocker.
- [ ] Add `docs/DEEPTALK-INTEGRATION.md` defining Contract V1 compatibility, final-media/manifest requirement, and handback to DeepTalk Nexus.
- [ ] Review exact governance SHA and confirm only governance/docs changed.
- [ ] Fast-forward Hand-drawn `main` to the governance SHA with `force=false`.
- [ ] Update Hand-drawn Issue #1 to use governed `main` as the optimization base and preserve blocker-first sequencing.

### Task 4: Close the cross-repository governance loop

**Files / durable records:**
- Update: DeepTalk Issue #3
- Update: DeepTalk Issue #4

**Interfaces:**
- Consumes: final governed `main` SHAs for all three plugins.
- Produces: one canonical plugin governance index for future DeepTalk and plugin Curator sessions.

- [ ] Verify all three plugin default branches now resolve to governed accepted runtime commits.
- [ ] Reconfirm no force pushes, runtime changes, tags, releases, or Core changes occurred.
- [ ] Record final governed plugin `main` SHAs and Recovery Issue links in DeepTalk Issue #3.
- [ ] Record `PASS / ACCEPTED` evidence in Issue #4 and close it only after exact-SHA verification.
- [ ] Leave Phase 6 owner-demo branch and acceptance state untouched.
