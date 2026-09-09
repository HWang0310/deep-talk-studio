# Visual Asset Plugin Contract V1 — Architecture Design

> **Status:** **ACCEPTED_UNRELEASED** architecture. It is not production code, runtime-schema adoption, a migration, a release, a tag, or a `main` change. The next gate is separate Multi-Asset Implementation Planning.

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

Every operation message has `contract_version: "visual-asset-plugin-contract/1"`. This identifies the compatibility boundary and is unrelated to an individual plugin release. Every response includes a plugin-owned `plugin_id` and `plugin_version`, which may advance independently.

The identifiers have deliberately separate scopes:

| Identifier | Scope and rule |
|---|---|
| `request_id` | Correlation ID for one contract operation/call. A Suitability call and a Generation call use different IDs; each response echoes the request ID of the call it answers. It is never cross-stage workflow identity. |
| `opportunity_id` | Stable identity for one Core Visual Opportunity across all stages. |
| `proposal_id` | Stable identity of one completed suitability proposal. It links the Generation Request and Generation Result back to that proposal. |
| `candidate_id` | Stable identity of one actually produced candidate asset. It exists only when generation completes with a candidate. |

`Visual Opportunity` is the stable payload identified by `opportunity_id`; `request_id` belongs to an operation envelope, not to that durable payload.

## Visual Opportunity input

The minimum required Visual Opportunity payload is:

```json
{
  "opportunity_id": "opp_…",
  "spoken_semantics": "The viewer-facing meaning to explain.",
  "visual_purpose": "What visual understanding should add.",
  "a_roll_window": { "start_ms": 182400, "end_ms": 190400 },
  "target_duration_ms": 7000,
  "language": "zh-CN",
  "canvas": { "width": 1920, "height": 1080 }
}
```

`a_roll_window` is Core-derived real time, never script-estimated time. `target_duration_ms` is a target rather than a forced equality because the families have different natural duration ranges. `spoken_semantics`, `visual_purpose`, duration, language, and canvas are evidenced by all three trials or natural-I/O documents. A Suitability Request wraps this payload with `contract_version` and a suitability-call `request_id`.

Optional fields are deliberately narrow:

| Field | Meaning |
|---|---|
| `semantic_context` | Extra bounded spoken context needed to avoid a misleading isolated treatment. |
| `factual_context` | References to already-approved Core facts/provenance relevant to visible copy or factual claims; it never relaxes factual safety. |
| `plugin_context` | Plugin-addressed opaque JSON. Core transports it but never reads, validates semantic meaning from it, or makes policy from it. |

No maximum duration, grammar, route, renderer, prompt, primitive, scene state, or required common display-text field enters V1. Each plugin translates this input to its own native validated model internally.

## Suitability proposal

