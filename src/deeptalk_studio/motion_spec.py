"""Small, binding-first MG and Advanced Motion contracts."""
import hashlib
import json
from decimal import Decimal


class MotionSpecError(ValueError):
    pass


MOTION_TYPES = {"timeline", "causal_chain", "comparison_mechanism", "svg_path_drawing", "controlled_conceptual_metaphor"}
ADVANCED = {"svg_path_drawing", "controlled_conceptual_metaphor"}
CAPACITY = {"timeline": 6, "causal_chain": 5, "comparison_mechanism": 3, "svg_path_drawing": 6, "controlled_conceptual_metaphor": 5}


def _digest(value):
    data = dict(value); data.pop("spec_digest", None)
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate_elements(elements):
    if not elements:
        raise MotionSpecError("Motion Spec 必须有元素")
    for element in elements:
        if not str(element.get("text", "")).strip():
            continue
        if element.get("origin") != "editorial" and not element.get("binding"):
            raise MotionSpecError("事实、数字、人名、机构和日期显示文字必须有 binding")


def _relative_timing(semantic_beats, source_time_range):
    start = Decimal(str(source_time_range.get("start_seconds", "")))
    end = Decimal(str(source_time_range.get("end_seconds", "")))
    if end <= start:
        raise MotionSpecError("真实 A-roll 时间窗口无效")
    relative = []
    for beat in semantic_beats:
        absolute = Decimal(str(beat.get("absolute_seconds", "")))
        if absolute < start or absolute > end:
            raise MotionSpecError("MG semantic beat 超出真实语义窗口")
        relative.append({"label": str(beat.get("label", "")), "absolute_seconds": str(absolute), "relative_seconds": str(absolute - start), "relative_progress": str((absolute - start) / (end - start))})
    return relative


def build_motion_spec(opportunity, content, *, spec_id="MS-1"):
    motion_type = content.get("motion_type")
    if opportunity.get("decision") not in {"MG_MOTION", "ADVANCED_MOTION"} or motion_type not in MOTION_TYPES:
        raise MotionSpecError("Motion Spec decision 或类型无效")
    if motion_type in ADVANCED and opportunity["decision"] != "ADVANCED_MOTION":
        raise MotionSpecError("Advanced Motion 必须来自 ADVANCED_MOTION 决策")
    if motion_type not in ADVANCED and opportunity["decision"] != "MG_MOTION":
        raise MotionSpecError("MG 必须来自 MG_MOTION 决策")
    elements = list(content.get("elements", [])); _validate_elements(elements)
    if len(elements) > CAPACITY[motion_type]:
        raise MotionSpecError("信息密度超过 grammar 容量，必须降级而非压缩事实")
    if motion_type in ADVANCED and not content.get("why_advanced_not_mg"):
        raise MotionSpecError("Advanced Motion 必须说明为什么不能简单使用 MG")
    semantic_beats = list(content.get("semantic_beats", []))
    data = {"artifact_version": "motion-spec/1", "spec_id": spec_id, "opportunity_id": opportunity["opportunity_id"], "alignment_digest": opportunity["alignment_digest"], "source_time_range": dict(opportunity["source_time_range"]), "motion_type": motion_type, "visual_intent": content["visual_intent"], "elements": elements, "semantic_beats": semantic_beats, "relative_timing": _relative_timing(semantic_beats, opportunity["source_time_range"]), "reveal_order": list(content.get("reveal_order", range(1, len(elements) + 1))), "protected_regions": list(content.get("protected_regions", [])), "allowed_masks": list(content.get("allowed_masks", [])), "review_status": "pending" if motion_type in ADVANCED else "not_required", "why_advanced_not_mg": content.get("why_advanced_not_mg", ""), "fallback": "MG_MOTION → REAL_MATERIAL → KEEP_A_ROLL"}
    data["spec_digest"] = _digest(data); return data


def recompute_motion_timing(spec, source_time_range):
    """Recalculate primitive timing for a changed real semantic span.

    Absolute semantic beat clocks remain bound to A-roll. A caller cannot use
    this as a generic stretch operation because beats outside the new window
    fail closed.
    """
    result = dict(spec)
    result["source_time_range"] = dict(source_time_range)
    result["relative_timing"] = _relative_timing(result.get("semantic_beats", []), result["source_time_range"])
    result["spec_digest"] = _digest(result)
    return result


def approve_advanced_motion_spec(spec, confirmation):
    if spec.get("motion_type") not in ADVANCED or not str(confirmation).strip():
        raise MotionSpecError("Advanced Motion Review 无效")
    result = dict(spec); result["review_status"] = "approved"; result["review_confirmation"] = str(confirmation); result["spec_digest"] = _digest(result); return result


def assert_renderable(spec):
    if spec.get("motion_type") in ADVANCED and spec.get("review_status") != "approved":
        raise MotionSpecError("Advanced Motion 未通过人工 Review，不得 Render")
    return True
