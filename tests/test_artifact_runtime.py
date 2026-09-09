import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from deeptalk_studio.artifact_runtime import (
    ArtifactRuntimeError,
    RuntimeArtifactResolver,
    load_artifact_runtime_config,
)


class ArtifactRuntimeResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.historical_root = base / "old" / "deep-talk-studio"
        self.canonical_root = base / "new" / "deep-talk-studio"
        self.historical_root.mkdir(parents=True)
        self.canonical_root.mkdir(parents=True)
        self.relative = Path("production_assets/PROD-1/assets/MA001.mp4")
        self.payload = b"sanitized-motion-output"
        self.target = self.canonical_root / self.relative
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(self.payload)
        self.recorded_path = self.historical_root / self.relative
        self.config_path = base / "artifact-runtime.local.json"
        self.config_path.write_text(json.dumps({
            "config_version": "artifact-runtime/1",
            "canonical_repository_root": str(self.canonical_root),
            "trusted_historical_repository_roots": [str(self.historical_root)],
            "current_production_id": "PROD-1",
        }), encoding="utf-8")
        self.resolver = RuntimeArtifactResolver(
            load_artifact_runtime_config(self.canonical_root, self.config_path)
        )
        self.sha256 = hashlib.sha256(self.payload).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def test_historical_motion_path_resolves_without_mutating_manifest_evidence(self):
        manifest = {
            "manifest_digest": "historical-digest",
            "assets": [{
                "motion_asset_id": "MA001",
                "scene_id": "S001",
                "asset_kind": "motion_clip",
                "format": "mp4",
                "output_path": str(self.recorded_path),
                "byte_size": len(self.payload),
                "sha256": self.sha256,
            }],
        }
        original = deepcopy(manifest)
        original_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode()
        plan = {
            "production_id": "PROD-1",
            "motion_assets": [{
                "motion_asset_id": "MA001", "scene_id": "S001",
                "asset_kind": "motion_clip", "requested_format": "mp4",
            }],
        }

        observation = self.resolver.resolve_motion_asset(plan, manifest["assets"][0])

        self.assertEqual(observation.recorded_path, self.recorded_path)
        self.assertEqual(observation.artifact_relative_path, self.relative)
        self.assertEqual(observation.resolved_path, self.target.resolve())
        self.assertEqual(manifest, original)
        self.assertEqual(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode(),
            original_bytes,
        )

    def test_unknown_historical_root_and_unexpected_absolute_location_are_rejected(self):
        unknown = Path(self.temp.name) / "unknown" / self.relative
        unexpected = self.canonical_root / "production_assets/PROD-other/assets/MA001.mp4"
        for recorded in (unknown, unexpected):
            with self.subTest(recorded=recorded):
                with self.assertRaisesRegex(ArtifactRuntimeError, "root|identity"):
                    self.resolver.resolve_artifact(
                        recorded, self.relative, len(self.payload), self.sha256,
                        lineage="motion_asset",
                    )

    def test_traversal_and_absolute_relative_identity_are_rejected(self):
        traversal = (
            str(self.historical_root)
            + "/production_assets/PROD-1/../PROD-1/assets/MA001.mp4"
        )
        for recorded, relative in (
            (traversal, self.relative),
            (self.recorded_path, Path("../production_assets/PROD-1/assets/MA001.mp4")),
            (self.recorded_path, Path("/production_assets/PROD-1/assets/MA001.mp4")),
        ):
            with self.subTest(recorded=recorded, relative=relative):
                with self.assertRaisesRegex(ArtifactRuntimeError, "traversal|relative|absolute"):
                    self.resolver.resolve_artifact(
                        recorded, relative, len(self.payload), self.sha256,
                        lineage="motion_asset",
                    )

    def test_symlink_escape_is_rejected_even_when_target_bytes_match(self):
        outside = Path(self.temp.name) / "outside.mp4"
        outside.write_bytes(self.payload)
        self.target.unlink()
        self.target.symlink_to(outside)

        with self.assertRaisesRegex(ArtifactRuntimeError, "symlink"):
            self.resolver.resolve_artifact(
                self.recorded_path, self.relative, len(self.payload), self.sha256,
                lineage="motion_asset",
            )

    def test_missing_size_sha_and_artifact_identity_mismatch_fail_closed(self):
        cases = (
            ("missing", len(self.payload), self.sha256, self.relative, "missing"),
            ("present", len(self.payload) + 1, self.sha256, self.relative, "size"),
            ("present", len(self.payload), "0" * 64, self.relative, "SHA"),
            (
                "present", len(self.payload), self.sha256,
                Path("production_assets/PROD-1/assets/MA002.mp4"), "identity",
            ),
        )
        for state, size, digest, relative, message in cases:
            with self.subTest(message=message):
                if state == "missing":
                    self.target.unlink(missing_ok=True)
                else:
                    self.target.parent.mkdir(parents=True, exist_ok=True)
                    self.target.write_bytes(self.payload)
                with self.assertRaisesRegex(ArtifactRuntimeError, message):
                    self.resolver.resolve_artifact(
                        self.recorded_path, relative, size, digest,
                        lineage="motion_asset",
                    )

    def test_configuration_rejects_root_mismatch_relative_roots_and_unknown_fields(self):
        valid = json.loads(self.config_path.read_text(encoding="utf-8"))
        cases = (
            dict(valid, canonical_repository_root=str(self.historical_root)),
            dict(valid, trusted_historical_repository_roots=["relative/root"]),
            dict(valid, unexpected=True),
        )
        for index, value in enumerate(cases):
            with self.subTest(index=index):
                path = Path(self.temp.name) / f"bad-{index}.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(ArtifactRuntimeError):
                    load_artifact_runtime_config(self.canonical_root, path)


if __name__ == "__main__":
    unittest.main()
