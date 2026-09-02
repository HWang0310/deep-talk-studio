# DT-CORE-5-001 final validation evidence

- Date: 2026-09-02 (`Asia/Shanghai`)
- Branch: `agent/multi-asset-phase5-three-plugin-synthetic`
- Accepted Phase 4 base: `817ca8b424f18714e4280d3990c1bc4221ec8dbe`
- Gate result: **PASS — IMPLEMENTED_UNRELEASED / AWAITING NEXUS ACCEPTANCE**

This validation is synthetic-only. It does not enable production plugin config,
change Contract V1, modify a plugin repository, run a real Episode, select a
winner, edit media, start Phase 6, or claim a release.

## Core

- Real runner host preflight/version: PASS.
- Targeted Phase 3B/Phase 5/Portfolio/Pack/map suite: PASS — 64 tests, one
  expected opt-in real-render skip.
- Real three-plugin integration: PASS — one test in 382.169 seconds.
- Exact full command, `PYTHONPATH=src python3 -m unittest discover -s tests
  -v`: PASS — 691 tests in 268.125 seconds, six expected opt-in skips.
- Deterministic scheduling/config order, mixed outcomes, failure isolation,
  Candidate Portfolio, Candidate Asset Pack, and `candidate-edit-map/1` all
  passed.

## Native plugin validation

### MG — PASS

- Exact SHA: `7ae59f1115da8a011113c81f31d320783b0ce8a4`
- Version/runner: `1.0.0-contract-v1`; `node scripts/contract-runner.js`
- Validation: `npm test`; lint; typecheck; benchmark renders and QA;
  `verify:contract-runner`.
- Result: 42 tests passed with one intentional integration skip. All eight QA
  fixtures passed. Two fresh real runner executions produced identical
  proposal/candidate IDs and PRIMARY_MEDIA SHA-256
  `776fea74d705c7bc8b6867e9972040f4d2afcf207addb37a340750360c830bab`,
  7000 ms duration, and Contract QA `PASSED`.

### Illustrated Metaphor — PASS

- Exact SHA: `48848affe018fc2cff8ee15bad7a09bb002776e4`
- Version/runner: `0.2.0-contract-runner`; `python3 scripts/contract_runner.py`
- Validation: `PYTHONPATH=src python3 -m unittest discover -s tests -v`; V0,
  V0.2 comparison, and common-brief repository render commands.
- Result: 77 tests passed; fresh rendering produced 42, 31, and 7 local assets.

### Hand-drawn Animation — PASS

- Accepted corrected SHA: `853618bdf19ae66ec393211b77d970911f53f4bc`
- Version/runner: `handdrawn-animation-contract/0.1.0`;
  `node src/contract-runner.js`
- Validation: `npm test`; `npm run test:integration`; lint;
  `render:primitives`; `render:benchmarks`; `render:v11`; `render:v12`;
  `render:v13`; `render:common`; and their repository QA counterparts.
- Result: 77 unit tests and 14 real integration tests passed. Primitive-sheet
  rendering and every benchmark/common render and hard machine-QA gate passed.
  The former bounds overflow did not recur.

All three plugin worktrees remained at their exact SHAs and tracked-clean.

## Real synthetic product result

The real-runner evidence root is:

```text
/Users/hwang/Movies/Program/DeepTalk/.artifacts/DT-CORE-5-001-handdrawn-853618b-v2/
```

Forward/reverse schedules produced the same Portfolio identity
`CP-cf60d72f034e9531a77fd142`. The structural opportunity produced one accepted
candidate from each family; a numeric opportunity yielded normal ABSTAIN/no-call
for all three; and an injected Illustrated preflight failure left MG and
Hand-drawn deliverable. Every staged primary medium was non-empty H.264,
1920x1080, SHA-bound, and within the Core duration tolerance.

Midpoint frames and the creator-facing JSON/CSV/Markdown were inspected. The
Hand-drawn causal chain, MG causal-card composition, and Illustrated metaphor
were non-placeholder, understandable, visibly distinct, and adequate for a
creator to judge. The map explicitly permits none, one, or multiple candidates
and performs no winner selection or automatic edit.

`PRODUCT_USABLE_SYNTHETIC: PASS`.
