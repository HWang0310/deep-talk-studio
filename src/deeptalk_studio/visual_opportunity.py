"""Build clock-bound V2 Visual Opportunities from safe semantic spans only."""

from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .visual_opportunity_directive import (
    VisualOpportunityDirectiveError,
    directive_digest,
    normalize_visual_opportunity_directives,
)


class VisualOpportunityError(ValueError):
    pass


_NO_OPPORTUNITY_REASONS = frozenset({
    "unsafe_alignment", "fact_conflict", "no_useful_visual_purpose", "creator_base_layer",
})


def build_visual_opportunity_plan(
    semantic_timeline: Mapping[str, Any],
    directives: Mapping[str, Any],
    *,
    defaults: Mapping[str, Any],
) -> dict:
    """Create one auditable opportunity decision per semantic span.

    Directives are deliberately clock-free.  The only clock projection is the
    canonical ``actual_*_seconds`` pair already carried by the timeline.
    """
    timeline = _validate_timeline(semantic_timeline)
    try:
        directive_artifact = normalize_visual_opportunity_directives(directives)
    except VisualOpportunityDirectiveError as exc:
        raise VisualOpportunityError(str(exc)) from exc
    if directive_artifact["semantic_timeline_digest"] != timeline["timeline_digest"]:
        raise VisualOpportunityError("semantic_timeline_digest 与 Semantic Timeline 不匹配")
    core_defaults = _validate_defaults(defaults)
    directives_by_span = {item["span_id"]: item for item in directive_artifact["directives"]}
    input_identity = {
        "semantic_timeline_digest": timeline["timeline_digest"],
        "alignment_digest": timeline["alignment_digest"],
        "transcript_digest": timeline["transcript_digest"],
        "directives_id": directive_artifact["directives_id"],
        "revision": directive_artifact["revision"],
        "directives_digest": directive_digest(directive_artifact),
        "reviewed_script_digest": directive_artifact["reviewed_script_digest"],
        "defaults": core_defaults,
    }
    plan_id = "VOP-" + _digest(input_identity)[:24]
    opportunities = []
    span_audit = []
    used_ids = set()
    for ordinal, span in enumerate(timeline["spans"], 1):
        span_id = span["span_id"]
        directive = directives_by_span.get(span_id)
        if span["visual_eligibility"] != "safe":
            reason = "fact_conflict" if span["reason"] == "FACT_CONFLICT" else "unsafe_alignment"
            span_audit.append({"span_id": span_id, "status": "NO_OPPORTUNITY", "reason": reason})
            continue
        if directive is None:
            span_audit.append({"span_id": span_id, "status": "NO_OPPORTUNITY", "reason": "creator_base_layer"})
            continue
        start_ms, end_ms = _window_from_span(span)
        opportunity_id = "VO-" + _digest({
            "plan_id": plan_id, "semantic_timeline_digest": timeline["timeline_digest"],
            "span_id": span_id, "ordinal": ordinal,
        })[:24]
        if opportunity_id in used_ids:
            raise VisualOpportunityError("opportunity_id collision")
        used_ids.add(opportunity_id)
        opportunity = {
            "opportunity_id": opportunity_id,
            "spoken_semantics": span["summary"],
            "visual_purpose": directive["visual_purpose"],
            "a_roll_window": {"start_ms": start_ms, "end_ms": end_ms},
            "target_duration_ms": core_defaults["target_duration_ms"],
            "language": core_defaults["language"],
            "canvas": copy.deepcopy(core_defaults["canvas"]),
            "factual_context": copy.deepcopy(directive["factual_context_refs"]),
        }
        semantic_context = _bounded_context(timeline["spans"], ordinal - 1, directive["semantic_context_selector"])
        if semantic_context:
            opportunity["semantic_context"] = semantic_context
        opportunities.append(opportunity)
        span_audit.append({"span_id": span_id, "status": "OPPORTUNITY_CREATED"})
    result = {
        "artifact_version": "visual-opportunity-plan/1",
        "plan_id": plan_id,
        "semantic_timeline_digest": timeline["timeline_digest"],
        "alignment_digest": timeline["alignment_digest"],
        "transcript_digest": timeline["transcript_digest"],
        "directives_digest": input_identity["directives_digest"],
        "reviewed_script_digest": directive_artifact["reviewed_script_digest"],
        "defaults_digest": _digest(core_defaults),
        "span_audit": span_audit,
        "opportunities": opportunities,
    }
    result["plan_digest"] = _digest(result)
    return result


