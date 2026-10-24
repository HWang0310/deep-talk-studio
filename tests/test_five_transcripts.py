"""Five-source utility: honest offline tool-boundary fixtures, real persistence."""
import json
import subprocess
import tempfile
from pathlib import Path
from tests import test_workbench as fixtures
from deeptalk_studio.workbench.flow import WorkbenchFlow, WorkbenchFlowError
from deeptalk_studio.workbench.five_transcripts import FiveTranscripts
from deeptalk_studio.bilibili_reference_provider import VideoMetadataOutcome

class FiveTranscriptTests(fixtures._UserSettingsIsolatedTestCase):
    def setup_tool(self, root):
        fixtures.TopicFirstChatTests._configure(self, root)
        from deeptalk_studio.workbench.settings import load_settings, save_settings
        config=load_settings(root);config['downloads_dir']=str(root);save_settings(root,config)
        self.calls=[];self.fail_video=True
        def acquire(cmd, **kw):
            self.calls.append(cmd[-1])
            if self.fail_video and cmd[-1].endswith('BV1fixture03'):
                return subprocess.CompletedProcess(cmd,1,'','HTTP 403')
            path=Path(cmd[cmd.index('-o')+1].replace('%(ext)s','mp4'));path.write_bytes(b'fixture media')
            return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path)}),'')
        def audio(cmd, **kw):
            Path(cmd[-1]).write_bytes(b'RIFF'+b'0'*100);return subprocess.CompletedProcess(cmd,0,'','')
        def whisper(cmd, **kw):
            source=cmd[cmd.index('--file')+1] if '--file' in cmd else str(cmd)
            text='离线夹具 '+source+'\n'+('完整口播。'*100)+'最后一行绝不能丢失。'
            Path(cmd[cmd.index('--output-file')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':i*1000,'to':(i+1)*1000},'text': text if i==29 else '段落%d。'%i} for i in range(30)]}))
            return subprocess.CompletedProcess(cmd,0,'','')
        class Installation:
            runtime_path='fixture';model_path='fixture';dtw_preset='none';model_name='fixture';runtime_version='fixture'
        class Bootstrap:
            def ensure(self):return Installation()
        self.llm=fixtures.TopicFirstChatTests.CapturingLLM(['离线融合夹具：事情先发生，再出现冲突，最后反转。'])
        flow=WorkbenchFlow(root, provider_factory=lambda s:self.llm, acquire_runner=acquire, audio_runner=audio, whisper_runner=whisper,whisper_bootstrap=Bootstrap())
        self.tool=FiveTranscripts(flow, metadata=lambda bv:VideoMetadataOutcome(status='ok',title='离线 '+bv,view_count=12345))
        return flow

    def test_normalization_and_validation_never_silently_drop_links(self):
        with tempfile.TemporaryDirectory() as raw:
            self.setup_tool(Path(raw))
            result=self.tool.start(['https://www.bilibili.com/video/BV1usn26NEdp/?spm_id_from=foo\nBV1fixture02','BV1usn26NEdp','https://evil.example/video/BV1fixture03'])
            self.assertEqual(len(result['items']),2)
            self.assertEqual([x['status'] for x in result['validation']],['valid','valid','duplicate','invalid'])
            self.assertEqual(result['items'][0]['url'],'https://www.bilibili.com/video/BV1usn26NEdp')
            self.assertEqual(self.calls,[]);self.assertEqual(self.llm.seen,[])
            with self.assertRaises(WorkbenchFlowError):self.tool.start(['BV1fixture%02d'%i for i in range(6)])

    def test_five_complete_exports_failure_retry_idempotence_and_restart(self):
        with tempfile.TemporaryDirectory() as raw:
            flow=self.setup_tool(Path(raw))
            state=self.tool.start(['BV1fixture%02d'%i for i in range(1,6)])
            sid=state['session_id']
            with self.assertRaisesRegex(WorkbenchFlowError,'授权'):self.tool.process(sid,consent=False)
            state=self.tool.process(sid,consent=True)
            self.assertEqual([i['status'] for i in state['items']],['complete','complete','failed','complete','complete'])
            self.assertIn('失败',state['combined_text']);self.assertEqual(self.llm.seen,[])
            self.fail_video=False
            state=self.tool.process(sid,consent=True)
            self.assertEqual(len(self.calls),6)
            self.assertTrue(all(i['status']=='complete' for i in state['items']))
            positions=[]
            for item in state['items']:
                self.assertIn('最后一行绝不能丢失。',item['transcript']['text'])
                self.assertEqual(len(item['transcript']['segments']),30)
                self.assertEqual(Path(item['artifact_path']).read_text(),item['text'])
                self.assertTrue(Path(item['json_path']).is_file())
                positions.append(state['combined_text'].index(item['text']))
                self.assertTrue(Path(item['media_path']).stem.endswith('-12345播放'))
            self.assertEqual(positions,sorted(positions))
            self.assertEqual(Path(state['combined_path']).read_text(),state['combined_text'])
            restarted=FiveTranscripts(flow,metadata=lambda bv:None)
            self.assertEqual(restarted.state(sid)['combined_text'],state['combined_text'])
            self.tool.process(sid,consent=True);self.assertEqual(len(self.calls),6)
            result=self.tool.fuse(sid,words=1234,style='有梗按经过讲',consent=True)
            self.assertIn('未审核',result['synthesis']['text'])
            prompt=json.dumps(self.llm.seen[-1],ensure_ascii=False)
            self.assertIn('1234',prompt)
            for item in state['items']:self.assertIn(json.dumps(item['transcript']['text'],ensure_ascii=False)[1:-1], self.llm.seen[-1][-1]['content'])
            self.assertEqual(len(self.llm.seen),1)
            with self.assertRaises(WorkbenchFlowError):self.tool.state('../outside')

    def test_fusion_requires_explicit_consent_and_complete_sources(self):
        with tempfile.TemporaryDirectory() as raw:
            self.setup_tool(Path(raw));state=self.tool.start(['BV1fixture01'])
            for consent in (False,True):
                with self.assertRaises(WorkbenchFlowError):self.tool.fuse(state['session_id'],words=800,consent=consent)
            self.assertEqual(self.llm.seen,[])

    def test_new_count_new_session_preserves_old_files_and_metadata(self):
        with tempfile.TemporaryDirectory() as raw:
            flow=self.setup_tool(Path(raw));self.fail_video=False
            first=self.tool.process(self.tool.start(['BV1fixture01'])['session_id'],consent=True)
            old_path=Path(first['items'][0]['artifact_path']);old=old_path.read_bytes()
            self.tool.metadata=lambda bv:VideoMetadataOutcome(status='ok',title='新标题',view_count=99999)
            second=self.tool.process(self.tool.start(['BV1fixture01','BV1fixture02'])['session_id'],consent=True)
            self.assertNotEqual(first['session_id'],second['session_id'])
            self.assertEqual(old_path.read_bytes(),old)
            self.assertTrue(Path(second['items'][0]['media_path']).stem.endswith('-99999播放'))
            self.assertEqual(second['items'][0]['transcript']['source_metadata']['bvid'],'BV1fixture01')
            restarted=FiveTranscripts(WorkbenchFlow(Path(raw)))
            self.assertEqual(restarted.state(first['session_id'])['combined_text'],first['combined_text'])
            with self.assertRaises(WorkbenchFlowError):self.tool.process(second['session_id'],consent=True,bvids=['BVoutside'])

    def test_http_utility_routes_default_and_advanced(self):
        import threading, urllib.request
        from deeptalk_studio.webui import make_server
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root)
            server=make_server(port=0,output_dir=root,provider_factory=lambda:None,flow=flow)
            server.transcripts=self.tool
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            try:
                html=urllib.request.urlopen(base).read().decode()
                self.assertIn('五视频口播提取',html);self.assertNotIn('先选热门参考',html)
                settings_html=urllib.request.urlopen(base+'/settings').read().decode()
                self.assertIn('保存文件夹',settings_html);self.assertIn('选择文件夹',settings_html)
                self.assertIn('chat-sidebar',urllib.request.urlopen(base+'/advanced').read().decode())
                def post(action,data):
                    return json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/workbench/transcripts/'+action,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})))
                result=post('start',{'links':['BV1fixture01']})
                result=post('process',{'session_id':result['session_id'],'consent':True})
                self.assertEqual(result['items'][0]['status'],'complete')
                self.assertIn('最后一行绝不能丢失',post('state',{'session_id':result['session_id']})['combined_text'])
                self.assertEqual(len(post('sessions',{})['sessions']),1)
                self.assertEqual(self.llm.seen,[])
            finally:server.shutdown();server.server_close();thread.join()

    def test_folder_picker_http_route_returns_selected_local_directory(self):
        import threading, urllib.request
        from deeptalk_studio.webui import make_server
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root)
            flow.choose_save_folder=lambda:{'path':str(root),'cancelled':False}
            server=make_server(port=0,output_dir=root,provider_factory=lambda:None,flow=flow)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            try:
                request=urllib.request.Request(base+'/api/workbench/settings/folder-picker',data=b'{}',headers={'Content-Type':'application/json'})
                result=json.load(urllib.request.urlopen(request))
                self.assertEqual(result,{'path':str(root),'cancelled':False})
            finally:server.shutdown();server.server_close();thread.join()

    def test_local_transcription_needs_no_model_key_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root)
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['api_key']='';config['downloads_dir']='';save_settings(root,config)
            result=self.tool.process(self.tool.start(['BV1fixture01'])['session_id'],consent=True)
            self.assertEqual(result['items'][0]['status'],'complete');self.assertEqual(self.llm.seen,[])
            self.assertEqual(Path(result['items'][0]['media_path']).parent,flow.store.session_dir(result['session_id'])/'media')
            outside=root/'outside';outside.mkdir()
            path=flow.store.references_dir(result['session_id'])/'BV1fixture01'/'transcript.json'
            path.unlink();path.symlink_to(outside/'transcript.json')
            # A symlink can never become a complete source or model input.
            self.assertNotEqual(self.tool.state(result['session_id'])['items'][0]['status'],'complete')
            self.tool.process(result['session_id'],consent=True)
            self.assertFalse((outside/'transcript.json').exists())
