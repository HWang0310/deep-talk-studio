import unittest
from pathlib import Path
class AlignVideoSkillTests(unittest.TestCase):
 def test_skill_has_six_intents_and_one_action_gate(self):
  text=(Path(__file__).resolve().parents[1]/".agents/skills/align-video/SKILL.md").read_text()
  for intent in ("我视频剪好了","这是口播视频","帮我把素材卡进去","给我生成粗剪","这张截图时间太长","关系图晚一点"):self.assertIn(intent,text)
  self.assertNotIn("请选择 provider",text)
if __name__=="__main__":unittest.main()
