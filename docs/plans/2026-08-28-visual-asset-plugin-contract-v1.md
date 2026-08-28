# Visual Asset Plugin Contract V1 — Architecture Design

> **Status:** Evidence-derived design prepared on `agent/visual-asset-plugin-contract-v1`. It is not production code, a migration, or an accepted production schema. ChatGPT Architecture Review is required before implementation planning.

## Decision

DeepTalk Visual Asset Ecosystem is a **multi-repo, plugin-first architecture**. DeepTalk Core stays stable while visual families are independently researched, optimized, benchmarked, QA'd, and versioned as Visual Asset Plugins. Core integrates those plugins through the deliberately small `visual-asset-plugin-contract/1` boundary.

V1 is a minimum contract, not a universal visual framework. It exposes neither scene grammars nor renderer internals. It is designed only for the three inspected generated-asset families and deliberately does not make `REAL_MATERIAL` pretend to be a generator.

## Evidence base

This design is derived from read-only inspection on 2026-08-28:

| Plugin | Inspected HEAD | Common Brief evidence relevant to the contract |
|---|---|---|
| `HWang0310/deeptalk-mg` | `2e8fc15a7a2fba800b593f70da014c42dca7de49` | CB01–CB08 are `SUITABLE`; deterministic `mg-scene/1` renders MP4, stills, contact sheet, manifest, and media/structural QA. |
| `HWang0310/deeptalk-illustrated-metaphor` | `cf1cdfe6855aa8d2902b4506184c6d6fd0c60d74` | CB01/CB02/CB07 are `BORDERLINE`, CB03–CB06 are `SUITABLE`, and CB08 is an intentional `ABSTAIN`; packages preserve MP4, still/contact sheet, manifest, provenance, and QA. |
| `HWang0310/deeptalk-handdrawn-animation` | `33422715f1627d7eaef7cc1ccbea7434b833d360` | CB01 is `ABSTAIN`, CB06 is `BORDERLINE`, the other six are `SUITABLE`; seven trial candidates passed mechanical QA while retaining non-blocking composition warnings. |

The shared facts are: every family receives concise semantic intent plus duration/canvas constraints; every family can make an autonomous suitability judgment; successful generation produces a short primary video and machine-verifiable evidence. Native input types, scene states, renderer routes, grammar names, primitive IDs, and review rubrics materially differ.

## Non-goals

- No plugin runtime, registry, adapter, candidate portfolio, migration, Episode workflow, A-roll alignment change, automatic edit, or production integration is implemented here.
- Core does not select a winner, suppress a family overlap, or require every plugin to generate for every opportunity.
- The contract does not expose MG grammar/profile, Illustrated Metaphor scene states/routes, Hand-drawn SVG elements/groups, prompts, renderer flags, or internal IDs.
- V1 does not define a `REAL_MATERIAL` generator contract, a fixed artifact filename, a universal scene graph, a fixed candidate quota, or a cross-plugin aesthetic score.

## Terminology and lifecycle

- **Visual Opportunity:** Core-owned, real-A-roll-anchored invitation for optional visual treatment. No opportunity means no extra asset.
- **Plugin:** Independently versioned visual-family implementation.
- **Suitability:** Plugin product/capability judgment, separate from execution.
- **Candidate:** A plugin-produced, independently QA'd possible asset. Candidates are intentionally non-exclusive.
- **Artifact:** A typed candidate attachment, addressed by role instead of filename.

```text
Core creates Visual Opportunity
  → each enabled plugin assesses suitability independently
  → Core policy may request generation for suitable and/or borderline proposals
  → plugin returns Candidate Result and artifact evidence
  → Core retains machine results; Candidate Portfolio keeps alternatives
  → creator-facing pack defaults to READY candidates; creator selects none, one, or many
```

The two-stage boundary is required by evidence. A one-stage generator-only API cannot represent a successful Illustrated Metaphor numeric abstention or a successful Hand-drawn core-judgment abstention. It also permits a `BORDERLINE` asset to be generated when it remains useful as a creator option.

## Contract envelope and identity

