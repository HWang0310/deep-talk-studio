"""Unified source bindings and timing derivation for visual placements."""

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

from .canonical_time import format_canonical_timecode, format_preview_frame_timecode, preview_frame


class EditBridgePlanningError(ValueError): pass


def _inside(path, roots):
    for root in roots:
        try: path.relative_to(Path(root).resolve()); return True
        except ValueError: pass
    return False


def _base_fields():
    return {
        "artifact_version":"visual-placement/1","safe_filename":"","beat_id":"","cue_id":"","scene_id":"",
        "visual_role":"base","asset_type":"clean_aroll","placement_anchor":"",
        "semantic_in_seconds":"","semantic_out_seconds":"","semantic_duration_seconds":"",
        "canonical_in_timecode":"","canonical_out_timecode":"","natural_duration_seconds":"","target_duration_seconds":"",
        "source_clip_in_seconds":"","source_clip_out_seconds":"","preview_effective_in_seconds":"","preview_effective_out_seconds":"",
        "preview_in_frame":-1,"preview_out_frame":-1,"preview_in_frame_timecode":"","preview_out_frame_timecode":"",
        "preview_adjustment_id":"","layout_mode":"full_screen_broll","layout_source":"profile_default",
        "preview_enabled":True,
        "audio_policy":"mute_source_keep_aroll","placement_status":"unplaced","timing_status":"clear",
        "duration_status":"unknown","confidence":"none","notes":[],"timing_conflict_ids":[],
        "local_path":"","byte_size":0,"sha256":"",
    }


def build_base_aroll_placement(media):
    duration=str(media["presentation_duration_seconds"]); p=_base_fields()
    p.update(placement_id="VP0000",track_order=0,source_kind="clean_aroll",source_id=media["media_id"],
      safe_filename=media.get("safe_original_filename",""),semantic_in_seconds="0",semantic_out_seconds=duration,
      semantic_duration_seconds=duration,canonical_in_timecode=format_canonical_timecode(0),canonical_out_timecode=format_canonical_timecode(duration),
      natural_duration_seconds=duration,target_duration_seconds=duration,layout_mode="full_screen_aroll",audio_policy="clean_aroll_primary",
      placement_status="ready",duration_status="natural",confidence="high",local_path=media.get("immutable_local_path",""),
      byte_size=int(media.get("byte_size",0)),sha256=media.get("sha256",""))
    return p


def _cue(alignment,cue_id): return next((c for c in alignment.get("cue_timeline",[]) if c["cue_id"]==cue_id),None)


def _verified(path,size,digest,roots):
    if not path: return False
    p=Path(path).resolve()
    return _inside(p,roots) and p.is_file() and not p.is_symlink() and p.stat().st_size==int(size) and hashlib.sha256(p.read_bytes()).hexdigest()==digest


def _semantic(p,cue):
    if not cue or not cue.get("actual_start_seconds") or not cue.get("actual_end_seconds"): return
    start=Decimal(cue["actual_start_seconds"]); end=Decimal(cue["actual_end_seconds"])
    p.update(beat_id=cue["beat_id"],cue_id=cue["cue_id"],placement_anchor=cue.get("placement_anchor",""),
      semantic_in_seconds=str(start),semantic_out_seconds=str(end),semantic_duration_seconds=str(end-start),
      canonical_in_timecode=format_canonical_timecode(start),canonical_out_timecode=format_canonical_timecode(end),target_duration_seconds=str(end-start),confidence=cue.get("confidence","none"))


