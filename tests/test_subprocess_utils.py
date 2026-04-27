import subprocess
import unittest
from pathlib import Path

from videotranslator.subprocess_utils import (
    command_for_log,
    common_subprocess_kwargs,
    normalize_command,
    text_subprocess_kwargs,
)


class SubprocessUtilsTests(unittest.TestCase):
    def test_normalize_command_rejects_shell_string(self):
        with self.assertRaises(TypeError):
            normalize_command("ffmpeg -version")  # type: ignore[arg-type]

    def test_normalize_command_stringifies_paths(self):
        self.assertEqual(
            normalize_command(["ffmpeg", "-i", Path("input video.mp4")]),
            ["ffmpeg", "-i", "input video.mp4"],
        )

    def test_normalize_command_rejects_empty_command(self):
        with self.assertRaises(ValueError):
            normalize_command([])

    def test_command_for_log_quotes_spaces(self):
        self.assertEqual(
            command_for_log(["ffmpeg", "-i", "input video.mp4"]),
            "ffmpeg -i 'input video.mp4'",
        )

    def test_windows_text_kwargs_are_utf8(self):
        kwargs = text_subprocess_kwargs("win32")

        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")
        self.assertTrue(kwargs["text"])

    def test_linux_text_kwargs_include_encoding_and_replace_errors(self):
        kwargs = text_subprocess_kwargs("linux")

        self.assertIn("encoding", kwargs)
        self.assertEqual(kwargs["errors"], "replace")
        self.assertTrue(kwargs["text"])

    def test_common_subprocess_kwargs_default_to_text_only(self):
        kwargs = common_subprocess_kwargs("win32")

        self.assertEqual(
            kwargs,
            {"text": True, "encoding": "utf-8", "errors": "replace"},
        )

    def test_common_subprocess_kwargs_add_requested_streams(self):
        kwargs = common_subprocess_kwargs(
            "win32",
            stdin_devnull=True,
            stdout_pipe=True,
            stderr_pipe=True,
        )

        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.PIPE)
        self.assertIs(kwargs["stderr"], subprocess.PIPE)
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertTrue(kwargs["text"])

    def test_common_subprocess_kwargs_streams_are_independent(self):
        kwargs = common_subprocess_kwargs("win32", stdout_pipe=True)

        self.assertIs(kwargs["stdout"], subprocess.PIPE)
        self.assertNotIn("stdin", kwargs)
        self.assertNotIn("stderr", kwargs)


if __name__ == "__main__":
    unittest.main()
