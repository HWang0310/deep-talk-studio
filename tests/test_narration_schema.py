import unittest

from deeptalk_studio.narration_schema import (
    AUDIO_TIMESTAMP_MAPPING_SCHEMA,
    EXTRACTED_AUDIO_SCHEMA,
    NARRATION_MEDIA_SCHEMA,
    TIMED_TRANSCRIPT_SCHEMA,
)
from deeptalk_studio.validation import ReportValidationError, validate_json_schema


def valid_mapping():
    return {
        "artifact_version": "audio-timestamp-mapping/1",
        "mapping_id": "MAP001",
        "narration_media_id": "MEDIA001",
        "narration_media_sha256": "a" * 64,
        "extracted_audio_id": "AUDIO001",
        "extracted_audio_digest": "b" * 64,
        "source_stream_index": 1,
        "source_time_base": "1/48000",
        "presentation_origin_seconds": "0",
        "first_included_source_pts": -1024,
        "last_included_source_pts": 480000,
        "first_extracted_sample_index": 0,
        "last_extracted_sample_index": 480000,
        "scale_numerator": 1,
        "scale_denominator": 1,
        "offset_seconds": "0.375",
        "mapped_start_seconds": "0.375",
        "mapped_end_seconds": "10.375",
        "rounding_mode": "decimal_exact",
        "mapping_tolerance_seconds": "0.021333333333333333",
        "evidence_digest": "c" * 64,
        "mapping_digest": "d" * 64,
    }


class NarrationSchemaTests(unittest.TestCase):
    def test_machine_schemas_are_strict_and_versioned(self):
        validate_json_schema(valid_mapping(), AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")
        with self.assertRaises(ReportValidationError):
            validate_json_schema(
                {**valid_mapping(), "model_gate": "pass"},
                AUDIO_TIMESTAMP_MAPPING_SCHEMA,
                "mapping",
            )
        for schema, version in (
            (NARRATION_MEDIA_SCHEMA, "narration-media/1"),
            (EXTRACTED_AUDIO_SCHEMA, "extracted-audio/1"),
            (AUDIO_TIMESTAMP_MAPPING_SCHEMA, "audio-timestamp-mapping/1"),
            (TIMED_TRANSCRIPT_SCHEMA, "timed-transcript/1"),
        ):
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(schema["properties"]["artifact_version"]["enum"], [version])

    def test_transcript_contract_has_no_frame_fields_and_binds_chunk_risks(self):
        properties = TIMED_TRANSCRIPT_SCHEMA["properties"]
        self.assertIn("transcription_chunk_plan_digest", properties)
        self.assertIn("boundary_risks", properties)
        unit = properties["timed_units"]["items"]["properties"]
        self.assertIn("boundary_risk_ids", unit)
        self.assertIn("chunk_index", unit)
        self.assertFalse(any("frame" in key for key in unit))
        self.assertFalse(any("frame" in key for key in properties))

    def test_mapping_rejects_non_numeric_string_and_negative_sample_index(self):
        malformed = valid_mapping()
        malformed["last_extracted_sample_index"] = -1
        with self.assertRaises(ReportValidationError):
            validate_json_schema(malformed, AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")
        malformed = valid_mapping()
        malformed["offset_seconds"] = 0.375
        with self.assertRaises(ReportValidationError):
            validate_json_schema(malformed, AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")


if __name__ == "__main__":
    unittest.main()
