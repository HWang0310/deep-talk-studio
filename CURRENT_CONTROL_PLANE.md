# DeepTalk Studio — Current Control Plane

> Compact recovery index for the current project state. It is **not** a replacement for GitHub remote facts, `PROJECT_STATE.md`, or durable history. On recovery, fetch the live remote state first; if this file conflicts with live GitHub facts, the remote facts win.

## Recovery baseline

- Engineering-governance baseline at compaction: `HWang0310/engineering-journal` `main` @ `4d780462d3d9e14cfa330e4380faf81d3b684700`.
- Project: `HWang0310/deep-talk-studio`.
- Compaction base: `main` was `abc2e2a8b302506eec73f76ebcf457015ecaea9a` before this docs-only compaction.
- Latest formal release: `v1.0.0`.
- Release URL: `https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0`.
- Canonical project truth: `PROJECT_STATE.md`.
- Canonical roster source: `AGENTS.md`.
- Historical engineering log: `HANDOFF.md`.

## Current control-plane state

- `v1.0.0` is formally released.
- There is currently **no active implementation PR**.
- There is currently **no active execution/review lane** that should be recovered from an old PR or correction thread.
- The old Nexus session-transfer Issue #3 is superseded by the released project state and this compact recovery index. It remains durable history and must not be used as current task state.
- `agent/multi-asset-studio` @ `788ed3806c145189a51427f71a65013c050c5f48` is the completed v1.0-cycle development lineage recorded by project state; do not treat it as an automatically active post-release lane. New work must start from live remote facts and an explicitly chosen current base.
- Phase 6 Owner-visible micro demo remains `TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW`; it is not an active implementation blocker unless the Owner chooses to review it.
- Product Architecture V2 Phase D/E/F remain not started. Phase D is the next recorded post-v1 engineering candidate, not an already-active task.

## Immediate next action

1. Before any new dispatch, fetch live `engineering-journal` and read the current `AGENT-OPERATING-MODEL.md` plus `BACKEND-CAPABILITY-CERTIFICATION.md`.
2. Recover DeepTalk engineer identities only from the current DeepTalk `AGENTS.md` roster.
3. If post-v1 implementation resumes, create exactly one active execution/review thread for the selected task; once a PR exists, that PR is the default active thread.
4. For correction rounds on the same PR, use delta-first review and correction delta handoff. Refresh remote facts only after a mutation or when staleness is reasonably suspected.
5. Preserve `HANDOFF.md`, closed Issues/PRs, commits, branches, tags, releases, and old handoff snapshots as durable history. Read them only when they materially affect current recovery, provenance, or technical judgment.

## Recovery rule

Do **not** replay old ChatGPT sessions or the full `HANDOFF.md` by default. Start from:

1. live remote branch / PR / Issue state;
2. `PROJECT_STATE.md`;
3. this compact control-plane index;
4. `docs/INDEX.md` and only task-relevant canonical docs.

Historical details are pulled only on demand.