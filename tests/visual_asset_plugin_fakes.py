"""Deterministic Contract V1 fixture emitter for later adapter tests."""

import json
import os
import signal
import sys
import time
import subprocess
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
    "generation-failed": "generation-failed.json",
    "generation-blocked": "generation-blocked.json",
    "generation-unavailable": "generation-unavailable.json",
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
    if scenario == "ignore-term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        pid_file = os.environ.get("FAKE_PID_FILE")
        if pid_file:
            Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")
        while True:
            time.sleep(0.1)
    if scenario == "orphan-ignore-term":
        pid_file = os.environ.get("FAKE_PID_FILE")
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import os,signal,time,pathlib; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "pathlib.Path(os.environ['FAKE_PID_FILE']).write_text(str(os.getpid())); "
                "time.sleep(300)",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        while not pid_file or not Path(pid_file).is_file():
            if child.poll() is not None:
                return child.returncode
            time.sleep(0.01)
        while True:
            time.sleep(0.1)
    if scenario == "non-zero": return 7
    if scenario == "missing-result": return 0
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if "proposal_id" in request and scenario in {"suitable", "borderline"}:
        scenario = "ready"
    if scenario == "borderline":
        response = fixture_for_scenario("suitable")
        response["suitability"] = "BORDERLINE"
    elif scenario != "wrong-contract":
        response = fixture_for_scenario(scenario)
    if scenario == "wrong-contract":
        response = fixture_for_scenario("suitable")
        response["contract_version"] = "visual-asset-plugin-contract/2"
    response["request_id"] = request["request_id"]
    response["opportunity_id"] = request["opportunity"]["opportunity_id"]
    response["plugin_id"] = os.environ.get("FAKE_PLUGIN_ID", "fake-visual-plugin"); response["plugin_version"] = os.environ.get("FAKE_PLUGIN_VERSION", "fake-1")
    if "proposal_id" in request: response["proposal_id"] = request["proposal_id"]
    if "candidate" in response and response["candidate"].get("candidate_status") == "READY":
        response["candidate"]["candidate_id"] = os.environ.get("FAKE_CANDIDATE_ID", response["candidate"]["candidate_id"])
        window = request["opportunity"]["a_roll_window"]
        response["candidate"]["suggested_placement"] = dict(window)
        response["candidate"]["duration_ms"] = request["opportunity"]["target_duration_ms"]
        response["candidate"]["artifacts"][0]["duration_ms"] = request["opportunity"]["target_duration_ms"]
        if os.environ.get("FAKE_WRITE_MEDIA") == "1":
            media = output_dir / "media.mp4"
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=1", "-an", "-c:v", "mpeg4", str(media)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            response["candidate"]["artifacts"][0]["uri"] = "local-runner://media.mp4"
            import hashlib
            response["candidate"]["artifacts"][0]["sha256"] = hashlib.sha256(media.read_bytes()).hexdigest()
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(response, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(temporary, result_path)
    print("fake plugin completed", file=sys.stderr)
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--version"]:
        print(os.environ.get("FAKE_PLUGIN_VERSION", "fake-1")); return 0
    if "--request" in args and "--result" in args and "--output-dir" in args:
        return _filesystem_main(args)
    if len(args) != 1:
        raise SystemExit("usage: visual_asset_plugin_fakes.py <scenario>")
    print(json.dumps(fixture_for_scenario(args[0]), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
