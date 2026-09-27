"""'Models for this PC' window. Tk tests: skip without a display, run under Xvfb."""

import gc
import tkinter as tk
import unittest
from unittest import mock

from test_ui_theme_tk import HAS_DISPLAY
from videotranslator import models_dialog_tk as md
from videotranslator.hardware_profile import GpuInfo, HardwareInfo
from videotranslator.model_catalog import MT, WHISPER
from videotranslator.ui_strings_models import MODELS_UI_STRINGS
from videotranslator.ui_theme import resolve_palette


def _s(key):
    return MODELS_UI_STRINGS["en"].get(key, key)


def _hw(vram=24.0):
    gpus = (GpuInfo("RTX 3090", vram, "cuda"),) if vram else ()
    return HardwareInfo("Linux", "i7", 16, 32.0, gpus, bool(vram), 200.0)


class TextTests(unittest.TestCase):
    def test_hardware_lines_for_gpu_cpu_and_unusable_gpu(self):
        self.assertIn("GPU: RTX 3090, 24.0 GB VRAM", md.hardware_lines(_hw(), _s))
        self.assertIn(_s("mdl_hw_no_gpu"), md.hardware_lines(_hw(None), _s))
        rocm = HardwareInfo("Linux", "x", 8, 16.0, (GpuInfo("Radeon", 16.0, "rocm"),),
                            False, 50.0)
        self.assertIn(_s("mdl_hw_gpu_unusable").format(gpu="Radeon"),
                      md.hardware_lines(rocm, _s))

    def test_option_text_shows_fit_and_download_state(self):
        text = md.option_text(WHISPER["large-v3"], _hw(), set(), _s)
        self.assertIn("Whisper large-v3", text)
        self.assertIn("fits", text)
        self.assertIn("to download: 3090 MB", text)
        self.assertIn("downloaded", md.option_text(WHISPER["small"], _hw(), {"small"}, _s))
        self.assertIn("online service", md.option_text(MT["google"], _hw(), set(), _s))
        self.assertIn("Ollama", md.option_text(MT["qwen3:14b"], _hw(), set(), _s))

    def test_reason_text_formats_params(self):
        self.assertEqual(md.reason_text((("rec_reason_fits", {"model": "X", "need": "2.0"}),),
                                        _s), "X needs about 2.0 GB")


class _Theme:
    def __init__(self):
        self.palette = resolve_palette("graphite", "default")


