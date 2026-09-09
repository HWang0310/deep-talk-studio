import unittest
from deeptalk_studio.aligned_preview.remotion import AudioPresentationEvidence,validate_preview_audio_presentation
class PreviewAudioSyncEvalTests(unittest.TestCase):
 def test_pa1_to_pa7_start_gap_stream_and_tamper(self):
  src=AudioPresentationEvidence(.375,2.0,1.625,((.7,1.1),),1,.0334,"aac","1/48000","x");validate_preview_audio_presentation(src,src,.0334)
  reset=AudioPresentationEvidence(0,2.0,2.0,((.7,1.1),),1,.0334,"aac","1/48000","y")
  with self.assertRaises(Exception):validate_preview_audio_presentation(src,reset,.0334)
if __name__=="__main__":unittest.main()
