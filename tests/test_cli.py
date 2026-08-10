import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.quality import calculate_quality_summary
from tests.fixtures import valid_codex_draft_input, valid_fact_check_data, valid_report_data


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
    def test_help_lists_research_build_report_and_migrate(self):
        result = run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("research", result.stdout)
        self.assertIn("build-report", result.stdout)
        self.assertIn("migrate", result.stdout)
        self.assertIn("review-report", result.stdout)
        self.assertIn("prepare-draft", result.stdout)

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

    def test_malformed_nested_report_has_no_uncaught_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "bad.json"
            input_path.write_text(
                json.dumps({"schema_version": "0.2", "sources": [{}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            result = run_cli("build-report", str(input_path), "--output", temp_dir)

        self.assertEqual(result.returncode, 2)
        self.assertIn("无法生成报告", result.stderr)
        self.assertIn("缺少必填字段", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_json_has_no_uncaught_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "bad.json"
            input_path.write_text("{broken", encoding="utf-8")
            result = run_cli("validate", str(input_path))

        self.assertEqual(result.returncode, 2)
        self.assertIn("无法生成报告", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_review_report_applies_separate_artifact_and_creates_revision(self):
        data = valid_report_data()
        data["status"] = "fact_check_pending"
        data["fact_check"] = {
            "review_id": "",
            "reviewed_at": "",
            "status": "not_run",
            "checked_claim_ids": [],
            "unresolved_claim_ids": [],
        }
        for claim in data["claims"]:
            claim["verification_status"] = "not_checked"
        for link in data["evidence_links"]:
            link["verified_in_review"] = False
        data["quality_summary"] = calculate_quality_summary(data)
        artifact = valid_fact_check_data(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            draft_path = Path(temp_dir) / "draft.json"
            artifact_path = Path(temp_dir) / "fact-check.json"
            output_dir = Path(temp_dir) / "reports"
            draft_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            artifact_path.write_text(
                json.dumps(artifact, ensure_ascii=False), encoding="utf-8"
            )

            result = run_cli(
                "review-report",
                str(draft_path),
                str(artifact_path),
                "--output",
                str(output_dir),
            )
            reviewed_files = list(output_dir.rglob("research-report-r0002.json"))
            reviewed = (
                json.loads(reviewed_files[0].read_text(encoding="utf-8"))
                if reviewed_files
                else {}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("独立核查已应用", result.stdout)
        self.assertEqual(len(reviewed_files), 1)
        self.assertEqual(reviewed["status"], "reviewed")

    def test_prepare_draft_builds_machine_fields_for_codex_skill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "codex-input.json"
            output_dir = Path(temp_dir) / "reports"
            input_path.write_text(
                json.dumps(valid_codex_draft_input(), ensure_ascii=False),
                encoding="utf-8",
            )

            result = run_cli(
                "prepare-draft", str(input_path), "--output", str(output_dir)
            )
            reports = list(output_dir.rglob("research-report-r0001.json"))
            data = (
                json.loads(reports[0].read_text(encoding="utf-8")) if reports else {}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Research Draft 已生成", result.stdout)
        self.assertEqual(len(reports), 1)
        self.assertEqual(data["research_mode"], "codex_skill")
        self.assertEqual(data["status"], "fact_check_pending")


if __name__ == "__main__":
    unittest.main()
