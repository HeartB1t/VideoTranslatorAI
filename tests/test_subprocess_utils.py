import unittest
from pathlib import Path

from videotranslator.subprocess_utils import (
    command_for_log,
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


if __name__ == "__main__":
    unittest.main()

