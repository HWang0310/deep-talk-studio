import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.quality import calculate_quality_summary
from tests.fixtures import (
    approved_report_data,
    valid_codex_draft_input,
    valid_discovery_input,
    valid_fact_check_data,
    valid_report_data,
    valid_script_content,
    valid_script_review_content,
)


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
        self.assertIn("discover", result.stdout)
        self.assertIn("select-topic", result.stdout)
        self.assertIn("approve-report", result.stdout)
        self.assertIn("prepare-script", result.stdout)
        self.assertIn("review-script", result.stdout)
        self.assertIn("compare-script", result.stdout)
        self.assertIn("revise-script", result.stdout)
        self.assertIn("write-script", result.stdout)
        self.assertIn("produce-assets", result.stdout)

    def test_produce_assets_help_exposes_simple_renderer_choice(self):
        result = run_cli("produce-assets", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--renderer", result.stdout)
        self.assertIn("auto", result.stdout)
        self.assertIn("remotion", result.stdout)
        self.assertIn("hyperframes", result.stdout)

    def test_prepare_review_and_compare_script_cli_have_clean_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "approved.json"
            content_path = root / "script-content.json"
            review_path = root / "script-review.json"
            output = root / "script_drafts"
            report_path.write_text(
                json.dumps(approved_report_data(), ensure_ascii=False), encoding="utf-8"
            )
            content_path.write_text(
                json.dumps(valid_script_content(), ensure_ascii=False), encoding="utf-8"
            )
            review_path.write_text(
                json.dumps(valid_script_review_content(), ensure_ascii=False), encoding="utf-8"
            )

            prepared = run_cli(
                "prepare-script",
                str(report_path),
                str(content_path),
                "--duration",
                "写成 8 分钟",
                "--output",
                str(output),
            )
            draft_files = list(output.rglob("script-draft-r0001.json"))
            reviewed_cli = run_cli(
                "review-script",
                str(report_path),
                str(draft_files[0]),
                str(review_path),
                "--output",
                str(output),
            )
            reviewed_files = list(output.rglob("script-draft-r0002.json"))
            compared = run_cli(
                "compare-script",
                str(report_path),
                str(draft_files[0]),
                str(reviewed_files[0]),
            )

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertIn("Teleprompter", prepared.stdout)
        self.assertEqual(reviewed_cli.returncode, 0, reviewed_cli.stderr)
        self.assertIn("稿件审查已完成", reviewed_cli.stdout)
        self.assertEqual(compared.returncode, 0, compared.stderr)
        self.assertIn('"from_revision": 1', compared.stdout)

    def test_prepare_script_rejects_unapproved_report_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "reviewed.json"
            content_path = root / "content.json"
            report_path.write_text(
                json.dumps(valid_report_data(), ensure_ascii=False), encoding="utf-8"
            )
            content_path.write_text(
                json.dumps(valid_script_content(), ensure_ascii=False), encoding="utf-8"
            )
            result = run_cli("prepare-script", str(report_path), str(content_path))

        self.assertEqual(result.returncode, 2)
        self.assertIn("用户确认", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_revise_script_cli_creates_new_revision_for_natural_duration_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "approved.json"
            first_content = root / "first.json"
            revised_content = root / "revised.json"
            output = root / "script_drafts"
            report_path.write_text(
                json.dumps(approved_report_data(), ensure_ascii=False), encoding="utf-8"
            )
            first_content.write_text(
                json.dumps(valid_script_content(), ensure_ascii=False), encoding="utf-8"
            )
            revised = valid_script_content()
            revised["beats"][0]["narration"] = "换一个更紧凑的开头。"
            revised_content.write_text(
                json.dumps(revised, ensure_ascii=False), encoding="utf-8"
            )
            prepared = run_cli(
                "prepare-script",
                str(report_path),
                str(first_content),
                "--output",
                str(output),
            )
            first_script = list(output.rglob("script-draft-r0001.json"))[0]
            result = run_cli(
                "revise-script",
                str(report_path),
                str(first_script),
                str(revised_content),
                "--duration",
                "压到 10 分钟",
                "--summary",
                "开头更紧凑并压到 10 分钟。",
                "--output",
                str(output),
            )
            files = list(output.rglob("script-draft-r0002.json"))
            data = json.loads(files[0].read_text(encoding="utf-8")) if files else {}

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["revision"], 2)
        self.assertEqual(data["target_duration_minutes"], 10)

    def test_write_script_without_api_key_gives_simple_guidance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "approved.json"
            report.write_text(
                json.dumps(approved_report_data(), ensure_ascii=False), encoding="utf-8"
            )
            result = run_cli("write-script", str(report), env={"OPENAI_API_KEY": ""})

        self.assertEqual(result.returncode, 2)
        self.assertIn("没有检测到 OPENAI_API_KEY", result.stderr)
        self.assertIn("确认", result.stderr)

    def test_approve_report_creates_a_persistent_ready_revision(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "reviewed.json"
            output = root / "reports"
            report_path.write_text(
                json.dumps(valid_report_data(), ensure_ascii=False), encoding="utf-8"
            )

            result = run_cli(
                "approve-report",
                str(report_path),
                "--confirmation",
                "确认进入写稿",
                "--output",
                str(output),
            )
            files = list(output.rglob("research-report-r0002.json"))
            approved = json.loads(files[0].read_text(encoding="utf-8")) if files else {}

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("用户确认已保存", result.stdout)
        self.assertEqual(len(files), 1)
        self.assertEqual(approved["status"], "ready_for_script")

    def test_prepare_discovery_and_select_topic_need_no_json_for_normal_user(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "discovery-input.json"
            manifest_path = Path(temp_dir) / "inspection-manifest.json"
            discovery_root = Path(temp_dir) / "discoveries"
            raw = valid_discovery_input()
            input_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "inspections": [
                            {
                                "url": seed["url"],
                                "tool_reference": f"open-{index}",
                                "inspected_at": "2026-08-10T11:00:00+00:00",
                            }
                            for index, candidate in enumerate(raw["candidates"], 1)
                            for seed in candidate["source_seeds"]
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            prepared = run_cli(
                "prepare-discovery",
                str(input_path),
                "--inspection-manifest",
                str(manifest_path),
                "--output",
                str(discovery_root),
            )
            selected = run_cli("select-topic", "1", "--output", str(discovery_root))

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertIn("候选选题已生成", prepared.stdout)
        self.assertIn("首选", prepared.stdout)
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertIn("已选择", selected.stdout)
        self.assertIn("research_question", selected.stdout)

    def test_discovery_without_api_key_gives_simple_codex_guidance(self):
        result = run_cli("discover", "今天讲什么？", env={"OPENAI_API_KEY": ""})

        self.assertEqual(result.returncode, 2)
        self.assertIn("没有检测到 OPENAI_API_KEY", result.stderr)
        self.assertIn("今天讲什么", result.stderr)

    def test_discover_does_not_accept_a_nonfunctional_count_option(self):
        result = run_cli("discover", "今天讲什么？", "--count", "3")

        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_selecting_without_latest_discovery_is_a_clean_cli_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_cli("select-topic", "1", "--output", temp_dir)

        self.assertEqual(result.returncode, 2)
        self.assertIn("无法生成报告", result.stderr)
        self.assertIn("没有可供选择", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

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