def build_visual_placements(alignment,material_view,production_plan,motion_manifest,media,allowed_roots,production_qa=None,*,artifact_resolver=None):
    result=[]
    for item in material_view.get("items",[]):
        p=_base_fields(); p.update(placement_id=f"VP{len(result)+1:04d}",track_order=len(result)+1,source_id=item["source_id"],
          safe_filename=Path(item.get("local_path","")).name,visual_role="material",asset_type=item.get("asset_type","document_screenshot"),
          local_path=item.get("local_path",""),byte_size=int(item.get("byte_size",0)),sha256=item.get("sha256",""))
        cue=_cue(alignment,(item.get("cue_ids") or [""])[0]); _semantic(p,cue)
        is_video=item.get("asset_type")=="video_clip_reference"
        p["source_kind"]="real_video" if is_video else "real_image"
        if cue and cue.get("placement_status")=="coarse": p["placement_status"]="coarse"
        elif cue and cue.get("placement_status")!="aligned": p["placement_status"]="needs_review" if cue else "unplaced"
        elif item.get("production_status")=="missing_asset": p["placement_status"]="missing_asset"
        elif item.get("production_status")!="ready" or not _verified(p["local_path"],p["byte_size"],p["sha256"],allowed_roots): p["placement_status"]="rejected"
        elif is_video:
            ref=item.get("video_reference",{}); start=ref.get("start_seconds",0); end=ref.get("end_seconds",0)
            if end>start:
                p.update(placement_status="ready",source_clip_in_seconds=str(start),source_clip_out_seconds=str(end),natural_duration_seconds=str(Decimal(str(end))-Decimal(str(start))),duration_status="natural")
            else: p["placement_status"]="clip_selection_needed"
        else: p.update(placement_status="ready",layout_mode="full_screen_broll",duration_status="natural")
        result.append(p)
    if motion_manifest:
        motion_observations={}
        if production_qa is None:
            if motion_manifest.get("qa_status")!="ready": raise EditBridgePlanningError("Motion Manifest QA 未通过")
            if artifact_resolver is not None:
                try:
                    motion_observations={
                        asset.get("motion_asset_id"):artifact_resolver.resolve_motion_asset(production_plan,asset)
                        for asset in motion_manifest.get("assets",[])
                    }
                except ValueError as exc:
                    raise EditBridgePlanningError(f"Motion Asset runtime resolution 失败：{exc}") from None
        else:
            from .production_qa import validate_motion_manifest,validate_production_qa
            motion_observations=validate_motion_manifest(motion_manifest,production_plan,artifact_resolver=artifact_resolver)
            validate_production_qa(production_qa,production_plan,motion_manifest)
            if production_qa.get("package_gate_status") not in {"pass","warnings"}:raise EditBridgePlanningError("Production QA 未通过")
        scenes={s["scene_id"]:s for s in production_plan.get("scenes",[])}
        for asset in motion_manifest.get("assets",[]):
            scene=scenes.get(asset.get("scene_id")); observation=motion_observations.get(asset.get("motion_asset_id")) if artifact_resolver is not None else None; asset_path=str(observation.resolved_path) if observation is not None else asset.get("local_path") or asset.get("output_path","")
            if asset.get("asset_kind") and asset.get("asset_kind")!="motion_clip":continue
            if scene is not None and "source_visual_ids" in scene and not scene.get("source_visual_ids"):continue
            asset_ready=asset.get("qa_status")=="ready" if production_qa is None else True
            if not scene or not asset_ready or not _verified(asset_path,asset.get("byte_size",0),asset.get("sha256",""),allowed_roots):
                raise EditBridgePlanningError("Motion Asset 身份、QA 或 SHA 无效")
            cue=_cue(alignment,scene.get("cue_id") or (scene.get("cue_ids") or [""])[0]); p=_base_fields(); _semantic(p,cue)
            p.update(placement_id=f"VP{len(result)+1:04d}",track_order=len(result)+1,source_kind="original_motion",source_id=asset["scene_id"],
              scene_id=asset["scene_id"],safe_filename=Path(asset_path).name,visual_role="motion",asset_type="original_motion",
              natural_duration_seconds=str(asset["duration_seconds"]),layout_mode="full_screen_visual",layout_source="production_plan",
              placement_status="ready" if cue and cue.get("placement_status")=="aligned" else "needs_review",duration_status="natural",
              local_path=asset_path,byte_size=asset["byte_size"],sha256=asset["sha256"])
            result.append(p)
    return tuple(result)


