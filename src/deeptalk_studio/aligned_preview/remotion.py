"""Safe Remotion aligned-preview staging and renderer adapter."""
import hashlib,json,os,re,shutil,subprocess
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from .base import AlignedPreviewProject,AlignedPreviewRender

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
 def __init__(self,browser_executable=None):
  self.browser_executable=browser_executable
 def prepare_project(self,bridge,media,subtitle_artifact,subtitle_profile,allowed_roots,project_root):
  if not re.fullmatch(r"[A-Za-z0-9._-]+",bridge["bridge_id"]):raise AlignedPreviewError("Bridge ID 无效")
  target=Path(project_root).resolve()/bridge["bridge_id"]/f"r{bridge['revision']:04d}"
  if target.exists():raise AlignedPreviewError("Aligned Preview project 已存在")
  template=Path(__file__).resolve().parents[3]/"renderer_templates/aligned_preview_remotion"
  if not (template/"package.json").is_file():raise AlignedPreviewError("Aligned Preview Remotion template 缺失")
  shutil.copytree(template,target,ignore=shutil.ignore_patterns("node_modules",".git"))
  public=target/"public/assets";public.mkdir(parents=True,exist_ok=True)
  ar_name="VP0000"+Path(media["immutable_local_path"]).suffix.lower();staged=[_stage(media["immutable_local_path"],public/ar_name,allowed_roots,media["byte_size"],media["sha256"])]
  if subtitle_artifact.get("narration_media_id")!=media.get("media_id") or subtitle_artifact.get("narration_media_sha256")!=media.get("sha256") or subtitle_artifact.get("profile_digest")!=subtitle_profile.get("profile_digest") or not subtitle_artifact.get("cues"):
   raise AlignedPreviewError("Subtitle Artifact 与 Preview roots 不一致")
  payload={"media_duration_seconds":media["presentation_duration_seconds"],"subtitle_artifact_digest":subtitle_artifact["artifact_digest"],"subtitle_profile":subtitle_profile,"subtitle_cues":subtitle_artifact["cues"],"subtitles_enabled":True,"placements":[{"placement_id":"VP0000","source_kind":"clean_aroll","asset_path":f"assets/{ar_name}","preview_in_frame":0,"preview_out_frame":None}]};ids=["VP0000"]
  for p in bridge.get("visual_placements",[]):
   if p.get("placement_status")!="ready" or not p.get("preview_enabled",True):continue
   suffix=Path(p["local_path"]).suffix.lower();name=p["placement_id"]+suffix;staged.append(_stage(p["local_path"],public/name,allowed_roots,p["byte_size"],p["sha256"]));ids.append(p["placement_id"])
   payload["placements"].append({"placement_id":p["placement_id"],"source_kind":p["source_kind"],"asset_path":f"assets/{name}","preview_in_frame":p["preview_in_frame"],"preview_out_frame":p["preview_out_frame"],"source_clip_in_seconds":p.get("source_clip_in_seconds","")})
  text=json.dumps(payload,ensure_ascii=False,indent=2)+"\n";payload_path=target/"public/bridge.json";payload_path.write_text(text,encoding="utf-8")
  return AlignedPreviewProject(target,payload_path,tuple(ids),tuple(staged),text,True,subtitle_artifact["artifact_digest"])
 def validate_project(self,project):
  if not project.payload_path.is_file() or json.loads(project.payload_text)!=json.loads(project.payload_path.read_text()):raise AlignedPreviewError("Aligned Preview project payload 无效")
  payload=json.loads(project.payload_text)
  if not project.subtitles_enabled or not payload.get("subtitles_enabled") or payload.get("subtitle_artifact_digest")!=project.subtitle_artifact_digest or not payload.get("subtitle_cues"):raise AlignedPreviewError("Aligned Preview 没有启用当前字幕")
 def render_visual(self,project,output_path):
  """Install the locked project and execute a real visual-only Remotion render."""
  self.validate_project(project);output=Path(output_path).resolve()
  if output.exists():raise AlignedPreviewError("Aligned Preview visual 输出已存在")
  output.parent.mkdir(parents=True,exist_ok=True)
  _run(["npm","ci","--ignore-scripts"],cwd=project.project_dir)
  command=["npx","remotion","render","src/index.ts","AlignedPreview",str(output),"--codec=h264","--pixel-format=yuv420p","--concurrency=1","--muted"]
  browser=self.browser_executable or os.getenv("DEEPTALK_REMOTION_BROWSER_EXECUTABLE")
  if not browser:
   system_chrome=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
   browser=str(system_chrome) if system_chrome.is_file() else None
  if browser:
   executable=Path(browser).resolve()
   if not executable.is_file() or not os.access(executable,os.X_OK):raise AlignedPreviewError("Remotion browser executable 无效")
   command.append(f"--browser-executable={executable}")
  _run(command,cwd=project.project_dir)
  if not output.is_file() or output.stat().st_size<=0:raise AlignedPreviewError("Remotion 未生成视觉预览")
  streams=json.loads(_run(["ffprobe","-v","error","-show_streams","-of","json",str(output)]).stdout).get("streams",[])
  if any(stream.get("codec_type")=="audio" for stream in streams):raise AlignedPreviewError("Remotion visual-only 中间片不应包含音轨")
  return AlignedPreviewRender(output,"locked npm ci + remotion visual-only render",hashlib.sha256(output.read_bytes()).hexdigest(),output.stat().st_size)

