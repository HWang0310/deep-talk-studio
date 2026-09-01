# DeepTalk Studio

**Latest Formal Release:** [`v0.6.1`](docs/releases/v0.6.1.md) (`8a0ac94`)

**Development:** **V1.0 Candidate — Unreleased**

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

The accepted and implemented V1 path includes Content Thesis and Script V1, local `whisper.cpp` `large-v3` ASR, alignment, Semantic Timeline, V1 Visual Director, Asset Pack + Edit Map, and Finished Cut Review. This work is unreleased; no version later than v0.6.1 has been tagged or released.

The next accepted product direction is **Multi-Asset Studio**: `Semantic Timeline → Visual Opportunity → non-exclusive Candidate Portfolio → Candidate Asset Pack → Multi-option Edit Map → creator selection`. Its ecosystem is multi-repo and plugin-first: families evolve independently behind a stable Core boundary. Contract V1 and Core Phases 0–2 are accepted/implemented-unreleased. The first MG runner is accepted and exact-pinned; Core Phase 3A-2 single-MG synthetic integration is implemented-unreleased and awaiting ChatGPT review. Candidate Pack, multi-plugin integration, production migration, and production default have not started.

MG Quality V2 is approved next but unimplemented. Hand-drawn Animation is an approved V1 experiment. Xiaohei is prototype/experimental only and is not DeepTalk-owned IP.

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
