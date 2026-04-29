import subprocess
import unittest

from videotranslator.media import (
    build_extract_audio_cmd,
    build_resample_vocals_cmd,
    demucs_apply_kwargs,
    extract_audio,
    run_ffmpeg,
)


class MediaTests(unittest.TestCase):
    def test_build_extract_audio_cmd_matches_pipeline_contract(self):
        cmd = build_extract_audio_cmd("input.mp4", "audio.wav")

        self.assertEqual(cmd[:4], ["ffmpeg", "-y", "-i", "input.mp4"])
        self.assertIn("pcm_s16le", cmd)
        self.assertEqual(cmd[-1], "audio.wav")

    def test_run_ffmpeg_returns_completed_process_on_success(self):
        completed = subprocess.CompletedProcess(["ffmpeg"], 0, stderr="")

        result = run_ffmpeg(["ffmpeg"], run=lambda *_args, **_kwargs: completed)

        self.assertIs(result, completed)

    def test_run_ffmpeg_raises_concise_tail_on_failure(self):
        stderr = "\n".join(f"line {i}" for i in range(12))
        completed = subprocess.CompletedProcess(["ffmpeg"], 1, stderr=stderr)

        with self.assertRaises(RuntimeError) as ctx:
            run_ffmpeg(["ffmpeg"], step="mux", run=lambda *_args, **_kwargs: completed)

        message = str(ctx.exception)
        self.assertIn("mux failed (exit 1)", message)
        self.assertNotIn("line 0", message)
        self.assertIn("line 11", message)

    def test_extract_audio_logs_and_uses_runner(self):
        calls = []
        logs = []

        def runner(cmd, step):
            calls.append((cmd, step))

        extract_audio("video.mp4", "audio.wav", log_cb=logs.append, runner=runner)

        self.assertEqual(calls[0][1], "extract_audio")
        self.assertEqual(calls[0][0], build_extract_audio_cmd("video.mp4", "audio.wav"))
        self.assertEqual(logs[0], "[1/6] Extracting audio from: video.mp4")
        self.assertEqual(logs[-1], "     -> audio.wav")

    def test_build_resample_vocals_cmd_matches_pipeline_contract(self):
        cmd = build_resample_vocals_cmd("vocals_raw.wav", "vocals_16k.wav")

        self.assertEqual(cmd[:4], ["ffmpeg", "-y", "-i", "vocals_raw.wav"])
        self.assertIn("16000", cmd)
        self.assertIn("1", cmd)
        self.assertEqual(cmd[-1], "vocals_16k.wav")

    def test_demucs_apply_kwargs_adds_chunking_when_supported(self):
        def apply_model(_model, _waveform, *, device, segment=None, overlap=None):
            return device, segment, overlap

        kwargs = demucs_apply_kwargs(apply_model, "cuda")

        self.assertEqual(kwargs["device"], "cuda")
        self.assertEqual(kwargs["segment"], 7.0)
        self.assertEqual(kwargs["overlap"], 0.25)

    def test_demucs_apply_kwargs_stays_minimal_for_old_signature(self):
        def apply_model(_model, _waveform, *, device):
            return device

        self.assertEqual(demucs_apply_kwargs(apply_model, "cpu"), {"device": "cpu"})


if __name__ == "__main__":
    unittest.main()
