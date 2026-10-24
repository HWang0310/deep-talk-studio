"""Disposable browser trial: python serve_fixture.py [--port 8323] [--real-model].

Sources, metadata, yt-dlp, ffmpeg and Whisper are explicitly synthetic fixtures.
--real-model reuses saved settings READ ONLY, with max four model calls, but
keeps all chat/media under a temporary root. Never imports test modules.
"""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
from deeptalk_studio.webui import make_server, _default_topic_search
from deeptalk_studio.workbench import settings, creative_chat
from deeptalk_studio.workbench.flow import WorkbenchFlow
from deeptalk_studio.workbench.llm import WorkbenchLLM
from deeptalk_studio.bilibili_reference_provider import SearchItem, SearchOutcome, VideoMetadataOutcome
from deeptalk_studio.providers.base import ProviderResult
from deeptalk_studio.provenance import ProviderProvenance

args = argparse.ArgumentParser()
args.add_argument('--port', type=int, default=8323)
args.add_argument('--real-model', action='store_true')
args.add_argument('--root', type=Path)
args.add_argument('--phase-delay', type=float, default=0)
options = args.parse_args()
root = options.root or Path(tempfile.mkdtemp(prefix='deeptalk-remix-trial-'))
(root/'downloads').mkdir(exist_ok=True)
creative_chat.USER_CHAT_DIR = root
if not options.real_model:
    settings.USER_SETTINGS_DIR = root
    settings.save_settings(root, settings.apply_settings_update(settings.load_settings(root), {
        'provider_mode':'deepseek','api_key':'fixture-not-a-real-key','downloads_dir':str(root/'downloads')}))
# Real-model trial overrides ONLY the effective download folder in memory.
original_settings = settings.load_settings
if options.real_model:
    import deeptalk_studio.workbench.flow as flow_module
    flow_module.load_settings = lambda repo: {**original_settings(repo), 'downloads_dir':str(root/'downloads')}

class Provider:
    def search_videos(self, query, page=1):
        return SearchOutcome(status='ok',items=tuple(SearchItem(bvid=b,title=query+' · 合成来源夹具 '+str(i),uploader='离线验收夹具',published_at='2026-10-24',snippet_view_count=99999999) for i,b in enumerate(['BV1fixture01','BV1fixture02'])),http_status=200,api_code=0)
    def fetch_video_metadata(self,bvid):
        return VideoMetadataOutcome(status='ok',title=active_topic[0]+' · 合成来源夹具 '+bvid[-2:],uploader='离线验收夹具',published_at='2026-10-24',view_count=123456 if bvid.endswith('01') else 987654,duration_sec=250,api_code=0)
active_topic=['']
searches=[]
def search(topic):
    searches.append(topic)
    (root/'search-count.json').write_text(json.dumps(searches))
    active_topic[0]=topic
    time.sleep(6 if '超时' in topic else 1.5)
    if '无参考' in topic or topic == '检索失败':return {'status':'unavailable','note':'刻意模拟检索失败'}
    outcome=_default_topic_search(Provider)(topic)
    for source in outcome.get('sources',[]):source['retrieval_note']='SYNTHETIC FIXTURE — not real platform metadata'
    return outcome

