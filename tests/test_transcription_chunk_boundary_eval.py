import tempfile,unittest
from pathlib import Path
from deeptalk_studio.transcription_chunking import load_transcription_chunk_profile,plan_transcription_chunks,profile_with_overrides
from tests.test_transcription_chunking import mapping,write_pcm
class TranscriptionChunkBoundaryEvalTests(unittest.TestCase):
 def test_cb1_to_cb7_pause_fallback_mapping_coverage_and_repeat(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);profile=profile_with_overrides(load_transcription_chunk_profile(),request_cap_bytes=1244,search_window_ms=600,analysis_window_ms=20,hop_ms=10,safe_pause_min_ms=300,fallback_interval_ms=300,risk_guard_ms=1000)
   pause=plan_transcription_chunks(write_pcm(root/"pause"/"pause.wav",[12000]*150+[0]*350+[12000]*1100),mapping(),profile);self.assertEqual(pause.boundaries[0].selection_mode,"safe_pause")
   risk_audio=write_pcm(root/"risk"/"risk.wav",[12000]*1600);risk=plan_transcription_chunks(risk_audio,mapping(),profile);self.assertEqual(risk.boundaries[0].boundary_risk,"high");self.assertEqual(risk.digest,plan_transcription_chunks(risk_audio,mapping(),profile).digest)
   self.assertTrue(all(a.end_sample==b.start_sample for a,b in zip(risk.chunks,risk.chunks[1:])));self.assertEqual(str(risk.chunks[0].media_start_seconds),"0.375")
if __name__=="__main__":unittest.main()
