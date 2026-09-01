---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '8d48561d-3a57-4032-842d-0fa6ea1c8cf2'
  PropagateID: '8d48561d-3a57-4032-842d-0fa6ea1c8cf2'
  ReservedCode1: 'bbfd5f2a-8eec-4203-bd97-ed6941cc41c0'
  ReservedCode2: 'bbfd5f2a-8eec-4203-bd97-ed6941cc41c0'
---

# DeepTalk Studio Roadmap

> **Canonical owner:** delivery-state classification. Read [PROJECT_STATE.md](PROJECT_STATE.md) first. A plan or a branch is not a release; an implementation is not a release.

## Released

### v0.6.1 — Formal Release

- Released at `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`.
- Includes the Motion Production Layer: reviewed-material safety, renderer adapters, actual MP4 QA, and release evidence.
- Earlier releases (`v0.1.0` through `v0.6.0`) remain documented in [docs/releases](docs/releases/) and [CHANGELOG.md](CHANGELOG.md).

## Accepted / Implemented / Unreleased

### V1.0 Candidate

- Topic discovery, Research, independent Fact Check, and approval lineage.
- Content Director + Script Agent V1, including Content Thesis, human confirmation, and reviewed-script quality gates.
- Final Clean A-roll, local `whisper.cpp` `large-v3` ASR, global monotonic alignment, Semantic Timeline, and timing safeguards.
- V1 Visual Director, asset generation/QA, Asset Pack + Edit Map, manual creator NLE assembly, and read-only Finished Cut Review / Production Feedback.
- No later tag or GitHub Release exists: this remains **V1.0 Candidate — Unreleased**.

## Current Validation

### 《牛来》 — first complete real production loop

- Completed local A-roll through Finished Cut Review / Production Feedback.
- 25 spans: 22 `KEEP_A_ROLL`, 3 MG; all three MG assets were used but shortened.
- Validates real A-roll timing, Edit Map usefulness, and creator-owned final editing.
- Reveals insufficient MG quantity/quality and plan-versus-actual window differences.
- Findings are episode evidence, not self-executing global policy.

### 《恒大》 — ready for recording

- Competitive Research, Fact Check, Content Thesis, human confirmation, and Final Reviewed Script are complete.
- Status is **READY_FOR_RECORDING**. A-roll, assets, and editing have not started.

## Current Work

### Visual Asset Plugin Contract V1 — accepted architecture

- Contract V1 is ACCEPTED_UNRELEASED architecture. Phase 0's strict validators, sanitized fixtures, test-only fake runner, and static configuration examples are ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation.
- Preserve the accepted multi-repo, plugin-first boundary; Phase 2's fake-only Core orchestration and `candidate-portfolio/1` are ACCEPTED / IMPLEMENTED_UNRELEASED. Phase 3A-2's one-pinned-MG synthetic integration is IMPLEMENTED_UNRELEASED / AWAITING_CHATGPT_REVIEW; production-schema adoption remains unstarted.
- Core relocation-safe artifact resolution is ACCEPTED / IMPLEMENTED_UNRELEASED: runtime resolution validates configured trusted historical roots, canonical artifact-relative identity, containment, symlink rejection, file existence, byte size, and SHA-256. Historical manifests are preserved. Current Production selection is explicit via machine-local `current_production_id`; filesystem mtime is no longer semantic truth. A formal immutable current-production index remains deferred.
- The [separate Multi-Asset Implementation Plan](docs/plans/2026-08-28-multi-asset-implementation-plan.md) is accepted. MG Phase 3A-1 is ACCEPTED / PINNED / IMPLEMENTED_UNRELEASED at `7ae59f1115da8a011113c81f31d320783b0ce8a4`. Core Phase 3A-2 is IMPLEMENTED_UNRELEASED / AWAITING_CHATGPT_REVIEW after one real synthetic suitability → generation → Core acceptance proof. Phase 3B has not started.

## Approved Next

### Multi-Asset Candidate Architecture — accepted direction; partially implemented, unreleased

```text
Semantic Timeline → Visual Opportunity → Candidate Portfolio
→ Candidate QA → Candidate Asset Pack → Multi-option Edit Map
→ creator manual NLE selection
```

- Candidates are non-exclusive and may overlap.
- The accepted ecosystem is multi-repo and plugin-first: independent visual families evolve behind a minimal Core contract rather than being absorbed into Core internals.
- V2 removes `KEEP_A_ROLL` from new candidate planning but preserves V1 compatibility readers/adapters.
- `REAL_MATERIAL` stays an independent evidence/documentary family.
- Visual Asset Plugin Contract V1 is ACCEPTED_UNRELEASED architecture. Phase 2 provides the accepted sanitized fake runtime portfolio and Core QA boundary; Phase 3A-2 adds one pinned MG synthetic integration awaiting review. Candidate Pack, migration, multi-plugin integration, and production workflow have not started.

### MG Quality V2

- Approved next; not implemented.
- Improve visual quality and art direction before increasing MG output volume.

## Experimental / Under Product Validation

- **Hand-drawn Animation V1:** approved experiment, not a renderer.
- **Xiaohei:** third-party prototype/experimental reference; no claim of DeepTalk IP and no long-term identity commitment.
- **Candidate density:** soft LEAN/STANDARD/RICH profiles; current creator prefers RICH, but no fixed counts or hard schema rules.
- **Original DeepTalk character / visual identity:** undecided.

## Deferred / Not Planned

- Automatic final editing, automatic candidate choice, or visual-overlap resolution.
- Take choice, A-roll deletion/cleanup, pause/re-record removal, retiming, or human-speech splicing.
- 剪映/NLE project generation, final-cut output, automatic publishing, TTS/fake presenter, BGM/SFX, cover/title automation, or engagement prediction.
- Treating a single episode as sufficient evidence to rewrite global aesthetic policy.

## Historical Milestones

- v0.1–v0.4.1: research, fact check, topic discovery, script workflow, and gate hardening.
- v0.5–v0.5.1: material provenance, rights, and review gates.
- v0.6–v0.6.1: Motion Production Layer and formal release.
- Historical rough/full preview paths: preserved for compatibility and QA, not the current primary UX.
