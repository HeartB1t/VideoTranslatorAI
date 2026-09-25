"""Importing the player modules never pulls a heavy or native dependency (spec 7.1).

Each import runs in a fresh interpreter, so the result does not depend on
which tests ran before in this process ([CC] T3).
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "videotranslator.libmpv_runtime",
    "videotranslator.system_packages",
    "videotranslator.player_panel_tk",
    "videotranslator.subprocess_utils",
    "videotranslator.ui_strings_player",
)
FORBIDDEN = ("mpv", "av", "faster_whisper", "edge_tts", "transformers", "yt_dlp", "onnxruntime")


class ImportHygieneTests(unittest.TestCase):
    def test_player_modules_import_without_heavy_dependencies(self):
        for module in MODULES:
            with self.subTest(module=module):
                code = ("import importlib, json, sys; importlib.import_module(%r); "
                        "print(json.dumps(sorted(m for m in %r if m in sys.modules)))"
                        % (module, FORBIDDEN))
                proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=60)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]), [])


if __name__ == "__main__":
    unittest.main()
