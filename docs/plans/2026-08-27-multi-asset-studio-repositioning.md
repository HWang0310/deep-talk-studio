# Multi-Asset Studio Repositioning — Product / Technical Reconnaissance

**Status:** PROPOSAL — Awaiting ChatGPT Product Review
**Research date:** 2026-08-27
**Inspected baseline:** `4713505` (`agent/audio-alignment-edit-bridge`)
**Scope:** research/design only. No production code, formal contract/schema, Episode artifact, media, release, tag, or `main` change is made by this document.

## 1. Executive Summary

**[Proposal]** DeepTalk should be a reviewed-script system, visual-material director, multi-candidate asset generator, and real-A-roll manual-edit placement assistant for serious talking-head creators. It is not an automatic video editor.

The current real-A-roll and manual-NLE safety model should remain. The essential proposed change is from one mutually exclusive visual decision per semantic span to a two-stage model:

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio (1:many)
→ family-specific generation → Candidate Asset QA → Candidate Asset Pack
→ multi-option Edit Map → creator manually chooses in an NLE
```

**[Proposal]** Candidate assets are intentionally non-exclusive. Several assets can fully or partially overlap the same real A-roll range, have different durations, or belong to different visual families. DeepTalk recommends and locates them, but does not select a winner, resolve overlap, create tracks, or output a final edit.

**[Episode fact]** 《牛来》 validated the existing safety backbone, not a high-density target: 25 real semantic spans produced 22 `KEEP_A_ROLL` rows and 3 QA-ready MG clips. The user legally shortened and used all three; recorded feedback says their visual quality and quantity did not satisfy actual editing needs. That supports researching candidate breadth and MG V2 quality, not automatically increasing density for every future Episode.

## 2. Evidence Classes and Limitations

| Evidence label | Meaning | Materials actually inspected |
|---|---|---|
| **[Repo fact]** | committed implementation/contract | `src/deeptalk_studio/`, `docs/`, tests, `HANDOFF.md` |
| **[Episode fact]** | recorded real production observation | `HANDOFF.md` |
| **[Xiaohei fact]** | actual public repository inspection | GitHub README, `SKILL.md`, `style-dna`, `xiaohei-ip`, `composition-patterns`, LICENSE, NOTICE |
| **[Reference fact]** | actual local reference inspection | local videos, `ffprobe`, contact sheets, transcriptions and reports |
| **[Proposal]** | recommendation/assumption for review | this document |

The proposal is not an accepted PRD, an altered product contract, or an implemented capability. Where only tutorial videos/reports were available, exact source code and implementation libraries are marked as unverified.

## 3. Current Architecture Audit

### Existing product boundary

**[Repo fact]** `docs/ASSET_PACK_EDIT_MAP_CONTRACT.md` and `docs/FINISHED_CUT_REVIEW_CONTRACT.md` set the default path to Final Clean A-roll → ASR → alignment → semantic timeline → Visual Director → QA-ready assets → Asset Pack/Edit Map → human NLE assembly → read-only Finished Cut Review. They prohibit take selection, A-roll deletion/splicing, NLE-project generation, final-video output, and publishing. `asset_pack_workflow.py` and `finished_cut_review.py` reflect those restrictions.

### Existing models

- **[Repo fact]** `visual_director.py` emits `visual-director-plan/1`: exactly one of `KEEP_A_ROLL`, `REAL_MATERIAL`, `MG_MOTION`, or `ADVANCED_MOTION` per proposal. Non-KEEP decisions need a reason.
- **[Repo fact]** `motion_spec.py` emits `motion-spec/1` for MG/Advanced Motion. It has real-A-roll relative timing, display-fact binding, capacity limits, grammar types, and an Advanced Motion review gate.
- **[Repo fact]** `asset_pack_workflow.py` expects one decision per semantic span, finds at most one ready asset for it, then applies `ADVANCED → MG → REAL → KEEP` fallback. It writes `visual-asset-manifest/1` plus an `edit-map/1` row per span.
- **[Repo fact]** `visual_asset_pack.py` uses `06_真实素材/`, `07_MG动画/`, `08_高级动画/`, `09_剪辑表/`.
- **[Repo fact]** `finished_cut_review.py` binds the finished cut SHA to `edit-map/1` and `visual-asset-manifest/1`; it records `USED` / `NOT_USED` / `UNKNOWN`, actual clock/presentation/use mode, and only episode-level feedback.
- **[Repo fact]** `post_alignment_visual_plan.py` already projects semantic opportunities through real alignment, but still classifies `a_roll`, `real_material`, `original_motion`, or `hybrid` as mutually exclusive kinds. It is relevant input, not the proposed portfolio contract.

### Current Dependency Graph

```text
Reviewed Script + approved Research ───── factual/source binding ──┐
Final Clean A-roll → ASR → Timed Transcript → Alignment → Semantic Timeline
                                                   ↓
                                  Visual Director (`visual-director-plan/1`)
                                                   ↓ exactly one decision / span
                   ┌──────────────────────────────┴─────────────────────────────┐
              REAL material bridge                                  Motion Spec → renderer(s)
                   └──────────────────────────────┬─────────────────────────────┘
                                                  asset QA
                                                    ↓
                         Asset Pack → `visual-asset-manifest/1` + `edit-map/1`
                                                    ↓
                                      human manual NLE assembly
                                                    ↓
                       Finished Cut Review → Production Feedback Loop
