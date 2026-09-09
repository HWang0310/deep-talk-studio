import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deeptalk_studio.output_truth import OutputTruthError, build_output_truth_evidence, validate_output_truth_evidence


class OutputTruthTests(unittest.TestCase):
 def test_primary_visual_requires_persisted_pre_in_post_evidence(self):
  placement={"placement_id":"VP1","placement_status":"ready","source_kind":"real_image","layout_mode":"full_screen_broll","preview_in_frame":30,"preview_out_frame":60}
  with tempfile.TemporaryDirectory() as temp, patch("deeptalk_studio.output_truth._frame", side_effect=["pre","in","post"]), patch.object(Path,"read_bytes",return_value=b"video"):
   result=build_output_truth_evidence(Path("preview.mp4"),[placement],evidence_dir=Path(temp)/"evidence")
  row=result["placements"][0]
  self.assertEqual(row["expected_presentation_mode"],"primary_visual")
  self.assertEqual(row["frame_sha256"],["pre","in","post"])
  self.assertEqual(row["frame_files"],["VP1-pre.png","VP1-in.png","VP1-post.png"])

 def test_unchanged_primary_window_fails_closed(self):
  placement={"placement_id":"VP1","placement_status":"ready","source_kind":"real_image","layout_mode":"full_screen_broll","preview_in_frame":30,"preview_out_frame":60}
  with tempfile.TemporaryDirectory() as temp, patch("deeptalk_studio.output_truth._frame", return_value="same"), patch.object(Path,"read_bytes",return_value=b"video"):
   with self.assertRaises(OutputTruthError): build_output_truth_evidence(Path("preview.mp4"),[placement],evidence_dir=Path(temp)/"evidence")

 def test_evidence_digest_and_video_binding_are_checked(self):
  evidence={"artifact_version":"output-truth-evidence/1","preview_sha256":hashlib.sha256(b"video").hexdigest(),"placements":[{"frame_sha256":["pre","in","post"],"frame_files":["pre.png","in.png","post.png"]}]}
  evidence["evidence_digest"]=hashlib.sha256(__import__("json").dumps(evidence,sort_keys=True,separators=(",",":" )).encode()).hexdigest()
  with patch.object(Path,"read_bytes",return_value=b"video"):
   validate_output_truth_evidence(evidence,Path("preview.mp4"))
