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
        self.assertIn("--preflight-player", proc.stdout)
        self.assertIn("--no-original-audio", proc.stdout)
        self.assertIn("--output-dir", proc.stdout)

    def _translate_kwargs_for(self, config, extra_args):
        """Run the CLI with an isolated config and capture the kwargs that
        reach ``translate_video``."""
        import video_translator_gui as legacy
        from videotranslator.cli import _cli

        captured = {}

        def fake_translate(**kwargs):
            captured.update(kwargs)
            return {"video": "/tmp/out.mp4", "segments": []}

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video, \
                mock.patch.object(legacy, "check_dependencies", return_value=([], [])), \
                mock.patch.object(legacy, "load_config", return_value=config), \
                mock.patch.object(legacy, "load_hf_token", return_value=""), \
                mock.patch.object(legacy, "translate_video", side_effect=fake_translate), \
                contextlib.redirect_stdout(io.StringIO()):
            _cli([video.name, "--lang-target", "it"] + extra_args)
        return captured

    def _keep_original_audio_for(self, config, extra_args):
        return self._translate_kwargs_for(config, extra_args)["keep_original_audio"]

    def test_output_dir_flag_flows_to_translate_video(self):
        self.assertEqual(
            self._translate_kwargs_for({}, ["--output-dir", "/data/out"])["output_dir"],
            "/data/out",
        )

    def test_output_dir_from_config_when_flag_absent(self):
        self.assertEqual(
            self._translate_kwargs_for({"output_dir": "/cfg/out"}, [])["output_dir"],
            "/cfg/out",
        )

    def test_output_dir_flag_overrides_config(self):
        self.assertEqual(
            self._translate_kwargs_for(
                {"output_dir": "/cfg/out"}, ["--output-dir", "/flag/out"])["output_dir"],
            "/flag/out",
        )

    def test_output_dir_is_none_by_default(self):
        self.assertIsNone(self._translate_kwargs_for({}, [])["output_dir"])

    def test_original_audio_kept_by_default(self):
        self.assertTrue(self._keep_original_audio_for({}, []))

    def test_no_original_audio_flag_disables_it(self):
        self.assertFalse(self._keep_original_audio_for({}, ["--no-original-audio"]))

    def test_config_can_disable_original_audio(self):
        self.assertFalse(
            self._keep_original_audio_for({"keep_original_audio": False}, []))

    def test_flag_overrides_config_enabling_it(self):
        self.assertFalse(
            self._keep_original_audio_for(
                {"keep_original_audio": True}, ["--no-original-audio"]))

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
