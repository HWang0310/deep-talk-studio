"""Fail-closed immutable storage for visual-opportunity-plan/1 artifacts."""
from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path
from typing import Any, Mapping
class VisualOpportunityStorageError(ValueError): pass

def _digest(value: Mapping[str, Any]) -> str: return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _sha(value: Any) -> bool: return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value) is not None
def _id(value: Any) -> bool: return isinstance(value,str) and bool(re.fullmatch(r"[A-Za-z0-9._-]+",value))

def save_visual_opportunity_plan(value: Mapping[str, Any], root: Path) -> Path:
    _valid(value); path=Path(root)/str(value["plan_id"])/"visual-opportunity-plan.json"; path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError as exc: raise VisualOpportunityStorageError("不会覆盖已有工件") from exc
    with os.fdopen(fd,"w",encoding="utf-8") as h: h.write(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    return path

def load_visual_opportunity_plan(path: Path) -> dict:
    source=Path(path)
    try:
        if source.is_symlink() or not source.is_file(): raise VisualOpportunityStorageError("opportunity plan 路径不安全")
        value=json.loads(source.read_text(encoding="utf-8")); _valid(value)
    except (OSError,json.JSONDecodeError,VisualOpportunityStorageError) as exc: raise VisualOpportunityStorageError("opportunity plan 工件无效") from exc
    if source.parent.name != value["plan_id"] or source.name != "visual-opportunity-plan.json": raise VisualOpportunityStorageError("opportunity plan 路径无效")
    return value

def _valid(value: Any) -> None:
    allowed={"artifact_version","plan_id","semantic_timeline_digest","alignment_digest","transcript_digest","directives_digest","reviewed_script_digest","defaults_digest","span_audit","opportunities","plan_digest"}
    if not isinstance(value,Mapping) or set(value)!=allowed or value.get("artifact_version")!="visual-opportunity-plan/1" or not re.fullmatch(r"VOP-[0-9a-f]{24}",str(value.get("plan_id",""))) or not all(_sha(value.get(field)) for field in ("semantic_timeline_digest","alignment_digest","transcript_digest","directives_digest","reviewed_script_digest","defaults_digest")) or not isinstance(value.get("opportunities"),list) or not isinstance(value.get("span_audit"),list): raise VisualOpportunityStorageError("opportunity plan schema 无效")
    seen_spans=set(); seen_opportunities=set()
    for audit in value["span_audit"]:
        if not isinstance(audit,Mapping) or set(audit)-{"span_id","status","reason"} or not _id(audit.get("span_id")) or audit.get("span_id") in seen_spans or audit.get("status") not in {"OPPORTUNITY_CREATED","NO_OPPORTUNITY"}: raise VisualOpportunityStorageError("span audit 无效")
        if audit["status"]=="NO_OPPORTUNITY" and audit.get("reason") not in {"unsafe_alignment","fact_conflict","no_useful_visual_purpose","creator_base_layer"}: raise VisualOpportunityStorageError("span audit reason 无效")
        if audit["status"]=="OPPORTUNITY_CREATED" and "reason" in audit: raise VisualOpportunityStorageError("created audit 不可带 reason")
        seen_spans.add(audit["span_id"])
    for opportunity in value["opportunities"]:
        required={"opportunity_id","spoken_semantics","visual_purpose","a_roll_window","target_duration_ms","language","canvas","factual_context"}
        if not isinstance(opportunity,Mapping) or set(opportunity)-required-{"semantic_context"} or not required.issubset(opportunity) or not _id(opportunity.get("opportunity_id")) or opportunity["opportunity_id"] in seen_opportunities or not all(isinstance(opportunity.get(field),str) and opportunity[field].strip() for field in ("spoken_semantics","visual_purpose","language")) or not isinstance(opportunity.get("target_duration_ms"),int) or opportunity["target_duration_ms"]<=0 or not isinstance(opportunity.get("factual_context"),list): raise VisualOpportunityStorageError("opportunity schema 无效")
        window=opportunity["a_roll_window"]; canvas=opportunity["canvas"]
        if not isinstance(window,Mapping) or set(window)!={"start_ms","end_ms"} or not all(isinstance(window[k],int) and window[k]>=0 for k in window) or window["start_ms"]>=window["end_ms"] or not isinstance(canvas,Mapping) or set(canvas)!={"width","height"} or not all(isinstance(canvas[k],int) and canvas[k]>0 for k in canvas): raise VisualOpportunityStorageError("opportunity placement 或 canvas 无效")
        seen_opportunities.add(opportunity["opportunity_id"])
    payload=dict(value); digest=payload.pop("plan_digest",None)
    if digest!=_digest(payload): raise VisualOpportunityStorageError("opportunity plan digest 无效")
