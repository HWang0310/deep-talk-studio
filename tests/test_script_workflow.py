import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.provenance import ProviderProvenance, SearchCall
from deeptalk_studio.providers.base import ProviderResult
from deeptalk_studio.script_profile import load_script_profile
from deeptalk_studio.script_workflow import (
    prepare_codex_script,
    run_codex_script_review,
    run_script_workflow,
)
from deeptalk_studio.script_validation import ScriptValidationError
from tests.fixtures import (
    approved_report_data,
    valid_report_data,
    valid_script_content,
    valid_script_review_content,
)


class FakeScriptProvider:
    def __init__(self, review_content=None):
        self.calls = []
        self.review_content = review_content or valid_script_review_content()

    def write_script(self, report, profile, target_duration_minutes, schema):
        self.calls.append(("write", report["report_id"], target_duration_minutes))
        return ProviderResult(
            data=valid_script_content(),
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )

    def review_script(self, report, script, schema):
        self.calls.append(("review", script["script_id"], script["revision"]))
        return ProviderResult(
            data=self.review_content,
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )


class SearchProvenanceProvider(FakeScriptProvider):
    def __init__(self, search_step):
        super().__init__()
        self.search_step = search_step

    @staticmethod
    def search_provenance():
        return ProviderProvenance(
            search_calls=(SearchCall("call-1", "search", ("forbidden",), ()),),
            citations=(),
        )

    def write_script(self, report, profile, target_duration_minutes, schema):
        result = super().write_script(report, profile, target_duration_minutes, schema)
        if self.search_step == "writer":
            return ProviderResult(result.data, self.search_provenance())
        return result

    def review_script(self, report, script, schema):
        result = super().review_script(report, script, schema)
        if self.search_step == "reviewer":
            return ProviderResult(result.data, self.search_provenance())
        return result


class ScriptWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile()

    def test_api_workflow_writes_reviews_and_saves_immutable_revisions(self):
        provider = FakeScriptProvider()
        moments = iter(
            [
                datetime(2026, 8, 10, 13, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_script_workflow(
                self.report,
                provider,
                Path(temp_dir),
                self.profile,
                target_duration_minutes=12,
                clock=lambda: next(moments),
                id_factory=lambda prefix: f"{prefix}-test",
            )
            draft = json.loads(result.draft.json.read_text(encoding="utf-8"))
            reviewed = json.loads(result.reviewed.json.read_text(encoding="utf-8"))
            review = json.loads(result.review_artifact.read_text(encoding="utf-8"))
            teleprompter = result.reviewed.teleprompter.read_text(encoding="utf-8")

        self.assertEqual(provider.calls, [("write", self.report.report_id, 12), ("review", "SCR-test", 1)])
        self.assertEqual(draft["revision"], 1)
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(reviewed["revision"], 2)
        self.assertEqual(reviewed["status"], "reviewed")
        self.assertEqual(review["gate_status"], "pass")
        self.assertIn(valid_script_content()["closing"], teleprompter)

    def test_codex_prepare_and_review_use_same_approved_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prepared = prepare_codex_script(
                valid_script_content(),
                self.report,
                root,
                self.profile,
                target_duration_minutes=8,
                created_at="2026-08-10T13:00:00+00:00",
                script_id="SCR-codex",
            )
            reviewed = run_codex_script_review(
                valid_script_review_content(),
                self.report,
                prepared.script,
                root,
                self.profile,
                created_at="2026-08-10T14:00:00+00:00",
                review_id="SRV-codex",
            )

        self.assertEqual(prepared.script.report_revision, self.report.revision)
        self.assertEqual(prepared.script.target_duration_minutes, 8)
        self.assertEqual(reviewed.script.status, "reviewed")

    def test_blocked_research_is_refused_before_writer_call(self):
        provider = FakeScriptProvider()
        with self.assertRaisesRegex(ScriptValidationError, "用户确认|ready_for_script"):
            run_script_workflow(
                ResearchReport.from_dict(valid_report_data()),
                provider,
                Path("script_drafts"),
                self.profile,
            )
        self.assertEqual(provider.calls, [])

    def test_writer_search_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ScriptValidationError, "Writer.*网络搜索"):
                run_script_workflow(
                    self.report,
                    SearchProvenanceProvider("writer"),
                    Path(temp_dir),
                    self.profile,
                )

    def test_reviewer_search_provenance_is_rejected(self):
        moments = iter(
            [
                datetime(2026, 8, 10, 13, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ScriptValidationError, "Reviewer.*网络搜索"):
                run_script_workflow(
                    self.report,
                    SearchProvenanceProvider("reviewer"),
                    Path(temp_dir),
                    self.profile,
                    clock=lambda: next(moments),
                    id_factory=lambda prefix: f"{prefix}-search",
                )


if __name__ == "__main__":
    unittest.main()
