---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '99333279-4ec1-4251-9a73-36d1c5be02ba'
  PropagateID: '99333279-4ec1-4251-9a73-36d1c5be02ba'
  ReservedCode1: 'f4013805-fb4e-44e0-96f8-5038fe0cd524'
  ReservedCode2: 'f4013805-fb4e-44e0-96f8-5038fe0cd524'
---

# DeepTalk Studio Product Requirements

> **Canonical owner:** current accepted product requirements and hard boundaries. Read [PROJECT_STATE.md](PROJECT_STATE.md) first for release/development state, and [ROADMAP.md](ROADMAP.md) for status classification. Historical milestones appear at the end; they do not override Parts A–D.

## Part A — Current Product

### Product purpose

DeepTalk Studio serves creators making human-led, deep spoken videos. It turns a defensible topic into a reviewed script and then prepares evidence-bound visual material with precise placement suggestions against the creator's final clean A-roll.

The product is successful when:

- a Reviewed Script is worth recording;
- an Asset Pack contains material the creator genuinely wants to use; and
- the creator understands where each material could fit against real A-roll.

It is not successful merely because a complete video can be generated.

### Users and roles

| Role | Responsibility |
|---|---|
| Creator / user | Content judgment, human confirmation, recording, final material selection, and final NLE aesthetic decisions. |
| ChatGPT | Product manager, architect, and reviewer. |
| Codex | Engineer and operator. |

### Implemented V1 workflow — accepted, unreleased

```text
Topic Discovery / Topic
→ Research → independent Fact Check
→ Content Thesis → human thesis confirmation
→ Reviewed Script
→ Final Clean A-roll → local ASR → Alignment → Semantic Timeline
→ V1 Visual Director → asset generation and individual QA
→ Asset Pack + Edit Map → creator manual NLE assembly
→ Finished Cut Review + Production Feedback
```

Requirements:

- Research must retain source provenance, fact status, counter-evidence, uncertainty, and an independent fact-check step.
- A Content Thesis must pass its gate and receive ordinary-language human confirmation before Script V1 is created.
- Reviewed Script must pass factual safety and Script Quality Gates; approval does not create an A-roll or start visual work.
- Only Final Clean A-roll can supply production timing. Script estimates, draft timings, and fixtures cannot become final placement time.
- Local ASR and alignment fail closed on missing, out-of-range, or overlapping timing evidence.
- Material, rights, factual binding, asset QA, and immutable lineage remain required.
- Asset Pack plus Markdown Edit Map is the creator-facing delivery. CSV supports lookup/sorting; JSON is the machine contract.
- Finished Cut Review may observe plan/actual use, timing deviation, shortening/extension, and presentation changes. It remains read-only, non-judgmental, and cannot change the finished cut.

### Current V1 visual semantics

V1 uses one decision per real semantic span: `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, or `ADVANCED_MOTION`. `KEEP_A_ROLL` is a legitimate historical and current V1 artifact. `REAL_MATERIAL` is evidence/documentary material, not a generated-family substitute.

Historical full-video/Aligned Preview remains a compatibility, QA, and optional preview capability. It is not the primary delivery or a promise of a finished video.

## Part B — Hard Product Boundaries

DeepTalk must not:

- automatically select takes, remove pauses/re-records, delete or alter A-roll, splice human speech, or substitute a synthetic presenter;
- select a final visual winner, resolve overlap, choose a track, or decide a creator's final material;
- generate 剪映/NLE projects, automatically assemble/finalise a video, output a final cut, or publish;
- use generated image/animation as documentary evidence, fabricate source/provenance, weaken rights review, or invent real timing;
- treat one episode's feedback as an automatic global product rule;
- claim Xiaohei as DeepTalk-owned IP or bind DeepTalk's long-term identity to a third-party character.

A-roll is the creator's base layer. DeepTalk contributes optional material and placement guidance, not an autonomous edit.

## Part C — Current V1 Candidate / Accepted Unreleased

The following are implemented in the repository and accepted on the V1 Candidate path, but are **not a formal release**:

- Topic Discovery, Research, independent Fact Check, and approval gates.
- Content Director + Script Agent V1, including Content Thesis, human confirmation, reviewed script, and quality checks.
- Final Clean A-roll gate, local `whisper.cpp` `large-v3` ASR, global monotonic alignment, and Semantic Timeline.
- V1 Visual Director, material/asset QA, Asset Pack + Edit Map, and Finished Cut Review + Production Feedback.

The latest formal release remains `v0.6.1`. “Implemented” never means “released.”

## Part D — Accepted Next and Experiments

### Multi-Asset Studio — accepted direction; partially implemented, unreleased

The accepted target abstraction is:

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio
→ family-specific Candidate Asset Generation → Candidate QA
→ Candidate Asset Pack → Multi-option Edit Map → creator manual NLE selection
```

