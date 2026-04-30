import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from videotranslator.tts_audio import (
    build_atempo_chain,
    concat_wavs,
    find_split_point,
    measure_wav_duration_s,
    probe_duration_ms,
    strip_xtts_terminal_punct,
)


class AtempoChainTests(unittest.TestCase):
    def test_invalid_ratio_returns_identity(self):
        self.assertEqual(build_atempo_chain(0), "atempo=1.0")
        self.assertEqual(build_atempo_chain(float("nan")), "atempo=1.0")

    def test_ratio_inside_single_filter_range(self):
        self.assertEqual(build_atempo_chain(1.25), "atempo=1.250")

    def test_high_ratio_is_split(self):
        self.assertEqual(build_atempo_chain(3.0), "atempo=2.0,atempo=1.500")

    def test_ratio_is_clamped_to_cap(self):
        self.assertEqual(build_atempo_chain(10.0, max_ratio=4.0), "atempo=2.0,atempo=2.000")


class TextUtilityTests(unittest.TestCase):
    def test_strip_terminal_punctuation(self):
        self.assertEqual(strip_xtts_terminal_punct("Ciao?!."), "Ciao")
        self.assertEqual(strip_xtts_terminal_punct("Mr. Smith parla."), "Mr. Smith parla")

    def test_find_split_point_prefers_punctuation_near_middle(self):
        text = "prima parte, seconda parte lunga"
        self.assertEqual(find_split_point(text), text.index(",") + 2)

    def test_find_split_point_uses_space_then_midpoint(self):
        self.assertEqual(find_split_point("abcdef ghijkl"), 7)
        self.assertEqual(find_split_point("abcdefghij"), 5)


class DurationProbeTests(unittest.TestCase):
    def test_probe_duration_uses_soundfile_info_first(self):
        info = SimpleNamespace(frames=22050, samplerate=44100)

        self.assertEqual(probe_duration_ms("x.wav", sf_info=lambda _p: info), 500)

    def test_probe_duration_falls_back_to_ffprobe(self):
        completed = subprocess.CompletedProcess(["ffprobe"], 0, stdout="1.250\n")

        self.assertEqual(
            probe_duration_ms(
                "x.mp3",
                sf_info=lambda _p: (_ for _ in ()).throw(RuntimeError("sf failed")),
                run=lambda *_args, **_kwargs: completed,
            ),
            1250,
        )

    def test_probe_duration_returns_zero_when_all_methods_fail(self):
        logs: list[str] = []

        self.assertEqual(
            probe_duration_ms(
                "x.mp3",
                sf_info=lambda _p: (_ for _ in ()).throw(RuntimeError("sf failed")),
                run=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("ffprobe failed")),
                log_cb=logs.append,
            ),
            0,
        )
        self.assertTrue(any("ffprobe duration fallback failed" in item for item in logs))

    def test_measure_wav_duration_returns_seconds(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            path = Path(tmp_str) / "tone.wav"
            import numpy as np
            import soundfile as sf

            sf.write(path, np.zeros(4410, dtype="float32"), 44100)
            self.assertAlmostEqual(measure_wav_duration_s(str(path)), 0.1, places=2)


class ConcatWavsTests(unittest.TestCase):
    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            concat_wavs([], "out.wav")

    def test_concat_wavs_writes_output(self):
        import numpy as np
        import soundfile as sf

        with tempfile.TemporaryDirectory() as tmp_str:
            a = Path(tmp_str) / "a.wav"
            b = Path(tmp_str) / "b.wav"
            out = Path(tmp_str) / "out.wav"
            sf.write(a, np.ones(4410, dtype="float32") * 0.1, 44100)
            sf.write(b, np.ones(4410, dtype="float32") * 0.2, 44100)

            concat_wavs([str(a), str(b)], str(out))

            self.assertTrue(out.exists())
            data, sr = sf.read(out)
            self.assertEqual(sr, 44100)
            self.assertGreater(len(data), 4410)


if __name__ == "__main__":
    unittest.main()