```

**[Repo fact]** `visual-director-plan/1` is keyed by `cue_id`, while `asset_pack_workflow.py` consumes plan opportunities keyed by `span_id`; both contracts have tests, but this reconnaissance did not establish one canonical wiring between these particular builders. **[Proposal]** Treat this as a migration/consolidation risk, not as a reason to alter V1 now.

## 4. Product Repositioning

**[Proposal]** Product sentence:

> DeepTalk is a topic-and-reviewed-script system, visual-material director, multi-candidate asset generator, and real-A-roll manual-edit placement assistant for deep talking-head creators — not an automatic video editor.

Non-negotiable boundaries:

- no automatic take selection, pause removal, A-roll deletion, splicing, NLE project, finished cut, or final candidate choice;
- Final Clean A-roll is always the creator-controlled base layer; its ASR/alignment is the only formal clock source;
- offer options with honest QA/provenance, never a disguised automatic decision;
- retain all current fact, rights, source, media and immutability gates.

## 5. Visual Opportunity Model

**[Proposal]** A Visual Opportunity is an alignment-bound invitation to offer visuals, not an order to cover the speaker and not a timeline decision.

```json
{
  "opportunity_id": "VO-…",
  "real_aroll_start": "42.2",
  "real_aroll_end": "51.8",
  "semantic_text": "…",
  "visual_intent": "explain | evidence | contrast | metaphor | transition",
  "core_information_window": {"start": "…", "end": "…"},
  "why_opportunity": "…",
  "eligibility": "ready | blocked | no_opportunity",
  "alignment_digest": "…"
}
```

`no_opportunity` means DeepTalk has no useful offer. It does not mean the system chose to suppress A-roll; A-roll still remains the base layer.

## 6. Candidate Portfolio Model

**[Proposal]** A Visual Opportunity owns a Candidate Portfolio: a set of independent, non-winning alternatives. `priority` may mean “look at this first,” never “machine-selected winner.”

```text
VO-12, 00:42.2–00:51.8, abstract causal turn
  ├─ C-12A  MG, 00:43.0–00:49.2
  ├─ C-12B  Xiaohei stop-motion, 00:42.2–00:51.8
  └─ C-12C  hand-drawn, 00:44.1–00:48.7
