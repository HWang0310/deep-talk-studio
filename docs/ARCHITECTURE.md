---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6a1d2587-b9df-461d-8bfa-631bc84fb1c5'
  PropagateID: '6a1d2587-b9df-461d-8bfa-631bc84fb1c5'
  ReservedCode1: '7bb9ebf4-2445-4ee5-b3fc-4d928d9d86f4'
  ReservedCode2: '7bb9ebf4-2445-4ee5-b3fc-4d928d9d86f4'
---

# DeepTalk Studio Architecture

> **Canonical owner:** current technical architecture. Read [PROJECT_STATE.md](../PROJECT_STATE.md) first. The target below is partially implemented through sanitized Phase 5 evidence, but it is not production-enabled.

## Architectural Principles

- Versioned JSON artifacts connect stages; human-readable Markdown is not the machine contract.
- Fact, source, rights, timing, digest, QA, and status decisions are program-owned and revalidated on read.
- Final Clean A-roll supplies production time. Script timing, fixtures, and inferred timestamps cannot become production truth.
- Private episode materials, media, assets, and finished cuts remain local/gitignored. Git preserves code, contracts, tests, and de-contented product evidence.
- The creator owns the final edit. Architecture may prepare assets and maps but cannot select an edit winner or alter A-roll.

## Current Implemented Architecture — V1 Candidate

```text
Topic / Topic Discovery
  → Research Report → independent Fact Check → approved Research revision
  → Content Thesis Card → Thesis Review → human confirmation
  → Reviewed Script
  → Final Clean A-roll
  → Local ASR (`whisper.cpp` large-v3) → Timed Transcript
  → Global monotonic Alignment → Semantic Timeline
  → V1 Visual Director plan
  → material / generated asset preparation → individual asset QA
  → visual-asset manifest + Asset Pack + edit-map/1
  → creator manual NLE assembly
  → finished-cut-review/1 + production-feedback/1 (read-only)
```

### Research and script system

Research preserves source provenance, claims, evidence, uncertainty, and Fact Check. Content Director consumes approved research, creates a Content Thesis Card, requires Thesis Review and human confirmation, then sends its bound inputs to Script V1. Script review independently checks factual safety and quality. Revisions are immutable and linked by IDs/digests.

Relevant contracts: [TOPIC_DISCOVERY_CONTRACT.md](TOPIC_DISCOVERY_CONTRACT.md), [SCRIPT_CONTRACT.md](SCRIPT_CONTRACT.md).

### A-roll timing and alignment

`clean_aroll_gate`, local transcription, transcript/chunk metadata, global monotonic alignment, canonical time, and semantic timeline modules establish real timing from the final clean A-roll. The production provider uses `whisper.cpp` v1.9.2 multilingual `large-v3` with `--dtw large.v3`; it retains runtime/model provenance and fails closed if token offsets are missing, invalid, or overlap. OpenAI transcription remains an optional future provider, not a silent fallback.

The Alignment/Timeline path is the bridge between reviewed semantic content and real spoken time. `FACT_CONFLICT` and missing/unsafe timing cannot become a false display placement.

Relevant contracts: [EDIT_BRIDGE_CONTRACT.md](EDIT_BRIDGE_CONTRACT.md), [ASSET_PACK_EDIT_MAP_CONTRACT.md](ASSET_PACK_EDIT_MAP_CONTRACT.md).

### V1 visual/material system

The implemented V1 Visual Director makes one decision for each real semantic span:

| Decision | Meaning |
|---|---|
| `KEEP_A_ROLL` | Keep the creator's A-roll without extra material. |
| `REAL_MATERIAL` | Documentary/evidence material subject to existing provenance and rights rules. |
| `MG_MOTION` | Generated explanatory motion graphic. |
| `ADVANCED_MOTION` | A separately reviewed advanced motion route. |