def _validate_timeline(value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("artifact_version") != "semantic-timeline/1":
        raise VisualOpportunityError("需要 semantic-timeline/1")
    if value.get("timing_provenance") != "actual_aroll_alignment":
        raise VisualOpportunityError("Semantic Timeline 必须来自 actual_aroll_alignment")
    for field in ("timeline_digest", "alignment_digest", "transcript_digest"):
        digest = value.get(field)
        if not isinstance(digest, str) or len(digest) != 64:
            raise VisualOpportunityError(f"Semantic Timeline 缺少 {field}")
    payload = dict(value); supplied_digest = payload.pop("timeline_digest")
    if _digest(payload) != supplied_digest:
        raise VisualOpportunityError("Semantic Timeline timeline_digest 不匹配")
    spans = value.get("spans")
    if not isinstance(spans, list):
        raise VisualOpportunityError("Semantic Timeline spans 无效")
    seen = set()
    normalized = []
    for span in spans:
        if not isinstance(span, Mapping):
            raise VisualOpportunityError("Semantic Timeline span 无效")
        span_id = str(span.get("span_id", ""))
        if not span_id or span_id in seen:
            raise VisualOpportunityError("Semantic Timeline span_id 无效")
        seen.add(span_id)
        if span.get("visual_eligibility") not in {"safe", "keep_only"}:
            raise VisualOpportunityError("Semantic Timeline visual_eligibility 无效")
        if not isinstance(span.get("summary"), str) or not span["summary"].strip():
            raise VisualOpportunityError("Semantic Timeline summary 无效")
        normalized.append(dict(span))
    return {"timeline_digest": supplied_digest, "alignment_digest": value["alignment_digest"], "transcript_digest": value["transcript_digest"], "spans": normalized}


def _validate_defaults(value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or set(value) != {"language", "canvas", "target_duration_ms"}:
        raise VisualOpportunityError("Core defaults 无效")
    language = value["language"]
    canvas = value["canvas"]
    duration = value["target_duration_ms"]
    if not isinstance(language, str) or not language.strip():
        raise VisualOpportunityError("language 无效")
    if not isinstance(canvas, Mapping) or set(canvas) != {"width", "height"}:
        raise VisualOpportunityError("canvas 无效")
    if any(not isinstance(canvas[key], int) or isinstance(canvas[key], bool) or canvas[key] <= 0 for key in ("width", "height")):
        raise VisualOpportunityError("canvas 无效")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise VisualOpportunityError("target_duration_ms 无效")
    return {"language": language, "canvas": {"width": canvas["width"], "height": canvas["height"]}, "target_duration_ms": duration}


def _window_from_span(span: Mapping[str, Any]) -> tuple[int, int]:
    try:
        start = Decimal(str(span.get("actual_start_seconds"))) * 1000
        end = Decimal(str(span.get("actual_end_seconds"))) * 1000
    except (InvalidOperation, ValueError) as exc:
        raise VisualOpportunityError("真实秒数无效") from exc
    if start != start.to_integral_value() or end != end.to_integral_value():
        raise VisualOpportunityError("真实秒数必须精确投影到 millisecond")
    start_ms, end_ms = int(start), int(end)
    if start_ms < 0 or end_ms <= start_ms:
        raise VisualOpportunityError("A-roll window 无效")
    return start_ms, end_ms


def _bounded_context(spans: list[Mapping[str, Any]], index: int, selector: Mapping[str, Any]) -> str:
    count = selector["include_neighboring_spans"]
    if count == 0:
        return ""
    start, end = max(0, index - count), min(len(spans), index + count + 1)
    return " ".join(str(item["summary"]).strip() for item in spans[start:end])


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
