"""Environment defaults the package applies at import (Windows symlink warning)."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from videotranslator import startup_env

ROOT = Path(__file__).resolve().parents[1]


class ApplyStartupEnvTests(unittest.TestCase):
    def test_missing_variables_get_their_default(self):
        environ = {}
        applied = startup_env.apply_startup_env(environ)
        self.assertEqual(environ.get("HF_HUB_DISABLE_SYMLINKS_WARNING"), "1")
        self.assertEqual(applied, dict(startup_env.STARTUP_ENV_DEFAULTS))

    def test_a_value_the_user_exported_wins(self):
        environ = {"HF_HUB_DISABLE_SYMLINKS_WARNING": "0"}
        applied = startup_env.apply_startup_env(environ)
        self.assertEqual(environ["HF_HUB_DISABLE_SYMLINKS_WARNING"], "0")
        self.assertNotIn("HF_HUB_DISABLE_SYMLINKS_WARNING", applied)

    def test_importing_the_package_sets_the_defaults_in_a_fresh_interpreter(self):
        env = {k: v for k, v in os.environ.items() if k not in startup_env.STARTUP_ENV_DEFAULTS}
        code = ("import json, os, videotranslator; "
                "print(json.dumps({k: os.environ.get(k) for k in %r}))"
                % sorted(startup_env.STARTUP_ENV_DEFAULTS))
        proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]),
                         dict(startup_env.STARTUP_ENV_DEFAULTS))

    def test_huggingface_hub_sees_the_default_when_imported_after_the_package(self):
        if importlib.util.find_spec("huggingface_hub") is None:
            self.skipTest("huggingface_hub is not installed")
        env = {k: v for k, v in os.environ.items() if k not in startup_env.STARTUP_ENV_DEFAULTS}
        code = ("import videotranslator; from huggingface_hub import constants; "
                "print(constants.HF_HUB_DISABLE_SYMLINKS_WARNING)")
        proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip().splitlines()[-1], "True")



class HardenStdStreamsTests(unittest.TestCase):
    """Windows writes a redirected stdout in the ANSI code page (cp1252): the
    first "\u2192" printed stopped the pipeline with UnicodeEncodeError."""

    def _stream(self, encoding, errors="strict"):
        return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors=errors)

    def test_a_legacy_code_page_escapes_a_character_it_lacks(self):
        stream = self._stream("cp1252")
        self.assertEqual(startup_env.harden_std_streams([stream]), [stream])
        stream.write("[6/6] voce \u2192 mix")
        stream.flush()
        self.assertEqual(stream.buffer.getvalue(), b"[6/6] voce \\u2192 mix")

    def test_utf8_a_chosen_error_policy_and_plain_objects_are_left_alone(self):
        utf8 = self._stream("utf-8")
        chosen = self._stream("cp1252", errors="replace")
        self.assertEqual(startup_env.harden_std_streams([utf8, chosen, io.StringIO(), None]), [])
        self.assertEqual((utf8.errors, chosen.errors), ("strict", "replace"))

    def test_importing_the_package_hardens_a_redirected_cp1252_stdout(self):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONUTF8"}
        env["PYTHONIOENCODING"] = "cp1252"
        code = "import videotranslator; print('voce \\u2192 mix')"
        proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                              capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), b"voce \\u2192 mix")


if __name__ == "__main__":
    unittest.main()
