"""Unified source bindings and timing derivation for visual placements."""

import hashlib
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


def build_visual_placements(alignment,material_view,production_plan,motion_manifest,media,allowed_roots):
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
        if motion_manifest.get("qa_status")!="ready": raise EditBridgePlanningError("Motion Manifest QA 未通过")
        scenes={s["scene_id"]:s for s in production_plan.get("scenes",[])}
        for asset in motion_manifest.get("assets",[]):
            scene=scenes.get(asset.get("scene_id"))
            if not scene or asset.get("qa_status")!="ready" or not _verified(asset.get("local_path",""),asset.get("byte_size",0),asset.get("sha256",""),allowed_roots):
                raise EditBridgePlanningError("Motion Asset 身份、QA 或 SHA 无效")
            cue=_cue(alignment,(scene.get("cue_ids") or [""])[0]); p=_base_fields(); _semantic(p,cue)
            p.update(placement_id=f"VP{len(result)+1:04d}",track_order=len(result)+1,source_kind="original_motion",source_id=asset["scene_id"],
              scene_id=asset["scene_id"],safe_filename=Path(asset["local_path"]).name,visual_role="motion",asset_type="original_motion",
              natural_duration_seconds=str(asset["duration_seconds"]),layout_mode="full_screen_visual",layout_source="production_plan",
              placement_status="ready" if cue and cue.get("placement_status")=="aligned" else "needs_review",duration_status="natural",
              local_path=asset["local_path"],byte_size=asset["byte_size"],sha256=asset["sha256"])
            result.append(p)
    return tuple(result)


@dataclass(frozen=True)
class PlacementTimingResult:
    placements: Tuple[dict,...]; conflicts: Tuple[dict,...]; adjustments: Tuple[dict,...]
