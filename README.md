---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '66061a2d-bded-45f7-b838-bf2e022e8514'
  PropagateID: '66061a2d-bded-45f7-b838-bf2e022e8514'
  ReservedCode1: '5d61b7e4-ecfb-4207-babc-f3e4602095fd'
  ReservedCode2: '5d61b7e4-ecfb-4207-babc-f3e4602095fd'
---

# DeepTalk Studio

**Latest Formal Release:** [`v0.6.1`](docs/releases/v0.6.1.md) (`8a0ac94`)

**Development:** **v1.0.0 release candidate prepared — pending Nexus exact-SHA / PR approval.** No `v1.0.0` tag or GitHub Release exists.

**Canonical Current State:** [PROJECT_STATE.md](PROJECT_STATE.md)

DeepTalk Studio is a content and visual-asset system for creators making human-led, deep spoken videos. It helps turn a defensible topic into a reviewed script, then prepares evidence-bound visual assets and precise placement suggestions against the creator's final clean A-roll.

The creator always owns content judgment, recording, final visual selection, and final NLE aesthetics. DeepTalk 不替用户剪辑最终视频，也不会自动编辑成片。

## The Current Product Path

```text
Topic → Research → Fact Check → Content Thesis → human confirmation
→ Reviewed Script → Final Clean A-roll → local ASR → Alignment
→ Semantic Timeline → Visual Director → asset QA
→ Asset Pack + Edit Map → creator manual NLE assembly
→ Finished Cut Review + Production Feedback
```

Asset Pack plus a creator-facing Markdown Edit Map is the normal delivery. CSV supports finding and sorting; JSON remains the machine contract. Historical full-video/Aligned Preview output remains compatibility and QA infrastructure, not the primary product experience.

## What DeepTalk Does

- discovers and researches topics with independent fact checks;
- develops a Content Thesis, waits for human confirmation, and produces a reviewed original script;
- anchors visual planning to the real timing of a final clean A-roll;
- prepares provenance-bound real materials and generated explanatory visual assets;
- runs asset QA, creates an Asset Pack, and tells the creator where material may fit;
- optionally reviews a creator's finished cut read-only to compare plan and actual use.

## v1.0 Product: One Main, Four Auxiliaries

- **Main — writing:** researched, fact-checked, thesis-approved, independently reviewed scripts ready for a creator to record.
- **Aux 1 — insert materials:** source-backed material preparation with provenance, rights, and factual binding.
- **Aux 2 — MG:** explicit, user-requested motion-graphic generation.
- **Aux 3 — Illustrated Metaphor / 小黑漫画:** explicit, user-requested illustrated explanation.
- **Aux 4 — Hand-drawn Animation:** explicit, user-requested hand-drawn explanation.

The generated visual auxiliaries run only when the creator explicitly names one family. DeepTalk does not automatically choose a family, rank a winner, resolve overlaps, edit an NLE project, or publish a finished video.

## What It Does Not Do

- choose takes, delete pauses/re-records, alter A-roll, or synthesize a talking edit;
- choose a final visual winner, resolve visual overlap, generate a 剪映/NLE project, or assemble a final cut;
- output a final finished video or publish it;
- treat generated imagery as evidence, fabricate timings, or turn one episode's feedback into an automatic global rule.

## Simplest Use

Open this repository in Codex and use ordinary language:

> 今天讲什么？

> 研究“你想研究的话题”，生成 Research Report。

> 确认进入写稿，做成 8 分钟的口播稿。

> 给这期配素材。

> 我已经完成最终 Clean A-roll，帮我生成素材包和剪辑表。

The repository skills and contracts guide the necessary gates. Private research, scripts, A-roll, media, assets, and finished cuts remain local and gitignored.

## Current Development State

The accepted and implemented V1 path includes Content Thesis and Script V1, local `whisper.cpp` `large-v3` ASR, alignment, Semantic Timeline, V1 Visual Director, Asset Pack + Edit Map, Finished Cut Review, and explicit access to the three generated visual plugins. A `v1.0.0` release candidate has been prepared for Nexus review; no version later than v0.6.1 has been tagged or released.

The accepted product direction is **Multi-Asset Studio**: `Semantic Timeline → Visual Opportunity → non-exclusive Candidate Portfolio → Candidate Asset Pack → Multi-option Edit Map → creator selection`. Its ecosystem is multi-repo and plugin-first: families evolve independently behind a stable Core boundary. Contract V1, Core Phases 0–4, and Phase 5 real three-plugin synthetic integration are all **ACCEPTED / IMPLEMENTED_UNRELEASED**. Phase 5 exact-pins MG, Illustrated Metaphor, and Hand-drawn runners. Production migration and production default have not started.

**Phase 6** (《牛来》 Owner-visible Micro Demo) is **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** on branch `agent/phase6-niulai-owner-demo` at `b72b7c2`. It is not PASS, ACCEPTED, MERGED, PRODUCTION, or RELEASED.

**Product Architecture V2** is **PASS / ACCEPTED**. Compatibility foundations (Phase A), the WHERE boundary (Phase B), and the WHEN Placement Planner (Phase C) are accepted and integrated, but remain unreleased and are not v1.0 production prerequisites. Phase D/E/F orchestration migration, REAL_MATERIAL migration, and production adoption have not started. See [Product Architecture V2](docs/plans/2026-09-07-product-architecture-v2.md).

MG Quality V2 is approved next but unimplemented. The v1.0 Hand-drawn and Illustrated Metaphor capabilities are explicit, disabled-by-default plugin paths; this does not claim ownership of third-party character IP.

## Documentation

Start with [PROJECT_STATE.md](PROJECT_STATE.md), then follow [docs/INDEX.md](docs/INDEX.md). The index identifies the canonical owner for product state, requirements, architecture, contracts, releases, and historical records.

## Local Verification

The repository is Python 3.9+ and generally needs no third-party Python packages for its basic checks.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
./scripts/deeptalk sample
./scripts/deeptalk validate examples/sample-research-report.json
```

Task-specific commands and contracts are listed in [AGENTS.md](AGENTS.md) and [docs/INDEX.md](docs/INDEX.md).

## Privacy and Safety

Do not commit private A-roll, finished cuts, raw research, competitor media, large binaries, model files, caches, or secrets. Evidence, rights, timing, and QA gates fail closed rather than quietly inventing an answer.
