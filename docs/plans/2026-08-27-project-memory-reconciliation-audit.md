# Project Memory Reconciliation Audit — 2026-08-27

**Scope:** documentation architecture only. Baseline audited: `agent/multi-asset-studio` at `4929ff2de1106bf218812915afa22f7b99a63932`. This audit does not change production code, schemas, episode artifacts, tags, releases, or `main`.

## Audit Method

Read and checked:

- `AGENTS.md`, `README.md`, `PROJECT_STATE.md` (absent before this work), `PRD.md`, `ROADMAP.md`, `CHANGELOG.md`, `HANDOFF.md`, and `docs/ARCHITECTURE.md`;
- current contracts, evaluations, `docs/plans`, `docs/superpowers/plans`, `docs/superpowers/specs`, and release notes;
- Git status, branches, tags, recent log, and the `v0.6.1` → current-baseline diff.

Repository-wide Markdown search included: current version, current state, current workflow, primary workflow, V1, preview, rough cut, full video, final video, auto edit, NLE, KEEP_A_ROLL, Visual Director, Asset Pack, Edit Map, renderer, release, blocker, next step, Production Gate, Finished Cut, Content Thesis, Script Agent, and Multi-Asset.

### Git Evidence

| Fact | Evidence |
|---|---|
| Formal release | `v0.6.1` points to `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`. |
| Accepted V1 code baseline | `agent/audio-alignment-edit-bridge` is at `4713505`. |
| Starting research baseline | `agent/multi-asset-studio` is at `4929ff2de1106bf218812915afa22f7b99a63932`. |
| Working state before documentation edits | Clean `agent/multi-asset-studio` working tree. |
| v0.6.1 → research baseline | 252 files changed; it contains V1 Candidate implementation, tests, evaluations, contracts, historical handoffs, and Multi-Asset research. It is not a later formal release. |

## Claim Reconciliation

