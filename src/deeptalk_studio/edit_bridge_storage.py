"""Immutable Edit Bridge package storage and natural-language revisions."""
import hashlib,json,re
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any,Mapping,Tuple
from .edit_bridge_renderer import render_edit_bridge_csv,render_edit_bridge_markdown

class EditBridgeStorageError(ValueError): pass
@dataclass(frozen=True)
class EditBridgePaths: json_path:Path; markdown_path:Path; csv_path:Path
@dataclass(frozen=True)
class AdjustmentResolution: unique:bool; adjustment:dict; candidates:Tuple[str,...]

def _safe(v):
 if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",str(v)): raise EditBridgeStorageError("Bridge ID 不安全")
 return str(v)
def _digest(v):
 p=deepcopy(dict(v));p.pop("package_digest",None);return hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
def save_edit_bridge(bridge,root):
 d=Path(root)/_safe(bridge["bridge_id"]);d.mkdir(parents=True,exist_ok=True);r=int(bridge["revision"]);stem=d/f"edit-bridge-r{r:04d}"
 paths=EditBridgePaths(stem.with_suffix(".json"),stem.with_suffix(".md"),d/f"edit-bridge-markers-r{r:04d}.csv")
 if any(p.exists() for p in (paths.json_path,paths.markdown_path,paths.csv_path)): raise EditBridgeStorageError("Edit Bridge 已存在，不得覆盖")
 paths.json_path.write_text(json.dumps(dict(bridge),ensure_ascii=False,indent=2)+"\n",encoding="utf-8");paths.markdown_path.write_text(render_edit_bridge_markdown(bridge),encoding="utf-8");paths.csv_path.write_bytes(render_edit_bridge_csv(bridge));return paths
def load_edit_bridge(path):
 try:return json.loads(Path(path).read_text(encoding="utf-8"))
 except Exception as exc:raise EditBridgeStorageError("Edit Bridge 文件无效") from exc
def resolve_adjustment_target(bridge,feedback):
 words=[w for w in re.split(r"[\s，。、]+",feedback) if len(w)>=2]
 keywords=[key for key in ("监管","文件","关系","截图","视频","时间线","比较") if key in feedback]
 matches=[]
 for p in bridge.get("visual_placements",[]):
  name=p.get("safe_filename","");score=sum(w in name or name.rsplit(".",1)[0] in w for w in words)+sum(key in name for key in keywords)
  if score:matches.append((score,p))
 matches.sort(key=lambda x:-x[0]); best=[p for score,p in matches if matches and score==matches[0][0]]
 if len(best)!=1:return AdjustmentResolution(False,{},tuple((p.get("safe_filename") or p.get("source_kind","画面")) for p in best[:3]))
 direction=("suppress" if any(w in feedback for w in ("留真人","不要画面","只要真人")) else
  "shorter" if any(w in feedback for w in ("短","太长")) else
  "longer" if any(w in feedback for w in ("长一点","多留")) else
  "later" if any(w in feedback for w in ("晚","后一点")) else "earlier")
 return AdjustmentResolution(True,{"placement_id":best[0]["placement_id"],"adjustment_type":direction,"reason":feedback},())
def create_bridge_revision(previous,adjustment,*,created_at):
 result=deepcopy(dict(previous));result["revision"]=int(previous["revision"])+1;result["previous_revision"]=int(previous["revision"]);result["created_at"]=created_at
 placement=next((p for p in result.get("visual_placements",[]) if p.get("placement_id")==adjustment["placement_id"]),None)
 if placement is None:raise EditBridgeStorageError("调整目标已不在当前 Bridge")
 start=Decimal(str(placement["preview_effective_in_seconds"]));end=Decimal(str(placement["preview_effective_out_seconds"]));duration=end-start
 new_start,new_end=start,end;kind=adjustment["adjustment_type"]
 if kind=="shorter":new_end=start+max(Decimal("0.5"),duration*Decimal("0.75"))
 elif kind=="longer":new_end=min(Decimal(str(placement.get("semantic_out_seconds") or end)),end+max(Decimal("0.5"),duration*Decimal("0.25")))
 elif kind=="later":new_start=min(end-Decimal("0.5"),start+min(Decimal("1"),duration*Decimal("0.25")))
 elif kind=="earlier":new_start=max(Decimal(str(placement.get("semantic_in_seconds") or 0)),start-min(Decimal("1"),duration*Decimal("0.25")))
 elif kind=="suppress":placement["preview_enabled"]=False
 else:raise EditBridgeStorageError("不支持的画面调整意图")
 placement["preview_effective_in_seconds"]=str(new_start);placement["preview_effective_out_seconds"]=str(new_end);placement["layout_source"]="user_adjustment"
 adjustment_id=f"PA{len(result.get('preview_adjustments',[]))+1:04d}";placement["preview_adjustment_id"]=adjustment_id
 result.setdefault("preview_adjustments",[]).append({"artifact_version":"preview-adjustment/1","adjustment_id":adjustment_id,"placement_id":adjustment["placement_id"],"adjustment_type":kind,"reason":adjustment["reason"],"original_in_seconds":str(start),"original_out_seconds":str(end),"preview_in_seconds":str(new_start),"preview_out_seconds":str(new_end),"provenance":"user_feedback"})
 result["package_digest"]=_digest(result);return result
