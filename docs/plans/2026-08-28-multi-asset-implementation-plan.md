# Multi-Asset Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Planning only. This plan is **AWAITING ChatGPT Implementation Plan Review**; it does not implement the runtime, schemas, adapters, output writers, or any episode work.

**Goal:** Add a local, plugin-first, multi-candidate visual-asset path that turns real-A-roll-bound Visual Opportunities into audited non-exclusive Candidate Portfolios and creator-facing Candidate Asset Packs, without changing V1 history or making edit decisions.

**Architecture:** Core owns real-time Visual Opportunities, Contract V1 validation, policy, per-plugin process supervision, Core-side acceptance checks, immutable portfolio records, and creator-facing delivery. Each plugin remains an independent repository and exposes a thin, plugin-owned Contract V1 runner; Core never imports its render, grammar, scene, or QA internals. A one-shot local subprocess uses a Core-owned job directory and JSON request/result files, allowing deterministic local output, explicit logs, and failure isolation without a registry or RPC service.

**Tech Stack:** Existing Python 3 standard-library Core and `unittest`; JSON artifacts; macOS `subprocess`, `ffprobe`, SHA-256; plugin-local Node/Python environments and their existing renderer dependencies.

**Spec:** `docs/plans/2026-08-28-visual-asset-plugin-contract-v1.md` (accepted Contract V1) and `docs/plans/2026-08-27-multi-asset-studio-repositioning.md` (accepted product direction).

## Global Constraints

- Contract messages use exactly `contract_version: "visual-asset-plugin-contract/1"`; retain accepted field names and status values.
- Core owns `opportunity_id`; the full chain is `Visual Opportunity → Suitability Proposal → Generation Request → Generation Result → Candidate`.
- `SUITABLE`, `BORDERLINE`, and normal `ABSTAIN` are completed suitability outcomes. `ABSTAIN` is neither an error nor a health failure.
- Generation operation statuses are exactly `COMPLETED`, `FAILED`, `BLOCKED`, and `UNAVAILABLE`; a produced plugin candidate is exactly `READY` or `QA_REJECTED`.
- Raw plugin `candidate_status` is immutable Contract V1 evidence. Core records independent `core_acceptance` as `ACCEPTED` or `REJECTED`; it never rewrites a plugin candidate from `READY` to `QA_REJECTED`.
- Every suggested placement satisfies `opportunity.a_roll_window.start_ms <= start_ms < end_ms <= opportunity.a_roll_window.end_ms`.
- New planning writes no `KEEP_A_ROLL`. No Visual Opportunity is the only V2 representation of “no additional asset.”
- Generated-plugin Contract V1 excludes `REAL_MATERIAL`; V1 documentary/evidence lineage remains unchanged.
- Candidate assets are non-exclusive. Core must not select a winner, resolve overlap, create NLE tracks/projects, alter A-roll, or create a finished cut.
- Existing `visual-asset-manifest/1`, `edit-map/1`, V1 Asset Packs, and `finished-cut-review/1` remain immutable and readable.
- Initial development uses only a sanitized synthetic fixture. No private or real episode is a development fixture.
- Plugin repositories are independently versioned and must not become Core imports. No dynamic marketplace, discovery service, cloud RPC, release, tag, or `main` change is in scope.

---

## 1. Verified Baseline and Scope

### Core baseline actually inspected

