import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.xtts_engine import generate_tts_xtts


class FakeCuda:
    def is_available(self):
        return False

    def empty_cache(self):
        pass

    def manual_seed_all(self, _seed):
        pass


class FakeTorch:
    cuda = FakeCuda()

    def manual_seed(self, _seed):
        pass


class FakeTTSModel:
    calls = []

    def to(self, device):
        self.device = device
        return self

    def tts_to_file(self, **kwargs):
        self.__class__.calls.append(kwargs)
        Path(kwargs["file_path"]).write_bytes(b"wav")


def fake_tts_factory(_model_name):
    return FakeTTSModel()


class XttsEngineTests(unittest.TestCase):
    def setUp(self):
        FakeTTSModel.calls = []

    def test_unsupported_language_returns_none_without_loading_model(self):
        result = generate_tts_xtts(
            [{"text_tgt": "ciao"}],
            "ref.wav",
            "xx",
            "/tmp",
            tts_factory=mock.Mock(side_effect=AssertionError("should not load")),
            torch_module=FakeTorch(),
            log=lambda *args, **kwargs: None,
        )

        self.assertIsNone(result)

    def test_generate_tts_xtts_uses_fake_model_and_sanitizes_text(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            ref = Path(tmp_str) / "ref.wav"
            ref.write_bytes(b"ref")

            with mock.patch("videotranslator.xtts_engine.build_vad_reference_tiered", return_value=str(ref)):
                files = generate_tts_xtts(
                    [{"start": 0.0, "end": 3.0, "text_tgt": "Ciao: mondo!"}],
                    str(ref),
                    "it",
                    tmp_str,
                    speed=1.35,
                    tts_factory=fake_tts_factory,
                    torch_module=FakeTorch(),
                    log=lambda *args, **kwargs: None,
                )

        self.assertEqual(len(files), 1)
        self.assertEqual(Path(files[0]).name, "seg_0000.wav")
        self.assertEqual(FakeTTSModel.calls[0]["language"], "it")
        self.assertEqual(FakeTTSModel.calls[0]["text"], "Ciao, mondo")
        self.assertLessEqual(FakeTTSModel.calls[0]["speed"], 1.35)


if __name__ == "__main__":
    unittest.main()
