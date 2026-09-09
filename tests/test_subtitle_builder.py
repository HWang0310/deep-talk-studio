import copy
import unittest

from deeptalk_studio.subtitle_builder import (
    SubtitleArtifactError,
    build_subtitle_artifact,
    validate_subtitle_artifact,
)
from deeptalk_studio.subtitle_profile import load_subtitle_profile


def media(duration="12"):
    return {"media_id": "NM1", "sha256": "a" * 64, "presentation_duration_seconds": duration}


def transcript(granularity="word"):
    units = [
        ("TU000000", "0.50", "0.90", "今天"),
        ("TU000001", "0.90", "1.30", "我们"),
        ("TU000002", "1.30", "1.80", "看证据。"),
        ("TU000003", "2.20", "3.10", "答案并不简单。"),
    ]
    if granularity == "segment":
        units = [
            ("TU000000", "0.50", "1.80", "今天我们看证据。"),
            ("TU000001", "2.20", "3.10", "答案并不简单。"),
        ]
    return {
        "artifact_version": "timed-transcript/1", "transcript_id": "TR1", "revision": 1,
        "transcript_digest": "t" * 64, "narration_media_id": "NM1",
        "narration_media_sha256": "a" * 64, "timestamp_granularity": granularity,
        "timed_units": [
            {"unit_id": uid, "media_start_seconds": start, "media_end_seconds": end, "spoken_text": text}
            for uid, start, end, text in units
        ],
    }


class SubtitleBuilderTests(unittest.TestCase):
    def build(self, granularity="word"):
        return build_subtitle_artifact(
            transcript(granularity), media(), load_subtitle_profile(),
            subtitle_id="SUB1", created_at="2026-08-13T12:00:00+08:00",
        )

    def test_word_units_group_without_inventing_boundaries(self):
        artifact = self.build("word")
        first = artifact["cues"][0]
        self.assertEqual((first["in_seconds"], first["out_seconds"]), ("0.50", "1.80"))
        self.assertEqual(first["text"], "今天我们看证据。")
        self.assertEqual(first["source_unit_ids"], ["TU000000", "TU000001", "TU000002"])
        self.assertEqual(first["timing_precision"], "word")

    def test_segment_units_remain_coarse_and_are_never_split_into_words(self):
        artifact = self.build("segment")
        self.assertEqual(len(artifact["cues"]), 2)
        self.assertTrue(all(cue["timing_precision"] == "segment" for cue in artifact["cues"]))
        self.assertTrue(all(len(cue["source_unit_ids"]) == 1 for cue in artifact["cues"]))

    def test_transcript_change_and_artifact_tamper_fail_closed(self):
        artifact = self.build()
        changed = transcript(); changed["revision"] = 2; changed["transcript_digest"] = "u" * 64
        with self.assertRaises(SubtitleArtifactError):
            validate_subtitle_artifact(artifact, changed, media(), load_subtitle_profile())
        tampered = copy.deepcopy(artifact); tampered["cues"][0]["text"] = "不存在的话"
        with self.assertRaises(SubtitleArtifactError):
            validate_subtitle_artifact(tampered, transcript(), media(), load_subtitle_profile())

    def test_invalid_time_or_empty_text_is_rejected(self):
        bad = transcript(); bad["timed_units"][0]["spoken_text"] = "   "
        with self.assertRaises(SubtitleArtifactError):
            build_subtitle_artifact(bad, media(), load_subtitle_profile(), subtitle_id="SUB1", created_at="now")


if __name__ == "__main__":
    unittest.main()
