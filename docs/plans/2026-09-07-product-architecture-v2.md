---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '9860a193-e900-4dac-b237-3d947e789a4f'
  PropagateID: '9860a193-e900-4dac-b237-3d947e789a4f'
  ReservedCode1: 'a0de461b-a73c-436c-a004-9610bdbcd176'
  ReservedCode2: 'a0de461b-a73c-436c-a004-9610bdbcd176'
---

# DeepTalk Product Architecture V2 — Design & Migration Document

> **Task ID:** DT-ARCH-V2-001
> **Branch:** `agent/product-architecture-v2`
> **Base SHA:** `db172cecc60ca6b0c276ec42010b113a767bc7b3` (Phase 5 accepted)
> **Status:** OWNER_APPROVED_DIRECTION / AWAITING_NEXUS_ARCH_REVIEW — Owner has approved the product direction; specific architecture design (migration matrix, adapter strategy, Contract V2 proposal, Placement Planner details, phased plan) has not yet received Nexus PASS. No runtime, schema, or code implementation.
> **Date:** 2026-09-07 (`Asia/Shanghai`)

---

## 0. Risk Restatement / Plan Gate

Before writing any architecture content, I restate my understanding of Owner-approved facts to confirm alignment.

### 0.1 DeepTalk Content Core boundary

DeepTalk 本体 = 内容创作产品：选题 → Research → Fact Check → Content Thesis → human confirmation → Reviewed Script。它的核心目标是帮创作者把事情想清楚、研究清楚、讲清楚。DeepTalk 本体**不负责**视频剪辑和视觉素材生产。

### 0.2 A-roll-first 原则

Final Clean A-roll 是视频质量基础，永远是 base layer。所有视觉素材（真实素材、MG、插画、手绘动画、图表、地图、AI Video 等）都只是建立在口播母片上的**可选视觉增强层**。禁止自动选 take、删除停顿/重录、裁剪/拼接 A-roll、重排讲话、修改人物讲话、生成替代人物口播。

### 0.3 WHERE → WHAT → WHEN 拆分

- **WHERE**（Visual Opportunity Detection）：判断"哪里值得增加视觉辅助"，只判断是否存在视觉机会及其目的，不能决定"这里必须用 MG"。
- **WHAT**（Asset Plugins）：回答"这里有哪些视觉表达方案"。各插件可 SUITABLE / BORDERLINE / ABSTAIN，插件之间没有自动赢家。
- **WHEN**（Placement Planner）：回答"某个具体 Candidate 最适合什么时候进入和退出"。Visual Opportunity 时间窗 ≠ 具体 Candidate 的 placement 时间窗。

### 0.4 保留的现有能力

Suitability、ABSTAIN、failure isolation、Candidate、Candidate Portfolio、Candidate QA、Candidate Asset Pack、Multi-option Edit Map、creator none/one/multiple choice——全部保留。禁止自动 winner selection、overlap resolution、final material choice。

### 0.5 Visual Director 不是简单删除历史

Current V1 Visual Director 仍是已实现的历史/current V1 能力。V2 将其职责拆分为 A-roll Understanding、Visual Opportunity Detection、Asset Provider 调用、Candidate aggregation/QA、Placement Planning——而不是删除。历史 `visual-director-plan/1` artifacts 通过 compatibility reader 保留。

### 0.6 REAL_MATERIAL 迁移但保留安全能力

"找真实素材"从 DeepTalk Core 的特殊功能迁移为标准 Real Material Asset Provider。但 source provenance、factual binding、rights/reuse review、actual inspection evidence、Evidence/Context/Illustration 区分、research_update_required、material QA、immutable lineage 全部保留。这是职责迁移，不是安全体系重写。

### 0.7 本 Task 明确不会实施的代码变更

本 Task **不修改**：runtime source、production code、renderer code、plugin runner、schemas 的实际 runtime adoption、production workflow、MG/Illustrated/Hand-drawn 插件、plugin pins、tests for new runtime behavior、Phase 6 code/state、main、release、tag。只产出文档和迁移设计。

### 0.8 计划修改的 canonical docs

| File | Why |
|---|---|
| `PROJECT_STATE.md` | 新增 Product Architecture V2 accepted design 状态 |
| `PRD.md` | 新增 Part D+ 产品方向：WHERE→WHAT→WHEN、插件统一、REAL_MATERIAL 插件化 |
| `ROADMAP.md` | 新增 V2 architecture 的 current/next/deferred 分类 |
| `docs/ARCHITECTURE.md` | 新增 V2 target architecture 与 Visual Director decomposition |
| `docs/INDEX.md` | 路由到新设计文档 |
| `docs/plans/2026-09-07-product-architecture-v2.md` | 本文件：完整设计文档 |