- Base branch: `agent/multi-asset-studio` at `0644c3f24c3a5cdc0cf6e3cba5d35b3e1461a840` (`docs: accept visual asset plugin contract v1`).
- Current code has real timing in `src/deeptalk_studio/semantic_timeline.py`: `semantic-timeline/1` emits ordered `span_id`, real start/end seconds, summary, alignment safety, and `FACT_CONFLICT`/unsafe `keep_only` reasons.
- `src/deeptalk_studio/visual_director.py` writes V1 `visual-director-plan/1`, whose one-of decision is `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, or `ADVANCED_MOTION`.
- `src/deeptalk_studio/asset_pack_workflow.py` writes `visual-asset-manifest/1` and `edit-map/1` and explicitly falls a missing V1 asset back to `KEEP_A_ROLL`.
- `src/deeptalk_studio/finished_cut_review.py` accepts only the two V1 artifact versions. It is a preservation boundary, not an early V2 extension point.
- `src/deeptalk_studio/post_alignment_visual_plan.py` is relevant historic input evidence but has mutually exclusive `visual_kind` values and a separate projection model. It is not the V2 portfolio writer.

### Read-only plugin interfaces actually inspected

| Plugin | HEAD inspected | Current local invocation and artifacts | Integration finding |
|---|---|---|---|
| `deeptalk-mg` | `2e8fc15a7a2fba800b593f70da014c42dca7de49` | `npm run render:benchmarks` / `render:variants`; Node scripts invoke Remotion with macOS Chrome, `--concurrency=1`, `--gl=swiftshader`, then FFmpeg. Each static fixture directory has MP4, stills, contact sheet, `manifest.json`, and `qa.json`. | Deterministic local proof exists, but the command chooses committed benchmark IDs and has no dynamic Contract V1 request/result runner. |
| `deeptalk-illustrated-metaphor` | `cf1cdfe6855aa8d2902b4506184c6d6fd0c60d74` | `python3 scripts/render_prototypes.py --common-brief-trial --output …`; Python renders fixed brief fixtures to MP4, PNG/SVG frames, contact sheet, per-asset manifest, QA, and root manifest. | It records `SUITABLE`, `BORDERLINE`, and `ABSTAIN`, but its CLI is explicitly an internal prototype runner, not a dynamic plugin API. |
| `deeptalk-handdrawn-animation` | `33422715f1627d7eaef7cc1ccbea7434b833d360` | `node src/cli.js render-common-brief-trial`; local JSON fixtures compile SVG, Resvg PNG frames, FFmpeg MP4, contact sheet, and QA. The process emits a small JSON summary to stdout and errors to stderr. | It has an importable local CLI only for named fixture collections; it has no Contract V1 request/result runner. |

All three repositories were clean during inspection. Their current scripts demonstrate that a local subprocess can own native dependencies and deterministic render settings, but they do **not** demonstrate that Core can call a production Contract V1 endpoint today. A plugin-owned runner is therefore an explicit prerequisite, not an assumption hidden in Core code.

### Scope

This implementation line delivers the generated-plugin path only: Visual Opportunity, Contract V1 message validation, one-shot local adapters, policy, Core acceptance, portfolio/audit artifacts, Candidate Asset Pack, and multi-option edit map. It preserves V1 readers and establishes the separate real-episode gate.

### Non-goals

- A `REAL_MATERIAL` retrieval plugin, source search, rights acquisition, copyright scraping, or a REAL generator contract.
- A universal scene graph, common MG grammar, illustrated-metaphor route, hand-drawn primitive model, cross-family score, or dynamic Plugin Registry.
- A cloud service, RPC daemon, queue, marketplace, plugin auto-installation, or remote object storage.
- Automatic candidate selection, candidate-overlap resolution, visual quota, NLE project creation, final video generation, or A-roll editing.
- Changing V1 artifacts in place, migrating historic episode files, or expanding `finished-cut-review/1` in this vertical slice.

## 2. Runtime Invocation Decision

### Alternatives considered

| Shape | Decision | Evidence-based reason |
|---|---|---|
| A. Local subprocess with JSON entirely on stdin/stdout | Reject as the primary protocol | It is compact, but the current MG scripts inherit renderer output and the illustrated runner prints human progress. Mixing tool logs and a single protocol response makes malformed-output diagnosis and deterministic capture fragile. |
| B. Local subprocess with Core-owned request/result files | **Adopt** | Every current plugin already works through local files and output directories. A request file, result file, stdout/stderr logs, and isolated output root make paths, cleanup, debugging, timeouts, and per-plugin failures explicit. |
| C. Direct language/module imports | Reject | The plugins use mixed Python and Node environments with incompatible dependencies. Imports would couple Core to their internals, lock versions together, and make a renderer crash part of the Core process. |
| D. Dynamic registry/discovery or RPC | Defer | No current plugin exposes a service or installation metadata. Static local configuration is simpler, observable, sufficient for exactly three known repositories, and does not precommit a future cloud design. |

### Adopted lifecycle

1. Core loads a validated static plugin configuration, sorted by `plugin_id`; no repository scanning occurs.
2. For each `(opportunity_id, plugin_id, operation)`, Core creates a new immutable job directory under an episode-local ignored root such as `candidate_plugin_runs/<portfolio_id>/<plugin_id>/<request_id>/`.
3. Core writes either `suitability-request.json` or `generation-request.json`, creates an empty plugin-owned `output/` subdirectory, and invokes the configured executable with explicit `--request`, `--result`, and `--output-dir` arguments, using the configured plugin root as `cwd`.
4. The runner writes exactly one result JSON atomically to the supplied result path. Native renderer output stays below the supplied `output/`; the runner may write normal human diagnostics to stderr only.
5. Core captures bounded stdout/stderr text to `process.log.json`, enforces a per-operation timeout, reads the result only after zero exit, and validates Contract V1 before policy, portfolio, or creator output consumes it.
6. A suitability `ABSTAIN` is recorded as a completed proposal and ends only that plugin's work. A failure for one plugin neither cancels nor downgrades another plugin's result for the same opportunity.
7. Cancellation terminates only the child process group, records a retryable `FAILED` process problem, retains logs, and never removes another plugin job or historic portfolio.

### Static plugin configuration

Add a tracked schema/example and an ignored machine-local instance. The instance has no secret and contains only: `plugin_id`, `plugin_version_command`, `plugin_root`, executable argv prefix, per-operation timeout, deterministic environment overrides, enabled state, `expected_source_revision`, and `require_clean_worktree`. A resolved configuration snapshot and its digest are stored in each portfolio so later readers know precisely which local plugin commit, reported version, command, and runtime environment were used.

The configuration must name all three known generated plugins explicitly; no lookup by folder name, `PATH`, package name, or arbitrary user request is allowed. `plugin_root` must resolve to an allowed local directory and each command must be an argv list, never a shell string. For a real configured plugin, Core preflight runs `git -C <plugin_root> rev-parse HEAD` and requires it to equal the configured full commit SHA. The default `require_clean_worktree: true` additionally requires `git status --porcelain=v1 --untracked-files=all` to be empty, except ignored Core-owned render outputs. A revision mismatch or dirty checkout prevents invocation and becomes a Core preflight/audit problem; it is not a plugin response and is not added to Contract V1.

## 3. Core Data Model and Validation Boundaries

### Schema ownership

| Model | Owner and future module | Boundary |
|---|---|---|
| Contract V1 envelopes and nested `Artifact`/`Problem` | `visual_asset_plugin_contract.py` | Strict structural and enum validation for requests and plugin responses. It directly reflects the accepted contract; it does not reinterpret opaque `plugin_metadata`. |
| Clock-free Visual Opportunity directives | `visual_opportunity_directive.py` | Validates and immutably stores the narrow V2 editorial input that says why an already-safe semantic span deserves optional visual treatment. It has no time or V1 decision enum. |
| Core Visual Opportunity plan | `visual_opportunity.py` | Converts safe `semantic-timeline/1` spans plus validated V2 directives into contract-ready opportunities and an explicit span audit. |
| Static plugin configuration | `visual_plugin_config.py` | Validates trusted local launch configuration before process execution. |
| Process adapter and execution records | `visual_plugin_adapter.py` | Translates Contract V1 file protocol to a supervised subprocess and preserves raw response/log evidence. |
| Core candidate acceptance and portfolio | `candidate_portfolio.py` | Enforces cross-stage lineage, locator resolution, Core factual/provenance restrictions, and non-exclusive aggregation. |
| Creator delivery | `candidate_pack_workflow.py` and `candidate_edit_map.py` | Filters only Core-accepted `READY` candidates into a distinct package, JSON source artifact, CSV, and Markdown. |

Do not create another model with renamed versions of Contract V1's `opportunity_id`, `proposal_id`, `candidate_id`, `a_roll_window`, `suggested_placement`, `operation_status`, or `candidate_status`.

### Clock-free directive producer and Visual Opportunity writer

The actual current boundary was inspected before this clarification. `visual_director.py` accepts clock-free proposal semantics (`cue_id`, `visual_intent`, `why_visual`) and derives time from supplied approved roots, but it has no production workflow caller and its output forces V1's `KEEP_A_ROLL` / `REAL_MATERIAL` / `MG_MOTION` / `ADVANCED_MOTION` decision enum. `post_alignment_visual_plan.py` is consumed by existing production/edit-bridge paths, but its input requires V1 `visual_kind` and pre-existing source bindings. Neither can be a direct V2 producer without leaking V1 mutually exclusive decisions or bindings into Candidate Portfolio planning.

Phase 1 therefore introduces the narrow, independent Core artifact `visual-opportunity-directives/1`, owned by `visual_opportunity_directive.py`. It reuses the **clock-free editorial-proposal shape** already proven by V1 — a purpose and reason tied to an anchor — but replaces `cue_id` with the authoritative `semantic-timeline/1` `span_id` and explicitly excludes `decision`, `visual_kind`, `asset_class`, `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, and `ADVANCED_MOTION`. It is not a second rendering or asset-planning architecture; it is the smallest V2-safe replacement for V1's proposal input boundary.

The producer is the future V2 Visual Opportunity Director authoring step: an agent/human supplies a draft directive payload; Core's `visual_opportunity_directive.py` validates, normalizes, digests, and stores the immutable artifact. Agent/human-authored fields are `span_id`, `visual_purpose`, `why_opportunity`, bounded semantic-context selectors, and approved factual-context references. Core-owned fields are artifact/version/IDs/revision/digests, validation result, and all real-time projection. No author may supply time, candidate family, generation policy, plugin context, candidate, or a V1 decision.

