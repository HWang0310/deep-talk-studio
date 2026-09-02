# Plugin Repository Governance Normalization Design

**Task:** `DT-GOV-PLUGIN-001`

## Goal

Normalize the three independent visual-plugin repositories before separate plugin-focused Curator sessions begin, while preserving DeepTalk Core release semantics and the existing plugin integration boundary.

## Canonical truth model

- `deep-talk-studio/main` remains Formal Release truth.
- `deep-talk-studio/agent/multi-asset-studio` remains accepted Core development truth.
- Plugin repository `main` means the latest plugin-local `ACCEPTED` stable runtime.
- Plugin optimization happens on isolated task branches from plugin `main`.
- Plugin-local acceptance does not authorize a DeepTalk Core repin; only DeepTalk Nexus may repin after independent integration review.

## Engineering standards

All new plugin Curator sessions must bootstrap from `HWang0310/engineering-journal` current default branch. Governance task baseline: `35fc8ef9e4c09a86907efd6e14d772d306451ca7`.

Inherited rules include Curator/Axiom/Mason/Rivet routing, Task IDs, one-writer/worktree isolation, GitHub-native handoff, exact-SHA review, scope control, and the restricted-content hard gate.

## Plugin baselines

- MG: `7ae59f1115da8a011113c81f31d320783b0ce8a4`
- Illustrated Metaphor: `48848affe018fc2cff8ee15bad7a09bb002776e4`
- Hand-drawn Animation: `853618bdf19ae66ec393211b77d970911f53f4bc`

Each accepted SHA is already verified to be a fast-forward descendant of its repository's pre-governance `main`.

## Required repository shape

Each plugin repository must expose from `main`:

1. `README.md` with a visible `Current Accepted Runtime` section.
2. `AGENTS.md` that requires engineering-journal bootstrap and preserves project-specific rules.
3. `PROJECT_STATE.md` as current operational truth.
4. `HANDOFF.md` as chronological history, not current-state authority.
5. `docs/DEEPTALK-INTEGRATION.md` describing the non-negotiable DeepTalk compatibility gate and handback protocol.
6. Recovery Issue #1 as the canonical new-session entry.

## DeepTalk compatibility gate

A plugin optimization is not accepted for DeepTalk integration unless it preserves, or changes only through an explicitly approved versioned contract:

- independent repository ownership;
- `visual-asset-plugin-contract/1` boundary;
- normal `Suitability -> Generation` flow;
- suitability outcomes `SUITABLE | BORDERLINE | ABSTAIN`;
- generation operation statuses `COMPLETED | FAILED | BLOCKED | UNAVAILABLE`;
- candidate statuses `READY | QA_REJECTED`;
- ordinary subprocess/file runner invocation;
- Core-owned request/result/output boundaries;
- no single-Agent proprietary runtime dependency;
- no automatic winner/editing or A-roll modification;
- honest explanatory media that does not impersonate evidence/REAL_MATERIAL.

## Hand-drawn special condition

Moving the accepted Hand-drawn runtime to `main` does not erase the Phase 6 real-A-roll blocker. The repository must state that real mechanism generation can currently render frame sequences without completing the final Contract-required media/manifest, and that this reliability defect must be fixed before broad visual-quality optimization is considered complete.

## Mutation strategy

For each plugin, serially:

1. Reconfirm accepted SHA is a fast-forward descendant of current `main`.
2. Move `main` to accepted SHA with `force=false`.
3. Create `governance/plugin-pm-bootstrap` from the new `main`.
4. Make documentation/governance-only changes.
5. Review exact governance SHA; no renderer/runtime/dependency changes allowed.
6. Fast-forward `main` to governance SHA with `force=false` only after PASS.
7. Update Recovery Issue #1 to the governed `main` truth.

## Out of scope

No renderer changes, no Contract semantic changes, no dependency upgrades, no Core runtime changes, no Phase 6 acceptance decision, no tag/release, and no force push.
