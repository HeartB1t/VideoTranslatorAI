"""PlayerPanel placeholder, HoverTip and the GUI player wiring (spec 2.3, 3.1, 6.1).

Tk tests: they skip without a display (CI) and run locally under Xvfb.
"""

import tkinter as tk
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from test_ui_theme_tk import HAS_DISPLAY, built_app
from videotranslator.libmpv_runtime import LibmpvStatus
from videotranslator.player_core import MediaItem, PlayerState
from videotranslator.system_packages import InstallResult, PlayerInstallRequest
from videotranslator.ui_theme import resolve_palette
from videotranslator.ui_strings_player import PLAYER_UI_STRINGS

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "assets" / "icon_256.png"
CMD = "sudo apt install libmpv2"
MISSING = LibmpvStatus(ok=False, reason="libmpv-missing", detail="no libmpv.so in ldconfig -p")
TOO_OLD = LibmpvStatus(ok=False, reason="libmpv-too-old", api_version=(1, 109), mpv_version=(0, 32))
READY = LibmpvStatus(ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
                     path="/usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0",
                     vo_profiles_ok=("x11egl", "x11sw"), detail="mpv 0.41.0, client API 2.5",
                     fingerprint="/usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0|10|20")


def _make_button(parent, **kwargs):
    kwargs.pop("primary", None)
    wrap = tk.Frame(parent)
    button = tk.Button(wrap, **kwargs)
    button.pack()
    return wrap, button


def _en(key):
    return PLAYER_UI_STRINGS["en"][key]


class _Theme:
    def __init__(self, name="graphite", scale=1.0):
        self.palette = resolve_palette(name, "default")
        self.scale = scale


