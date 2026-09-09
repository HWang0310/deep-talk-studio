import unittest

from deeptalk_studio.post_alignment_visual_materials import build_real_trial_visual_completion_content


class RealTrialVisualContentTests(unittest.TestCase):
    def test_adds_story_driven_motions_without_rewriting_existing_material_input(self):
        original = {"cue_sheet": [], "visual_specs": [], "materials": [], "gaps": [], "research_update_signals": [], "warnings": []}
        result = build_real_trial_visual_completion_content(original)
        self.assertEqual(original["cue_sheet"], [])
        self.assertEqual([item["beat_id"] for item in result["visual_specs"]], ["B005", "B007", "B009", "B011", "B013", "B018"])
        self.assertEqual(result["visual_specs"][-2]["nodes"][3]["label"], "正式安全港保护")
        self.assertEqual(result["visual_specs"][-1]["claim_ids"], ["C4", "C13"])


if __name__ == "__main__":
    unittest.main()
