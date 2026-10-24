"""Owner journey regressions; isolated HOME/settings/history, offline providers."""
import json
import subprocess
import tempfile
from pathlib import Path
from unittest import mock
from tests import test_workbench as fixtures
from deeptalk_studio.workbench.flow import WorkbenchFlow, WorkbenchFlowError

class OwnerFlowTests(fixtures._UserSettingsIsolatedTestCase):
    def setup_flow(self, root):
        fixtures.TopicFirstChatTests._configure(self,root)
        self.llm=fixtures.TopicFirstChatTests.CapturingLLM(['【犀利吐槽】完整稿一。\n【搞笑玩梗】完整稿二。\n【故事反转】完整稿三。'])
        self.flow=WorkbenchFlow(root,provider_factory=lambda s:self.llm,topic_search=lambda t:{'status':'ok','sources':[{'title':t,'url':'https://www.bilibili.com/video/BV1fixture01','bvid':'BV1fixture01','view_count':987654,'view_count_status':'verified','view_count_source':'per_video_api'}]})
        context=self.flow.chat_send_start('我想做一期王扁被打的视频',new_session=True)
        self.sid=context['session']['session_id']
        return context

    def test_topic_stops_at_actionable_preview_without_paid_generation(self):
        with tempfile.TemporaryDirectory() as raw:
            context=self.setup_flow(Path(raw));events=list(self.flow.chat_stream_reply(context))
            self.assertEqual(self.llm.seen,[])
            output=''.join(e.get('text','') for e in events)
            self.assertIn('选参考',output)
            self.assertNotIn('【犀利吐槽】',output)
            self.assertEqual(self.flow.chat_state(self.sid)['chat']['creation']['mode'],'pending')
            with self.assertRaisesRegex(WorkbenchFlowError,'分析|自由创作'):
                self.flow.chat_draft_generate(self.sid)
            self.assertEqual(self.llm.seen,[])

    def test_bare_topic_metadata_survives_reload_and_keeps_casual_chat_normal(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);self.setup_flow(root)
            context=self.flow.chat_send_start('王扁被打',creation_topic='王扁被打',new_session=True)
            list(self.flow.chat_stream_reply(context))
            sid=context['session']['session_id']
            self.assertEqual(self.flow.chat_state(sid)['chat']['creation']['topic'],'王扁被打')
            self.assertEqual(self.llm.seen,[])
            casual=self.flow.chat_send_start('你好，随便聊聊',new_session=True)
            list(self.flow.chat_stream_reply(casual))
            self.assertEqual(len(self.llm.seen),1)

    def test_explicit_skip_is_labeled_and_never_claims_reference_analysis(self):
        with tempfile.TemporaryDirectory() as raw:
            context=self.setup_flow(Path(raw));list(self.flow.chat_stream_reply(context))
            result=self.flow.chat_create(self.sid,'t1',[],mode='topic_only')
            self.assertIn('仅按选题',result['draft']['content'])
            self.assertEqual(len(self.llm.seen),1)
            self.assertEqual(result['chat']['creation']['mode'],'topic_only')
            self.assertIn('未分析参考视频',json.dumps(self.llm.seen[-1],ensure_ascii=False))
            self.assertTrue(all(d['status']=='unreviewed' for d in result['chat']['drafts']))

    def test_consent_and_real_completed_asr_are_required_before_video_draft(self):
        with tempfile.TemporaryDirectory() as raw:
            context=self.setup_flow(Path(raw));list(self.flow.chat_stream_reply(context))
            with self.assertRaisesRegex(WorkbenchFlowError,'授权|确认'):
                self.flow.chat_create(self.sid,'t1',['BV1fixture01'],consent=False)
            workspace=self.flow.chat_references(self.sid,'t1')
            # A model study without a persisted transcript is insufficient.
            refdir=self.flow.store.references_dir(workspace['session_id'])/'BV1fixture01';refdir.mkdir()
            study=refdir/'study.json';study.write_text(json.dumps({'analysis_status':'analyzed','narrative_summary':'声称分析成功'}))
            self.flow.store.update(workspace['session_id'],lambda s:s['references'].update({'BV1fixture01':{'status':'analyzed','study_path':str(study)}}))
            with self.assertRaisesRegex(WorkbenchFlowError,'转写|分析'):
                self.flow.chat_draft_generate(self.sid)
            self.assertEqual(self.llm.seen,[])
            (refdir/'transcript.json').write_text(json.dumps({'text':'完整ASR仍然保留','segments':[]}))
            study.write_text(json.dumps({'analysis_status':'unverified','narrative_summary':''}))
            self.flow.store.update(workspace['session_id'],lambda s:s['references']['BV1fixture01'].update({'status':'unverified','analysis_error':'fixture analysis failure'}))
            state=self.flow.chat_state(self.sid)['chat']['creation']
            self.assertEqual(state['transcribed_bvids'],['BV1fixture01'])
            self.assertEqual(state['ready_bvids'],[])
            self.assertFalse(state['can_generate'])

    def test_authorized_pipeline_reports_actual_phases_then_creates_three_scripts(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);context=self.setup_flow(root);list(self.flow.chat_stream_reply(context))
            from deeptalk_studio.workbench.settings import load_settings,save_settings
            config=load_settings(root);config['downloads_dir']=str(root);save_settings(root,config)
            def acquire(cmd,**kw):
                path=Path(cmd[cmd.index('-o')+1].replace('%(ext)s','mp4'));path.write_bytes(b'fixture-video')
                return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path)}),'')
            def audio(cmd,**kw):
                Path(cmd[-1]).write_bytes(b'RIFF'+b'0'*100);return subprocess.CompletedProcess(cmd,0,'','')
            def whisper(cmd,**kw):
                Path(cmd[cmd.index('--output-file')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':0,'to':2000},'text':'合成夹具口播：反差开场，吐槽注意力，再反转收尾。'}]}))
                return subprocess.CompletedProcess(cmd,0,'','')
            class Installation:
                runtime_path='fixture';model_path='fixture';dtw_preset='none';model_name='fixture';runtime_version='fixture'
            class Bootstrap:
                def ensure(self):return Installation()
            self.flow.acquire_runner=acquire;self.flow.audio_runner=audio;self.flow.whisper_runner=whisper;self.flow.whisper_bootstrap=Bootstrap()
            self.llm.summarize_reference=fixtures.FakeWorkbenchLLM({}).summarize_reference
            phases=[]
            result=self.flow.chat_create(self.sid,'t1',['BV1fixture01'],consent=True,progress=lambda e:phases.append(e['phase']))
            self.assertEqual(phases,['downloading','extracting','transcribing','analyzing','generating'])
            self.assertIn('基于已分析参考',result['draft']['content'])
            self.assertEqual(len(self.llm.seen),1)
            self.assertEqual(result['chat']['creation']['ready_bvids'],['BV1fixture01'])
            self.assertTrue(result['chat']['creation']['has_draft'])
            self.assertIn('三',result['chat']['turns'][-1]['content'])
            transcript=self.flow.reference_transcript(result['chat']['creation']['reference_session_id'],'BV1fixture01')
            self.assertIn('合成夹具口播',transcript['text'])
            # A partly completed multi-reference batch cannot borrow the first one's readiness.
            self.flow.creative.set_creation_mode(self.sid,'王扁被打','pending',['BV1fixture01','BV1fixture02'])
            self.assertFalse(self.flow.chat_state(self.sid)['chat']['creation']['can_generate'])
            with self.assertRaises(WorkbenchFlowError):
                self.flow.chat_draft_generate(self.sid)
            # Explicit topic-only switch must not inject an old analysis block.
            self.flow.chat_draft_generate(self.sid, mode='topic_only')
            self.assertNotIn('【本选题参考创作灵感】',json.dumps(self.llm.seen[-1],ensure_ascii=False))
            self.flow.creative.set_creation_mode(self.sid,'王扁被打','reference',['BV1fixture01'])
            (Path(transcript['artifact_path']).parent/'transcript.json').unlink()
            before=len(self.llm.seen)
            list(self.flow.chat_stream_reply(self.flow.chat_send_start('改得更好玩',session_id=self.sid)))
            self.assertEqual(len(self.llm.seen),before)

from tests import test_webui as http_fixtures

class OwnerFlowHttpTests(http_fixtures.LocalWebUITestCase):
    def test_creation_route_scoped_consent_flight_guard_and_done(self):
        with tempfile.TemporaryDirectory() as raw:
            context=OwnerFlowTests.setup_flow(self,Path(raw));list(self.flow.chat_stream_reply(context))
            self.start_server(flow=self.flow)
            data={'session_id':self.sid,'turn_id':'t1','bvids':['BV1fixture01']}
            self.assertEqual(self.post('/api/workbench/chat/create',data)[0],400)
            data['mode']='topic_only'
            self.server.chat_in_flight.add(self.sid)
            self.assertEqual(self.post('/api/workbench/chat/create',data)[0],409)
            self.server.chat_in_flight.clear()
            status,headers,body=self.post('/api/workbench/chat/create',data)
            self.assertEqual(status,200)
            events=[json.loads(block[6:]) for block in body.split('\n\n') if block.startswith('data: ')]
            self.assertEqual(events[0]['phase'],'generating')
            self.assertEqual(events[-1]['type'],'done')
            self.assertEqual(events[-1]['chat']['creation']['mode'],'topic_only')
            self.assertNotIn(self.sid,self.server.chat_in_flight)
