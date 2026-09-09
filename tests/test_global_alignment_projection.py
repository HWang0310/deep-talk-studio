import copy
import unittest
from unittest.mock import patch

from deeptalk_studio.alignment_builder import build_script_alignment
from tests.alignment_fixtures import NOW, mapping_fixture, media_fixture, profile_fixture


def _units(texts):
    units = []
    cursor = 0
    for text in texts:
        units.append({
            "unit_id": f"TU{len(units) + 1:04d}",
            "order": len(units),
            "spoken_text": text,
            "media_start_seconds": str(cursor),
            "media_end_seconds": str(cursor + len(text)),
            "boundary_risk_ids": [],
        })
        cursor += len(text)
    return units


def _fixture():
    script = {
        "script_id": "SCR-global-projection",
        "revision": 1,
        "beats": [
            {"beat_id": "B001", "narration": "甲乙丙丁"},
            {"beat_id": "B002", "narration": "戊己庚辛"},
            {"beat_id": "B003", "narration": "壬癸子丑寅卯辰巳午未申"},
            {"beat_id": "B004", "narration": "酉戌亥天"},
        ],
    }
    transcript = {
        "artifact_version": "timed-transcript/1",
        "transcript_id": "TR-global-projection",
        "transcript_digest": "t" * 64,
        "timestamp_granularity": "word",
        "timed_units": _units([
            "甲乙丙丁",
            "戊已填充庚辛",
            "壬癸",
            "酉戌亥天",
            "尾声额外口播保持原样",
        ]),
        "boundary_risks": [],
        "transcription_chunk_plan_digest": "c" * 64,
        "narration_media_id": "NM-align",
        "narration_media_sha256": "m" * 64,
        "timestamp_mapping_id": "MAP-align",
        "timestamp_mapping_digest": "p" * 64,
    }
    cues = [
        {"cue_id": "VC001", "beat_id": "B002", "placement_anchor": "戊己"},
        {"cue_id": "VC002", "beat_id": "B004", "placement_anchor": "酉戌亥"},
    ]
    return script, transcript, cues


def build_global_fixture():
    script, transcript, cues = _fixture()
    return build_script_alignment(
        script, transcript, mapping_fixture(), profile_fixture(), cues,
        alignment_id="AL-global-projection", created_at=NOW,
        media=media_fixture(duration="120"),
    )


class GlobalAlignmentProjectionTests(unittest.TestCase):
    def test_alignment_uses_one_global_pass_not_one_full_scan_per_beat(self):
        script, transcript, cues = _fixture()
        from deeptalk_studio.sequence_alignment import align_sequences as real_align

        with patch("deeptalk_studio.alignment_builder.align_sequences", wraps=real_align) as aligned:
            build_script_alignment(
                script, transcript, mapping_fixture(), profile_fixture(), cues,
                alignment_id="AL-global-pass", created_at=NOW,
                media=media_fixture(duration="120"),
            )
        self.assertEqual(aligned.call_count, 1)

    def test_global_projection_keeps_insertions_local_and_preserves_trailing_tail(self):
        artifact = build_global_fixture()
        beats = {beat["beat_id"]: beat for beat in artifact["beat_timeline"]}
        self.assertEqual(len(artifact["global_mapping"]["script_units"]), 23)
        self.assertNotIn("ad_lib_transcript_span", beats["B001"]["deviation_codes"])
        self.assertIn("ad_lib_transcript_span", beats["B002"]["deviation_codes"])
        self.assertIn(
            "trailing_ad_lib_transcript_span",
            [gap["gap_type"] for gap in artifact["gaps"]],
        )
        self.assertEqual(beats["B004"]["alignment_status"], "aligned")

    def test_global_projection_is_deterministic_and_does_not_mutate_transcript_truth(self):
        script, transcript, cues = _fixture()
        original = copy.deepcopy(transcript)
        one = build_script_alignment(
            script, transcript, mapping_fixture(), profile_fixture(), cues,
            alignment_id="AL-global-stable", created_at=NOW,
            media=media_fixture(duration="120"),
        )
        two = build_script_alignment(
            script, transcript, mapping_fixture(), profile_fixture(), cues,
            alignment_id="AL-global-stable", created_at=NOW,
            media=media_fixture(duration="120"),
        )
        self.assertEqual(one["artifact_digest"], two["artifact_digest"])
        self.assertEqual(transcript, original)

    def test_safe_cue_projects_despite_an_unrelated_parent_omission(self):
        script = {"script_id": "SCR-cue-local", "revision": 1, "beats": [{
            "beat_id": "B001", "narration": "前半已经说完这里有个很容易被忽略的关键后半锚点春夏秋冬天地玄黄宇宙洪荒日月盈昃辰宿列张"
        }]}
        transcript = _fixture()[1]
        transcript["timed_units"] = _units(["前半已经说完后半锚点春夏秋冬天地玄黄宇宙洪荒日月盈昃辰宿列张"])
        artifact = build_script_alignment(
            script, transcript, mapping_fixture(), profile_fixture(),
            [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "后半锚点春夏秋冬天地玄黄宇宙洪荒日月盈昃辰宿列张"}],
            alignment_id="AL-cue-local", created_at=NOW, media=media_fixture(duration="120"),
        )
        self.assertEqual(artifact["beat_timeline"][0]["alignment_status"], "needs_review")
        cue = artifact["cue_timeline"][0]
        self.assertEqual(cue["placement_status"], "aligned")
        self.assertEqual(cue["confidence"], "high")

    def test_anchor_crossing_actual_deletion_remains_unplaced(self):
        script = {"script_id": "SCR-cue-delete", "revision": 1, "beats": [{
            "beat_id": "B001", "narration": "可靠锚点后面内容"
        }]}
        transcript = _fixture()[1]
        transcript["timed_units"] = _units(["可靠内容"])
        artifact = build_script_alignment(
            script, transcript, mapping_fixture(), profile_fixture(),
            [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "锚点后面"}],
            alignment_id="AL-cue-delete", created_at=NOW, media=media_fixture(duration="120"),
        )
        cue = artifact["cue_timeline"][0]
        self.assertEqual(cue["placement_status"], "unplaced")
        self.assertIn("semantic_span_unmatched", cue["deviation_codes"])

    def test_eighteen_of_twenty_safe_substitution_anchor_projects_without_guessing_time(self):
        text = "天地玄黄宇宙洪荒日月盈昃辰宿列张寒来暑往"[:20]
        spoken = text.replace("玄", "悬").replace("黄", "皇")
        script = {"script_id": "SCR-cue-substitution", "revision": 1, "beats": [{
            "beat_id": "B001", "narration": text
        }]}
        transcript = _fixture()[1]
        transcript["timed_units"] = _units([spoken])
        artifact = build_script_alignment(
            script, transcript, mapping_fixture(), profile_fixture(),
            [{"cue_id": "VC001", "beat_id": "B001", "placement_anchor": text}],
            alignment_id="AL-cue-substitution", created_at=NOW, media=media_fixture(duration="120"),
        )
        direct = sum(unit["operation"] in {"primary_match", "numeric_match"} for unit in artifact["global_mapping"]["script_units"])
        self.assertEqual(direct, 18)
        cue = artifact["cue_timeline"][0]
        self.assertEqual(cue["placement_status"], "aligned")
        self.assertEqual(cue["actual_start_seconds"], transcript["timed_units"][0]["media_start_seconds"])
        self.assertEqual(cue["actual_end_seconds"], transcript["timed_units"][0]["media_end_seconds"])


if __name__ == "__main__":
    unittest.main()