Every message has `contract_version: "visual-asset-plugin-contract/1"`. This identifies the compatibility boundary and is unrelated to an individual plugin release. Every response includes a plugin-owned `plugin_id` and `plugin_version`, which may advance independently. `request_id` correlates a call and `opportunity_id` binds results to the Core-owned opportunity; both are opaque to plugins.

## Visual Opportunity input

The minimum required input is:

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "req_…",
  "opportunity_id": "opp_…",
  "spoken_semantics": "The viewer-facing meaning to explain.",
  "visual_purpose": "What visual understanding should add.",
  "a_roll_window": { "start_ms": 182400, "end_ms": 190400 },
  "target_duration_ms": 7000,
  "language": "zh-CN",
  "canvas": { "width": 1920, "height": 1080 }
}
```

`a_roll_window` is Core-derived real time, never script-estimated time. `target_duration_ms` is a target rather than a forced equality because the families have different natural duration ranges. `spoken_semantics`, `visual_purpose`, duration, language, and canvas are evidenced by all three trials or natural-I/O documents.

Optional fields are deliberately narrow:

| Field | Meaning |
|---|---|
| `semantic_context` | Extra bounded spoken context needed to avoid a misleading isolated treatment. |
| `factual_context` | References to already-approved Core facts/provenance relevant to visible copy or factual claims; it never relaxes factual safety. |
| `plugin_context` | Plugin-addressed opaque JSON. Core transports it but never reads, validates semantic meaning from it, or makes policy from it. |

No maximum duration, grammar, route, renderer, prompt, primitive, scene state, or required common display-text field enters V1. Each plugin translates this input to its own native validated model internally.

## Suitability proposal

Each enabled plugin responds before generation:

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "req_…",
  "opportunity_id": "opp_…",
  "plugin_id": "org.deeptalk.illustrated-metaphor",
  "plugin_version": "0.x",
  "proposal_id": "prop_…",
  "operation_status": "COMPLETED",
  "suitability": "BORDERLINE",
  "reason": "The metaphor conveys the transition, but not its exact business condition."
}
```

Required: `contract_version`, `request_id`, `opportunity_id`, `plugin_id`, `plugin_version`, `proposal_id`, and `operation_status`. A `COMPLETED` proposal also requires `suitability` and short `reason`.

`suitability` is exactly one of:

- `SUITABLE`: the family can naturally add value.
- `BORDERLINE`: a candidate may be valuable, but naturalness or semantic precision has an evidenced limitation.
- `ABSTAIN`: the family should not generate this opportunity; this is a normal successful capability judgment.

`operation_status` is separately `COMPLETED`, `FAILED`, or `UNAVAILABLE`. The latter two require a structured `problem` (`code`, human-readable `message`, optional retryability) and omit `suitability`; they never masquerade as `ABSTAIN`.

Core logs every proposal for audit. A normal creator-facing Candidate Asset Pack omits abstentions, while an optional diagnostics view may say that a family declined because it was not a natural fit. ABSTAIN does not count against plugin health; health measures operational failures and availability separately.

## BORDERLINE policy

- A `BORDERLINE` proposal is eligible for generation. Both Illustrated Metaphor and Hand-drawn generated borderline trial candidates.
- Core policy, not the plugin contract, decides whether a product profile asks it to generate.
- If generated and QA-ready, it remains a valid non-exclusive candidate. Core presentation may assign lower `suggested_review_order`, an inspection hint that never chooses a winner.
- V1 defines neither a universal numeric score nor cross-family ranking.

## Generation request and result

