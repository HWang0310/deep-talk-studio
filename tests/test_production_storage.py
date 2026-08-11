import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.production_renderer import render_production_summary
from deeptalk_studio.production_storage import (
    ProductionStorageError,
    production_output_path,
    save_production_artifact,
    save_production_plan,
)


def tiny_plan():
    return {
        "production_id": "PROD-store", "revision": 1,
        "created_at": "2026-08-11T12:00:00+08:00",
        "selected_renderer": "remotion",
        "scenes": [{"scene_id": "S001", "scene_type": "aroll_placeholder"}],
        "motion_assets": [{"motion_asset_id": "MA001"}],
        "production_gaps": [{
            "reason": "只有 reference-only 新闻画面。",
            "recommended_fallback": "保留真人口播。",
        }],
    }


class ProductionStorageTests(unittest.TestCase):
    def test_plan_storage_is_immutable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = save_production_plan(tiny_plan(), root)
            self.assertTrue(path.exists())
            with self.assertRaisesRegex(ProductionStorageError, "覆盖"):
                save_production_plan(tiny_plan(), root)

    def test_output_path_rejects_traversal_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = production_output_path(root, "PROD-safe", "MA001", "mp4")
            self.assertEqual(path.parent.parent, root.resolve() / "PROD-safe")
            with self.assertRaisesRegex(ProductionStorageError, "ID"):
                production_output_path(root, "../escape", "MA001", "mp4")
            path.parent.mkdir(parents=True)
            path.write_bytes(b"exists")
            with self.assertRaisesRegex(ProductionStorageError, "覆盖"):
                production_output_path(root, "PROD-safe", "MA001", "mp4")

    def test_bound_artifacts_are_saved_beside_plan_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan_path = save_production_plan(tiny_plan(), root)
            artifact = {"manifest_id": "MAM-store", "production_id": "PROD-store"}
            path = save_production_artifact(
                artifact, plan_path, "motion-asset-manifest-r0001.json"
            )
            self.assertEqual(path.parent, plan_path.parent)
            self.assertTrue(path.exists())
            with self.assertRaisesRegex(ProductionStorageError, "覆盖"):
                save_production_artifact(
                    artifact, plan_path, "motion-asset-manifest-r0001.json"
                )
            with self.assertRaisesRegex(ProductionStorageError, "文件名"):
                save_production_artifact(artifact, plan_path, "../escape.json")

    def test_user_summary_hides_json_and_explains_safe_gap(self):
        summary = render_production_summary(tiny_plan(), ready_count=1, failed_count=0)
        self.assertIn("动画素材：1 个", summary)
        self.assertIn("只有 reference-only", summary)
        self.assertNotIn("production_id", summary)


if __name__ == "__main__":
    unittest.main()