Implementation status of this direction is **partially implemented, unreleased**: Core Phases 0–3B, Core Phase 4 (Candidate Asset Pack + Multi-option Edit Map), and Core Phase 5 (real three-plugin synthetic integration) are all ACCEPTED / IMPLEMENTED_UNRELEASED. **Production migration has not started and the production default is not enabled.** This is distinct from the implementation not existing: the implementation exists on accepted branches and is deliberately not production-enabled.

Requirements (govern the accepted target; production adoption remains unstarted):

- DeepTalk Visual Asset Ecosystem is multi-repo and plugin-first: Core remains stable while each visual family is independently researched, optimized, benchmarked, QA'd, and versioned as a Visual Asset Plugin.
- Candidate assets are non-exclusive. Multiple candidates can overlap fully or partly, have different durations, and come from different families.
- `suggested_review_order` (or equivalent) may tell a creator what to inspect first; it must never mean that the machine chose a winner.
- No Visual Opportunity means no additional asset. New candidate planning removes `KEEP_A_ROLL` as an outcome, but V1 readers/adapters and immutable historical lineage remain compatible.
- `REAL_MATERIAL` remains an independent evidence/documentary family. Generated explanation families do not replace it.
- Machine records must preserve Generation outcomes (`COMPLETED`, `FAILED`, `BLOCKED`, `UNAVAILABLE`) separately from produced Candidate outcomes (`READY`, `QA_REJECTED`). Creator-facing packs default to READY candidates only. Contract V1 is ACCEPTED_UNRELEASED architecture; production-schema adoption and production migration are not started.
- The product maximises useful choice density, not file count. LEAN/STANDARD/RICH are soft profiles only; no fixed opportunity/candidate count is a schema invariant.

The evidence-derived [`Visual Asset Plugin Contract V1 design`](docs/plans/2026-08-28-visual-asset-plugin-contract-v1.md) is the accepted minimum two-stage suitability/generation architecture. Its [Multi-Asset Implementation Plan](docs/plans/2026-08-28-multi-asset-implementation-plan.md) is accepted.

Implementation status on the accepted path:

