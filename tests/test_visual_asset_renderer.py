import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.motion_spec import approve_advanced_motion_spec, build_motion_spec
from deeptalk_studio.visual_asset_renderer import (
    VisualAssetRenderError,
    _positioned_text,
    compile_primitives,
    layout_display_text,
    render_visual_asset,
)


def opportunity(decision):
    return {"opportunity_id": "VO1", "decision": decision, "source_time_range": {"start_seconds": "0", "end_seconds": "2"}, "alignment_digest": "a" * 64}


class VisualAssetRendererTests(unittest.TestCase):
    def test_chinese_layout_is_bounded_and_preserves_exact_text(self):
        text = "为什么票房还在上涨？"
        layout = layout_display_text(text, "body", max_width=480, max_lines=2)
        self.assertEqual(layout["text"], text)
        self.assertGreaterEqual(len(layout["lines"]), 1)
        self.assertLessEqual(len(layout["lines"]), 2)
        self.assertEqual("".join(layout["lines"]), text)

    def test_chinese_layout_rejects_unsafe_overflow_instead_of_rewriting(self):
        with self.assertRaises(VisualAssetRenderError):
            layout_display_text("这是一个不能为了塞进画面而被缩写或改写的超长中文事实标签", "body", max_width=180, max_lines=1)

    def test_causal_labels_remain_inside_horizontal_safe_area(self):
        spec = build_motion_spec(opportunity("MG_MOTION"), {"motion_type": "causal_chain", "visual_intent": "中文压力测试", "elements": [{"kind": "node", "text": text, "origin": "editorial"} for text in ("首周口碑", "社交讨论", "二次传播", "3.2 亿", "B站 / AI")]})
        entries = _positioned_text(compile_primitives(spec), spec)[1:]
        self.assertTrue(all(entry["x"] >= 96 and entry["x"] + entry["width"] <= 1824 for entry in entries))

    def test_path_uses_shared_primitives_and_renders_mp4(self):
        spec = build_motion_spec(opportunity("ADVANCED_MOTION"), {"motion_type": "svg_path_drawing", "visual_intent": "路线", "why_advanced_not_mg": "路径本身是含义", "elements": [{"kind": "node", "text": "起点", "origin": "editorial"}, {"kind": "node", "text": "终点", "origin": "editorial"}], "reveal_order": [1, 2]})
        spec = approve_advanced_motion_spec(spec, "可以")
        payload = compile_primitives(spec)
        self.assertEqual(payload["primitives"][0]["kind"], "path")
        with tempfile.TemporaryDirectory() as raw:
            output = render_visual_asset(spec, Path(raw), "路线.mp4")
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
            self.assertTrue(output.with_suffix(".text-reference.png").is_file())
            self.assertTrue(output.with_suffix(".text-evidence.json").is_file())
