import re
import unittest
from pathlib import Path

import deeptalk_studio


class VersionTests(unittest.TestCase):
    def test_public_package_version_matches_project_metadata(self):
        text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(deeptalk_studio.__version__, match.group(1))


if __name__ == "__main__":
    unittest.main()