### 0.9 Conflict check

以上 restatement 与 Owner-approved facts 无实质冲突。Proceeding to design.

---

## 1. Product Module Responsibility Map

### 1.1 DeepTalk Content Core

| Aspect | Detail |
|---|---|
| Responsible for | Topic discovery, Research, independent Fact Check, Content Thesis, human confirmation, Reviewed Script. Helping the creator think clearly, research clearly, and communicate clearly. |
| Not responsible for | Video editing, visual asset production, placement planning, NLE output. |
| Main input | Topic / discovery seeds, source materials, creator confirmations. |
| Main output | Approved Research revision, Reviewed Script (immutable, digest-bound). |
| Boundary | Script exits Content Core; Final Clean A-roll is a separate gate. Visual work begins only after A-roll exists. |

### 1.2 Final Clean A-roll / A-roll Foundation

| Aspect | Detail |
|---|---|
| Responsible for | Canonical base layer. All production timing derives from this audio. Creator-owned and creator-recorded. |
| Not responsible for | Any visual layer or edit decision. |
| Main input | Creator recording. |
| Main output | Final Clean A-roll audio/media (local, gitignored). |
| Boundary | DeepTalk may diagnose A-roll issues (read-only) but must never alter it. |

### 1.3 A-roll Understanding

| Aspect | Detail |
|---|---|
| Responsible for | ASR transcription, global monotonic alignment, canonical time establishment, Semantic Timeline generation. |
| Not responsible for | Visual opportunity decisions, asset generation, placement. |
| Main input | Final Clean A-roll, reviewed script (for alignment reference). |
| Main output | `semantic-timeline/1` artifact with real start/end seconds, span summaries, alignment status. |
| Boundary | Exits at Semantic Timeline; Visual Opportunity Detection consumes timeline but does not modify it. |

### 1.4 Semantic Timeline

| Aspect | Detail |
|---|---|
| Responsible for | Ordered, real-A-roll-anchored semantic spans with `actual_start_seconds`, `actual_end_seconds`, `summary`, `alignment_status`. |
| Not responsible for | Interpreting which spans need visual treatment. |
| Main input | Alignment result + transcript. |
| Main output | `semantic-timeline/1` artifact ( immutable, digest-bound). |
| Boundary | Timing provenance must be `actual_aroll_alignment`; estimates and fixtures are forbidden. |

### 1.5 Read-only A-roll Review / Readiness

| Aspect | Detail |
|---|---|
| Responsible for | Diagnosing obvious hesitations, repeated expressions, abnormal pace, audio issues, logic gaps, significant deviation from reviewed script, and whether re-recording is worthwhile. |
| Not responsible for | Modifying A-roll, selecting takes, deleting pauses, auto-cleanup, or blocking production. |
| Main input | Final Clean A-roll, Semantic Timeline, Reviewed Script. |
| Main output | Diagnostic report + suggestions (read-only). |
| Boundary | Diagnosis + suggestion only. The creator decides whether to re-record. No automatic A-roll modification. |

### 1.6 Visual Opportunity Detection (WHERE)

| Aspect | Detail |
|---|---|
| Responsible for | Answering "where is visual assistance worth adding?" and "what is the visual purpose?" Only detecting opportunities and their purposes. |
| Not responsible for | Deciding which visual family/type to use. Does not decide "this must be MG." |
| Main input | Semantic Timeline, Reviewed Script, approved Research context. |
| Main output | Visual Opportunity artifacts with `opportunity_id`, `a_roll_window`, `spoken_semantics`, `visual_purpose`, `target_duration_ms`. |
| Boundary | No opportunity = no additional asset. Opportunity time window ≠ candidate placement time window (that belongs to Placement Planner). |

### 1.7 Asset Plugins (WHAT)

| Aspect | Detail |
|---|---|
| Responsible for | Answering "what visual expression options exist here?" Each plugin independently assesses suitability (SUITABLE / BORDERLINE / ABSTAIN) and generates candidates when requested. |
| Not responsible for | Deciding when a candidate enters/exits the final video. Selecting winners. Resolving overlaps. |
| Main input | Visual Opportunity (from WHERE stage), approved factual context. |
| Main output | Suitability proposals, generation results, candidate artifacts (media, manifest, QA, provenance). |
| Boundary | Plugins include: REAL_MATERIAL, MG, Illustrated Metaphor, Hand-drawn, Chart, Map, AI Video, future families. No plugin has Core-special status. Core does not depend on plugin internals. |

### 1.8 Candidate Portfolio

