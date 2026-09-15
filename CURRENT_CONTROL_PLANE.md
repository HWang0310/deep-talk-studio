# DeepTalk Studio — Current Control Plane

> Compact recovery index for the current project state. It is **not** a replacement for GitHub remote facts, `PROJECT_STATE.md`, or durable history. On recovery, fetch the live remote state first; if this file conflicts with live GitHub facts, the remote facts win.

## Recovery baseline

- Engineering-governance baseline at compaction: `HWang0310/engineering-journal` `main` @ `4d780462d3d9e14cfa330e4380faf81d3b684700`.
- Project: `HWang0310/deep-talk-studio`.
- Latest formal release: `v1.0.0`.
- Release URL: `https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0`.
- Canonical project truth: `PROJECT_STATE.md`.
- Canonical roster source: `AGENTS.md`.
- Historical engineering log: `HANDOFF.md`.

## Current control-plane state

- `v1.0.0` is formally released.
- There is currently **no active implementation task, PR, execution lane, or correction thread**.
- Issue #19 was created during the engineering-governance refresh by mistake; the Owner had requested standards adoption / control-plane compaction only, not activation of Product Architecture V2 Phase D. Issue #19 is closed `not_planned` and is historical context only.
- Product Architecture V2 Phase D/E/F remain future work. Phase D is a documented candidate, **not** the current product priority and **not started**.
- The old Nexus session-transfer Issue #3 is closed and superseded by the released project state and this compact recovery index. It remains durable history and must not be used as current task state.
- `agent/multi-asset-studio` @ `788ed3806c145189a51427f71a65013c050c5f48` is completed v1.0-cycle development lineage, not an active post-release lane.
- Phase 6 Owner-visible micro demo remains `TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW`; it is not an active blocker unless the Owner chooses to review it.

## Immediate next action

1. Wait for the Owner's next product goal / priority; do not infer a new implementation task from roadmap ordering alone.
2. Before any future dispatch, fetch live `engineering-journal` and read the current `AGENT-OPERATING-MODEL.md` plus `BACKEND-CAPABILITY-CERTIFICATION.md`.
3. Recover DeepTalk engineer identities only from the current DeepTalk `AGENTS.md` roster.
4. When a real implementation task is selected, maintain one active execution/review thread; once a PR exists, that PR is the default active thread.
5. For correction rounds on the same PR, use delta-first review and correction delta handoff. Refresh remote facts only after a mutation or when staleness is reasonably suspected.
6. Preserve `HANDOFF.md`, closed Issues/PRs, commits, branches, tags, releases, and old handoff snapshots as durable history. Read them only when they materially affect current recovery, provenance, or technical judgment.

## Recovery rule

Do **not** replay old ChatGPT sessions or the full `HANDOFF.md` by default. Start from:

1. live remote branch / PR / Issue state;
2. `PROJECT_STATE.md`;
3. this compact control-plane index;
4. `docs/INDEX.md` and only task-relevant canonical docs.

Historical details are pulled only on demand.
