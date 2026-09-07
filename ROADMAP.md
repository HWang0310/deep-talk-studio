---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '9041f851-2e1b-4e27-90eb-7d9d8697554d'
  PropagateID: '9041f851-2e1b-4e27-90eb-7d9d8697554d'
  ReservedCode1: 'e55ebfc4-6131-4cce-9e2f-d0f1f867b135'
  ReservedCode2: 'e55ebfc4-6131-4cce-9e2f-d0f1f867b135'
---

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

### Visual Asset Plugin Contract V1 — accepted architecture; Phase 5 awaiting acceptance

- Contract V1 is ACCEPTED_UNRELEASED architecture. Phase 0's strict validators, sanitized fixtures, test-only fake runner, and static configuration examples are ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation.
- Preserve the accepted multi-repo, plugin-first boundary. Phases 0–3B are ACCEPTED / IMPLEMENTED_UNRELEASED. Phase 4 Candidate Asset Pack + Multi-option Edit Map is ACCEPTED / IMPLEMENTED_UNRELEASED at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`.
- Core relocation-safe artifact resolution is ACCEPTED / IMPLEMENTED_UNRELEASED: runtime resolution validates configured trusted historical roots, canonical artifact-relative identity, containment, symlink rejection, file existence, byte size, and SHA-256. Historical manifests are preserved. Current Production selection is explicit via machine-local `current_production_id`; filesystem mtime is no longer semantic truth. A formal immutable current-production index remains deferred.
- Phase 5 real three-plugin synthetic integration is **ACCEPTED / IMPLEMENTED_UNRELEASED**. It preserves MG `7ae59f1115da8a011113c81f31d320783b0ce8a4` and Illustrated `48848affe018fc2cff8ee15bad7a09bb002776e4`, and uses the accepted Hand-drawn correction `853618bdf19ae66ec393211b77d970911f53f4bc`. It proves deterministic order, failure isolation, Portfolio/Pack/map delivery, and minimum creator usability with sanitized opportunities only. Production adoption remains unstarted.

## Approved Next

### Multi-Asset Candidate Architecture — accepted direction; partially implemented, unreleased

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio
→ Candidate QA → Candidate Asset Pack → Multi-option Edit Map
→ creator manual NLE selection
```

- Candidates are non-exclusive and may overlap.
- The accepted ecosystem is multi-repo and plugin-first: independent visual families evolve behind a minimal Core contract rather than being absorbed into Core internals.
- V2 removes `KEEP_A_ROLL` from new candidate planning but preserves V1 compatibility readers/adapters.
- `REAL_MATERIAL` stays an independent evidence/documentary family.
- Visual Asset Plugin Contract V1 is ACCEPTED_UNRELEASED architecture. Accepted implementation now extends through Phase 4; Phase 5's real three-plugin synthetic path is **ACCEPTED / IMPLEMENTED_UNRELEASED**. Production migration, production enablement, and real-Episode validation have not started. Phase 6 (《牛来》 Owner-visible Micro Demo) is **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** on branch `agent/phase6-niulai-owner-demo` at `b72b7c2`.

### MG Quality V2

- Approved next; not implemented.
- Improve visual quality and art direction before increasing MG output volume.

## Accepted Product Architecture V2 — Owner-Approved Direction, Design Awaiting Nexus Review

The Owner-approved [Product Architecture V2](docs/plans/2026-09-07-product-architecture-v2.md) is **OWNER_APPROVED_DIRECTION / AWAITING_NEXUS_ARCH_REVIEW**. The Owner has approved the product direction (WHERE→WHAT→WHEN, Visual Director decomposition, REAL_MATERIAL plugin migration, plugin unification, HOW deferred). The specific architecture design (migration matrix, adapter strategy, Contract V2 proposal, Placement Planner details, phased plan) has not yet received Nexus PASS. No runtime, schema, or code implementation has started. It does not change the status of any implemented work above.

Key V2 directions:

- **WHERE → WHAT → WHEN separation**: Visual Opportunity Detection (WHERE) is a Studio Host capability; Asset Plugins (WHAT) are non-exclusive; Placement Planner (WHEN) is a separate Studio Host capability.
- **V1 Visual Director decomposition**: SPLIT into Visual Opportunity Detection + Asset Plugin orchestration + Candidate aggregation/QA + Placement Planning. V1 `visual-director-plan/1` preserved via compatibility reader.
- **REAL_MATERIAL plugin migration**: MIGRATE from V1 Visual Director decision to standard Real Material Asset Provider, retaining all provenance/rights/factual/inspection obligations.
- **Plugin unification**: MG, Illustrated, Hand-drawn, and REAL_MATERIAL all become standard Asset Plugins. No Core-special status.
- **Contract migration**: `suggested_placement` identified as WHAT/WHEN coupling. Future contract version separates `intrinsic_placement_hint` from Placement Planner. Legacy artifacts remain immutable.
- **HOW deferred**: Presentation style (PIP, split, zoom, overlay, transition) is not in V2 Phase 1.

Implementation is phased (Phase A–F) with compatibility-first, no big-bang rewrite, and each phase independently reversible. See the [design document](docs/plans/2026-09-07-product-architecture-v2.md) §6 for the phased plan.

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