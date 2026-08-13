import os,tempfile,unittest
from pathlib import Path

from deeptalk_studio.audio_timestamp_mapping import derive_timestamp_mapping,validate_timestamp_mapping
from deeptalk_studio.narration_media import audio_extraction_profile,extract_transcription_audio,import_narration_media
from deeptalk_studio.transcript_builder import build_timed_transcript,validate_timed_transcript
from deeptalk_studio.transcription.openai import OpenAISDKTranscriptionTransport,OpenAITranscriptionProvider
from deeptalk_studio.transcription_chunking import load_transcription_chunk_profile,plan_transcription_chunks,validate_transcription_chunk_plan

@unittest.skipUnless(os.getenv("DEEPTALK_RUN_OPENAI_TRANSCRIPTION_SMOKE")=="1" and os.getenv("OPENAI_API_KEY") and os.getenv("DEEPTALK_TRANSCRIPTION_SMOKE_MEDIA"),"real OpenAI transcription smoke environment unavailable")
class OpenAITranscriptionSmokeTests(unittest.TestCase):
 def test_authorized_real_smoke_builds_bound_timed_transcript(self):
  source=Path(os.environ["DEEPTALK_TRANSCRIPTION_SMOKE_MEDIA"])
  self.assertTrue(source.is_file());self.assertEqual(source.suffix.casefold(),".wav");self.assertLess(source.stat().st_size,25*1024*1024)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);media=import_narration_media(source,root/"media",imported_at="2026-08-13T12:00:00Z",id_factory=lambda _:"SMOKE-MEDIA").artifact
   profile=audio_extraction_profile();extracted=extract_transcription_audio(media,root/"derived.wav",profile=profile,created_at="2026-08-13T12:00:00Z").artifact
   mapping=derive_timestamp_mapping(media,extracted,mapping_id="SMOKE-MAP",created_at="2026-08-13T12:00:00Z");validate_timestamp_mapping(mapping,media,extracted)
   chunk_profile=load_transcription_chunk_profile();plan=plan_transcription_chunks(extracted,mapping,chunk_profile);validate_transcription_chunk_plan(plan,extracted,mapping,chunk_profile)
   transport=OpenAISDKTranscriptionTransport(api_key=os.environ["OPENAI_API_KEY"]);provider=OpenAITranscriptionProvider(api_key=os.environ["OPENAI_API_KEY"],transport=transport)
   provider_result=provider.transcribe(extracted,plan,"zh","whisper-1")
   transcript=build_timed_transcript(provider_result,media,extracted,mapping,plan,transcript_id="SMOKE-TRANSCRIPT",created_at="2026-08-13T12:00:00Z")
   validate_timed_transcript(transcript,media,extracted,mapping,plan)
   self.assertEqual(transcript["provider"],"openai");self.assertEqual(transcript["timestamp_granularity"],"word");self.assertTrue(transcript["timed_units"])
if __name__=="__main__":unittest.main()
