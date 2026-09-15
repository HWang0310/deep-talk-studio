# DeepTalk Studio — Current Control Plane

> Compact recovery index for the current project state. It is **not** a replacement for GitHub remote facts, `PROJECT_STATE.md`, or durable history. On recovery, fetch the live remote state first; if this file conflicts with live GitHub facts, the remote facts win.

## Recovery baseline

- Engineering-governance baseline at compaction: `HWang0310/engineering-journal` `main` @ `4d780462d3d9e14cfa330e4380faf81d3b684700`.
- Project: `HWang0310/deep-talk-studio`.
- Compaction base: `main` was `abc2e2a8b302506eec73f76ebcf457015ecaea9a` before the docs-only control-plane compaction.
- Latest formal release: `v1.0.0`.
- Release URL: `https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0`.
- Canonical project truth: `PROJECT_STATE.md`.
- Canonical roster source: `AGENTS.md`.
- Historical engineering log: `HANDOFF.md`.

## Current control-plane state

- `v1.0.0` is formally released.
- Active task: **Issue #19 — `DT-V2-PHASE-D-001`, Generated Asset Provider Orchestration Migration**.
- Current active execution/review thread: **Issue #19** until an implementation PR exists. Once the PR is opened, that PR becomes the single active execution/review thread and Issue #19 remains durable task context.
- Writer identity: **Atlas** (DeepTalk canonical roster / Deep Engineering Role). Backend routing is operational and must follow the latest engineering-journal registry at dispatch/recovery time.
- There is currently **no active implementation PR** yet.
- The old Nexus session-transfer Issue #3 is closed and superseded by the released project state and this compact recovery index. It remains durable history and must not be used as current task state.
- `agent/multi-asset-studio` @ `788ed3806c145189a51427f71a65013c050c5f48` is the completed v1.0-cycle development lineage recorded by project state; it is not the active Phase D lane.
- Phase 6 Owner-visible micro demo remains `TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW`; it is not an active implementation blocker unless the Owner chooses to review it.
- Product Architecture V2 Phase D is now active through Issue #19. Phase E/F remain not started and out of scope.

## Immediate next action

1. Atlas recovers live `main`, Issue #19, task-relevant architecture/contracts, and the latest engineering-journal routing facts.
2. Atlas creates one isolated Phase D task branch from **live remote `main`** and implements only the Issue #19 scope.
3. Atlas opens one implementation PR to `main`; that PR then becomes the single active execution/review thread.
4. Nexus performs exact-SHA Review. If corrections are required, review `PREVIOUS_REVIEWED_HEAD...CURRENT_HEAD` delta first and require correction delta handoff rather than repeating full history.
5. Refresh remote facts only after a relevant mutation or when staleness is reasonably suspected.
6. Preserve `HANDOFF.md`, closed Issues/PRs, commits, branches, tags, releases, and old handoff snapshots as durable history. Read them only when they materially affect current recovery, provenance, or technical judgment.

## Recovery rule

Do **not** replay old ChatGPT sessions or the full `HANDOFF.md` by default. Start from:

1. live remote branch / PR / Issue state;
2. `PROJECT_STATE.md`;
3. this compact control-plane index;
4. `docs/INDEX.md` and only task-relevant canonical docs.

Historical details are pulled only on demand.