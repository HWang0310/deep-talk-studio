"""Offline regressions for PR #48 final remix contract. No Owner data/network."""
import json
import subprocess
import tempfile
import time
from pathlib import Path
from unittest import mock

from tests import test_workbench as helpers
from tests.test_workbench import _UserSettingsIsolatedTestCase
from deeptalk_studio.workbench.creative_chat import CreativeChatStore, CreativeChatError
from deeptalk_studio.workbench.flow import WorkbenchFlow
from deeptalk_studio.workbench import acquisition


class RemixIsolationTests(_UserSettingsIsolatedTestCase):
    _configure = helpers.TopicFirstChatTests._configure
    _flow = helpers.TopicFirstChatTests._flow
    CapturingLLM = helpers.TopicFirstChatTests.CapturingLLM
    def test_topic_switch_draft_context_and_reload(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            calls = []
            def search(topic):
                calls.append(topic)
                return {'status': 'ok', 'sources': [{'title': topic, 'url': 'https://example.org/'+topic}]}
            llm = self.CapturingLLM(['完整原创稿'])
            flow = self._flow(root, llm, search)
            a = flow.chat_send_start('我想就苹果做个视频', new_session=True)
            sid = a['session']['session_id']
            list(flow.chat_stream_reply(a))
            b = flow.chat_send_start('我想就香蕉做个视频', session_id=sid)
            list(flow.chat_stream_reply(b))
            flow.chat_draft_generate(sid)
            context = json.dumps(llm.seen[-1], ensure_ascii=False)
            self.assertIn('香蕉', context)
            self.assertNotIn('苹果', context)
            self.assertEqual(calls, ['苹果', '香蕉'])
            restored = flow.chat_state(sid)['chat']
            self.assertEqual([d['query'] for d in restored['topic_discoveries']], ['苹果', '香蕉'])
            self.assertEqual([d['turn_id'] for d in restored['topic_discoveries']], ['t1', 't3'])

    def test_timeout_is_bounded_and_late_result_cannot_replace_unavailable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            def slow(topic):
                time.sleep(.15)
                return {'status':'ok','sources':[{'title':'late'}]}
            flow = self._flow(root, self.CapturingLLM(['回复']), slow)
            flow.TOPIC_SEARCH_TIMEOUT = .02
            started = time.monotonic()
            context = flow.chat_send_start('我想就香蕉做个视频')
            self.assertLess(time.monotonic()-started, .12)
            self.assertEqual(context['session']['topic_discovery']['status'], 'unavailable')
            time.sleep(.18)
            self.assertEqual(flow.chat_state(context['session']['session_id'])['chat']['topic_discovery']['status'], 'unavailable')


class RemixStoreTests(_UserSettingsIsolatedTestCase):
    def test_rename_trash_restore_and_symlink(self):
        with tempfile.TemporaryDirectory() as raw:
            store = CreativeChatStore(Path(raw))
            a, b = store.new_session(), store.new_session()
            sid = a['session_id']
            store.manage_session(sid, 'rename', '我的吐槽')
            self.assertEqual(store.list_sessions()[0]['title'], '我的吐槽')
            store.manage_session(sid, 'delete')
            self.assertNotIn(sid, [s['session_id'] for s in store.list_sessions()])
            self.assertEqual(len(store.list_sessions(deleted=True)), 1)
            with self.assertRaises(CreativeChatError):
                store.append_assistant_turn(sid, 'late')
            store.manage_session(sid, 'restore')
            self.assertEqual(store.load(sid)['custom_title'], '我的吐槽')
            self.assertEqual(store.load(b['session_id'])['turns'], [])
            path = store._session_path(sid)
            path.unlink()
            outside = Path(raw)/'outside.json'
            outside.write_text(json.dumps(a))
            path.symlink_to(outside)
            with self.assertRaises(CreativeChatError):
                store.manage_session(sid, 'delete')
            self.assertEqual(json.loads(outside.read_text()), a)


class RemixDownloadTests(_UserSettingsIsolatedTestCase):
    def test_download_template_count_merge_and_unknown(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for verified, count, marker in [(True,123456,'123456播放'),(False,999,'播放量未知')]:
                ref = {'bvid':'BV1fixture01','url':'https://www.bilibili.com/video/BV1fixture01','title':'标题',
                       'view_count':count,'view_count_status':'verified' if verified else 'unverified','view_count_source':'per_video_api' if verified else 'search_result'}
                def runner(cmd, **kwargs):
                    template = cmd[cmd.index('-o')+1]
                    self.assertTrue(template.endswith('-'+marker+'.%(ext)s'))
                    path = Path(template.replace('%(ext)s','mp4'))
                    path.write_bytes(b'fixture media')
                    return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path.with_suffix('.webm'))}), '')
                result = acquisition.acquire_reference(ref,root,'我授权在本地学习参考视频',runner=runner)
                self.assertTrue(result['media_path'].endswith('-'+marker+'.mp4'))