```

All may be QA-ready. The user may use none, one, several, or a newly sourced visual. Different candidate duration and overlap are delivery data, not a conflict DeepTalk must eliminate.

## 7. Candidate Density Strategy

**[Proposal]** First find meaningful explanatory, evidentiary, contrast, mnemonic, or pacing opportunities. Only then generate portfolios where families provide truly different editorial value.

| Strategy | Hypothesised opportunities for a 5–6 minute Episode | Portfolio posture | Success criterion |
|---|---:|---|---|
| Minimum | about 6–10 | usually one candidate; a few differentiated alternatives | useful choice without forced coverage |
| Typical | about 10–16 | one to three candidates at appropriate opportunities | varied, placeable coverage across the Episode |
| Rich | about 16–24 | two to four differentiated candidates at high-value moments | broad creator choice, not file-count maximisation |

These are planning hypotheses, not hard-coded counts or release gates. Topic type, real evidence, A-roll performance, repetition risk, cost, and creator feedback govern final density.

## 8. KEEP_A_ROLL Migration Recommendation

**Recommendation — [Proposal]: remove it from new candidate planning; retain it through a compatibility adapter.**

1. A V2 opportunity with no value has zero candidates; it is not a `KEEP_A_ROLL` candidate.
2. `KEEP_A_ROLL` remains readable in historic V1 plans, Maps and Finished Cut Reviews.
3. An old KEEP row maps to a V2 `no_opportunity` span. An old non-KEEP row maps to a single imported legacy candidate using the original family.
4. No adapter may imply that historic KEEP means “no future visual could help.”

This preserves immutable lineage while fixing the new model's semantics: A-roll is always present rather than a decision outcome.

## 9. MG Quality V2 Analysis

### Current evidence

**[Episode fact]** The three 《牛来》 MG clips were semantically correct and technically usable, but the user reported low visual quality and insufficient choice.

**[Repo fact]** `motion_spec.py` provides timing, fact binding, and capacity safeguards. `visual_asset_renderer.py` compiles a deliberately small primitive set, applies a fixed dark “Neutral Editorial” appearance, uses shared geometric layouts, and relies mainly on a single cubic-opacity reveal cadence. These traits plausibly cause template feeling, but no rerender or fresh visual review of 《牛来》 was conducted here, so they are not a complete root-cause claim.

| Dimension | V2 diagnosis | Primary responsibility |
|---|---|---|
| Composition | generic rows/cards lack scene-specific staging | Visual Direction / Design System |
| Typography | safety exists; expressive Chinese hierarchy is narrow | Design System + Renderer Engineering |
| Visual hierarchy | title and uniform nodes compete for attention | Planning/Motion Spec + Design System |
| Motion grammar | few grammars / generic reveal order | Planning/Motion Spec |
| Easing | one safe curve can feel flat | Renderer Engineering |
| Transition | not art-directed per intent | Planning + Renderer Engineering |
| Primitive combination | primitives do not form rich scene systems | Design System + Renderer Engineering |
| Information density | a capacity limit is not choice of the strongest claim | Planning/Motion Spec |
| Template feeling | fixed colour, geometry, cadence, layout reuse | all layers |
| Art direction | no versioned MG art-direction system mediates mood/metaphor | Visual Direction / Design System |

**[Proposal]** “More MG” means more files. “Better MG” requires a stronger art-direction contract, scene grammar, layout variants, typography system, and deliberate motion semantics. Increase MG candidate count only after MG Quality V2 is separately validated.

## 10. Xiaohei Stop-motion Research

### Actual repository findings

**[Xiaohei fact]** The public [Ian Xiaohei Illustrations repository](https://github.com/helloianneo/ian-xiaohei-illustrations) is a Codex Skill for 16:9 Chinese article illustrations and shot lists. The inspected `README.md` and `SKILL.md` specify PNG outputs and expressly exclude an animation system, SVG, HTML and Canvas editable graphics. Its workflow is article understanding → cognitive-anchor shot list → one image-model call per still → QA.

**[Xiaohei fact]** Inspected: root `README.md`, `LICENSE`, `NOTICE.md`; `ian-xiaohei-illustrations/SKILL.md`; `references/style-dna.md`, `xiaohei-ip.md`, `composition-patterns.md`, `qa-checklist.md`. They specify white ground, black hand-drawn line work, restrained red/orange/blue notes, whitespace, one visual action, and the recurring “小黑” character. Composition patterns require newly invented metaphors rather than copied examples.

**[Xiaohei fact]** The repository uses MIT licence (copyright Ian, 2026). Its NOTICE says derived redistribution/adaptation should retain the Ian Xiaohei Illustrations name or attribute Ian, and identifies the examples and recurring Xiaohei character as Ian's visual language. MIT permits code/documentation reuse subject to notice conditions, but DeepTalk must retain applicable notice/attribution when copying/redistributing material and must not claim Xiaohei as DeepTalk-owned IP.

### Stop-motion extension proposal

**[Proposal]** Xiaohei Stop-motion is a proposed 3–10 second asset built from static scene states plus restricted deterministic motion; it is not an existing upstream video capability.

| Route | Method | Strength | Main risk |
|---|---|---|---|
| Independent keyframes | generate controlled successive states then compose stepped holds/cuts | clearest state change / stop-motion rhythm | character and frame drift; generation cost |
| One still + deterministic emphasis | one approved illustration plus reveal/pan/cut/object emphasis | lowest cost and repeatable after still creation | can feel like camera movement, not stop-motion |
| Structured state + composition hybrid | store character/object/layer/state deltas and compose fixed parts | strongest reproducibility and QA path | highest design/segmentation investment |

Prototype dependency and future visual identity must remain separate. A prototype may use an attributed/licence-compliant upstream dependency. A future DeepTalk identity needs original character, style tokens, scene grammar, and rights review; it must not be marketed as ownership of “小黑.”

### Quality, cost and fallback limits

- Put critical factual Chinese text in renderer-owned typography, not generated raster art; upstream documentation itself warns that short Chinese notes are more reliable.
- Require a reference sheet, explicit state deltas, image fingerprints and adjacency/contact-sheet review for continuity.
- Version style packs to control drift; use QA to reject mixed unreviewed packs.
- Per-state image generation incurs cost; deterministic composition only avoids recurring image-model calls after approved art exists.
- A local renderer can animate approved assets. This research found no complete local/no-key image-generation or character-consistent multi-state pipeline in the upstream repository, so such a promise would be unsupported.

## 11. Hand-drawn Animation Reference Audit

### Actual local inspection

**[Reference fact]** I inspected `/Users/hwang/Movies/自媒体创意库/Codex动画参考`: five MP4 tutorials; WAV/SRT/JSON transcript sets; keyframes/contact sheets; and Markdown analysis reports. It contains **no HTML, JS, TypeScript, SVG, Canvas, Remotion, CSS, or source-code files**. Exact libraries and algorithms are therefore unverified.

| Reference | `ffprobe` facts | Observed/documented grammar |
|---|---|---|
| 01 GitHub Xiaohei illustration | 100.055s, AV1, 1670×1080, 30fps | walkthrough of static article illustration, not an animation renderer |
| 02 Skill whiteboard | 632.488s, AV1, 1920×1080, 30fps | light canvas, black lines, accent colours, hand overlay, sequential diagram/image reveal; SRT-led flow described |
| 03 agent hand-drawn | 267.703s, AV1, 1920×1080, 30fps | metaphor stills, masks/hand illusion; HyperFrames UI appears in tutorial |
| 04 hand-drawn 1.0 | 324.011s, AV1, 1920×1080, 30fps | prepared monkey illustration, white mask removal and hand/pen overlay; story-order presentation |
| 05 hand-drawn 3.0 | 487.211s, AV1, 1920×1080, 30fps | SRT-to-clip flow with line-draw, colour-fill, element order/mask boundaries and hand overlay |

**[Reference fact]** I viewed all five contact sheets. Reusable visual cues are a light canvas, hand-drawn outlines, sparse red/green/orange accents, large hand/pen overlay, deliberate whitespace, sequential reveal and low-to-medium information density. Surrounding tutorial UI is evidence, not a DeepTalk visual requirement. Local reports/transcripts describe semantic segmentation, static illustration preparation, element ordering, masks/reveals/path-like drawing and preview QA. They explicitly distinguish 04's mask illusion from true per-line drawing; source code is unavailable.

### Hand-drawn Animation V1 proposal

**[Proposal]** Retain the grammar, not a promise to automate whole videos: one visual claim per candidate; constrained style pack; semantic element ordering; real-A-roll duration; holds; reveal/line/colour phases; minimal non-factual labels; and a return-to-A-roll recommendation.

```text
candidate brief + real window
→ approved/generate still → scene decomposition (elements/layers/safe text/order)
→ render plan (masks/path hints/hand/holds/accents)
→ deterministic render → candidate QA
```

This does not assume vector paths are recoverable from all raster art or that “zero token” covers original art generation.

## 12. Three Generated Families and REAL_MATERIAL

| Family | Portfolio responsibility | Must not become |
|---|---|---|
| MG Animation | concise temporal, causal, comparative or factual structure | generic card deck / sole visual answer |
| Xiaohei Stop-motion | memorable cognitive metaphor and state change | claimed DeepTalk-owned IP or real-world evidence |
| Hand-drawn Animation | explanatory reveal, process, causal story | substitute for source proof |
| REAL_MATERIAL | documentary/evidence option: approved court notice, photo, chart, screenshot/capture | generated-family quota item |

**Recommendation — [Proposal]: retain REAL_MATERIAL.** It should be product-language separate from the three generated families, yet enter a Candidate Asset Pack when existing provenance, rights/reuse, factual binding, capture and QA requirements pass. Knowledge video continues to need auditable documentary visuals that illustration cannot honestly replace.

## 13. Edit Map V2 Proposal

**[Proposal]** `edit-map/2` is a creator candidate map, not a final-decision table. It has repeated rows for one `opportunity_id` where appropriate.

Required fields: `opportunity_id`, `real_aroll_start`, `real_aroll_end`, `semantic_text`, `visual_intent`, `candidate_id`, `asset_family`, `asset_filename`, `asset_duration`, `recommended_placement_start`, `recommended_placement_end`, `core_information_window`, `suggested_display_mode`, `why_this_candidate`, `source_or_provenance`, `qa_state`; optional `priority` (only “look first”) and `confidence`.

| Output | Purpose | Multiple candidates |
|---|---|---|
| JSON | machine source of truth | one opportunity contains `candidates[]`, digests and full QA/provenance |
| CSV | NLE/spreadsheet helper | one row/candidate, repeated opportunity/time fields |
| Markdown | creator guide | group options under an opportunity and state “choose, combine manually, or use none” |

All formats must make overlapping/different-length options explicit and state that DeepTalk has not eliminated overlap, assigned tracks or chosen a final candidate.

## 14. Asset Pack V2 Proposal

**[Proposal]** Do not change current episode numbering/folder conventions until compatibility review. A V2 candidate pack may later expose distinct MG, Xiaohei Stop-motion, Hand-drawn, REAL_MATERIAL and edit-map folders, but exact names are a migration decision.

Replace “every non-KEEP decision has one ready asset” with portfolio-quality dimensions:

- opportunity coverage: eligible meaningful opportunities have at least one useful candidate;
- candidate readiness: every shown candidate independently passes media/binding/placement QA;
- family diversity: alternatives differ in visual function, not just colour/filename;
- QA pass rate: failures are visible; no invented replacement winner;
- provenance completeness: source/rights/style/generator lineage is available;
- creator choice clarity: folders, names and map permit comparison without machine JSON.

These are proposed evaluation dimensions, not an approved fixed score.

## 15. Finished Cut Review Adaptation

**[Proposal]** Keep it read-only and add: candidate `USED`/`NOT_USED`/`UNKNOWN`; family selection rate across reviewed Episodes; voluntarily supplied ignore reasons; selected candidate/family within an opportunity; planned/actual window delta; and presentation, shortening, extension or creator-added alternatives.

Non-use is never a failure or a wrong edit. No automatic taste score, creator score or one-Episode global policy change is permitted. The existing `EPISODE_OBSERVATION` → human/multi-Episode review constraint should be inherited.

## 16. Target Architecture V2

```text
Reviewed Script + approved Research ── factual/source binding ─────┐
Final Clean A-roll → ASR → Alignment → Real + Semantic Timeline    │
                             ↓                                    │
            Visual Opportunity Detection (`…/2`)                   │
                             ↓                                    │
            Candidate Portfolio Planning (`…/1`)                   │
       ┌─────────────┬───────────────┬───────────────┬────────────┘
       MG           Xiaohei        Hand-drawn   REAL_MATERIAL
       renderer     state/composition renderer  existing provenance/capture
       └──────────────────── Candidate Asset QA ───────────────────┐
                          ↓                                        │
 Candidate Asset Pack (`manifest/2`) + multi-option `edit-map/2`  │
                          ↓                                        │
                  User manual NLE selection                        │
                          ↓                                        │
  portfolio-aware, read-only Finished Cut Review + feedback        │
