"""LiveBar widget (spec 2.3, 4.2, 5.9). Tk tests: skip without a display, run under Xvfb."""

import tkinter as tk
import unittest
from types import SimpleNamespace

from test_ui_theme_tk import HAS_DISPLAY
from videotranslator.ui_strings_player import PLAYER_UI_STRINGS
from videotranslator.ui_theme import resolve_palette


def _make_button(parent, **kwargs):
    kwargs.pop("primary", None)
    wrap = tk.Frame(parent)
    button = tk.Button(wrap, **kwargs)
    button.pack()
    return wrap, button


def _s(key):
    return PLAYER_UI_STRINGS["en"].get(key, key)


class _Theme:
    def __init__(self):
        self.palette = resolve_palette("graphite", "default")
        self.scale = 1.0


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class LiveBarTests(unittest.TestCase):
    def setUp(self):
        from videotranslator.live_bar_tk import LiveBar
        self.root = tk.Tk()
        self.root.withdraw()
        self.commands = []
        self.bar = LiveBar(
            self.root, ui_s=_s, make_button=_make_button,
            on_command=lambda intent, params: self.commands.append((intent, params)),
            theme=_Theme())

    def tearDown(self):
        self.root.destroy()

    def test_starts_in_idle_row(self):
        self.assertTrue(self.bar._idle.winfo_manager())
        self.assertFalse(self.bar._running.winfo_manager())

    def test_start_button_emits_source(self):
        self.bar._start_button.invoke()
        self.assertIn(("start", {"source": "file"}), self.commands)

    def test_mode_toggle_emits(self):
        self.bar._mode_buttons["live"].invoke()
        self.assertIn(("mode", {"mode": "live"}), self.commands)

    def test_engine_select_emits_and_warns_online(self):
        self.bar._engine_combo.current(2)  # google
        self.bar._on_engine()
        self.assertIn(("engine", {"engine": "google"}), self.commands)
        self.assertTrue(self.bar._banner.winfo_manager())  # online-engine warning

    def test_dub_and_subs_emit(self):
        self.bar._chk_dub.invoke()
        self.bar._chk_subs.invoke()
        intents = [c[0] for c in self.commands]
        self.assertIn("dub", intents)
        self.assertIn("subs", intents)

    def test_stop_button_emits(self):
        self.bar.show_running()
        self.bar._stop_button.invoke()
        self.assertIn(("stop", {}), self.commands)

    def test_config_values_reflect_selection(self):
        self.bar._mode_var.set("live")
        self.bar._dub_var.set(False)
        values = self.bar.config_values()
        self.assertEqual(values["sync_mode"], "live")
        self.assertFalse(values["dub_enabled"])

    def test_render_running_status(self):
        self.bar.show_running()
        status = SimpleNamespace(state="running", lag_s=None, warning_key=None,
                                 error_key=None)
        self.bar.render(status)
        self.assertEqual(self.bar._status_label.cget("text"),
                         _s("live_status_running"))

    def test_render_lag_formats_seconds(self):
        self.bar.show_running()
        status = SimpleNamespace(state="lag", lag_s=3.0, warning_key=None, error_key=None)
        self.bar.render(status)
        self.assertIn("3", self.bar._status_label.cget("text"))

    def test_render_warning_shows_banner_with_switch(self):
        self.bar.show_running()
        status = SimpleNamespace(
            state="running", lag_s=None, error_key=None,
            warning_key="rate_limited", warning_params={"engine": "Google", "s": 30},
            warning_action="live_btn_switch_marian")
        self.bar.render(status)
        self.assertTrue(self.bar._banner.winfo_manager())
        self.assertTrue(self.bar._switch_wrap.winfo_manager())
        self.assertIn("Google", self.bar._banner_label.cget("text"))

    def test_recovered_warning_clears_the_banner_on_render(self):
        self.bar.show_running()
        warned = SimpleNamespace(
            state="running", lag_s=None, error_key=None,
            warning_key="rate_limited", warning_params={"engine": "Google"},
            warning_action=None)
        self.bar.render(warned)
        self.assertTrue(self.bar._banner.winfo_manager())
        recovered = SimpleNamespace(state="running", lag_s=None,
                                    warning_key=None, error_key=None)
        self.bar.render(recovered)
        self.assertFalse(self.bar._banner.winfo_manager())

    def test_error_banner_is_not_auto_cleared(self):
        self.bar.show_running()
        self.bar.render(SimpleNamespace(state="failed", lag_s=None, warning_key=None,
                                        error_key="ingest", error_params={}))
        self.bar.render(SimpleNamespace(state="running", lag_s=None,
                                        warning_key=None, error_key=None))
        self.assertTrue(self.bar._banner.winfo_manager())   # errors stay up

    def test_render_error_shows_error_banner(self):
        self.bar.show_running()
        status = SimpleNamespace(state="failed", lag_s=None, warning_key=None,
                                 error_key="ingest", error_params={})
        self.bar.render(status)
        self.assertTrue(self.bar._banner.winfo_manager())
        self.assertTrue(self.bar._banner_is_error)

    def test_banner_close_clears_and_emits(self):
        self.bar.show_banner("live_warn_cpu_fallback", {})
        self.assertTrue(self.bar._banner.winfo_manager())
        self.bar._banner_close.invoke()
        self.assertFalse(self.bar._banner.winfo_manager())
        self.assertIn(("banner_close", {}), self.commands)

    def test_url_source_shows_live_badge_on_render(self):
        self.bar.set_source_kind("url")
        self.bar.show_running()
        self.bar.render(SimpleNamespace(state="running", lag_s=None, warning_key=None,
                                        error_key=None))
        self.assertTrue(self.bar._badge.winfo_manager())

    def test_relabel_and_theme_do_not_crash(self):
        self.bar.relabel()
        self.bar.apply_theme()
        self.assertEqual(self.bar._start_button.cget("text"), _s("player_btn_live"))


if __name__ == "__main__":
    unittest.main()
