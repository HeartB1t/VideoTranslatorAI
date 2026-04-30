import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.cosyvoice_runtime import (
    cosyvoice_cache_dir,
    cosyvoice_download_model,
    cosyvoice_install,
    cosyvoice_is_installed,
    cosyvoice_model_present,
)


class CosyVoiceRuntimeTests(unittest.TestCase):
    def test_cache_dir_linux_uses_xdg_cache_home(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            cache = cosyvoice_cache_dir(
                sys_platform="linux",
                env={"XDG_CACHE_HOME": tmp_str},
                home=Path(tmp_str) / "home",
            )

            self.assertEqual(cache, Path(tmp_str) / "videotranslatorai" / "cosyvoice")
            self.assertTrue(cache.exists())

    def test_cache_dir_windows_uses_localappdata(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            cache = cosyvoice_cache_dir(
                sys_platform="win32",
                env={"LOCALAPPDATA": tmp_str},
                home=Path(tmp_str) / "home",
            )

            self.assertEqual(cache, Path(tmp_str) / "VideoTranslatorAI" / "cosyvoice")

    def test_is_installed_handles_find_spec_errors(self):
        self.assertTrue(cosyvoice_is_installed(find_spec=lambda _name: object()))

        def raises(_name):
            raise ModuleNotFoundError("x")

        self.assertFalse(cosyvoice_is_installed(find_spec=raises))

    def test_model_present_uses_llm_marker(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            cache = Path(tmp_str)
            self.assertFalse(cosyvoice_model_present(cache))
            model_dir = cache / "CosyVoice-300M-Instruct"
            model_dir.mkdir()
            (model_dir / "llm.pt").write_bytes(b"x")
            self.assertTrue(cosyvoice_model_present(cache))

    def test_install_fails_fast_on_python_312_plus(self):
        logs = []

        ok, msg = cosyvoice_install(
            version_info=(3, 13),
            log_cb=logs.append,
            popen=mock.Mock(side_effect=AssertionError("should not spawn")),
        )

        self.assertFalse(ok)
        self.assertIn("Python 3.13", msg)
        self.assertTrue(logs)

    def test_install_success_registers_and_unregisters_process(self):
        proc = mock.Mock()
        proc.stdout = iter(["ok\n"])
        proc.returncode = 0
        timer = mock.Mock()
        registered = []
        unregistered = []

        ok, msg = cosyvoice_install(
            version_info=(3, 11),
            log_cb=lambda _s: None,
            popen=mock.Mock(return_value=proc),
            timer_factory=mock.Mock(return_value=timer),
            register_subprocess=registered.append,
            unregister_subprocess=unregistered.append,
            python_executable="/python",
        )

        self.assertTrue(ok)
        self.assertEqual(msg, "")
        self.assertEqual(registered, [proc])
        self.assertEqual(unregistered, [proc])
        timer.start.assert_called_once()
        timer.cancel.assert_called_once()

    def test_install_reports_nonzero_exit(self):
        proc = mock.Mock()
        proc.stdout = iter([])
        proc.returncode = 1

        ok, msg = cosyvoice_install(
            version_info=(3, 11),
            popen=mock.Mock(return_value=proc),
            timer_factory=mock.Mock(return_value=mock.Mock()),
        )

        self.assertFalse(ok)
        self.assertIn("failed", msg)

    def test_download_model_is_idempotent_when_marker_exists(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            cache = Path(tmp_str)
            model = cache / "CosyVoice-300M-Instruct"
            model.mkdir()
            (model / "llm.pt").write_bytes(b"x")
            logs = []

            ok, msg = cosyvoice_download_model(cache, log_cb=logs.append)

            self.assertTrue(ok)
            self.assertEqual(msg, "")
            self.assertTrue(any("già presente" in item for item in logs))

    def test_download_model_falls_back_to_huggingface(self):
        calls = []

        def ms_fail(*_args, **_kwargs):
            raise RuntimeError("ms down")

        def hf_ok(*args, **kwargs):
            calls.append((args, kwargs))

        with tempfile.TemporaryDirectory() as tmp_str:
            ok, msg = cosyvoice_download_model(
                Path(tmp_str),
                modelscope_snapshot_download=ms_fail,
                hf_snapshot_download=hf_ok,
            )

        self.assertTrue(ok)
        self.assertEqual(msg, "")
        self.assertEqual(calls[0][1]["repo_id"], "model-scope/CosyVoice-300M-Instruct")

    def test_download_model_reports_both_failures(self):
        def fail(*_args, **_kwargs):
            raise RuntimeError("down")

        with tempfile.TemporaryDirectory() as tmp_str:
            ok, msg = cosyvoice_download_model(
                Path(tmp_str),
                modelscope_snapshot_download=fail,
                hf_snapshot_download=fail,
            )

        self.assertFalse(ok)
        self.assertIn("HuggingFace", msg)


if __name__ == "__main__":
    unittest.main()