def _plan_semantic(placement, opportunity):
    """Copy only already safe, global-projection time from a Visual Plan."""
    placement.update(
        beat_id=opportunity["beat_id"], placement_anchor=opportunity.get("semantic_target", ""),
        semantic_in_seconds=opportunity.get("actual_in_seconds", ""),
        semantic_out_seconds=opportunity.get("actual_out_seconds", ""),
        semantic_duration_seconds=opportunity.get("duration_seconds", ""),
        target_duration_seconds=opportunity.get("duration_seconds", ""), confidence=opportunity.get("confidence", "none"),
    )
    if placement["semantic_in_seconds"] and placement["semantic_out_seconds"]:
        placement["canonical_in_timecode"] = format_canonical_timecode(placement["semantic_in_seconds"])
        placement["canonical_out_timecode"] = format_canonical_timecode(placement["semantic_out_seconds"])


def build_visual_plan_placements(visual_plan, material_view, production_plan, motion_manifest, allowed_roots, *, artifact_resolver=None):
    """Turn a reviewed Post-Alignment Visual Plan into safe existing-source placements.

    The plan owns semantic timing. This adapter never projects, extends, or guesses time.
    """
    materials = {item.get("source_id"): item for item in material_view.get("items", [])}
    scenes = {item.get("scene_id"): item for item in production_plan.get("scenes", [])}
    motion_by_scene = {
        item.get("scene_id"): item for item in motion_manifest.get("assets", [])
        if item.get("asset_kind", "motion_clip") == "motion_clip"
    }
    result = []
    for opportunity in visual_plan.get("opportunities", []):
        binding = opportunity.get("source_binding", {})
        placement = _base_fields()
        placement.update(
            placement_id=f"VP{len(result) + 1:04d}", track_order=len(result) + 1,
            visual_role=opportunity.get("visual_role", "context"), notes=[
                f"post_alignment_visual_plan:{opportunity.get('opportunity_id', '')}"
            ],
        )
        _plan_semantic(placement, opportunity)
        if opportunity.get("timing_status") != "ready" or opportunity.get("placement_status") != "ready":
            # An unplaced opportunity is still an auditable request for a
            # specific reviewed source.  Keep its typed source identity so it
            # remains schema-valid and cannot silently become a generic blank
            # placement in an Edit Bridge.
            if opportunity.get("visual_kind") == "original_motion":
                scene_id = binding.get("scene_id", "")
                if not scene_id and binding.get("visual_id"):
                    matching_scenes = [
                        candidate["scene_id"] for candidate in production_plan.get("scenes", [])
                        if binding["visual_id"] in candidate.get("source_visual_ids", [])
                    ]
                    if len(matching_scenes) == 1:
                        scene_id = matching_scenes[0]
                placement.update(
                    source_kind="original_motion", source_id=scene_id or binding.get("visual_id", ""),
                    scene_id=scene_id, asset_type="original_motion", layout_mode="full_screen_visual",
                    layout_source="production_plan", audio_policy="mute_source_keep_aroll",
                )
            elif opportunity.get("visual_kind") == "real_material":
                placement.update(
                    source_kind="real_image", source_id=binding.get("material_id", ""),
                    asset_type="document_screenshot", layout_mode="full_screen_broll",
                    audio_policy="mute_source_keep_aroll",
                )
            placement["placement_status"] = "unplaced"
            result.append(placement)
            continue
        if opportunity.get("visual_kind") == "real_material":
            material_id = binding.get("material_id", "")
            item = materials.get(material_id)
            if item is None:
                placement.update(source_kind="real_image", source_id=material_id, placement_status="missing_asset")
            else:
                is_video = item.get("asset_type") == "video_clip_reference"
                placement.update(
                    source_kind="real_video" if is_video else "real_image", source_id=material_id,
                    safe_filename=Path(item.get("local_path", "")).name, asset_type=item.get("asset_type", "document_screenshot"),
                    local_path=item.get("local_path", ""), byte_size=int(item.get("byte_size", 0)), sha256=item.get("sha256", ""),
                    layout_mode="full_screen_broll", duration_status="natural",
                )
                if item.get("production_status") != "ready":
                    placement["placement_status"] = "missing_asset"
                elif not _verified(placement["local_path"], placement["byte_size"], placement["sha256"], allowed_roots):
                    placement["placement_status"] = "rejected"
                elif is_video:
                    reference = item.get("video_reference", {})
                    start, end = reference.get("start_seconds", 0), reference.get("end_seconds", 0)
                    if end > start:
                        placement.update(placement_status="ready", source_clip_in_seconds=str(start), source_clip_out_seconds=str(end), natural_duration_seconds=str(Decimal(str(end)) - Decimal(str(start))))
                    else:
                        placement["placement_status"] = "clip_selection_needed"
                else:
                    placement["placement_status"] = "ready"
        elif opportunity.get("visual_kind") == "original_motion":
            scene_id = binding.get("scene_id", "")
            if not scene_id and binding.get("visual_id"):
                matching_scenes = [
                    candidate["scene_id"] for candidate in production_plan.get("scenes", [])
                    if binding["visual_id"] in candidate.get("source_visual_ids", [])
                ]
                if len(matching_scenes) == 1:
                    scene_id = matching_scenes[0]
            asset = motion_by_scene.get(scene_id)
            scene = scenes.get(scene_id)
            if asset is not None and artifact_resolver is not None:
                try:
                    asset_path = str(artifact_resolver.resolve_motion_asset(production_plan, asset).resolved_path)
                except ValueError as exc:
                    raise EditBridgePlanningError(f"Motion Asset runtime resolution 失败：{exc}") from None
            else:
                asset_path = (asset or {}).get("local_path") or (asset or {}).get("output_path", "")
            placement.update(
                source_kind="original_motion", source_id=scene_id, scene_id=scene_id,
                safe_filename=Path(asset_path).name, asset_type="original_motion", local_path=asset_path,
                byte_size=int((asset or {}).get("byte_size", 0)), sha256=(asset or {}).get("sha256", ""),
                natural_duration_seconds=str((asset or {}).get("duration_seconds", "")), layout_mode="full_screen_visual",
                layout_source="production_plan", duration_status="natural",
            )
            if scene is None or asset is None or asset.get("qa_status") != "ready":
                placement["placement_status"] = "missing_asset"
            elif not _verified(placement["local_path"], placement["byte_size"], placement["sha256"], allowed_roots):
                placement["placement_status"] = "rejected"
            else:
                placement["placement_status"] = "ready"
        else:
            # Hybrid is represented as separate Material and Motion opportunities so neither
            # source gets a fabricated composite timing or mixed provenance record.
            placement["placement_status"] = "unplaced"
        result.append(placement)
    return tuple(result)


