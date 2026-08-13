"""Five-group QA checks, stable issues and repository-owned canonical Gate."""
import hashlib,json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any,Callable,List,Mapping,Optional,Sequence

class EditBridgeQAError(ValueError):pass
@dataclass
class EditBridgeQAInputs:
 checks:List["QACheck"];placements:List[dict];preview_used_placement_ids:List[str]
@dataclass(frozen=True)
class QACheck:
 group:str;check_name:str;validator:Callable[[],None];issue_type:str;severity:str="blocking"

@dataclass(frozen=True)
class CanonicalEditBridgeQAContext:
 media:Mapping[str,Any];extracted:Mapping[str,Any];mapping:Mapping[str,Any]
 chunk_plan:Any;chunk_profile:Mapping[str,Any];transcript:Mapping[str,Any]
 script:Any;alignment_profile:Mapping[str,Any];cues:Sequence[Mapping[str,Any]];alignment:Mapping[str,Any]
 material_view:Mapping[str,Any];material_package_path:Path;report:Any;material_profile:Mapping[str,Any];material_asset_root:Path
 production_plan:Mapping[str,Any];motion_manifest:Mapping[str,Any];production_qa:Mapping[str,Any]
 placements:Sequence[Mapping[str,Any]];timing_profiles:tuple;timing_result:Any;bridge:Mapping[str,Any]
 preview_profile:Mapping[str,Any];preview_manifest:Mapping[str,Any];preview_path:Path
 preview_used_placement_ids:Sequence[str];allowed_roots:Sequence[Path]
 preview_project:Optional[Any]=None;preview_renderer:Optional[Any]=None
 previous_bridge:Optional[Mapping[str,Any]]=None;revision_adjustment:Optional[Mapping[str,Any]]=None
 subtitle_artifact:Optional[Mapping[str,Any]]=None;subtitle_profile:Optional[Mapping[str,Any]]=None

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
 used_ready=used_ready or all(pid=="VP0000" or (pid in by_id and by_id[pid].get("placement_status")=="ready" and by_id[pid].get("preview_enabled",True)) for pid in inputs.preview_used_placement_ids)
 check("preview","preview_uses_ready_only",used_ready,"preview_used_unready_asset")
 unready=[p for p in inputs.placements if p.get("placement_status")!="ready"]
 if unready:issues.append({"issue_id":f"EBI{len(issues)+1:04d}","issue_type":"partial_placement_unready","scope":"placement","severity":"warning"})
 gate="fail" if any(i["severity"]=="blocking" for i in issues) else "warnings" if issues else "pass"
 qa={"artifact_version":"edit-bridge-qa/1","checks":checks,"issues":issues,"package_gate_status":gate};qa["qa_digest"]=_digest(qa);return qa
def validate_edit_bridge_qa(qa,inputs):
 if dict(qa)!=run_edit_bridge_qa(inputs) or qa.get("qa_digest")!=_digest(qa):raise EditBridgeQAError("Edit Bridge QA 与受控检查重推导不一致")

def _value(value): return value.data if hasattr(value,"data") else value
def _root_digest(value,*names):
 raw=_value(value)
 for name in names:
  if isinstance(raw,Mapping) and raw.get(name):return raw[name]
 raise EditBridgeQAError(f"canonical root 缺少 digest：{names[0]}")

def _validate_root_chain(context):
 from .narration_media import canonical_digest,probe_narration_media,sha256_file
 from .production_qa import validate_motion_manifest,validate_production_qa
 source=Path(context.media["immutable_local_path"])
 if sha256_file(source)!=context.media["sha256"]:raise EditBridgeQAError("Clean A-roll SHA 已变化")
 evidence=probe_narration_media(source)
 if Decimal(evidence.presentation_duration_seconds)!=Decimal(str(context.media["presentation_duration_seconds"])):raise EditBridgeQAError("Clean A-roll presentation duration 已变化")
 validate_motion_manifest(context.motion_manifest,context.production_plan)
 validate_production_qa(context.production_qa,context.production_plan,context.motion_manifest)
 expected={
  "narration_media_digest":_root_digest(context.media,"artifact_digest"),
  "extracted_audio_digest":_root_digest(context.extracted,"artifact_digest"),
  "timestamp_mapping_digest":_root_digest(context.mapping,"mapping_digest"),
  "chunk_plan_digest":context.chunk_plan.digest,
  "transcript_digest":_root_digest(context.transcript,"transcript_digest"),
  "script_content_digest":_root_digest(context.alignment,"script_content_digest"),
  "research_digest":canonical_digest(_value(context.report)),
  "material_package_digest":_root_digest(context.material_view,"package_digest"),
  "material_view_digest":_root_digest(context.material_view,"view_digest"),
  "production_plan_digest":_root_digest(context.production_plan,"plan_digest"),
  "motion_manifest_digest":_root_digest(context.motion_manifest,"manifest_digest"),
  "production_qa_digest":_root_digest(context.production_qa,"qa_digest"),
  "alignment_digest":_root_digest(context.alignment,"artifact_digest"),
  "alignment_profile_digest":_root_digest(context.alignment_profile,"profile_digest"),
  "rough_cut_profile_digest":_root_digest(context.timing_profiles[0],"profile_digest"),
 "aligned_preview_profile_digest":_root_digest(context.preview_profile,"profile_digest"),
 }
 if context.subtitle_artifact is not None and context.subtitle_profile is not None:
  expected.update(subtitle_artifact_digest=_root_digest(context.subtitle_artifact,"artifact_digest"),subtitle_profile_digest=_root_digest(context.subtitle_profile,"profile_digest"))
 if dict(context.bridge.get("root_bindings",{}))!=expected:raise EditBridgeQAError("Edit Bridge canonical root binding 不一致")

