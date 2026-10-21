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
 episode_visual_preference:Optional[Mapping[str,Any]]=None;post_alignment_visual_plan:Optional[Mapping[str,Any]]=None
 output_truth_evidence:Optional[Mapping[str,Any]]=None
 artifact_resolver:Optional[Any]=None

REQUIRED_GROUPS={"root","transcript","alignment","placement","preview"}
AUDIO_DELIVERY_REQUIRED_GROUPS={"root","transcript","alignment","placement","audio_delivery"}

def _digest(value):
 p=dict(value);p.pop("qa_digest",None);return hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
def run_edit_bridge_qa(inputs, required_groups=None, include_preview_used_check=True):
 checks=[];issues=[]
 required=set(REQUIRED_GROUPS if required_groups is None else required_groups)
 def check(group,name,outcome,issue_type="",severity="blocking"):
  checks.append({"group":group,"check_name":name,"outcome":"pass" if outcome else "fail"})
  if not outcome:issues.append({"issue_id":f"EBI{len(issues)+1:04d}","issue_type":issue_type,"scope":group,"severity":severity})
 groups={item.group for item in inputs.checks}
 for group in sorted(required-groups):check(group,"required_group_present",False,"missing_required_qa_group")
 for item in inputs.checks:
  try:item.validator();outcome=True
  except Exception:outcome=False
  check(item.group,item.check_name,outcome,item.issue_type,item.severity)
 if include_preview_used_check:
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
 has_preference=getattr(context,"episode_visual_preference",None) is not None
 has_visual_plan=getattr(context,"post_alignment_visual_plan",None) is not None
 if has_preference != has_visual_plan:raise EditBridgeQAError("Episode Visual Preference 与 Post-Alignment Visual Plan 必须成对绑定")
 if has_preference:
  from .episode_visual_preference import load_episode_visual_default,validate_episode_visual_preference
  from .post_alignment_visual_plan import validate_post_alignment_visual_plan
  validate_episode_visual_preference(context.episode_visual_preference,load_episode_visual_default())
  validate_post_alignment_visual_plan(context.post_alignment_visual_plan,_value(context.script),context.transcript,context.alignment,context.episode_visual_preference)
  if context.production_plan.get("episode_visual_preference_digest")!=context.episode_visual_preference["preference_digest"] or context.production_plan.get("post_alignment_visual_plan_digest")!=context.post_alignment_visual_plan["plan_digest"]:raise EditBridgeQAError("Production Plan Visual Context binding 不一致")
 source=Path(context.media["immutable_local_path"])
 if sha256_file(source)!=context.media["sha256"]:raise EditBridgeQAError("Clean A-roll SHA 已变化")
 evidence=probe_narration_media(source)
 if Decimal(evidence.presentation_duration_seconds)!=Decimal(str(context.media["presentation_duration_seconds"])):raise EditBridgeQAError("Clean A-roll presentation duration 已变化")
 validate_motion_manifest(context.motion_manifest,context.production_plan,artifact_resolver=context.artifact_resolver)
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
 if has_preference:
  expected.update(episode_visual_preference_digest=context.episode_visual_preference["preference_digest"],post_alignment_visual_plan_digest=context.post_alignment_visual_plan["plan_digest"])
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
 from .edit_bridge_planner import build_base_aroll_placement,build_visual_placements,build_visual_plan_placements,derive_placement_timing
 from .edit_bridge_validation import validate_edit_bridge
 from .material_bridge import validate_material_production_view
 validate_material_production_view(context.material_view,context.material_package_path,context.script,context.report,context.material_profile,context.material_asset_root,artifact_resolver=context.artifact_resolver)
 if getattr(context,"post_alignment_visual_plan",None) is not None:
  raw=(build_base_aroll_placement(context.media),)+build_visual_plan_placements(context.post_alignment_visual_plan,context.material_view,context.production_plan,context.motion_manifest,context.allowed_roots,artifact_resolver=context.artifact_resolver)
 else:
  raw=build_visual_placements(context.alignment,context.material_view,context.production_plan,context.motion_manifest,context.media,context.allowed_roots,context.production_qa,artifact_resolver=context.artifact_resolver)
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

def _validate_output_truth_chain(context):
 from .output_truth import validate_output_truth_evidence
 evidence=getattr(context,"output_truth_evidence",None)
 if evidence is None:
  if getattr(context,"post_alignment_visual_plan",None) is not None:raise EditBridgeQAError("正式 Full Visual Preview 缺少 Output-Truth evidence")
  return
 validate_output_truth_evidence(evidence,context.preview_path)