Each enabled plugin receives a Suitability Request before generation. Its operation envelope has a suitability-call correlation ID and wraps the full Visual Opportunity payload defined above:

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "suit-req_…",
  "opportunity": {
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

The response echoes that suitability-call ID:

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "suit-req_…",
  "opportunity_id": "opp_…",
  "plugin_id": "org.deeptalk.illustrated-metaphor",
  "plugin_version": "0.x",
  "proposal_id": "prop_…",
  "operation_status": "COMPLETED",
  "suitability": "BORDERLINE",
  "reason": "The metaphor conveys the transition, but not its exact business condition."
}
```

Suitability Response common required fields are `contract_version`, `request_id`, `opportunity_id`, `plugin_id`, `plugin_version`, and `operation_status`.

If `operation_status` is `COMPLETED`, the response additionally requires `proposal_id`, `suitability`, and a short `reason`. Only this successfully completed Suitability Proposal creates `proposal_id`:

- `COMPLETED` + `SUITABLE`: `proposal_id` exists and Generation may be requested.
- `COMPLETED` + `BORDERLINE`: `proposal_id` exists and Generation may be requested under Core policy.
- `COMPLETED` + `ABSTAIN`: `proposal_id` exists as a successful audit record, but no Generation Request is sent.

`suitability` is exactly one of:

- `SUITABLE`: the family can naturally add value.
- `BORDERLINE`: a candidate may be valuable, but naturalness or semantic precision has an evidenced limitation.
- `ABSTAIN`: the family should not generate this opportunity; this is a normal successful capability judgment.

`operation_status` is separately `COMPLETED`, `FAILED`, or `UNAVAILABLE`. `FAILED` and `UNAVAILABLE` require a structured `problem` (`code`, human-readable `message`, optional retryability), omit `proposal_id`, `suitability`, and `reason`, and never send a Generation Request. They never masquerade as `ABSTAIN`.

Core logs every proposal for audit. A normal creator-facing Candidate Asset Pack omits abstentions, while an optional diagnostics view may say that a family declined because it was not a natural fit. ABSTAIN does not count against plugin health; health measures operational failures and availability separately.

## BORDERLINE policy

- A `BORDERLINE` proposal is eligible for generation. Both Illustrated Metaphor and Hand-drawn generated borderline trial candidates.
- Core policy, not the plugin contract, decides whether a product profile asks it to generate.
- If generated and QA-ready, it remains a valid non-exclusive candidate. Core presentation may assign lower `suggested_review_order`, an inspection hint that never chooses a winner.
- V1 defines neither a universal numeric score nor cross-family ranking.

## Generation request and result

Core sends generation only for a completed `SUITABLE` or `BORDERLINE` proposal. The request has a new generation-call `request_id`, includes the complete Visual Opportunity plus `proposal_id`, and plugins must not rely on hidden assessment-call state.

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "gen-req_…",
  "proposal_id": "prop_…",
  "opportunity": {
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

A Generation Result echoes the generation-call `request_id` and must include `proposal_id`, so the complete lineage is explicit: `Visual Opportunity → Suitability Proposal → Generation Request → Generation Result → Candidate`. Generation operation state is separate from candidate asset state:

```json
{
  "contract_version": "visual-asset-plugin-contract/1",
  "request_id": "gen-req_…",
  "opportunity_id": "opp_…",
  "proposal_id": "prop_…",
  "plugin_id": "org.deeptalk.mg",
  "plugin_version": "0.x",
  "operation_status": "COMPLETED",
  "candidate": {
    "candidate_id": "cand_…",
    "asset_family": "MG",
    "candidate_status": "READY",
    "duration_ms": 8000,
    "suggested_placement": { "start_ms": 182400, "end_ms": 190400 },
    "artifacts": [
      { "role": "PRIMARY_MEDIA", "uri": "opaque-locator-for-asset", "media_type": "video/mp4", "sha256": "…", "duration_ms": 8000 },
      { "role": "MANIFEST", "uri": "opaque-locator-for-manifest", "media_type": "application/json" },
      { "role": "QA_REPORT", "uri": "opaque-locator-for-qa", "media_type": "application/json" }
    ],
    "qa": { "status": "PASSED", "summary": "all required checks passed" },
    "provenance": { "origin": "plugin-generated", "source_ref": "plugin-native manifest reference" },
    "plugin_metadata": {}
  }
}
```

Generation Result required fields are `contract_version`, `request_id`, `opportunity_id`, `proposal_id`, `plugin_id`, `plugin_version`, and `operation_status`. Generation `operation_status` is exactly `COMPLETED`, `FAILED`, `BLOCKED`, or `UNAVAILABLE`. `FAILED`, `BLOCKED`, and `UNAVAILABLE` require `problem` and normally contain no `candidate`. `COMPLETED` contains exactly one candidate with a candidate asset status.

Candidate required fields are `candidate_id`, `asset_family`, and `candidate_status` in addition to enclosing plugin/proposal identity. A `READY` candidate also requires `duration_ms`, `suggested_placement`, at least one `PRIMARY_MEDIA` artifact, `qa.status: PASSED`, and provenance. `asset_family` is a stable plugin-supplied display/category string, not a Core-controlled closed enum.

`suggested_placement` is a recommendation strictly within the opportunity's real A-roll window. It must satisfy `a_roll_window.start_ms <= suggested_placement.start_ms < suggested_placement.end_ms <= a_roll_window.end_ms`. A plugin must not expand the real-time boundary. Future pre-roll, post-roll, or transition extension requires a Core-expanded Opportunity or a contract revision. `duration_ms` is the duration of the complete media asset; suggested placement is the recommended A-roll use window. They are distinct, and candidate duration may exceed placement duration because a creator may use only part of an asset.

## Status, failures, and artifacts

Generation operation status and candidate asset status are different domains. `candidate_status` exists only when a candidate was actually produced and is exactly one of:

| Status | Meaning |
|---|---|
| `READY` | Candidate exists and required QA passed. |
| `QA_REJECTED` | A candidate was produced but failed required QA. |

`QA_REJECTED` requires the actual candidate identity and `qa.status: FAILED`; it may retain artifacts and a QA report for machine audit, but never enters the normal creator pack. There is no third produced-but-incomplete candidate state in V1. Whether one is needed is explicitly deferred. `ABSTAIN` is intentionally absent from this enum.

Every artifact has required `role` and `uri`, with optional `media_type`, `sha256`, `duration_ms`, and `metadata`. In V1, `uri` is an opaque artifact locator: the contract does not prescribe `file://`, `http://`, `plugin://`, absolute paths, storage backends, runtime resolution, or URI validation. Those runtime questions belong to implementation planning. Roles are:

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
| MG CB08 Numeric Evidence | `SUITABLE` proposal | New generation request ID + `proposal_id`; completed result echoes both and returns a `READY` MG candidate, 8s media, placement inside the Opportunity, media/preview/manifest/QA | `delta-metric`, `editorial-cn-v1`, semantic variant, Remotion composition. |
| Illustrated CB03 Accumulation Pressure | `SUITABLE` proposal | New generation request ID + `proposal_id`; completed result returns a `READY` 5s candidate with placement inside the Opportunity and evidence bundle | B1 vocabulary, actor/object choice, `structured_hybrid`, state names, focal treatment. |
| Illustrated CB01 Core Judgment | `BORDERLINE` proposal | Core may generate; completed result echoes `proposal_id` and a QA-passing result is `READY`, not a special borderline status | wheel interpretation, generic actor, route, and overreach rubric. |
| Illustrated CB08 Numeric Evidence | `ABSTAIN` proposal | No Generation Request and no candidate; successful proposal audit record only | attempted metaphor/scene details. |
| Hand-drawn CB02 Causal Transmission | `SUITABLE` proposal | New generation request ID + `proposal_id`; completed result returns a `READY` 9s candidate with placement inside the Opportunity and evidence bundle | composition grammar, SVG elements, groups, reveal timing, warnings. |
| Hand-drawn CB06 Surface vs Mechanism | `BORDERLINE` proposal | Generation permitted; a completed QA-passing result is `READY` and stays non-exclusive | SVG composition pattern, focus warnings, element IDs. |
| Hand-drawn CB01 Core Judgment | `ABSTAIN` proposal | No Generation Request and no candidate; successful proposal audit record only | any forced object/scene implementation. |

