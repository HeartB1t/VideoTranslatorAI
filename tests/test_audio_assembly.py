import csv
import os
import tempfile
import unittest

import numpy as np
import soundfile as sf

from videotranslator.audio_assembly import build_dubbed_track


class AudioAssemblyTests(unittest.TestCase):
    def test_build_dubbed_track_writes_stereo_track_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            sr = 44100
            t = np.linspace(0.0, 0.10, int(sr * 0.10), endpoint=False)
            mono = (0.2 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
            stereo = np.column_stack([mono, mono])
            tts_path = os.path.join(tmp_dir, "seg_0000.wav")
            sf.write(tts_path, stereo, sr)
            metrics_path = os.path.join(tmp_dir, "metrics.csv")

            out = build_dubbed_track(
                [{"start": 0.0, "end": 0.20, "text_src": "hello", "text_tgt": "ciao"}],
                [tts_path],
                bg_path=None,
                total_duration=0.25,
                tmp_dir=tmp_dir,
                metrics_csv_path=metrics_path,
                rubberband_available=False,
                log=lambda *_args, **_kwargs: None,
            )

            self.assertTrue(os.path.exists(out))
            data, rate = sf.read(out, dtype="float32", always_2d=True)
            self.assertEqual(rate, sr)
            self.assertEqual(data.shape[1], 2)
            self.assertEqual(data.shape[0], int(sr * 0.25))
            self.assertTrue(os.path.exists(metrics_path))

            with open(metrics_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["stretch_engine"], "none")


if __name__ == "__main__":
    unittest.main()
