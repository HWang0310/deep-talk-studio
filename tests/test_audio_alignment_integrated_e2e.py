"""Real renderer regression for the exact concrete production entrypoint."""
import json,os,shutil,tempfile,unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.edit_bridge_session import revise_real_edit_bridge_session,run_real_edit_bridge_session
from deeptalk_studio.narration_media import canonical_digest
from deeptalk_studio.transcription.base import ProviderTimedUnit,ProviderTranscript,boundary_risks_from_plan
from tests.media_fixture_factory import MediaFixtureSpec,build_media_fixture
from tests.integrated_upstream_factory import create_integrated_roots

class ScriptProvider:
 def __init__(self,script):self.script=script
 def transcribe(self,extracted,plan,language,model):
  phrases=[]
  for beat in self.script.beats:
   text=beat["narration"]
   for index in range(0,len(text),6):
    phrase=text[index:index+6]
    if phrase and not any(char.isalnum() or "\u3400"<=char<="\u9fff" for char in phrase):
     phrases[-1]+=phrase
    else:phrases.append(phrase)
  duration=Decimal(str(extracted["duration_seconds"]));step=duration/Decimal(len(phrases)+1)
  units=tuple(ProviderTimedUnit(0,index,step*index,step*(index+1),phrase) for index,phrase in enumerate(phrases))
  metadata={"source":"integrated-production-entrypoint","chunk_plan_digest":plan.digest}
  return ProviderTranscript("deterministic",model,"fixture/1","",language,"token",units,boundary_risks_from_plan(plan),metadata,canonical_digest(metadata),plan.digest)

@unittest.skipUnless(os.getenv("DEEPTALK_RUN_ALIGNED_E2E")=="1","set DEEPTALK_RUN_ALIGNED_E2E=1 for real Remotion E2E")
class AudioAlignmentIntegratedE2E(unittest.TestCase):
 def test_exact_production_entrypoint_renders_real_preview_and_canonical_qa(self):
  with tempfile.TemporaryDirectory() as temp:
   upstream=Path(temp)/"upstream";report,script,package,asset_root,plan,manifest,production_qa=create_integrated_roots(upstream)
   session=Path(temp)/"session";session.mkdir();source=build_media_fixture(session,MediaFixtureSpec(name="clean-aroll",duration="2",internal_gap=True))
   from deeptalk_studio.edit_bridge_session import RealEditBridgeSessionInputs
   output=session/"DeepTalk-Aligned-Edit";inputs=RealEditBridgeSessionInputs(session,source,report,script,package,plan,manifest,production_qa,asset_root,(asset_root,upstream/"production_assets",output,session),output)
   result=run_real_edit_bridge_session(inputs,ScriptProvider(inputs.script),clock=lambda:"2026-08-13T21:00:00+08:00",id_factory=lambda kind:{"MEDIA":"NM-E2E","MAPPING":"MAP-E2E","TRANSCRIPT":"TR-E2E","SUBTITLE":"SUB-E2E","ALIGNMENT":"AL-E2E","BRIDGE":"EB-E2E"}[kind])
   self.assertTrue(result.preview_path.is_file());self.assertGreater(result.preview_path.stat().st_size,0)
   self.assertIn(result.qa["package_gate_status"],{"pass","warnings"})
   self.assertEqual(result.artifacts["preview_manifest"]["used_placement_ids"][0],"VP0000")
   placements=result.artifacts["bridge"]["visual_placements"]
   self.assertTrue(any(p["source_kind"]=="real_image" and p["placement_status"]=="ready" for p in placements))
   self.assertTrue(any(p["source_kind"]=="real_video" and p["placement_status"]=="ready" and p["source_clip_out_seconds"] for p in placements))
   self.assertTrue(any(p["source_kind"]=="real_video" and p["placement_status"]=="clip_selection_needed" for p in placements))
   self.assertTrue(any(p["source_kind"]=="original_motion" and p["placement_status"]=="ready" for p in placements))
   staged=set(result.artifacts["preview_manifest"]["used_placement_ids"])
   self.assertTrue(any(p["placement_id"] not in staged for p in placements if p["placement_status"]=="clip_selection_needed"))
   self.assertEqual(result.artifacts["alignment"]["presentation_duration_seconds"],result.artifacts["media"]["presentation_duration_seconds"])
   self.assertTrue(result.artifacts["preview_manifest"]["subtitles_enabled"])
   self.assertEqual(result.artifacts["preview_manifest"]["subtitle_artifact_digest"],result.artifacts["subtitle"]["artifact_digest"])
   self.assertTrue(result.paths["subtitle_srt"].is_file())
   image=next(p for p in placements if p["source_kind"]=="real_image" and p["placement_status"]=="ready")
   revised=revise_real_edit_bridge_session(result,f"{image['safe_filename']} 短一点",clock=lambda:"2026-08-13T21:05:00+08:00")
   self.assertTrue(revised.preview_path.is_file())
   self.assertEqual(revised.artifacts["preview_manifest"]["subtitle_artifact_digest"],result.artifacts["subtitle"]["artifact_digest"])
   self.assertTrue(revised.artifacts["preview_manifest"]["subtitles_enabled"])
   self.assertEqual(revised.artifacts["mux"].audio_presentation_start_seconds,result.artifacts["mux"].audio_presentation_start_seconds)
   self.assertEqual(revised.artifacts["mux"].internal_gaps,result.artifacts["mux"].internal_gaps)
   evidence_root=os.getenv("DEEPTALK_E2E_EVIDENCE_DIR")
   if evidence_root:
    target=Path(evidence_root);target.mkdir(parents=True,exist_ok=True)
    for source,name in ((result.preview_path,"ALIGNED_PREVIEW-subtitled.mp4"),(revised.preview_path,"ALIGNED_PREVIEW-subtitled-r0002.mp4"),(result.paths["subtitle"],"subtitle-r0001.json"),(result.paths["subtitle_srt"],"subtitle-r0001.srt"),(result.paths["preview_manifest"],"aligned-preview-manifest.json"),(result.paths["qa"],"edit-bridge-qa.json")):
     shutil.copy2(source,target/name)
    summary={"initial_preview_sha256":result.artifacts["preview_manifest"]["output_sha256"],"revised_preview_sha256":revised.artifacts["preview_manifest"]["output_sha256"],"subtitle_artifact_digest":result.artifacts["subtitle"]["artifact_digest"],"initial_gate":result.qa["package_gate_status"],"revised_gate":revised.qa["package_gate_status"],"subtitles_enabled":True}
    (target/"evidence-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":unittest.main()