Material and production components retain factual grounding, rights/capture provenance, staging checks, renderer checks, actual-file metadata, binding QA, and immutable storage. Remotion and HyperFrames are rendering adapters over a shared semantic payload; normal production selects one renderer. Existing full-video/Aligned Preview infrastructure is compatibility/QA/optional preview, not the primary creator output.

Relevant contracts: [MATERIAL_CONTRACT.md](MATERIAL_CONTRACT.md), [VISUAL_SPEC.md](VISUAL_SPEC.md), [PRODUCTION_CONTRACT.md](PRODUCTION_CONTRACT.md).

### Asset Pack, Edit Map, and review loop

`asset_pack_workflow`, `visual_asset_pack`, and `edit_map` publish only ready V1 assets in an Asset Pack. `edit-map/1` carries real A-roll time, semantic explanation, selected V1 decision, asset information, placement guidance, provenance, QA, and fallback. The creator manually selects and assembles material in an NLE.

`finished_cut_review` records bound observations of planned versus actual use. It cannot change the finished media, output a replacement, generate an NLE project, assign aesthetic quality, or convert one episode into a global policy.

Relevant contract: [FINISHED_CUT_REVIEW_CONTRACT.md](FINISHED_CUT_REVIEW_CONTRACT.md).

## Current Storage and Safety Boundaries

- Repository code owns schemas, validation, stable examples, tests, and de-contented evaluations.
- Versioned production/review artifacts are immutable. Readers validate linkage, digests, and input identities rather than trusting a handwritten status.
- Digest-covered absolute paths remain immutable historical evidence after a workspace move. Core may map only a lineage-derived relative identity from an explicitly trusted historical repository root into the configured canonical repository root; this produces a separate runtime observation and never rewrites the artifact.
- Runtime resolution rejects unknown roots, traversal, identity mismatch, symlink components, root escape, missing/non-file targets, byte-size mismatch, and SHA-256 mismatch. The ignored machine-local runtime config may also identify the exact current Production; compatibility fallback uses artifact-owned time/revision/identity fields and never filesystem mtime.
- `reports/`, `script_drafts/`, `material_packages/`, `material_assets/`, `production_packages/`, `production_assets/`, `production_projects/`, A-roll media, and finished-cut media are local/gitignored.
- Renderer command success is insufficient: assets must pass typed checks, `ffprobe`, dimensions/fps/duration/size/SHA checks, and binding QA.
- Generated imagery cannot masquerade as evidence; raw PDFs and unsafe/unreviewed materials cannot enter renderers.

## Accepted Target Architecture — Partially Implemented, Unreleased

```text
Reviewed Script + approved Research ── factual/source binding ──┐
Final Clean A-roll → ASR → Alignment → Semantic Timeline        │
                                 ↓                               │
                        Visual Opportunity                       │
                                 ↓                               │
                    non-exclusive Candidate Portfolio            │
       ┌───────────┬──────────────┬───────────────┬─────────────┘
       MG       Illustrated Metaphor          Hand-drawn       REAL_MATERIAL
                (explicit v1 auxiliary)       (explicit v1)   (evidence)
       └──────────────── Candidate QA ───────────────────────────┐
                         ↓                                        │
      Candidate Asset Pack + multi-option Edit Map               │
                         ↓                                        │
               creator manual NLE selection                       │
                         ↓                                        │
      portfolio-aware, read-only Finished Cut Review              │
```

Target requirements:

