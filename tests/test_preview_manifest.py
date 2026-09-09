import tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import build_aligned_preview_manifest,validate_aligned_preview_manifest
from tests.test_subtitle_builder import transcript,media
from deeptalk_studio.subtitle_builder import build_subtitle_artifact
from deeptalk_studio.subtitle_profile import load_subtitle_profile
class PreviewManifestTests(unittest.TestCase):
 def test_manifest_binds_real_file_bridge_profile_and_source(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/"p.mp4";p.write_bytes(b"preview");profile=load_subtitle_profile();sub=build_subtitle_artifact(transcript(),media(),profile,subtitle_id="SUB1",created_at="now");m=build_aligned_preview_manifest(p,{"bridge_id":"EB1","package_digest":"b"*64,"root_bindings":{"transcript_digest":sub["transcript_digest"]}},{"profile_digest":"p"*64},{"media_id":"NM1","sha256":"m"*64,"presentation_evidence":{"evidence_digest":"e"*64}},["VP0000"],sub,profile,True);validate_aligned_preview_manifest(m,p);self.assertEqual(m["used_placement_ids"],["VP0000"]);self.assertTrue(m["subtitles_enabled"])
if __name__=="__main__":unittest.main()
