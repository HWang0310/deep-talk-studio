"""Explicit offline tool-boundary fixtures; real flow, HTTP, files and browser. No live media/LLM."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from deeptalk_studio.webui import make_server
from deeptalk_studio.workbench import settings, creative_chat
from deeptalk_studio.workbench.flow import WorkbenchFlow
from deeptalk_studio.workbench.five_transcripts import FiveTranscripts
from deeptalk_studio.bilibili_reference_provider import VideoMetadataOutcome

parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8324);parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
root=args.root;root.mkdir(parents=True,exist_ok=True)
settings.USER_SETTINGS_DIR=root;creative_chat.USER_CHAT_DIR=root
settings.save_settings(root,settings.apply_settings_update(settings.load_settings(root),{'provider_mode':'deepseek','api_key':'fixture-not-real'}))
logpath=root/'tool-calls.json'
log=json.loads(logpath.read_text()) if logpath.exists() else []
def record(tool,**data):
    log.append({'tool':tool,**data});logpath.write_text(json.dumps(log,ensure_ascii=False,indent=2));time.sleep(.3)
def acquire(cmd,**kw):
    bv=cmd[-1].split('/')[-1];record('yt-dlp',bvid=bv)
    if bv.endswith('03') and sum(c['tool']=='yt-dlp' and c.get('bvid')==bv for c in log)==1:
        return subprocess.CompletedProcess(cmd,1,'','HTTP 403 FIXTURE deliberate first failure')
    path=Path(cmd[cmd.index('-o')+1].replace('%(ext)s','mp4'));path.write_bytes(b'EXPLICIT OFFLINE MEDIA FIXTURE '+bv.encode())
    return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path),'duration':250}),'')
audio_sources={}
def audio(cmd,**kw):
    audio_sources[cmd[-1]]=cmd[cmd.index('-i')+1]
    record('ffmpeg',input=cmd[cmd.index('-i')+1]);Path(cmd[-1]).write_bytes(b'RIFF'+b'0'*100)
    return subprocess.CompletedProcess(cmd,0,'','')
def whisper(cmd,**kw):
    source=cmd[cmd.index('--file')+1];record('whisper',input=source)
    source=audio_sources[source]
    bv=next((b for b in ['BV1usn26NEdp','BV1fixture02','BV1fixture03','BV1fixture04','BV1fixture05'] if b in source),'未知')
    segments=[{'offsets':{'from':i*1000,'to':(i+1)*1000},'text':f'{bv} 第{i+1}句：这是离线软件验收夹具，完整保存原文，不描述真实事件。'} for i in range(250)]
    segments[-1]['text']=f'{bv} 第250句：最后一行完整保留。'
    Path(cmd[cmd.index('--output-file')+1]+'.json').write_text(json.dumps({'transcription':segments},ensure_ascii=False))
    return subprocess.CompletedProcess(cmd,0,'','')
class Installation:
    runtime_path='fixture';model_path='fixture';dtw_preset='none';model_name='FIXTURE-not-real-ASR';runtime_version='fixture'
class Bootstrap:
    def ensure(self):return Installation()
class LLM:
    def chat_stream(self,messages):
        record('model',messages=messages)
        yield '离线模型融合夹具。事情先从误会开始，随后双方解释经过，冲突逐步解开，最后留下一个轻松的反转。这是单篇未审核稿件，非真实模型质量证明。'
flow=WorkbenchFlow(root,provider_factory=lambda config:LLM(),acquire_runner=acquire,audio_runner=audio,whisper_runner=whisper,whisper_bootstrap=Bootstrap())
server=make_server(port=args.port,output_dir=root/'discoveries',provider_factory=lambda:None,flow=flow)
server.transcripts=FiveTranscripts(flow,metadata=lambda bv:VideoMetadataOutcome(status='ok',title='离线验收来源 '+bv,view_count=12345+len(bv)))
print(json.dumps({'root':str(root),'port':server.server_port,'fixture':True}),flush=True)
server.serve_forever()