For every generation-eligible mapping, a runtime `FAILED`, `BLOCKED`, or `UNAVAILABLE` outcome returns its generation operation status plus `problem` and no fabricated candidate. If an actual candidate is produced but required QA fails, the completed Generation Result carries that candidate as `QA_REJECTED` with machine evidence. Every generated candidate is linked through its enclosing `proposal_id`; no plugin internals or placement outside its Opportunity are required.

The mapping proves that observed suitability outcomes, candidate forms, evidence, QA, and abstentions all fit without Core learning native scene models.

## Explicitly deferred questions

- Core implementation shape, registry/discovery, transport/security, storage URI, and authentication.
- Exact Portfolio/Candidate Asset Pack schemas, creator diagnostics UI, and calculation of a review-order hint.
- Whether a future contract needs a third produced-but-incomplete candidate state; V1 intentionally has only `READY` and `QA_REJECTED`.
- Complete Core-side validation of URIs/hashes and integration with source/rights/factual binding gates.
- Legacy V1 adapter mechanics and a future `edit-map/2`.
- `REAL_MATERIAL` retrieval/evidence contract.
- Data visualization, maps, 3D diagrams, and future families; each needs its own evidence first.

## Risks and review criteria

The trial is a fixed synthetic brief set, not real multi-plugin episode validation. Architecture Review accepted V1 on the basis that the two-stage split is sufficient; `BORDERLINE` is a Core policy concern rather than forced rejection; normal abstention is not operational failure; artifact roles are enough without a universal media schema; and keeping `REAL_MATERIAL` outside V1 is safer than premature abstraction. The next gate is separate implementation planning, not direct implementation.

No plugin repository was modified. No DeepTalk production integration code was implemented.
