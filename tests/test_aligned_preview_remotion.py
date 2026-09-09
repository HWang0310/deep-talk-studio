import json,subprocess,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; TEMPLATE=ROOT/"renderer_templates/aligned_preview_remotion/src/AlignedPreview.tsx"
class AlignedPreviewRemotionTests(unittest.TestCase):
 def test_composition_uses_aroll_base_and_muted_ready_overlays(self):
  source=TEMPLATE.read_text(encoding="utf-8")
  self.assertIn("layer 0",source);self.assertIn("muted",source);self.assertNotIn("backgroundMusic",source);self.assertNotIn("animation:",source)
 def test_profile_contract_is_1920x1080_30_and_dynamic_duration(self):
  root=(ROOT/"renderer_templates/aligned_preview_remotion/src/Root.tsx").read_text()
  self.assertIn("width={1920}",root);self.assertIn("height={1080}",root);self.assertIn("fps={30}",root);self.assertIn("Math.ceil",root)
 def test_package_versions_are_locked(self):
  package=json.loads((ROOT/"renderer_templates/aligned_preview_remotion/package.json").read_text());self.assertEqual(package["dependencies"]["remotion"],"4.0.507")
 def test_basic_subtitles_are_frame_driven_and_visuals_respect_reserved_region(self):
  subtitle=(ROOT/"renderer_templates/aligned_preview_remotion/src/BasicSubtitles.tsx").read_text()
  source=TEMPLATE.read_text()
  self.assertIn("useCurrentFrame",subtitle);self.assertIn("subtitle-region",subtitle)
  self.assertNotIn("karaoke",subtitle.casefold());self.assertIn("content-safe-region",source)

if __name__=="__main__":unittest.main()
