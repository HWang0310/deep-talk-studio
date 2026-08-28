"""Deterministic Contract V1 fixture emitter for later adapter tests."""

import json
import sys
from pathlib import Path


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "multi_asset_synthetic"
SCENARIOS = {
    "suitable": "suitability-completed-suitable.json",
    "abstain": "suitability-completed-abstain.json",
    "failed": "suitability-failed.json",
    "unavailable": "suitability-unavailable.json",
    "ready": "generation-completed-ready.json",
    "qa-rejected": "generation-completed-qa-rejected.json",
    "malformed": "invalid/invalid-enum.json",
}


def fixture_for_scenario(scenario):
    try:
        path = FIXTURE_ROOT / SCENARIOS[scenario]
    except KeyError as exc:
        raise ValueError(f"unknown synthetic fixture scenario: {scenario}") from exc
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: visual_asset_plugin_fakes.py <scenario>")
    print(json.dumps(fixture_for_scenario(args[0]), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