Phase 1's sanitized fixture directly supplies one valid `visual-opportunity-directives/1` artifact. Before Phase 6 real-episode validation, Phase 2 adds the production directive authoring/validation boundary: it reads a reviewed Script plus approved factual references and a verified `semantic-timeline/1`, writes the immutable directives artifact, then passes it to `visual_opportunity.py`. This artifact, rather than the synthetic fixture, is the real production input. It can be produced by the future V2 authoring workflow without changing the legacy `visual_director.py` or `post_alignment_visual_plan.py` path.

`visual_opportunity.py` is the sole V2 Visual Opportunity writer. It consumes:

- a verified `semantic-timeline/1` artifact, including its alignment and transcript digests;
- a validated `visual-opportunity-directives/1` artifact;
- the reviewed script and approved factual/source bindings already accepted by Core; and
- canvas/language/profile values from approved Core configuration.

It rejects a directive that supplies time, references a `keep_only` span, falls outside the semantic span, lacks a factual binding needed for its visible factual claim, or duplicates a semantic scope within one immutable plan. The writer derives `a_roll_window` only from the selected safe semantic span. It constructs `spoken_semantics` from the exact span summary plus the selected bounded context, and constructs `factual_context` as already-approved Core references rather than free-form facts.

`opportunity_id` is a deterministic, collision-checked Core ID based on the immutable opportunity-plan identity, semantic timeline digest, `span_id`, and a stable ordinal. It is stable for every retry and all plugin calls within that plan. A materially revised semantic scope creates a new immutable plan/revision and therefore a new opportunity; old portfolios remain unchanged.

No opportunity is represented by omission from the `opportunities` array. The plan contains a `span_audit` row for every semantic span with either `OPPORTUNITY_CREATED` and its ID or `NO_OPPORTUNITY` with one controlled reason: `unsafe_alignment`, `fact_conflict`, `no_useful_visual_purpose`, or `creator_base_layer`. Thus no V2 output contains a fake `KEEP_A_ROLL` candidate.

### Proposed Core artifact shapes

The following are Core artifacts, not replacements for Contract V1 envelopes:

```json
{
  "artifact_version": "visual-opportunity-directives/1",
  "directives_id": "VOD-…",
  "revision": 1,
  "semantic_timeline_digest": "…",
  "reviewed_script_digest": "…",
  "directives": [{
    "directive_id": "vod_…",
    "span_id": "ST001",
    "visual_purpose": "Explain the approved causal relation.",
    "why_opportunity": "The spoken transition benefits from a bounded explanatory visual.",
    "semantic_context_selector": {"include_neighboring_spans": 1},
    "factual_context_refs": [{"claim_id": "…", "evidence_id": "…"}]
  }]
}
```

```json
{
  "artifact_version": "visual-opportunity-plan/1",
  "plan_id": "VOP-…",
  "revision": 1,
  "semantic_timeline_digest": "…",
  "alignment_digest": "…",
  "span_audit": [{"span_id": "ST001", "outcome": "NO_OPPORTUNITY", "reason": "creator_base_layer"}],
  "opportunities": [{
    "opportunity_id": "opp_…",
    "spoken_semantics": "…",
    "visual_purpose": "…",
    "a_roll_window": {"start_ms": 12400, "end_ms": 20000},
    "target_duration_ms": 7000,
    "language": "zh-CN",
    "canvas": {"width": 1920, "height": 1080},
    "semantic_context": "…",
    "factual_context": [{"claim_id": "…", "evidence_id": "…"}]
  }]
}
```

```json
{
  "artifact_version": "candidate-portfolio/1",
  "portfolio_id": "CP-…",
  "visual_opportunity_plan_digest": "…",
  "plugin_config_digest": "…",
  "opportunities": [{
    "opportunity": {"opportunity_id": "opp_…"},
    "proposals": ["completed suitability, abstention, failure, or unavailable records"],
    "generation_records": ["attempted generation records"],
    "candidates": [{
      "plugin_candidate": {"candidate_id": "cand_…", "candidate_status": "READY"},
      "core_acceptance": {"status": "ACCEPTED", "problems": []}
    }]
  }],
  "audit_records": ["append-only job summaries"]
}
```

The full request/response evidence is retained by locator from each audit record. The creator pack is derived from this artifact and is never its machine-history replacement.

## 4. Adapter, Failure, and Artifact Rules

### Plugin runner prerequisite

Before a real adapter is enabled, each plugin repository must independently release a small runner that accepts the Core-supplied request/result/output paths, supports both `suitability` and `generation`, emits Contract V1 result JSON, and records native manifest/QA artifacts in the supplied output root. It translates Contract V1 to its own native grammar, routes, fixtures, and renderer flags inside its repository.

The Core planning branch must not write those runners. The existing plugin files that demonstrate the native boundary are `deeptalk-mg/scripts/render-variants.mjs`, `deeptalk-illustrated-metaphor/scripts/render_prototypes.py` plus `src/illustrated_metaphor/cli.py`, and `deeptalk-handdrawn-animation/src/cli.js` plus `src/render.js`. Each plugin implementation session must add its own tests and exact files in that repository; Core only consumes an independently reviewed and accepted pinned commit, reported plugin version, and deterministic runner contract. This gate does not authorize a Git tag, GitHub Release, or formal product release.

### Three evidence layers

The portfolio deliberately distinguishes these records:

1. **Raw Plugin Contract V1 response.** It exists only if the plugin runner wrote a result file that Core parsed and validated. Core stores it unchanged by locator/digest; the contained plugin `candidate_status` is immutable.
2. **Core adapter/process execution record.** Core owns this record for preflight and process facts: resolved command/config digest, expected and actual Git revision, clean-tree result, process start/exit/timeout, stdout/stderr locators, result-file presence, parse/contract validation outcome, runtime duration, and typed Core problems. It may use normalized execution states such as `UNAVAILABLE`, `BLOCKED`, `FAILED`, or `COMPLETED`, but it is never serialized as a plugin Contract V1 response.
3. **Core policy no-call record.** Core owns this record when trusted configuration disables a plugin, `ABSTAIN` ends the lifecycle, or profile policy skips an otherwise valid BORDERLINE proposal. It names the proposal/decision reason and records `generation_call: NOT_REQUESTED`; it contains no fabricated Generation Result.

A debugger can therefore distinguish “the plugin returned FAILED” from “Core could not start it” and from “Core deliberately made no generation call.”

### Exit and status mapping

