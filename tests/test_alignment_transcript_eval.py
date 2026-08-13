import unittest
from deeptalk_studio.alignment_profile import load_alignment_profile
from evaluations.audio_alignment_edit_bridge.run_alignment_calibration import run_alignment_calibration
class AlignmentTranscriptEvalTests(unittest.TestCase):
 def test_false_precision_cases_and_later_recovery(self):
  r=run_alignment_calibration(load_alignment_profile());self.assertEqual(r.false_ready_cases,());self.assertTrue(r.case("C").later_beats_recovered);self.assertTrue(r.case("CR3").later_beats_recovered)
if __name__=="__main__":unittest.main()