@dataclass(frozen=True)
class AudioPresentationEvidence:
 audio_start_seconds:float;audio_end_seconds:float;duration_seconds:float;internal_gaps:tuple;audio_stream_count:int;tolerance_seconds:float;codec:str;time_base:str;evidence_digest:str
@dataclass(frozen=True)
class AudioMuxResult:
 output_path:Path;command_summary:str;audio_stream_count:int;duration_seconds:float;audio_presentation_start_seconds:float;audio_presentation_end_seconds:float;internal_gaps:tuple;tolerance_seconds:float;codec_copy:bool;sha256:str;byte_size:int

def _run(command,cwd=None):
 result=subprocess.run(command,capture_output=True,text=True,cwd=cwd)
 if result.returncode:raise AlignedPreviewError((result.stderr or result.stdout)[-1200:])
 return result
def probe_audio_presentation(path):
 raw=json.loads(_run(["ffprobe","-v","error","-show_format","-show_streams","-show_packets","-of","json",str(path)]).stdout);streams=raw.get("streams",[]);audio=[s for s in streams if s.get("codec_type")=="audio"]
 if not audio:raise AlignedPreviewError("Preview 没有 Clean A-roll 音轨")
 stream=audio[0];packets=[p for p in raw.get("packets",[]) if p.get("codec_type")=="audio"]
 start=float(stream.get("start_time",packets[0].get("pts_time",0)));duration=float(stream.get("duration",raw.get("format",{}).get("duration",0)));end=start+duration
 silence=_run(["ffmpeg","-v","info","-nostdin","-i",str(path),"-map","0:a:0","-af","silencedetect=noise=-60dB:d=0.05","-f","null","-"]).stderr
 starts=[float(x) for x in re.findall(r"silence_start: ([0-9.]+)",silence)];ends=[float(x) for x in re.findall(r"silence_end: ([0-9.]+)",silence)];gaps=tuple((round(a,6),round(b,6)) for a,b in zip(starts,ends) if b-a>=0.05)
 rate=int(stream.get("sample_rate",48000) or 48000);frame=(int(stream.get("frame_size",1024) or 1024)/rate);tb=stream.get("time_base","1/48000");num,den=(int(x) for x in tb.split("/"));tolerance=max(1/30,num/den,frame)
 payload={"start":start,"end":end,"duration":duration,"gaps":gaps,"count":len(audio),"codec":stream.get("codec_name","")};digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
 return AudioPresentationEvidence(start,end,duration,gaps,len(audio),tolerance,stream.get("codec_name",""),tb,digest)
