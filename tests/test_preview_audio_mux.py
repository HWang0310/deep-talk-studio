import shutil,subprocess,tempfile,unittest
from pathlib import Path
from deeptalk_studio.aligned_preview.remotion import mux_clean_aroll_audio
from deeptalk_studio.narration_media import import_narration_media
from tests.media_fixture_factory import MediaFixtureSpec,build_media_fixture

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"ffmpeg required")
class PreviewAudioMuxTests(unittest.TestCase):
 def test_mux_keeps_single_aroll_audio_without_edit_filters_and_offset(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=build_media_fixture(root/"in",MediaFixtureSpec(name="source",audio_offset="0.375",internal_gap=True));media=import_narration_media(source,root/"media",imported_at="2026-08-13T12:00:00Z",id_factory=lambda _:"NM1").artifact
   visual=root/"visual.mp4";subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i","color=size=1920x1080:rate=30:duration=2","-an","-c:v","libx264","-pix_fmt","yuv420p",str(visual)],check=True)
   result=mux_clean_aroll_audio(visual,media,root/"preview.mp4")
   self.assertEqual(result.audio_stream_count,1);self.assertNotRegex(result.command_summary,r"trim|loudnorm|silenceremove|atempo|shortest");self.assertGreater(result.audio_presentation_start_seconds,0.3);self.assertTrue(result.internal_gaps)

if __name__=="__main__":unittest.main()