| Observed condition | Core record |
|---|---|
| Valid result JSON, exit `0`, completed suitability with `ABSTAIN` | Store raw completed Suitability Response unchanged; store a Core policy no-call record; no health failure. |
| Valid result JSON, exit `0`, generation `COMPLETED` plus plugin `QA_REJECTED` | Store raw Generation Result unchanged; `candidate_status` remains `QA_REJECTED`; omit from creator output. |
| Plugin root missing, expected source revision mismatch, dirty required-clean checkout, executable missing, or dependency/bootstrap preflight absent | Store a Core preflight execution record with `UNAVAILABLE` or `BLOCKED` and problem; no raw plugin response exists. |
| Core trusted configuration disables a plugin or profile skips BORDERLINE | Store a Core policy no-call record; no raw Generation Result exists. |
| Valid plugin response explicitly reports `BLOCKED` / `FAILED` / `UNAVAILABLE` | Store the raw Plugin Contract response unchanged and separately record Core execution as completed-with-valid-response. |
| Process fails to start, exits non-zero, times out/cancels, omits result, or writes malformed/mismatched/invalid result | Store a Core `FAILED` execution record with bounded log locator; no fabricated plugin Contract response. Timeout/cancellation is retryable. |
| Valid plugin `READY` candidate fails Core acceptance (lineage, placement, resolver, hash, media, factual/provenance, or source restriction) | Preserve raw candidate `candidate_status: READY`; store `core_acceptance.status: REJECTED` with typed Core validation problems; omit from creator output. |

### Artifact locator strategy

| Strategy | Decision |
|---|---|
| Plugin absolute local paths | Do not persist as the portable locator. They expose repo layout and break if a repo moves. |
| Relative path plus plugin root | Do not use as the stored authority. It couples historic candidates to a mutable checkout. |
| `file://` URI | Accept only as an optional input resolver for development diagnostics; do not make it the archival format. |
| Core-owned copied asset location | **Adopt for V1 runtime.** The job output root is Core-owned from creation, and accepted media is copied/hard-linked into the immutable episode-local candidate package only after SHA verification. |
| Manifest-based resolver | **Adopt with the Core-owned location.** Store opaque `local-plugin-artifact://<portfolio_id>/<plugin_id>/<request_id>/<relative-posix-path>` locators; resolve them only through the immutable Core job manifest, reject traversal, and retain a SHA when available. |

The migration path is explicit: a later storage backend adds a resolver for another opaque scheme while preserving stored locators and Core validation semantics. Contract V1 remains unchanged.

### Core-side acceptance validation

Core validates in this order: contract envelope; request/response correlation; opportunity and proposal lineage; plugin identity/version equals resolved configuration; candidate ID uniqueness within portfolio and plugin result; placement containment; required `PRIMARY_MEDIA` and media type; locator resolution and root containment; file existence; SHA-256 when provided; `ffprobe` readable video and sane positive duration; reported/observed duration consistency under a documented tolerance; plugin QA status; factual-context binding; generated provenance; and source/rights restrictions.

Plugin QA proves the plugin's native checks. Core acceptance proves whether the candidate may enter a DeepTalk portfolio. Neither substitutes for the other. A generated candidate always retains `origin: plugin-generated` and cannot be represented as documentary or `REAL_MATERIAL` evidence. The candidate record keeps the raw plugin object unchanged and adds a sibling Core-owned `core_acceptance: {status: ACCEPTED | REJECTED, problems: [...]}`. Creator-facing READY projection requires both raw `candidate_status: READY` and `core_acceptance.status: ACCEPTED`; raw `QA_REJECTED` naturally never qualifies.

## 5. Portfolio, Policy, Pack, and Edit Map

### Deterministic generation policy

The initial policy uses the existing soft LEAN/STANDARD/RICH direction as a choice-breadth control, not a count quota:

| Production profile | Generate after completed suitability | Rationale |
|---|---|---|
| `LEAN` | Every `SUITABLE`; never `BORDERLINE`. | Keeps only natural family fits. |
| `STANDARD` | Every `SUITABLE`; a `BORDERLINE` only when that opportunity has no completed `SUITABLE` proposal. | Avoids an empty useful opportunity without assuming cross-family ranking. |
| `RICH` | Every `SUITABLE` and every `BORDERLINE`. | Maximizes differentiated possible choices; it does not require an opportunity or file count. |
| all profiles | Never `ABSTAIN`; never a failed/unavailable suitability call. | Preserves the accepted lifecycle. |

`suggested_review_order` is a stable presentation hint: `SUITABLE` candidates precede `BORDERLINE` candidates, then ties sort by configured `plugin_id` and `candidate_id`. It never means winner, selected asset, mandatory usage, or timeline order.

### Candidate Portfolio

For one opportunity, machine history retains every configured plugin's suitability record, policy decision, generation record (including no-call policy decisions), raw response/log locators when they exist, Core execution/preflight records, Core validation reports, and all generated candidates. The public `ready_candidates` projection includes only raw plugin `candidate_status: READY` plus `core_acceptance: ACCEPTED`. It has zero or more candidates, can overlap, and does not require equal duration, one family, or one candidate. A portfolio with MG raw READY/Core ACCEPTED, Illustrated Core UNAVAILABLE without a raw response, and Hand-drawn raw ABSTAIN plus policy no-call is valid and must remain inspectable as such.

### Candidate Asset Pack

The new pack is rooted by Visual Opportunity, not plugin repository. Every opportunity section states real A-roll window/timecode, spoken semantics, visual purpose/reason, and the creator instruction: “choose none, one, or several manually; these options do not choose an edit.” Its default view lists only Core-accepted `READY` candidates with family, preview locator/path, primary media filename, suggested placement, full media duration, short suitability reason, QA-ready state, and `suggested_review_order`. Diagnostics/history stays in `_DeepTalk记录` and does not expose plugin grammar, routes, primitives, or opaque plugin metadata to the default creator guide.

### Multi-option edit map version

Existing conventions identify artifacts as scoped names such as `edit-map/1`, `visual-asset-manifest/1`, and `finished-cut-review/1`. Do **not** claim an unreviewed `edit-map/2` migration. Introduce a distinct `candidate-edit-map/1` alongside old `edit-map/1`; this prevents V1 readers from accepting a semantically different table accidentally.

- JSON is the machine source: one opportunity with `candidates[]`, complete digest/lineage and audit references.
- CSV has one row per READY candidate and repeats `opportunity_id` and real A-roll window; it includes `suggested_review_order`, never a selected/winner field.
- Markdown groups options under one opportunity, identifies candidates as optional, and makes different duration/overlap visible.

## 6. File-Level Implementation Map

### Core files to add

