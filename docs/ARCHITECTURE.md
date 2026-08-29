# DeepTalk Studio Architecture

> **Canonical owner:** current technical architecture. Read [PROJECT_STATE.md](../PROJECT_STATE.md) first. “Accepted target” below is explicitly not implemented.

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
- `reports/`, `script_drafts/`, `material_packages/`, `material_assets/`, `production_packages/`, `production_assets/`, `production_projects/`, A-roll media, and finished-cut media are local/gitignored.
- Renderer command success is insufficient: assets must pass typed checks, `ffprobe`, dimensions/fps/duration/size/SHA checks, and binding QA.
- Generated imagery cannot masquerade as evidence; raw PDFs and unsafe/unreviewed materials cannot enter renderers.

## Accepted Target Architecture — Not Yet Implemented

```text
Reviewed Script + approved Research ── factual/source binding ──┐
Final Clean A-roll → ASR → Alignment → Semantic Timeline        │
                                 ↓                               │
                        Visual Opportunity                       │
                                 ↓                               │
                    non-exclusive Candidate Portfolio            │
       ┌───────────┬──────────────┬───────────────┬─────────────┘
       MG       Illustrated / Character      Hand-drawn       REAL_MATERIAL
                Metaphor (future family)      (experiment)    (evidence)
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
- The evidence-derived [Visual Asset Plugin Contract V1 design](plans/2026-08-28-visual-asset-plugin-contract-v1.md) is **ACCEPTED_UNRELEASED** architecture: two-stage `Suitability → Generation`, normal `ABSTAIN`, eligible `BORDERLINE`, role-based artifacts, independent plugin/contract versions, and opaque plugin metadata. Phase 0 implements strict Core validators and a sanitized fixture baseline only; it is not runtime implementation or production-schema adoption.
- The [Multi-Asset Implementation Plan](plans/2026-08-28-multi-asset-implementation-plan.md) is accepted. Phase 1 is IMPLEMENTED_UNRELEASED on its review branch: clock-free directives feed safe real-timeline-derived opportunities, a Core-owned fake subprocess job, and an immutable machine portfolio. No real plugin, V2 production migration, Candidate Pack, or production default has started.

No V2 runtime schema, migration, renderer, candidate pack, `edit-map/2`, or production default exists yet. The Phase 0 validators, synthetic fixtures, test-only fake runner, and static examples do not alter that boundary.

## Extension Rules

- Add a versioned contract and explicit compatibility reader before changing a primary artifact meaning.
- Preserve real A-roll timing, source/provenance binding, immutable history, and QA; no new visual family may bypass them.
- Validate MG Quality V2 before increasing MG volume. Hand-drawn and Xiaohei-related work remain experiments. Xiaohei is not DeepTalk IP.
- Candidate density is a product-research variable, not a fixed schema quota.
- A product or architecture change must update its canonical owner: [PROJECT_STATE.md](../PROJECT_STATE.md), [PRD.md](../PRD.md), [ROADMAP.md](../ROADMAP.md), and this document as applicable.

## Historical Notes

Prior architecture documents, release notes, and plans may describe rough/full preview as central because that was true at the time. Preserve those records for debugging and lineage; they do not override the current primary Asset Pack + Edit Map architecture.