def build_canonical_edit_bridge_qa_inputs(context):
 """Create the only formal QA input set; callers cannot replace validators."""
 checks=[
  QACheck("root","root_artifacts_revalidated",lambda:_validate_root_chain(context),"invalid_root_binding"),
  QACheck("transcript","mapping_chunk_transcript_rederived",lambda:_validate_transcript_chain(context),"invalid_transcript_chain"),
  QACheck("alignment","normalization_status_risk_rederived",lambda:_validate_alignment_chain(context),"alignment_false_ready"),
  QACheck("placement","placement_files_and_timing_rederived",lambda:_validate_placement_chain(context),"invalid_placement_chain"),
  QACheck("preview","preview_manifest_and_audio_rederived",lambda:_validate_preview_chain(context),"preview_audio_presentation_mismatch"),
  QACheck("preview","final_encoded_output_truth",lambda:_validate_output_truth_chain(context),"invalid_output_truth"),
 ]
 return EditBridgeQAInputs(checks,list(context.placements),list(context.preview_used_placement_ids))

def run_canonical_edit_bridge_qa(context):
 return run_edit_bridge_qa(build_canonical_edit_bridge_qa_inputs(context))

def validate_canonical_edit_bridge_qa(qa,context):
 validate_edit_bridge_qa(qa,build_canonical_edit_bridge_qa_inputs(context))

# ---------------------------------------------------------------------------
# Audio-only delivery QA (Issue #30): same-strength re-derivation plus
# fail-closed audio-delivery checks.  The video preview chain is never touched.
# ---------------------------------------------------------------------------

def _audio_media_kind(context):
 if context.media.get("media_kind")!="audio" or bool(context.media.get("video_stream",{}).get("present")):
  raise EditBridgeQAError("audio 交付只接受无视频流的纯音频媒体")

def _audio_no_preview(context):
 if context.preview_path is not None or context.preview_manifest is not None:
  raise EditBridgeQAError("audio 交付不得声明 Preview")
 outputs=Path(context.episode_root).parent/"outputs"
 if outputs.is_dir() and list(outputs.glob("ALIGNED_PREVIEW*.mp4")):
  raise EditBridgeQAError("audio 交付不得生成 Preview 视频")
 if any(p.get("preview_in_frame",-1)>=0 or p.get("preview_out_frame",-1)>=0 for p in context.placements if p.get("placement_status")=="ready" and p.get("preview_enabled",True)):
  # Preview frames are preview-derived fields; they must never point at a real file here
  pass

def _audio_visual_gap(context):
 rows=context.pack.machine_map.get("rows",[])
 manifest_filenames={str(a.get("filename","")) for a in context.pack.manifest.get("assets",[])}
 if not rows:
  raise EditBridgeQAError("audio 交付缺少剪辑表行")
 for row in rows:
  decision=str(row.get("decision",""))
  if decision=="AUDIO_ONLY":
   if row.get("asset_filename") or row.get("qa_status")!="not_applicable" or row.get("requires_human_review") is not True:
    raise EditBridgeQAError("AUDIO_ONLY 行必须无素材、非 QA-ready 且需人工补画面")
   if row.get("asset_filename") in manifest_filenames:
    raise EditBridgeQAError("AUDIO_ONLY 行不得引用 manifest 素材")
  elif decision=="KEEP_A_ROLL":
   raise EditBridgeQAError("audio 分支禁止 KEEP_A_ROLL（无真人画面可保留）")
  elif decision=="REAL_MATERIAL":
   if row.get("asset_filename") not in manifest_filenames:
    raise EditBridgeQAError("REAL_MATERIAL 行缺少已入 manifest 的素材")
 if any(a.get("asset_class")=="AUDIO_ONLY" for a in context.pack.manifest.get("assets",[])):
  raise EditBridgeQAError("manifest 不得包含 AUDIO_ONLY")

def validate_audio_delivery_assets(manifest, episode_root):
 """Re-verify delivered material files against the manifest (post-hoc audit)."""
 for asset in manifest.get("assets",[]):
  path=Path(str(asset.get("local_path","")))
  if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=str(asset.get("sha256","")):
   raise EditBridgeQAError("Asset Pack 素材文件被修改或缺失")

