import unittest

from deeptalk_studio.motion_spec import MotionSpecError, approve_advanced_motion_spec, build_motion_spec, assert_renderable


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
