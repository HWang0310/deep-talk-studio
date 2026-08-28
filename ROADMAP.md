# DeepTalk Studio Roadmap

> **Canonical owner:** delivery-state classification. Read [PROJECT_STATE.md](PROJECT_STATE.md) first. A plan or a branch is not a release; an implementation is not a release.

## Released

### v0.6.1 — Formal Release

- Released at `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`.
- Includes the Motion Production Layer: reviewed-material safety, renderer adapters, actual MP4 QA, and release evidence.
- Earlier releases (`v0.1.0` through `v0.6.0`) remain documented in [docs/releases](docs/releases/) and [CHANGELOG.md](CHANGELOG.md).

## Accepted / Implemented / Unreleased

### V1.0 Candidate

- Topic discovery, Research, independent Fact Check, and approval lineage.
- Content Director + Script Agent V1, including Content Thesis, human confirmation, and reviewed-script quality gates.
- Final Clean A-roll, local `whisper.cpp` `large-v3` ASR, global monotonic alignment, Semantic Timeline, and timing safeguards.
- V1 Visual Director, asset generation/QA, Asset Pack + Edit Map, manual creator NLE assembly, and read-only Finished Cut Review / Production Feedback.
- No later tag or GitHub Release exists: this remains **V1.0 Candidate — Unreleased**.

## Current Validation

### 《牛来》 — first complete real production loop

- Completed local A-roll through Finished Cut Review / Production Feedback.
- 25 spans: 22 `KEEP_A_ROLL`, 3 MG; all three MG assets were used but shortened.
- Validates real A-roll timing, Edit Map usefulness, and creator-owned final editing.
- Reveals insufficient MG quantity/quality and plan-versus-actual window differences.
- Findings are episode evidence, not self-executing global policy.

### 《恒大》 — ready for recording

- Competitive Research, Fact Check, Content Thesis, human confirmation, and Final Reviewed Script are complete.
- Status is **READY_FOR_RECORDING**. A-roll, assets, and editing have not started.

## Current Work

### Visual Asset Plugin Contract V1 — accepted architecture

- Contract V1 is ACCEPTED_UNRELEASED architecture, integrated as canonical design documentation only.
- Preserve the accepted multi-repo, plugin-first boundary; do not start runtime implementation or schema adoption.
- The [separate Multi-Asset Implementation Plan](docs/plans/2026-08-28-multi-asset-implementation-plan.md) is accepted. Runtime implementation and schema adoption remain unstarted; the next gate is Phase 0 (Contract fixtures + frozen V1 compatibility baseline) in a separate implementation session, branch, and review.

## Approved Next

### Multi-Asset Candidate Architecture — accepted direction; implementation not started

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio
→ Candidate QA → Candidate Asset Pack → Multi-option Edit Map
→ creator manual NLE selection
```

- Candidates are non-exclusive and may overlap.
- The accepted ecosystem is multi-repo and plugin-first: independent visual families evolve behind a minimal Core contract rather than being absorbed into Core internals.
- V2 removes `KEEP_A_ROLL` from new candidate planning but preserves V1 compatibility readers/adapters.
- `REAL_MATERIAL` stays an independent evidence/documentary family.
- Visual Asset Plugin Contract V1 is ACCEPTED_UNRELEASED architecture. The implementation plan is accepted; V2 runtime schemas, migration, and product code have not started. Phase 0 is the next gate and must begin in a separate implementation session, branch, and review.

### MG Quality V2

- Approved next; not implemented.
- Improve visual quality and art direction before increasing MG output volume.

## Experimental / Under Product Validation

- **Hand-drawn Animation V1:** approved experiment, not a renderer.
- **Xiaohei:** third-party prototype/experimental reference; no claim of DeepTalk IP and no long-term identity commitment.
- **Candidate density:** soft LEAN/STANDARD/RICH profiles; current creator prefers RICH, but no fixed counts or hard schema rules.
- **Original DeepTalk character / visual identity:** undecided.

## Deferred / Not Planned

- Automatic final editing, automatic candidate choice, or visual-overlap resolution.
- Take choice, A-roll deletion/cleanup, pause/re-record removal, retiming, or human-speech splicing.
- 剪映/NLE project generation, final-cut output, automatic publishing, TTS/fake presenter, BGM/SFX, cover/title automation, or engagement prediction.
- Treating a single episode as sufficient evidence to rewrite global aesthetic policy.

## Historical Milestones

- v0.1–v0.4.1: research, fact check, topic discovery, script workflow, and gate hardening.
- v0.5–v0.5.1: material provenance, rights, and review gates.
- v0.6–v0.6.1: Motion Production Layer and formal release.
- Historical rough/full preview paths: preserved for compatibility and QA, not the current primary UX.
