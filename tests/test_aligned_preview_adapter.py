import hashlib,tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import RemotionAlignedPreviewRenderer
from tests.edit_bridge_fixtures import media
from tests.test_subtitle_builder import transcript
from deeptalk_studio.subtitle_builder import build_subtitle_artifact
from deeptalk_studio.subtitle_profile import load_subtitle_profile

def subtitle():
 data=transcript();data["narration_media_sha256"]=hashlib.sha256(b"aroll").hexdigest()
 return build_subtitle_artifact(data,media()|{"sha256":hashlib.sha256(b"aroll").hexdigest(),"presentation_duration_seconds":"20"},load_subtitle_profile(),subtitle_id="SUB1",created_at="now")

class AlignedPreviewAdapterTests(unittest.TestCase):
 def test_renderer_exposes_real_visual_render_boundary(self):
  self.assertTrue(callable(getattr(RemotionAlignedPreviewRenderer(),"render_visual",None)))
 def test_only_ready_placements_are_staged(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); ar=root/"a.mp4"; ar.write_bytes(b"aroll"); image=root/"i.png"; image.write_bytes(b"image")
   m=media(str(ar));m.update(byte_size=5,sha256=hashlib.sha256(b"aroll").hexdigest())
   def p(pid,status,path,data): return {"placement_id":pid,"placement_status":status,"source_kind":"real_image","local_path":str(path),"byte_size":len(data),"sha256":hashlib.sha256(data).hexdigest(),"preview_in_frame":0,"preview_out_frame":10}
   bridge={"bridge_id":"EB1","revision":1,"visual_placements":[p("VP0001","ready",image,b"image"),p("VP0002","missing_asset",root/"missing.png",b"")]}
   project=RemotionAlignedPreviewRenderer().prepare_project(bridge,m,subtitle(),load_subtitle_profile(),[root],root/"projects")
   self.assertEqual(set(project.staged_placement_ids),{"VP0000","VP0001"});self.assertNotIn("VP0002",project.payload_text)
   self.assertTrue((project.project_dir/"package.json").is_file());self.assertTrue(project.subtitles_enabled)
   self.assertIn("今天我们看证据。",project.payload_text)
   self.assertIn('"presentation_mode": "primary_visual"',project.payload_text)
   RemotionAlignedPreviewRenderer().validate_project(project)
 def test_tampered_ready_asset_fails_closed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ar=root/"a.mp4";ar.write_bytes(b"aroll");m=media(str(ar));m.update(byte_size=5,sha256=hashlib.sha256(b"aroll").hexdigest())
   bridge={"bridge_id":"EB1","revision":1,"visual_placements":[{"placement_id":"VP1","placement_status":"ready","source_kind":"real_image","local_path":str(root/"no.png"),"byte_size":1,"sha256":"x","preview_in_frame":0,"preview_out_frame":1}]}
   with self.assertRaises(Exception):RemotionAlignedPreviewRenderer().prepare_project(bridge,m,subtitle(),load_subtitle_profile(),[root],root/"projects")

 def test_layout_mode_has_a_single_controlled_presentation_mapping(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); ar=root/"a.mp4"; ar.write_bytes(b"aroll"); image=root/"i.png"; image.write_bytes(b"image")
   m=media(str(ar));m.update(byte_size=5,sha256=hashlib.sha256(b"aroll").hexdigest())
   base={"placement_status":"ready","source_kind":"real_image","local_path":str(image),"byte_size":5,"sha256":hashlib.sha256(b"image").hexdigest(),"preview_in_frame":0,"preview_out_frame":10}
   bridge={"bridge_id":"EB1","revision":1,"visual_placements":[
    base|{"placement_id":"VP1","layout_mode":"full_screen_broll"},
    base|{"placement_id":"VP2","layout_mode":"picture_in_picture"},
    base|{"placement_id":"VP3","layout_mode":"supporting_overlay"},
   ]}
   project=RemotionAlignedPreviewRenderer().prepare_project(bridge,m,subtitle(),load_subtitle_profile(),[root],root/"projects")
   import json
   modes={p["placement_id"]:p["presentation_mode"] for p in json.loads(project.payload_text)["placements"] if p["placement_id"] != "VP0000"}
   self.assertEqual(modes,{"VP1":"primary_visual","VP2":"primary_visual_with_pip","VP3":"supporting_overlay"})

if __name__=="__main__":unittest.main()
