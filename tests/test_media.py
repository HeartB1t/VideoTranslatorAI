import subprocess
import sys
import types
import unittest
from unittest import mock

from videotranslator.media import (
    build_extract_audio_cmd,
    build_resample_vocals_cmd,
    demucs_apply_kwargs,
    extract_audio,
    run_ffmpeg,
    separate_instrumental,
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


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


class SeparateInstrumentalTests(unittest.TestCase):
    """Task 3: full-quality instrumental via Demucs, with Demucs mocked so no
    real model is loaded (CI has no torch/demucs)."""

    def test_separate_instrumental_saves_full_quality_background(self):
        class FakeTensor:
            def __init__(self, shape=(2, 1000)):
                self.shape = shape

            def repeat(self, *_a):
                return FakeTensor((2, self.shape[1]))

            def to(self, _device):
                return self

            def unsqueeze(self, _dim):
                return self

            def __getitem__(self, _idx):
                return self

            def sum(self, _dim):
                return self

            def cpu(self):
                return self

        saved: list[tuple] = []

        fake_torch = types.SimpleNamespace(
            cuda=types.SimpleNamespace(
                is_available=lambda: False,
                empty_cache=lambda: saved.append(("empty_cache",)),
            ),
            no_grad=lambda: _NullCtx(),
        )
        fake_torchaudio = types.SimpleNamespace(
            load=lambda _p: (FakeTensor((2, 1000)), 48000),
            save=lambda path, tensor, sr: saved.append((path, tensor, sr)),
        )
        fake_pretrained = types.SimpleNamespace(
            get_model=lambda _name: types.SimpleNamespace(to=lambda _d: None)
        )
        fake_apply = types.SimpleNamespace(apply_model=lambda *a, **k: FakeTensor())
        fake_demucs = types.ModuleType("demucs")
        fake_demucs.pretrained = fake_pretrained
        fake_demucs.apply = fake_apply

        modules = {
            "torch": fake_torch,
            "torchaudio": fake_torchaudio,
            "demucs": fake_demucs,
            "demucs.pretrained": fake_pretrained,
            "demucs.apply": fake_apply,
        }
        logs: list[str] = []
        with mock.patch.dict(sys.modules, modules):
            result = separate_instrumental(
                "song.wav", "/tmp/instr.wav", log_cb=logs.append)

        self.assertEqual(result, "/tmp/instr.wav")
        self.assertEqual(len(saved), 1)
        saved_path, _tensor, saved_sr = saved[0]
        self.assertEqual(saved_path, "/tmp/instr.wav")
        self.assertEqual(saved_sr, 48000)  # original sample rate, not resampled
        self.assertTrue(any("Demucs" in line or "nstrumental" in line
                            for line in logs))


if __name__ == "__main__":
    unittest.main()
