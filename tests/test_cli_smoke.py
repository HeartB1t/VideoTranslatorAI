import subprocess
import sys
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_help_does_not_require_runtime_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "video_translator_gui.py"), "--help"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("--translation-engine", proc.stdout)
        self.assertIn("--no-cove", proc.stdout)
        self.assertIn("--hotwords", proc.stdout)


if __name__ == "__main__":
    unittest.main()