| Claim | Source | Observed status | Current / Historical / Proposal | Conflict | Canonical resolution | Action |
|---|---|---|---|---|---|---|
| “Current version is V0.6.1” | Old README and release-era docs | `v0.6.1` is the latest formal tag, but substantial V1 Candidate work exists after it. | Mixed current/release language | Can imply no current unreleased development. | Latest **Formal Release** is v0.6.1; current development is **V1.0 Candidate — Unreleased**. | PROJECT_STATE, README, PRD, ROADMAP, CHANGELOG. |
| Multi-Asset research is “awaiting ChatGPT Product Review” | CHANGELOG and HANDOFF entry dated 2026-08-27 | New Product Review decision supplied for this consolidation accepts the core direction. | Historical proposal followed by current accepted decision | Stale “awaiting review” language. | Mark core direction **ACCEPTED_UNRELEASED / implementation not started**; preserve research as research/proposal detail. | CHANGELOG, HANDOFF, PROJECT_STATE, PRD, ROADMAP, ARCHITECTURE. |
| A complete/aligned preview is the primary E2E success gate | Old README, PRD, ROADMAP, handoffs, preview plans | Some early entries still say preview gate blocked or describe rough/full preview as the V1 outcome. | Historical at time; stale when read as current | Contradicts current Asset Pack + Edit Map primary UX and completed 《牛来》 loop. | Asset Pack + Edit Map → creator manual NLE is primary. Preview is compatibility/QA/optional only. | README, PRD, ROADMAP, ARCHITECTURE, AGENTS; retain history. |
| “Current real user gate blocked because safe materials were unavailable” | README / ROADMAP older text | Real 《牛来》 later completed Asset Pack, manual assembly, Finished Cut Review, and feedback. | Historical blocker | Misstates current real-episode evidence. | 《牛来》 is the first complete production-loop baseline; findings remain limited to one episode. | PROJECT_STATE, ROADMAP, HANDOFF pointer; remove stale README/ROADMAP current wording. |
| Full video / automatic edit direction | Old preview plans/specs and old long-term wording | Code has preview capability, but current V1 contract is manual NLE and no automatic final edit. | Historical capability / superseded primary direction | A new agent could infer DeepTalk edits the final video. | No automatic editing, selection, NLE project, final output, or publishing. | PROJECT_STATE, README, PRD, ROADMAP, ARCHITECTURE, AGENTS. |
| V1 `KEEP_A_ROLL` is the default single visual decision | `ASSET_PACK_EDIT_MAP_CONTRACT.md`, V1 code/plan | Implemented and required for historic V1 artifact lineage. | Current V1 implementation | Could be mistaken for accepted V2 candidate semantics. | Keep V1 reader/adapter compatibility; V2 has no new `KEEP_A_ROLL` candidate planning. | PROJECT_STATE, PRD, ROADMAP, ARCHITECTURE; do not rewrite V1 contract. |
| Visual Director / selected asset per span is the architecture | V1 contracts, code, architecture, plans | Implemented V1 fact. | Current V1 implementation | Could make V2 Candidate Portfolio look implemented. | Distinguish V1 Visual Director from accepted target Visual Opportunity → non-exclusive Candidate Portfolio. | ARCHITECTURE, PRD, PROJECT_STATE. |
| Asset Pack + Edit Map is primary delivery | V1 Asset Pack/Edit Map contract, 2026-08-25 handoff | Implemented and real-episode validated. | Current V1 truth | Old preview language dilutes it. | Keep as current V1 primary delivery; Markdown is creator-facing, CSV helper, JSON machine contract. | PROJECT_STATE, README, PRD, ROADMAP, ARCHITECTURE. |
| Content Thesis / Script V1 waits for human confirmation | AGENTS, Script contract, code/handoffs | Implemented, accepted, unreleased; 《恒大》 is READY_FOR_RECORDING. | Current V1 truth | Old entries describe earlier pre-confirmation state. | Human confirmation remains mandatory; 《恒大》 has no A-roll yet. | PROJECT_STATE, PRD, ROADMAP. |
| Finished Cut Review may learn from actual use | Finished Cut contract, code, 2026-08-25 handoff | Implemented and validated with 《牛来》. | Current V1 truth | Could be read as autonomous quality scoring or rule creation. | Read-only, non-judgmental observation; one episode cannot set global rules. | PROJECT_STATE, README, PRD, ROADMAP, ARCHITECTURE. |
| MG Quality V2, Hand-drawn, Xiaohei | Multi-Asset research and 2026-08-27 Product Review | MG V2 approved next; Hand-drawn approved experiment; Xiaohei prototype only. | Accepted next / experimental | Research wording could be read as renderer/product availability. | Do not call any implemented; Xiaohei is not DeepTalk IP. | PROJECT_STATE, README, PRD, ROADMAP, ARCHITECTURE. |
| Candidate density uses fixed counts | Multi-Asset research proposal | Counts are hypotheses, not accepted schema invariants. | Proposal / under validation | “RICH” could become an accidental quota. | Optimise useful choice density; LEAN/STANDARD/RICH stay soft profiles. | PROJECT_STATE, PRD, ROADMAP. |
| Formal Release status | 98+ unreleased commits and changelog sections | No post-v0.6.1 tag/release was found. | Current truth | Unreleased commit history could be mistaken for releases. | CHANGELOG separates formal version entries from Unreleased development. | CHANGELOG top note, PROJECT_STATE, README, ROADMAP. |

## Canonical Ownership After Reconciliation

| Fact type | Canonical owner |
|---|---|
| Concise current truth, release, development state, accepted/experimental state, episode evidence | `PROJECT_STATE.md` |
| Newcomer orientation | `README.md` |
| Product requirements and hard boundaries | `PRD.md` |
| State classification and sequencing | `ROADMAP.md` |
| Current implemented and accepted-target technical architecture | `docs/ARCHITECTURE.md` |
| Navigation and reading order | `docs/INDEX.md` |
| Formal release and unreleased change chronology | `CHANGELOG.md` |
| Engineering/product chronology | `HANDOFF.md` |
| Research, proposals, designs, and implementation plans | `docs/plans/`, `docs/superpowers/specs/`, `docs/superpowers/plans/` |

## Memory Maintenance Rules

- Ordinary bug fixes or small changes generally update CHANGELOG and, when worth retaining chronologically, HANDOFF.
- A change to positioning, hard boundary, primary workflow, canonical architecture, release state, validated capability, or major accepted direction must update the relevant canonical owner(s), not every file mechanically.
- Historical plans, specs, evaluations, release notes, and handoffs remain intact. Add a current pointer rather than silently deleting evidence.
- Private research, competitor media, A-roll, assets, finished cuts, large binaries, and secrets remain outside Git. Product-level validation findings may be documented without private content.

## Audit Conclusion

The largest memory risk was not an implementation contradiction; it was **chronology masquerading as current truth**. The former README/ROADMAP and the opening of HANDOFF mixed old preview blockers, V1 Candidate status, and current product direction. The new canonical state and index centralise the answer while preserving the complete historical record.
