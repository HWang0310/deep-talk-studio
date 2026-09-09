import hashlib
from pathlib import Path


def media(path="/tmp/aroll.mp4"):
    return {"media_id":"NM1","sha256":"a"*64,"media_kind":"video","safe_original_filename":"aroll.mp4","immutable_local_path":path,"presentation_duration_seconds":"20"}

def alignment():
    return {"cue_timeline":[
        {"cue_id":"VC001","beat_id":"B001","placement_anchor":"日期","actual_start_seconds":"2","actual_end_seconds":"12","placement_status":"aligned","confidence":"high"},
        {"cue_id":"VC002","beat_id":"B002","placement_anchor":"比较","actual_start_seconds":"12","actual_end_seconds":"18","placement_status":"aligned","confidence":"high"},
    ]}

def write_png(root: Path, name="image.png"):
    path=root/name; data=b"\x89PNG\r\n\x1a\nvalid-image"; path.write_bytes(data)
    return path,len(data),hashlib.sha256(data).hexdigest()

def material_view(path,size,digest,kind="image"):
    asset_type="video_clip_reference" if kind=="video" else "document_screenshot"
    return {"items":[{"source_kind":"material","source_id":"M001","cue_ids":["VC001"],"title":"监管文件","caption":"监管文件截图","local_path":str(path),"byte_size":size,"sha256":digest,"production_status":"ready","asset_type":asset_type,
      "video_reference":{"start_seconds":0,"end_seconds":0}}]}

def production_motion(path,size,digest):
    return ({"plan_id":"PP1","plan_digest":"p"*64,"scenes":[{"scene_id":"SC001","cue_ids":["VC002"],"beat_id":"B002"}]},
      {"manifest_id":"MM1","manifest_digest":"q"*64,"qa_status":"ready","assets":[{"scene_id":"SC001","local_path":str(path),"byte_size":size,"sha256":digest,"duration_seconds":"6","width":1920,"height":1080,"fps":30,"qa_status":"ready"}]})
