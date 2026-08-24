import unittest

from deeptalk_studio.motion_spec import MotionSpecError, approve_advanced_motion_spec, build_motion_spec, assert_renderable, recompute_motion_timing


def opportunity(decision="MG_MOTION"):
    return {"opportunity_id": "VO001", "decision": decision, "source_time_range": {"start_seconds": "12", "end_seconds": "20"}, "alignment_digest": "a" * 64}


class MotionSpecTests(unittest.TestCase):
    def test_advanced_requires_review_before_render(self):
        spec = build_motion_spec(opportunity("ADVANCED_MOTION"), {"motion_type": "controlled_conceptual_metaphor", "visual_intent": "票变资格", "why_advanced_not_mg": "需要物理转换", "elements": [{"kind": "shape", "text": "电影票", "origin": "editorial"}]})
        with self.assertRaises(MotionSpecError):
            assert_renderable(spec)
        assert_renderable(approve_advanced_motion_spec(spec, "可以"))

    def test_rejects_unbound_fact_text(self):
        with self.assertRaises(MotionSpecError):
            build_motion_spec(opportunity(), {"motion_type": "timeline", "visual_intent": "时间线", "elements": [{"kind": "text", "text": "2026年机构报告", "origin": "factual"}]})

    def test_real_semantic_beats_must_stay_inside_actual_span(self):
        content = {"motion_type": "timeline", "visual_intent": "解释", "elements": [{"text": "节点", "origin": "editorial"}], "semantic_beats": [{"absolute_seconds": "9.9", "label": "先出现"}]}
        with self.assertRaisesRegex(MotionSpecError, "真实语义窗口"):
            build_motion_spec(opportunity(), content)

    def test_real_duration_change_recomputes_relative_timing(self):
        content = {"motion_type": "timeline", "visual_intent": "解释", "elements": [{"text": "第一步", "origin": "editorial"}, {"text": "第二步", "origin": "editorial"}], "semantic_beats": [{"absolute_seconds": "14", "label": "第一步"}, {"absolute_seconds": "18", "label": "第二步"}]}
        short = build_motion_spec(opportunity(), content)
        long = recompute_motion_timing(short, {"start_seconds": "12", "end_seconds": "24"})
        self.assertNotEqual(short["relative_timing"], long["relative_timing"])
        self.assertEqual(long["semantic_beats"][0]["absolute_seconds"], "14")
