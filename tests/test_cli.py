import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, env=None):
    command = [sys.executable, "-m", "deeptalk_studio", *args]
    merged_env = os.environ.copy()
    merged_env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_help_lists_research_and_build_report(self):
        result = run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("research", result.stdout)
        self.assertIn("build-report", result.stdout)

    def test_sample_writes_a_readable_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_cli("sample", "--output", temp_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("示例报告已生成", result.stdout)
            self.assertEqual(len(list(Path(temp_dir).rglob("*.md"))), 1)
            self.assertEqual(len(list(Path(temp_dir).rglob("*.json"))), 1)

    def test_research_without_api_key_gives_simple_guidance(self):
        env = {"OPENAI_API_KEY": ""}
        result = run_cli("research", "某个话题", env=env)

        self.assertEqual(result.returncode, 2)
        self.assertIn("没有检测到 OPENAI_API_KEY", result.stderr)
        self.assertIn("Codex", result.stderr)


if __name__ == "__main__":
    unittest.main()

