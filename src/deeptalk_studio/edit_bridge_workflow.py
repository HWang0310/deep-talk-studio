"""Partial-success orchestration boundary for aligned edit bridge outputs."""
import csv,json
from dataclasses import dataclass
from pathlib import Path
from typing import List,Mapping,Optional

@dataclass
class EditBridgeWorkflowInputs:
 media_kind:str;placements:List[dict];root_bindings:Mapping[str,str]
@dataclass(frozen=True)
class WorkflowSummary:ready_count:int;unready_count:int
@dataclass(frozen=True)
class EditBridgeWorkflowResult:
 qa:dict;marker_csv_path:Path;preview_path:Optional[Path];summary:WorkflowSummary
@dataclass(frozen=True)
class FullEditBridgeWorkflowResult:
 artifact_paths:Mapping[str,Path];artifacts:Mapping[str,object]

FULL_STAGE_ORDER=("import_media","extract_audio","build_mapping","plan_chunks","transcribe","build_transcript","build_alignment","build_bridge","render_preview","run_qa")

def run_full_edit_bridge_workflow(stages,output_root):
 """Execute the approved chain in one owner-controlled order.

 Stage callables are injected so unit tests and provider/renderer adapters remain
 isolated; production wiring supplies the concrete Tasks 3–26 callables.
 """
 if set(stages)!=set(FULL_STAGE_ORDER):raise ValueError("完整 Edit Bridge Workflow 缺少或多出 stage")
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);paths={};artifacts={};previous=None
 for index,name in enumerate(FULL_STAGE_ORDER,1):
  value=stages[name](previous)
  target=root/f"{index:02d}-{name}.json"
  if target.exists():raise ValueError("完整 Edit Bridge Workflow 不覆盖已有 stage")
  serial=value if isinstance(value,(dict,list,str,int,float,bool)) or value is None else {"repr":repr(value)}
  target.write_text(json.dumps(serial,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8");paths[name]=target;artifacts[name]=value;previous=value
 return FullEditBridgeWorkflowResult(paths,artifacts)

def run_edit_bridge_workflow(inputs,output_root):
 if inputs.media_kind not in {"video","audio"}:raise ValueError("Clean A-roll 类型无效")
 if not inputs.root_bindings:raise ValueError("根工件链不完整")
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);marker=root/"edit-bridge-markers.csv"
 if marker.exists():raise ValueError("工作流输出已存在，不得覆盖")
 with marker.open("x",encoding="utf-8-sig",newline="") as handle:
  writer=csv.writer(handle);writer.writerow(["placement","status"]);writer.writerows((p["placement_id"],p["placement_status"]) for p in inputs.placements)
 ready=sum(p["placement_status"]=="ready" for p in inputs.placements);unready=len(inputs.placements)-ready
 issues=[]
 if unready:issues.append({"issue_type":"partial_placement_unready","severity":"warning"})
 if inputs.media_kind=="audio":issues.append({"issue_type":"clean_aroll_video_missing","severity":"warning"})
 qa={"artifact_version":"edit-bridge-qa/1","issues":issues,"package_gate_status":"warnings" if issues else "pass"}
 # A real preview path is created only after Task 23-25 renderer completion; audio-only never gets one.
 return EditBridgeWorkflowResult(qa,marker,None,WorkflowSummary(ready,unready))
