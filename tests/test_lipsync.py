import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.lipsync import (
    apply_lipsync,
    build_wav2lip_command,
    build_wav2lip_env,
)


class LipsyncHelperTests(unittest.TestCase):
    def test_build_wav2lip_command(self):
        cmd = build_wav2lip_command(
            "in.mp4",
            "dub.wav",
            "out.mp4",
            inference_py=Path("/repo/inference.py"),
            checkpoint_path=Path("/model.pth"),
            python_executable="/python",
        )

        self.assertEqual(cmd[0], "/python")
        self.assertIn("--checkpoint_path", cmd)
        self.assertIn("/model.pth", cmd)
        self.assertIn("--nosmooth", cmd)

    def test_build_wav2lip_env_routes_temp_to_work_dir(self):
        env = build_wav2lip_env(
            Path("/repo"),
            Path("/work"),
            {"PYTHONPATH": "/existing", "OTHER": "1"},
        )

        self.assertEqual(env["TMPDIR"], "/work")
        self.assertEqual(env["TEMP"], "/work")
        self.assertEqual(env["TMP"], "/work")
        self.assertEqual(env["PYTHONPATH"], "/repo" + os.pathsep + "/existing")
        self.assertEqual(env["OTHER"], "1")


class ApplyLipsyncTests(unittest.TestCase):
    def test_apply_lipsync_runs_in_work_dir_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            repo = tmp / "repo"
            work = tmp / "work"
            model = tmp / "model.pth"
            repo.mkdir()
            work.mkdir()
            (work / "temp").mkdir()
            (repo / "inference.py").write_text("# stub", encoding="utf-8")
            model.write_bytes(b"model")

            proc = mock.Mock()
            proc.stdout = iter(["ok\n"])
            proc.returncode = 0

            def wait_side_effect():
                (tmp / "video_lipsync.mp4").write_bytes(b"out")

            proc.wait.side_effect = wait_side_effect
            timer = mock.Mock()
            registered = []
            unregistered = []

            result = apply_lipsync(
                "input.mp4",
                "dub.wav",
                str(tmp),
                wav2lip_repo=repo,
                wav2lip_model=model,
                wav2lip_work_dir=work,
                ensure_assets=lambda: None,
                register_subprocess=registered.append,
                unregister_subprocess=unregistered.append,
                popen=mock.Mock(return_value=proc),
                timer_factory=mock.Mock(return_value=timer),
                device_selector=lambda: "cpu",
                log=lambda *args, **kwargs: None,
            )

        self.assertEqual(result, str(tmp / "video_lipsync.mp4"))
        self.assertEqual(registered, [proc])
        self.assertEqual(unregistered, [proc])
        self.assertFalse((work / "temp").exists())
        timer.start.assert_called_once()
        timer.cancel.assert_called_once()

    def test_apply_lipsync_raises_with_process_tail(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            repo = tmp / "repo"
            work = tmp / "work"
            model = tmp / "model.pth"
            repo.mkdir()
            work.mkdir()
            (repo / "inference.py").write_text("# stub", encoding="utf-8")
            model.write_bytes(b"model")

            proc = mock.Mock()
            proc.stdout = iter(["line1\n", "line2\n"])
            proc.returncode = 2

            with self.assertRaisesRegex(RuntimeError, "line2"):
                apply_lipsync(
                    "input.mp4",
                    "dub.wav",
                    str(tmp),
                    wav2lip_repo=repo,
                    wav2lip_model=model,
                    wav2lip_work_dir=work,
                    ensure_assets=lambda: None,
                    popen=mock.Mock(return_value=proc),
                    timer_factory=mock.Mock(),
                    device_selector=lambda: "cpu",
                    log=lambda *args, **kwargs: None,
                )


if __name__ == "__main__":
    unittest.main()
