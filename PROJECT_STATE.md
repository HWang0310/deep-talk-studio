---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '1a8d7895-0676-44a2-acc3-eebb40a53e04'
  PropagateID: '1a8d7895-0676-44a2-acc3-eebb40a53e04'
  ReservedCode1: '8e6110d3-a684-4a21-b60d-05f39974740e'
  ReservedCode2: '8e6110d3-a684-4a21-b60d-05f39974740e'
---

# DeepTalk Studio — Canonical Project State

> **Read this first for current truth.** This file is the concise, canonical state of the product as of 2026-09-02. Historical evidence remains in [HANDOFF.md](HANDOFF.md), release notes, plans, and specs; those sources do not override this file.

## Identity

| Field | Current truth |
|---|---|
| Product | A content and visual-asset system for creators making human-led, deep spoken videos. |
| Latest Formal Release | [`v0.6.1`](docs/releases/v0.6.1.md), commit `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`. |
| Current Development Status | **V1.0 Candidate — Unreleased.** No later tag or GitHub Release exists. |
| Product Code Baseline | `agent/audio-alignment-edit-bridge` at accepted HEAD `4713505`. |
| Canonical Development Branch | `agent/multi-asset-studio`. The temporary `docs/project-memory-consolidation` branch remains preserved for now. |
| Current work | Visual Asset Plugin Contract V1 architecture and Phases 0–3B are ACCEPTED / IMPLEMENTED_UNRELEASED. Core Phase 4 Candidate Asset Pack + Multi-option Edit Map is ACCEPTED / IMPLEMENTED_UNRELEASED at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`. Core Phase 5 real three-plugin synthetic integration is **ACCEPTED / IMPLEMENTED_UNRELEASED**. It exact-pins MG `7ae59f1115da8a011113c81f31d320783b0ce8a4`, Illustrated Metaphor `48848affe018fc2cff8ee15bad7a09bb002776e4`, and the corrected Hand-drawn runner `853618bdf19ae66ec393211b77d970911f53f4bc`; production configuration remains disabled. Phase 6 (《牛来》 Owner-visible Micro Demo) is **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** on branch `agent/phase6-niulai-owner-demo` at `b72b7c2`. No V2 production migration, production default, release, tag, or `main` change is included. |

## Current Product Positioning

DeepTalk Studio helps a creator turn a defensible topic into a reviewed spoken script, then prepare evidence-bound visual assets and precise placement suggestions against the creator's final clean A-roll.

DeepTalk is responsible for topic discovery, research, fact check, Content Thesis, reviewed script, final-clean-A-roll semantic timing, visual-material preparation, asset QA, Asset Pack, and Edit Map. The creator retains content judgment, human confirmation, recording, final material selection, and final NLE aesthetic decisions.

### Roles

- **Creator / user:** content judgment, confirmations, human recording, and final edit selection.
- **ChatGPT:** product manager, architect, and product reviewer.
- **Codex:** engineer and operator.

## Current Accepted Workflow

### Implemented V1 path — accepted, unreleased

```text
Topic → Research → Fact Check → Content Thesis → human confirmation
→ Reviewed Script → Final Clean A-roll → local ASR → Alignment
→ Semantic Timeline → Visual Director → individual asset QA
→ Asset Pack + Edit Map → creator manual NLE assembly
→ Finished Cut Review + Production Feedback
```

- The timing source is final clean A-roll, not script estimates.
- Asset Pack and creator-facing Markdown Edit Map are the primary delivery. CSV supports finding/sorting; JSON remains the machine contract.
- Finished Cut Review is read-only and non-judgmental: it observes plan/actual differences and does not alter the cut.
- The historical full-video/Aligned Preview renderer remains compatibility, QA, and optional preview infrastructure — not primary UX or a finished-video product promise.

### Accepted V2 target — partially implemented, unreleased

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio
→ family-specific generation → Candidate QA → Candidate Asset Pack
→ Multi-option Edit Map → creator manual NLE selection
```

This is an **ACCEPTED_UNRELEASED product direction** with accepted Core foundations through Phase 4 and Phase 5 ACCEPTED / IMPLEMENTED_UNRELEASED. It is not a production schema migration or production workflow. Candidates are intentionally non-exclusive: they may overlap, have different durations, come from multiple families, and be used singly, together, or not at all.

