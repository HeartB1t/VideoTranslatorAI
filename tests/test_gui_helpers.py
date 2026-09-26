import unittest

import video_translator_gui as gui


class NoisyX11LogTests(unittest.TestCase):
    def test_matches_the_x11_badwindow_block(self):
        for line in (
            "X11 error: BadWindow (invalid Window parameter)",
            "Type: 0, display: 0x1f18ba00, resourceid: 4e4307d, serial: 1a484e",
            "Error code: 3, request code: f, minor code: 0",
        ):
            self.assertTrue(gui._is_noisy_x11_log(line), line)

    def test_keeps_normal_mpv_lines(self):
        for line in (
            "Using hardware decoding (nvdec).",
            "VO: [gpu] 1280x720 yuv420p",
            "File tags: title=...",
            "",
        ):
            self.assertFalse(gui._is_noisy_x11_log(line), line)


if __name__ == "__main__":
    unittest.main()