| Aspect | Detail |
|---|---|
| Responsible for | Aggregating all READY candidates from all plugins for all opportunities, non-exclusively. Preserving audit records for every suitability/generation call. |
| Not responsible for | Selecting a winner. Resolving overlap. Ranking candidates. |
| Main input | Generation results from all plugins, Core acceptance checks. |
| Main output | `candidate-portfolio/1` artifact with audit records, candidates, immutable IDs. |
| Boundary | Portfolio never chooses. Creator may use none, one, or multiple. |

### 1.9 Placement Planner (WHEN)

| Aspect | Detail |
|---|---|
| Responsible for | Answering "when should a specific candidate enter and exit?" Producing placement recommendations per candidate, distinct from the Visual Opportunity time window. |
| Not responsible for | Deciding what visual to produce. Selecting winners. Auto-editing. Resolving final material choice. |
| Main input | Candidate Portfolio, Visual Opportunities, A-roll windows, candidate intrinsic duration/timing hints. |
| Main output | Placement recommendations (start/end per candidate within or relative to the opportunity window). |
| Boundary | Placement Planner is a Studio Host capability, not a plugin capability. It uses but does not override candidate identity, produced media, QA, or provenance. This is a V2 target design — not yet implemented. |

### 1.10 Candidate Asset Pack

| Aspect | Detail |
|---|---|
| Responsible for | Packaging READY candidates into a creator-facing bundle with staged media, edit-map entries, and provenance. |
| Not responsible for | Choosing which candidate the creator should use. Generating NLE projects. |
| Main input | Candidate Portfolio, staged media. |
| Main output | `candidate-asset-pack/1` with per-opportunity candidate blocks and primary media. |
| Boundary | Pack is the delivery boundary. Creator takes over in NLE after this. |

### 1.11 Multi-option Edit Map

| Aspect | Detail |
|---|---|
| Responsible for | Providing JSON/CSV/Markdown edit-map entries with real A-roll time, semantic context, candidate list, placement, and provenance. |
| Not responsible for | Selecting which entry the creator uses. Auto-assembling a cut. |
| Main input | Candidate Asset Pack, placement recommendations. |
| Main output | `candidate-edit-map/1` (JSON machine contract, CSV lookup, Markdown creator-facing). |
| Boundary | Edit Map explicitly permits none, one, or multiple candidates per opportunity. No winner selection. Legacy `edit-map/1` preserved through compatibility reader. |

### 1.12 Finished Cut Review

| Aspect | Detail |
|---|---|
| Responsible for | Read-only observation of planned vs actual material use, timing deviation, shortening/extension. |
| Not responsible for | Modifying the finished cut. Assigning aesthetic quality. Generating global policy from one episode. |
| Main input | Creator's finished cut, Candidate Asset Pack / Edit Map, Semantic Timeline. |
| Main output | `finished-cut-review/1` + `production-feedback/1` (read-only). |
| Boundary | Cannot change media, output replacement, generate NLE project, or convert one episode into global policy. |

### 1.13 Studio Host / Common Infrastructure

| Aspect | Detail |
|---|---|
| Responsible for | Episode/project identity, canonical A-roll identity, canonical timebase, canonical timeline, artifact IDs/lineage, plugin registration/loading boundary, contract validation, artifact storage, Candidate Portfolio identity, shared safety/QA policy, provenance/digest/runtime safety framework, failure isolation, ABSTAIN semantics, packaging. |
| Not responsible for | Visual content generation (that belongs to plugins). Content thesis/script (that belongs to Content Core). |
| Main input | Configuration, plugin registrations, all stage artifacts. |
| Main output | Immutable artifact storage, validated lineage, safe runtime environment. |
| Boundary | Studio Host owns the shared truth; plugins own their visual capability. See §6 for detailed boundary reasoning. |

---

## 2. Current → V2 Migration Matrix

