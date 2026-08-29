"""Deterministic Contract V1 fixture emitter for later adapter tests."""

import json
import os
import sys
import time
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


def _filesystem_main(args):
    scenario = args[args.index("--scenario") + 1] if "--scenario" in args else "suitable"
    request_path = Path(args[args.index("--request") + 1])
    result_path = Path(args[args.index("--result") + 1])
    output_dir = Path(args[args.index("--output-dir") + 1]); output_dir.mkdir(parents=True, exist_ok=True)
    if scenario == "timeout":
        time.sleep(5); return 0
    if scenario == "non-zero": return 7
    if scenario == "missing-result": return 0
    request = json.loads(request_path.read_text(encoding="utf-8"))
    response = fixture_for_scenario(scenario)
    response["request_id"] = request["request_id"]
    response["opportunity_id"] = request["opportunity"]["opportunity_id"]
    response["plugin_id"] = "fake-visual-plugin"; response["plugin_version"] = "fake-1"
    if "proposal_id" in request: response["proposal_id"] = request["proposal_id"]
    if "candidate" in response and response["candidate"].get("candidate_status") == "READY":
        window = request["opportunity"]["a_roll_window"]
        response["candidate"]["suggested_placement"] = dict(window)
        response["candidate"]["duration_ms"] = request["opportunity"]["target_duration_ms"]
        response["candidate"]["artifacts"][0]["duration_ms"] = request["opportunity"]["target_duration_ms"]
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(response, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(temporary, result_path)
    print("fake plugin completed", file=sys.stderr)
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if "--request" in args and "--result" in args and "--output-dir" in args:
        return _filesystem_main(args)
    if len(args) != 1:
        raise SystemExit("usage: visual_asset_plugin_fakes.py <scenario>")
    print(json.dumps(fixture_for_scenario(args[0]), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
