"""Real renderer regression for the exact concrete production entrypoint."""
import os,tempfile,unittest
from decimal import Decimal
from pathlib import Path

from deeptalk_studio.edit_bridge_session import resolve_real_edit_bridge_session,run_real_edit_bridge_session
from deeptalk_studio.narration_media import canonical_digest
from deeptalk_studio.transcription.base import ProviderTimedUnit,ProviderTranscript,boundary_risks_from_plan
from tests.media_fixture_factory import MediaFixtureSpec,build_media_fixture
from tests.integrated_upstream_factory import create_integrated_roots

class ScriptProvider:
 def __init__(self,script):self.script=script
 def transcribe(self,extracted,plan,language,model):
  duration=Decimal(str(extracted["duration_seconds"]));step=duration/Decimal(len(self.script.beats)+1)
  units=tuple(ProviderTimedUnit(0,index,step*index,step*(index+1),beat["narration"]) for index,beat in enumerate(self.script.beats))
  metadata={"source":"integrated-production-entrypoint","chunk_plan_digest":plan.digest}
  return ProviderTranscript("deterministic",model,"fixture/1","",language,"word",units,boundary_risks_from_plan(plan),metadata,canonical_digest(metadata),plan.digest)

@unittest.skipUnless(os.getenv("DEEPTALK_RUN_ALIGNED_E2E")=="1","set DEEPTALK_RUN_ALIGNED_E2E=1 for real Remotion E2E")
class AudioAlignmentIntegratedE2E(unittest.TestCase):
 def test_exact_production_entrypoint_renders_real_preview_and_canonical_qa(self):
  with tempfile.TemporaryDirectory() as temp:
   upstream=Path(temp)/"upstream";report,script,package,asset_root,plan,manifest,production_qa=create_integrated_roots(upstream)
   session=Path(temp)/"session";session.mkdir();source=build_media_fixture(session,MediaFixtureSpec(name="clean-aroll",duration="2",internal_gap=True))
   from deeptalk_studio.edit_bridge_session import RealEditBridgeSessionInputs
   output=session/"DeepTalk-Aligned-Edit";inputs=RealEditBridgeSessionInputs(session,source,report,script,package,plan,manifest,production_qa,asset_root,(asset_root,upstream/"production-assets",output,session),output)
   result=run_real_edit_bridge_session(inputs,ScriptProvider(inputs.script),clock=lambda:"2026-08-13T21:00:00+08:00",id_factory=lambda kind:{"MEDIA":"NM-E2E","MAPPING":"MAP-E2E","TRANSCRIPT":"TR-E2E","ALIGNMENT":"AL-E2E","BRIDGE":"EB-E2E"}[kind])
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

if __name__=="__main__":unittest.main()