class RemixReferenceTests(_UserSettingsIsolatedTestCase):
    def test_complete_transcript_export_idempotence_and_safe_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            flow = WorkbenchFlow(Path(raw))
            bvid = 'BV1fixture01'
            session = flow.store.create('香蕉', [{'bvid':bvid,'title':'香蕉研究','url':'https://www.bilibili.com/video/'+bvid}], None)
            sid = session['session_id']
            refdir = flow.store.references_dir(sid)/bvid
            refdir.mkdir()
            original = {'text':'完整全文尾部', 'segments':[{'start_seconds':i,'end_seconds':i+1,'text':'第%d句'%i} for i in range(250)], 'model':'fixture-whisper', 'transcript_provenance':{'source_media_sha256':'digest','transcribed_at':'fixture-time'}}
            (refdir/'transcript.json').write_text(json.dumps(original))
            exported = flow.reference_transcript(sid,bvid)
            self.assertEqual(len(exported['transcript']['segments']),250)
            self.assertIn('完整全文尾部', exported['text'])
            self.assertIn('digest',exported['text'])
            self.assertEqual(json.loads((refdir/'transcript.json').read_text()), original)
            txt = Path(exported['artifact_path'])
            stamp = txt.stat().st_mtime_ns
            self.assertEqual(flow.reference_transcript(sid,bvid)['artifact_path'],str(txt))
            self.assertEqual(txt.stat().st_mtime_ns,stamp)
            with self.assertRaises(Exception):
                flow.reference_transcript(sid,'../../outside')

    def test_workspace_binding_and_summary_only_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            helpers.TopicFirstChatTests._configure(self,root)
            llm=helpers.TopicFirstChatTests.CapturingLLM(['【犀利吐槽】完整稿一【搞笑玩梗】完整稿二【故事反转】完整稿三'])
            flow=WorkbenchFlow(root,provider_factory=lambda settings:llm,topic_search=lambda t:{'status':'ok','sources':[{'bvid':'BV1fixture01','title':t,'url':'https://www.bilibili.com/video/BV1fixture01'}]})
            ctx=flow.chat_send_start('我想就香蕉做个视频',new_session=True)
            sid=ctx['session']['session_id']
            list(flow.chat_stream_reply(ctx))
            workspace=flow.chat_references(sid,'t1')
            self.assertEqual(flow.chat_references(sid,'t1')['session_id'], workspace['session_id'])
            refdir=flow.store.references_dir(workspace['session_id'])/'BV1fixture01'
            refdir.mkdir()
            study=refdir/'study.json'
            study.write_text(json.dumps({'narrative_summary':'先抛反差再反转','creator_viewpoint':'流量焦虑','hook_text':'PROTECTED_FULL_TEXT','analysis_status':'analyzed'}))
            flow.store.update(workspace['session_id'],lambda s:s['references'].update({'BV1fixture01':{'status':'analyzed','study_path':str(study)}}))
            flow.chat_draft_generate(sid)
            context=json.dumps(llm.seen[-1],ensure_ascii=False)
            self.assertIn('先抛反差再反转',context)
            self.assertNotIn('PROTECTED_FULL_TEXT',context)
            self.assertIn('三篇完整',context)

from tests import test_webui as webhelpers