The accepted ecosystem principle is **multi-repo, plugin-first**: Core stays stable while visual capabilities are independently researched, optimized, benchmarked, QA'd, and versioned as Visual Asset Plugins. The evidence-derived [Contract V1 design](docs/plans/2026-08-28-visual-asset-plugin-contract-v1.md) is **ACCEPTED_UNRELEASED** architecture. It is not production implementation, runtime-schema adoption, a release, a tag, or a `main` change.

### Product Architecture V2 — Owner-approved direction, design awaiting Nexus review

**Owner-approved** product architecture direction is documented in [Product Architecture V2](docs/plans/2026-09-07-product-architecture-v2.md). The Owner has approved the product direction (WHERE→WHAT→WHEN, Visual Director decomposition, REAL_MATERIAL plugin migration, plugin unification, HOW deferred, creator authority). The specific architecture design (migration matrix, adapter strategy, Contract V2 proposal, Placement Planner details, phased implementation plan) is **AWAITING_NEXUS_ARCH_REVIEW** — it has not yet received Nexus PASS. No runtime, schema, or code implementation has started.

Key V2 directions:

- **WHERE → WHAT → WHEN separation**: Visual Opportunity Detection (WHERE) is a Studio Host capability; Asset Plugins (WHAT) are non-exclusive; Placement Planner (WHEN) is a separate Studio Host capability, distinct from both opportunity windows and plugin candidates.
- **V1 Visual Director decomposition**: SPLIT into Visual Opportunity Detection + Asset Plugin orchestration + Candidate aggregation/QA + Placement Planning. V1 `visual-director-plan/1` preserved via compatibility reader.
- **REAL_MATERIAL plugin migration**: MIGRATE from V1 Visual Director decision to standard Real Material Asset Provider. All provenance, rights, factual binding, and inspection evidence obligations are preserved.
- **Contract migration analysis**: `suggested_placement` in `visual-asset-plugin-contract/1` is identified as a WHAT/WHEN coupling. A future contract version will separate `intrinsic_placement_hint` from Placement Planner-owned placement. Legacy artifacts remain immutable and readable.
- **Studio Host boundary**: Core retains episode identity, canonical timebase, artifact IDs/lineage, plugin registration, contract validation, portfolio identity, shared safety/QA, failure isolation, and packaging. Plugins own suitability, generation, internal QA, and renderer internals.
- **HOW deferred**: Presentation style (PIP, split screen, zoom, overlay, transition) is not in V2 Phase 1 scope.

This is a design document only. `Plan exists ≠ accepted; implemented ≠ released.` The Owner has approved the product direction; the specific design awaits Nexus architecture review.

## Hard Product Boundaries

DeepTalk does **not**:

- automatically choose takes or final visual winners;
- delete, clean up, shorten, retime, splice, or replace A-roll; delete pauses/re-records; or synthesize a human talking edit;
- generate a 剪映/NLE project, resolve candidate overlap, assemble a final edit, output a final finished video, or publish;
- decide which visual material a creator must use;
- treat generated illustration as documentary evidence, weaken factual/provenance/rights QA, or silently fabricate timing;
- infer a global aesthetic rule from one episode's feedback.

A-roll is always the base layer. In the accepted V2 model, absence of a Visual Opportunity simply means no extra material is generated.

## Released

- **v0.6.1:** formally released Motion Production Layer with reviewed-material safety, renderer adapters, real MP4 QA, and release evidence.

Earlier releases are historical milestones; see [CHANGELOG.md](CHANGELOG.md) and [docs/releases](docs/releases/).

## Accepted, Implemented, Unreleased

