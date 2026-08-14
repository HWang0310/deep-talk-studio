import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.transcription.local_whisper_cpp import (
    WhisperCppBootstrap,
    WhisperCppBootstrapError,
    WhisperCppRuntimeSpec,
    production_transcription_cache_root,
)


class LocalWhisperBootstrapTests(unittest.TestCase):
    def test_production_cache_namespace_is_not_selection_cache(self):
        root = production_transcription_cache_root(Path(tempfile.mkdtemp()))
        self.assertNotIn("asr-selection", str(root))
        self.assertTrue(str(root).endswith("transcription"))

    def test_missing_runtime_and_model_are_prepared_and_provenance_is_written(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = production_transcription_cache_root(Path(temp))
            model_bytes = b"verified-medium-model"
            model_sha = hashlib.sha256(model_bytes).hexdigest()
            spec = WhisperCppRuntimeSpec(
                version="1.9.2",
                source_commit="source-commit",
                model_name="medium",
                model_sha256=model_sha,
                model_bytes=len(model_bytes),
                source_url="https://example.invalid/whisper.cpp.tar.gz",
                model_url="https://example.invalid/ggml-medium.bin",
            )

            def build_runtime(runtime_path, _source_root):
                runtime_path.parent.mkdir(parents=True, exist_ok=True)
                runtime_path.write_text("runtime", encoding="utf-8")

            def download_model(target, _url):
                target.write_bytes(model_bytes)

            bootstrap = WhisperCppBootstrap(
                spec=spec,
                cache_root=cache,
                runtime_builder=build_runtime,
                model_downloader=download_model,
                runtime_version_reader=lambda _path: "whisper.cpp version: 1.9.2",
            )
            installation = bootstrap.ensure()

            self.assertTrue(installation.runtime_path.is_file())
            self.assertTrue(installation.model_path.is_file())
            self.assertEqual(installation.model_sha256, model_sha)
            provenance = json.loads(installation.provenance_path.read_text(encoding="utf-8"))
            self.assertEqual(provenance["runtime_version"], "1.9.2")
            self.assertEqual(provenance["source_commit"], "source-commit")
            self.assertEqual(provenance["model_sha256"], model_sha)
            self.assertEqual(provenance["bootstrap_status"], "verified")

    def test_model_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = production_transcription_cache_root(Path(temp))
            model_dir = cache / "models" / "whisper.cpp-1.9.2-medium"
            model_dir.mkdir(parents=True)
            (model_dir / "ggml-medium.bin").write_bytes(b"tampered")
            spec = WhisperCppRuntimeSpec(
                version="1.9.2",
                source_commit="source-commit",
                model_name="medium",
                model_sha256="0" * 64,
                model_bytes=8,
                source_url="https://example.invalid/whisper.cpp.tar.gz",
                model_url="https://example.invalid/ggml-medium.bin",
            )
            bootstrap = WhisperCppBootstrap(
                spec=spec,
                cache_root=cache,
                runtime_builder=lambda *_: None,
                model_downloader=lambda *_: None,
            )
            with self.assertRaises(WhisperCppBootstrapError):
                bootstrap.ensure()


if __name__ == "__main__":
    unittest.main()
