#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GROUPS={
 "media_timebase":"tests.test_alignment_media_eval",
 "transcript_alignment":"tests.test_alignment_transcript_eval",
 "material_placement":"tests.test_alignment_material_eval",
 "placement_timing":"tests.test_alignment_placement_eval",
 "preview_audio":"tests.test_alignment_preview_eval",
 "revision_binding":"tests.test_alignment_revision_eval",
}
def run():
 cases=json.loads((ROOT/"evaluations/audio-alignment-edit-bridge/case-manifest.json").read_text())
 modules=sorted(set(GROUPS[value] for value in cases.values()))+["tests.test_alignment_invariants","tests.test_transcription_chunk_boundary_eval","tests.test_preview_audio_sync_eval"]
 result=subprocess.run([sys.executable,"-m","unittest",*modules,"-v"],cwd=ROOT,env={**__import__("os").environ,"PYTHONPATH":str(ROOT/"src")+":"+str(ROOT)},capture_output=True,text=True)
 if result.returncode:raise RuntimeError((result.stderr or result.stdout)[-4000:])
 payload={"executed_test_modules":modules,"cases":{key:"pass" for key in cases},"cb_cases":{f"CB{i}":"pass" for i in range(1,8)},"pa_cases":{f"PA{i}":"pass" for i in range(1,8)},"status":"pass"}
 payload["repeat_digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest();return payload
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--verify-repeat",action="store_true");args=parser.parse_args();one=run()
 if args.verify_repeat and one!=run():raise SystemExit("repeat mismatch")
 print(json.dumps(one,ensure_ascii=False,sort_keys=True))
if __name__=="__main__":main()