| Phase | File | Responsibility |
|---|---|---|
| 0–1 | `src/deeptalk_studio/visual_asset_plugin_contract.py` | Contract V1 constants, schemas, request/response validators, status and artifact invariants. |
| 0–1 | `src/deeptalk_studio/visual_opportunity_directive.py` | `visual-opportunity-directives/1` validation, V1-proposal-shape adapter boundary, directive digest, and prohibited V1 decision/time fields. |
| 0–1 | `src/deeptalk_studio/visual_opportunity_directive_storage.py` | Immutable save/load of validated V2 directives. |
| 0–1 | `src/deeptalk_studio/visual_opportunity.py` | `visual-opportunity-plan/1` construction, deterministic IDs, span audit, timing and factual-context guards. |
| 0–1 | `src/deeptalk_studio/visual_opportunity_storage.py` | Immutable save/load of opportunity plans under a new ignored local output root. |
| 1 | `src/deeptalk_studio/visual_plugin_config.py` | Static local plugin configuration schema, path and argv validation, configuration digest. |
| 1–2 | `src/deeptalk_studio/visual_plugin_adapter.py` | Job-directory creation, subprocess supervision, timeout/cancellation, logs, result parsing, status mapping. |
| 2–3 | `src/deeptalk_studio/candidate_portfolio.py` | Policy evaluation, per-plugin records, Core acceptance QA, immutable `candidate-portfolio/1` construction. |
| 2–3 | `src/deeptalk_studio/candidate_portfolio_storage.py` | Immutable portfolio/audit storage and opaque local-artifact resolver. |
| 4 | `src/deeptalk_studio/candidate_pack_workflow.py` | Candidate media staging/copy verification and creator-pack assembly. |
| 4 | `src/deeptalk_studio/candidate_edit_map.py` | `candidate-edit-map/1` JSON, candidate-row CSV, opportunity-grouped Markdown. |
| 0 | `tests/visual_asset_plugin_fakes.py` | Deterministic fake runner used by Core adapter tests; it never imports a real plugin. |
| 0–1 | `tests/test_visual_asset_plugin_contract.py` | Contract, enum, ID, request/response, placement, and problem validation tests. |
| 0–1 | `tests/test_visual_opportunity_directive.py` | Synthetic and production directive source, V1-decision/time rejection, span/fact binding, ownership, and immutable storage tests. |
| 0–1 | `tests/test_visual_opportunity.py` | Real-span inheritance, no-opportunity, `FACT_CONFLICT`, determinism, and factual-context tests. |
| 1–3 | `tests/test_visual_plugin_config.py` | Static config, path, argv, duplicate plugin, timeout, expected Git revision, clean-tree and digest tests. |
| 1–3 | `tests/test_visual_plugin_adapter.py` | Valid response, ABSTAIN, raw plugin failure, Core preflight failure, UNAVAILABLE/BLOCKED, malformed/timeout, source-revision and clean-tree process tests. |
| 2–3 | `tests/test_candidate_portfolio.py` | Policy no-call, lineage, non-exclusive aggregation, raw READY/Core ACCEPTED, raw READY/Core REJECTED, raw QA_REJECTED, isolation, and audit tests. |
| 2–3 | `tests/test_candidate_portfolio_storage.py` | Immutability, resolver containment, copied-artifact and digest tests. |
| 4 | `tests/test_candidate_pack_workflow.py` | READY-only pack, opportunity grouping, media copying, no-winner wording, CSV/JSON/Markdown assertions. |
| 4 | `tests/test_candidate_edit_map.py` | Repeated opportunity rows, overlap visibility, review-order and digest tests. |
| 5 | `tests/test_multi_asset_synthetic_integration.py` | One-plugin and three-plugin fake-runner end-to-end synthetic integration. |
| 0, 5 | `tests/fixtures/multi_asset_synthetic/` | Sanitized synthetic script/alignment/timeline/brief/config/result fixture corpus. |
| 0, 4 | `config/visual-asset-plugins.example.json` | Tracked static configuration shape with placeholders only. |
| 0, 4 | `config/candidate-generation-profile.json` | Tracked LEAN/STANDARD/RICH deterministic policy schema. |

### Core files to modify

| Phase | File | Change boundary |
|---|---|---|
| 0 | `.gitignore` | Ignore only local plugin configuration and new episode-local candidate job/output roots; retain tracked examples and `.gitkeep` files. |
| 1 | `src/deeptalk_studio/semantic_timeline.py` | Add only a documented consumer helper or explicit digest/type validation needed by the new writer. Do not alter the emitted V1 `semantic-timeline/1` fields or its timing rules. |
| 2–3 | `src/deeptalk_studio/__init__.py` | Export new public Core entry points only if existing package conventions require exports. |
| 4 | `docs/ASSET_PACK_EDIT_MAP_CONTRACT.md` | Add a clearly labelled parallel Candidate Pack / `candidate-edit-map/1` compatibility section after implementation review; retain every V1 statement. |
| 5 | `PROJECT_STATE.md`, `ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/INDEX.md`, `CHANGELOG.md`, `HANDOFF.md` | Update only after the corresponding implementation gates pass; describe capability as implemented/unreleased, never released. |

### Files explicitly not changed in the first implementation vertical slice

- `src/deeptalk_studio/asset_pack_workflow.py`, `visual_asset_pack.py`, and `edit_map.py`: V1 writers/readers stay behaviorally frozen.
- `src/deeptalk_studio/visual_director.py`, `motion_spec.py`, `visual_asset_renderer.py`, and all legacy renderers: no new portfolio behavior is inserted into a V1 decision/render path.
- `src/deeptalk_studio/finished_cut_review.py`: first release validates its V1 regression only; it does not claim `candidate-edit-map/1` support.
- `src/deeptalk_studio/post_alignment_visual_plan.py`: no in-place conversion from its mutually exclusive `visual_kind` design.
- All three plugin repositories: this Core plan performs no changes. Their runner work is separately reviewed and pinned before Phase 3.

## 7. Phased Implementation Sequence

### Phase 0: Contract fixtures and frozen compatibility baseline

**Goal:** Establish Contract V1 validators, explicit synthetic V2 directive source, configuration shape, and evidence that V1 readers remain untouched before any process integration.

**Files:** Add contract module, fake runner, Contract/fixture tests, `config/visual-asset-plugins.example.json`, `config/candidate-generation-profile.json`; modify `.gitignore` only for local roots.

