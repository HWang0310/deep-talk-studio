import copy
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.alignment_profile import (
    AlignmentProfileError,
    alignment_profile_digest,
    load_alignment_profile,
)
from deeptalk_studio.alignment_schema import ALIGNMENT_PROFILE_SCHEMA, SCRIPT_ALIGNMENT_SCHEMA
from deeptalk_studio.validation import ReportValidationError, validate_json_schema


class AlignmentProfileSchemaTests(unittest.TestCase):
    def test_candidate_values_are_versioned_and_digest_bound(self):
        profile = load_alignment_profile()
        self.assertEqual(profile["artifact_version"], "alignment-profile/1")
        self.assertEqual(profile["ambiguity_normalized_margin"], 0.08)
        self.assertEqual(profile["calibration_status"], "candidate")
        self.assertEqual(profile["profile_digest"], alignment_profile_digest(profile))
        validate_json_schema(profile, ALIGNMENT_PROFILE_SCHEMA)

    def test_exact_scores_floors_and_provenance_are_locked(self):
        profile = load_alignment_profile()
        self.assertEqual(
            {key: profile[key] for key in (
                "primary_match_score", "numeric_alias_match_score", "substitution_score",
                "script_deletion_score", "transcript_insertion_score",
            )},
            {
                "primary_match_score": 4.0, "numeric_alias_match_score": 3.0,
                "substitution_score": -2.5, "script_deletion_score": -2.0,
                "transcript_insertion_score": -1.5,
            },
        )
        self.assertEqual(profile["accepted_floors"], {"coverage": 0.85, "similarity": 0.88})
        self.assertEqual(profile["review_floors"], {"coverage": 0.55, "similarity": 0.65})
        self.assertEqual(profile["long_gap_token_threshold"], 8)
        self.assertEqual(profile["timestamp_epsilon_seconds"], "0.001")
        self.assertEqual(len(profile["source_design_head"]), 40)

    def test_digest_threshold_revision_unknown_and_premature_acceptance_fail(self):
        for field, value in (
            ("profile_digest", "0" * 64),
            ("ambiguity_normalized_margin", 0.09),
            ("value_revision", 2),
            ("calibration_status", "accepted"),
        ):
            forged = copy.deepcopy(load_alignment_profile())
            forged[field] = value
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "profile.json"
                path.write_text(json.dumps(forged), encoding="utf-8")
                with self.assertRaises(AlignmentProfileError):
                    load_alignment_profile(path)
        unknown = copy.deepcopy(load_alignment_profile())
        unknown["model_status"] = "aligned"
        with self.assertRaises(ReportValidationError):
            validate_json_schema(unknown, ALIGNMENT_PROFILE_SCHEMA)

    def test_alignment_root_forbids_unknown_machine_owned_fields(self):
        required = set(SCRIPT_ALIGNMENT_SCHEMA["required"])
        self.assertIn("beat_timeline", required)
        self.assertIn("cue_timeline", required)
        self.assertFalse(SCRIPT_ALIGNMENT_SCHEMA["additionalProperties"])
        self.assertNotIn("llm_alignment_status", SCRIPT_ALIGNMENT_SCHEMA["properties"])


if __name__ == "__main__":
    unittest.main()
