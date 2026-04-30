import os
import tempfile
import unittest

import numpy as np
import soundfile as sf

from videotranslator.audio_mix import apply_tail_fade, overlay_pcm, read_segment_to_pcm


class AudioMixTests(unittest.TestCase):
    def test_overlay_pcm_adds_with_bounds(self):
        mix = np.zeros((5, 2), dtype=np.int32)
        pcm = np.ones((4, 2), dtype=np.int16) * 10

        overlay_pcm(mix, pcm, start_frame=3, total_frames=5)

        self.assertTrue(np.array_equal(mix[:3], np.zeros((3, 2), dtype=np.int32)))
        self.assertTrue(np.array_equal(mix[3:], np.ones((2, 2), dtype=np.int32) * 10))

    def test_apply_tail_fade_changes_tail_only(self):
        pcm = np.ones((8, 2), dtype=np.int16) * 1000

        out = apply_tail_fade(pcm.copy(), 2)

        self.assertTrue(np.array_equal(out[:6], np.ones((6, 2), dtype=np.int16) * 1000))
        self.assertLess(out[-1, 0], out[-2, 0])

    def test_read_segment_to_pcm_fast_path(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            path = os.path.join(tmp_str, "seg.wav")
            sf.write(path, np.zeros((100, 2), dtype=np.int16), 44100)

            pcm = read_segment_to_pcm(path, tmp_dir=tmp_str)

            self.assertIsNotNone(pcm)
            self.assertEqual(pcm.shape, (100, 2))

    def test_read_segment_to_pcm_converts_when_format_differs(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            path = os.path.join(tmp_str, "seg.wav")
            converted = os.path.join(tmp_str, "seg_pcm.wav")
            sf.write(path, np.zeros((100,), dtype=np.int16), 22050)

            def fake_run_ffmpeg(_cmd, **_kwargs):
                sf.write(converted, np.zeros((50, 2), dtype=np.int16), 44100)

            pcm = read_segment_to_pcm(path, tmp_dir=tmp_str, run_ffmpeg=fake_run_ffmpeg)

            self.assertIsNotNone(pcm)
            self.assertEqual(pcm.shape, (50, 2))

    def test_read_segment_to_pcm_returns_none_for_missing_file(self):
        self.assertIsNone(read_segment_to_pcm("/missing/file.wav", tmp_dir="/tmp"))


if __name__ == "__main__":
    unittest.main()
