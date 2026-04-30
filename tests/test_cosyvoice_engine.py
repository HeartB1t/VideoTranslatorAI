import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.cosyvoice_engine import generate_tts_cosyvoice


class FakeCuda:
    def is_available(self):
        return False

    def empty_cache(self):
        pass

    def manual_seed_all(self, _seed):
        pass


class FakeTensor:
    def unsqueeze(self, _dim):
        return self


class FakeTorch:
    cuda = FakeCuda()

    def manual_seed(self, _seed):
        pass

    def from_numpy(self, _arr):
        return FakeTensor()


class FakeTorchaudio:
    saved = []

    def save(self, out_path, _speech_tensor, _sample_rate):
        self.__class__.saved.append(out_path)
        Path(out_path).write_bytes(b"wav")


class FakeLibrosa:
    def load(self, _path, sr=16000, mono=True):
        return [0.0, 0.1], sr


class FakeCosy:
    calls = []

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs

    def inference_cross_lingual(self, text, _prompt_speech, stream=False, speed=1.0):
        self.__class__.calls.append(("cross", text, stream, speed))
        yield {"tts_speech": object()}

    def inference_zero_shot(self, text, _prompt_text, _prompt_speech, stream=False, speed=1.0):
        self.__class__.calls.append(("zero", text, stream, speed))
        yield {"tts_speech": object()}


class CosyVoiceEngineTests(unittest.TestCase):
    def setUp(self):
        FakeCosy.calls = []
        FakeTorchaudio.saved = []

    def test_not_installed_returns_none(self):
        result = generate_tts_cosyvoice(
            [{"text_tgt": "ciao"}],
            "ref.wav",
            "it",
            "/tmp",
            installed_check=lambda: False,
            torch_module=FakeTorch(),
            log=lambda *args, **kwargs: None,
        )

        self.assertIsNone(result)

    def test_generate_cosyvoice_with_fake_runtime(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            ref = Path(tmp_str) / "ref.wav"
            ref.write_bytes(b"ref")
            cache = Path(tmp_str) / "cache"
            cache.mkdir()

            with mock.patch("videotranslator.cosyvoice_engine.build_vad_reference_tiered", return_value=str(ref)):
                files = generate_tts_cosyvoice(
                    [{"start": 0.0, "end": 3.0, "text_tgt": "Ciao!"}],
                    str(ref),
                    "it",
                    tmp_str,
                    speed=1.25,
                    torch_module=FakeTorch(),
                    torchaudio_module=FakeTorchaudio(),
                    librosa_module=FakeLibrosa(),
                    cosy_cls=FakeCosy,
                    installed_check=lambda: True,
                    cache_dir_func=lambda: cache,
                    model_present=lambda _cache: True,
                    log=lambda *args, **kwargs: None,
                )

        self.assertEqual(len(files), 1)
        self.assertEqual(Path(files[0]).name, "seg_0000.wav")
        self.assertEqual(FakeCosy.calls[0][0], "cross")
        self.assertEqual(FakeCosy.calls[0][1], "<|it|>Ciao")
        self.assertEqual(FakeTorchaudio.saved, [files[0]])


if __name__ == "__main__":
    unittest.main()
