"""Five-source utility: honest offline tool-boundary fixtures, real persistence."""
import json
import subprocess
import tempfile
from unittest import mock
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
        self.wav_paths=[];self.whisper_output_dirs=[]
        def acquire(cmd, **kw):
            self.calls.append(cmd[-1])
            if self.fail_video and cmd[-1].endswith('BV1fixture03'):
                return subprocess.CompletedProcess(cmd,1,'','HTTP 403')
            path=Path(cmd[cmd.index('-o')+1].replace('%(ext)s','mp4'));path.write_bytes(b'fixture media')
            return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path)}),'')
        def audio(cmd, **kw):
            self.wav_paths.append(Path(cmd[-1]));Path(cmd[-1]).write_bytes(b'RIFF'+b'0'*100);return subprocess.CompletedProcess(cmd,0,'','')
        def whisper(cmd, **kw):
            source=cmd[cmd.index('--file')+1] if '--file' in cmd else str(cmd)
            self.whisper_output_dirs.append(Path(cmd[cmd.index('--output-file')+1]).parent)
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

    def test_auto_save_batch_is_incremental_and_retry_preserves_successful_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root)
            save_root=root/'指定保存';save_root.mkdir()
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)
            original_metadata=self.tool.metadata
            sid_holder={}
            saw_incremental_export=[]
            def metadata(bv):
                if bv=='BV1fixture02':
                    saved_path=flow.store.load(sid_holder['sid']).get('save_batch_path')
                    if not saved_path:
                        saw_incremental_export.append(False)
                        return original_metadata(bv)
                    batch=Path(saved_path)
                    first_text=list((batch/'口播稿').glob('01-*.txt'))
                    self.assertEqual(len(first_text),1,'first transcript must be written before video 2 begins')
                    self.assertIn('最后一行绝不能丢失。',first_text[0].read_text(encoding='utf-8'))
                    partial=(batch/'合并参考稿.txt').read_text(encoding='utf-8')
                    self.assertIn('最后一行绝不能丢失。',partial)
                    self.assertIn('BV1fixture02',partial)
                    self.assertIn('未完成 / 失败',partial)
                    saw_incremental_export.append(True)
                return original_metadata(bv)
            self.tool.metadata=metadata
            state=self.tool.start(['BV1fixture01','BV1fixture02','BV1fixture03'])
            sid_holder['sid']=state['session_id']
            batch=Path(state.get('batch_path',''))
            self.assertTrue(batch.is_dir(),'new extraction should allocate a batch below the configured root')
            self.assertEqual(batch.parent,save_root.resolve())
            self.assertTrue((batch/'视频').is_dir())
            self.assertTrue((batch/'口播稿').is_dir())
            state=self.tool.process(state['session_id'],consent=True)
            self.assertEqual(saw_incremental_export,[True],'the first completed item should be archived before the second starts')
            self.assertEqual([item['status'] for item in state['items']],['complete','complete','failed'])
            merged=batch/'合并参考稿.txt'
            self.assertEqual(merged.read_text(encoding='utf-8'),state['combined_text'])
            self.assertIn('未完成 / 失败',state['combined_text'])
            successful=[]
            for item in state['items'][:2]:
                paths=item.get('save_paths') or {}
                self.assertTrue(all(paths.get(key) for key in ('video','transcript_txt','transcript_json')),'each completed item exposes all archive paths')
                media=Path(paths.get('video',''))
                txt=Path(paths.get('transcript_txt',''))
                timed=Path(paths.get('transcript_json',''))
                self.assertEqual(media.parent,batch/'视频')
                self.assertTrue(media.is_file())
                self.assertTrue(media.stem.endswith('-12345播放'))
                self.assertTrue(txt.is_file());self.assertTrue(timed.is_file())
                self.assertEqual(txt.read_text(encoding='utf-8'),item['text'])
                self.assertEqual(json.loads(timed.read_text(encoding='utf-8')),item['transcript'])
                successful.append((media,txt,timed,[p.stat().st_ino for p in (media,txt,timed)]))
            self.assertEqual(state.get('batch_path'),str(batch))
            self.assertEqual(len(self.calls),3)
            self.fail_video=False
            state=self.tool.process(state['session_id'],consent=True,bvids=['BV1fixture03'])
            self.assertEqual(len(self.calls),4,'retry only invokes acquisition for the failed video')
            for media,txt,timed,inodes in successful:
                self.assertTrue(media.is_file(),'original video remains in the archive')
                self.assertEqual([p.stat().st_ino for p in (media,txt,timed)],inodes)
            final_texts=[item['transcript']['text'] for item in state['items']]
            self.assertEqual([state['combined_text'].index(text) for text in final_texts],sorted(state['combined_text'].index(text) for text in final_texts))
            self.assertEqual(merged.read_text(encoding='utf-8'),state['combined_text'])
            self.assertTrue(all(not path.exists() for path in self.wav_paths),'temporary WAVs are removed after Whisper')
            self.assertTrue(all(not path.exists() for path in self.whisper_output_dirs),'temporary Whisper JSON directories are removed')
            restarted=FiveTranscripts(flow).state(state['session_id'])
            self.assertEqual(restarted['batch_path'],str(batch))
            self.assertEqual((batch/'合并参考稿.txt').read_text(encoding='utf-8'),restarted['combined_text'])

    def test_new_task_uses_a_collision_safe_batch_folder_and_root_failure_is_clear(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);self.setup_tool(root)
            save_root=root/'chosen';save_root.mkdir()
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)
            first=self.tool.start(['BV1fixture01'])
            second=self.tool.start(['BV1fixture01'])
            first_path=Path(first.get('batch_path',''))
            second_path=Path(second.get('batch_path',''))
            self.assertTrue(first_path.is_dir())
            self.assertTrue(second_path.is_dir())
            self.assertNotEqual(first_path,second_path)
            import deeptalk_studio.workbench.settings as settings_module
            with mock.patch.object(settings_module.os,'access',return_value=False):
                with self.assertRaisesRegex(WorkbenchFlowError,'不可写'):
                    self.tool.start(['BV1fixture02'])

    def test_history_archive_copies_complete_files_without_moving_or_duplicating(self):
        import threading, urllib.error, urllib.request
        from deeptalk_studio.webui import make_server
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root);self.fail_video=False
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']='';save_settings(root,config)
            original=self.tool.process(self.tool.start(['BV1fixture01'])['session_id'],consent=True)
            item=original['items'][0]
            old_media=Path(item['media_path']);old_txt=Path(item['artifact_path']);old_json=Path(item['json_path'])
            old_bytes={path:path.read_bytes() for path in (old_media,old_txt,old_json)}
            save_root=root/'new archive';save_root.mkdir()
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)
            server=make_server(port=0,output_dir=root,provider_factory=lambda:None,flow=flow)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            def post(action,data):
                request=urllib.request.Request(base+'/api/workbench/transcripts/'+action,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
                try:
                    response=urllib.request.urlopen(request)
                    return response.status,json.load(response)
                except urllib.error.HTTPError as exc:
                    return exc.code,json.load(exc)
            try:
                status,archived=post('archive',{'session_id':original['session_id']})
                self.assertEqual(status,200,archived)
                batch=Path(archived['batch_path']);self.assertEqual(batch.parent,save_root.resolve())
                copied=archived['items'][0]['save_paths'];new_media=Path(copied['video'])
                new_txt=Path(copied['transcript_txt']);new_json=Path(copied['transcript_json'])
                self.assertEqual(new_media.parent,batch/'视频');self.assertTrue(new_media.stem.endswith('-12345播放'))
                self.assertEqual(new_txt.parent,batch/'口播稿');self.assertEqual(new_json.parent,batch/'口播稿')
                self.assertEqual(new_media.read_bytes(),old_bytes[old_media])
                self.assertEqual(new_txt.read_bytes(),old_bytes[old_txt])
                self.assertEqual(new_json.read_bytes(),old_bytes[old_json])
                self.assertEqual((batch/'合并参考稿.txt').read_text(encoding='utf-8'),archived['combined_text'])
                status,repeated=post('archive',{'session_id':original['session_id']})
                self.assertEqual(status,200,repeated);self.assertEqual(repeated['batch_path'],str(batch))
                self.assertEqual([p.read_bytes() for p in (old_media,old_txt,old_json)],[old_bytes[p] for p in (old_media,old_txt,old_json)])
            finally:server.shutdown();server.server_close();thread.join()

    def test_open_folder_route_opens_only_the_session_saved_path(self):
        import threading, urllib.error, urllib.request
        from deeptalk_studio.webui import make_server
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root);save_root=root/'selected';save_root.mkdir()
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)
            state=self.tool.start(['BV1fixture01']);opened=[]
            server=make_server(port=0,output_dir=root,provider_factory=lambda:None,flow=flow)
            server.transcripts.open_folder=lambda sid:opened.append(sid) or {'path':state['batch_path']}
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            try:
                request=urllib.request.Request(base+'/api/workbench/transcripts/open-folder',data=json.dumps({'session_id':state['session_id']}).encode(),headers={'Content-Type':'application/json'})
                try:
                    response=urllib.request.urlopen(request);status=response.status;result=json.load(response)
                except urllib.error.HTTPError as exc:
                    status=exc.code;result=json.load(exc)
                self.assertEqual(status,200,result)
                self.assertEqual(opened,[state['session_id']])
                self.assertEqual(result['path'],state['batch_path'])
            finally:server.shutdown();server.server_close();thread.join()

    def test_history_archive_never_follows_a_symlinked_transcript(self):
        import threading, urllib.error, urllib.request
        from deeptalk_studio.webui import make_server
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root);self.fail_video=False
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']='';save_settings(root,config)
            result=self.tool.process(self.tool.start(['BV1fixture01'])['session_id'],consent=True)
            sid=result['session_id'];source=flow.store.references_dir(sid)/'BV1fixture01'/'transcript.json'
            outside=root/'outside.json';outside.write_text('{"text":"private outside content"}',encoding='utf-8')
            source.unlink();source.symlink_to(outside)
            save_root=root/'new archive';save_root.mkdir()
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)
            server=make_server(port=0,output_dir=root,provider_factory=lambda:None,flow=flow)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            try:
                request=urllib.request.Request(base+'/api/workbench/transcripts/archive',data=json.dumps({'session_id':sid}).encode(),headers={'Content-Type':'application/json'})
                try:
                    response=urllib.request.urlopen(request);status=response.status;archived=json.load(response)
                except urllib.error.HTTPError as exc:
                    status=exc.code;archived=json.load(exc)
                self.assertEqual(status,200,archived)
                batch=Path(archived['batch_path'])
                self.assertFalse(any((batch/'口播稿').iterdir()))
                self.assertIn('未完成 / 失败',(batch/'合并参考稿.txt').read_text(encoding='utf-8'))
                self.assertEqual(outside.read_text(encoding='utf-8'),'{"text":"private outside content"}')
            finally:server.shutdown();server.server_close();thread.join()

    def test_history_archive_preserves_manual_transcript_edits_and_original_json(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root)
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']='';save_settings(root,config)
            result=self.tool.process(self.tool.start(['BV1fixture01'])['session_id'],consent=True)
            sid=result['session_id'];item=result['items'][0]
            source_txt=Path(item['artifact_path']);source_json=Path(item['json_path'])
            edited_bytes=source_txt.read_bytes()+ '\nOwner 手工校订必须保留。'.encode('utf-8')
            json_bytes=source_json.read_bytes()
            local_merge=flow.store.session_dir(sid)/'合并参考稿.txt'
            edited_merge_bytes=local_merge.read_bytes()+'\nOwner 合并稿备注必须保留。'.encode('utf-8')
            source_txt.write_bytes(edited_bytes)
            local_merge.write_bytes(edited_merge_bytes)
            save_root=root/'selected archive';save_root.mkdir()
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)

            state=self.tool.state(sid)
            self.assertEqual(source_txt.read_bytes(),edited_bytes)
            self.assertEqual(local_merge.read_bytes(),edited_merge_bytes)
            self.assertIn('Owner 手工校订必须保留。',state['items'][0]['text'])
            archived=self.tool.archive(sid)
            paths=archived['items'][0]['save_paths']
            self.assertEqual(Path(paths['transcript_txt']).read_bytes(),edited_bytes)
            self.assertEqual(Path(paths['transcript_json']).read_bytes(),json_bytes)
            self.assertEqual(source_txt.read_bytes(),edited_bytes)
            self.assertEqual(local_merge.read_bytes(),edited_merge_bytes)
            self.assertEqual(source_json.read_bytes(),json_bytes)

    def test_history_archive_rejects_symlinked_per_video_directory(self):
        import shutil
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);flow=self.setup_tool(root)
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']='';save_settings(root,config)
            result=self.tool.process(self.tool.start(['BV1fixture01'])['session_id'],consent=True)
            sid=result['session_id'];media=Path(result['items'][0]['media_path'])
            video_dir=flow.store.references_dir(sid)/'BV1fixture01'
            outside=root/'outside-reference';shutil.copytree(video_dir,outside)
            video_dir.unlink() if video_dir.is_symlink() else shutil.rmtree(video_dir)
            video_dir.symlink_to(outside,target_is_directory=True)
            save_root=root/'selected archive';save_root.mkdir()
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)

            archived=self.tool.archive(sid)
            self.assertEqual(list((Path(archived['batch_path'])/'视频').iterdir()),[])
            self.assertTrue(media.is_file())
            self.assertTrue((outside/'acquisition.json').is_file())

    def test_retry_after_save_root_is_set_allocates_a_task_subfolder(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);self.setup_tool(root)
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']='';save_settings(root,config)
            pending=self.tool.start(['BV1fixture01'])
            save_root=root/'selected save';save_root.mkdir()
            config=load_settings(root);config['downloads_dir']=str(save_root);save_settings(root,config)

            completed=self.tool.process(pending['session_id'],consent=True)
            batch=Path(completed['batch_path']);media=Path(completed['items'][0]['save_paths']['video'])
            self.assertEqual(batch.parent,save_root.resolve())
            self.assertEqual(media.parent,batch/'视频')
            self.assertEqual(len(list(save_root.iterdir())),1)

    def test_proxy_refusal_guidance_does_not_change_saved_settings(self):
        from deeptalk_studio.workbench.acquisition import WorkbenchAcquisitionError, acquire_reference
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);self.setup_tool(root)
            from deeptalk_studio.workbench.settings import load_settings
            before=load_settings(root)
            reference={'bvid':'BV1proxy01','url':'https://www.bilibili.com/video/BV1proxy01','title':'proxy fixture','view_count_status':'verified','view_count_source':'per_video_api','view_count':123}
            runner=lambda cmd,**kwargs:subprocess.CompletedProcess(cmd,1,'','ProxyError: HTTPConnectionPool(host=127.0.0.1, port=7897): Connection refused')
            with self.assertRaises(WorkbenchAcquisitionError) as ctx:
                acquire_reference(reference,root,FiveTranscripts.CONSENT if hasattr(FiveTranscripts,'CONSENT') else '我授权本机分析本批视频',runner=runner)
            message=str(ctx.exception)
            self.assertIn('代理',message);self.assertIn('127.0.0.1:7897',message)
            self.assertIn('检查',message);self.assertIn('不会自动关闭或绕过代理',message)
            self.assertNotIn('Whisper',message)
            self.assertEqual(load_settings(root),before)

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
