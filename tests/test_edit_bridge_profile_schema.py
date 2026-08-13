import copy
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.edit_bridge_schema import EDIT_BRIDGE_SCHEMA, VISUAL_PLACEMENT_SCHEMA
from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.rough_cut_profile import (
    EditBridgeProfileError, load_aligned_preview_profile, load_rough_cut_profile,
)
from deeptalk_studio.validation import ReportValidationError, validate_json_schema


class EditBridgeProfileSchemaTests(unittest.TestCase):
    def test_still_cap_is_inherited_and_digest_bound(self):
        profile = load_rough_cut_profile(load_material_profile())
        self.assertEqual(profile["still_exposure_seconds"], 7)
        self.assertEqual(profile["source_profile_version"], "0.5")
        self.assertTrue(profile["source_profile_digest"])
        self.assertTrue(profile["profile_digest"])

    def test_preview_is_fixed_30fps_ceil_exclusive(self):
        profile = load_aligned_preview_profile()
        self.assertEqual((profile["width"], profile["height"], profile["fps"]), (1920, 1080, 30))
        self.assertEqual(profile["frame_rounding"], "ceil")
        self.assertEqual(profile["out_frame_semantics"], "exclusive")

    def test_tamper_and_unknown_profile_fields_fail(self):
        profile = load_aligned_preview_profile()
        for field, value in (("fps", 25), ("profile_digest", "x" * 64)):
            forged = copy.deepcopy(profile); forged[field] = value
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "profile.json"; path.write_text(json.dumps(forged))
                with self.assertRaises(EditBridgeProfileError): load_aligned_preview_profile(path)

    def test_schema_separates_placement_and_timing_and_forbids_frame_canonical_timecode(self):
        properties = VISUAL_PLACEMENT_SCHEMA["properties"]
        self.assertIn("placement_status", properties)
        self.assertIn("timing_status", properties)
        self.assertEqual(properties["canonical_in_timecode"]["type"], "string")
        self.assertNotIn("frame", "canonical_in_timecode")
        self.assertFalse(VISUAL_PLACEMENT_SCHEMA["additionalProperties"])
        self.assertFalse(EDIT_BRIDGE_SCHEMA["additionalProperties"])
        with self.assertRaises(ReportValidationError):
            validate_json_schema({"placement_status": "ready", "renderer_status": "pass"}, VISUAL_PLACEMENT_SCHEMA)


if __name__ == "__main__": unittest.main()
