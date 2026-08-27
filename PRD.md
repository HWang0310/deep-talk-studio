# DeepTalk Studio Product Requirements

> **Canonical owner:** current accepted product requirements and hard boundaries. Read [PROJECT_STATE.md](PROJECT_STATE.md) first for release/development state, and [ROADMAP.md](ROADMAP.md) for status classification. Historical milestones appear at the end; they do not override Parts A–D.

## Part A — Current Product

### Product purpose

DeepTalk Studio serves creators making human-led, deep spoken videos. It turns a defensible topic into a reviewed script and then prepares evidence-bound visual material with precise placement suggestions against the creator's final clean A-roll.

The product is successful when:

- a Reviewed Script is worth recording;
- an Asset Pack contains material the creator genuinely wants to use; and
- the creator understands where each material could fit against real A-roll.

It is not successful merely because a complete video can be generated.

### Users and roles

| Role | Responsibility |
|---|---|
| Creator / user | Content judgment, human confirmation, recording, final material selection, and final NLE aesthetic decisions. |
| ChatGPT | Product manager, architect, and reviewer. |
| Codex | Engineer and operator. |

### Implemented V1 workflow — accepted, unreleased

```text
Topic Discovery / Topic
→ Research → independent Fact Check
→ Content Thesis → human thesis confirmation
→ Reviewed Script
→ Final Clean A-roll → local ASR → Alignment → Semantic Timeline
→ V1 Visual Director → asset generation and individual QA
→ Asset Pack + Edit Map → creator manual NLE assembly
→ Finished Cut Review + Production Feedback
```

Requirements:

- Research must retain source provenance, fact status, counter-evidence, uncertainty, and an independent fact-check step.
- A Content Thesis must pass its gate and receive ordinary-language human confirmation before Script V1 is created.
- Reviewed Script must pass factual safety and Script Quality Gates; approval does not create an A-roll or start visual work.
- Only Final Clean A-roll can supply production timing. Script estimates, draft timings, and fixtures cannot become final placement time.
- Local ASR and alignment fail closed on missing, out-of-range, or overlapping timing evidence.
- Material, rights, factual binding, asset QA, and immutable lineage remain required.
- Asset Pack plus Markdown Edit Map is the creator-facing delivery. CSV supports lookup/sorting; JSON is the machine contract.
- Finished Cut Review may observe plan/actual use, timing deviation, shortening/extension, and presentation changes. It remains read-only, non-judgmental, and cannot change the finished cut.

### Current V1 visual semantics

V1 uses one decision per real semantic span: `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, or `ADVANCED_MOTION`. `KEEP_A_ROLL` is a legitimate historical and current V1 artifact. `REAL_MATERIAL` is evidence/documentary material, not a generated-family substitute.

Historical full-video/Aligned Preview remains a compatibility, QA, and optional preview capability. It is not the primary delivery or a promise of a finished video.

## Part B — Hard Product Boundaries

DeepTalk must not:

- automatically select takes, remove pauses/re-records, delete or alter A-roll, splice human speech, or substitute a synthetic presenter;
- select a final visual winner, resolve overlap, choose a track, or decide a creator's final material;
- generate 剪映/NLE projects, automatically assemble/finalise a video, output a final cut, or publish;
- use generated image/animation as documentary evidence, fabricate source/provenance, weaken rights review, or invent real timing;
- treat one episode's feedback as an automatic global product rule;
- claim Xiaohei as DeepTalk-owned IP or bind DeepTalk's long-term identity to a third-party character.

A-roll is the creator's base layer. DeepTalk contributes optional material and placement guidance, not an autonomous edit.

## Part C — Current V1 Candidate / Accepted Unreleased

The following are implemented in the repository and accepted on the V1 Candidate path, but are **not a formal release**:

- Topic Discovery, Research, independent Fact Check, and approval gates.
- Content Director + Script Agent V1, including Content Thesis, human confirmation, reviewed script, and quality checks.
- Final Clean A-roll gate, local `whisper.cpp` `large-v3` ASR, global monotonic alignment, and Semantic Timeline.
- V1 Visual Director, material/asset QA, Asset Pack + Edit Map, and Finished Cut Review + Production Feedback.

The latest formal release remains `v0.6.1`. “Implemented” never means “released.”

## Part D — Accepted Next and Experiments

### Multi-Asset Studio — accepted direction, implementation not started

The accepted target abstraction is:

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio
→ family-specific Candidate Asset Generation → Candidate QA
→ Candidate Asset Pack → Multi-option Edit Map → creator manual NLE selection
```

Requirements for the future implementation:

- Candidate assets are non-exclusive. Multiple candidates can overlap fully or partly, have different durations, and come from different families.
- `suggested_review_order` (or equivalent) may tell a creator what to inspect first; it must never mean that the machine chose a winner.
- No Visual Opportunity means no additional asset. New candidate planning removes `KEEP_A_ROLL` as an outcome, but V1 readers/adapters and immutable historical lineage remain compatible.
- `REAL_MATERIAL` remains an independent evidence/documentary family. Generated explanation families do not replace it.
- Machine records must preserve failed/blocked/unavailable/QA-rejected candidates. Creator-facing packs default to READY candidates only. Final enum and schema design are still pending.
- The product maximises useful choice density, not file count. LEAN/STANDARD/RICH are soft profiles only; no fixed opportunity/candidate count is a schema invariant.

This direction is accepted; V2 contracts, schemas, migrations, and implementation have **not** begun.

### Approved next / experimental work

| Direction | Status | Requirement boundary |
|---|---|---|
| MG Quality V2 | Approved next; not implemented | Improve art direction, composition, typography, hierarchy, motion grammar, easing, transitions, primitives, and density before increasing volume. |
| Hand-drawn Animation | Approved V1 experiment | Not an implemented production renderer. |
| Xiaohei | Prototype / experimental | Upstream is static illustration/shot-list oriented, not a ready video system; preserve licence/attribution and do not claim IP ownership. |
| Original DeepTalk visual identity | Undecided | Do not assume an original character exists. |

## Part E — Historical Milestones

These milestones preserve lineage; their earlier success criteria are not automatically current requirements.

- **v0.1–v0.4.1:** research, fact check, topic discovery, original-script workflow, and gate hardening.
- **v0.5–v0.5.1:** material search, provenance/rights safeguards, and material gate hardening.
- **v0.6–v0.6.1:** Motion Production Layer and formal release.
- **V1 Candidate:** A-roll alignment, visual planning, Asset Pack + Edit Map, Finished Cut Review, and real-episode validation.
- **Historical preview path:** rough/full preview output provided valuable QA evidence but is no longer the primary creator outcome.

For detailed historical work, use [HANDOFF.md](HANDOFF.md), [CHANGELOG.md](CHANGELOG.md), [docs/releases](docs/releases/), and [docs/superpowers](docs/superpowers/).