def _validate_transcript_chain(context):
 from .audio_timestamp_mapping import validate_timestamp_mapping
 from .transcript_builder import validate_timed_transcript
 from .transcription_chunking import validate_transcription_chunk_plan
 validate_timestamp_mapping(context.mapping,context.media,context.extracted)
 validate_transcription_chunk_plan(context.chunk_plan,context.extracted,context.mapping,context.chunk_profile)
 validate_timed_transcript(context.transcript,context.media,context.extracted,context.mapping,context.chunk_plan)
 if context.subtitle_artifact is None or context.subtitle_profile is None:raise EditBridgeQAError("正式 Preview 缺少 Subtitle roots")
 from .subtitle_builder import validate_subtitle_artifact
 validate_subtitle_artifact(context.subtitle_artifact,context.transcript,context.media,context.subtitle_profile)

def _validate_alignment_chain(context):
 from .alignment_validation import validate_script_alignment
 validate_script_alignment(context.alignment,context.script,context.transcript,context.mapping,context.alignment_profile,context.cues,context.media)

def _validate_placement_chain(context):
 from .edit_bridge_planner import build_visual_placements,derive_placement_timing
 from .edit_bridge_validation import validate_edit_bridge
 from .material_bridge import validate_material_production_view
 validate_material_production_view(context.material_view,context.material_package_path,context.script,context.report,context.material_profile,context.material_asset_root)
 raw=build_visual_placements(context.alignment,context.material_view,context.production_plan,context.motion_manifest,context.media,context.allowed_roots,context.production_qa)
 derived=derive_placement_timing(raw,context.timing_profiles)
 if tuple(context.timing_result.placements)!=tuple(derived.placements) or tuple(context.timing_result.conflicts)!=tuple(derived.conflicts) or tuple(context.timing_result.adjustments)!=tuple(derived.adjustments):raise EditBridgeQAError("Placement timing 无法从 canonical roots 重推导")
 if context.previous_bridge is not None:
  from .edit_bridge_storage import create_bridge_revision
  if tuple(context.previous_bridge.get("visual_placements",[]))!=tuple(derived.placements):raise EditBridgeQAError("上一 Bridge 不是 canonical placement 基线")
  expected=create_bridge_revision(context.previous_bridge,context.revision_adjustment,created_at=context.bridge["created_at"],fps=context.preview_profile["fps"])
  if dict(context.bridge)!=expected:raise EditBridgeQAError("Bridge Revision 不是用户反馈的确定性结果")
 else:
  if tuple(context.placements)!=tuple(derived.placements):raise EditBridgeQAError("Bridge placements 与重推导不一致")
  validate_edit_bridge(context.bridge,context.bridge["root_bindings"],derived.placements,derived.conflicts,derived.adjustments,context.alignment.get("gaps",[]))

def _validate_preview_chain(context):
 from .aligned_preview.remotion import probe_audio_presentation,validate_aligned_preview_manifest,validate_preview_audio_presentation
 validate_aligned_preview_manifest(context.preview_manifest,context.preview_path)
 if context.preview_manifest.get("bridge_digest")!=context.bridge.get("package_digest") or context.preview_manifest.get("profile_digest")!=context.preview_profile.get("profile_digest"):raise EditBridgeQAError("Preview Manifest root binding 不一致")
 if not context.preview_manifest.get("subtitles_enabled") or context.preview_manifest.get("subtitle_artifact_digest")!=context.subtitle_artifact.get("artifact_digest") or context.preview_manifest.get("subtitle_transcript_digest")!=context.transcript.get("transcript_digest") or context.preview_manifest.get("subtitle_profile_digest")!=context.subtitle_profile.get("profile_digest"):raise EditBridgeQAError("Preview Subtitle binding 或 renderer enablement 不一致")
 if list(context.preview_manifest.get("used_placement_ids",[]))!=list(context.preview_used_placement_ids):raise EditBridgeQAError("Preview 使用画面清单不一致")
 source=probe_audio_presentation(context.media["immutable_local_path"]);preview=probe_audio_presentation(context.preview_path)
 validate_preview_audio_presentation(source,preview,max(source.tolerance_seconds,preview.tolerance_seconds,1/30))
 if context.preview_renderer is not None and context.preview_project is not None:
  context.preview_renderer.validate_project(context.preview_project)
  if not context.preview_project.subtitles_enabled or context.preview_project.subtitle_artifact_digest!=context.subtitle_artifact.get("artifact_digest"):raise EditBridgeQAError("Renderer project 未启用当前字幕")

def build_canonical_edit_bridge_qa_inputs(context):
 """Create the only formal QA input set; callers cannot replace validators."""
 checks=[
  QACheck("root","root_artifacts_revalidated",lambda:_validate_root_chain(context),"invalid_root_binding"),
  QACheck("transcript","mapping_chunk_transcript_rederived",lambda:_validate_transcript_chain(context),"invalid_transcript_chain"),
  QACheck("alignment","normalization_status_risk_rederived",lambda:_validate_alignment_chain(context),"alignment_false_ready"),
  QACheck("placement","placement_files_and_timing_rederived",lambda:_validate_placement_chain(context),"invalid_placement_chain"),
  QACheck("preview","preview_manifest_and_audio_rederived",lambda:_validate_preview_chain(context),"preview_audio_presentation_mismatch"),
 ]
 return EditBridgeQAInputs(checks,list(context.placements),list(context.preview_used_placement_ids))

def run_canonical_edit_bridge_qa(context):
 return run_edit_bridge_qa(build_canonical_edit_bridge_qa_inputs(context))

def validate_canonical_edit_bridge_qa(qa,context):
 validate_edit_bridge_qa(qa,build_canonical_edit_bridge_qa_inputs(context))
