import shutil,tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import probe_audio_presentation,validate_preview_audio_presentation
from tests.media_fixture_factory import MediaFixtureSpec,build_media_fixture

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"ffmpeg required")
class PreviewAudioPresentationTests(unittest.TestCase):
 def test_same_positive_offset_and_internal_silence_pass(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=build_media_fixture(root,MediaFixtureSpec(name="source",audio_offset="0.375",internal_gap=True))
   evidence=probe_audio_presentation(source);self.assertGreater(evidence.audio_start_seconds,0.3);self.assertTrue(evidence.internal_gaps);validate_preview_audio_presentation(evidence,evidence,evidence.tolerance_seconds)
 def test_same_duration_but_reset_audio_fails(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);shifted=probe_audio_presentation(build_media_fixture(root,MediaFixtureSpec(name="shifted",audio_offset="0.375")));zero=probe_audio_presentation(build_media_fixture(root,MediaFixtureSpec(name="zero")))
   with self.assertRaises(Exception):validate_preview_audio_presentation(shifted,zero,max(shifted.tolerance_seconds,zero.tolerance_seconds))

if __name__=="__main__":unittest.main()
