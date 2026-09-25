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
from videotranslator.player_engine import InMemoryBackend
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
        self.assertEqual(self.panel.placeholder.winfo_manager(), "")
        self.panel._layout_video()
        self.assertEqual(self.panel.placeholder.winfo_manager(), "")
        self.panel.render(self._state(status="idle", item=None, duration=None), position=None)
        self.assertTrue(self.panel.placeholder_visible)
        self.assertEqual(self.panel.placeholder.winfo_manager(), "place")
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
    @staticmethod
    def _attach_backend(app):
        backend = InMemoryBackend(mixer=app._player_mixer)
        app._player_backend = backend
        app._player_controller.attach_backend(backend)
        return backend

    def test_selecting_an_input_previews_it_paused_and_builds_the_playlist(self):
        with built_app({"ui_lang": "en", "player_volume": 73}) as (_gui, app, _):
            backend = self._attach_backend(app)
            app._batch_files[:] = ["/tmp/first.mp4", "/tmp/second.mkv"]
            for path in app._batch_files:
                app._batch_listbox.insert("end", Path(path).name)
            app._batch_listbox.selection_set(1)
            app._on_input_select()
            self.assertEqual([item.path for item in app._player_controller.playlist],
                             app._batch_files)
            self.assertEqual(app._player_controller.state.item.path, "/tmp/second.mkv")
            self.assertIn(("load", "/tmp/second.mkv", True, 0.0, {}), backend.calls)
            self.assertEqual(app._player_controller.state.volume, 73)

    def test_selecting_while_unavailable_keeps_the_install_explanation(self):
        with built_app({"ui_lang": "en"}) as (_gui, app, _):
            app._on_player_status(MISSING, PlayerInstallRequest(manual_command=CMD))
            app._batch_files.append("/tmp/first.mp4")
            app._batch_listbox.insert("end", "first.mp4")
            app._batch_listbox.selection_set(0)
            app._on_input_select()
            self.assertIn(CMD, app._player_panel.message_label.cget("text"))
            self.assertIsNone(app._player_backend)

    def test_remove_and_clear_release_loaded_source_before_mutating_the_list(self):
        with built_app({"ui_lang": "en"}) as (_gui, app, _):
            backend = self._attach_backend(app)
            app._batch_files[:] = ["/tmp/one.mp4", "/tmp/two.mp4"]
            for path in app._batch_files:
                app._batch_listbox.insert("end", Path(path).name)
            app._batch_listbox.selection_set(0)
            app._on_input_select()
            app._remove_file()
            self.assertEqual(app._batch_files, ["/tmp/two.mp4"])
            self.assertIn(("stop",), backend.calls)
            self.assertIsNone(app._player_controller.state.item)
            app._clear_files()
            self.assertEqual(app._player_controller.playlist, ())

    def test_keyboard_filter_protects_form_controls_but_accepts_player_focus(self):
        with built_app({"ui_lang": "en"}) as (_gui, app, _):
            backend = self._attach_backend(app)
            app._player_controller.load(MediaItem("/tmp/a.mp4", "source", "a.mp4"))
            app._url_text.focus_force()
            app.update()
            self.assertIsNone(app._on_player_key(SimpleNamespace(
                keysym="space", widget=app._url_text)))
            app._btn.focus_force()
            app.update()
            self.assertIsNone(app._on_player_key(SimpleNamespace(
                keysym="space", widget=app._btn)))
            app._player_panel.volume_scale.focus_force()
            app.update()
            self.assertEqual(app._on_player_key(SimpleNamespace(
                keysym="space", widget=app._player_panel.volume_scale)), "break")
            self.assertIn(("set_pause", False), backend.calls)

    def test_fullscreen_hides_and_restores_every_non_player_region(self):
        with built_app({"ui_lang": "en", "ui_log_visible": True}) as (_gui, app, _):
            app._toggle_player_fullscreen(True)
            self.assertTrue(app._player_fullscreen)
            for widget in (app._header_frame, app._right_column, app._log_frame,
                           app._progress):
                self.assertEqual(widget.winfo_manager(), "")
            self.assertEqual(int(app._player_area.cget("highlightthickness")), 0)
            app._toggle_player_fullscreen(False)
            self.assertFalse(app._player_fullscreen)
            for widget in (app._header_frame, app._right_column, app._log_frame,
                           app._progress):
                self.assertEqual(widget.winfo_manager(), "grid")
            self.assertEqual(int(app._player_area.cget("highlightthickness")), 1)

    def test_a_dubbed_result_is_released_before_a_job_dispatches(self):
        with built_app({"ui_lang": "en"}) as (_gui, app, _):
            backend = self._attach_backend(app)
            item = MediaItem("/tmp/result.mp4", "dubbed", "result.mp4")
            app._player_controller.load(item, paused=True)
            app._player_bridge.set_latest("idle-active", True, time.monotonic())
            dispatched = []
            app._release_player_then(lambda: dispatched.append(True))
            self.assertEqual(dispatched, [True])
            self.assertIn(("stop",), backend.calls)

    def test_video_output_failure_recreates_backend_with_the_next_profile(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            old = self._attach_backend(app)
            app._player_status = READY
            app._player_vo_profile = "x11egl"
            app._player_guard = SimpleNamespace(captured=True, restore=mock.Mock())
            item = MediaItem("/tmp/a.mp4", "source", "a.mp4")
            app._player_controller.load(item, paused=True, start=3.0)
            replacement = InMemoryBackend(mixer=app._player_mixer)

            class ImmediateThread:
                def __init__(self, target):
                    self.target = target

                def start(self):
                    self.target()

                def is_alive(self):
                    return False

            with mock.patch.object(
                    app, "_redirecting_thread_factory",
                    side_effect=lambda target, **_kw: ImmediateThread(target)), \
                    mock.patch.object(gui._libmpv_runtime, "load_mpv", return_value=object()), \
                    mock.patch.object(gui._player_engine, "create_video_backend",
                                      return_value=replacement):
                app._begin_player_vo_fallback()
                app.update()
            self.assertTrue(old.terminated)
            self.assertIs(app._player_backend, replacement)
            self.assertEqual(app._player_vo_profile, "x11sw")
            self.assertIn(("load", item.path, True, 3.0, {}), replacement.calls)

    def test_a_new_load_does_not_reuse_stale_video_params(self):
        with built_app({"ui_lang": "en"}) as (_gui, app, _):
            self._attach_backend(app)
            app._player_bridge.set_latest("video-params", {"w": 640}, time.monotonic())
            app._player_bridge.drain()
            app._player_controller.load(
                MediaItem("/tmp/new.mp4", "source", "new.mp4"), paused=True)
            app._player_tick()
            self.assertFalse(app._player_video_params_seen)

    def test_close_terminates_the_backend_before_destroying_the_tk_host(self):
        with built_app({"ui_lang": "en"}) as (_gui, app, _):
            backend = self._attach_backend(app)
            destroyed_after_terminate = []
            original_destroy = app.destroy

            def destroy():
                destroyed_after_terminate.append(backend.terminated)

            app.destroy = destroy
            app._on_close()
            deadline = time.monotonic() + 1.0
            while not destroyed_after_terminate and time.monotonic() < deadline:
                app.update()
            self.assertEqual(destroyed_after_terminate, [True])
            self.assertIn(("terminate", 3.0), backend.calls)
            app.destroy = original_destroy

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
               "ui_lang": "en", "player_vo_profile": "x11sw",
               "player_probe": {"fingerprint": "x", "status": {}}}
        with built_app(cfg) as (gui, app, _):
            app._reset_ui_settings()
            saved = gui.load_config()
            self.assertNotIn("player_probe", saved)
            self.assertNotIn("player_vo_profile", saved)
            self.assertEqual(saved.get("ui_lang"), "en")
            self.assertEqual(saved.get("ui_theme"), "graphite")


if __name__ == "__main__":
    unittest.main()
