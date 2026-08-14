import os
import subprocess,tempfile,unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class EditBridgeCLITests(unittest.TestCase):
 def test_missing_real_aroll_stops_at_one_simple_user_action(self):
  with tempfile.TemporaryDirectory() as temp:
   p=subprocess.run([str(ROOT/"scripts/deeptalk"),"align-video","--session",temp],capture_output=True,text=True)
   self.assertEqual(p.returncode,0);self.assertIn("把已经剪好口气的正式真人口播视频拖进来",p.stdout);self.assertNotIn("provider",p.stdout.casefold());self.assertNotIn("JSON",p.stdout)

 def test_clean_aroll_uses_local_provider_without_openai_key(self):
  with tempfile.TemporaryDirectory() as temp:
   session=Path(temp);(session/"clean.mp4").write_bytes(b"video")
   stdout=StringIO();stderr=StringIO()
   with patch.dict(os.environ,{},clear=True), patch("deeptalk_studio.edit_bridge_session.resolve_real_edit_bridge_session",return_value=object()), patch("deeptalk_studio.edit_bridge_session.run_real_edit_bridge_session",return_value=SimpleNamespace(preview_path=Path(temp)/"preview.mp4")), patch("deeptalk_studio.transcription.local_whisper_cpp.resolve_default_transcription_provider") as resolver, redirect_stdout(stdout), redirect_stderr(stderr):
    resolver.return_value=object()
    from deeptalk_studio.cli import main
    code=main(("align-video","--session",temp))
   self.assertEqual(code,0,stderr.getvalue())
   resolver.assert_called_once_with()
   self.assertNotIn("OPENAI_API_KEY",stdout.getvalue()+stderr.getvalue())
if __name__=="__main__":unittest.main()