def _make_button(parent, **kwargs):
    kwargs.pop("primary", None)
    wrap = tk.Frame(parent)
    button = tk.Button(wrap, **kwargs)
    button.pack()
    return wrap, button


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class DialogTests(unittest.TestCase):
    def setUp(self):
        # Collect Tk variables here, on the main thread: collected later inside a
        # worker thread of another test, Variable.__del__ calls Tk without a
        # running main loop and blocks that thread.
        self.addCleanup(gc.collect)
        self.root = tk.Tk()
        self.root.withdraw()
        self.applied = []
        self.logged = []
        self.asked = []
        self.picked = ""
        self.busy = False
        self.media = None
        self.previous = {"asr": "small", "asr_live": "small", "mt": "google", "tts": "edge"}

    def tearDown(self):
        self.root.destroy()

    def _dialog(self, current=None, hw=None):
        dlg = md.ModelsDialog(
            self.root, ui_s=_s, theme=_Theme(), make_button=_make_button,
            current=current or {"asr": "medium", "asr_live": "small", "mt": "marian",
                                "tts": "edge"},
            on_apply=self.applied.append, on_revert=lambda: self.previous,
            media_path=lambda: self.media, busy=lambda: self.busy,
            detect=lambda: hw or _hw(), cached=lambda: {"small", "medium"},
            log=self.logged.append,
            ask_media=lambda parent, title: (self.asked.append(title), self.picked)[1])
        self.addCleanup(dlg.close)
        for _ in range(100):
            self.root.update()
            if dlg._hw is not None:
                break
            self.root.after(10)
        self.assertIsNotNone(dlg._hw)
        return dlg

    def test_shows_current_settings_then_recommendations_on_priority_change(self):
        dlg = self._dialog()
        self.assertEqual(dlg.choices(), {"asr": "medium", "asr_live": "small",
                                         "mt": "marian", "tts": "edge"})
        dlg._pref_var.set("quality")
        dlg._select_recommended()
        self.assertEqual(dlg.choices(), {"asr": "large-v3", "asr_live": "large-v3-turbo",
                                         "mt": "qwen3:14b", "tts": "xtts"})
        self.assertIn("Recommended", dlg._reason_labels["asr"].cget("text"))

    def test_apply_hands_the_choices_over_and_revert_restores(self):
        dlg = self._dialog()
        dlg._apply()
        self.assertEqual(self.applied, [dlg.choices()])
        dlg._revert()
        self.assertEqual(dlg.choices(), self.previous)
        self.assertEqual(dlg._status.cget("text"), _s("mdl_reverted"))

    def test_busy_blocks_apply_and_benchmark(self):
        dlg = self._dialog()
        self.busy = True
        dlg._set_buttons()
        self.assertEqual(str(dlg._buttons["apply"].cget("state")), "disabled")
        dlg._apply()
        self.assertEqual(self.applied, [])
        self.assertEqual(dlg._status.cget("text"), _s("mdl_busy"))

    def test_messages_hardware_and_choices_reach_the_app_log(self):
        dlg = self._dialog()
        self.assertTrue(any(line.startswith("CPU") or "CPU" in line for line in self.logged))
        dlg._apply()
        self.assertTrue(self.logged[-1].startswith(_s("mdl_applied")))
        self.assertIn("asr=", self.logged[-1])
        count = len(self.logged)
        dlg._set_status("same")
        dlg._set_status("same")                       # a repeated result is logged again
        dlg._set_status("progress 1", progress=True)
        dlg._set_status("progress 2", progress=True)  # progress within 5 s: not logged
        self.assertEqual(self.logged[count:], ["same", "same", "progress 1"])

    def test_busy_is_explained_and_apply_greys_out_until_it_ends(self):
        dlg = self._dialog()
        pal = dlg._pal
        self.assertEqual(dlg._buttons["apply"].cget("bg"), pal.ACC)
        self.busy = True
        dlg._poll()                                  # noticed without any click
        self.assertEqual(dlg._status.cget("text"), _s("mdl_busy"))
        self.assertEqual(dlg._buttons["apply"].cget("bg"), pal.BTN)
        self.assertEqual(dlg._buttons["apply"].cget("disabledforeground"), pal.FG2)
        self.busy = False
        dlg._poll()
        self.assertEqual(dlg._status.cget("text"), "")
        self.assertEqual(str(dlg._buttons["apply"].cget("state")), "normal")
        self.assertEqual(dlg._buttons["apply"].cget("bg"), pal.ACC)

    def test_download_enabled_only_for_missing_whisper_models(self):
        dlg = self._dialog()
        self.assertEqual(str(dlg._buttons["download"].cget("state")), "disabled")
        dlg._set_choice("asr", "large-v3")
        dlg._set_buttons()
        self.assertEqual(dlg._missing_whisper(), ["large-v3"])
        self.assertEqual(str(dlg._buttons["download"].cget("state")), "normal")

    def test_download_progress_and_completion(self):
        dlg = self._dialog()
        dlg._set_choice("asr", "large-v3")
        fake = mock.Mock(key="large-v3", expected_mb=3090, state="running", error="")
        fake.progress_mb.return_value = 100.0
        with mock.patch.object(md, "WhisperDownload", return_value=fake):
            dlg._start_download()
        fake.start.assert_called_once_with()
        dlg._poll_download()
        self.assertIn("100 of 3090 MB", dlg._status.cget("text"))
        fake.state = "done"
        dlg._poll_download()
        self.assertIn("large-v3", dlg._cached)
        self.assertEqual(dlg.choices()["asr"], "large-v3")      # selection kept
        self.assertEqual(dlg._missing_whisper(), [])

    def test_benchmark_without_media_asks_for_a_file(self):
        dlg = self._dialog()
        dlg._start_benchmark()
        self.assertEqual(self.asked, [_s("mdl_bench_pick")])
        self.assertEqual(dlg._status.cget("text"), _s("mdl_bench_no_file"))
        dlg._start_benchmark()                        # a new click logs its result again
        self.assertEqual(self.logged[-2:], [_s("mdl_bench_no_file")] * 2)
        self.picked = "/clips/speech.mp4"
        seen = []
        with mock.patch.object(md, "benchmark_whisper",
                               side_effect=lambda key, media, **kw: seen.append(media)), \
                mock.patch.object(md.threading, "Thread",
                                  side_effect=lambda target, **kw: mock.Mock(
                                      start=target)):
            dlg._start_benchmark()
        self.assertEqual(seen, ["/clips/speech.mp4"])

    def test_benchmark_is_explained_in_the_window(self):
        dlg = self._dialog()
        texts = [w.cget("text") for w in dlg.win.winfo_children()[0].winfo_children()
                 if isinstance(w, tk.Label)]
        self.assertIn(_s("mdl_bench_hint"), texts)

    def test_benchmark_result_is_shown(self):
        from videotranslator.model_manager import BenchmarkResult
        dlg = self._dialog()
        dlg._handle("bench", BenchmarkResult("small", "cuda", 30.0, 1.2, 0.4, 0.6))
        self.assertIn("50.0x real time", dlg._status.cget("text"))

    def test_close_cancels_work(self):
        dlg = self._dialog()
        fake = mock.Mock()
        dlg._download = fake
        dlg.close()
        fake.cancel.assert_called_once_with()
        self.assertTrue(dlg.closed)


if __name__ == "__main__":
    unittest.main()
