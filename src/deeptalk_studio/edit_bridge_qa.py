"""Five-group QA checks, stable issues and fail-closed package Gate."""
import hashlib,json
from dataclasses import dataclass
from typing import Callable,List

class EditBridgeQAError(ValueError):pass
@dataclass
class EditBridgeQAInputs:
 checks:List["QACheck"];placements:List[dict];preview_used_placement_ids:List[str]
@dataclass(frozen=True)
class QACheck:
 group:str;check_name:str;validator:Callable[[],None];issue_type:str;severity:str="blocking"

REQUIRED_GROUPS={"root","transcript","alignment","placement","preview"}

def _digest(value):
 p=dict(value);p.pop("qa_digest",None);return hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
def run_edit_bridge_qa(inputs):
 checks=[];issues=[]
 def check(group,name,outcome,issue_type="",severity="blocking"):
  checks.append({"group":group,"check_name":name,"outcome":"pass" if outcome else "fail"})
  if not outcome:issues.append({"issue_id":f"EBI{len(issues)+1:04d}","issue_type":issue_type,"scope":group,"severity":severity})
 groups={item.group for item in inputs.checks}
 for group in sorted(REQUIRED_GROUPS-groups):check(group,"required_group_present",False,"missing_required_qa_group")
 for item in inputs.checks:
  try:item.validator();outcome=True
  except Exception:outcome=False
  check(item.group,item.check_name,outcome,item.issue_type,item.severity)
 by_id={p["placement_id"]:p for p in inputs.placements};used_ready=all(pid in by_id and by_id[pid].get("placement_status")=="ready" for pid in inputs.preview_used_placement_ids)
 check("preview","preview_uses_ready_only",used_ready,"preview_used_unready_asset")
 unready=[p for p in inputs.placements if p.get("placement_status")!="ready"]
 if unready:issues.append({"issue_id":f"EBI{len(issues)+1:04d}","issue_type":"partial_placement_unready","scope":"placement","severity":"warning"})
 gate="fail" if any(i["severity"]=="blocking" for i in issues) else "warnings" if issues else "pass"
 qa={"artifact_version":"edit-bridge-qa/1","checks":checks,"issues":issues,"package_gate_status":gate};qa["qa_digest"]=_digest(qa);return qa
def validate_edit_bridge_qa(qa,inputs):
 if dict(qa)!=run_edit_bridge_qa(inputs) or qa.get("qa_digest")!=_digest(qa):raise EditBridgeQAError("Edit Bridge QA 与受控检查重推导不一致")
