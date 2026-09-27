"""Environment defaults the package applies at import (Windows symlink warning)."""

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
