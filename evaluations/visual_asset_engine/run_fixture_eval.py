import argparse
from pathlib import Path
from .fixture_episode import run_fixture_episode

parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True)
args = parser.parse_args(); result = run_fixture_episode(Path(args.output))
print(f"fixture-only: {result['manifest']['asset_count']} assets; not a real episode acceptance")
