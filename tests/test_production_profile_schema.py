import unittest

from deeptalk_studio.production_profile import (
    ProductionValidationError,
    load_production_profile,
)
from deeptalk_studio.production_schema import (
    MOTION_ASSET_MANIFEST_SCHEMA,
    PRODUCTION_PLAN_SCHEMA,
    PRODUCTION_QA_SCHEMA,
)
from deeptalk_studio.validation import validate_json_schema


class ProductionProfileSchemaTests(unittest.TestCase):
    def test_default_profile_locks_bilibili_canvas_renderer_and_design_tokens(self):
        profile = load_production_profile()
        self.assertEqual(profile["profile_version"], "0.6")
        self.assertEqual(profile["platform"], "bilibili")
        self.assertEqual(profile["canvas"], {
            "width": 1920, "height": 1080, "aspect_ratio": "16:9", "fps": 30,
        })
        self.assertIn(profile["default_renderer"], {"remotion", "hyperframes"})
        self.assertEqual(profile["design_tokens"]["safe_area"]["horizontal"], 96)
        self.assertEqual(profile["dependencies"]["remotion"], "4.0.507")
        self.assertTrue(profile["dependencies"]["hyperframes"])

    def test_profile_rejects_wrong_canvas_or_unknown_field(self):
        profile = load_production_profile()
        profile["canvas"]["fps"] = 60
        with self.assertRaisesRegex(ProductionValidationError, "1920×1080.*30 fps"):
            load_production_profile(data=profile)
        profile = load_production_profile()
        profile["surprise"] = True
        with self.assertRaisesRegex(ProductionValidationError, "字段"):
            load_production_profile(data=profile)

    def test_public_artifact_schemas_are_strict(self):
        for schema in (
            PRODUCTION_PLAN_SCHEMA,
            MOTION_ASSET_MANIFEST_SCHEMA,
            PRODUCTION_QA_SCHEMA,
        ):
            self.assertFalse(schema["additionalProperties"])
            with self.assertRaises(Exception):
                validate_json_schema({"unexpected": True}, schema, "artifact")


if __name__ == "__main__":
    unittest.main()