| Current capability | V2 disposition | Notes |
|---|---|---|
| Topic Discovery | **KEEP** | Content Core capability, unchanged. |
| Research | **KEEP** | Content Core capability, unchanged. |
| Fact Check | **KEEP** | Content Core capability, unchanged. |
| Content Thesis | **KEEP** | Content Core capability, unchanged. |
| Script (V1) | **KEEP** | Content Core capability, unchanged. |
| Final Clean A-roll Gate | **KEEP** | A-roll Foundation, unchanged. |
| ASR | **KEEP** | A-roll Understanding, unchanged. |
| Alignment | **KEEP** | A-roll Understanding, unchanged. |
| Semantic Timeline | **KEEP** | A-roll Understanding, unchanged. |
| V1 Visual Director | **SPLIT** | Decomposed into: Visual Opportunity Detection (WHERE) + Asset Plugin orchestration + Candidate aggregation/QA + Placement Planning (WHEN). `visual-director-plan/1` preserved via compatibility reader. |
| Visual Opportunity | **RECLASSIFY** | Already exists as `visual-opportunity/1` in Contract V1 path; V2 elevates it to the primary WHERE stage output. |
| REAL_MATERIAL | **MIGRATE** | From V1 Visual Director decision to standard Real Material Asset Provider plugin. Retains provenance, rights, factual binding, inspection evidence. |
| MG | **RECLASSIFY** | From V1 `MG_MOTION` decision to standard MG Asset Provider plugin (already done in Contract V1 / Phase 5). |
| Illustrated Metaphor | **RECLASSIFY** | Already a standard plugin under Contract V1. |
| Hand-drawn Animation | **RECLASSIFY** | Already a standard plugin under Contract V1. |
| Candidate Portfolio | **KEEP** | Existing `candidate-portfolio/1` retained. |
| Candidate QA | **KEEP** | Per-candidate QA + Core acceptance, retained. |
| Candidate Asset Pack | **KEEP** | Existing `candidate-asset-pack/1` retained. |
| `candidate-edit-map/1` | **KEEP** | Existing multi-option edit map retained. |
| Legacy `edit-map/1` | **LEGACY_COMPAT_ONLY** | V1 single-decision edit map. Preserved through compatibility reader. No new V2 writes. |
| `KEEP_A_ROLL` | **LEGACY_COMPAT_ONLY** | V1 decision meaning "no visual." V2 represents this as "no Visual Opportunity." Existing `KEEP_A_ROLL` artifacts preserved through compatibility reader. |
| Finished Cut Review | **KEEP** | Read-only review, unchanged. |
| Material Search | **MIGRATE** | From Core special function to REAL_MATERIAL plugin's retrieval capability. Search → suitability → retrieval → rights/factual QA → candidate. |
| Provenance | **KEEP** | All provenance types retained. REAL_MATERIAL provenance is richer than generated-plugin provenance (see §4.9). |
| Rights/reuse | **KEEP** | Rights/reuse review remains mandatory for REAL_MATERIAL. Generated plugins have simpler provenance but do not bypass rights. |
| Factual binding | **KEEP** | Factual binding remains mandatory for all candidates that make factual claims. |

---

## 3. Contract Migration Analysis

### 3.1 Current `suggested_placement` coupling

In `visual-asset-plugin-contract/1`, every READY candidate requires a `suggested_placement` field (see `visual_asset_plugin_contract.py` line 145). This means the Asset Plugin simultaneously participates in:

- **WHAT** (producing the visual asset)
- **WHEN** (recommending when it should appear)

This coupling exists because Contract V1 was designed before the Placement Planner existed as a separate concept. The plugin provides a placement recommendation as a convenience, since the plugin knows the candidate's intrinsic duration and natural timing. However, this creates a semantic problem: the placement decision should ultimately belong to a Studio Host capability (Placement Planner), not to the asset producer.

### 3.2 What continues to belong to the Asset Plugin

The following candidate fields remain Asset Provider owned:

| Field | Why it stays |
|---|---|
| `candidate_id` | Plugin-produced identity. |
| `asset_family` | Plugin-owned display/category. |
| `candidate_status` | Plugin-produced QA result. |
| `duration_ms` | Actual duration of produced media — a physical fact. |
| `artifacts` | Produced media bundle (PRIMARY_MEDIA, PREVIEW, MANIFEST, QA_REPORT). |
| `qa` | Plugin-internal QA evidence. |
| `provenance` | Plugin-generated origin and source reference. |
| `plugin_metadata` | Opaque plugin-internal detail. |

### 3.3 What migrates to Placement Planner

The following information should eventually migrate to Placement Planner ownership:

