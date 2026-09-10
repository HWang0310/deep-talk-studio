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

### v1.0.0 Release Candidate — Pending Nexus Approval

- **One main — writing:** Topic discovery, Research, independent Fact Check, Content Thesis, human confirmation, and reviewed-script quality gates.
- **Four auxiliaries:** source-backed insert materials plus explicit MG, Illustrated Metaphor / 小黑漫画, and Hand-drawn Animation plugin invocation.
- Final Clean A-roll, local `whisper.cpp` `large-v3` ASR, global monotonic alignment, Semantic Timeline, and timing safeguards.
- V1 Visual Director, asset generation/QA, Asset Pack + Edit Map, manual creator NLE assembly, and read-only Finished Cut Review / Production Feedback.
- The release candidate is prepared on `release/v1.0.0-rc` for exact-SHA / PR review. No `v1.0.0` tag, GitHub Release, package publication, production-default change, or PR merge is part of preparation.

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

### Visual Asset Plugin Contract V1 — accepted architecture; Phase 5 ACCEPTED / IMPLEMENTED_UNRELEASED

- Contract V1 is ACCEPTED_UNRELEASED architecture. Phase 0's strict validators, sanitized fixtures, test-only fake runner, and static configuration examples are ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation.
- Preserve the accepted multi-repo, plugin-first boundary. Phases 0–3B are ACCEPTED / IMPLEMENTED_UNRELEASED. Phase 4 Candidate Asset Pack + Multi-option Edit Map is ACCEPTED / IMPLEMENTED_UNRELEASED at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`.
- Core relocation-safe artifact resolution is ACCEPTED / IMPLEMENTED_UNRELEASED: runtime resolution validates configured trusted historical roots, canonical artifact-relative identity, containment, symlink rejection, file existence, byte size, and SHA-256. Historical manifests are preserved. Current Production selection is explicit via machine-local `current_production_id`; filesystem mtime is no longer semantic truth. A formal immutable current-production index remains deferred.
- Phase 5 real three-plugin synthetic integration is **ACCEPTED / IMPLEMENTED_UNRELEASED**. It preserves MG `7ae59f1115da8a011113c81f31d320783b0ce8a4` and Illustrated `48848affe018fc2cff8ee15bad7a09bb002776e4`, and uses the accepted Hand-drawn correction `624526f4dce0ba9794c1a717fa397eb3c7a1baad`. It proves deterministic order, failure isolation, Portfolio/Pack/map delivery, and minimum creator usability with sanitized opportunities only. Production adoption remains unstarted.

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

## Product Architecture V2 — PASS / ACCEPTED; Phase A–C Integrated

The [Product Architecture V2](docs/plans/2026-09-07-product-architecture-v2.md) is **PASS / ACCEPTED**. Phase A compatibility foundations, Phase B Visual Opportunity Detection (WHERE), and Phase C Placement Planner (WHEN) are accepted, integrated, and unreleased. They do not replace the v1.0 explicit single-plugin path or change production defaults.

Key V2 directions:

- **WHERE → WHAT → WHEN separation**: Visual Opportunity Detection (WHERE) is a Studio Host capability; Asset Plugins (WHAT) are non-exclusive; Placement Planner (WHEN) is a separate Studio Host capability.
- **V1 Visual Director decomposition**: SPLIT into Visual Opportunity Detection + Asset Plugin orchestration + Candidate aggregation/QA + Placement Planning. V1 `visual-director-plan/1` preserved via compatibility reader.
- **REAL_MATERIAL plugin migration**: MIGRATE from V1 Visual Director decision to standard Real Material Asset Provider, retaining all provenance/rights/factual/inspection obligations.
- **Plugin unification**: MG, Illustrated, Hand-drawn, and REAL_MATERIAL all become standard Asset Plugins. No Core-special status.
- **Contract migration**: `suggested_placement` identified as WHAT/WHEN coupling. Future contract version separates `intrinsic_placement_hint` from Placement Planner. Legacy artifacts remain immutable.
- **HOW deferred**: Presentation style (PIP, split, zoom, overlay, transition) is not in V2 Phase 1.

Implementation is phased (Phase A–F) with compatibility-first, no big-bang rewrite, and each phase independently reversible. Phase D generated-provider orchestration migration, Phase E REAL_MATERIAL migration, and Phase F production adoption have not started and are not v1.0 capabilities. See the [design document](docs/plans/2026-09-07-product-architecture-v2.md) §6 for the phased plan.

## Experimental / Under Product Validation

- **Hand-drawn Animation quality:** the explicit v1.0 plugin path is accepted; broader style/quality evolution remains product validation.
- **Illustrated Metaphor / 小黑漫画 quality:** the explicit v1.0 plugin path is accepted; preserve licence/attribution and do not claim third-party character IP.
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
