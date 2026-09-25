import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
        self.assertIn("--preflight", proc.stdout)

    def test_translation_unavailable_exits_with_clear_message(self):
        import video_translator_gui as legacy
        from videotranslator.cli import _cli
        from videotranslator.translation import TranslationUnavailableError

        # Isolate from the machine: CI lacks the ML stack (check_dependencies
        # would exit first) and the real config/keyring must not be read.
        with tempfile.NamedTemporaryFile(suffix=".mp4") as video, \
                mock.patch.object(legacy, "check_dependencies", return_value=([], [])), \
                mock.patch.object(legacy, "load_config", return_value={}), \
                mock.patch.object(legacy, "load_hf_token", return_value=""), \
                mock.patch.object(
                    legacy, "translate_video",
                    side_effect=TranslationUnavailableError("Google blocked"),
                ), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as ctx:
                _cli([video.name, "--lang-target", "it"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("[!] Google blocked", out.getvalue())


if __name__ == "__main__":
    unittest.main()
