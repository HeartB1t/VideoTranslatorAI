import types
import unittest

from videotranslator.transcription import (
    build_transcribe_kwargs,
    is_cuda_runtime_error,
    normalize_whisper_segments,
    transcribe_audio,
    whisper_device_and_compute,
)


class FakeCuda:
    def __init__(self, available: bool):
        self.available = available
        self.empty_cache_calls = 0

    def is_available(self):
        return self.available

    def empty_cache(self):
        self.empty_cache_calls += 1


class FakeTorch:
    def __init__(self, cuda_available: bool):
        self.cuda = FakeCuda(cuda_available)


class TranscriptionHelperTests(unittest.TestCase):
    def test_whisper_device_and_compute_cuda(self):
        self.assertEqual(whisper_device_and_compute(FakeTorch(True)), ("cuda", "float16"))

    def test_whisper_device_and_compute_cpu(self):
        self.assertEqual(whisper_device_and_compute(FakeTorch(False)), ("cpu", "int8"))

    def test_build_transcribe_kwargs_auto_language_and_hotwords(self):
        kwargs = build_transcribe_kwargs("auto", ["Strix", "Docker"])

        self.assertIsNone(kwargs["language"])
        self.assertEqual(kwargs["beam_size"], 5)
        self.assertTrue(kwargs["vad_filter"])
        self.assertEqual(kwargs["hotwords"], "Strix Docker")

    def test_build_transcribe_kwargs_explicit_language(self):
        self.assertEqual(build_transcribe_kwargs("it")["language"], "it")

    def test_normalize_whisper_segments_drops_empty_and_adjacent_dupes(self):
        raw = [
            types.SimpleNamespace(start=0.0, end=1.0, text=" Hello "),
            types.SimpleNamespace(start=1.0, end=2.0, text="Hello"),
            types.SimpleNamespace(start=2.0, end=3.0, text=""),
            types.SimpleNamespace(start=3.0, end=4.0, text="World"),
        ]

        self.assertEqual(
            normalize_whisper_segments(raw),
            [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
                {"start": 3.0, "end": 4.0, "text": "World"},
            ],
        )

    def test_is_cuda_runtime_error(self):
        self.assertTrue(is_cuda_runtime_error(RuntimeError("libcublas failed")))
        self.assertTrue(is_cuda_runtime_error(RuntimeError("CUDA out of memory")))
        self.assertFalse(is_cuda_runtime_error(RuntimeError("file not found")))


class TranscribeAudioTests(unittest.TestCase):
    def test_transcribe_audio_uses_model_and_returns_detected_language(self):
        calls = []

        class FakeModel:
            def __init__(self, model_name, device, compute_type):
                calls.append(("init", model_name, device, compute_type))

            def transcribe(self, audio_path, **kwargs):
                calls.append(("transcribe", audio_path, kwargs))
                return (
                    [types.SimpleNamespace(start=0.0, end=1.0, text=" hello ")],
                    types.SimpleNamespace(language="en"),
                )

        result, detected = transcribe_audio(
            "audio.wav",
            "small",
            "auto",
            ["Strix"],
            whisper_model_cls=FakeModel,
            torch_module=FakeTorch(False),
        )

        self.assertEqual(detected, "en")
        self.assertEqual(result, [{"start": 0.0, "end": 1.0, "text": "hello"}])
        self.assertEqual(calls[0], ("init", "small", "cpu", "int8"))
        self.assertEqual(calls[1][2]["hotwords"], "Strix")

    def test_transcribe_audio_falls_back_to_cpu_when_cuda_init_fails(self):
        devices = []

        class FakeModel:
            def __init__(self, _model_name, device, compute_type):
                self.compute_type = compute_type
                devices.append(device)
                if device == "cuda":
                    raise RuntimeError("CUDA unavailable")

            def transcribe(self, _audio_path, **_kwargs):
                return ([], types.SimpleNamespace(language=None))

        result, detected = transcribe_audio(
            "audio.wav",
            "small",
            "it",
            whisper_model_cls=FakeModel,
            torch_module=FakeTorch(True),
        )

        self.assertEqual(devices, ["cuda", "cpu"])
        self.assertEqual(result, [])
        self.assertEqual(detected, "it")

    def test_transcribe_audio_retries_cpu_when_cuda_inference_fails(self):
        devices = []

        class FakeModel:
            def __init__(self, _model_name, device, compute_type):
                self.device = device
                self.compute_type = compute_type
                devices.append(device)

            def transcribe(self, _audio_path, **_kwargs):
                if self.device == "cuda":
                    raise RuntimeError("CUDA out of memory")
                return (
                    [types.SimpleNamespace(start=0.0, end=1.0, text="ok")],
                    types.SimpleNamespace(language="en"),
                )

        result, detected = transcribe_audio(
            "audio.wav",
            "small",
            "auto",
            whisper_model_cls=FakeModel,
            torch_module=FakeTorch(True),
        )

        self.assertEqual(devices, ["cuda", "cpu"])
        self.assertEqual(result[0]["text"], "ok")
        self.assertEqual(detected, "en")


if __name__ == "__main__":
    unittest.main()
