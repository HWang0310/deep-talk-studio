"""Clock-free, immutable editorial inputs for Visual Opportunity planning."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping


DIRECTIVES_VERSION = "visual-opportunity-directives/1"
_ROOT_FIELDS = frozenset({
    "artifact_version", "directives_id", "revision", "semantic_timeline_digest",
    "reviewed_script_digest", "factual_context_digest", "directives",
})
_DIRECTIVE_FIELDS = frozenset({
    "directive_id", "span_id", "visual_purpose", "why_opportunity",
    "semantic_context_selector", "factual_context_refs",
})
_FORBIDDEN_KEYS = frozenset({
    "start_ms", "end_ms", "start_seconds", "end_seconds", "duration_ms", "duration_seconds",
    "a_roll_window", "suggested_placement", "decision", "visual_kind", "asset_class",
    "candidate", "candidate_id", "plugin_id", "plugin_context", "generation_policy",
})
_FORBIDDEN_VALUES = frozenset({"KEEP_A_ROLL", "REAL_MATERIAL", "MG_MOTION", "ADVANCED_MOTION"})
_IDENTIFIER = re.compile(r"[A-Za-z0-9._-]+")


class VisualOpportunityDirectiveError(ValueError):
    """The clock-free V2 editorial boundary was violated."""


def directive_digest(value: Mapping[str, Any]) -> str:
    """Return the deterministic digest of a validated directives artifact."""
    normalized = normalize_visual_opportunity_directives(value)
    return hashlib.sha256(_canonical_json(normalized).encode("utf-8")).hexdigest()


def normalize_visual_opportunity_directives(value: Any) -> dict:
    """Validate and return a detached, deterministic V2 directives artifact."""
    data = _mapping(value, "directives")
    _only_fields(data, _ROOT_FIELDS, "directives")
    _required_fields(data, _ROOT_FIELDS - {"factual_context_digest"}, "directives")
    if data["artifact_version"] != DIRECTIVES_VERSION:
        raise VisualOpportunityDirectiveError("artifact_version 必须是 visual-opportunity-directives/1")
    _identifier(data["directives_id"], "directives_id")
    if not isinstance(data["revision"], int) or isinstance(data["revision"], bool) or data["revision"] < 1:
        raise VisualOpportunityDirectiveError("revision 必须是正整数")
    _digest(data["semantic_timeline_digest"], "semantic_timeline_digest")
    _digest(data["reviewed_script_digest"], "reviewed_script_digest")
    if "factual_context_digest" in data:
        _digest(data["factual_context_digest"], "factual_context_digest")
    if not isinstance(data["directives"], list):
        raise VisualOpportunityDirectiveError("directives 必须是列表")
    _reject_forbidden(value)
    directive_ids = set()
    span_ids = set()
    normalized = []
    for item in data["directives"]:
        directive = _mapping(item, "directive")
        _only_fields(directive, _DIRECTIVE_FIELDS, "directive")
        _required_fields(directive, _DIRECTIVE_FIELDS, "directive")
        directive_id = _identifier(directive["directive_id"], "directive_id")
        span_id = _identifier(directive["span_id"], "span_id")
        if directive_id in directive_ids:
            raise VisualOpportunityDirectiveError("directive_id 不可重复")
        if span_id in span_ids:
            raise VisualOpportunityDirectiveError("span_id 不可重复")
        directive_ids.add(directive_id); span_ids.add(span_id)
        _text(directive["visual_purpose"], "visual_purpose")
        _text(directive["why_opportunity"], "why_opportunity")
        selector = _mapping(directive["semantic_context_selector"], "semantic_context_selector")
        _only_fields(selector, {"include_neighboring_spans"}, "semantic_context_selector")
        _required_fields(selector, {"include_neighboring_spans"}, "semantic_context_selector")
        neighbors = selector["include_neighboring_spans"]
        if not isinstance(neighbors, int) or isinstance(neighbors, bool) or neighbors < 0:
            raise VisualOpportunityDirectiveError("include_neighboring_spans 必须是非负整数")
        refs = directive["factual_context_refs"]
        if not isinstance(refs, list):
            raise VisualOpportunityDirectiveError("factual_context_refs 必须是列表")
        for ref in refs:
            fact = _mapping(ref, "factual_context_ref")
            _only_fields(fact, {"claim_id", "evidence_id"}, "factual_context_ref")
            _required_fields(fact, {"claim_id", "evidence_id"}, "factual_context_ref")
            _identifier(fact["claim_id"], "claim_id"); _identifier(fact["evidence_id"], "evidence_id")
        normalized.append(copy.deepcopy(dict(directive)))
    result = {
        "artifact_version": DIRECTIVES_VERSION,
        "directives_id": str(data["directives_id"]),
        "revision": data["revision"],
        "semantic_timeline_digest": str(data["semantic_timeline_digest"]),
        "reviewed_script_digest": str(data["reviewed_script_digest"]),
        "directives": normalized,
    }
    if "factual_context_digest" in data:
        result["factual_context_digest"] = str(data["factual_context_digest"])
    return result


def author_visual_opportunity_directives(semantic_timeline: Mapping[str, Any], reviewed_script: Mapping[str, Any], factual_context: list[Mapping[str, Any]], editorial_directives: list[Mapping[str, Any]], *, directives_id: str, revision: int, review_artifact: Mapping[str, Any] | None = None, report: Any = None, profile: Mapping[str, Any] | None = None) -> dict:
    """Create the production directive boundary from canonical, verifiable inputs.

    Callers author only visual intent and why; Core derives all lineage digests,
    canonicalizes fact references, and never accepts supplied timing or V1
    decisions.
    """
    timeline_digest = semantic_timeline.get("timeline_digest")
    if semantic_timeline.get("artifact_version") != "semantic-timeline/1" or semantic_timeline.get("timing_provenance") != "actual_aroll_alignment":
        raise VisualOpportunityDirectiveError("需要已验证的 semantic-timeline/1")
    _digest(timeline_digest, "semantic_timeline_digest")
    timeline_payload = dict(semantic_timeline)
    timeline_payload.pop("timeline_digest", None)
    if hashlib.sha256(_canonical_json(timeline_payload).encode("utf-8")).hexdigest() != timeline_digest:
        raise VisualOpportunityDirectiveError("semantic-timeline/1 digest 不匹配")
    review_state = reviewed_script.get("review_state") if isinstance(reviewed_script.get("review_state"), Mapping) else {}
    reviewed_digest = review_state.get("reviewed_content_digest")
    _digest(reviewed_digest, "reviewed_script_digest")
    from .script_validation import script_content_digest, validate_script_draft
    try:
        actual_script_digest = script_content_digest(reviewed_script)
    except (KeyError, TypeError) as exc:
        raise VisualOpportunityDirectiveError("需要 canonical reviewed Script") from exc
    if reviewed_script.get("status") != "reviewed" or actual_script_digest != reviewed_digest or review_artifact is None or report is None or profile is None:
        raise VisualOpportunityDirectiveError("Reviewed Script digest 不匹配")
    try: validate_script_draft(reviewed_script, report, profile, review_artifact)
    except Exception as exc: raise VisualOpportunityDirectiveError("Reviewed Script canonical Review linkage 无效") from exc
    if not isinstance(factual_context, list):
        raise VisualOpportunityDirectiveError("factual_context 必须是列表")
    allowed_facts = []
    for fact in factual_context:
        mapping = _mapping(fact, "factual_context")
        _only_fields(mapping, {"claim_id", "evidence_id"}, "factual_context")
        _required_fields(mapping, {"claim_id", "evidence_id"}, "factual_context")
        _identifier(mapping["claim_id"], "claim_id"); _identifier(mapping["evidence_id"], "evidence_id")
        allowed_facts.append({"claim_id": mapping["claim_id"], "evidence_id": mapping["evidence_id"]})
    facts_digest = hashlib.sha256(_canonical_json(allowed_facts).encode("utf-8")).hexdigest()
    if not isinstance(editorial_directives, list):
        raise VisualOpportunityDirectiveError("editorial_directives 必须是列表")
    converted = []
    spans={item.get("span_id"): item for item in semantic_timeline.get("spans", []) if isinstance(item,Mapping)}
    approved_pairs={(item["claim_id"],item["evidence_id"]) for item in allowed_facts}
    report_links = getattr(report,"evidence_links",None) or getattr(report,"data",{}).get("evidence_links",[])
    report_pairs={(getattr(link,"claim_id",None) if not isinstance(link,Mapping) else link.get("claim_id"),getattr(link,"id",None) if not isinstance(link,Mapping) else link.get("id")) for link in report_links}
    if not approved_pairs.issubset(report_pairs):
        raise VisualOpportunityDirectiveError("approved factual pool 必须来自 canonical verified Research bindings")
    for item in editorial_directives:
        source = _mapping(item, "editorial_directive")
        _only_fields(source, {"directive_id", "span_id", "visual_intent", "why_visual", "semantic_context_selector", "factual_context_refs"}, "editorial_directive")
        _required_fields(source, {"directive_id", "span_id", "visual_intent", "why_visual"}, "editorial_directive")
        if source["span_id"] not in spans or spans[source["span_id"]].get("visual_eligibility") != "safe":
            raise VisualOpportunityDirectiveError("directive span_id 必须是 verified safe Semantic Timeline span")
        refs = source.get("factual_context_refs", [])
        if not isinstance(refs,list) or any(not isinstance(ref,Mapping) or (ref.get("claim_id"),ref.get("evidence_id")) not in approved_pairs for ref in refs):
            raise VisualOpportunityDirectiveError("factual_context_refs 必须绑定已批准事实")
        converted.append({"directive_id": source["directive_id"], "span_id": source["span_id"], "visual_purpose": source["visual_intent"], "why_opportunity": source["why_visual"], "semantic_context_selector": source.get("semantic_context_selector", {"include_neighboring_spans": 0}), "factual_context_refs": copy.deepcopy(refs)})
    return normalize_visual_opportunity_directives({"artifact_version": DIRECTIVES_VERSION, "directives_id": directives_id, "revision": revision, "semantic_timeline_digest": timeline_digest, "reviewed_script_digest": reviewed_digest, "factual_context_digest": facts_digest, "directives": converted})


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VisualOpportunityDirectiveError(f"{label} 必须是对象")
    return value


def _only_fields(value: Mapping[str, Any], allowed: frozenset | set, label: str) -> None:
    unexpected = sorted(set(value) - set(allowed))
    if unexpected:
        raise VisualOpportunityDirectiveError(f"{label} 含有未允许字段：{unexpected[0]}")


def _required_fields(value: Mapping[str, Any], required: frozenset | set, label: str) -> None:
    missing = sorted(set(required) - set(value))
    if missing:
        raise VisualOpportunityDirectiveError(f"{label} 缺少字段：{missing[0]}")


def _identifier(value: Any, label: str) -> str:
    text = str(value)
    if not _IDENTIFIER.fullmatch(text) or text in {".", ".."}:
        raise VisualOpportunityDirectiveError(f"{label} 无效")
    return text


def _digest(value: Any, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise VisualOpportunityDirectiveError(f"{label} 必须是 SHA-256 digest")


def _text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise VisualOpportunityDirectiveError(f"{label} 必须是非空文本")


def _reject_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise VisualOpportunityDirectiveError(f"禁止字段：{key}")
            _reject_forbidden(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden(nested)
    elif isinstance(value, str) and value in _FORBIDDEN_VALUES:
        raise VisualOpportunityDirectiveError(f"禁止 V1 decision 值：{value}")
