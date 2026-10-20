"""Synthetic-only regression for Issue #21; no creator episode inputs."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import json

from deeptalk_studio.models import ResearchReport, ScriptDraft
from deeptalk_studio.script_profile import load_script_profile, ScriptValidationError, parse_target_duration
from deeptalk_studio.script_prompt import build_script_writer_prompt
from deeptalk_studio.script_renderer import render_editor_markdown
from deeptalk_studio.script_revisions import create_script_revision
from deeptalk_studio.script_review import prepare_script_review
from deeptalk_studio.script_storage import save_script, load_script, save_script_review_artifact, ScriptStorageError
from deeptalk_studio.script_validation import prepare_script_draft, validate_script_draft, script_content_digest
from deeptalk_studio.script_workflow import prepare_codex_script, run_script_workflow
from deeptalk_studio.content_director import prepare_content_thesis_card
from deeptalk_studio.content_director_profile import load_content_director_profile
from deeptalk_studio.providers.base import ProviderResult
from deeptalk_studio.provenance import ProviderProvenance
from deeptalk_studio.schema import SCRIPT_REVIEW_CHECK_NAMES_LEGACY, SCRIPT_QUALITY_GATE_CHECK_NAMES_V1
from tests.fixtures import approved_report_data
from tests.test_script_agent_v1 import _approved_thesis, _v1_content
from tests.test_content_director import valid_thesis_content


class ScriptDurationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.report = ResearchReport.from_dict(approved_report_data())
        self.profile = load_script_profile(Path('config/script-profile-v1.json'))
        self.thesis = _approved_thesis(self.report)

    def content(self, count):
        content = _v1_content()
        # A counting fixture, not a model of editorial quality.
        content['beats'][0]['narration'] = '文' * count
        content['closing'] = '完'
        return content

    def draft(self, count=2599, **kwargs):
        return prepare_script_draft(self.content(count), self.report, self.profile,
            created_at='2026-10-20T10:00:00+08:00', script_id='duration-test',
            content_thesis_card=self.thesis, **kwargs)

    def review_content(self):
        return dict(issues=[], checks=[dict(check_name=n, outcome='pass', reason='synthetic gate fixture')
            for n in SCRIPT_REVIEW_CHECK_NAMES_LEGACY + SCRIPT_QUALITY_GATE_CHECK_NAMES_V1], overall_notes='Synthetic only')

    def test_no_preference_allows_natural_short_and_long_content(self):
        for count, expected in [(259, 1.0), (2599, 10.0), (10399, 40.0)]:
            with self.subTest(count=count):
                draft = self.draft(count)
                self.assertEqual(draft.duration_mode, 'content_driven')
                self.assertEqual(draft.character_count, count + 1)
                self.assertEqual(draft.estimated_duration_minutes, expected)
                self.assertEqual(draft.target_duration_minutes, expected)
                self.assertEqual(draft.content_thesis_card_id, self.thesis.card_id)
                validate_script_draft(draft, self.report, self.profile)

    def test_preference_is_advisory_even_when_actual_duration_differs(self):
        draft = self.draft(259, target_duration_minutes=10)
        self.assertEqual(draft.duration_mode, 'preference')
        self.assertEqual(draft.target_duration_minutes, 10)
        self.assertEqual(draft.estimated_duration_minutes, 1)
        editor = render_editor_markdown(draft, self.report, self.profile)
        self.assertIn('软偏好', editor)
        self.assertIn('-9', editor)

    def test_codex_workflow_has_no_implicit_target(self):
        with tempfile.TemporaryDirectory() as directory:
            result = prepare_codex_script(self.content(2599), self.report, Path(directory), self.profile,
                content_thesis_card=self.thesis)
            self.assertEqual(result.script.duration_mode, 'content_driven')
            self.assertEqual(result.script.estimated_duration_minutes, 10)

    def test_writer_prompt_explains_content_driven_and_soft_preference(self):
        prompt = build_script_writer_prompt(self.report.to_dict(), self.profile, None)
        self.assertIn('内容决定时长', prompt)
        preference = build_script_writer_prompt(self.report.to_dict(), self.profile, 10)
        self.assertIn('软偏好', preference)
        self.assertIn('10', preference)

    def test_current_profile_keeps_legacy_profile_readable(self):
        legacy = deepcopy(self.profile)
        legacy.pop('duration_policy', None)
        legacy['duration_range_minutes'] = [5, 6]
        legacy['default_duration_minutes'] = 5.5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'legacy-profile.json'
            path.write_text(json.dumps(legacy), encoding='utf-8')
            legacy = load_script_profile(path)
        draft = prepare_script_draft(_v1_content(), self.report, legacy,
            created_at='2026-10-20T10:00:00+08:00', script_id='legacy-duration',
            target_duration_minutes=5.5, content_thesis_card=self.thesis)
        self.assertNotIn('duration_mode', draft.to_dict())
        # Golden digest produced by the unchanged origin/main implementation.
        self.assertEqual(script_content_digest(draft.to_dict()),
            'ec5e7e5f61635cde7cde2791e05d734fe8d166f4dda7c00dcbfa97d697e6a69f')
        validate_script_draft(draft, self.report, self.profile)
        reviewed = prepare_script_review(self.review_content(), self.report, draft, self.profile,
            created_at='2026-10-20T10:01:00+08:00', review_id='legacy-review')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_script(draft, self.report, self.profile, root)
            save_script_review_artifact(reviewed.artifact, draft, root)
            paths = save_script(reviewed.script, self.report, self.profile, root, reviewed.artifact)
            loaded = load_script(paths.json, self.report, self.profile, content_thesis_card=self.thesis)
            self.assertEqual(loaded.to_dict(), reviewed.script.to_dict())
            with self.assertRaises(ScriptStorageError):
                save_script(reviewed.script, self.report, self.profile, root, reviewed.artifact)

    def test_v1_revision_preserves_thesis_and_content_driven_mode(self):
        old = self.draft(2599)
        revised = create_script_revision(self.content(5199), old, self.report, self.profile,
            generated_at='2026-10-20T10:01:00+08:00')
        self.assertEqual(revised.content_thesis_card_id, self.thesis.card_id)
        self.assertEqual(revised.duration_mode, 'content_driven')
        self.assertEqual(revised.target_duration_minutes, 20)
        self.assertEqual(revised.review_state['state'], 'not_reviewed')

    def test_invalid_preferences_and_resource_budget_fail_closed(self):
        for value in [True, False, 0, -1, float('nan'), float('inf'), '10']:
            with self.subTest(value=value), self.assertRaises(ScriptValidationError):
                self.draft(target_duration_minutes=value)
        with self.assertRaisesRegex(ScriptValidationError, '字符.*预算'):
            self.draft(100001)

    def test_preference_is_not_replaced_by_another_minute_envelope(self):
        for preference in (1, 90):
            draft = self.draft(2599, target_duration_minutes=preference)
            self.assertEqual(draft.target_duration_minutes, preference)
            self.assertEqual(draft.estimated_duration_minutes, 10)

    def test_content_driven_parser_keeps_absence_and_accepts_long_soft_preference(self):
        self.assertIsNone(parse_target_duration('', default=None))
        self.assertEqual(parse_target_duration('约 90 分钟', default=None), 90)
        self.assertIsNone(parse_target_duration('做长一点', default=None))
        self.assertIsNone(parse_target_duration('更紧凑一点', default=None))

    def test_content_driven_parser_rejects_negative_and_zero_range_endpoints(self):
        for text in ('约 -1 分钟', '0到10分钟', '-1到10分钟'):
            with self.subTest(text=text), self.assertRaises(ScriptValidationError):
                parse_target_duration(text, default=None)
        self.assertEqual(parse_target_duration('5 - 6 分钟', default=None), 5.5)

    def test_api_path_keeps_no_preference_and_reviews_exact_draft(self):
        owner = self
        class Provider:
            def __init__(self):
                self.calls = []
            def write_script(self, report, profile, target_duration_minutes, schema):
                self.calls.append(('writer', target_duration_minutes))
                return ProviderResult(owner.content(2599), ProviderProvenance((), ()))
            def review_script(self, report, script, schema):
                self.calls.append(('reviewer', script['revision']))
                return ProviderResult(owner.review_content(), ProviderProvenance((), ()))
        provider = Provider()
        with tempfile.TemporaryDirectory() as directory:
            result = run_script_workflow(self.report, provider, Path(directory), self.profile,
                content_thesis_card=self.thesis)
            loaded = load_script(result.reviewed.json, self.report, self.profile,
                content_thesis_card=self.thesis)
            self.assertEqual(loaded.status, 'reviewed')
            self.assertEqual(loaded.estimated_duration_minutes, 10)
            with self.assertRaises(ScriptValidationError):
                load_script(result.reviewed.json, self.report, self.profile)
        self.assertEqual(provider.calls, [('writer', None), ('reviewer', 1)])

    def test_unapproved_thesis_is_rejected_before_api_writer(self):
        draft_card = prepare_content_thesis_card(valid_thesis_content(), self.report,
            load_content_director_profile(), created_at='2026-10-20T10:00:00+08:00', card_id='unapproved')
        class Provider:
            called = False
            def write_script(self, *args):
                self.called = True
                raise AssertionError('Writer must not run')
        provider = Provider()
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ScriptValidationError):
            run_script_workflow(self.report, provider, Path(directory), self.profile,
                content_thesis_card=draft_card)
        self.assertFalse(provider.called)

    def test_every_quality_failure_still_blocks_long_v1_script(self):
        draft = self.draft(2599)
        for name in SCRIPT_QUALITY_GATE_CHECK_NAMES_V1:
            review = self.review_content()
            for check in review['checks']:
                if check['check_name'] == name:
                    check['outcome'] = 'fail'
            review['issues'] = [dict(issue_type='quality_gate_failure', beat_ids=['B001'],
                claim_ids=[], explanation='Synthetic quality failure', suggested_fix='Revise')]
            result = prepare_script_review(review, self.report, draft, self.profile,
                created_at='2026-10-20T10:01:00+08:00', review_id='failed-quality')
            with self.subTest(name=name):
                self.assertEqual(result.artifact['gate_status'], 'fail')
                self.assertEqual(result.script.status, 'draft')

    def test_derived_duration_and_review_metadata_cannot_be_tampered(self):
        draft = self.draft(2599)
        for key, value in [('character_count', 1), ('estimated_duration_minutes', 5.5),
                           ('target_duration_minutes', 5.5)]:
            data = draft.to_dict()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ScriptValidationError):
                validate_script_draft(data, self.report, self.profile, content_thesis_card=self.thesis)
        reviewed = prepare_script_review(self.review_content(), self.report, draft, self.profile,
            created_at='2026-10-20T10:01:00+08:00', review_id='duration-review')
        data = reviewed.script.to_dict()
        data['duration_mode'] = 'preference'
        with self.assertRaises(ScriptValidationError):
            ScriptDraft.from_dict(data, self.report, self.profile, reviewed.artifact, self.thesis)

    def test_new_duration_does_not_bypass_thesis_research_or_quality_gates(self):
        with self.assertRaisesRegex(ScriptValidationError, 'Thesis'):
            prepare_script_draft(self.content(2599), self.report, self.profile,
                created_at='2026-10-20T10:00:00+08:00', script_id='missing-thesis')
        draft = self.draft(2599)
        review = self.review_content()
        review['checks'] = review['checks'][:-1]
        with self.assertRaises(ScriptValidationError):
            prepare_script_review(review, self.report, draft, self.profile,
                created_at='2026-10-20T10:01:00+08:00', review_id='missing-gate')