- DeepTalk Visual Asset Ecosystem is multi-repo and plugin-first. Core owns the stable opportunity/portfolio boundary; each visual family independently owns research, optimization, benchmarking, QA, versioning, and native rendering internals.
- `Visual Opportunity` replaces V1's forced single-decision planning model; an absence of opportunity produces no additional material.
- `Candidate Portfolio` holds non-exclusive alternatives. Candidate overlap, duration differences, and use of none/one/multiple options are valid outcomes, not planner conflicts.
- Candidate QA is per candidate. Machine records separate Generation operation outcomes (`COMPLETED`, `FAILED`, `BLOCKED`, `UNAVAILABLE`) from produced Candidate outcomes (`READY`, `QA_REJECTED`); creator-facing packs default to READY items.
- New V2 writer contracts must preserve V1 readers/adapters, V1 `KEEP_A_ROLL` lineage, old `edit-map/1`, old manifests, and Finished Cut Review history.
- `REAL_MATERIAL` remains a distinct evidence/documentary family. Generated explanation families cannot displace factual/provenance requirements.
- `suggested_review_order` may guide inspection but must never encode an automatic selected winner.
- The evidence-derived [Visual Asset Plugin Contract V1 design](plans/2026-08-28-visual-asset-plugin-contract-v1.md) is **ACCEPTED_UNRELEASED** architecture: two-stage `Suitability → Generation`, normal `ABSTAIN`, eligible `BORDERLINE`, role-based artifacts, independent plugin/contract versions, and opaque plugin metadata. Accepted additive Core implementation extends through Phase 5; production-schema adoption remains disabled.
- The [Multi-Asset Implementation Plan](plans/2026-08-28-multi-asset-implementation-plan.md) is accepted. Phases 0–3B are ACCEPTED / IMPLEMENTED_UNRELEASED. Phase 4 adds the accepted Candidate Asset Pack + `candidate-edit-map/1` boundary at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`. Phase 5 invokes exact-pinned MG, Illustrated Metaphor, and Hand-drawn runners independently, canonicalizes non-semantic scheduling/config order, isolates failures, and emits deterministic synthetic Portfolio/Pack/map evidence. Phase 5 is **ACCEPTED / IMPLEMENTED_UNRELEASED** and pins Hand-drawn at `624526f4dce0ba9794c1a717fa397eb3c7a1baad`.

No V2 production migration, production default, or `edit-map/2` exists. The implemented Candidate Asset Pack and `candidate-edit-map/1` paths remain additive, synthetic, creator-choice artifacts; they do not select a winner or alter a cut.

## Product Architecture V2 — PASS / ACCEPTED; Phase A–C Integrated

The [Product Architecture V2](plans/2026-09-07-product-architecture-v2.md) is **PASS / ACCEPTED**. Phase A's compatibility representation/readers, Phase B's Visual Opportunity Detection boundary, and Phase C's independent Placement Planner are accepted, integrated, and unreleased. They remain additive and do not replace or override the implemented v1.0 path above.

### WHERE → WHAT → WHEN separation

V2 separates the visual pipeline into three independent stages:

```text
Semantic Timeline
  → WHERE: Visual Opportunity Detection (Studio Host)
       → WHAT: Asset Plugin suitability + generation (Plugins)
            → Candidate Portfolio (Studio Host)
                 → WHEN: Placement Planner (Studio Host)
                      → Candidate Asset Pack + Multi-option Edit Map
                           → creator manual NLE selection
