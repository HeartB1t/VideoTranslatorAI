import os
import tempfile
import unittest
from subprocess import CompletedProcess

from videotranslator.output_media import (
    format_srt_timestamp,
    get_duration,
    mux_video,
    save_subtitles,
    segments_to_srt,
)


class OutputMediaTests(unittest.TestCase):
    def test_format_srt_timestamp(self):
        self.assertEqual(format_srt_timestamp(3661.234), "01:01:01,234")

    def test_format_srt_timestamp_rounds_with_rollover(self):
        self.assertEqual(format_srt_timestamp(1.9995), "00:00:02,000")

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

    def test_segments_to_srt_is_pure_and_keeps_export_semantics(self):
        content = segments_to_srt([
            {"start": 0.0, "end": 1.5, "text_tgt": " ciao ", "text": "hello"},
            {"start": 2.0, "end": 3.0, "text": "fallback"},
        ])
        self.assertEqual(content, (
            "1\n00:00:00,000 --> 00:00:01,500\nciao\n\n"
            "2\n00:00:02,000 --> 00:00:03,000\n\n\n"
        ))

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

    def test_mux_video_maps_named_dubbed_and_original_tracks(self):
        calls = []
        mux_video("in.mp4", "dub.wav", "out.mp4", original_audio_input="in.mp4",
                  run_ffmpeg=lambda cmd, **kw: calls.append((cmd, kw)),
                  log=lambda *_args, **_kwargs: None)
        cmd = calls[0][0]
        self.assertEqual(cmd.count("-i"), 2)
        self.assertIn("0:a:0?", cmd)
        self.assertIn("title=Dubbed", cmd)
        self.assertIn("title=Original", cmd)
        self.assertIn("handler_name=Dubbed", cmd)
        self.assertIn("handler_name=Original", cmd)
        self.assertIn("default", cmd)
        # Per-stream codecs and bitrates as prescribed by the design (3.4):
        # the dubbed track at 192k, the original at 160k.
        self.assertEqual(cmd[cmd.index("-b:a:0") + 1], "192k")
        self.assertEqual(cmd[cmd.index("-b:a:1") + 1], "160k")
        self.assertEqual(cmd[cmd.index("-c:a:0") + 1], "aac")
        self.assertEqual(cmd[cmd.index("-c:a:1") + 1], "aac")

    def test_mux_video_single_track_when_original_not_kept(self):
        calls = []
        mux_video("in.mp4", "dub.wav", "out.mp4", original_audio_input=None,
                  run_ffmpeg=lambda cmd, **kw: calls.append(cmd),
                  log=lambda *_args, **_kwargs: None)
        cmd = calls[0]
        self.assertEqual(cmd.count("-i"), 2)  # video + dubbed only, no source
        audio_maps = [cmd[i + 1] for i, item in enumerate(cmd[:-1])
                      if item == "-map" and ":a:" in cmd[i + 1]]
        self.assertEqual(audio_maps, ["1:a:0"])
        self.assertNotIn("title=Original", cmd)
        self.assertNotIn("handler_name=Original", cmd)

    def test_mux_video_separate_original_input_precedes_output_options(self):
        calls = []
        mux_video("video.mp4", "dub.wav", "out.mp4", original_audio_input="source.mkv",
                  run_ffmpeg=lambda cmd, **kw: calls.append(cmd),
                  log=lambda *_args, **_kwargs: None)
        cmd = calls[0]
        inputs = [cmd[i + 1] for i, item in enumerate(cmd[:-1]) if item == "-i"]
        self.assertEqual(inputs, ["video.mp4", "dub.wav", "source.mkv"])
        self.assertIn("2:a:0?", cmd)


if __name__ == "__main__":
    unittest.main()
