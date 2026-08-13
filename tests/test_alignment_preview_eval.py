import shutil,tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import probe_audio_presentation,validate_preview_audio_presentation
from tests.media_fixture_factory import MediaFixtureSpec,build_media_fixture
@unittest.skipUnless(shutil.which("ffmpeg"),"ffmpeg required")
class AlignmentPreviewEvalTests(unittest.TestCase):
 def test_pa_positive_offset_gap_and_reset_detection(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);one=probe_audio_presentation(build_media_fixture(root,MediaFixtureSpec(name="one",audio_offset="0.375",internal_gap=True)));self.assertGreater(one.audio_start_seconds,.3);self.assertTrue(one.internal_gaps);validate_preview_audio_presentation(one,one,one.tolerance_seconds)
if __name__=="__main__":unittest.main()