Core sends generation only for a completed `SUITABLE` or `BORDERLINE` proposal. The request includes the complete Visual Opportunity plus `proposal_id`; plugins must not rely on hidden assessment-call state.

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "req_…",
  "proposal_id": "prop_…",
  "opportunity": {
    "contract_version": "visual-asset-plugin-contract/1",
    "request_id": "req_…",
    "opportunity_id": "opp_…",
    "spoken_semantics": "The viewer-facing meaning to explain.",
    "visual_purpose": "What visual understanding should add.",
    "a_roll_window": { "start_ms": 182400, "end_ms": 190400 },
    "target_duration_ms": 7000,
    "language": "zh-CN",
    "canvas": { "width": 1920, "height": 1080 }
  }
}
```

A Generation Result has common identity fields and exactly one `candidate` when one was created, or a `problem` when none can be returned. Candidate execution state is separate from suitability:

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "req_…",
  "opportunity_id": "opp_…",
  "plugin_id": "org.deeptalk.mg",
  "plugin_version": "0.x",
  "candidate": {
    "candidate_id": "cand_…",
    "asset_family": "MG",
    "candidate_status": "READY",
    "duration_ms": 8000,
    "suggested_placement": { "start_ms": 182400, "end_ms": 190400 },
    "artifacts": [
      { "role": "PRIMARY_MEDIA", "uri": "plugin://asset.mp4", "media_type": "video/mp4", "sha256": "…", "duration_ms": 8000 },
      { "role": "MANIFEST", "uri": "plugin://manifest.json", "media_type": "application/json" },
      { "role": "QA_REPORT", "uri": "plugin://qa.json", "media_type": "application/json" }
    ],
    "qa": { "status": "PASSED", "summary": "all required checks passed" },
    "provenance": { "origin": "plugin-generated", "source_ref": "plugin-native manifest reference" },
    "plugin_metadata": {}
  }
}
```

Generation Result required fields are `contract_version`, `request_id`, `opportunity_id`, `plugin_id`, and `plugin_version`, plus either `candidate` or `problem`. Candidate required fields are `candidate_id`, `asset_family`, and `candidate_status` in addition to enclosing plugin identity. A `READY` candidate also requires `duration_ms`, `suggested_placement`, at least one `PRIMARY_MEDIA` artifact, `qa.status: PASSED`, and provenance. `asset_family` is a stable plugin-supplied display/category string, not a Core-controlled closed enum.

`suggested_placement` is a recommendation within or anchored to the opportunity's real A-roll window. It may differ from the original window because a candidate can be shorter; it is not an edit decision and never alters A-roll.

## Status, failures, and artifacts

`candidate_status` is exactly one of:

| Status | Meaning |
|---|---|
| `READY` | Candidate exists and required QA passed. |
| `FAILED` | An unexpected generation or artifact process failure prevented a usable candidate. |
| `BLOCKED` | A declared prerequisite, policy gate, or safe input condition prevented generation. |
| `QA_REJECTED` | A candidate was produced but failed required QA. |
| `UNAVAILABLE` | The plugin, a required local capability, or runtime is unavailable. |

Every non-READY candidate and every generation result without a candidate has a `problem`; a `QA_REJECTED` candidate may retain partial artifacts and a QA report for machine audit, but never enters the normal creator pack. `ABSTAIN` is intentionally absent from this enum.

Every artifact has required `role` and `uri`, with optional `media_type`, `sha256`, `duration_ms`, and `metadata`. Roles are:

- `PRIMARY_MEDIA` — usable visual media; required for `READY`.
- `PREVIEW` — a still, frame sequence, or contact sheet.
- `MANIFEST` — plugin-native asset/render manifest.
- `QA_REPORT` — machine QA evidence.

The bundle is role-based, not filename-, renderer-, or format-based. All three inspected families have primary media and QA evidence, but V1 does not force each candidate to supply both a still and a contact sheet.

## QA, provenance, and opaque metadata

The contract transports compact QA status and a pointer to QA evidence; it does not standardize plugin-internal checks. This preserves MG media/structural QA, Illustrated Metaphor provenance/state/readability checks, and Hand-drawn mechanical QA plus warnings.

Provenance identifies that an asset was plugin-generated and where plugin-native manifest/evidence originates. Existing Core factual, source, rights, and binding requirements remain; a generated asset may not claim documentary evidence merely because it has a manifest.

`plugin_metadata` is optional opaque JSON. Core may store and round-trip it for machine audit, but must not branch product logic, compare internal values across plugins, or promote a subfield to a common requirement. MG grammar/profile, Illustrated Metaphor actor/route/state detail, and Hand-drawn groups/primitives remain private.

## Non-exclusive portfolio