@dataclass(frozen=True)
class PlacementTimingResult:
    placements: Tuple[dict,...]; conflicts: Tuple[dict,...]; adjustments: Tuple[dict,...]


def _conflict(conflicts, kind, placements, klass, summary, policy):
    value={"artifact_version":"timing-conflict/1","conflict_id":f"TC{len(conflicts)+1:04d}","conflict_type":kind,
      "placement_ids":[p["placement_id"] for p in placements],"conflict_class":klass,"severity":"blocking" if klass=="selection_blocker" else "warning",
      "human_summary":summary,"preview_policy":policy,"resolution_status":"unresolved" if klass=="selection_blocker" else "preview_adjusted"}
    conflicts.append(value)
    for p in placements: p.setdefault("timing_conflict_ids",[]).append(value["conflict_id"])
    return value


def _adjust(adjustments,p,kind,reason,old_in,old_out,new_in,new_out,provenance):
    value={"artifact_version":"preview-adjustment/1","adjustment_id":f"PA{len(adjustments)+1:04d}","placement_id":p["placement_id"],
      "adjustment_type":kind,"reason":reason,"original_in_seconds":str(old_in),"original_out_seconds":str(old_out),
      "preview_in_seconds":str(new_in),"preview_out_seconds":str(new_out),"provenance":provenance}
    adjustments.append(value); p["preview_adjustment_id"]=value["adjustment_id"]


