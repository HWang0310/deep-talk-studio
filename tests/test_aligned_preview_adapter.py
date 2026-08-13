import hashlib,tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import RemotionAlignedPreviewRenderer
from tests.edit_bridge_fixtures import media

class AlignedPreviewAdapterTests(unittest.TestCase):
 def test_only_ready_placements_are_staged(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); ar=root/"a.mp4"; ar.write_bytes(b"aroll"); image=root/"i.png"; image.write_bytes(b"image")
   m=media(str(ar));m.update(byte_size=5,sha256=hashlib.sha256(b"aroll").hexdigest())
   def p(pid,status,path,data): return {"placement_id":pid,"placement_status":status,"source_kind":"real_image","local_path":str(path),"byte_size":len(data),"sha256":hashlib.sha256(data).hexdigest(),"preview_in_frame":0,"preview_out_frame":10}
   bridge={"bridge_id":"EB1","revision":1,"visual_placements":[p("VP0001","ready",image,b"image"),p("VP0002","missing_asset",root/"missing.png",b"")]}
   project=RemotionAlignedPreviewRenderer().prepare_project(bridge,m,[root],root/"projects")
   self.assertEqual(set(project.staged_placement_ids),{"VP0000","VP0001"});self.assertNotIn("VP0002",project.payload_text)
 def test_tampered_ready_asset_fails_closed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ar=root/"a.mp4";ar.write_bytes(b"aroll");m=media(str(ar));m.update(byte_size=5,sha256=hashlib.sha256(b"aroll").hexdigest())
   bridge={"bridge_id":"EB1","revision":1,"visual_placements":[{"placement_id":"VP1","placement_status":"ready","source_kind":"real_image","local_path":str(root/"no.png"),"byte_size":1,"sha256":"x","preview_in_frame":0,"preview_out_frame":1}]}
   with self.assertRaises(Exception):RemotionAlignedPreviewRenderer().prepare_project(bridge,m,[root],root/"projects")

if __name__=="__main__":unittest.main()
