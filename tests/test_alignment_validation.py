import copy
import hashlib
import json
import unittest

from deeptalk_studio.alignment_builder import build_script_alignment
from deeptalk_studio.alignment_validation import AlignmentValidationError, validate_script_alignment
from tests.alignment_fixtures import NOW, cue_fixture, mapping_fixture, profile_fixture, script_fixture, transcript_fixture


def digest_without(value, field="artifact_digest"):
    payload = copy.deepcopy(value)
    payload.pop(field, None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AlignmentValidationTests(unittest.TestCase):
    def setUp(self):
        self.script = script_fixture()
        self.transcript = transcript_fixture()
        self.mapping = mapping_fixture()
        self.profile = profile_fixture()
        self.cues = cue_fixture()
        self.artifact = build_script_alignment(
            self.script, self.transcript, self.mapping, self.profile, self.cues,
            alignment_id="AL001", created_at=NOW,
        )

    def validate(self, value):
        return validate_script_alignment(value, self.script, self.transcript, self.mapping, self.profile, self.cues)

    def test_valid_artifact_is_fully_rederived(self):
        self.assertIsNone(self.validate(self.artifact))

    def test_validator_rejects_status_tamper_even_with_recomputed_outer_digest(self):
        forged = copy.deepcopy(self.artifact)
        forged["beat_timeline"][0]["alignment_status"] = "needs_review"
        forged["artifact_digest"] = digest_without(forged)
        with self.assertRaises(AlignmentValidationError):
            self.validate(forged)

    def test_all_machine_bindings_and_evidence_are_protected(self):
        mutations = [
            ("transcript_digest", "x" * 64), ("alignment_profile_digest", "x" * 64),
            ("alignment_trace_digest", "x" * 64), ("timestamp_mapping_digest", "x" * 64),
        ]
        for field, value in mutations:
            forged = copy.deepcopy(self.artifact)
            forged[field] = value
            forged["artifact_digest"] = digest_without(forged)
            with self.subTest(field=field), self.assertRaises(AlignmentValidationError):
                self.validate(forged)
        forged = copy.deepcopy(self.artifact)
        forged["beat_timeline"][0]["actual_start_seconds"] = "99"
        forged["artifact_digest"] = digest_without(forged)
        with self.assertRaises(AlignmentValidationError):
            self.validate(forged)

    def test_root_script_transcript_or_profile_change_invalidates_artifact(self):
        script = copy.deepcopy(self.script)
        script["beats"][0]["narration"] += "新文字"
        with self.assertRaises(AlignmentValidationError):
            validate_script_alignment(self.artifact, script, self.transcript, self.mapping, self.profile, self.cues)


if __name__ == "__main__":
    unittest.main()
