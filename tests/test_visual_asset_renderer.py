import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.motion_spec import approve_advanced_motion_spec, build_motion_spec
from deeptalk_studio.visual_asset_renderer import compile_primitives, render_visual_asset


def opportunity(decision):
    return {"opportunity_id": "VO1", "decision": decision, "source_time_range": {"start_seconds": "0", "end_seconds": "2"}, "alignment_digest": "a" * 64}


class VisualAssetRendererTests(unittest.TestCase):
    def test_path_uses_shared_primitives_and_renders_mp4(self):
        spec = build_motion_spec(opportunity("ADVANCED_MOTION"), {"motion_type": "svg_path_drawing", "visual_intent": "路线", "why_advanced_not_mg": "路径本身是含义", "elements": [{"kind": "node", "text": "起点", "origin": "editorial"}, {"kind": "node", "text": "终点", "origin": "editorial"}], "reveal_order": [1, 2]})
        spec = approve_advanced_motion_spec(spec, "可以")
        payload = compile_primitives(spec)
        self.assertEqual(payload["primitives"][0]["kind"], "path")
        with tempfile.TemporaryDirectory() as raw:
            output = render_visual_asset(spec, Path(raw), "路线.mp4")
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
