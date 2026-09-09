#!/usr/bin/env python3
"""CLI wrapper for the importable calibration runner."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from deeptalk_studio.alignment_profile import load_alignment_profile  # noqa: E402
from evaluations.audio_alignment_edit_bridge.run_alignment_calibration import run_alignment_calibration  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-repeat", action="store_true")
    args = parser.parse_args()
    profile = load_alignment_profile()
    first = run_alignment_calibration(profile)
    if args.verify_repeat:
        second = run_alignment_calibration(profile)
        if first != second:
            raise SystemExit("repeat mismatch")
        print("repeat: identical")
    print(f"status: {first.calibration_status}; digest: {first.result_digest}")


if __name__ == "__main__":
    main()