| Field | Migration target |
|---|---|
| `suggested_placement` (start_ms, end_ms) | Placement Planner produces the authoritative placement recommendation per candidate, considering: (a) candidate intrinsic duration, (b) opportunity A-roll window, (c) candidate timing hints, (d) cross-candidate context. |
| Future placement metadata (transition, alignment style, etc.) | Placement Planner. These do not exist in V1 and are deferred (see Owner directive #12). |

### 3.4 Legacy `suggested_placement` compatibility path

**Existing `visual-asset-plugin-contract/1` artifacts are immutable.** The `suggested_placement` field in existing candidates must continue to be readable by:

1. `candidate-portfolio/1` readers (audit records).
2. `candidate-asset-pack/1` readers.
3. `candidate-edit-map/1` writers (which currently read `suggested_placement` to populate edit-map entries).

Legacy compatibility path:
- Existing Contract V1 artifacts remain valid and readable.
- A future `visual-asset-plugin-contract/2` (or an extended V1.x) may make `suggested_placement` optional or rename it to `intrinsic_placement_hint`.
- The Placement Planner reads existing `suggested_placement` as an input hint, not as the final placement decision.
- New writers use Placement Planner for placement; old readers continue to find `suggested_placement` in legacy artifacts.

### 3.5 Contract versioning strategy

Recommendation: **versioned contract + adapter**, not rewrite.

- `visual-asset-plugin-contract/1` remains frozen and valid.
- A future `visual-asset-plugin-contract/2` (when implemented) changes `suggested_placement` from required to optional for READY candidates, and introduces an `intrinsic_timing_hints` field for plugin-owned natural timing information.
- Core maintains a `ContractV1ToV2Adapter` that reads V1 artifacts and maps `suggested_placement` to `intrinsic_placement_hint` for the Placement Planner.
- No existing artifact is rewritten. The adapter is a reader, not a mutator.

### 3.6 Why historical artifacts should not be rewritten

1. **Immutable lineage is a core architectural principle** — digests, IDs, and audit records must remain verifiable.
2. **Rewriting artifacts breaks Finished Cut Review** — historical reviews reference specific artifact versions and digests.
3. **Rewriting artifacts breaks provenance chains** — candidate → proposal → opportunity → timeline linkage is digest-bound.
4. **Compatibility readers are cheaper and safer** than mutation — a reader adapter costs O(1) maintenance per artifact version.

### 3.7 REAL_MATERIAL retrieval/provider characteristics

REAL_MATERIAL is fundamentally different from generated plugins:

| Aspect | Generated plugins (MG, Illustrated, Hand-drawn) | REAL_MATERIAL |
|---|---|---|
| Source | Plugin-generated from semantic intent. | Retrieved from external sources via search. |
| Provenance | `origin: "plugin-generated"`, `source_ref: "plugin-native manifest"`. | Multi-layer: search provenance (discovered/inspected), source provenance (publisher, URL, capture), rights provenance (license, rights_evidence_url). |
| Rights | Generated → no external rights issue. | Must verify rights/reuse status from actual opened source pages. |
| Factual binding | May reference approved facts via `factual_context`. | Must bind to specific Claim/Evidence; Evidence vs Context vs Illustration distinction is mandatory. |
| QA | Mechanical QA (format, duration, dimensions, SHA). | Mechanical QA + factual QA + rights QA + capture metadata QA. |
| Failure modes | FAILED, BLOCKED, UNAVAILABLE (generation). | FAILED, BLOCKED, UNAVAILABLE (retrieval) + rights_rejected, factual_conflict, research_update_required. |

REAL_MATERIAL needs its own retrieval/provider contract extension because:
1. It has a search/retrieval stage that generated plugins do not have.
2. It has rights/factual obligations that generated plugins do not have.
3. It has Evidence/Context/Illustration classification that generated plugins do not produce.

### 3.8 Shared Candidate envelope fields

REAL_MATERIAL and generated plugins can share these Candidate envelope fields:

| Shared field | Notes |
|---|---|
| `candidate_id` | Same identity scheme. |
| `asset_family` | `"REAL_MATERIAL"` vs `"MG"` etc. |
| `candidate_status` | Same READY / QA_REJECTED. |
| `duration_ms` | Same physical fact. |
| `artifacts` | Same role-based bundle (PRIMARY_MEDIA, PREVIEW, MANIFEST, QA_REPORT). |
| `qa` | Same QA status structure (but REAL_MATERIAL QA has additional dimensions). |
| `suggested_placement` / `intrinsic_timing_hint` | Same placement hint structure. |

### 3.9 Provenance / rights / evidence that cannot be abstracted away

The following REAL_MATERIAL-specific fields and obligations **cannot** be replaced by the generated-plugin `provenance` abstraction:

| REAL_MATERIAL obligation | Why it cannot be abstracted |
|---|---|
| `source_provenance` (publisher, URL, discovered_at, inspected_at) | Documents where the material came from in the real world. Generated plugins have no real-world source. |
| `rights_provenance` (license, rights_evidence_url, reuse_status) | Legal reuse rights. Generated assets do not require external rights verification. |
| `capture_metadata` (page number, region, context, caption, format verification) | Proves the material was actually inspected, not fabricated. Generated plugins fabricate by design. |
| `factual_binding` (Claim ID, Evidence ID, Evidence/Context/Illustration classification) | Binds material to approved research. Generated plugins may reference facts but do not serve as evidence. |
| `research_update_required` | Signals that material search discovered new/conflicting information. Generated plugins cannot trigger this. |
| `material_type` (Evidence / Context / Illustration) | Documentary classification. Generated plugins produce illustration only. |

A REAL_MATERIAL contract extension must carry these as first-class fields or structured metadata, not as opaque `plugin_metadata` that Core cannot read. Core needs to verify rights/factual compliance for REAL_MATERIAL candidates in a way it does not for generated candidates.

---

## 4. Visual Director Decomposition

### 4.1 Current V1 Visual Director responsibilities

The V1 `visual_director.py` `build_visual_director_plan()` currently:

1. Validates alignment binding (A-roll timing).
2. Processes proposals with `cue_id` → real time range mapping.
3. Makes one decision per span: `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, or `ADVANCED_MOTION`.
4. Outputs `visual-director-plan/1` with `opportunity_id`, `decision`, `visual_intent`, `why_visual`.

This is a **single-decision central planner** — it simultaneously decides WHERE, WHAT, and implicitly WHEN.

### 4.2 V2 decomposition

| V1 responsibility | V2 destination | Type |
|---|---|---|
| Validate alignment binding | A-roll Understanding | **Studio Host** — canonical timebase validation. |
| Process proposals with real time | Visual Opportunity Detection (WHERE) | **Studio Host** — opportunity creation from timeline. |
| `KEEP_A_ROLL` decision | "No Visual Opportunity" | **Studio Host** — absence of opportunity = no additional asset. |
| `REAL_MATERIAL` decision | REAL_MATERIAL Asset Plugin suitability + generation | **Plugin Capability** — plugin decides if it can serve the opportunity. |
| `MG_MOTION` decision | MG Asset Plugin suitability + generation | **Plugin Capability** — plugin decides. |
| `ADVANCED_MOTION` decision | Future asset plugin (or Hand-drawn / future family) | **Plugin Capability** — plugin decides. |
| `visual_intent` / `why_visual` | Visual Opportunity `visual_purpose` and `spoken_semantics` | **Studio Host** — opportunity payload. |
| Placement within span | Placement Planner (WHEN) | **Studio Host** — separate from opportunity window and from plugin. |

### 4.3 Studio Host vs Plugin Capability

| Responsibility | Owner | Why |
|---|---|---|
| Canonical A-roll identity and timebase | Studio Host | Shared truth — all modules depend on same timing. |
| Semantic Timeline | Studio Host | Shared truth — all visual work references same spans. |
| Visual Opportunity Detection | Studio Host | WHERE is a product judgment about the A-roll, not a plugin capability. No plugin should be the sole arbiter of "where." |
| Opportunity → Plugin dispatch | Studio Host | Core orchestrates which plugins receive which opportunities. Plugins do not self-dispatch. |
| Plugin subprocess supervision | Studio Host | Failure isolation, timeout, result validation — all Core owned. |
| Candidate Portfolio identity and storage | Studio Host | Non-exclusive aggregation requires a neutral party. |
| Candidate acceptance / QA policy | Studio Host | Shared safety gates (provenance, digest, format) are Core owned. Plugin QA is a subset. |
| Placement Planning | Studio Host | WHEN is a cross-candidate, cross-opportunity concern. A single plugin cannot plan placement for candidates it does not own. |
| Asset Pack and Edit Map packaging | Studio Host | Creator-facing delivery must be neutral and complete. |
| Suitability judgment | Plugin | Only the plugin knows its own capability boundary. |
| Generation / media production | Plugin | Only the plugin produces visual content. |
| Plugin-internal QA | Plugin | Plugin owns its mechanical/structural QA rubric. |
| Scene grammar / renderer internals | Plugin | MG grammar, Illustrated scene model, Hand-drawn primitives — all plugin-private. |

---

## 5. Studio Host / Kernel Boundary

### 5.1 What Studio Host must own (and why)

| Capability | Why Studio Host owns it |
|---|---|
| Episode / project identity | All artifacts must trace to one episode. Plugins cannot self-assign episode identity. |
| Canonical A-roll identity | All timing derives from one A-roll. Plugins cannot declare their own A-roll. |
| Canonical timebase | All modules must reference the same monotonic time. No plugin may create its own time. |
| Canonical timeline | `semantic-timeline/1` is shared input. Plugins consume it; they do not produce it. |
| Artifact IDs | `opportunity_id`, `candidate_id`, `proposal_id`, `request_id` — all Core-assigned or Core-validated. Plugins echo, not create, these. |
| Lineage | The full chain (Opportunity → Proposal → Generation → Candidate → Portfolio → Pack → Edit Map) is Core-owned lineage. Plugins contribute links; Core owns the chain. |
| Plugin registration / loading | Which plugins are enabled, their pins, their config — all Core owned. Plugins do not self-register. |
| Contract validation | Core validates Contract V1 messages before and after plugin calls. Plugins cannot skip validation. |
| Artifact storage | Immutable, digest-bound, relocation-safe storage is Core infrastructure. Plugins do not manage storage. |
| Candidate Portfolio identity | Portfolio ID, audit records, immutable storage — all Core owned. |
| Shared safety / QA policy | Provenance verification, digest matching, format validation, failure isolation — Core-level safety that applies to all plugins. |
| ABSTAIN semantics | ABSTAIN is a normal successful outcome. Core policy (not plugin) decides whether BORDERLINE is generated. Core (not plugin) decides creator-facing pack inclusion. |
| Packaging | Asset Pack and Edit Map are creator-facing deliveries. Core owns the packaging boundary. |

### 5.2 What Studio Host must NOT own

| Capability | Why it stays with plugins |
|---|---|
| Visual content generation | Plugins produce the actual media. Core never renders. |
| Suitability judgment | Only the plugin knows what it can naturally express. |
| Plugin-internal QA rubric | MG media QA differs from Illustrated readability QA differs from Hand-drawn mechanical QA. Core must not homogenize. |
| Scene grammar / renderer internals | MG grammar, Illustrated scene model, Hand-drawn SVG primitives — all plugin-private. Core must not import them. |
| Factual content of generated visuals | Plugins translate semantic intent to visual content. Core validates factual binding but does not author visual content. |

---

## 6. Phased Implementation Plan

> **This is a plan only. No implementation is in scope for DT-ARCH-V2-001.**
> Compatibility-first. No big-bang rewrite. Each phase is additive and independently reversible.

### Phase A — Contracts, Adapters, Compatibility Readers, Tests

**Goal:** Establish the compatibility layer that allows V2 concepts to coexist with V1 artifacts without rewriting history.

**Scope:**
- Define `visual-asset-plugin-contract/2` schema (design only, not runtime adoption):
  - `suggested_placement` → optional, renamed `intrinsic_placement_hint`.
  - New `intrinsic_timing_hints` field for plugin-owned natural timing.
- Implement `ContractV1ToV2Adapter` (read-only reader that maps V1 → V2 view).
- Implement `LegacyEditMapV1Reader` (compatibility reader for `edit-map/1`).
- Implement `VisualDirectorPlanV1Reader` (compatibility reader for `visual-director-plan/1`).
- Tests: verify all existing V1 artifacts are correctly read by adapters.

**Constraint:** No existing artifact is rewritten. No production schema is changed. All existing tests must pass.

**Reversibility:** Disable adapters/readers; V1 behavior is unchanged.

### Phase B — Visual Opportunity Detection Responsibility Extraction

**Goal:** Extract WHERE as a first-class Studio Host capability, separate from V1 Visual Director.

**Scope:**
- Implement `VisualOpportunityDetector` that consumes `semantic-timeline/1` and produces Visual Opportunity artifacts.
- The detector replaces V1 Visual Director's "where" responsibility but does not make WHAT decisions.
- V1 Visual Director remains readable via compatibility reader.
- Tests: verify opportunities from same timeline are deterministic and do not encode WHAT decisions.

**Constraint:** No plugin calls. No candidate generation. Pure WHERE.

**Reversibility:** Disable detector; V1 Visual Director remains operational.

### Phase C — Placement Planner Boundary

**Goal:** Define WHEN as a separate Studio Host capability.

**Scope:**
- Implement `PlacementPlanner` (design + interface):
  - Input: Candidate Portfolio, Visual Opportunities, candidate intrinsic timing hints.
  - Output: Placement recommendations per candidate.
- Implement `PlacementPlannerV1Adapter` that reads existing `suggested_placement` from Contract V1 candidates as placement hints.
- New `candidate-edit-map/2` (or extended V1) that separates opportunity window from candidate placement.
- Tests: verify placement recommendations respect opportunity windows and candidate durations.

**Constraint:** No automatic winner selection. No overlap resolution. No NLE generation. Placement is recommendation, not decision.

**Reversibility:** Disable Placement Planner; existing `candidate-edit-map/1` with embedded `suggested_placement` remains operational.

### Phase D — Generated Asset Provider Orchestration Migration

**Goal:** Migrate MG / Illustrated / Hand-drawn from V1 Visual Director decisions to standard Contract V1 plugin invocation as the sole WHAT path.

**Scope:**
- Remove V1 `MG_MOTION` and `ADVANCED_MOTION` as Visual Director decisions for new artifacts.
- All new visual planning goes through Visual Opportunity → Contract V1 plugin invocation.
- V1 `MG_MOTION` and `ADVANCED_MOTION` artifacts preserved via compatibility readers.
- Tests: verify new path produces same portfolio semantics as Phase 5 synthetic evidence.

**Constraint:** No plugin repository changes. No plugin pin updates. Plugin runners remain as-is.

**Reversibility:** Disable new path; V1 Visual Director produces legacy artifacts.

### Phase E — REAL_MATERIAL Plugin Migration

**Goal:** Migrate REAL_MATERIAL from V1 Visual Director decision to a standard Real Material Asset Provider.

**Scope:**
- Define `real-material-plugin-contract/1` (design only):
  - Extends candidate envelope with retrieval, rights, factual binding, capture metadata.
  - Adds REAL_MATERIAL-specific suitability criteria (retrieval capability, not generation).
  - Preserves all existing Material Search, provenance, rights, factual binding, and inspection evidence obligations.
- Implement `RealMaterialPluginAdapter` that wraps existing Material Search/Review/Assets workflow as a Contract-compatible plugin.
- V1 `REAL_MATERIAL` artifacts preserved via compatibility readers.
- Tests: verify REAL_MATERIAL candidates pass enhanced QA (rights + factual + format).

**Constraint:** No weakening of provenance, rights, factual binding, or inspection evidence. The migration is a responsibility move, not a safety rewrite. Existing Material Contract and Visual Spec remain authoritative.

**Reversibility:** Disable REAL_MATERIAL plugin; V1 Material Search remains operational.

### Phase F — Production Adoption

**Goal:** Enable V2 path as the production default for new episodes.

**Scope:**
- Enable V2 Visual Opportunity Detection + Contract V1 plugins + Placement Planner as production path.
- V1 Visual Director enters LEGACY_COMPAT_ONLY for historical episodes.
- Episode-specific validation on real A-roll (Phase 6 real-episode gate).
- Creator manual NLE assembly remains the final step.

**Constraint:** No automatic editing. No winner selection. No NLE generation. No publishing. Phase 6 verdict remains HOLD_FOR_OWNER_REVIEW until separately approved.

**Reversibility:** Disable V2 path; V1 production path restored. Historical episodes unaltered.

### Phase Dependencies

```text
Phase A (contracts/adapters)
  └→ Phase B (WHERE extraction)
       └→ Phase C (WHEN boundary)
            └→ Phase D (generated plugin migration)
                 └→ Phase E (REAL_MATERIAL migration)
                      └→ Phase F (production adoption)
```

Phase A must complete first. B and C have a natural sequence but C depends on B for opportunity inputs. D and E can partially overlap once C defines the placement interface, but E depends on D's contract patterns. F depends on all prior phases.

**HOW (Presentation Planner) is explicitly deferred** from all phases. Full screen, PIP, split screen, zoom, crop, overlay, transition, and presentation style are not in V2 Phase 1 scope.

---

## 7. Known Risks and Open Questions

### 7.1 Risks

| Risk | Mitigation |
|---|---|
| Placement Planner introduction may appear to select winners | Design explicitly states: placement is recommendation, not final choice. Creator retains none/one/multiple. |
| REAL_MATERIAL plugin abstraction may weaken safety | Design explicitly preserves all provenance/rights/factual obligations as first-class, not opaque metadata. |
| Contract V2 may fragment the plugin ecosystem | V1 remains frozen and valid. V2 is additive. Adapter bridges V1 → V2. No plugin forced to upgrade. |
| Visual Director decomposition may break historical episodes | Compatibility readers preserve `visual-director-plan/1`. Historical artifacts are immutable. |
| Phase ordering may introduce gaps | Each phase is independently reversible. No phase removes V1 capability until its V2 replacement is proven. |

### 7.2 Open questions (deferred, not blocking this design)

- Exact `visual-asset-plugin-contract/2` field names and validation rules.
- Whether Placement Planner should produce a versioned artifact (`placement-plan/1`).
- How REAL_MATERIAL's retrieval stage maps to the two-stage suitability/generation lifecycle (may need a three-stage: suitability → retrieval → candidate).
- Whether `candidate-edit-map/2` is needed or `candidate-edit-map/1` can be extended.
- How future Chart/Map/AI Video families fit the contract (each needs its own evidence first).

---

## 8. No Implementation Statement

This document is design and migration analysis only. No runtime source, production code, renderer code, plugin runner, schema runtime adoption, production workflow, plugin repository, plugin pin, test for new runtime behavior, Phase 6 code/state, main, release, or tag has been modified.

`Plan exists ≠ accepted; implemented ≠ released.`