- Topic, Research, independent Fact Check, and topic discovery gates.
- Content Director + Script Agent V1: Content Thesis, human confirmation, reviewed script, and quality gates.
- Final Clean A-roll gate, local `whisper.cpp` `large-v3` ASR, global monotonic alignment, and Semantic Timeline.
- V1 Visual Director with `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, and `ADVANCED_MOTION` decisions.
- Individual asset QA, Asset Pack + Edit Map, and read-only Finished Cut Review / Production Feedback.

“Implemented” means repository code and tests exist. It does **not** mean formally released.

## Real Episode Validation

### 《牛来》 — first complete production-loop baseline

Completed locally and kept out of Git: Final Clean A-roll → local ASR → Alignment → Semantic Timeline → visual planning → asset generation → asset QA → Asset Pack → Edit Map → creator manual NLE assembly → Finished Cut → Finished Cut Review → Production Feedback.

Observed: 25 spans, including 22 `KEEP_A_ROLL` and 3 MG assets. All three MG assets were actually used, but shortened; one was visibly more useful. This validates the value of real A-roll timing, Edit Map, and creator-owned final editing. It also shows that MG quantity and quality need improvement, and that planned semantic windows differ from final creator windows. These are episode findings, **not** global automatic rules.

### 《恒大》 — script ready, recording not started

Competitive Research, Fact Check, Content Thesis, human thesis confirmation, and a Final Reviewed Script are complete. Status: **READY_FOR_RECORDING**. No A-roll production, material generation, or edit work has started.

Episode research, scripts, A-roll, assets, finished cuts, and private media stay local and gitignored. Git stores only product-level validation findings.

## Accepted but Not Yet Implemented in Production

- V2 migration away from planning new `KEEP_A_ROLL` artifacts, while retaining V1 readers/adapters and immutable lineage.
- Production migration and episode adoption of the Phase 4 Candidate Asset Pack and multi-option Edit Map semantics.
- `REAL_MATERIAL` as an independent documentary/evidence family, distinct from generated explanation families.
- Machine records distinguish Generation operation outcomes (`COMPLETED`, `FAILED`, `BLOCKED`, `UNAVAILABLE`) from produced Candidate asset outcomes (`READY`, `QA_REJECTED`); Core acceptance is separate and creator packs will default to raw READY plus Core ACCEPTED candidates only. Phase 2 implements this only through sanitized fake subprocess data, not production-schema migration.
- The `visual-asset-plugin-contract/1` design and its two-stage suitability/generation boundary are accepted. Phases 3A-2 through 4 are ACCEPTED / IMPLEMENTED_UNRELEASED. Phase 5 connects all three exact-pinned runners to the existing portfolio, Candidate Asset Pack, and `candidate-edit-map/1` synthetic path; it is **ACCEPTED / IMPLEMENTED_UNRELEASED**. No registry, production migration/default, or production episode code exists.
- Core relocation-safe artifact resolution is ACCEPTED / IMPLEMENTED_UNRELEASED. Runtime resolution validates configured trusted historical roots, canonical artifact-relative identity, containment, symlink rejection, file existence, byte size, and SHA-256. Historical manifests are preserved without rewriting. Current Production selection is explicit via machine-local `current_production_id`; filesystem mtime is no longer semantic truth. A formal immutable current-production index/pointer schema remains deferred.

## Approved Next / Experimental

- **MG Quality V2 — Approved Next, not implemented:** improve composition, typography, hierarchy, motion grammar, easing, transitions, primitive combinations, information density, template feeling, and art direction before increasing output volume.
- **Hand-drawn Animation — Approved V1 experiment:** its Contract V1 runner is exact-pinned and ACCEPTED as a disabled readiness record, but it is not a released or production-enabled renderer.
- **Xiaohei — Prototype / experimental only:** upstream is primarily a static 16:9 illustration / shot-list skill, not a ready video system. It is not DeepTalk IP. Long-term product vocabulary must remain independent, such as Illustrated Metaphor or Character Metaphor Motion.
- **Candidate density:** maximise useful choice density, not asset count. LEAN/STANDARD/RICH may remain soft creator profiles; `RICH` is a current creator preference, not a schema invariant or fixed quota.

## Known Limitations

- Current MG assets are usable but visually insufficient and too template-like.
- V1 production still makes a single visual decision per span; the additive multi-candidate architecture is not production-enabled.
- Candidate diversity and family comparison are validated only with sanitized synthetic opportunities, not a real Episode.
- `KEEP_A_ROLL` remains a real V1 artifact and historical compatibility concern; its V2 migration has not begun.

## Historical / Superseded Directions

- Full-video/rough-preview output was once framed as a primary V1 path. It is now compatibility/QA/optional preview, not current primary UX.
- Automatic final editing is not planned. Old plans and handoffs that describe preview gates or rough cuts reflect the state at their time; consult them only for lineage.
- A plan or spec is not accepted merely because it exists. Implemented work is not released merely because it exists on a branch.

## Current Next Step

The [Multi-Asset Implementation Plan](docs/plans/2026-08-28-multi-asset-implementation-plan.md) is accepted. Phase 2 is ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation: fake-only portfolio breadth, deterministic policy, Core QA, hardened immutable storage, and production directive authoring. Core relocation-safe artifact resolution is ACCEPTED / IMPLEMENTED_UNRELEASED: runtime resolution validates configured trusted historical roots, canonical artifact-relative identity, containment, symlink rejection, file existence, byte size, and SHA-256. Historical Production/Material/Capture manifests are not rewritten. Current Production may be explicitly selected by machine-local `current_production_id`; filesystem mtime is no longer semantic current-production truth. A formal immutable current-production index/pointer schema remains deferred. Machine-specific canonical repository root belongs to gitignored local config, not product invariants.

Phase 3A-1 MG is ACCEPTED / PINNED / IMPLEMENTED_UNRELEASED at exact SHA `7ae59f1115da8a011113c81f31d320783b0ce8a4`, identity `org.deeptalk.mg`, version `1.0.0-contract-v1`, and canonical runner `node scripts/contract-runner.js`. Core Phase 3A-2 is ACCEPTED / IMPLEMENTED_UNRELEASED at accepted Core SHA `990fc03922e527bef64b819cf898e4266d5669c1` (Nexus independent exact-SHA review). Its real-plugin path verifies exact HEAD, clean checkout, reported version, result identity, Contract V1, configured argv, timeout termination evidence, and Core-owned artifacts before accepting a candidate. Artifact resolution rejects the lexical output root, ancestor, or final artifact when any is a symlink before applying containment, existence, SHA-256, and duration checks.

Core Phase 3B is ACCEPTED / IMPLEMENTED_UNRELEASED at accepted implementation SHA `ec595587a378d54bd2a18270ded504707b04ddea`. Core Phase 4 Candidate Asset Pack + Multi-option Edit Map is ACCEPTED / IMPLEMENTED_UNRELEASED at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`. Phase 5 updates the independently accepted Hand-drawn revision to `853618bdf19ae66ec393211b77d970911f53f4bc` while preserving MG `7ae59f1115da8a011113c81f31d320783b0ce8a4` and Illustrated Metaphor `48848affe018fc2cff8ee15bad7a09bb002776e4`. Its real-runner synthetic evidence proves order independence, failure isolation, Portfolio/Pack/map output, and basic creator usability across the three families. Phase 5 is **ACCEPTED / IMPLEMENTED_UNRELEASED**. All static config entries remain `enabled: false`; no production enablement, real Episode, merge to the canonical branch, release, or tag exists.

