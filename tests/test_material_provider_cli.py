import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.cli import build_parser
from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES
from deeptalk_studio.material_workflow import run_material_workflow
from deeptalk_studio.provenance import ProviderProvenance, SearchCall
from deeptalk_studio.providers.base import ProviderResult
from deeptalk_studio.providers.openai import OpenAIResponsesProvider
from tests.material_fixtures import reviewed_inputs, valid_material_content


def review_content():
    return {
        "issues": [],
        "checks": [{"check_name": name, "outcome": "pass", "reason": "独立复核完成。"}
                   for name in MATERIAL_REVIEW_CHECK_NAMES],
        "overall_notes": "通过。",
    }


class FakeMaterialProvider:
    def __init__(self):
        self.calls = []

    def search_materials(self, script, report, profile, schema):
        self.calls.append("search")
        return ProviderResult(
            valid_material_content(),
            ProviderProvenance((SearchCall("ws-material", "search", ("素材",),
                                                  ("https://example.com/official.pdf",)),), ()),
        )

    def review_materials(self, package, script, report, schema):
        self.calls.append("review")
        return ProviderResult(review_content(), ProviderProvenance((), ()))


class MaterialProviderCliTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.profile = load_material_profile()

    def test_api_workflow_preserves_search_provenance_but_does_not_call_search_in_review(self):
        provider = FakeMaterialProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_material_workflow(
                self.script, self.report, provider, root / "packages", root / "assets",
                self.profile, clock=lambda: "2026-08-11T12:00:00+08:00",
                id_factory=lambda prefix: f"{prefix}-api",
            )
            data = json.loads(result.reviewed.json.read_text(encoding="utf-8"))
        self.assertEqual(provider.calls, ["search", "review"])
        self.assertEqual(data["provider_provenance"]["search_call_ids"], ["ws-material"])
        self.assertEqual(data["materials"][0]["provenance_status"], "discovered")
        self.assertEqual(data["materials"][0]["eligibility_status"], "reference_only")

    def test_openai_material_search_uses_web_search_and_review_has_no_search_tool(self):
        bodies = []

        def transport(url, headers, body, timeout):
            bodies.append(body)
            output = valid_material_content() if len(bodies) == 1 else review_content()
            records = []
            if len(bodies) == 1:
                records.append({
                    "type": "web_search_call", "id": "ws-material", "status": "completed",
                    "action": {"type": "search", "queries": ["素材"],
                               "sources": [{"type": "url", "url": "https://example.com/official.pdf"}]},
                })
            records.append({"type": "message", "id": "msg", "content": [{
                "type": "output_text", "text": json.dumps(output, ensure_ascii=False), "annotations": [],
            }]})
            return {"output": records}

        provider = OpenAIResponsesProvider(api_key="secret", transport=transport)
        provider.search_materials(self.script.to_dict(), self.report.to_dict(), self.profile, {})
        provider.review_materials({}, self.script.to_dict(), self.report.to_dict(), {})
        self.assertEqual(bodies[0]["tools"], [{"type": "web_search"}])
        self.assertNotIn("tools", bodies[1])
        self.assertNotIn("web_search", json.dumps(bodies[1]))

    def test_cli_exposes_prepare_review_and_api_material_commands(self):
        parser = build_parser()
        for command in ("prepare-materials", "review-materials", "materials"):
            with self.subTest(command=command):
                with self.assertRaises(SystemExit) as caught:
                    parser.parse_args([command, "--help"])
                self.assertEqual(caught.exception.code, 0)

    def test_prepare_materials_skill_exists_and_keeps_search_review_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / ".agents/skills/prepare-materials/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("给这期配素材", skill)
        self.assertIn("实际打开", skill)
        self.assertIn("独立 Material Review", skill)
        self.assertIn("不能扩展 Research", skill)


if __name__ == "__main__":
    unittest.main()