def derive_placement_timing(placements, profiles, user_adjustments=()):
    rough,preview,media_duration=profiles; duration=Decimal(str(media_duration)); result=[deepcopy(p) for p in placements]
    conflicts=[]; adjustments=[]; overrides={a["placement_id"]:a for a in user_adjustments}
    ready=[]
    for p in result:
        p.setdefault("timing_conflict_ids",[]); p.setdefault("notes",[]); p.setdefault("timing_status","clear"); p.setdefault("duration_status","unknown"); p.setdefault("preview_adjustment_id",""); p.setdefault("preview_enabled",True)
        if p.get("placement_status")!="ready": continue
        try: start=Decimal(p["semantic_in_seconds"]); end=Decimal(p["semantic_out_seconds"])
        except Exception: p["placement_status"]="rejected"; p["timing_status"]="blocking"; continue
        if start<0 or end<=start or end>duration:
            p["placement_status"]="rejected"; p["timing_status"]="blocking"
            _conflict(conflicts,"out_of_media_bounds",[p],"selection_blocker","可视窗口超出真人底轨。","reject_without_clamp"); continue
        p["semantic_duration_seconds"]=str(end-start); p["target_duration_seconds"]=str(end-start)
        p["canonical_in_timecode"]=format_canonical_timecode(start); p["canonical_out_timecode"]=format_canonical_timecode(end)
        effective_end=end
        natural=Decimal(p["natural_duration_seconds"]) if p.get("natural_duration_seconds") else None
        if p["source_kind"]=="real_image" and end-start>Decimal(str(rough["still_exposure_seconds"])):
            effective_end=start+Decimal(str(rough["still_exposure_seconds"])); p["duration_status"]="long_still_warning"; p["timing_status"]="warning"
            _adjust(adjustments,p,"still_exposure_capped","长静帧粗剪曝光上限",start,end,start,effective_end,"rough_cut_profile")
        if natural is not None and natural != end-start:
            longer=natural>end-start; prefix="motion" if p["source_kind"]=="original_motion" else "source_clip"
            kind=f"{prefix}_{'longer' if longer else 'shorter'}_than_semantic_window"
            p["timing_status"]="warning"; p["duration_status"]="asset_longer" if longer else "asset_shorter"
            _conflict(conflicts,kind,[p],"timing_warning","素材自然时长与口播语义窗口不同。","trim_preview_tail" if longer else "return_to_aroll")
            if not longer:
                effective_end=min(effective_end,start+natural)
        if p["placement_id"] in overrides:
            override=overrides[p["placement_id"]]; new_end=min(end,start+Decimal(str(override["duration_seconds"])))
            _adjust(adjustments,p,"user_duration_override",override["reason"],start,end,start,new_end,"user_feedback"); effective_end=new_end
        p["preview_effective_in_seconds"]=str(start); p["preview_effective_out_seconds"]=str(effective_end); ready.append((start,p))
    ready.sort(key=lambda pair: pair[0])
    for index,(start,p) in enumerate(ready):
        same=[other for other_start,other in ready if other_start==start]
        if len(same)>1 and p["placement_status"]=="ready":
            if not any(c["conflict_type"]=="same_start_selection_ambiguity" and p["placement_id"] in c["placement_ids"] for c in conflicts):
                _conflict(conflicts,"same_start_selection_ambiguity",same,"selection_blocker","两个画面的语义起点完全相同。","show_aroll")
            for other in same: other["placement_status"]="needs_review"; other["timing_status"]="blocking"
        if index+1<len(ready):
            next_start,next_p=ready[index+1]; current_end=Decimal(p.get("preview_effective_out_seconds") or p["semantic_out_seconds"])
            if next_start>start and next_start<current_end:
                old=current_end; p["preview_effective_out_seconds"]=str(next_start); p["timing_status"]="warning"
                _conflict(conflicts,"visual_overlap",[p,next_p],"timing_warning","后开始的可用画面接管上层。","later_ready_takes_over")
                _adjust(adjustments,p,"overlap_takeover","后开始画面接管",start,old,start,next_start,"overlap_policy")
    fps=preview["fps"]
    for p in result:
        if p.get("placement_status")!="ready" or not p.get("preview_enabled",True):
            p.update(preview_in_frame=-1,preview_out_frame=-1,preview_in_frame_timecode="",preview_out_frame_timecode="")
            continue
        start=Decimal(p["preview_effective_in_seconds"]); end=Decimal(p["preview_effective_out_seconds"])
        inf=preview_frame(start,fps); outf=preview_frame(end,fps); p["preview_in_frame"]=inf; p["preview_out_frame"]=outf
        p["preview_in_frame_timecode"]="Preview "+format_preview_frame_timecode(inf,fps); p["preview_out_frame_timecode"]="Preview "+format_preview_frame_timecode(outf,fps)
    return PlacementTimingResult(tuple(result),tuple(conflicts),tuple(adjustments))