class RemixHttpTests(webhelpers.LocalWebUITestCase):
    def test_manage_and_transcript_routes_boundaries_and_flight_safety(self):
        with tempfile.TemporaryDirectory() as raw:
            flow=WorkbenchFlow(Path(raw))
            session=flow.creative.new_session()
            sid=session['session_id']
            self.start_server(flow=flow)
            status,_,_=self.post('/api/workbench/chat/manage',{'session_id':sid,'action':'rename','title':'新标题'})
            self.assertEqual(status,200)
            self.server.chat_in_flight.add(sid)
            status,_,_=self.post('/api/workbench/chat/manage',{'session_id':sid,'action':'delete'})
            self.assertEqual(status,409)
            self.assertFalse(flow.creative.load(sid).get('deleted_at'))
            self.server.chat_in_flight.clear()
            self.assertEqual(self.post('/api/workbench/chat/manage',{'session_id':sid,'action':'delete'})[0],200)
            self.assertEqual(self.post('/api/workbench/chat/manage',{'session_id':sid,'action':'restore'})[0],200)
            self.assertEqual(self.post('/api/workbench/chat/manage',{'session_id':'../../evil','action':'delete'})[0],400)
            self.assertEqual(self.post('/api/workbench/references/transcript',{'session_id':'../../evil','bvid':'x'})[0],400)

class RemixWhisperTests(_UserSettingsIsolatedTestCase):
    def test_missing_whisper_does_not_bootstrap_or_install(self):
        from deeptalk_studio.transcription.local_whisper_cpp import WhisperCppBootstrap
        with tempfile.TemporaryDirectory() as raw:
            bootstrap=WhisperCppBootstrap(cache_root=Path(raw))
            with mock.patch.object(WhisperCppBootstrap,'ensure') as ensure:
                with mock.patch('deeptalk_studio.transcription.local_whisper_cpp.WhisperCppBootstrap',return_value=bootstrap):
                    with self.assertRaisesRegex(acquisition.WorkbenchAcquisitionError,'尚未安装'):
                        acquisition.transcribe_audio(Path(raw)/'voice.wav')
                ensure.assert_not_called()

    def test_real_whisper_full_json_offsets_preserved(self):
        with tempfile.TemporaryDirectory() as raw:
            wav=Path(raw)/'voice.wav'; wav.write_bytes(b'fixture')
            class Installation:
                runtime_path='fixture';model_path='fixture';dtw_preset='none';model_name='fixture';runtime_version='fixture'
            class Bootstrap:
                def ensure(self):return Installation()
            def runner(cmd,**kwargs):
                Path(cmd[cmd.index('--output-file')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':1250,'to':3500},'text':'完整语音'}]}))
                return subprocess.CompletedProcess(cmd,0,'','')
            result=acquisition.transcribe_audio(wav,bootstrap=Bootstrap(),runner=runner)
            self.assertEqual(result['segments'][0]['start_seconds'],1.25)
            self.assertEqual(result['segments'][0]['end_seconds'],3.5)

class RemixAdditionalIsolationTests(_UserSettingsIsolatedTestCase):
    def test_unavailable_b_retry_and_legacy_notes_are_isolated(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);helpers.TopicFirstChatTests._configure(self,root)
            calls=[]
            def search(t):
                calls.append(t)
                return {'status':'unavailable','note':'B-only failure'} if t=='香蕉' else {'status':'ok','sources':[{'title':t,'url':'https://example.org/APPLE_ONLY'}]}
            llm=helpers.TopicFirstChatTests.CapturingLLM(['回复'])
            flow=WorkbenchFlow(root,provider_factory=lambda s:llm,topic_search=search)
            a=flow.chat_send_start('我想就苹果做个视频',new_session=True);sid=a['session']['session_id'];list(flow.chat_stream_reply(a))
            legacy=flow.creative.load(sid);legacy.pop('topic_discoveries');flow.creative.save(legacy)
            b=flow.chat_send_start('我想就香蕉做个视频',session_id=sid)
            retry=flow.chat_send_start('',session_id=sid,retry_turn_id=b['user_turn']['turn_id'])
            events=list(flow.chat_stream_reply(retry))
            self.assertEqual(events[0]['query'],'香蕉')
            self.assertEqual(calls,['苹果','香蕉'])
            self.assertNotIn('APPLE_ONLY',json.dumps(llm.seen[-1]))
            flow.chat_draft_generate(sid)
            self.assertNotIn('APPLE_ONLY',json.dumps(llm.seen[-1]))
            self.assertIn('未联网核实',json.dumps(llm.seen[-1],ensure_ascii=False))
            restored=WorkbenchFlow(root).chat_state(sid)['chat']
            self.assertEqual(len(restored['topic_discoveries']),2)
            other=flow.chat_send_start('我想就香蕉做个视频',new_session=True)
            self.assertNotEqual(other['session']['session_id'],sid)
            self.assertEqual(calls,['苹果','香蕉','香蕉'])

    def test_new_download_preserves_collision_and_rejects_external_return(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);ref={'bvid':'BV1fixture01','title':'标题','url':'https://www.bilibili.com/video/BV1fixture01'}
            old=root/'标题-BV1fixture01-播放量未知.mp4';old.write_bytes(b'OWNER')
            def runner(cmd,**kw):
                path=Path(cmd[cmd.index('-o')+1].replace('%(ext)s','mp4'))
                self.assertNotEqual(path,old);path.write_bytes(b'new')
                return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path)}),'')
            acquisition.acquire_reference(ref,root,'我授权本地学习参考',runner=runner)
            self.assertEqual(old.read_bytes(),b'OWNER')
            outside=root.parent/'external-reference.mp4'
            outside.write_bytes(b'outside')
            try:
                with self.assertRaises(acquisition.WorkbenchAcquisitionError):
                    acquisition.acquire_reference(ref,root,'我授权本地学习参考',runner=lambda *a,**k:subprocess.CompletedProcess([],0,json.dumps({'_filename':str(outside)}),''))
            finally:outside.unlink()

