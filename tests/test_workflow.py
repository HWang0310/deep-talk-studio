import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from deeptalk_studio.provenance import ProviderProvenance, SearchCall, UrlCitation
from deeptalk_studio.providers.base import ProviderResult
from deeptalk_studio.validation import ReportValidationError
from deeptalk_studio.workflow import _prepare_draft, prepare_codex_draft, run_research
from tests.fixtures import (
    valid_api_research_draft_input,
    valid_codex_draft_input,
    valid_fact_check_data,
    valid_report_data,
)


class FakeProvider:
    def __init__(self, fact_check_provenance=True):
        self.calls = []
        self.fact_check_provenance = fact_check_provenance
        self.research_schema = None

    def research(self, topic, schema):
        self.calls.append(("research", topic))
        self.research_schema = schema
        data = valid_api_research_draft_input()
        data["topic"] = topic
        provenance = ProviderProvenance(
            search_calls=(
                SearchCall(
                    call_id="ws_research",
                    action_type="search",
                    queries=(topic,),
                    source_urls=(
                        "https://example.com/official",
                        "https://example.org/report",
                    ),
                ),
            ),
            citations=(),
        )
        return ProviderResult(data=data, provenance=provenance)

    def fact_check(self, report, schema):
        self.calls.append(("fact_check", report["report_id"]))
        artifact = valid_fact_check_data(report)
        provenance = ProviderProvenance(
            search_calls=(
                SearchCall(
                    call_id="ws_fact",
                    action_type="search",
                    queries=("反证检查",),
                    source_urls=("https://example.com/official",),
                ),
            )
            if self.fact_check_provenance
            else (),
            citations=(
                UrlCitation(
                    url="https://example.org/report",
                    title="媒体核查报道",
                    output_item_id="msg_fact",
                    start_index=1,
                    end_index=5,
                ),
            )
            if self.fact_check_provenance
            else (),
        )
        return ProviderResult(data=artifact, provenance=provenance)


class WorkflowTests(unittest.TestCase):
    def test_codex_draft_input_gets_deterministic_machine_metadata(self):
        report = prepare_codex_draft(
            valid_codex_draft_input(),
            created_at="2026-08-10T10:00:00+08:00",
            report_id="RPT-codex-test",
        )

        self.assertEqual(report.report_id, "RPT-codex-test")
        self.assertEqual(report.revision, 1)
        self.assertEqual(report.research_mode, "codex_skill")
        self.assertEqual(report.status, "fact_check_pending")
        self.assertEqual(report.fact_check["status"], "not_run")
        self.assertEqual(report.quality_summary["gate_status"], "fail")
        self.assertEqual(report.sources[0]["normalized_url"], "https://example.com/official")
        self.assertEqual(report.evidence_links[0]["independence_group"], "IG1")
        self.assertFalse(report.evidence_links[0]["verified_in_review"])

    def test_topic_runs_research_then_independent_fact_check_and_saves_history(self):
        provider = FakeProvider()
        moments = iter(
            [
                datetime(2026, 8, 10, 2, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 10, 3, 0, tzinfo=timezone.utc),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_research(
                "人工智能就业影响",
                provider,
                Path(temp_dir),
                clock=lambda: next(moments),
                id_factory=lambda prefix: f"{prefix}-test",
            )
            draft = json.loads(result.draft.json.read_text(encoding="utf-8"))
            reviewed = json.loads(result.reviewed.json.read_text(encoding="utf-8"))
            fact_check = json.loads(result.fact_check.read_text(encoding="utf-8"))

        self.assertEqual([call[0] for call in provider.calls], ["research", "fact_check"])
        self.assertNotIn("quality_summary", provider.research_schema["properties"])
        self.assertEqual(draft["report_id"], "RPT-test")
        self.assertEqual(draft["revision"], 1)
        self.assertEqual(draft["status"], "fact_check_pending")
        self.assertEqual(reviewed["report_id"], draft["report_id"])
        self.assertEqual(reviewed["revision"], 2)
        self.assertEqual(reviewed["previous_revision"], 1)
        self.assertEqual(reviewed["status"], "reviewed")
        self.assertEqual(reviewed["quality_summary"]["gate_status"], "pass")
        self.assertEqual(fact_check["review_id"], "FCR-test")
        self.assertEqual(fact_check["tool_provenance"]["search_call_ids"], ["ws_fact"])
        self.assertTrue(result.draft.markdown.name.endswith("r0001.md"))
        self.assertTrue(result.reviewed.markdown.name.endswith("r0002.md"))

    def test_api_content_cannot_smuggle_machine_owned_quality_or_approval(self):
        data = valid_api_research_draft_input()
        data["quality_summary"] = {"gate_status": "pass"}
        data["approval_gate"] = {
            "status": "approved",
            "ready_for_script": True,
        }
        result = ProviderResult(
            data=data,
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )

        with self.assertRaisesRegex(ReportValidationError, "未知字段"):
            _prepare_draft(
                "示例公共事件",
                result,
                "2026-08-10T10:00:00+08:00",
                "RPT-api-owned",
            )

    def test_fact_check_without_separate_tool_provenance_is_rejected(self):
        provider = FakeProvider(fact_check_provenance=False)
        moments = iter(
            [
                datetime(2026, 8, 10, 2, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 10, 3, 0, tzinfo=timezone.utc),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ReportValidationError, "tool provenance"):
                run_research(
                    "人工智能就业影响",
                    provider,
                    Path(temp_dir),
                    clock=lambda: next(moments),
                    id_factory=lambda prefix: f"{prefix}-test",
                )

    def test_empty_topic_is_rejected_before_provider_call(self):
        provider = FakeProvider()

        with self.assertRaisesRegex(ValueError, "主题不能为空"):
            run_research("   ", provider, Path("reports"))

        self.assertEqual(provider.calls, [])


if __name__ == "__main__":
    unittest.main()