def validate_preview_audio_presentation(source,preview,tolerance):
 tol=float(tolerance)
 if preview.audio_stream_count!=1 or abs(source.audio_start_seconds-preview.audio_start_seconds)>tol or abs(source.audio_end_seconds-preview.audio_end_seconds)>tol:raise AlignedPreviewError("Preview audio presentation start/end 与 Clean A-roll 不一致")
 if len(source.internal_gaps)!=len(preview.internal_gaps):raise AlignedPreviewError("Preview internal audio gap 数量不一致")
 for left,right in zip(source.internal_gaps,preview.internal_gaps):
  if any(abs(a-b)>tol for a,b in zip(left,right)):raise AlignedPreviewError("Preview internal audio gap 被移动或压平")
def mux_clean_aroll_audio(visual_path,media,output_path):
 source=Path(media["immutable_local_path"]);output=Path(output_path)
 if output.exists():raise AlignedPreviewError("Aligned Preview 输出已存在")
 output.parent.mkdir(parents=True,exist_ok=True)
 if hashlib.sha256(source.read_bytes()).hexdigest()!=media["sha256"]:raise AlignedPreviewError("Clean A-roll SHA 与 Media 绑定不一致")
 src=probe_audio_presentation(source);reported=media["presentation_evidence"]
 evidence_tol=max(src.tolerance_seconds,1/30)
 if abs(src.audio_start_seconds-float(reported["audio_presentation_start_seconds"]))>evidence_tol or abs(src.audio_end_seconds-float(reported["audio_presentation_end_seconds"]))>evidence_tol:raise AlignedPreviewError("Clean A-roll presentation evidence 无法重推导")
 codec_copy=src.codec in {"aac","mp3"};audio_args=["copy"] if codec_copy else ["aac","-b:a","192k"]
 # Preserve input presentation timestamps. Conversion is codec-only: no trim,
 # reset, normalization, tempo, silence removal, concatenation or -shortest.
 command=["ffmpeg","-v","error","-nostdin","-copyts","-i",str(visual_path),"-copyts","-i",str(source),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a",*audio_args,"-avoid_negative_ts","disabled",str(output)]
 _run(command);preview=probe_audio_presentation(output);tol=max(src.tolerance_seconds,preview.tolerance_seconds,1/30);validate_preview_audio_presentation(src,preview,tol)
 summary="ffmpeg presentation-preserving stream copy" if codec_copy else "ffmpeg presentation-preserving AAC conversion"
 return AudioMuxResult(output,summary,preview.audio_stream_count,float(json.loads(_run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(output)]).stdout)["format"]["duration"]),preview.audio_start_seconds,preview.audio_end_seconds,preview.internal_gaps,tol,codec_copy,hashlib.sha256(output.read_bytes()).hexdigest(),output.stat().st_size)
def build_aligned_preview_manifest(path,bridge,profile,media,used_placement_ids,subtitle_artifact,subtitle_profile,subtitles_enabled):
 value={"artifact_version":"aligned-preview-manifest/1","bridge_id":bridge["bridge_id"],"bridge_digest":bridge["package_digest"],"profile_digest":profile["profile_digest"],"media_id":media["media_id"],"media_sha256":media["sha256"],"source_presentation_evidence_digest":media["presentation_evidence"]["evidence_digest"],"used_placement_ids":list(used_placement_ids),"subtitle_artifact_digest":subtitle_artifact["artifact_digest"],"subtitle_transcript_digest":subtitle_artifact["transcript_digest"],"subtitle_profile_digest":subtitle_profile["profile_digest"],"subtitles_enabled":bool(subtitles_enabled),"output_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest(),"output_byte_size":Path(path).stat().st_size}
 value["manifest_digest"]=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",", ":")).encode()).hexdigest();return value
def validate_aligned_preview_manifest(manifest,path):
 value=dict(manifest);digest=value.pop("manifest_digest",None)
 if digest!=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",", ":")).encode()).hexdigest() or value["output_sha256"]!=hashlib.sha256(Path(path).read_bytes()).hexdigest() or value["output_byte_size"]!=Path(path).stat().st_size:raise AlignedPreviewError("Aligned Preview Manifest 无效")
