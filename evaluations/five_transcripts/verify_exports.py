"""Compare actual browser downloads with durable full exports. Fixture data only."""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--downloads',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
sessions=list((args.root/'workbench/sessions').glob('WBX-*/session.json'))
assert len(sessions)==1
session=json.loads(sessions[0].read_text());directory=sessions[0].parent
combined=(directory/'合并参考稿.txt').read_text()
assert (args.downloads/'合并参考稿.txt').read_text()==combined
rows=[];positions=[]
for index,candidate in enumerate(session['discovery']['candidates'],1):
    bv=candidate['bvid'];ref=directory/'references'/bv
    transcript=json.loads((ref/'transcript.json').read_text());txt=next(ref.glob('*口播转写.txt'))
    assert len(transcript['segments'])==250
    assert transcript['text'].endswith(bv+' 第250句：最后一行完整保留。')
    assert transcript['text'] in txt.read_text()
    assert (args.downloads/f'source-{index}.txt').read_bytes()==txt.read_bytes()
    positions.append(combined.index(txt.read_text()))
    media=Path(session['references'][bv]['media_path'])
    assert media.stem.endswith('-12357播放')
    rows.append({'bvid':bv,'text_path':str(txt),'json_path':str(ref/'transcript.json'),'segments':250,'asr_chars':len(transcript['text']),'txt_bytes':len(txt.read_bytes()),'txt_sha256':hashlib.sha256(txt.read_bytes()).hexdigest(),'tail_preserved':True,'browser_download_exact':True,'media_filename':media.name})
assert positions==sorted(positions)
assert combined.count('第250句：最后一行完整保留。')==5
log=json.loads((args.root/'tool-calls.json').read_text())
counts={tool:sum(c['tool']==tool for c in log) for tool in ['yt-dlp','ffmpeg','whisper','model']}
assert counts=={'yt-dlp':6,'ffmpeg':5,'whisper':5,'model':1},counts
model=next(c for c in log if c['tool']=='model')
assert '1234' in model['messages'][-1]['content']
for row in rows:
    text=json.loads(Path(row['json_path']).read_text())['text']
    assert json.dumps(text,ensure_ascii=False)[1:-1] in model['messages'][-1]['content']
assert (args.downloads/'第一份.txt').read_bytes()==Path(rows[0]['text_path']).read_bytes()
assert json.loads((args.downloads/'第一份.json').read_text())==json.loads(Path(rows[0]['json_path']).read_text())
result={'fixture':True,'session_id':session['session_id'],'root':str(args.root),'sources':rows,'combined_path':str(directory/'合并参考稿.txt'),'combined_chars':len(combined),'combined_bytes':len(combined.encode()),'combined_sha256':hashlib.sha256(combined.encode()).hexdigest(),'combined_browser_download_exact':True,'ordered_full_text':True,'tool_calls':counts,'model_custom_words':1234,'model_full_sources_present':True}
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
