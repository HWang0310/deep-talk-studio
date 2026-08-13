"""Partial-success orchestration boundary for aligned edit bridge outputs."""
import csv
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