- Core Phases 0–2 are ACCEPTED / IMPLEMENTED_UNRELEASED.
- Core Phase 3A-2 (one accepted, exact-pinned MG runner on the synthetic portfolio path) is **ACCEPTED / IMPLEMENTED_UNRELEASED** — its review is complete and it is no longer pending.
- Core Phase 3B is ACCEPTED / IMPLEMENTED_UNRELEASED.
- Core Phase 4 — Candidate Asset Pack + Multi-option Edit Map — is **ACCEPTED / IMPLEMENTED_UNRELEASED** at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`. Candidate delivery has therefore begun and is implemented.
- Core Phase 5 — real three-plugin synthetic integration — is **ACCEPTED / IMPLEMENTED_UNRELEASED** at `db172cecc60ca6b0c276ec42010b113a767bc7b3`. Multi-plugin integration has therefore begun and is implemented.
- V2 production migration and production adoption have **not** begun: no production schema adoption, no production default, no production Episode, no release, and static plugin config remains disabled.
- Phase 6 (《牛来》 Owner-visible Micro Demo) is **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** — the demo is complete but held; it is not PASS, ACCEPTED, MERGED, PRODUCTION, or RELEASED.
- Product Architecture V2 is **Owner-approved product direction**; its specific architecture design is **AWAITING_NEXUS_ARCH_REVIEW** and has no runtime implementation. See Part E.

### Approved next / experimental work

| Direction | Status | Requirement boundary |
|---|---|---|
| MG Quality V2 | Approved next; not implemented | Improve art direction, composition, typography, hierarchy, motion grammar, easing, transitions, primitives, and density before increasing volume. |
| Hand-drawn Animation | Approved V1 experiment | Not an implemented production renderer. |
| Xiaohei | Prototype / experimental | Upstream is static illustration/shot-list oriented, not a ready video system; preserve licence/attribution and do not claim IP ownership. |
| Original DeepTalk visual identity | Undecided | Do not assume an original character exists. |

## Part E — Product Architecture V2 — Owner-Approved Direction, Design Awaiting Nexus Review

DeepTalk's Owner-approved product architecture direction is documented in [Product Architecture V2](docs/plans/2026-09-07-product-architecture-v2.md). The Owner has approved the product direction (WHERE→WHAT→WHEN, Visual Director decomposition, REAL_MATERIAL plugin migration, plugin unification, HOW deferred, creator authority). The specific architecture design (migration matrix, adapter strategy, Contract V2 proposal, Placement Planner details, phased implementation plan) is **AWAITING_NEXUS_ARCH_REVIEW** — it has not yet received Nexus PASS. No runtime, schema, or code implementation has started. This section records the product direction; it does not change Parts A–D or override the implemented V1 workflow.

### WHERE → WHAT → WHEN separation

V2 separates visual work into three independent stages:

- **WHERE** (Visual Opportunity Detection): a Studio Host capability that determines where visual assistance is worth adding and for what purpose. It does not decide which visual family to use.
- **WHAT** (Asset Plugins): each plugin independently assesses suitability (SUITABLE / BORDERLINE / ABSTAIN) and generates candidates when requested. No plugin has Core-special status. Plugins include REAL_MATERIAL, MG, Illustrated Metaphor, Hand-drawn, and future families (Chart, Map, AI Video).
- **WHEN** (Placement Planner): a separate Studio Host capability that produces per-candidate placement recommendations, distinct from opportunity time windows.

### V1 Visual Director decomposition

The V1 Visual Director (current implemented, single-decision central planner) is **decomposed, not deleted**: WHERE → Visual Opportunity Detection, WHAT → Asset Plugin orchestration, WHEN → Placement Planner, candidate aggregation/QA → Studio Host. V1 `visual-director-plan/1` artifacts are preserved through compatibility readers. The V1 Visual Director remains implemented and operational.

### REAL_MATERIAL plugin migration

REAL_MATERIAL migrates from a V1 Visual Director decision to a standard Real Material Asset Provider plugin. All existing obligations — source provenance, rights/reuse review, factual binding, Evidence/Context/Illustration classification, capture metadata, inspection evidence, `research_update_required`, material QA, immutable lineage — are preserved. This is a responsibility migration, not a safety subsystem rewrite.

### Plugin unification

MG, Illustrated Metaphor, Hand-drawn, and REAL_MATERIAL all become standard Asset Plugins under the same contract boundary. None has Core-special status. Core does not depend on plugin internals. The Candidate Portfolio, Candidate QA, Candidate Asset Pack, and Multi-option Edit Map mechanisms are retained.

### Contract migration

`suggested_placement` in `visual-asset-plugin-contract/1` is identified as a WHAT/WHEN coupling. A future contract version will separate `intrinsic_placement_hint` from Placement Planner-owned placement. Legacy artifacts remain immutable and readable through adapters. No existing artifact is rewritten.

### HOW deferred

Presentation style (PIP, split screen, zoom, crop, overlay, transition) is explicitly **not** in V2 Phase 1 scope.

### Creator authority

The creator retains final video decisions: none, one, or multiple candidates per opportunity. No automatic winner selection, overlap resolution, final material choice, A-roll modification, NLE generation, or publishing.

This is a design document only. The Owner has approved the product direction; the specific design awaits Nexus architecture review. `Plan exists ≠ accepted; implemented ≠ released.`

## Part F — Historical Milestones

These milestones preserve lineage; their earlier success criteria are not automatically current requirements.

- **v0.1–v0.4.1:** research, fact check, topic discovery, original-script workflow, and gate hardening.
- **v0.5–v0.5.1:** material search, provenance/rights safeguards, and material gate hardening.
- **v0.6–v0.6.1:** Motion Production Layer and formal release.
- **V1 Candidate:** A-roll alignment, visual planning, Asset Pack + Edit Map, Finished Cut Review, and real-episode validation.
- **Historical preview path:** rough/full preview output provided valuable QA evidence but is no longer the primary creator outcome.

For detailed historical work, use [HANDOFF.md](HANDOFF.md), [CHANGELOG.md](CHANGELOG.md), [docs/releases](docs/releases/), and [docs/superpowers](docs/superpowers/).