```

- **WHERE** detects where visual assistance is worth adding and for what purpose. It does not decide which visual family to use. No opportunity = no additional asset.
- **WHAT** is answered by Asset Plugins, each independently SUITABLE / BORDERLINE / ABSTAIN. No plugin has Core-special status.
- **WHEN** produces per-candidate placement recommendations, distinct from opportunity time windows.

### Visual Director decomposition

The V1 Visual Director (single-decision central planner: `KEEP_A_ROLL` / `REAL_MATERIAL` / `MG_MOTION` / `ADVANCED_MOTION`) is decomposed into:

| V1 responsibility | V2 destination | Owner |
|---|---|---|
| Alignment validation, canonical timebase | A-roll Understanding | Studio Host |
| Where to add visuals | Visual Opportunity Detection (WHERE) | Studio Host |
| `KEEP_A_ROLL` → no visual | "No Visual Opportunity" | Studio Host |
| `REAL_MATERIAL` / `MG_MOTION` / `ADVANCED_MOTION` → which visual | Asset Plugin suitability + generation (WHAT) | Plugin |
| Placement within span | Placement Planner (WHEN) | Studio Host |

V1 `visual-director-plan/1` preserved via compatibility reader. The V1 Visual Director remains implemented and operational.

### Studio Host / Plugin boundary

| Studio Host owns | Plugins own |
|---|---|
| Episode identity, canonical A-roll identity, canonical timebase, Semantic Timeline, **authoritative identity governance and lineage** (Core creates `opportunity_id` / `request_id` / `portfolio_id` / Pack–Edit-Map IDs / Core staged locators; plugins create `proposal_id` / `candidate_id` and Core validates, persists, and binds them — "Core owns lineage" ≠ "Core creates every ID"), plugin registration/loading, contract validation, artifact storage, Candidate Portfolio identity, shared safety/QA, failure isolation, ABSTAIN semantics, packaging, Placement Planning | Visual content generation, suitability judgment, plugin-internal QA, scene grammar / renderer internals, **plugin-native artifact identity** (native URI / manifest identity; Core validates and may assign its own Core locator but must not rewrite plugin manifests, provenance, or historical evidence) |

See the [V2 design document](plans/2026-09-07-product-architecture-v2.md) §5.3 (Identity Authority vs Lineage Ownership) and §5.4 (plugin-native vs Core artifact identity) for the full ID-by-ID table. No ID creation semantics change: Contract V1 creators are preserved.

### REAL_MATERIAL plugin migration

REAL_MATERIAL migrates from a V1 Visual Director decision to a standard Real Material Asset Provider plugin. All existing obligations are preserved: source provenance, rights/reuse review, factual binding (Evidence/Context/Illustration), capture metadata, inspection evidence, `research_update_required`, material QA, immutable lineage.

### Contract migration

`suggested_placement` in `visual-asset-plugin-contract/1` is identified as a WHAT/WHEN coupling. A future `visual-asset-plugin-contract/2` will make `suggested_placement` optional (renamed `intrinsic_placement_hint`) and introduce `intrinsic_timing_hints`. A `ContractV1ToV2Adapter` will read V1 artifacts and map to V2 view. No existing artifact is rewritten. Legacy compatibility readers preserve all V1 history.

### HOW deferred

Presentation style (PIP, split screen, zoom, crop, overlay, transition) is explicitly not in V2 Phase 1 scope.

### Phased implementation plan

Implementation is phased (Phase A–F), compatibility-first, no big-bang rewrite, each phase independently reversible. Phase A–C are implemented and accepted; Phase D–F have not started:

- **Phase A — accepted / integrated:** Contracts, adapters, compatibility readers, tests.
- **Phase B — accepted / integrated:** Visual Opportunity Detection (WHERE) extraction.
- **Phase C — accepted / integrated:** Placement Planner (WHEN) boundary.
- **Phase D — not started:** Generated Asset Provider orchestration migration.
- **Phase E — not started:** REAL_MATERIAL plugin migration.
- **Phase F — not started:** Production adoption.

See the [design document](plans/2026-09-07-product-architecture-v2.md) §6 for full details.

`Accepted ≠ production-enabled; implemented ≠ released.`

## Extension Rules

- Add a versioned contract and explicit compatibility reader before changing a primary artifact meaning.
- Preserve real A-roll timing, source/provenance binding, immutable history, and QA; no new visual family may bypass them.
- Validate MG Quality V2 before increasing MG volume. Hand-drawn and Illustrated Metaphor are explicit v1.0 plugin capabilities; future quality expansion remains product validation. DeepTalk does not claim third-party character IP.
- Candidate density is a product-research variable, not a fixed schema quota.
- A product or architecture change must update its canonical owner: [PROJECT_STATE.md](../PROJECT_STATE.md), [PRD.md](../PRD.md), [ROADMAP.md](../ROADMAP.md), and this document as applicable.

## Historical Notes

Prior architecture documents, release notes, and plans may describe rough/full preview as central because that was true at the time. Preserve those records for debugging and lineage; they do not override the current primary Asset Pack + Edit Map architecture.