class RemixDraftRevisionTests(_UserSettingsIsolatedTestCase):
    def test_followup_edits_use_current_saved_draft_but_never_old_topic_draft(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);helpers.TopicFirstChatTests._configure(self,root)
            llm=helpers.TopicFirstChatTests.CapturingLLM(['三篇完整稿'])
            flow=WorkbenchFlow(root,provider_factory=lambda s:llm)
            ctx=flow.chat_send_start('我想就香蕉做个视频',new_session=True);sid=ctx['session']['session_id'];list(flow.chat_stream_reply(ctx))
            flow.chat_draft_generate(sid)
            flow.chat_draft_save('UNIQUE_SAVED_DRAFT 香蕉吐槽稿',sid)
            change=flow.chat_send_start('把吐槽版改得更损点',session_id=sid)
            list(flow.chat_stream_reply(change))
            self.assertIn('UNIQUE_SAVED_DRAFT',json.dumps(llm.seen[-1]))
            b=flow.chat_send_start('我想就苹果做个视频',session_id=sid)
            list(flow.chat_stream_reply(b))
            self.assertNotIn('UNIQUE_SAVED_DRAFT',json.dumps(llm.seen[-1]))

class RemixReanalysisTests(_UserSettingsIsolatedTestCase):
    def test_reopening_completed_analysis_does_not_call_paid_model_again(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);bvid='BV1fixture01';media=root/'fixture.mp4';media.write_bytes(b'fixture')
            factory=mock.Mock(side_effect=AssertionError('duplicate paid call'))
            flow=WorkbenchFlow(root,provider_factory=factory)
            sid=flow.store.create('香蕉',[{'bvid':bvid,'title':'香蕉','url':'https://www.bilibili.com/video/'+bvid}],None)['session_id']
            refdir=flow.store.references_dir(sid)/bvid;refdir.mkdir()
            (refdir/'transcript.json').write_text(json.dumps({'text':'完整转写','segments':[]}))
            study=refdir/'study.json';study.write_text(json.dumps({'analysis_status':'analyzed','narrative_summary':'已有叙事摘要'}))
            flow.store.update(sid,lambda s:s['references'].update({bvid:{'status':'analyzed','media_path':str(media),'study_path':str(study)}}))
            self.assertEqual(flow.analyze_reference(sid,bvid)['study']['narrative_summary'],'已有叙事摘要')
            factory.assert_not_called()
