# Phase 5 runner-host preflight evidence

- Task: `DT-CORE-5-001`
- Branch: `agent/multi-asset-phase5-three-plugin-synthetic`
- Accepted Phase 4 base: `817ca8b424f18714e4280d3990c1bc4221ec8dbe`
- Observed: 2026-09-02 (`Asia/Shanghai`)
- Host: macOS `26.6.2` (`25G83`), Darwin `25.6.0`, `arm64`
- Tools: Git `2.50.1 (Apple Git-155)`; Python `3.14.7`; Node.js
  `22.23.2`; npm `10.9.8`; ffmpeg/ffprobe `9.0.1`; sips `316`

## Pinned runners

All three checkouts were exact-HEAD and tracked-clean before and after their
native validations. Runner entrypoints existed, reported the configured
versions, and resolved the required local runtime dependencies.

| Plugin | Root and exact HEAD | Runner | Reported version |
| --- | --- | --- | --- |
| MG (`org.deeptalk.mg`) | `/Users/hwang/Movies/Program/DeepTalk/deeptalk-mg` at `7ae59f1115da8a011113c81f31d320783b0ce8a4` | `node scripts/contract-runner.js` | `1.0.0-contract-v1` |
| Illustrated Metaphor (`org.deeptalk.illustrated-metaphor`) | `/Users/hwang/Movies/Program/DeepTalk/deeptalk-illustrated-metaphor` at `48848affe018fc2cff8ee15bad7a09bb002776e4` | `python3 scripts/contract_runner.py` | `0.2.0-contract-runner` |
| Hand-drawn Animation (`org.deeptalk.handdrawn-animation`) | `/Users/hwang/Movies/Program/DeepTalk/.worktrees/deeptalk-handdrawn-animation-cv1-002` at `853618bdf19ae66ec393211b77d970911f53f4bc` | `node src/contract-runner.js` | `handdrawn-animation-contract/0.1.0` |

## Fresh preflight results

- Core real Phase 3B preflight/version test: PASS against the new Hand-drawn
  checkout and the exact Illustrated checkout.
- Core targeted Phase 5/portfolio/pack/map suite: PASS — 64 tests, one expected
  opt-in real-render skip.
- Exact full Core command, `PYTHONPATH=src python3 -m unittest discover -s
  tests -v`: PASS — 691 tests, six expected opt-in skips.
- MG: PASS — unit, lint, typecheck, benchmark render/QA, and deterministic real
  Contract runner verification.
- Illustrated: PASS — 77 tests plus V0, V0.2 comparison, and common-brief real
  rendering commands.
- Hand-drawn: PASS — 77 unit tests, lint, 14 real integration tests,
  `render:primitives`, and all repository benchmark/common render and QA gates.
  The old primitive-sheet bounds blocker did not recur.

## Gate result

`RUNNER_HOST_PREFLIGHT: PASS`. The accepted correction changes only the
Hand-drawn exact revision. MG and Illustrated pins, Contract V1, runner
semantics, and disabled production configuration remain unchanged.
