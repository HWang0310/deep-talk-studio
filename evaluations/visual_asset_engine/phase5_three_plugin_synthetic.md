# DT-CORE-5-001 Phase 5 three-plugin synthetic evidence

Status: `IMPLEMENTED_UNRELEASED / AWAITING NEXUS ACCEPTANCE`

This evidence is synthetic-only. It does not enable production plugin config,
select a winner, edit a cut, exercise REAL retrieval, or claim Phase 6 or a
release.

## Reproducible command

```bash
DEEPTALK_RUN_PHASE5_INTEGRATION=1 \
DEEPTALK_PHASE5_OUTPUT_ROOT=/Users/hwang/Movies/Program/DeepTalk/.artifacts/DT-CORE-5-001-handdrawn-853618b-v2 \
DEEPTALK_MG_PLUGIN_ROOT=/Users/hwang/Movies/Program/DeepTalk/deeptalk-mg \
DEEPTALK_ILLUSTRATED_PLUGIN_ROOT=/Users/hwang/Movies/Program/DeepTalk/deeptalk-illustrated-metaphor \
DEEPTALK_HANDDRAWN_PLUGIN_ROOT=/Users/hwang/Movies/Program/DeepTalk/.worktrees/deeptalk-handdrawn-animation-cv1-002 \
PYTHONPATH=src python3 -m unittest \
  tests.test_phase5_real_three_plugin_integration.RealThreePluginIntegrationTests -v
```

Result on 2026-09-02: `Ran 1 test in 382.169s — OK`.

Exact pins: MG `7ae59f1115da8a011113c81f31d320783b0ce8a4`, Illustrated
Metaphor `48848affe018fc2cff8ee15bad7a09bb002776e4`, and accepted
Hand-drawn correction `853618bdf19ae66ec393211b77d970911f53f4bc`.

The reusable entrypoint is
`evaluations.visual_asset_engine.phase5_three_plugin_eval`. It enables the
three exact pinned checkouts only in its in-memory runtime config and writes
large media plus machine evidence to the caller-selected external directory.

## Observed result

- Forward and reverse real subprocess invocation/collection schedules produced
  the same `CP-cf60d72f034e9531a77fd142` identity, raw Contract V1 responses,
  candidate IDs, Core truth/provenance, audit lineage, and creator eligibility.
  Wall-clock timestamps, durations, and absolute job argv are operational
  observations and are deliberately not semantic identity.
- The structural synthetic opportunity produced three raw `READY` / Core
  `ACCEPTED` candidates: `HANDDRAWN_SVG`, `MG`, and `Illustrated Metaphor`.
- The numeric synthetic opportunity naturally produced `ABSTAIN` / no-call for
  MG, Illustrated Metaphor, and Handdrawn. Core did not force any plugin to
  generate a semantically mismatched exact-percent candidate.
- An in-memory wrong expected SHA for Illustrated Metaphor produced a failed
  preflight with no fabricated raw response. The MG and Handdrawn candidates
  remained accepted and both reached `candidate-asset-pack/1` and
  `candidate-edit-map/1` JSON/CSV/Markdown.
- `ffprobe` confirmed every creator-pack primary medium was H.264, 1920×1080,
  non-empty, and within Core's 100 ms expected-duration tolerance. Core observed
  SHA-256 and duration evidence remained attached to each accepted candidate.

## Manual product review

Representative midpoint frames were extracted from the staged creator pack and
opened at original resolution:

- `cand_1c32a1be5a7a3780cf46dfb2` (Handdrawn): warm off-white hand-drawn causal
  chain with legible Chinese labels.
- `cand_78df65a3a80e63f3dea3374a` (MG): dark structured motion-graphics
  composition with causal cards and explicit synthetic-context copy.
- `cand-im-0c3aa09870a20288e65e2201` (Illustrated Metaphor): off-white framed
  character-and-object metaphor with a visibly different visual grammar.

The three families were intelligible, non-placeholder, technically valid, and
visibly distinct. The actual Markdown, CSV, and JSON were also inspected: every
creator-eligible candidate is present, `review_order` is browsing order only,
and the Markdown explicitly permits none, one, or several choices and says the
system will not select or auto-edit.

Machine evidence and review media for this run are under:

```text
/Users/hwang/Movies/Program/DeepTalk/.artifacts/DT-CORE-5-001-handdrawn-853618b-v2/
```

The root `phase5-evidence.json` records exact candidate IDs, family identities,
media probes, order-independence outcome, failure-isolation outcome, and paths
to the Portfolio, Candidate Asset Pack, and candidate edit maps.
