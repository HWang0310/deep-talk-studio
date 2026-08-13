"""Safe Remotion aligned-preview staging and renderer adapter."""
import hashlib,json,re,shutil
from copy import deepcopy
from pathlib import Path
from .base import AlignedPreviewProject

class AlignedPreviewError(ValueError):pass
def _inside(path,roots):
 for root in roots:
  try:path.relative_to(Path(root).resolve());return True
  except ValueError:pass
 return False
def _stage(source,target,roots,size,digest):
 path=Path(source).resolve()
 if not _inside(path,roots) or path.is_symlink() or not path.is_file() or path.stat().st_size!=int(size) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise AlignedPreviewError("Preview asset path/SHA 无效")
 shutil.copyfile(path,target);return target
class RemotionAlignedPreviewRenderer:
 def prepare_project(self,bridge,media,allowed_roots,project_root):
  if not re.fullmatch(r"[A-Za-z0-9._-]+",bridge["bridge_id"]):raise AlignedPreviewError("Bridge ID 无效")
  target=Path(project_root).resolve()/bridge["bridge_id"]/f"r{bridge['revision']:04d}"
  if target.exists():raise AlignedPreviewError("Aligned Preview project 已存在")
  public=target/"public/assets";public.mkdir(parents=True)
  ar_name="VP0000"+Path(media["immutable_local_path"]).suffix.lower();staged=[_stage(media["immutable_local_path"],public/ar_name,allowed_roots,media["byte_size"],media["sha256"])]
  payload={"media_duration_seconds":media["presentation_duration_seconds"],"placements":[{"placement_id":"VP0000","source_kind":"clean_aroll","asset_path":f"assets/{ar_name}","preview_in_frame":0,"preview_out_frame":None}]};ids=["VP0000"]
  for p in bridge.get("visual_placements",[]):
   if p.get("placement_status")!="ready":continue
   suffix=Path(p["local_path"]).suffix.lower();name=p["placement_id"]+suffix;staged.append(_stage(p["local_path"],public/name,allowed_roots,p["byte_size"],p["sha256"]));ids.append(p["placement_id"])
   payload["placements"].append({"placement_id":p["placement_id"],"source_kind":p["source_kind"],"asset_path":f"assets/{name}","preview_in_frame":p["preview_in_frame"],"preview_out_frame":p["preview_out_frame"],"source_clip_in_seconds":p.get("source_clip_in_seconds","")})
  text=json.dumps(payload,ensure_ascii=False,indent=2)+"\n";payload_path=target/"public/bridge.json";payload_path.write_text(text,encoding="utf-8")
  return AlignedPreviewProject(target,payload_path,tuple(ids),tuple(staged),text)
 def validate_project(self,project):
  if not project.payload_path.is_file() or json.loads(project.payload_text)!=json.loads(project.payload_path.read_text()):raise AlignedPreviewError("Aligned Preview project payload 无效")
