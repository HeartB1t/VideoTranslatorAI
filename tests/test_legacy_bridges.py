import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import video_translator_gui as legacy
from videotranslator import config, secrets, segments, timing


class LegacyTimingBridgeTests(unittest.TestCase):
    def test_timing_helpers_are_extracted_module_functions(self):
        self.assertIs(legacy._suggest_xtts_speed, timing.suggest_xtts_speed)
        self.assertIs(legacy._estimate_tts_duration_s, timing.estimate_tts_duration_s)
        self.assertIs(legacy._compute_segment_speed, timing.compute_segment_speed)


class LegacySegmentBridgeTests(unittest.TestCase):
    def test_segment_helpers_are_extracted_module_functions(self):
        self.assertIs(legacy._split_on_punctuation, segments.split_on_punctuation)
        self.assertIs(legacy._merge_short_segments, segments.merge_short_segments)


class LegacyConfigBridgeTests(unittest.TestCase):
    def test_config_wrappers_use_extracted_helpers_on_config_path(self):
        self.assertIs(legacy._load_json_config, config.load_json_config)
        self.assertIs(legacy._write_json_config, config.write_json_config)
        self.assertIs(legacy._merge_json_config, config.merge_json_config)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            with mock.patch.object(legacy, "CONFIG_PATH", path):
                self.assertEqual(legacy.load_config(), {})

                legacy._write_config_raw({"lang": "it", "model": "small"})
                self.assertEqual(
                    json.loads(path.read_text(encoding="utf-8")),
                    {"lang": "it", "model": "small"},
                )

                legacy.save_config({"model": "medium"})
                self.assertEqual(
                    legacy.load_config(),
                    {"lang": "it", "model": "medium"},
                )


class LegacySecretsBridgeTests(unittest.TestCase):
    def test_secret_helpers_are_extracted_module_functions(self):
        self.assertIs(legacy._import_keyring_backend, secrets.import_keyring_backend)
        self.assertIs(legacy._load_secret_token, secrets.load_secret_token)
        self.assertIs(legacy._save_secret_token, secrets.save_secret_token)


class LegacyWav2LipBridgeTests(unittest.TestCase):
    def test_wav2lip_assets_check_python_deps_when_assets_are_present(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            repo = tmp / "Wav2Lip"
            model = tmp / "wav2lip_gan.pth"
            work = tmp / "work"
            repo.mkdir()
            (repo / "inference.py").write_text("# stub", encoding="utf-8")
            model.write_bytes(b"model")

            with (
                mock.patch.object(legacy, "WAV2LIP_DIR", tmp),
                mock.patch.object(legacy, "WAV2LIP_REPO", repo),
                mock.patch.object(legacy, "WAV2LIP_MODEL", model),
                mock.patch.object(legacy, "WAV2LIP_WORK_DIR", work),
                mock.patch.object(legacy, "_ensure_wav2lip_python_deps") as ensure_deps,
            ):
                legacy._ensure_wav2lip_assets()

        ensure_deps.assert_called_once_with()

    def test_wav2lip_assets_raise_on_incomplete_existing_repo(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            repo = tmp / "Wav2Lip"
            model = tmp / "wav2lip_gan.pth"
            work = tmp / "work"
            repo.mkdir()

            with (
                mock.patch.object(legacy, "WAV2LIP_DIR", tmp),
                mock.patch.object(legacy, "WAV2LIP_REPO", repo),
                mock.patch.object(legacy, "WAV2LIP_MODEL", model),
                mock.patch.object(legacy, "WAV2LIP_WORK_DIR", work),
                mock.patch.object(legacy, "_ensure_wav2lip_python_deps") as ensure_deps,
            ):
                with self.assertRaisesRegex(RuntimeError, "missing inference.py"):
                    legacy._ensure_wav2lip_assets()

        ensure_deps.assert_not_called()

    def test_wav2lip_python_deps_install_face_stack_on_linux_when_missing(self):
        with (
            mock.patch.object(legacy, "_install_wav2lip_base_stack") as base_stack,
            mock.patch.object(
                legacy,
                "_missing_wav2lip_face_packages",
                return_value=["dlib", "facexlib"],
            ),
            mock.patch.object(legacy, "_install_wav2lip_face_stack_linux") as face_stack,
            mock.patch.object(legacy.sys, "platform", "linux"),
        ):
            legacy._ensure_wav2lip_python_deps()

        base_stack.assert_called_once_with()
        face_stack.assert_called_once_with()

    def test_wav2lip_python_deps_do_not_install_linux_face_stack_on_windows(self):
        with (
            mock.patch.object(legacy, "_install_wav2lip_base_stack") as base_stack,
            mock.patch.object(
                legacy,
                "_missing_wav2lip_face_packages",
                return_value=["dlib"],
            ),
            mock.patch.object(legacy, "_install_wav2lip_face_stack_linux") as face_stack,
            mock.patch.object(legacy.sys, "platform", "win32"),
        ):
            legacy._ensure_wav2lip_python_deps()

        base_stack.assert_called_once_with()
        face_stack.assert_not_called()

    def test_apply_lipsync_runs_subprocess_in_work_dir(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            repo = tmp / "assets" / "Wav2Lip"
            model = tmp / "assets" / "wav2lip_gan.pth"
            work = tmp / "work"
            repo.mkdir(parents=True)
            work.mkdir()
            (repo / "inference.py").write_text("# stub", encoding="utf-8")
            model.write_bytes(b"model")
            (work / "temp").mkdir()

            proc = mock.Mock()
            proc.stdout = iter(["ok\n"])
            proc.returncode = 0

            def wait_side_effect():
                (tmp / "video_lipsync.mp4").write_bytes(b"out")

            proc.wait.side_effect = wait_side_effect

            timer = mock.Mock()

            with (
                mock.patch.object(legacy, "WAV2LIP_REPO", repo),
                mock.patch.object(legacy, "WAV2LIP_MODEL", model),
                mock.patch.object(legacy, "WAV2LIP_WORK_DIR", work),
                mock.patch.object(legacy, "_ensure_wav2lip_assets"),
                mock.patch.object(legacy.subprocess, "Popen", return_value=proc) as popen,
                mock.patch.object(legacy.threading, "Timer", return_value=timer),
                mock.patch.object(legacy, "_register_subprocess"),
                mock.patch.object(legacy, "_unregister_subprocess"),
            ):
                result = legacy.apply_lipsync("input.mp4", "dub.wav", str(tmp))

        self.assertEqual(result, str(tmp / "video_lipsync.mp4"))
        self.assertEqual(popen.call_args.kwargs["cwd"], str(work))
        self.assertFalse((work / "temp").exists())


if __name__ == "__main__":
    unittest.main()
