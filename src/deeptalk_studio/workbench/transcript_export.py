"""Local source-study ASR exports, separate from original creative scripts."""
import json
import os
import tempfile
from pathlib import Path


def atomic_text(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValueError('不允许符号链接转写工件')
    if path.is_file() and path.read_text(encoding='utf-8') == content:
        return
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.transcript-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(content)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def study_text(transcript, metadata):
    provenance = transcript.get('transcript_provenance') or {}
    header = {
        'label':'机器识别 ASR · 本地参考学习材料，可复制校订；不是作者原始书面稿',
        'bvid':metadata.get('bvid',''), 'title':metadata.get('title',''),
        'url':metadata.get('url',''), 'status':transcript.get('transcript_status','complete'),
        'model':transcript.get('model',provenance.get('model','')),
        **provenance,
    }
    return json.dumps(header, ensure_ascii=False, indent=2) + '\n\n' + str(transcript.get('text','')) + '\n'