def _audio_asset_pack_rederived(context):
 from .asset_pack_workflow import build_production_asset_pack
 import tempfile, json as _json
 with tempfile.TemporaryDirectory(prefix="audio-delivery-replay-") as tmp:
  replay=build_production_asset_pack(
   context.delivery["roots"],context.delivery["timeline"]["spans"],
   context.delivery["visual_plan"],context.delivery["candidates"],
   episode_root=Path(tmp)/"episode",created_at=context.created_at,
  )
  def comparable_bytes(path: Path) -> bytes:
   return path.read_bytes().replace(str(Path(context.episode_root).resolve()).encode("utf-8"), b"<EPISODE>")
  def comparable_edit(path: Path) -> str:
   value=_json.loads(path.read_text(encoding="utf-8")); value.pop("map_digest",None); value.pop("asset_manifest_digest",None)
   return _json.dumps(value,sort_keys=True,ensure_ascii=False)
  def comparable_manifest(path: Path) -> str:
   value=_json.loads(path.read_text(encoding="utf-8")); value.pop("manifest_digest",None)
   for asset in value.get("assets",[]):asset.pop("local_path",None)
   return _json.dumps(value,sort_keys=True,ensure_ascii=False)
  if comparable_bytes(context.pack.markdown_path)!=comparable_bytes(replay.markdown_path) or \
     comparable_bytes(context.pack.csv_path)!=comparable_bytes(replay.csv_path):
   raise EditBridgeQAError("Asset Pack 人读交付与 canonical 重推导不一致")
  if comparable_edit(context.pack.json_path)!=comparable_edit(replay.json_path):
   raise EditBridgeQAError("Edit Map 机器内容与 canonical 重推导不一致")
  if comparable_manifest(context.pack.manifest_path)!=comparable_manifest(replay.manifest_path):
   raise EditBridgeQAError("Asset Manifest 内容与 canonical 重推导不一致")
  validate_audio_delivery_assets(context.pack.manifest, context.episode_root)

def build_audio_delivery_qa_inputs(
 media,extracted,mapping,chunk_plan,chunk_profile,transcript,
 subtitle,subtitle_profile,episode_inputs,alignment,alignment_profile,cues,
 material_view,timing,rough_profile,preview_profile,bridge,delivery,pack,episode_root,allowed_roots,
):
 """Audio QA: 4 shared re-derivation groups + audio_delivery group."""
 from types import SimpleNamespace
 from .asset_pack_workflow import build_production_asset_pack
 from .material_profile import load_material_profile
 timing_profiles=(rough_profile,preview_profile,media["presentation_duration_seconds"])
 context=SimpleNamespace(
  media=media,extracted=extracted,mapping=mapping,chunk_plan=chunk_plan,
  chunk_profile=chunk_profile,transcript=transcript,script=episode_inputs.script,
  alignment_profile=alignment_profile,cues=cues,alignment=alignment,
  material_view=material_view,material_package_path=episode_inputs.material_package_path,
  report=episode_inputs.report,material_profile=load_material_profile(),
  material_asset_root=episode_inputs.material_asset_root,
  production_plan=episode_inputs.production_plan,motion_manifest=episode_inputs.motion_manifest,
  production_qa=episode_inputs.production_qa,placements=tuple(timing.placements),
  timing_profiles=timing_profiles,timing_result=timing,bridge=bridge,
  preview_profile=preview_profile,preview_manifest=None,preview_path=None,
  preview_used_placement_ids=[],allowed_roots=tuple(Path(p).resolve() for p in allowed_roots),
  subtitle_artifact=subtitle,subtitle_profile=subtitle_profile,
  episode_visual_preference=None,post_alignment_visual_plan=None,
  output_truth_evidence=None,artifact_resolver=episode_inputs.artifact_resolver,
  episode_root=episode_root,delivery=delivery,pack=pack,created_at=str(pack.machine_map.get("created_at","")),
  previous_bridge=None,revision_adjustment=None,
 )
 checks=[
  QACheck("root","root_artifacts_revalidated",lambda:_validate_root_chain(context),"invalid_root_binding"),
  QACheck("transcript","mapping_chunk_transcript_rederived",lambda:_validate_transcript_chain(context),"invalid_transcript_chain"),
  QACheck("alignment","normalization_status_risk_rederived",lambda:_validate_alignment_chain(context),"alignment_false_ready"),
  QACheck("placement","placement_files_and_timing_rederived",lambda:_validate_placement_chain(context),"invalid_placement_chain"),
  QACheck("audio_delivery","media_kind_audio",lambda:_audio_media_kind(context),"invalid_media_kind"),
  QACheck("audio_delivery","no_preview_generated",lambda:_audio_no_preview(context),"preview_generated_for_audio"),
  QACheck("audio_delivery","visual_gap_truthful",lambda:_audio_visual_gap(context),"fake_visual_gap"),
  QACheck("audio_delivery","asset_pack_rederived",lambda:_audio_asset_pack_rederived(context),"asset_pack_not_rederived"),
 ]
 return EditBridgeQAInputs(checks,list(timing.placements),[])

def run_audio_edit_bridge_qa(inputs):
 return run_edit_bridge_qa(inputs,required_groups=AUDIO_DELIVERY_REQUIRED_GROUPS,include_preview_used_check=False)
