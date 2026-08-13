import tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import build_aligned_preview_manifest,validate_aligned_preview_manifest
class PreviewManifestTests(unittest.TestCase):
 def test_manifest_binds_real_file_bridge_profile_and_source(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/"p.mp4";p.write_bytes(b"preview");m=build_aligned_preview_manifest(p,{"bridge_id":"EB1","package_digest":"b"*64},{"profile_digest":"p"*64},{"media_id":"NM1","sha256":"m"*64,"presentation_evidence":{"evidence_digest":"e"*64}},["VP0000"]);validate_aligned_preview_manifest(m,p);self.assertEqual(m["used_placement_ids"],["VP0000"])
if __name__=="__main__":unittest.main()
