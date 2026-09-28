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

    def test_every_exclamation_mark_survives_delayed_expansion(self):
        # The script runs with delayed expansion: a bare "!" vanished ("[!]"
        # printed "[]"), and two on one command deleted everything between
        # them, down to the Start-Process of the Ollama uninstaller. Only
        # !VAR! references and the escaped "^^!" may carry one; PowerShell
        # code builds the marker with [char]33.
        reference = re.compile(r"![A-Za-z_][A-Za-z0-9_]*!")
        for number, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("::") or stripped.lower().startswith("rem "):
                continue
            with self.subTest(line=number, text=stripped[:80]):
                self.assertNotIn("!", reference.sub("", line.replace("^^!", "")))

    def test_the_uninstallers_powershell_builds_its_marker_from_char_33(self):
        for label, end in (("remove_python", ":remove_git"), ("remove_git", ":remove_ollama"),
                           ("remove_ollama", ":end")):
            body = self._label_body(label, end)
            with self.subTest(label=label):
                self.assertIn("$W = '[' + [char]33 + ']';", body)
                self.assertIn("Start-Process -FilePath", body)

    def test_a_finished_run_asks_for_a_key_once(self):
        # :print_done already ends with a pause: another one after it made
        # the user press a key twice at the end of an install or repair.
        self.assertTrue(self._label_body("print_done", ":pause_exit").rstrip().endswith("pause\ngoto :eof"))
        for done in ("Installation complete", "Repair complete"):
            with self.subTest(done=done):
                self.assertIn(f'call :print_done "{done}"\nexit /b 0\n', self.flat)

    def test_the_installer_copy_stays_only_when_it_is_the_running_script(self):
        # Run from the release folder, the uninstaller left the install folder
        # behind with only setup_windows.bat in it. A marker written next to
        # the running script tells whether the two folders are the same.
        body = self._label_body("remove_app", ":remove_shortcut_public")
        self.assertIn('set "_KEEP_SELF=1"', body)
        self.assertIn('type nul > "%SCRIPT_DIR%%_SELF_MARK%" 2>nul', body)
        self.assertIn('if not exist "%INSTALL_DIR%\\%_SELF_MARK%" set "_KEEP_SELF="', body)
        self.assertIn('if not defined _KEEP_SELF del /F /Q "%INSTALL_DIR%\\setup_windows.bat" 2>nul', body)
        # The marker check comes before anything is deleted.
        self.assertLess(body.index("_SELF_MARK%"), body.index("rmdir /S /Q"))

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
        # Repair always re-creates the shortcuts: an older install gets the
        # Start Menu entries too (comment lines may sit in between).
        self.assertRegex(self.flat, r'call :step_ffmpeg "4/6" "1"\s+call :step_player "5/6"\s+'
                                    r'(?:::[^\n]*\n\s*)*call :step_shortcut "6/6"')
        self.assertNotRegex(self.flat, r'"\d/5"')
        self.assertNotIn("[5/5]", self.text)

    def _label_body(self, label, end_pattern):
        """Text from the line ``:label`` up to the first line matching ``end_pattern``."""
        match = re.search(rf"\n:{label}\n(.*?)\n{end_pattern}\n", self.flat, re.S)
        self.assertIsNotNone(match, f":{label} not found")
        return match.group(1)

    def test_the_player_check_only_warns_after_validation(self):
        pattern = (r'call :validate_install\nif errorlevel 1 \( call :logfile "RESULT: [a-z]+ incomplete" '
                   r'& pause & exit /b 1 \)\ncall :player_check\n')
        self.assertEqual(len(re.findall(pattern, self.flat)), 2)
        body = self._label_body("player_check", "goto :eof")  # the final line, not the early `if`
        self.assertIn('-m videotranslator.libmpv_runtime check --dir "%MPV_DIR%"', body)
        self.assertNotIn("exit /b 1", body)

    def test_player_uses_the_canonical_profile(self):
        body = self._label_body("step_player", ":player_check")
        self.assertIn('-r "%PLAYER_REQUIREMENTS%"', body)
        self.assertIn('set "PLAYER_REQUIREMENTS=%INSTALL_DIR%\\requirements-player.txt"', self.text)
        self.assertIn(PIN, (ROOT / "requirements-player.txt").read_text(encoding="utf-8"))

    def test_pyannote_uses_profile_constraints_without_cmd_redirection(self):
        # Version bounds live in text files, so cmd never parses their < or >.
        commands = [line for line in self.lines if line.startswith('"%PYTHON_EXE%" -m pip install')]
        command = next(line for line in commands if ' pyannote.audio ' in line)
        self.assertIn('-c "%OPTIONAL_REQUIREMENTS%"', command)
        self.assertIn('pyannote.audio>=3.1,<4.0',
                      (ROOT / 'requirements-optional.txt').read_text())
        self.assertNotRegex(self.flat, re.compile(r'^set "[A-Z_0-9]+="[^"\n]*[<>]', re.M))

    def test_every_pip_install_preserves_the_core_optional_and_torch_bounds(self):
        commands = [line.strip() for line in self.lines
                    if line.lstrip().startswith('"%PYTHON_EXE%" -m pip install ')]
        self.assertGreater(len(commands), 10)
        for command in commands:
            for profile in ('CORE_REQUIREMENTS', 'OPTIONAL_REQUIREMENTS', 'GPU_REQUIREMENTS'):
                with self.subTest(command=command, profile=profile):
                    self.assertIn(f'-c "%{profile}%"', command)

    def test_profiles_are_required_and_copied_for_later_repair(self):
        body = self.flat[self.flat.index('\n:step_copy_files\n'):
                         self.flat.index('\n:step_install_deps\n')]
        for profile in ('core', 'optional', 'gpu-cu124', 'player'):
            self.assertIn(f'requirements-{profile}.txt', body)
        self.assertIn('if not exist "%SCRIPT_DIR%%%F"', body)
        self.assertLess(body.index('if not exist "%SCRIPT_DIR%%%F"'), body.index('os.path.samefile'))
        self.assertIn('copy /Y "%SCRIPT_DIR%%%F" "%INSTALL_DIR%\\%%F"', body)
        # A missing profile must stop before pip can modify the installation.
        self.assertIn('exit /b 1', body[:body.index('os.path.samefile')])

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

    def test_per_user_cleanup_removes_every_app_folder_and_nothing_else(self):
        # The app's own per-user folders: config + logs (Roaming), data with the
        # player, JS and Wav2Lip runtimes (Local), live cache and shaders (Temp).
        self.assertIn(r'set "USER_APP_DATA=%APPDATA%\VideoTranslatorAI"', self.text)
        self.assertIn(r'set "USER_LOCAL_DATA=%LOCALAPPDATA%\VideoTranslatorAI"', self.text)
        self.assertIn(r'set "USER_TEMP_DATA=%TEMP%\VideoTranslatorAI"', self.text)
        for var in ("USER_APP_DATA", "USER_LOCAL_DATA", "USER_TEMP_DATA"):
            self.assertIn(f'rmdir /S /Q "%{var}%"', self.text)
        for sub in (r"AppData\Roaming\VideoTranslatorAI", r"AppData\Local\VideoTranslatorAI",
                    r"AppData\Local\Temp\VideoTranslatorAI"):
            self.assertIn(f'rmdir /S /Q "%%~U\\{sub}"', self.text)
        # never a parent folder shared with other programs
        for parent in ("%APPDATA%", "%LOCALAPPDATA%", "%TEMP%", r"%%~U\AppData\Local",
                       r"%%~U\AppData\Roaming", r"%%~U\AppData\Local\Temp"):
            self.assertNotIn(f'rmdir /S /Q "{parent}"', self.text)

    def test_uninstall_removes_the_saved_keys_before_the_packages(self):
        self.assertIn(":remove_saved_keys", self.text)
        self.assertIn("keyring.delete_password('VideoTranslatorAI',u)", self.text)
        for user in ("'hf_token'", "'elevenlabs_api_key'"):
            self.assertIn(user, self.text)
        full = self.text[self.text.index(":uninst_full"):self.text.index(":uninst_user")]
        self.assertLess(full.index("call :remove_saved_keys"),
                        full.index("call :remove_python_packages_all"))
        self.assertIn("call :remove_saved_keys", self.text[self.text.index(":uninst_user"):
                                                           self.text.index(":uninst_custom")])

    def test_model_cache_filter_covers_marian(self):
        self.assertEqual(self.text.count("whisper XTTS coqui wav2vec pyannote opus-mt"), 2)

    def test_pipeline_and_torch_install_from_canonical_profiles(self):
        body = self.flat[self.flat.index('\n:step_install_deps\n'):
                         self.flat.index('\n:step_tts_failed\n')]
        self.assertIn('-r "%CORE_REQUIREMENTS%" pyannote.audio sentencepiece sacremoses silero-vad keyring', body)
        self.assertIn('-r "%GPU_REQUIREMENTS%"', body)
        self.assertNotIn('set "PACKAGES=', body)
        self.assertNotIn('"torch==', body)
        # With a version range, --no-deps could pick a torch version that the
        # pinned torchaudio/torchvision cannot use during a forced reinstall.
        self.assertNotIn('--no-deps', body)
        core = (ROOT / 'requirements-core.txt').read_text().splitlines()
        self.assertIn('requests', core)
        self.assertIn('numpy>=2.0,<2.4', core)
        self.assertIn('audioop-lts; python_version >= "3.13"', core)
        self.assertNotRegex(self.text, r"\bav>=|onnxruntime")

    def test_no_folder_named_mpv(self):
        self.assertIsNone(re.search(r'\\mpv(["\\\s]|$)', self.text, re.MULTILINE))

    # -- setup log (install, repair, uninstall) --

    def test_setup_log_survives_the_uninstall(self):
        self.assertIn(r'set "VTAI_SETUP_LOG=%USERPROFILE%\VideoTranslatorAI-setup.log"', self.text)
        for mode in ("INSTALL", "REPAIR", "UNINSTALL"):
            self.assertIn(f'call :log_session "{mode}"', self.text)
        # nothing the uninstaller deletes may contain the log file
        self.assertNotIn(r'del /Q "%USERPROFILE%\VideoTranslatorAI-setup.log"', self.text)

    def test_every_log_call_is_one_safe_quoted_argument(self):
        calls = [line for line in self.lines if "call :logfile" in line]
        self.assertGreater(len(calls), 50)
        for line in calls:
            message = re.search(r'call :logfile "([^"]*)"', line)
            self.assertIsNotNone(message, line)
            self.assertNotRegex(message.group(1), r"[<>|^]", line)

    def test_every_download_hides_the_progress_bar(self):
        # PowerShell 5.1 redraws the bar per chunk: a 416 MB file took minutes.
        lines = self.flat.split("\n")
        downloads = [n for n, line in enumerate(lines) if "Invoke-WebRequest" in line]
        self.assertEqual(len(downloads), 7)
        for n in downloads:
            self.assertIn("$ProgressPreference = 'SilentlyContinue';", lines[n - 1])

    # -- Visual C++ runtime: torch\lib\c10.dll fails with WinError 126 without it --

    def test_the_vc_runtime_comes_before_pytorch_in_install_and_repair(self):
        body = self.flat[self.flat.index("\n:step_install_deps\n"):]
        self.assertLess(body.index("call :step_vc_runtime"), body.index('-r "%GPU_REQUIREMENTS%"'))

    # -- PyTorch: the 2.5 GB CUDA build only where an NVIDIA GPU is found --

    def test_the_cuda_build_is_chosen_only_for_an_nvidia_gpu(self):
        body = self._label_body("detect_torch_build", "exit /b 0")
        self.assertIn("where nvidia-smi", body)
        # the PCI vendor id finds the card even before its driver is installed
        self.assertIn("Get-CimInstance Win32_VideoController", body)
        self.assertIn(r"$_.PNPDeviceID -like 'PCI\VEN_10DE*'", body)
        # the CPU build only once both probes missed
        self.assertLess(body.index("where nvidia-smi"), body.index('set "TORCH_BUILD=cpu"'))
        self.assertLess(body.index("VEN_10DE"), body.index('set "TORCH_BUILD=cpu"'))
        self.assertIn('call :logfile "Step 3/6 PyTorch: no NVIDIA GPU found, CPU build"', body)

    def test_the_cpu_build_skips_every_cuda_install(self):
        body = self.flat[self.flat.index("\n:step_install_deps\n"):self.flat.index("\n:step_tts_failed\n")]
        cuda = [match.start() for match in re.finditer("download.pytorch.org/whl/cu124", body)]
        self.assertEqual(len(cuda), 2)
        # the first install
        skip = body.index('if "%TORCH_BUILD%"=="cpu" goto step_torch_cpu')
        self.assertLess(body.index("call :detect_torch_build"), skip)
        self.assertLess(skip, cuda[0])
        self.assertLess(cuda[0], body.index("goto step_torch_done\n\n:step_torch_cpu\n"))
        cpu = body[body.index("\n:step_torch_cpu\n"):body.index("\n:step_torch_done\n")]
        self.assertIn('-r "%GPU_REQUIREMENTS%"', cpu)  # PyPI's Windows wheels are the CPU build
        self.assertNotIn("--index-url", cpu)
        # the "+cu" check that brings a replaced CUDA build back
        skip = body.index('if "%TORCH_BUILD%"=="cpu" goto step_torch_checked')
        self.assertLess(body.index("\n:step_torch_done\n"), skip)
        self.assertLess(skip, cuda[1])
        self.assertLess(cuda[1], body.index("\n:step_torch_checked\n"))

    # -- per-user packages of Python 3.11 --

    def test_uninstalling_python_also_removes_its_per_user_packages(self):
        # pip without admin rights (the app installs what it misses that way)
        # writes to %APPDATA%\Python\Python311; the Python uninstaller left it,
        # and the next Python 3.11 loaded those packages again.
        self.assertIn(r'set "PY311_USER_SITE=%APPDATA%\Python\Python311"', self.text)
        self.assertEqual(self.text.count("Uninstall Python 3.11 and its per-user packages ? [Y/N]: "), 2)
        body = self._label_body("remove_python", ":remove_git")
        self.assertLess(body.index("Removing leftover folder"), body.index("call :remove_python_user_site"))
        site = self._label_body("remove_python_user_site", "exit /b 0")
        self.assertLess(site.index("call :python311_present"), site.index('rmdir /S /Q "%PY311_USER_SITE%"'))

    def test_the_per_user_packages_stay_while_a_python_311_is_left(self):
        # Every CPython 3.11 of the account shares that folder.
        body = self._label_body("python311_present", "exit /b 1")
        for key in (r"HKCU:\Software\Python\PythonCore\3.11\InstallPath",
                    r"HKLM:\Software\Python\PythonCore\3.11\InstallPath",
                    r"HKLM:\Software\WOW6432Node\Python\PythonCore\3.11\InstallPath"):
            self.assertIn(key, body)
        self.assertIn("(Join-Path $d 'python.exe')", body)
        self.assertIn("'where python 2^>nul'", body)
        self.assertIn("sys.version_info[:2] == (3, 11)", body)

    def test_the_vc_runtime_is_verified_and_run_from_an_admin_only_folder(self):
        body = self._label_body("step_vc_runtime", ":step_vc_runtime_manual")
        self.assertIn(r'set "VC_DIR=%INSTALL_DIR%\_downloads"', body)
        self.assertNotIn("%TEMP%", body)
        self.assertIn("https://aka.ms/vs/17/release/vc_redist.x64.exe", body)
        # the signature is checked before the installer runs
        self.assertLess(body.index("Get-AuthenticodeSignature"), body.index("Start-Process"))
        self.assertIn("-notlike '*O=Microsoft Corporation*'", body)
        for dll in ("msvcp140.dll", "vcruntime140_1.dll"):
            self.assertIn(dll, body)

    def test_the_uninstaller_never_removes_the_shared_vc_runtime(self):
        uninstall = self.flat[self.flat.index("\n:remove_app\n"):]
        self.assertNotIn("vc_redist", uninstall)
        self.assertNotIn("msvcp140", uninstall)

    # -- updater hand-over (docs/superpowers/specs/2026-09-27-windows-updater-design.md) --

    def _mode_repair(self):
        return self.flat[self.flat.index("\n:mode_repair\n"):self.flat.index("\n:mode_uninstall\n")]

    def test_the_handover_flag_is_read_once_and_cleared_before_dispatch(self):
        head = self.flat[:self.flat.index("\n:dispatch\n")]
        self.assertIn('set "VTAI_HANDED_OVER=%VTAI_UPDATE_HANDOFF%"\nset "VTAI_UPDATE_HANDOFF="\n'
                      'set "VTAI_NEW_SETUP="', head)

    def test_the_handover_is_a_top_level_line_without_delayed_expansion(self):
        body = self._mode_repair()
        self.assertIn('set "VTAI_UPDATE_HANDOFF=1"\nsetlocal DisableDelayedExpansion\n'
                      '"%VTAI_NEW_SETUP%" repair', body)
        # reached by goto, never inside parentheses or a called subroutine
        self.assertIn("if defined VTAI_NEW_SETUP goto repair_handover", body)
        self.assertNotIn("call :repair_handover", self.text)
        before = body[:body.index('"%VTAI_NEW_SETUP%" repair')]
        depth = 0
        for line in before.split("\n"):
            code = re.sub(r'"[^"]*"', "", line)
            if not code.strip().startswith("::"):
                depth += code.count("(") - code.count(")")
        self.assertEqual(depth, 0)

    def test_the_update_is_staged_in_program_files_and_handed_over_only_on_10(self):
        self.assertIn(r'set "UPDATE_DIR=%INSTALL_DIR%\_update"', self.text)
        body = self._label_body("update_prepare", ":update_prepare_ready")
        self.assertIn('-m videotranslator.updater download --local "%SCRIPT_DIR%." '
                      '--dest "%UPDATE_DIR%" --log "%VTAI_SETUP_LOG%"', body)
        self.assertIn('if "%UPDATE_RC%"=="10" goto update_prepare_ready', body)
        self.assertNotIn("%TEMP%", body)

    def test_the_installer_is_kept_and_never_copied_onto_itself(self):
        body = self.flat[self.flat.index("\n:step_copy_files\n"):self.flat.index("\n:step_install_deps\n")]
        self.assertIn("os.path.samefile", body)
        self.assertLess(body.index("os.path.samefile"), body.index("Copying script"))
        self.assertIn(r'copy /Y "%SCRIPT_DIR%setup_windows.bat" "%INSTALL_DIR%\setup_windows.bat"', body)

    def test_the_update_entry_runs_elevated_through_cmd(self):
        self.assertIn(r'set "START_MENU_DIR=%ProgramData%\Microsoft\Windows\Start Menu\Programs'
                      r'\Video Translator AI"', self.text)
        self.assertIn("$upd.TargetPath = $env:ComSpec;", self.text)
        self.assertIn("$b[0] -eq 0x4C) { $b[0x15] = $b[0x15] -bor 0x20;", self.text)
        self.assertIn('rmdir /S /Q "%START_MENU_DIR%"', self.text)

    def test_uninstall_never_deletes_the_running_script_early(self):
        body = self._label_body("remove_app", "exit /b 0\n\n:remove_shortcut_public")
        self.assertIn('if /i not "%%~nxF"=="setup_windows.bat" del /F /Q "%%~F"', body)
        # the install folder is never removed recursively: only a plain rmdir,
        # which succeeds when the folder is empty
        self.assertNotIn('rmdir /S /Q "%INSTALL_DIR%"', self.text)
        done = self.flat[self.flat.index("\n:uninst_done\n"):]
        self.assertIn('rmdir "%INSTALL_DIR%" 2>nul', done)


if __name__ == "__main__":
    unittest.main()