class IconShapesTests(unittest.TestCase):
    def test_every_file_player_icon_is_nonempty_and_scales(self):
        from videotranslator.player_panel_tk import icon_shapes

        names = {
            "previous", "back", "stop", "play", "pause", "forward", "next",
            "snapshot", "open_folder", "volume", "muted", "fullscreen",
            "exit_fullscreen",
        }
        for name in names:
            with self.subTest(name=name):
                small = icon_shapes(name, 16)
                large = icon_shapes(name, 32)
                self.assertTrue(small)
                self.assertEqual([kind for kind, _ in small], [kind for kind, _ in large])
                self.assertGreater(max(large[0][1]), max(small[0][1]))
        with self.assertRaises(ValueError):
            icon_shapes("unknown", 16)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class PlayerPanelTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.lang = "en"
        self.commands = []
        self.theme = _Theme()
        self.panel = self._panel(LOGO, "linux")

    def tearDown(self):
        self.root.destroy()

    def _panel(self, logo, platform):
        from videotranslator.player_panel_tk import PlayerPanel

        panel = PlayerPanel(self.root, ui_s=lambda key: PLAYER_UI_STRINGS[self.lang][key],
                            make_button=_make_button,
                            on_command=lambda name, args: self.commands.append((name, args)),
                            logo_path=logo, sys_platform=platform, theme=self.theme)
        panel.pack(fill="both", expand=True)
        self.root.update_idletasks()
        return panel

    def test_before_any_status_only_the_logo_shows(self):
        self.assertEqual(self.panel.title_label.cget("text"), "")
        self.assertEqual(self.panel.message_label.cget("text"), "")
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")
        self.assertEqual(self.panel.status_text(), _en("player_badge"))

    def test_a_missing_library_shows_reason_command_and_install(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.assertEqual(self.panel.title_label.cget("text"), _en("player_unavailable_title"))
        self.assertEqual(self.panel.message_label.cget("text"),
                         _en("player_missing_libmpv_linux").format(cmd=CMD))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "pack")
        self.assertEqual(self.panel.install_button.cget("text"), _en("player_install_btn"))

    def test_too_old_has_no_install_button(self):
        self.panel.show_unavailable(TOO_OLD, install_cmd=None)
        self.assertEqual(self.panel.message_label.cget("text"),
                         _en("player_libmpv_too_old").format(version="0.32"))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")

    def test_ready_shows_the_version_and_the_system_credits(self):
        self.panel.show_ready(READY)
        self.assertEqual(self.panel.title_label.cget("text"), "")
        self.assertEqual(self.panel.message_label.cget("text"),
                         _en("player_badge_ok").format(version="0.41") + "\n"
                         + _en("player_credits").format(license=_en("player_license_system")))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")

    def test_windows_texts(self):
        panel = self._panel(LOGO, "win32")
        panel.show_ready(LibmpvStatus(ok=True, reason="ok", mpv_version=(0, 41),
                                      build={"licence": "LGPL"}))
        self.assertTrue(panel.status_text().endswith(_en("player_credits").format(license="LGPL")))
        panel.show_unavailable(LibmpvStatus(ok=False, reason="libmpv-missing"), install_cmd=None)
        self.assertEqual(panel.message_label.cget("text"), _en("player_missing_libmpv_win"))
        self.assertEqual(panel._install_wrap.winfo_manager(), "pack")

    def test_the_install_button_sends_the_install_command(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.panel.install_button.invoke()
        self.assertEqual(self.commands, [("install", {})])

    def test_install_progress_line_and_button(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.panel.show_install_progress("installing")
        self.assertEqual(self.panel.install_label.cget("text"), _en("player_installing"))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")
        self.panel.show_install_progress("failed")
        self.assertEqual(self.panel.install_label.cget("text"), _en("player_install_failed"))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "pack")
        self.assertIn(CMD, self.panel.message_label.cget("text"))  # the manual command stays
        self.panel.show_install_progress(None)
        self.assertEqual(self.panel.install_label.cget("text"), "")

    def test_relabel_follows_the_language(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.lang = "ja"
        self.panel.relabel()
        self.assertEqual(self.panel.title_label.cget("text"),
                         PLAYER_UI_STRINGS["ja"]["player_unavailable_title"])
        self.assertEqual(self.panel.install_button.cget("text"),
                         PLAYER_UI_STRINGS["ja"]["player_install_btn"])

    def test_logo_image_and_canvas_fallback(self):
        self.assertIsInstance(self.panel.logo, tk.Label)
        self.assertTrue(self.panel.logo.cget("image"))
        fallback = self._panel(ROOT / "assets" / "missing.png", "linux")
        self.assertIsInstance(fallback.logo, tk.Canvas)
        self.assertEqual(fallback.logo.itemcget(fallback.logo.find_all()[0], "fill"), "#c3c3c3")

    def test_only_reserved_colours(self):
        for widget in (self.panel, self.panel.video_host, self.panel.placeholder):
            self.assertEqual(widget.cget("bg"), "#000000")
        self.assertEqual(self.panel.message_label.cget("fg"), "#a3a3a3")

    def _state(self, **changes):
        values = dict(
            status="paused", item=MediaItem("/tmp/movie.mp4", "source", "movie.mp4"),
            position=12.0, duration=125.0, volume=72, muted=False, audio="dubbed",
            ab_available=False, subs_available=False, subs_visible=True,
        )
        values.update(changes)
        return PlayerState(**values)

    def test_render_updates_transport_time_title_volume_and_placeholder(self):
        self.panel.render(self._state(), position=13.0)
        self.assertEqual(self.panel.now_playing_label.cget("text"),
                         _en("player_now_playing").format(name="movie.mp4"))
        self.assertEqual(self.panel.elapsed_label.cget("text"), "00:13")
        self.assertEqual(self.panel.duration_label.cget("text"), "02:05")
        self.assertEqual(round(float(self.panel.volume_scale.get())), 72)
        self.assertFalse(self.panel.placeholder_visible)
        self.panel.render(self._state(status="idle", item=None, duration=None), position=None)
        self.assertTrue(self.panel.placeholder_visible)
        self.assertEqual(self.panel.message_label.cget("text"), _en("player_idle_hint"))

    def test_every_control_dispatches_and_reflow_hides_only_planned_icons(self):
        self.root.deiconify()
        self.root.geometry("800x600")
        self.root.update()
        self.panel.render(self._state(), position=12.0)
        self.panel._apply_reflow(700)
        self.root.update()
        for control in self.panel._icon_controls.values():
            control.event_generate("<Button-1>", x=5, y=5)
        self.panel.playlist_button.invoke()
        self.root.update()
        self.assertEqual([name for name, _args in self.commands], [
            "previous", "back_10", "stop", "play_pause", "forward_10", "next",
            "snapshot", "open_folder", "mute", "fullscreen", "playlist",
        ])
        self.panel._apply_reflow(700)
        self.assertTrue(all(widget.winfo_manager() for widget in self.panel._icon_controls.values()))
        self.panel._apply_reflow(430)
        self.assertEqual(self.panel._icon_controls["back"].winfo_manager(), "")
        self.assertEqual(self.panel._icon_controls["forward"].winfo_manager(), "")
        self.assertTrue(self.panel._icon_controls["snapshot"].winfo_manager())
        self.panel._apply_reflow(360)
        self.assertEqual(self.panel._icon_controls["snapshot"].winfo_manager(), "")
        self.assertEqual(self.panel._icon_controls["open_folder"].winfo_manager(), "")

    def test_seek_drag_is_throttled_and_render_does_not_fight_the_drag(self):
        self.panel.render(self._state(duration=100.0, position=10.0), position=10.0)
        before = tuple(self.panel.seek_canvas.coords("knob"))
        self.panel._dragging = True
        self.panel.render(self._state(duration=100.0, position=80.0), position=80.0)
        self.assertEqual(tuple(self.panel.seek_canvas.coords("knob")), before)
        self.panel._dragging = False
        self.panel._seek_press(SimpleNamespace(x=25))
        self.panel._last_drag_seek = time.monotonic()
        count = len(self.commands)
        self.panel._seek_motion(SimpleNamespace(x=75))
        self.assertEqual(len(self.commands), count)
        self.panel._seek_release(SimpleNamespace(x=75))
        self.assertEqual(self.commands[-1][0], "seek")
        self.assertFalse(self.commands[-1][1]["dragging"])

    def test_notify_relabel_theme_and_keyboard_focus_ring(self):
        self.panel.render(self._state(), position=12.0)
        normal = self.panel.now_playing_label.cget("text")
        self.panel.notify("player_snapshot_saved", {"path": "/tmp/a.png"}, seconds=0.01)
        self.assertIn("/tmp/a.png", self.panel.now_playing_label.cget("text"))
        self.root.after(30, self.root.quit)
        self.root.mainloop()
        self.assertEqual(self.panel.now_playing_label.cget("text"), normal)
        self.lang = "ja"
        self.panel.relabel()
        self.assertIn("movie.mp4", self.panel.now_playing_label.cget("text"))
        old_bg = self.panel.controls_frame.cget("bg")
        self.theme.palette = resolve_palette("light", "default")
        self.panel.apply_theme()
        self.assertNotEqual(self.panel.controls_frame.cget("bg"), old_bg)
        self.assertEqual(self.panel.video_host.cget("bg"), "#000000")
        control = self.panel._icon_controls["play_pause"]
        self.assertEqual(int(control.cget("takefocus")), 1)
        self.assertEqual(int(control.cget("highlightthickness")), 2)
        self.assertEqual(control.cget("highlightcolor"), self.theme.palette.ACC)
        self.root.deiconify()
        self.root.update()
        control.focus_force()
        before = len(self.commands)
        control.event_generate("<Return>")
        self.root.update()
        self.assertEqual(len(self.commands), before + 1)

    def test_builds_in_every_theme_and_scale(self):
        for name in ("graphite", "slate", "light", "neon"):
            for scale in (0.9, 1.0, 1.15, 1.3):
                with self.subTest(theme=name, scale=scale):
                    self.theme.palette = resolve_palette(name, "default")
                    self.theme.scale = scale
                    panel = self._panel(None, "linux")
                    panel.apply_theme()
                    panel._apply_reflow(460)
                    self.assertEqual(panel.video_host.cget("bg"), "#000000")
                    panel.destroy()

    def test_playlist_popup_groups_items_and_dispatches_selection(self):
        sources = [MediaItem("/tmp/a.mp4", "source", "a.mp4")]
        results = [MediaItem("/tmp/b.mp4", "dubbed", "b.mp4")]
        popup = self.panel.show_playlist(sources, results, job_running=False)
        self.assertIsInstance(popup, tk.Toplevel)
        self.assertEqual(self.panel._playlist_list.size(), 4)
        self.panel._playlist_list.selection_set(1)
        self.panel._choose_playlist_item()
        self.assertEqual(self.commands[-1], ("load_item", {"item": sources[0]}))

    def test_host_wid_and_fullscreen_state(self):
        self.assertIsInstance(self.panel.host_wid(), int)
        self.panel.set_fullscreen_layout(True)
        self.assertTrue(self.panel.fullscreen)
        self.panel.set_fullscreen_layout(False)
        self.assertFalse(self.panel.fullscreen)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class HoverTipTests(unittest.TestCase):
    def test_show_reads_text_and_colours_each_time_and_hide_destroys(self):
        from videotranslator.player_panel_tk import HoverTip

        root = tk.Tk()
        root.withdraw()
        try:
            label = tk.Label(root, text="x")
            label.pack()
            texts = iter(["first", "second"])
            tip = HoverTip(label, lambda: next(texts), colors_fn=lambda: ("#111111", "#eeeeee"))
            tip._show()
            shown = tip._tip.winfo_children()[0]
            self.assertEqual(shown.cget("text"), "first")
            self.assertEqual(shown.cget("bg"), "#111111")
            tip.hide()
            self.assertIsNone(tip._tip)
            tip._show()
            self.assertEqual(tip._tip.winfo_children()[0].cget("text"), "second")
            tip.hide()
        finally:
            root.destroy()


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class GuiPlayerWiringTests(unittest.TestCase):
    def test_badge_and_placeholder_follow_the_status(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            self.assertEqual(app._player_badge_label.cget("text"), gui.UI_STRINGS["en"]["player_badge"])
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.FG2)
            app._on_player_status(MISSING, PlayerInstallRequest(manual_command=CMD))
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.WARN)
            self.assertIn(CMD, app._player_panel.message_label.cget("text"))
            self.assertEqual(app._player_status_text(), app._player_panel.status_text())
            app._on_player_status(TOO_OLD, PlayerInstallRequest())
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.ERR)
            app._on_player_status(READY, PlayerInstallRequest())
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.OK)

    def test_a_probed_ready_status_is_cached_in_the_config(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            app._on_player_status(READY, PlayerInstallRequest())
            self.assertEqual(gui.load_config()["player_probe"]["fingerprint"], READY.fingerprint)

    def test_the_language_switch_relabels_badge_and_placeholder(self):
        with built_app({"ui_lang": "it"}) as (gui, app, _):
            app._on_player_status(MISSING, PlayerInstallRequest(manual_command=CMD))
            app._ui_lang.set("ja")
            app._apply_lang()
            self.assertEqual(app._player_badge_label.cget("text"), gui.UI_STRINGS["ja"]["player_badge"])
            self.assertEqual(app._player_panel.title_label.cget("text"),
                             gui.UI_STRINGS["ja"]["player_unavailable_title"])

    def test_a_second_install_is_refused_while_one_runs(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            app._installing = True
            with mock.patch.object(gui.messagebox, "showerror") as showerror:
                app._install_player()
            showerror.assert_called_once()
            self.assertEqual(showerror.call_args.args[1], gui.UI_STRINGS["en"]["live_err_busy_install"])

    def _run_install(self, app, result):
        request = PlayerInstallRequest(pip_packages=("mpv>=1.0.6,<2",),
                                       system_plans=((("pkexec", "apt-get", "update"),),),
                                       manual_command=CMD)
        app._on_player_status(MISSING, request)
        calls = []

        class FakeInstaller:
            saw_installing = None

            def install(self, **kwargs):
                calls.append(kwargs)
                self.saw_installing = app._installing
                kwargs["on_done"](result)

        fake = FakeInstaller()
        with mock.patch.object(app, "_player_installer", return_value=fake), \
                mock.patch.object(app, "_refresh_player_status") as refresh:
            app._install_player()
        return calls, fake, refresh

    def test_install_runs_the_request_then_reprobes(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            calls, fake, refresh = self._run_install(app, InstallResult(True, False, None))
            self.assertEqual(calls[0]["pip_packages"], ("mpv>=1.0.6,<2",))
            self.assertEqual(calls[0]["system_plans"], ((("pkexec", "apt-get", "update"),),))
            self.assertIsNone(calls[0]["windows_install"])
            self.assertEqual(calls[0]["expect_modules"], ("mpv",))
            self.assertTrue(fake.saw_installing)
            self.assertFalse(app._installing)
            refresh.assert_called_once_with(force_probe=True)
            self.assertEqual(app._player_panel.install_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_install_ok"])

    def test_an_install_that_needs_a_restart_says_so(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            _, _, refresh = self._run_install(app, InstallResult(True, True, None))
            refresh.assert_not_called()
            self.assertEqual(app._player_status.reason, "restart-required")
            self.assertEqual(app._player_panel.message_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_restart_required"])
            self.assertEqual(app._player_panel.install_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_install_ok"])
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.WARN)

    def test_a_failed_install_keeps_the_reason_and_the_manual_command(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            _, _, refresh = self._run_install(app, InstallResult(False, False, "system"))
            refresh.assert_not_called()
            self.assertIn(CMD, app._player_panel.message_label.cget("text"))
            self.assertEqual(app._player_panel.install_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_install_failed"])
            self.assertEqual(app._player_panel._install_wrap.winfo_manager(), "pack")
            self.assertFalse(app._installing)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class PlayerProbeResetTests(unittest.TestCase):
    """Spec 2.5: Settings Reset also forgets the cached libmpv probe."""

    def test_reset_removes_player_probe_and_keeps_other_keys(self):
        cfg = {"ui_theme": "light", "ui_accent": "default", "ui_scale": "normal",
               "ui_lang": "en", "player_probe": {"fingerprint": "x", "status": {}}}
        with built_app(cfg) as (gui, app, _):
            app._reset_ui_settings()
            saved = gui.load_config()
            self.assertNotIn("player_probe", saved)
            self.assertEqual(saved.get("ui_lang"), "en")
            self.assertEqual(saved.get("ui_theme"), "graphite")


if __name__ == "__main__":
    unittest.main()
