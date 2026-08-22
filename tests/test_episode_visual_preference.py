import unittest
import tempfile
from pathlib import Path

from deeptalk_studio.episode_visual_preference import (
    build_episode_visual_preference,
    load_episode_visual_default,
    parse_visual_preference_feedback,
    validate_episode_visual_preference,
)
from deeptalk_studio.episode_visual_preference_storage import (
    EpisodeVisualPreferenceStorageError,
    load_episode_visual_preference,
    save_episode_visual_preference,
)


class EpisodeVisualPreferenceTests(unittest.TestCase):
    def test_default_is_a_versioned_balanced_persistent_profile(self):
        default = load_episode_visual_default()
        self.assertEqual(default["artifact_version"], "episode-visual-default/1")
        self.assertEqual(default["preferences"], {
            "overall_visual_density": "balanced",
            "real_material_preference": "balanced",
            "motion_preference": "balanced",
            "a_roll_preference": "balanced",
        })

    def test_episode_override_isolated_from_persistent_default(self):
        preference = build_episode_visual_preference(
            load_episode_visual_default(),
            "这期素材和动画都多一点，真人保持正常",
            preference_id="EVP-1",
            created_at="2026-08-22T10:00:00+08:00",
        )
        self.assertEqual(preference["persistent_default"]["preferences"]["motion_preference"], "balanced")
        self.assertEqual(preference["resolved_preference"], {
            "overall_visual_density": "high",
            "real_material_preference": "high",
            "motion_preference": "high",
            "a_roll_preference": "balanced",
        })
        self.assertEqual(preference["episode_override"]["scope"], "episode")
        validate_episode_visual_preference(preference, load_episode_visual_default())

    def test_explicit_future_default_is_the_only_persistent_intent(self):
        persistent = parse_visual_preference_feedback("以后默认动画都多一点")
        episode = parse_visual_preference_feedback("这期动画多一点")
        self.assertEqual(persistent["scope"], "persistent")
        self.assertEqual(persistent["patch"], {"motion_preference": "high"})
        self.assertEqual(episode["scope"], "episode")
        self.assertEqual(episode["patch"], {"motion_preference": "high"})

    def test_human_preview_revision_has_highest_precedence(self):
        preference = build_episode_visual_preference(
            load_episode_visual_default(),
            "这期整体丰富一点，真实截图多一点，动画多一点",
            preference_id="EVP-2",
            created_at="2026-08-22T10:00:00+08:00",
            human_preview_feedback=("动画收一点，结尾多留真人",),
        )
        self.assertEqual(preference["resolved_preference"]["motion_preference"], "low")
        self.assertEqual(preference["resolved_preference"]["a_roll_preference"], "high")
        self.assertEqual(preference["human_preview_revisions"][0]["scope"], "human_preview")

    def test_unknown_feedback_keeps_defaults_and_preserves_original_words(self):
        preference = build_episode_visual_preference(
            load_episode_visual_default(),
            "画面有一种克制的工业感",
            preference_id="EVP-3",
            created_at="2026-08-22T10:00:00+08:00",
        )
        self.assertEqual(preference["resolved_preference"], load_episode_visual_default()["preferences"])
        self.assertEqual(preference["episode_override"]["patch"], {})
        self.assertEqual(preference["episode_override"]["raw_text"], "画面有一种克制的工业感")

    def test_preference_artifact_saves_immutably_and_reopens_with_default_binding(self):
        preference = build_episode_visual_preference(
            load_episode_visual_default(), "这期素材多一点", preference_id="EVP-4", created_at="2026-08-22T10:00:00+08:00",
        )
        with tempfile.TemporaryDirectory() as temp:
            path = save_episode_visual_preference(preference, Path(temp))
            self.assertEqual(load_episode_visual_preference(path, load_episode_visual_default()), preference)
            with self.assertRaises(EpisodeVisualPreferenceStorageError):
                save_episode_visual_preference(preference, Path(temp))


if __name__ == "__main__":
    unittest.main()
