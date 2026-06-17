import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

import videotranslator


ROOT = Path(__file__).resolve().parents[1]


class PackagingMetadataTests(unittest.TestCase):
    def test_pyproject_exposes_installable_console_scripts(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["project"]["name"], "videotranslatorai")
        scripts = data["project"]["scripts"]
        self.assertEqual(scripts["videotranslatorai"], "videotranslator.cli:main")
        self.assertEqual(scripts["videotranslator-ai"], "videotranslator.cli:main")
        self.assertEqual(scripts["video-translator-ai"], "videotranslator.cli:main")
        gui_scripts = data["project"]["gui-scripts"]
        self.assertEqual(gui_scripts["videotranslatorai-gui"], "videotranslator.cli:main")
        self.assertEqual(gui_scripts["videotranslator-ai-gui"], "videotranslator.cli:main")

    def test_package_version_is_single_source(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["tool"]["setuptools"]["dynamic"]["version"]["attr"], "videotranslator.__version__")
        self.assertRegex(videotranslator.__version__, r"^\d+\.\d+\.\d+$")


class ModuleEntryPointSmokeTests(unittest.TestCase):
    def test_python_m_videotranslator_help_uses_legacy_cli(self):
        proc = subprocess.run(
            [sys.executable, "-m", "videotranslator", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("--translation-engine", proc.stdout)
        self.assertIn("--preflight", proc.stdout)


if __name__ == "__main__":
    unittest.main()
