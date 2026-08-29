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
    "reviewed_script_digest", "directives",
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
    _required_fields(data, _ROOT_FIELDS, "directives")
    if data["artifact_version"] != DIRECTIVES_VERSION:
        raise VisualOpportunityDirectiveError("artifact_version 必须是 visual-opportunity-directives/1")
    _identifier(data["directives_id"], "directives_id")
    if not isinstance(data["revision"], int) or isinstance(data["revision"], bool) or data["revision"] < 1:
        raise VisualOpportunityDirectiveError("revision 必须是正整数")
    _digest(data["semantic_timeline_digest"], "semantic_timeline_digest")
    _digest(data["reviewed_script_digest"], "reviewed_script_digest")
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
    return result


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
