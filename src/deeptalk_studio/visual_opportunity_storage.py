"""Immutable storage for machine-only ``visual-opportunity-plan/1`` artifacts."""
from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import Any, Mapping
class VisualOpportunityStorageError(ValueError): pass
def save_visual_opportunity_plan(value: Mapping[str, Any], root: Path) -> Path:
    _valid(value); path=Path(root)/str(value["plan_id"])/"visual-opportunity-plan.json"; path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError as exc: raise VisualOpportunityStorageError("不会覆盖已有工件") from exc
    with os.fdopen(fd,"w",encoding="utf-8") as h: h.write(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    return path
def load_visual_opportunity_plan(path: Path) -> dict:
    try: value=json.loads(Path(path).read_text(encoding="utf-8")); _valid(value)
    except (OSError,json.JSONDecodeError,VisualOpportunityStorageError) as exc: raise VisualOpportunityStorageError("opportunity plan 工件无效") from exc
    if Path(path).parent.name != value["plan_id"]: raise VisualOpportunityStorageError("opportunity plan 路径无效")
    return value
def _valid(value: Any) -> None:
    if not isinstance(value,Mapping) or value.get("artifact_version")!="visual-opportunity-plan/1" or not re.fullmatch(r"VOP-[0-9a-f]{24}",str(value.get("plan_id",""))) or len(str(value.get("plan_digest","")))!=64: raise VisualOpportunityStorageError("opportunity plan schema 无效")