def _bridge_digest(value):
    payload=deepcopy(dict(value)); payload.pop("package_digest",None)
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()).hexdigest()


def build_edit_bridge(root_bindings,placements,conflicts,adjustments,alignment_gaps,*,bridge_id,created_at,revision=1,previous_revision=0):
    legacy_bindings={"narration_media_digest","extracted_audio_digest","timestamp_mapping_digest","chunk_plan_digest","transcript_digest","script_content_digest","research_digest","material_package_digest","material_view_digest","production_plan_digest","motion_manifest_digest","production_qa_digest","alignment_digest","alignment_profile_digest","rough_cut_profile_digest","aligned_preview_profile_digest"}
    subtitle_bindings={"subtitle_artifact_digest","subtitle_profile_digest"}
    visual_plan_bindings={"episode_visual_preference_digest","post_alignment_visual_plan_digest"}
    accepted={frozenset(legacy_bindings),frozenset(legacy_bindings|subtitle_bindings),frozenset(legacy_bindings|visual_plan_bindings),frozenset(legacy_bindings|subtitle_bindings|visual_plan_bindings)}
    if frozenset(root_bindings) not in accepted or not all(root_bindings.values()): raise EditBridgePlanningError("Edit Bridge root bindings 不完整")
    for p in placements:
        if p.get("placement_status")!="ready" and (p.get("preview_in_frame",-1)>=0 or p.get("preview_out_frame",-1)>=0):
            raise EditBridgePlanningError("非 ready Placement 不得携带 Preview frame")
    state="warnings" if conflicts or any(p.get("placement_status")!="ready" for p in placements) else "not_run"
    bridge={"artifact_version":"edit-bridge/1","bridge_id":bridge_id,"revision":revision,"previous_revision":previous_revision,"created_at":created_at,
      "root_bindings":deepcopy(dict(root_bindings)),"visual_placements":deepcopy(list(placements)),"timing_conflicts":deepcopy(list(conflicts)),
      "preview_adjustments":deepcopy(list(adjustments)),"alignment_gaps":[{"gap_id":g["gap_id"],"gap_type":g["gap_type"],"reason_code":g["reason_code"]} for g in alignment_gaps],"qa_state":state}
    bridge["package_digest"]=_bridge_digest(bridge); return bridge