- [ ] Write failing tests for each required Contract V1 envelope, all enums, unique IDs, required problem fields, raw plugin `READY` artifact/QA requirements, raw plugin `QA_REJECTED`, and placement containment.
- [ ] Add a sanitized `visual-opportunity-directives/1` fixture as the explicit Phase 1 directive producer; it supplies purpose/reason/fact references, no time, and no V1 decision or visual-kind field.
- [ ] Add fixed synthetic examples for completed suitability (`SUITABLE`, `BORDERLINE`, `ABSTAIN`), raw plugin `FAILED`/`UNAVAILABLE` responses, raw completed `READY`, raw completed `QA_REJECTED`, malformed result, and out-of-window placement.
- [ ] Implement only the strict validation primitives and deterministic fixture fake runner required for the tests.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.test_visual_asset_plugin_contract -v` and confirm every valid fixture passes while invalid fixtures fail closed.
- [ ] Run V1 regression commands: `PYTHONPATH=src python3 -m unittest tests.test_semantic_timeline tests.test_visual_director tests.test_asset_pack_workflow tests.test_finished_cut_review -v`.
- [ ] Review gate: inspect the artifact names and fixture messages against Contract V1; do not begin adapter work until the V1 regression is green.

**Acceptance criteria:** Contract field names exactly match the accepted document; a synthetic `ABSTAIN` succeeds without generation; no test or fixture contains `KEEP_A_ROLL` as a V2 candidate; the synthetic directive artifact is the only Phase 1 editorial source; legacy readers still consume their old fixtures.

**Rollback point:** Revert this isolated contract/fixture commit; no existing writer or episode artifact has changed.

### Phase 1: Visual Opportunity and fake subprocess vertical slice

**Goal:** Prove the smallest complete path: safe synthetic Semantic Timeline + explicit synthetic directives → one Visual Opportunity → one configured fake plugin's suitability and generation → Core validation → one immutable portfolio record.

**Files:** Add opportunity/config/adapter/portfolio/storage modules and Phase 1 tests; modify only `semantic_timeline.py` if a non-breaking consumer helper is genuinely required.

- [ ] Write failing tests that `visual-opportunity-directives/1` rejects V1 decisions/visual kinds and supplied time; a V2 opportunity takes every millisecond boundary from a safe `semantic-timeline/1` span, rejects `keep_only` / fact-conflict spans, and records a no-opportunity audit without a candidate.
- [ ] Implement directive validation/storage plus `visual-opportunity-plan/1` construction and immutable storage with deterministic IDs/digests.
- [ ] Write failing adapter tests using the fake runner for valid raw response, `ABSTAIN`, raw plugin failure response, non-zero exit, missing executable, malformed result, and timeout; assert which cases have no raw plugin response.
- [ ] Implement the filesystem request/result subprocess adapter with configured `cwd`, argv, output root, process logs, timeout, and typed status mapping.
- [ ] Write failing portfolio tests for `opportunity_id → proposal_id → candidate_id` lineage, raw plugin READY + Core ACCEPTED, raw plugin READY + Core REJECTED, raw plugin QA_REJECTED, and READY projection requiring both domains.
- [ ] Implement minimal one-plugin orchestration and Core validation sufficient for the synthetic fake result.
- [ ] Run the Phase 0 tests plus `PYTHONPATH=src python3 -m unittest tests.test_visual_opportunity tests.test_visual_plugin_config tests.test_visual_plugin_adapter tests.test_candidate_portfolio tests.test_candidate_portfolio_storage -v`.
- [ ] Review gate: inspect the saved job tree and portfolio JSON manually; verify the only persisted artifact locators resolve beneath the Core-owned job root.

**Acceptance criteria:** A fake plugin can complete the complete two-stage Contract V1 lifecycle; an `ABSTAIN` is retained but never generated; a timeout produces only a retryable Core `FAILED` execution record and no synthetic plugin result; Core never mutates raw plugin candidate status; existing code remains unmodified except the allowed non-breaking helper.

**Rollback point:** Revert the Phase 1 commits; only ignored synthetic job output exists outside Git.

### Phase 2: Portfolio breadth, policy, Core QA, and audit

**Goal:** Make one opportunity safely retain zero-to-many results across independent plugins, with deterministic LEAN/STANDARD/RICH policy, a real production directive source, and separate Core acceptance.

**Files:** Extend `candidate_portfolio.py`, storage/resolver, fake runner and candidate portfolio tests; no V1 writer changes.

- [ ] Write failing tests for the production `visual-opportunity-directives/1` authoring/validation boundary: reviewed-script/factual/timeline digest binding, human/agent-authored fields, machine-owned fields, no V1 decision leakage, and immutable storage. This replaces the Phase 1 fixture before any real Episode gate.
- [ ] Implement the production directive boundary and its adapter from the current V1-style clock-free `visual_intent` / `why_visual` authoring semantics, keyed only by `semantic-timeline/1` `span_id`; do not call or mutate `visual_director.py` or `post_alignment_visual_plan.py`.
- [ ] Write failing policy tests for every profile and proposal mix, including the STANDARD no-SUITABLE edge case, `ABSTAIN` never generating, trusted disabled-plugin no-call, and BORDERLINE policy no-call.
- [ ] Implement the deterministic policy table and persist the policy/config digest and individual no-call reasons.
- [ ] Write failing Core QA tests for wrong opportunity/proposal IDs, duplicate candidate ID, wrong plugin version, placement escape, missing primary artifact, path traversal, missing file, hash mismatch, invalid ffprobe media, duration mismatch, factual-context mismatch, and generated-as-real provenance.
- [ ] Implement ordered Core acceptance validation that adds `core_acceptance: ACCEPTED | REJECTED` and typed Core validation problems without mutating the raw plugin response or its candidate status.
- [ ] Write failure-isolation tests for a portfolio containing `MG READY`, `Illustrated UNAVAILABLE`, and `Hand-drawn ABSTAIN`.
- [ ] Run the new tests and the complete Phase 0/1 suite.
- [ ] Review gate: inspect an audit record and confirm it answers opportunity, plugin/version, proposal, policy decision, operation result, candidate state, locators, QA, problem, timestamps, and duration without a telemetry service.

**Acceptance criteria:** One failed plugin never erases or blocks another result; `RICH` can generate all eligible borderline proposals without a count quota; a raw READY/Core REJECTED candidate remains raw READY in machine evidence but never reaches the creator READY projection; Phase 6 has a real directives artifact path rather than a synthetic source.

**Rollback point:** Revert the additive portfolio commits; the Phase 1 vertical slice and V1 behavior remain intact.

### Phase 3A: First independently reviewed runner and one real Core integration

**Goal:** Replace exactly one fake runner with one separately reviewed, accepted-pinned plugin commit and prove the Core protocol against actual local files without importing plugin internals.

**Dependencies:** One plugin-repository implementation session/branch/review has added a Contract V1 runner, tests, deterministic command flags, atomic result writing, manifest/QA artifacts, and an accepted commit SHA. Core work starts only after its exact SHA is configured and the plugin remains independently testable. This is an acceptance/pin gate, not a Git tag, GitHub Release, or product release.

**Files:** Core modifies only local plugin configuration and integration tests. The selected plugin repository owns its own exact runner files and tests.

- [ ] Select the first plugin by runner readiness and deterministic evidence, not visual preference; record `expected_source_revision`, reported `plugin_version`, resolved command, environment/config digest, and `require_clean_worktree: true` in its configuration snapshot.
- [ ] Write Core preflight tests for HEAD mismatch and dirty checkout; assert both produce Core audit records and no raw Plugin Contract V1 response.
- [ ] Write a Core integration test that invokes the clean, exact pinned runner on one sanitized synthetic Visual Opportunity and asserts Contract V1 validity, raw READY/Core ACCEPTED, locator resolution, SHA/ffprobe/media checks, and portfolio acceptance.
- [ ] Run the plugin's own documented test, lint/typecheck, deterministic render/QA commands in its repository, then run the new Core integration test.
- [ ] Confirm Core only invokes the configured command and reads result/artifact files; inspect imports to prove no plugin package is added to Core dependencies.
- [ ] Review gate: review Git preflight evidence, logs, raw result JSON, generated manifest/QA, and Core acceptance report before enabling a second plugin.

**Acceptance criteria:** One real plugin completes a sanitized synthetic opportunity into a Core-accepted candidate using a subprocess, Core-owned output directory, opaque locator, expected source revision, clean checkout, and pinned reported version. No real episode runs and no tag/GitHub Release is created.

**Rollback point:** Disable the one plugin in local static configuration; fake integration and all V1 paths stay usable.

### Phase 3B: Remaining two independently reviewed runner gates

**Goal:** Establish Contract V1 runner readiness for the remaining two plugins before Core claims three-plugin integration.

**Dependencies:** Phase 3A is accepted. Each remaining plugin receives its own implementation session, branch, tests, independent review, and accepted pinned commit; the two runner implementations must not be bundled into the Core branch or one another's repository.

**Files:** Each plugin repository owns its own runner changes/tests. Core only adds two disabled-or-ready static configuration entries and runner-readiness fixtures after each review passes.

- [ ] Implement and independently review the second plugin's runner; record its exact accepted commit SHA, plugin version, command, deterministic environment, and clean-tree requirement in Core configuration only after approval.
- [ ] Repeat the same independent runner implementation/review/pin for the third plugin.
- [ ] For each runner, execute its native test/lint/typecheck/render/QA evidence and a Core preflight-only test that confirms exact revision and clean checkout before invocation.
- [ ] Do not run the three-plugin portfolio integration while either runner lacks its accepted pinned commit or fails the preflight gate.
- [ ] Review gate: verify all three runner readiness records separately identify repository, accepted commit, reported version, command, configuration digest, clean-tree result, and validation evidence. No tag/GitHub Release is implied or created.

**Acceptance criteria:** All three runners are independently reviewed and pinned, but Phase 3B alone does not assert a multi-plugin Core portfolio or creator delivery.

**Rollback point:** Disable only the affected plugin entry; previously accepted runners and fake/V1 paths remain isolated.

### Phase 4: Candidate Asset Pack and multi-option Edit Map

**Goal:** Publish only Core-accepted READY candidates in an opportunity-centred creator delivery while retaining complete machine history separately.

**Files:** Add candidate pack/edit-map modules and tests; modify `.gitignore` for ignored local output roots. Do not modify V1 pack/map writers.

- [ ] Write failing tests for zero candidates, multiple overlapping candidates, different durations, multiple families, raw READY/Core ACCEPTED inclusion, raw READY/Core REJECTED exclusion, raw QA_REJECTED exclusion, media copy/hash preservation, and the absence of plugin-internal metadata from Markdown/CSV.
- [ ] Implement immutable staging into a candidate asset root with Core-owned locator manifests and non-overwriting filenames.
- [ ] Write failing tests asserting JSON opportunity arrays, repeated CSV opportunity rows, Markdown grouping, visible real A-roll time/reason/family/preview/duration/QA/review order, and clear “none/one/multiple” creator language.
- [ ] Implement `candidate-asset-pack/1` and `candidate-edit-map/1` output writers.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.test_candidate_pack_workflow tests.test_candidate_edit_map tests.test_asset_pack_workflow tests.test_finished_cut_review -v`.
- [ ] Review gate: manually open the synthetic Markdown, CSV, and JSON. Confirm that `suggested_review_order` is present only as review order and no output claims a winner.