### Phase 6 — Tech Demo Completed, Hold for Owner Review

Phase 6 (《牛来》 Owner-visible Micro Demo) is **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** on branch `agent/phase6-niulai-owner-demo` at `b72b7c232d24f4b1e1ac531f6f6ef0396e001c0b`. It demonstrates a complete Owner-visible micro demo with real A-roll and Contract V1 plugin output. It is not PASS, ACCEPTED, MERGED, PRODUCTION, or RELEASED. The Phase 6 verdict must not be modified.

## Read Next

1. [docs/INDEX.md](docs/INDEX.md) for reading order and document ownership.
2. [README.md](README.md) for a fast product introduction.
3. [PRD.md](PRD.md), [ROADMAP.md](ROADMAP.md), and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for canonical product, state, and architecture detail.
4. Only when needed: [HANDOFF.md](HANDOFF.md), historical plans/specs, release notes, and evaluation records.

## Memory Maintenance Rule

Update the canonical owner when truth changes. Ordinary fixes usually need only CHANGELOG and, when useful, HANDOFF. A change to product positioning, a hard boundary, primary workflow, canonical architecture, release state, validated capability, or major accepted direction must also update its owner in this file, PRD, ROADMAP, ARCHITECTURE, and README when newcomer understanding changes. Do not mechanically duplicate every fact into every Markdown file.