```

Existing canonical timing, fact binding, source/provenance guardrails, media QA, immutability and no-auto-edit boundaries are inherited, not reinvented.

## 17. Schema / Contract Migration Impact

| Current | Proposed disposition | Backward compatibility |
|---|---|---|
| `visual-director-plan/1` | supersede with opportunity + portfolio contracts | retain immutable V1 reader; write V2 only after approval |
| `KEEP_A_ROLL` | no new candidate-planning member | adapter maps to `no_opportunity` |
| `motion-spec/1` | retain timing/binding/capacity safety; version family specs | do not force new families into MG-only fields |
| `visual-asset-manifest/1` | candidate-aware manifest version | retain V1 digest/reader for historic review |
| Asset Pack | selected assets → portfolios | retain V1 folders/output until approved migration |
| `edit-map/1` | versioned `edit-map/2` | V1 stays readable and reviewable |
| Asset QA | selected-decision readiness → per-candidate readiness + portfolio assessment | no weakening of current gates |
| `finished-cut-review/1` | extend via new version/adaptor | retain old digests and plan/actual rows |

No current production contract/schema should be edited to imply V2 acceptance. Add versioned artifacts and explicit adapters before changing defaults.

## 18. Backward Compatibility

**[Proposal]** Completed Episodes remain immutable V1 lineages. Their decision, asset, digest, QA and Finished Cut Review remain historical truth. A V2 viewer may display them as one-candidate portfolios only when clearly labelled adapter-derived; it cannot claim they originally offered options. V1 and V2 consumers should coexist until migration tests, digest boundaries and creator usability review pass.

## 19. Risks

1. Candidate explosion can create clutter; control it through opportunity eligibility and real family differentiation.
2. More generation before MG V2 could multiply template-like assets.
3. Xiaohei attribution/IP requires MIT notice compliance, NOTICE-aware credit and an original-identity decision.
4. Image models risk Chinese errors, style drift and character/frame inconsistency; QA must be explicit.
5. REAL_MATERIAL gates must not erode; generated metaphor must never impersonate evidence.
6. Parallel V1/V2 contracts require adapters, digest boundaries and migration tests.
7. Feedback may only inform human review; it must not self-modify aesthetic policy.

## 20. Open Questions for Product Review

1. Is a short, attributed Xiaohei prototype desirable, or should DeepTalk begin with original identity only?
2. Which first slice is most valuable: MG + Hand-drawn, or all three generated families?
3. Should the first portfolio experience be folders/Markdown, with a contact-sheet browser later?
4. What evidence threshold supports the rich density mode where REAL_MATERIAL is sparse?
5. Does creator-facing `priority` help or risk looking like an automatic decision?
6. Should failed candidates remain visible for audit only, or be hidden from the creator pack while retained in machine records?

## 21. Proposed Implementation Phases

This is a proposal only; no implementation is authorised by it.

1. Approve vocabulary, artifact boundaries, adapters, candidate QA taxonomy and migration fixtures; do not replace V1 defaults.
2. Build data-only V2 opportunities and non-exclusive portfolios from real alignment; verify overlap, lineage, no-winner semantics and V1 adapters.
3. Validate MG Quality V2 art direction/scene grammar before increasing MG output volume.
4. Prototype one new family at a time with explicit rights/provenance policy and a non-production fixture.
5. Add parallel Candidate Pack/Edit Map V2 and candidate-aware QA while retaining V1 delivery.
6. Add portfolio-aware read-only feedback only after actual creator use; require multi-Episode/human review for policy changes.

## 22. What NOT to Build

- automatic candidate choice, a “best asset” winner, or timeline conflict resolution;
- take selection, A-roll deletion, silence removal, retiming, splicing or replacement;
- 剪映/NLE project generation, automatic montage or final-video output;
- automated taste/compliance scoring, engagement prediction or self-modifying visual policy;
- a claim that Xiaohei is DeepTalk IP;
- a claim of complete local/no-key image generation without separately verified capability;
- sentence-by-sentence asset flooding or file-count quotas unrelated to visual value.

## 23. Recommendation

**[Proposal]** Enter implementation planning only after Product Review approves: the opportunity/portfolio abstraction, the `KEEP_A_ROLL` migration, the Xiaohei-versus-original-identity position, and the first-family validation order. This direction preserves the real-A-roll, manual-edit, evidence-bound backbone while removing the false requirement that DeepTalk choose a single visual answer.
