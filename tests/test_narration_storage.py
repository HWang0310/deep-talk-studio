import copy
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.narration_storage import (
    NarrationBundle,
    NarrationStorageError,
    load_narration_bundle,
    save_narration_bundle,
)


def bundle(media_id="MEDIA001", sha="a" * 64):
    return NarrationBundle(
        media={
            "artifact_version": "narration-media/1",
            "media_id": media_id,
            "sha256": sha,
            "presentation_duration_seconds": "10",
            "artifact_digest": "m" * 64,
            "imported_at": "2026-08-13T12:00:00+08:00",
        },
        extracted_audio={
            "artifact_version": "extracted-audio/1",
            "audio_id": "AUDIO-" + media_id,
            "narration_media_id": media_id,
            "artifact_digest": "e" * 64,
        },
        mapping={
            "artifact_version": "audio-timestamp-mapping/1",
            "mapping_id": "MAP-" + media_id,
            "narration_media_id": media_id,
            "mapping_digest": "p" * 64,
        },
        transcript={
            "artifact_version": "timed-transcript/1",
            "transcript_id": "TR-" + media_id,
            "narration_media_id": media_id,
            "transcript_digest": "t" * 64,
        },
    )


class NarrationStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_storage_is_immutable_and_new_media_never_inherits_transcript(self):
        paths = save_narration_bundle(bundle(), self.root)
        with self.assertRaisesRegex(NarrationStorageError, "覆盖"):
            save_narration_bundle(bundle(), self.root)
        changed = bundle(media_id="MEDIA002", sha="b" * 64)
        changed_paths = save_narration_bundle(changed, self.root)
        self.assertNotEqual(paths.media.parent, changed_paths.media.parent)
        self.assertEqual(load_narration_bundle(changed_paths.media).transcript["transcript_id"], "TR-MEDIA002")

    def test_reload_detects_tamper_missing_and_wrong_root_binding(self):
        paths = save_narration_bundle(bundle(), self.root)
        paths.mapping.write_text("{}", encoding="utf-8")
        with self.assertRaises(NarrationStorageError):
            load_narration_bundle(paths.media)

        wrong = bundle(media_id="../escape")
        with self.assertRaises(NarrationStorageError):
            save_narration_bundle(wrong, self.root)

    def test_partial_bundle_does_not_search_another_media_directory(self):
        complete = save_narration_bundle(bundle(), self.root)
        partial = bundle(media_id="MEDIA003", sha="c" * 64)
        partial = NarrationBundle(media=partial.media)
        paths = save_narration_bundle(partial, self.root)
        loaded = load_narration_bundle(paths.media)
        self.assertIsNone(loaded.transcript)
        self.assertNotEqual(complete.media.parent, paths.media.parent)


if __name__ == "__main__":
    unittest.main()