**Acceptance criteria:** A creator sees only candidates satisfying raw plugin READY plus Core ACCEPTED under one opportunity and can choose none, one, or several; machine output retains raw responses, Core execution/preflight, policy no-call, and Core rejection history; old Asset Pack/Edit Map and Finished Cut Review tests stay green.

**Rollback point:** Stop producing the additive Candidate Pack outputs; V1 delivery remains the production default and existing V2 portfolio data remains immutable audit data.

### Phase 5: Three-plugin synthetic integration and compatibility hardening

**Goal:** Prove the accepted multi-repo, non-exclusive model against all three configured runners using a sanitized fixture corpus, then document the implemented-unreleased boundary accurately.

**Dependencies:** Phase 3A and both independent Phase 3B runner gates have passed. The three resolved configurations must each have an accepted expected source revision, matching current HEAD, clean required checkout, reported plugin version, resolved command, and configuration digest.

**Files:** Extend synthetic integration fixtures/tests; after green gates update only relevant canonical docs and changelog/handoff.

- [ ] Add a deterministic synthetic opportunity whose expected results include at least one raw READY/Core ACCEPTED candidate and at least one valid raw alternative, Core preflight/process failure, or ABSTAIN/no-call across the three plugin runners.
- [ ] Run three independent subprocesses and assert scheduling order does not change portfolio semantics, candidate IDs, raw response evidence, Core acceptance, or audit lineage.
- [ ] Assert a failed/unavailable preflight or process for one plugin leaves other raw READY/Core ACCEPTED candidates in the creator pack.
- [ ] Run full Core regression: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [ ] Run each plugin's own required validation commands against the pinned runner commits; record reproducibility evidence and version snapshots outside the Core source tree.
- [ ] Update `PROJECT_STATE.md`, `ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/INDEX.md`, `CHANGELOG.md`, and `HANDOFF.md` only to say the synthetic runtime is implemented/unreleased. Do not alter the V1.0 Candidate release truth.
- [ ] Review gate: product/architecture review confirms Contract V1, generated-only scope, V1 compatibility, and creator no-winner semantics before any real episode gate.

**Acceptance criteria:** Three independently reviewed/pinned clean runners can contribute non-exclusive synthetic results; all V1 regressions pass; no production claim mentions REAL retrieval, a formal release, tag, GitHub Release, or automatic editing.

**Rollback point:** Disable all real plugin entries and keep Core artifacts/readers/tests. V1 production behavior remains unchanged because no V1 writer was replaced.

### Phase 6: Separate real-episode validation gate

**Goal:** Validate product usefulness and operational safety on one separately approved real episode only after the synthetic multi-plugin suite is stable.

**Preconditions:** Phase 5 is accepted; a reviewed script, approved facts, Final Clean A-roll, real alignment, a validated production `visual-opportunity-directives/1` artifact, and a human-authorized episode are available; no private material is committed.

