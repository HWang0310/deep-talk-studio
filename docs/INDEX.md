---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '347e4206-096e-4bd0-af9f-c21e628eeb9f'
  PropagateID: '347e4206-096e-4bd0-af9f-c21e628eeb9f'
  ReservedCode1: 'bea5d600-2483-42ae-936a-a5163bf18156'
  ReservedCode2: 'bea5d600-2483-42ae-936a-a5163bf18156'
---

# DeepTalk Studio Documentation Index

This index routes readers to the canonical owner of each fact. It prevents historical documents from being mistaken for current product truth.

## Bootstrap Reading Order

For a new Codex session:

1. [AGENTS.md](../AGENTS.md) — repository operating rules and bootstrap protocol.
2. [PROJECT_STATE.md](../PROJECT_STATE.md) — concise canonical current truth.
3. This index — document ownership and task routing.
4. [README.md](../README.md), [PRD.md](../PRD.md), and [ROADMAP.md](../ROADMAP.md) — product orientation and status.
5. [ARCHITECTURE.md](ARCHITECTURE.md) — implemented and accepted-target architecture.
6. Only the contracts relevant to the task.
7. Only when history is needed: [HANDOFF.md](../HANDOFF.md), plans, specs, release notes, and old evaluations.

Before acting, also inspect the current Git branch, HEAD, and working-tree status.

## Current Product

| Need | Canonical owner |
|---|---|
| Current truth, formal release, accepted/unreleased/experimental state | [PROJECT_STATE.md](../PROJECT_STATE.md) |
| Fast introduction for a new contributor or creator | [README.md](../README.md) |
| Accepted product requirements and hard boundaries | [PRD.md](../PRD.md) |
| Released versus accepted, current, next, experimental, and deferred work | [ROADMAP.md](../ROADMAP.md) |
| Current technical architecture and accepted target architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Eventual `v1.0.0` GitHub Release body source | [v1.0.0 release notes](releases/v1.0.0.md) |

## Current Contracts

- [Topic Discovery Contract](TOPIC_DISCOVERY_CONTRACT.md) and [Topic Discovery Evals](TOPIC_DISCOVERY_EVALS.md)
- [Script Contract](SCRIPT_CONTRACT.md) and [Script Evals](SCRIPT_EVALS.md)
- [Material Contract](MATERIAL_CONTRACT.md) and [Material Evals](MATERIAL_EVALS.md)
- [Visual Spec](VISUAL_SPEC.md)
- [Production Contract](PRODUCTION_CONTRACT.md) and [Production Evals](PRODUCTION_EVALS.md)
- [Audio Alignment + Visual Edit Bridge Contract](EDIT_BRIDGE_CONTRACT.md)
- [Asset Pack + Edit Map Contract (V1)](ASSET_PACK_EDIT_MAP_CONTRACT.md)
- [Finished Cut Review + Production Feedback Contract (V1)](FINISHED_CUT_REVIEW_CONTRACT.md)
- [Remotion Adapter](REMOTION_ADAPTER.md) and [HyperFrames Adapter](HYPERFRAMES_ADAPTER.md)
- [Visual Asset Plugin Contract V1 design](plans/2026-08-28-visual-asset-plugin-contract-v1.md) — ACCEPTED_UNRELEASED architecture; not an implemented runtime contract.
- [Multi-Asset Implementation Plan](plans/2026-08-28-multi-asset-implementation-plan.md) — accepted implementation sequencing. Phases 0–3B are ACCEPTED / IMPLEMENTED_UNRELEASED; Phase 4 is ACCEPTED / IMPLEMENTED_UNRELEASED at `817ca8b424f18714e4280d3990c1bc4221ec8dbe`; Phase 5 real three-plugin synthetic integration is **ACCEPTED / IMPLEMENTED_UNRELEASED** and uses accepted Hand-drawn revision `624526f4dce0ba9794c1a717fa397eb3c7a1baad`. This is not a release, production default, or production enablement. Phase 6 (《牛来》 Owner-visible Micro Demo) is **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** on branch `agent/phase6-niulai-owner-demo` at `b72b7c2`.

Contracts describe the version named in their title. They do not by themselves establish release status or make a future plan current.

## Evaluations

- [Evaluation methods](EVALS.md)
- [Local ASR Selection evidence](../evaluations/local_asr_selection/report.md)
- [Phase 5 runner-host preflight](../evaluations/visual_asset_engine/phase5_runner_host_preflight.md), [three-plugin synthetic evidence](../evaluations/visual_asset_engine/phase5_three_plugin_synthetic.md), and [final validation](../evaluations/visual_asset_engine/phase5_final_validation.md)
- Product-level real-episode findings: [PROJECT_STATE.md](../PROJECT_STATE.md#real-episode-validation)

Do not add private episode materials, finished videos, raw research, or credentials to Git.

## Research, Proposals, and Implementation Plans

- [Product Architecture V2 — Design & Migration](plans/2026-09-07-product-architecture-v2.md) — **PASS / ACCEPTED.** Phase A compatibility foundations, Phase B WHERE boundary, and Phase C WHEN Placement Planner are accepted and integrated. Phase D/E/F orchestration migration, REAL_MATERIAL migration, and production adoption have not started.
- [Product research and proposals](plans/)
- [Implementation plans](superpowers/plans/)
- [Historical design specs](superpowers/specs/)

These preserve decision context. Their status must be read through PROJECT_STATE, PRD, and ROADMAP. **Plan exists ≠ accepted; implemented ≠ released.**

## Historical Engineering Log and Versions

- [HANDOFF.md](../HANDOFF.md) — chronological engineering and product handoff log; use for decision lineage, episode evidence, bug origin, and architecture evolution.
- [CHANGELOG.md](../CHANGELOG.md) — formal release entries and chronological unreleased development history.
- [Release notes](releases/) — released version records plus the prepared, unpublished [v1.0.0 release-note source](releases/v1.0.0.md).
- [RELEASE_POLICY.md](../RELEASE_POLICY.md) — rules for making a future formal release.

## Reconciliation Record

- [2026-08-27 Project Memory Reconciliation Audit](plans/2026-08-27-project-memory-reconciliation-audit.md) records stale/conflicting claims, evidence, and canonical resolutions from this consolidation.
