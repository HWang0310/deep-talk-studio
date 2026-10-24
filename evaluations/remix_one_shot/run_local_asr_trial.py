import hashlib,json,subprocess,tempfile
from pathlib import Path
from deeptalk_studio.workbench import creative_chat
from deeptalk_studio.workbench.flow import WorkbenchFlow
from deeptalk_studio.workbench.llm import WorkbenchLLMError

root=Path(tempfile.mkdtemp(prefix='deeptalk-real-asr-'))
script='这里是原创软件验收音频。今天不追热点，我们观察一个简单的反差：手机一响，注意力就上班了。热闹可以看，情绪不用包年。以上是自行编写的合成语音，不描述任何真实人物事件。'
subprocess.run(['say','-v','Tingting','-o',str(root/'speech.aiff'),script],check=True,capture_output=True)
subprocess.run(['ffmpeg','-y','-f','lavfi','-i','color=c=0xd9c9b6:s=320x180:r=10','-i',str(root/'speech.aiff'),'-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(root/'owned-synthetic.mp4')],check=True,capture_output=True)
creative_chat.USER_CHAT_DIR=root
class NoMoreModelCalls:
    def summarize_reference(self,*a):raise WorkbenchLLMError('本轮仅验收真实本地ASR，未再调用模型')
flow=WorkbenchFlow(root,provider_factory=lambda s:NoMoreModelCalls())
bvid='BV1fixture03';url='https://www.bilibili.com/video/'+bvid
sid=flow.store.create('自行生成的原创ASR测试', [{'bvid':bvid,'title':'自行生成的原创ASR测试','url':url,'view_count':None,'view_count_status':'unavailable'}],None)['session_id']
media=root/'owned-synthetic.mp4'
flow.store.update(sid,lambda s:s['references'].update({bvid:{'status':'downloaded','media_path':str(media),'title':'自行生成的原创ASR测试','url':url,'authorization_text':'我授权处理自行生成的原创软件验收合成语音和视频。'}}))
result=flow.analyze_reference(sid,bvid)
export=flow.reference_transcript(sid,bvid)
transcript=export['transcript']
evidence={'media_origin':'Original test text synthesized locally using installed macOS Tingting; video created locally by ffmpeg. No Bilibili download. BVID/URL are fixture identifiers only.', 'real_ffmpeg_and_whisper':True,'model_calls':0,'expected_script':script,'recognized_text':transcript['text'],'segments':transcript['segments'],'model':transcript['model'],'runtime_version':transcript['runtime_version'],'source_media_sha256':transcript['transcript_provenance']['source_media_sha256'],'txt_path':export['artifact_path'],'status':transcript['transcript_status'],'analysis_status':result['study']['analysis_status']}
assert transcript['segments'] and max(s['end_seconds'] for s in transcript['segments'])>0
assert '软件' in transcript['text'] and '注意力' in transcript['text']
Path('evaluations/remix_one_shot/real-local-asr.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
print(json.dumps({'root':str(root),'segments':len(transcript['segments']),'model':transcript['model'],'runtime':transcript['runtime_version'],'status':transcript['transcript_status'],'recognized_chars':len(transcript['text'])},ensure_ascii=False),flush=True)