- [ ] Create an episode-specific validation checklist that binds the chosen real opportunity windows to actual alignment and declares no-output/no-winner expectations.
- [ ] Run a limited set of meaningful Visual Opportunities, not a coverage quota, through the pinned local configuration.
- [ ] Validate every Core candidate, inspect the Candidate Asset Pack and map with the creator, and record only product-level findings in Git.
- [ ] Require the creator to assemble manually in an NLE; no Core command may modify the cut or pick a candidate.
- [ ] If a Finished Cut Review is desired, run the unchanged V1 review only on a V1 pack, or plan a separate versioned review contract. Do not force `candidate-edit-map/1` through `finished-cut-review/1`.
- [ ] Review gate: ChatGPT product review assesses useful-choice density, clarity, quality, provenance, and creator experience before any policy/default changes.

**Acceptance criteria:** Real A-roll anchors all placements, the creator can make choices without a machine winner, generated assets remain honest illustrations, and all private artifacts remain local/gitignored.

**Rollback point:** Disable the candidate workflow for that episode and retain immutable audit evidence; V1 delivery and historic episodes are unaltered.

## 8. Test Pyramid

| Level | Coverage | Rendering cost rule |
|---|---|---|
| Unit | Contract schema, IDs/enums, placement invariant, policy table/no-call, V2 directive ownership and V1-field rejection, opportunity span/factual binding, locator containment, proposal/candidate lineage, raw plugin status, Core acceptance state. | No real plugin render. Use JSON fixtures and tiny synthetic media only where ffprobe behavior is tested. |
| Adapter contract | Valid raw response, ABSTAIN, raw plugin FAILED/UNAVAILABLE/BLOCKED response, Core missing-executable/root/revision/dirty-tree preflight failure, valid generation, malformed result, non-zero exit, timeout, raw plugin QA rejection, raw READY/Core REJECTED. | Fake subprocess runner by default; spawn an actual real runner only in dedicated integration. |
| Integration | One synthetic opportunity through one real configured exact-pinned clean plugin; all-three-runner readiness gates; multi-plugin non-exclusive portfolio; one Core preflight/process failure does not block others; local staging and candidate pack/map. | Use a single sanitized tiny/deterministic case and one pinned runner per targeted test job. |
| Regression | `semantic-timeline/1`, V1 Visual Director, V1 Asset Pack, `edit-map/1`, and `finished-cut-review/1` readers/writers. | No new generated render required. |
| Real-episode gate | Alignment, placement, candidate pack usability, source/provenance honesty, and creator manual editing observation. | Deliberate manual validation only after all synthetic gates. |

Tests must never require an expensive full render in the ordinary unit suite. A fake runner has explicit scenarios selected by request fixture and writes only the requested contract result/artifacts; it must not mock Core validation itself.

## 9. Review, Rollback, and Delivery Strategy

### Checkpoints

1. **Contract checkpoint:** strict field/status compatibility and V1 regressions before process work.
2. **Vertical-slice checkpoint:** one fake runner completes or abstains safely from an explicit synthetic directives artifact; no real plugin assumed.
3. **Core QA checkpoint:** portfolio retains raw plugin status, separate Core acceptance, execution/preflight evidence, policy no-calls, and no false creator READY.
4. **First real-runner checkpoint:** one plugin runner is independently reviewed, exact-pinned, clean, and integrated against a synthetic opportunity.
5. **Remaining-runner checkpoint:** the other two runners are each independently reviewed, exact-pinned, and preflight-ready; no formal release/tag is implied.
6. **Creator-output checkpoint:** synthetic Candidate Pack/Map is intelligible without machine internals.
7. **Multi-plugin checkpoint:** three-plugin synthetic integration and V1 regression pass only after all three runner gates.
8. **Real-episode checkpoint:** separate product review; no formal release claim follows automatically.

Every phase is additive and commit-sized. Reverting a phase disables a new writer/configuration without rewriting historic files. Candidate job roots, portfolios, packs, and maps use immutable IDs/revisions and reject overwrite; rollback means stop using a new path, not erase its evidence.

### Recommended implementation-session strategy

Use **one independent Codex session/branch/review per phase**, not one uninterrupted branch for all phases. The Core contract, plugin-owned runners, local dependencies, compatibility boundary, and real-episode gate have different failure domains. Each phase ends in a narrow reviewable commit set and a stop gate; a real plugin runner belongs to the owning plugin repository and is pinned only after its own review. This keeps rollback to a small boundary and avoids coupling an experimental renderer change to Core compatibility work.

### Deferred work

- `REAL_MATERIAL` retrieval/evidence plugin or any contract expansion for it.
- A new Finished Cut Review contract for `candidate-edit-map/1`.
- Cloud/artifact-store locators, remote execution, authentication, registry/discovery, retries/queueing, plugin installation, metrics platform, or UI dashboard.
- Cross-family aesthetic ranking, ML selection, candidate quota, automatic overlap resolution, and automatic editing.
- New generated families, maps/data visualization/3D, and any universal scene model.

### Risks and mitigations

| Risk | Mitigation in this plan |
|---|---|
| Current plugins cannot yet consume dynamic Contract V1 requests. | Treat an independently reviewed/accepted pinned runner commit as a hard dependency; prove fake adapter first. No tag or GitHub Release is implied. |
| Different Node/Python dependencies and browser/FFmpeg requirements make Core unstable. | One-shot subprocess, plugin `cwd`, Core-owned output directories, configured environment, timeouts, logs, and no direct imports. |
| A malformed plugin result could fabricate a ready candidate. | Strict response/request correlation and Core acceptance validation; malformed output is `FAILED`, never `ABSTAIN` or READY. |
| V2 changes damage V1 delivery/history. | Parallel artifact names, frozen V1 writers/readers, regression suite, immutable storage, no in-place migration. |
| “RICH” becomes a material-count requirement. | Policy controls only eligibility of borderline proposals; it defines no opportunity/candidate quota. |
| Plugin-generated illustration is mistaken for evidence. | Generated provenance is mandatory and Core factual/source restrictions reject `REAL_MATERIAL` impersonation. |
| A plugin failure hides useful alternatives. | Per-plugin execution records and aggregate portfolio always preserve mixed outcomes. |

## 10. Final Readiness Assessment

The plan is mechanically complete for ChatGPT's final implementation-plan decision. It is grounded in the accepted Contract V1, the actual V1 source/caller boundaries, and the actual three-plugin command/output surfaces. The first executable vertical slice is deliberately **one synthetic directives artifact → one synthetic Visual Opportunity → one configured fake plugin → two-stage Contract V1 → raw-status-preserving Core acceptance → immutable Candidate Portfolio**. It proves the Core architecture before a real runner or real episode is involved; Phase 3A integrates one independently reviewed/pinned plugin commit, Phase 3B gates the remaining two independently, and Phase 5 starts only after all three readiness gates and Candidate Pack delivery exist.

No production implementation was performed while creating or clarifying this plan. No plugin repository was modified. No merge, tag, GitHub Release, formal release, or `main` change is part of this planning work.