Candidate Portfolio retains all `READY` candidates that pass required Core-side safety/lineage checks. One opportunity may simultaneously receive READY MG, Illustrated Metaphor, and Hand-drawn results, even with duration/window overlap. Portfolio never chooses a winner or treats overlap as conflict. The creator may use none, one, or multiple candidates.

## Legacy compatibility strategy

No migration is implemented. A future adapter layer, rather than a rewrite, should:

1. Read existing V1 `KEEP_A_ROLL`, `MG_MOTION`, `ADVANCED_MOTION`, and `REAL_MATERIAL` lineage unchanged.
2. Convert only new eligible visual planning intent into a Visual Opportunity; `KEEP_A_ROLL` maps to no new opportunity, never a fake candidate.
3. Preserve old `edit-map/1`, visual-asset manifests, Asset Packs, and Finished Cut Review records through compatibility readers.
4. Write any portfolio artifact beside legacy artifacts with a new version and reader, never overwrite history.

## REAL_MATERIAL decision

`REAL_MATERIAL` is excluded from generated-plugin Contract V1. It is an evidence/retrieval family with rights, capture, and factual-provenance obligations not demonstrated by the three generated-plugin trials. A separate retrieval/evidence adapter or V1.x extension may share portfolio packaging only after dedicated evidence; it must not be forced into a generator-shaped lifecycle.

## Paper mapping

| Real trial case | Proposal | Generation / Candidate representation | Internal facts deliberately not exposed |
|---|---|---|---|
| MG CB08 Numeric Evidence | `SUITABLE` with MG reason | `READY` MG candidate, 8s placement, primary MP4 + preview + manifest + QA report | `delta-metric`, `editorial-cn-v1`, semantic variant, Remotion composition. |
| Illustrated CB03 Accumulation Pressure | `SUITABLE` with physical-load reason | `READY` Illustrated candidate, 5s placement, MP4/sequence/contact sheet + manifest + QA | B1 vocabulary, actor/object choice, `structured_hybrid`, state names, focal treatment. |
| Illustrated CB01 Core Judgment | `BORDERLINE` with recursive-dependency limitation | Core may request; if generated, `READY` candidate remains in portfolio with borderline-derived review hint | wheel interpretation, generic actor, route, and overreach rubric. |
| Illustrated CB08 Numeric Evidence | `ABSTAIN` with precision/evidence reason | No generation request or candidate; machine proposal retained, creator pack unchanged | attempted metaphor/scene details. |
| Hand-drawn CB02 Causal Transmission | `SUITABLE` with staged-reveal reason | `READY` Hand-drawn candidate, 9s placement, primary media + preview/contact sheet + QA | composition grammar, SVG elements, groups, reveal timing, warnings. |
| Hand-drawn CB06 Surface vs Mechanism | `BORDERLINE` with hidden-mechanism limitation | Generation permitted; if rendered and QA passes, valid non-exclusive candidate | SVG composition pattern, focus warnings, element IDs. |
| Hand-drawn CB01 Core Judgment | `ABSTAIN` with headline-misfit reason | No candidate; successful proposal audit record only | any forced object/scene implementation. |

The mapping proves that observed suitability outcomes, candidate forms, evidence, QA, and abstentions all fit without Core learning native scene models.

## Explicitly deferred questions

- Core implementation shape, registry/discovery, transport/security, storage URI, and authentication.
- Exact Portfolio/Candidate Asset Pack schemas, creator diagnostics UI, and calculation of a review-order hint.
- Complete Core-side validation of URIs/hashes and integration with source/rights/factual binding gates.
- Legacy V1 adapter mechanics and a future `edit-map/2`.
- `REAL_MATERIAL` retrieval/evidence contract.
- Data visualization, maps, 3D diagrams, and future families; each needs its own evidence first.

## Risks and review criteria

The trial is a fixed synthetic brief set, not real multi-plugin episode validation. V1 is ready for implementation planning only if Architecture Review accepts that: the two-stage split is sufficient; `BORDERLINE` is a Core policy concern rather than forced rejection; normal abstention is not operational failure; artifact roles are enough without a universal media schema; and keeping `REAL_MATERIAL` outside V1 is safer than premature abstraction.

No plugin repository was modified. No DeepTalk production integration code was implemented.
