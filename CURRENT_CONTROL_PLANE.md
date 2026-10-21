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
- **Creator Workbench UI [Issue #26](https://github.com/HWang0310/deep-talk-studio/issues/26) completed:** Forge's initial localhost topic→Bilibili-search UI received Nexus exact-head PASS at `b67ce2e43e8caa751e72c63b145246f2c9e3d17d`; [PR #27](https://github.com/HWang0310/deep-talk-studio/pull/27) merged to `main` at `da0e96d122738cf07edadb83bcc355986138e061`. **ACCEPTED / IMPLEMENTED_UNRELEASED; Owner still needs to open and experience it locally.** Reference discovery [Issue #24 / PR #25](https://github.com/HWang0310/deep-talk-studio/pull/25) is also integrated (merge `90919cf8b2eadc361ffa4a879211c8d7fc089e73`). The formal release/tag remains `v1.0.0`; no production rollout is implied. Owner's optional self-voice cloning is a future product direction in [Issue #28](https://github.com/HWang0310/deep-talk-studio/issues/28), **BACKLOG/HOLD** (not an active implementation). Parent product tracker [#23](https://github.com/HWang0310/deep-talk-studio/issues/23) remains open.
- Issue #19 was created during the engineering-governance refresh by mistake; the Owner had requested standards adoption / control-plane compaction only, not activation of Product Architecture V2 Phase D. Issue #19 is closed `not_planned` and is historical context only.
- Product Architecture V2 Phase D/E/F remain future work. Phase D is a documented candidate, **not** the current product priority and **not started**.
- The old Nexus session-transfer Issue #3 is closed and superseded by the released project state and this compact recovery index. It remains durable history and must not be used as current task state.
- `agent/multi-asset-studio` @ `788ed3806c145189a51427f71a65013c050c5f48` is completed v1.0-cycle development lineage, not an active post-release lane.
- Phase 6 Owner-visible micro demo remains `TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW`; it is not an active blocker unless the Owner chooses to review it.

## Immediate next action

1. **Owner priority is first published video, not adding features** ([pilot Issue #29](https://github.com/HWang0310/deep-talk-studio/issues/29), 2026-10-21). First choose a real episode/topic or reuse an existing reviewed script. The Mac UI on accepted `main` can be started with `./scripts/deeptalk ui` at `http://127.0.0.1:8321/` after protecting local dirty/unpushed work. Owner generates narration using external VoxCPM2 online or locally and supplies a final audio file. Current canonical timed-asset workflow only supports Final Clean human A-roll, so DO NOT describe external AI narration as already supported by automated Edit Map; either use manual NLE timing or independently review a tiny audio-first adapter if strictly needed. Creator manually edits/publishes with lawful materials and appropriate AI-audio disclosure. Native voice clone [Issue #28](https://github.com/HWang0310/deep-talk-studio/issues/28) is **DEFERRED/HOLD**, and BYO model settings/full UI integrations are not blockers for this first-episode pilot. No model downloads, private voice access or editing work yet dispatched.
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
