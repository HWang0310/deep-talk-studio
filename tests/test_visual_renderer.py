import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_validation import MaterialValidationError, prepare_material_package
from deeptalk_studio.visual_renderer import VisualRenderError, render_visual_svg
from tests.material_fixtures import (
    inspection_manifest,
    reviewed_inputs,
    rights_manifest,
    valid_material_content,
)


class VisualRendererTests(unittest.TestCase):
    def setUp(self):
        self.report, self.script, _ = reviewed_inputs()
        self.profile = load_material_profile()

    def package(self, content):
        return prepare_material_package(
            content, self.script, self.report, self.profile,
            inspection_manifest=inspection_manifest(), rights_manifest=rights_manifest(),
            created_at="2026-08-11T10:00:00+08:00", package_id="MAT-visual",
        )

    def test_timeline_renders_actual_1920x1080_svg_with_attribution(self):
        spec = self.package(valid_material_content()).generated_visuals[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = render_visual_svg(spec, Path(temp_dir))
            svg = path.read_text(encoding="utf-8")
            self.assertIn('width="1920"', svg)
            self.assertIn('height="1080"', svg)
            self.assertIn("事件、解释与核查", svg)
            self.assertIn("已批准 Research Report", svg)
            self.assertIn('x="96" y="620" text-anchor="start" class="body"', svg)

    def test_svg_escapes_untrusted_display_text(self):
        content = valid_material_content()
        content["visual_specs"][0]["title"] = "事实 < 解释 & 猜测"
        spec = self.package(content).generated_visuals[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            svg = render_visual_svg(spec, Path(temp_dir)).read_text(encoding="utf-8")
            self.assertIn("事实 &lt; 解释 &amp; 猜测", svg)
            self.assertNotIn("<script", svg)

    def test_comparison_and_diagram_have_deterministic_renderers(self):
        for visual_type in ("comparison", "diagram"):
            content = valid_material_content()
            spec = content["visual_specs"][0]
            spec.update(visual_type=visual_type, events=[])
            if visual_type == "comparison":
                spec["evidence_link_ids"] = ["E1", "E3"]
                spec["comparison_items"] = [{
                    "label": "信息层级", "left_text": "已确认事件", "right_text": "原因仍待核查",
                    "claim_ids": ["C1", "C2"], "evidence_link_ids": ["E1", "E3"],
                }]
            else:
                spec["nodes"] = [
                    {"node_id": "N1", "label": "事实", "claim_ids": ["C1"]},
                    {"node_id": "N2", "label": "解释", "claim_ids": ["C2"]},
                ]
                spec["edges"] = [{"from_node": "N1", "to_node": "N2", "label": "需要核查"}]
            visual = self.package(content).generated_visuals[0]
            with tempfile.TemporaryDirectory() as temp_dir:
                svg = render_visual_svg(visual, Path(temp_dir)).read_text(encoding="utf-8")
                self.assertIn("<svg", svg)
                self.assertIn("Research Report", svg)

    def test_unsupported_numeric_data_is_rejected_before_render(self):
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="bar", events=[], data_points=[{
            "label": "虚构数值", "value": 999, "value_label": "999",
            "claim_ids": ["C1"], "evidence_link_ids": ["E1"],
        }])
        with self.assertRaisesRegex(MaterialValidationError, "unsupported_data"):
            self.package(content)

    def test_bar_rejects_wrong_evidence_numeric_substring_and_label_value_mismatch(self):
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="bar", events=[], data_points=[{
            "label": "日期不能当数值", "value": 16, "value_label": "16",
            "claim_ids": ["C1"], "evidence_link_ids": ["E1"],
        }])
        with self.assertRaisesRegex(MaterialValidationError, "unsupported_data"):
            self.package(content)
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="bar", events=[], data_points=[{
            "label": "明确日期", "value": 9, "value_label": "999 亿",
            "claim_ids": ["C1"], "evidence_link_ids": ["E1"],
        }])
        with self.assertRaisesRegex(MaterialValidationError, "value_label"):
            self.package(content)

    def test_comparison_child_refs_and_diagram_nodes_are_grounded(self):
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="comparison", events=[], comparison_items=[{
            "label": "错误", "left_text": "A", "right_text": "B",
            "claim_ids": ["C404"], "evidence_link_ids": ["E404"],
        }])
        with self.assertRaisesRegex(MaterialValidationError, "不存在"):
            self.package(content)
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="diagram", events=[], nodes=[
            {"node_id": "N1", "label": "事实", "claim_ids": ["C1"]},
        ], edges=[{"from_node": "N1", "to_node": "N404", "label": "错误"}])
        spec["claim_ids"] = ["C1"]
        spec["evidence_link_ids"] = ["E1"]
        with self.assertRaisesRegex(MaterialValidationError, "edge"):
            self.package(content)
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="diagram", events=[], nodes=[
            {"node_id": "N1", "label": "事实", "claim_ids": ["C1"]},
            {"node_id": "N1", "label": "重复", "claim_ids": ["C2"]},
        ], edges=[])
        with self.assertRaisesRegex(MaterialValidationError, "唯一"):
            self.package(content)
        content = valid_material_content()
        spec = content["visual_specs"][0]
        spec.update(visual_type="diagram", events=[], nodes=[
            {"node_id": "N1", "label": "无依据", "claim_ids": ["C404"]},
        ], edges=[{"from_node": "N1", "to_node": "N404", "label": "错误"}])
        spec["claim_ids"] = ["C404"]
        with self.assertRaisesRegex(MaterialValidationError, "不存在"):
            self.package(content)

    def test_renderer_never_overwrites_existing_visual(self):
        spec = self.package(valid_material_content()).generated_visuals[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            render_visual_svg(spec, Path(temp_dir))
            with self.assertRaisesRegex(VisualRenderError, "覆盖"):
                render_visual_svg(spec, Path(temp_dir))


if __name__ == "__main__":
    unittest.main()
