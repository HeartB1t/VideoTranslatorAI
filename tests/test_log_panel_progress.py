"""The Log panel keeps one line per progress bar and rewrites it.

Needs a display (Xvfb in CI-like runs): the panel logic is exercised on a
real ``tk.Text`` through App's own methods, bound to a stand-in that carries
just the attributes they use.
"""

import tkinter as tk
import unittest

import video_translator_gui as gui

BAR = "Loading weights: {pct:3d}%|{fill:<10}| {pct}/100 [00:00<00:01, 90.0it/s]"
LEVEL_WORDS = {"log_level_info": "INFO", "log_level_warn": "WARNING",
               "log_level_error": "ERROR"}


def bar(pct: int, label: str = "Loading weights") -> str:
    return BAR.format(pct=pct, fill="#" * (pct // 10)).replace("Loading weights", label)


class _Panel:
    """App's log methods on a plain object with a real Text widget."""

    _LOG_MAX_LINES = 5000
    _log_write = gui.App._log_write
    _log_insert = gui.App._log_insert
    _log_prefix = gui.App._log_prefix
    _log_words = gui.App._log_words
    _log_emit = gui.App._log_emit
    _log_clear = gui.App._log_clear

    def __init__(self, root):
        self._log = tk.Text(root)
        self._log_bol = True
        self._log_level_now = "info"
        self._log_progress_key = None
        self._log_pending_cr = False
        self._destroying = False
        self._log_file = None

    def _s(self, key):
        return LEVEL_WORDS[key]

    def lines(self) -> list[str]:
        text = self._log.get("1.0", "end-1c")
        return [line for line in text.split("\n") if line != ""] if text else []


class LogPanelProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"no display: {exc}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.panel = _Panel(self.root)

    def test_updates_of_one_activity_rewrite_a_single_line(self):
        for pct in range(0, 101, 5):
            self.panel._log_write(bar(pct) + "\n")
        lines = self.panel.lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].endswith(bar(100)), lines[0])
        self.assertRegex(lines[0], r"^\d{2}:\d{2}:\d{2} INFO    \[app\] Loading weights")
        self.panel._log_write("[+] done\n")
        self.assertEqual([line.split("] ", 1)[1] for line in self.panel.lines()],
                         [bar(100), "done"])

    def test_updates_arriving_in_one_buffer_or_split_behave_the_same(self):
        self.panel._log_write("".join(bar(pct) + "\n" for pct in range(0, 50, 10)))
        self.panel._log_write(bar(50) + "\n" + bar(60))
        self.panel._log_write("\n" + bar(70) + "\n")
        lines = self.panel.lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].endswith(bar(70)))

    def test_carriage_return_rewrites_the_current_line_like_a_terminal(self):
        self.panel._log_write("     1/10...\r     2/10...\r     3/10...\n")
        self.assertEqual(self.panel.lines(), ["     3/10..."])   # continuation: no prefix
        self.panel._log_write("step one\rstep two\n")
        lines = self.panel.lines()
        self.assertEqual(len(lines), 2, lines)
        self.assertRegex(lines[1], r"^\d{2}:\d{2}:\d{2} INFO    \[app\] step two$")

    def test_a_split_crlf_does_not_erase_the_line(self):
        self.panel._log_write("hello\r")
        self.panel._log_write("\nnext\n")
        self.assertEqual([line.split("] ", 1)[1] for line in self.panel.lines()],
                         ["hello", "next"])
        self.panel._log_write("again\r")
        self.panel._log_write("rewritten\n")
        self.assertEqual([line.split("] ", 1)[1] for line in self.panel.lines()],
                         ["hello", "next", "rewritten"])

    def test_an_event_between_two_updates_is_kept(self):
        self.panel._log_write(bar(10) + "\n")
        self.panel._log_emit("Clicked: Start", "ui")
        self.panel._log_write(bar(20) + "\n")
        self.assertEqual([line.split("] ", 1)[1] for line in self.panel.lines()],
                         [bar(10), "Clicked: Start", bar(20)])

    def test_different_activities_keep_their_own_lines(self):
        self.panel._log_write(bar(10, "a.bin") + "\n")
        self.panel._log_write(bar(10, "b.bin") + "\n")
        self.panel._log_write(bar(50, "a.bin") + "\n")
        self.panel._log_write(bar(90, "a.bin") + "\n")
        self.assertEqual([line.split("] ", 1)[1] for line in self.panel.lines()],
                         [bar(10, "a.bin"), bar(10, "b.bin"), bar(90, "a.bin")])

    def test_a_cleared_panel_never_loses_an_ordinary_line(self):
        self.panel._log_write(bar(10) + "\n")
        self.panel._log_clear()
        self.panel._log_write("[+] fresh start\n")
        self.panel._log_progress_key = "Loading weights|100"    # stale state, on purpose
        self.panel._log_write(bar(20) + "\n")
        self.assertEqual([line.split("] ", 1)[1] for line in self.panel.lines()],
                         ["fresh start", bar(20)])


if __name__ == "__main__":
    unittest.main()