fixture_script='''【犀利吐槽】
现在的热搜像什么？像小区电梯，谁都能按两下，谁也不负责送你到真相那层。网上这事传得热闹，我最想吐槽的却是围观区的上班纪律：正主还没更新，解说已经排好早晚班了。第一班负责震惊，第二班负责内幕，第三班说前两班都不懂。三拨人各唱各的，唯一团建项目就是催你点关注。咱们脑补个小剧场：热点问运营，我今天能休息吗？运营说可以，先拍一期你为什么休息。看懂没有？流量最怕的不是事情没反转，是你把手机放下了。我不替谁判输赢，我就一个观点：热闹可以看，情绪别包年。人家做的是更新计划，你交的是心情月供。等你终于拼出前因后果，下一条热搜已经在电梯口招手。下回见到“最后一次回应”，你先别感动，可能只是今天最后一次。

【搞笑玩梗】
互联网有一种健身，叫吃瓜：手指走一万步，脑子还在被窝。一个话题上热搜，评论区立刻启动人才招聘。懂一点的当军师，完全不懂的当总指挥，我负责把瓜切成九宫格，显得参与度很高。这是脑补段子：瓜摊老板问要几成熟？网友说不要熟，要反转。我原来以为吃瓜是消遣，后来才知道这是连续剧订阅：今天站队，明天撤回，后天发一条“早就觉得不对劲”。好家伙，互联网人均天气预报，昨天的大雨今天说自己一直支持晴天。我的看法很简单，乐子值得拥有，情绪不用加仓。看完能笑两声就收工，别为了一个不认识的人，把自己的午休整成季度复盘。瓜再甜也不能代替饭；你饿着肚子主持公道的时候，人家的账号已经接上晚饭广告了。

【故事反转】
我本来打算做一期热点分析，结果先被自己的浏览记录分析了。第一条告诉我事情不简单，第二条说所有人都被骗了，第三条说第二条才在骗。看了半小时，我唯一确定的事，是我下的面已经坨了。我以为自己在追剧情，后来发现，我才是每集都准时出场的固定嘉宾。脑补一下，平台给我发演员证：角色，愤怒观众；片酬，凌晨两点的黑眼圈。转折就在这儿——我们嘴上笑网红离不开流量，手却替流量按了下一集。真正该反转的不是今天站哪边，是我能不能把注意力的遥控器拿回来。网上的说法先让它飞，我的生活先正常过。今天这期不替谁写结案书，只替那碗面讨个公道。故事结尾我把手机扣下，重新烧水。你说这算什么反转？算我终于从别人的连续剧里，杀青了。
参考来源：离线合成夹具，仅用于验收界面。'''
call_count=[int((root/'model-calls.json').read_text()) if (root/'model-calls.json').exists() else 0]
class LLM:
    def chat_stream(self,messages):
        for i in range(0,len(fixture_script),80):
            time.sleep(.01);yield fixture_script[i:i+80]
    def summarize_reference(self,*a):
        time.sleep(options.phase_delay)
        return ProviderResult(data={'narrative_summary':'合成夹具：开场反差→评论区脑补小剧场→注意力反转收尾。','creator_viewpoint':'围观情绪与流量生产之间的反差','hook_style':'反问与荒诞比喻','pacing':'短句，三段递进','struct_patterns':['钩子','冲突','小剧场','回扣'],'takeaways':['换用原创比喻，避免复述原话']},provenance=ProviderProvenance((),()))
class BoundedReal:
    def __init__(self, config): self.actual=WorkbenchLLM(config)
    def count(self):
        call_count[0]+=1
        if call_count[0]>4:raise RuntimeError('real trial four-call limit reached')
        (root/'model-calls.json').write_text(str(call_count[0]))
    def chat_stream(self,messages):self.count();return self.actual.chat_stream(messages)
    def summarize_reference(self,*a):self.count();return self.actual.summarize_reference(*a)
def acquire(cmd,**kwargs):
    time.sleep(options.phase_delay)
    path=Path(cmd[cmd.index('-o')+1].replace('%(ext)s','mp4'));path.write_bytes(b'SYNTHETIC AUTHORIZED LOCAL MEDIA FIXTURE')
    return subprocess.CompletedProcess(cmd,0,json.dumps({'_filename':str(path),'duration':250}), '')
def audio(cmd,**kwargs):
    time.sleep(options.phase_delay)
    Path(cmd[-1]).write_bytes(b'RIFF'+b'0'*100);return subprocess.CompletedProcess(cmd,0,'','')
def whisper(cmd,**kwargs):
    time.sleep(options.phase_delay)
    if '转写失败' in active_topic[0]:return subprocess.CompletedProcess(cmd,1,'','fixture Whisper failed')
    out=Path(cmd[cmd.index('--output-file')+1]+'.json')
    out.write_text(json.dumps({'transcription':[{'offsets':{'from':i*1000,'to':(i+1)*1000},'text':f'第{i+1}句合成转写：围观热点的节奏与荒诞小剧场，只是软件验收夹具，不描述真实事件。'} for i in range(250)]},ensure_ascii=False))
    return subprocess.CompletedProcess(cmd,0,'','')
class Installation:
    runtime_path='fixture-whisper';model_path='fixture-model';dtw_preset='none';model_name='FIXTURE-not-real-ASR';runtime_version='fixture'
class Bootstrap:
    def ensure(self):return Installation()
flow=WorkbenchFlow(root,provider_factory=(BoundedReal if options.real_model else lambda config:LLM()),topic_search=search)
flow.connection_kind='real' if options.real_model else 'fixture'
flow.TOPIC_SEARCH_TIMEOUT=4
flow.acquire_runner=acquire;flow.audio_runner=audio;flow.whisper_runner=whisper;flow.whisper_bootstrap=Bootstrap()
(root/'trial-info.json').write_text(json.dumps({'port':options.port,'real_model':options.real_model,'all_sources_and_media':'synthetic fixtures'}))
print('DISPOSABLE_TRIAL_ROOT='+str(root),flush=True)
server=make_server(options.port,output_dir=root/'discoveries',provider_factory=Provider,flow=flow)
server.serve_forever()
