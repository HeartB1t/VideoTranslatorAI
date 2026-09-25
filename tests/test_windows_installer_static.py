import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup_windows.bat"
PIN = "mpv>=1.0.6,<2"


class WindowsInstallerStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SETUP.read_bytes()
        cls.text = cls.raw.decode("ascii")  # raises on any non-ASCII byte
        cls.flat = cls.text.replace("\r\n", "\n")
        cls.lines = cls.flat.split("\n")

    def test_installer_copies_python_package(self):
        self.assertIn(r"%SCRIPT_DIR%videotranslator", self.text)
        self.assertIn(r"%INSTALL_DIR%\videotranslator", self.text)
        self.assertIn(r"videotranslator\*.py", self.text)

    def test_validate_install_imports_application(self):
        self.assertIn('pushd "%INSTALL_DIR%"', self.text)
        self.assertIn('"import video_translator_gui"', self.text)
        self.assertIn("Application importable.", self.text)

    def test_every_line_ends_with_crlf(self):
        lf_only = [number for number, line in enumerate(self.raw.split(b"\n")[:-1], 1)
                   if not line.endswith(b"\r")]
        self.assertEqual(lf_only, [])

    def test_player_runtime_paths(self):
        self.assertIn(r'set "MPV_DIR=%INSTALL_DIR%\mpv-runtime"', self.text)
        self.assertIn(r'set "USER_MPV_RUNTIME=%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime"', self.text)

    def test_player_step_runs_after_ffmpeg_in_install_and_repair(self):
        self.assertRegex(self.flat, r'call :step_ffmpeg "4/6" "0"\s+call :step_player "5/6"\s+'
                                    r'call :step_shortcut "6/6"')
        self.assertRegex(self.flat, r'call :step_ffmpeg "4/6" "1"\s+call :step_player "5/6"')
        self.assertIn('echo [6/6] Desktop shortcut already present, skipping.', self.text)
        self.assertNotRegex(self.flat, r'"\d/5"')
        self.assertNotIn("[5/5]", self.text)

    def _label_body(self, label, end_pattern):
        """Text from the line ``:label`` up to the first line matching ``end_pattern``."""
        match = re.search(rf"\n:{label}\n(.*?)\n{end_pattern}\n", self.flat, re.S)
        self.assertIsNotNone(match, f":{label} not found")
        return match.group(1)

    def test_the_player_check_only_warns_after_validation(self):
        pattern = r'call :validate_install\nif errorlevel 1 \( pause & exit /b 1 \)\ncall :player_check\n'
        self.assertEqual(len(re.findall(pattern, self.flat)), 2)
        body = self._label_body("player_check", "goto :eof")  # the final line, not the early `if`
        self.assertIn('-m videotranslator.libmpv_runtime check --dir "%MPV_DIR%"', body)
        self.assertNotIn("exit /b 1", body)

    def test_the_pin_has_its_own_quoted_variable_and_is_never_echoed(self):
        self.assertIn(f'set "MPV_PIN={PIN}"', self.text)
        self.assertIn('-m pip install "%MPV_PIN%" --quiet', self.text)
        for line in self.lines:
            if line.lstrip().lower().startswith("echo"):
                self.assertNotIn("MPV_PIN", line)
        self.assertIn(PIN, (ROOT / "requirements-player.txt").read_text(encoding="utf-8"))

    def test_libmpv_install_runs_from_the_install_dir_and_never_fails_the_setup(self):
        self.assertIn('-m videotranslator.libmpv_runtime install --dest "%MPV_DIR%"', self.text)
        body = self._label_body("step_player", ":player_check")
        self.assertIn('pushd "%INSTALL_DIR%"', body)
        self.assertIn("Integrated player disabled - everything else works", body)
        self.assertNotIn("exit /b 1", body)

    def test_both_uninstall_lists_remove_python_mpv(self):
        # Full list: right before its last line; custom menu: its own prompt.
        self.assertIn("    mpv python-mpv ^\n    yt-dlp edge-tts deep-translator pydub pyloudnorm "
                      "soundfile sacremoses sentencepiece 2>nul", self.flat)
        self.assertIn('if /i "!Q_MPV!"=="Y" "%PYTHON_EXE%" -m pip uninstall -y mpv python-mpv', self.text)

    def test_per_user_cleanup_removes_only_the_player_runtime(self):
        self.assertIn('rmdir /S /Q "%USER_MPV_RUNTIME%"', self.text)
        self.assertIn(r'rmdir /S /Q "%%~U\AppData\Local\VideoTranslatorAI\mpv-runtime"', self.text)
        self.assertNotIn(r'rmdir /S /Q "%%~U\AppData\Local\VideoTranslatorAI"', self.text)
        self.assertNotIn(r'rmdir /S /Q "%LOCALAPPDATA%\VideoTranslatorAI"', self.text)

    def test_pipeline_packages_line_is_unchanged(self):
        self.assertIn('set "PACKAGES=faster-whisper demucs soundfile edge-tts deep-translator pydub '
                      'yt-dlp pyloudnorm sentencepiece sacremoses torchcodec silero-vad keyring"',
                      self.text)
        self.assertNotRegex(self.text, r"\bav>=|onnxruntime")

    def test_no_folder_named_mpv(self):
        self.assertIsNone(re.search(r'\\mpv(["\\\s]|$)', self.text, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
