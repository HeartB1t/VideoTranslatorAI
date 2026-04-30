import os
import tempfile
import unittest
from subprocess import CompletedProcess

from videotranslator.output_media import (
    format_srt_timestamp,
    get_duration,
    mux_video,
    save_subtitles,
)


class OutputMediaTests(unittest.TestCase):
    def test_format_srt_timestamp(self):
        self.assertEqual(format_srt_timestamp(3661.234), "01:01:01,233")

    def test_save_subtitles_writes_srt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_base = os.path.join(tmp_dir, "out")
            path = save_subtitles(
                [{"start": 0.0, "end": 1.5, "text_tgt": "ciao"}],
                output_base,
                log=lambda *_args, **_kwargs: None,
            )

            self.assertEqual(path, output_base + ".srt")
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("00:00:00,000 --> 00:00:01,500", content)
            self.assertIn("ciao", content)

    def test_get_duration_parses_ffprobe_json(self):
        def fake_run(*_args, **_kwargs):
            return CompletedProcess([], 0, stdout='{"format": {"duration": "12.5"}}', stderr="")

        self.assertEqual(get_duration("video.mp4", run=fake_run), 12.5)

    def test_get_duration_raises_on_ffprobe_failure(self):
        def fake_run(*_args, **_kwargs):
            return CompletedProcess([], 1, stdout="", stderr="bad file")

        with self.assertRaisesRegex(RuntimeError, "ffprobe failed"):
            get_duration("video.mp4", run=fake_run)

    def test_mux_video_builds_expected_command(self):
        calls = []

        def fake_run_ffmpeg(cmd, **kwargs):
            calls.append((cmd, kwargs))

        mux_video(
            "in.mp4",
            "audio.wav",
            "out.mp4",
            run_ffmpeg=fake_run_ffmpeg,
            log=lambda *_args, **_kwargs: None,
        )

        cmd, kwargs = calls[0]
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("in.mp4", cmd)
        self.assertIn("audio.wav", cmd)
        self.assertEqual(cmd[-1], "out.mp4")
        self.assertEqual(kwargs["step"], "mux_video")


if __name__ == "__main__":
    unittest.main()
