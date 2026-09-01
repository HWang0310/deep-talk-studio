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
- [Multi-Asset Implementation Plan](plans/2026-08-28-multi-asset-implementation-plan.md) — accepted implementation sequencing. Phase 2 fake-only Core work is ACCEPTED / IMPLEMENTED_UNRELEASED. MG Phase 3A-1 is accepted and exact-pinned; Core Phase 3A-2 single-MG synthetic integration is IMPLEMENTED_UNRELEASED / AWAITING_CHATGPT_REVIEW. This is not a release, production default, or Phase 3B claim.

Contracts describe the version named in their title. They do not by themselves establish release status or make a future plan current.

## Evaluations

- [Evaluation methods](EVALS.md)
- [Local ASR Selection evidence](../evaluations/local_asr_selection/report.md)
- Product-level real-episode findings: [PROJECT_STATE.md](../PROJECT_STATE.md#real-episode-validation)

Do not add private episode materials, finished videos, raw research, or credentials to Git.

## Research, Proposals, and Implementation Plans

- [Product research and proposals](plans/)
- [Implementation plans](superpowers/plans/)
- [Historical design specs](superpowers/specs/)

These preserve decision context. Their status must be read through PROJECT_STATE, PRD, and ROADMAP. **Plan exists ≠ accepted; implemented ≠ released.**

## Historical Engineering Log and Versions

- [HANDOFF.md](../HANDOFF.md) — chronological engineering and product handoff log; use for decision lineage, episode evidence, bug origin, and architecture evolution.
- [CHANGELOG.md](../CHANGELOG.md) — formal release entries and chronological unreleased development history.
- [Release notes](releases/) — released version records.
- [RELEASE_POLICY.md](../RELEASE_POLICY.md) — rules for making a future formal release.

## Reconciliation Record

- [2026-08-27 Project Memory Reconciliation Audit](plans/2026-08-27-project-memory-reconciliation-audit.md) records stale/conflicting claims, evidence, and canonical resolutions from this consolidation.
