import contextlib
import gc
import threading
import time
import tkinter as tk
import re
import sys
import unittest
import weakref
from tkinter import font as tkfont, ttk
from unittest import mock

from videotranslator.ui_theme import resolve_palette

try:
    _probe = tk.Tk()
    _probe.destroy()
    HAS_DISPLAY = True
except tk.TclError:
    HAS_DISPLAY = False


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class ThemeManagerTkTests(unittest.TestCase):
    def setUp(self):
        from videotranslator import ui_theme_tk
        self.mod = ui_theme_tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.globals = {}
        self.tm = ui_theme_tk.ThemeManager(self.root, module_globals=self.globals)

    def tearDown(self):
        self.root.destroy()

    def test_apply_creates_named_fonts_and_globals(self):
        p = self.tm.apply({"ui_theme": "graphite"}, recolor=False)
        for name in self.mod.FONT_ROLES:
            self.assertIn(name, tkfont.names(self.root))
        self.assertEqual(self.globals["BG"], p.BG)
        self.assertEqual(self.globals["CARD"], p.SURFACE)
        self.assertEqual(self.globals["PILL"], p.BTN)
        self.assertEqual(self.globals["GRN"], p.OK)
        self.assertEqual(self.globals["ACC2"], p.WARN)
        self.assertEqual(self.globals["RED"], p.ERR)

    def test_scale_changes_font_size(self):
        self.tm.apply({"ui_scale": "normal"}, recolor=False)
        base = tkfont.nametofont("VT.Base").actual("size")
        self.tm.apply({"ui_scale": "xlarge"}, recolor=False)
        self.assertGreater(tkfont.nametofont("VT.Base").actual("size"), base)

    def test_scale_changes_tk_standard_fonts(self):
        self.tm.apply({"ui_scale": "normal"}, recolor=False)
        base = tkfont.nametofont("TkTextFont", root=self.root).actual("size")
        fixed = tkfont.nametofont("TkFixedFont", root=self.root).actual()
        self.tm.apply({"ui_scale": "xlarge"}, recolor=False)
        for name in ("TkDefaultFont", "TkTextFont"):
            font = tkfont.nametofont(name, root=self.root)
            self.assertGreater(font.actual("size"), base)
            self.assertEqual(font.actual("family"),
                             tkfont.nametofont("VT.Base", root=self.root).actual("family"))
        self.assertEqual(tkfont.nametofont("TkFixedFont", root=self.root).actual(), fixed)

    def test_mono_theme_switches_ui_family_but_mono_font_stays_mono(self):
        self.tm.apply({"ui_theme": "graphite"}, recolor=False)
        sans_family = tkfont.nametofont("VT.Base").actual("family")
        mono_family = tkfont.nametofont("VT.Mono").actual("family")
        self.tm.apply({"ui_theme": "neon"}, recolor=False)
        self.assertEqual(tkfont.nametofont("VT.Base").actual("family"), mono_family)
        self.assertEqual(tkfont.nametofont("VT.Mono").actual("family"), mono_family)
        self.assertNotEqual(sans_family, mono_family)

    def test_skin_fonts_use_their_family_and_size_factor(self):
        from videotranslator import ui_theme_tk
        self.tm.apply({"ui_theme": "graphite"}, recolor=False)
        mono_family = tkfont.nametofont("VT.Mono", root=self.root).actual("family")
        self.tm._skin_family = {"pixel": None, "crt": mono_family}
        factor = {mono_family: 1.5}
        original = ui_theme_tk.SIZE_FACTOR
        ui_theme_tk.SIZE_FACTOR = factor
        self.addCleanup(setattr, ui_theme_tk, "SIZE_FACTOR", original)
        self.tm.apply({"ui_theme": "crt", "ui_scale": "normal"}, recolor=False)
        base = tkfont.nametofont("VT.Base", root=self.root)
        self.assertEqual(base.actual("family"), mono_family)
        self.assertEqual(base.cget("size"), round(9 * 1.5))
        self.assertEqual(tkfont.nametofont("VT.Mono", root=self.root).cget("size"), 9)
        self.assertEqual(tkfont.nametofont("TkDefaultFont", root=self.root).cget("size"),
                         round(9 * 1.5))
        # Without its bundled font the pixel skin reads as the sans-serif.
        self.tm.apply({"ui_theme": "dex"}, recolor=False)
        self.assertEqual(self.tm.ui_family("pixel"), self.tm._sans)
        self.assertEqual(tkfont.nametofont("VT.Base", root=self.root).cget("size"), 9)

    def test_bundled_fonts_are_seen_by_tk_when_registered_first(self):
        # This process registered them in the test runner only if a GUI test
        # did; check the mapping when the families are installed.
        from videotranslator import ui_theme_tk
        installed = set(tkfont.families(self.root))
        for role, names in ui_theme_tk.SKIN_FAMILIES.items():
            if names[0] in installed:
                self.assertEqual(self.tm.ui_family(role), names[0])

    def test_recolor_maps_every_role_and_leaves_foreign_colours(self):
        old = self.tm.apply({"ui_theme": "graphite"}, recolor=False)
        f = tk.Frame(self.root, bg=old.BG)
        f.pack()
        lbl = tk.Label(f, bg=old.SURFACE, fg=old.FG2, text="x")
        lbl.pack()
        btn = tk.Button(f, bg=old.BTN, fg=old.FG, activebackground=old.BORDER,
                        highlightbackground=old.BORDER)
        btn.pack()
        ent = tk.Entry(f, bg=old.FIELD, fg=old.FG, insertbackground=old.FG)
        ent.pack()
        txt = tk.Text(f, bg=old.FIELD, fg=old.FG)
        txt.tag_configure("warn", foreground=old.WARN)
        txt.pack()
        top = tk.Toplevel(self.root, bg=old.BG)
        top.withdraw()
        top_lbl = tk.Label(top, bg=old.SURFACE, fg=old.ACC)
        top_lbl.pack()
        foreign = tk.Label(f, bg="#123456", fg=old.FG)
        foreign.pack()

        new = self.tm.apply({"ui_theme": "light"}, recolor=True)

        self.assertEqual(f.cget("bg"), new.BG)
        self.assertEqual(lbl.cget("bg"), new.SURFACE)
        self.assertEqual(lbl.cget("fg"), new.FG2)
        self.assertEqual(btn.cget("bg"), new.BTN)
        self.assertEqual(btn.cget("activebackground"), new.BORDER)
        self.assertEqual(btn.cget("highlightbackground"), new.BORDER)
        self.assertEqual(ent.cget("insertbackground"), new.FG)
        self.assertEqual(txt.tag_cget("warn", "foreground"), new.WARN)
        self.assertEqual(top.cget("bg"), new.BG)
        self.assertEqual(top_lbl.cget("fg"), new.ACC)
        self.assertEqual(foreign.cget("bg"), "#123456")
        self.assertEqual(foreign.cget("fg"), new.FG)

    def test_widgets_left_at_tk_defaults_survive_a_round_trip(self):
        # I2: a widget that never set a colour option keeps Tk's default and
        # must not be recoloured as if it carried a palette role.
        self.tm.apply({"ui_theme": "graphite", "ui_accent": "default", "ui_scale": "normal"},
                      recolor=False)
        widgets = [tk.Entry(self.root), tk.Label(self.root, text="x"),
                   tk.Checkbutton(self.root, text="x")]
        options = ("fg", "bg", "selectforeground", "selectbackground", "highlightcolor",
                   "activeforeground", "activebackground", "insertbackground")
        before = {}
        for w in widgets:
            keys = set(w.keys())
            for opt in options:
                full = {"fg": "foreground", "bg": "background"}.get(opt, opt)
                if full in keys:
                    before[(str(w), opt)] = w.cget(opt)
        self.assertGreater(len(before), 10)
        for theme in ("slate", "graphite"):
            self.tm.apply({"ui_theme": theme}, recolor=True)
        after = {(str(w), opt): w.cget(opt) for w in widgets for opt in options
                 if (str(w), opt) in before}
        self.assertEqual(after, before)

    def test_apply_does_not_create_popdowns_but_later_ones_get_the_palette(self):
        # M2: restyling must not create the drop-down of a combobox never opened.
        self.tm.apply({"ui_theme": "graphite"}, recolor=False)
        cb = ttk.Combobox(self.root, values=("a", "b"))
        cb.pack()
        opened = ttk.Combobox(self.root, values=("c", "d"))
        opened.pack()
        pd_opened = self.root.tk.call("ttk::combobox::PopdownWindow", opened)
        p = self.tm.apply({"ui_theme": "light", "ui_accent": "amber"}, recolor=True)
        self.assertFalse(int(self.root.tk.call("winfo", "exists", f"{cb}.popdown")))
        self.assertEqual(self.root.tk.call(f"{pd_opened}.f.l", "cget", "-background"), p.FIELD)
        self.assertEqual(self.root.tk.call(f"{pd_opened}.f.l", "cget", "-selectbackground"), p.SEL)
        pd_late = self.root.tk.call("ttk::combobox::PopdownWindow", cb)
        listbox = f"{pd_late}.f.l"
        self.assertEqual(str(self.root.tk.call(listbox, "cget", "-background")), p.FIELD)
        self.assertEqual(str(self.root.tk.call(listbox, "cget", "-foreground")), p.FG)
        self.assertEqual(str(self.root.tk.call(listbox, "cget", "-selectbackground")), p.SEL)
        self.assertEqual(str(self.root.tk.call(listbox, "cget", "-selectforeground")), p.FG)
        self.assertEqual(str(self.root.tk.call(listbox, "cget", "-font")), "VT.Base")

    def test_recolor_before_any_palette_is_noop(self):
        # First apply has nothing to map from: must not raise.
        self.tm.apply({"ui_theme": "slate"}, recolor=True)
        self.assertEqual(self.tm.palette.name, "slate")

    def test_ttk_styles_configured(self):
        p = self.tm.apply({"ui_theme": "slate"}, recolor=False)
        style = ttk.Style(self.root)
        self.assertEqual(style.lookup("TCombobox", "fieldbackground"), p.FIELD)
        self.assertEqual(style.lookup("Horizontal.TProgressbar", "background"), p.ACC)
        self.assertEqual(style.lookup("Treeview", "background"), p.FIELD)

class _GatedDetector:
    """Stand-in for ``detect_system_dark`` that answers only once released."""

    def __init__(self, value):
        self.value = value
        self.entered = threading.Event()
        self.released = threading.Event()
        self.threads = []

    def __call__(self):
        self.threads.append(threading.current_thread())
        self.entered.set()
        self.released.wait(10)
        return self.value


def _pump_until(root, condition, timeout=5.0):
    """Run the Tk event loop until ``condition()`` holds; False on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        root.update()
        if condition():
            return True
        time.sleep(0.01)
    return False


def _pending_timers(root):
    return root.tk.splitlist(root.tk.call("after", "info"))


def focus_until(app, widget, timeout=5.0):
    """Give ``widget`` the keyboard focus; True once ``app`` reports it there.

    On Windows the focus reaches a widget of a window just shown only after
    the system activates that window, so it is forced again between event
    loop turns until it arrives. Where it is there at once (X11), no loop
    turn runs, so nothing can move it before the caller sends a key.
    """
    deadline = time.monotonic() + timeout
    widget.focus_force()
    while app.focus_get() is not widget and time.monotonic() < deadline:
        app.update()
        widget.focus_force()
    return app.focus_get() is widget


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class AutoThemeDetectionTests(unittest.TestCase):
    """M7: the OS dark-mode probe runs off the Tk thread, its answer comes back late."""

    def setUp(self):
        from videotranslator import ui_theme_tk
        self.mod = ui_theme_tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.on_system_dark = mock.Mock()
        self.on_reapplied = mock.Mock()

    def tearDown(self):
        for after_id in _pending_timers(self.root):
            self.root.after_cancel(after_id)
        self.root.destroy()

    def _gated(self, value):
        detector = _GatedDetector(value)
        self.addCleanup(detector.released.set)
        return detector

    def _manager(self, detector, system_dark=None, root=None):
        patcher = mock.patch.object(self.mod, "detect_system_dark", detector)
        patcher.start()
        self.addCleanup(patcher.stop)
        tm = self.mod.ThemeManager(root or self.root, module_globals={},
                                   system_dark=system_dark,
                                   on_system_dark=self.on_system_dark,
                                   on_reapplied=self.on_reapplied)
        self.addCleanup(tm.close)
        return tm

    def _settle(self, tm, detector):
        """Let the detector answer and the Tk thread take the answer in."""
        detector.released.set()
        tm._detector.join(5)
        self.assertFalse(tm._detector.is_alive())
        self.assertTrue(_pump_until(self.root, lambda: not _pending_timers(self.root)))

    def test_apply_does_not_wait_for_the_detector(self):
        detector = self._gated(False)
        tm = self._manager(detector)
        start = time.monotonic()
        p = tm.apply({"ui_theme": "auto"}, recolor=False)
        self.assertLess(time.monotonic() - start, 5.0)
        self.assertEqual(p.name, "graphite")  # nothing cached yet: dark
        detector.released.set()
        tm._detector.join(5)
        self.assertEqual(len(detector.threads), 1)
        self.assertIsNot(detector.threads[0], threading.main_thread())

    def test_a_running_probe_keeps_neither_the_manager_nor_the_root(self):
        # If the probe thread held the manager, it could drop the last
        # reference to the root, and the Tk interpreter would be released
        # outside the thread that created it.
        detector = self._gated(False)
        patcher = mock.patch.object(self.mod, "detect_system_dark", detector)
        patcher.start()
        self.addCleanup(patcher.stop)
        tm = self.mod.ThemeManager(self.root, module_globals={})
        tm.apply({"ui_theme": "auto"}, recolor=False)
        probe = tm._detector
        self.assertTrue(detector.entered.wait(5))
        tm.close()
        manager = weakref.ref(tm)
        del tm
        gc.collect()
        self.assertTrue(probe.is_alive())
        self.assertIsNone(manager(), "the probe thread keeps the theme manager alive")
        detector.released.set()
        probe.join(5)

    def test_cached_value_paints_first(self):
        for cached, expected in ((False, "light"), (True, "graphite"), ("yes", "graphite")):
            with self.subTest(cached=cached):
                tm = self._manager(self._gated(None), system_dark=cached)
                self.assertEqual(tm.apply({"ui_theme": "auto"}, recolor=False).name, expected)

    def test_late_answer_reapplies_through_the_recolour_path(self):
        detector = self._gated(False)
        tm = self._manager(detector)
        old = tm.apply({"ui_theme": "auto"}, recolor=False)
        ring = tk.Frame(self.root, bg=old.BG, highlightthickness=2,
                        highlightbackground=old.BG, highlightcolor=old.ACC)
        label = tk.Label(ring, bg=old.SURFACE, fg=old.FG)
        detector.released.set()
        tm._detector.join(5)
        # The worker never applies anything itself: only the Tk loop does.
        self.assertIs(tm.palette, old)
        self.assertTrue(_pump_until(self.root, lambda: tm.palette is not old))
        new = tm.palette
        self.assertEqual(new.name, "light")
        self.assertEqual(ring.cget("bg"), new.BG)
        self.assertEqual(ring.cget("highlightbackground"), new.BG)
        self.assertEqual(ring.cget("highlightcolor"), new.ACC)
        self.assertEqual(label.cget("bg"), new.SURFACE)
        self.assertEqual(label.cget("fg"), new.FG)
        self.assertEqual(tm._globals["BG"], new.BG)
        self.on_system_dark.assert_called_once_with(False)
        self.on_reapplied.assert_called_once_with()
        self.assertTrue(_pump_until(self.root, lambda: not _pending_timers(self.root)))

    def test_answer_that_keeps_the_palette_does_not_reapply(self):
        cases = ((None, True, [mock.call(True)]), (True, True, []),
                 (False, False, []), (False, None, []), (None, None, []))
        for cached, detected, remembered in cases:
            with self.subTest(cached=cached, detected=detected):
                self.on_system_dark.reset_mock()
                self.on_reapplied.reset_mock()
                detector = self._gated(detected)
                tm = self._manager(detector, system_dark=cached)
                before = tm.apply({"ui_theme": "auto"}, recolor=False)
                self._settle(tm, detector)
                self.assertIs(tm.palette, before)
                self.assertEqual(self.on_system_dark.call_args_list, remembered)
                self.on_reapplied.assert_not_called()

    def test_answer_after_leaving_auto_only_updates_the_cache(self):
        detector = self._gated(False)
        tm = self._manager(detector)
        tm.apply({"ui_theme": "auto"}, recolor=False)
        graphite = tm.apply({"ui_theme": "graphite"}, recolor=True)
        self._settle(tm, detector)
        self.assertIs(tm.palette, graphite)
        self.on_system_dark.assert_called_once_with(False)
        self.on_reapplied.assert_not_called()
        # Back to auto: the value learnt meanwhile paints at once, and a
        # fresh probe starts.
        self.assertEqual(tm.apply({"ui_theme": "auto"}, recolor=True).name, "light")
        tm._detector.join(5)
        self.assertEqual(len(detector.threads), 2)

    def test_one_probe_per_switch_to_auto(self):
        detector = self._gated(True)
        tm = self._manager(detector)
        tm.apply({"ui_theme": "auto"}, recolor=False)
        tm.apply({"ui_theme": "auto", "ui_accent": "rose"}, recolor=True)
        self._settle(tm, detector)
        self.assertEqual(len(detector.threads), 1)
        tm.apply({"ui_theme": "graphite"}, recolor=True)
        tm.apply({"ui_theme": "auto"}, recolor=True)
        tm._detector.join(5)
        self.assertEqual(len(detector.threads), 2)

    def test_back_to_auto_while_probing_waits_for_the_running_probe(self):
        detector = self._gated(False)
        tm = self._manager(detector)
        tm.apply({"ui_theme": "auto"}, recolor=False)
        tm.apply({"ui_theme": "graphite"}, recolor=True)
        tm.apply({"ui_theme": "auto"}, recolor=True)
        self._settle(tm, detector)
        self.assertEqual(len(detector.threads), 1)
        self.assertEqual(tm.palette.name, "light")
        self.on_reapplied.assert_called_once_with()

    def test_close_drops_a_pending_answer(self):
        detector = self._gated(False)
        tm = self._manager(detector)
        before = tm.apply({"ui_theme": "auto"}, recolor=False)
        self.assertTrue(_pending_timers(self.root))
        tm.close()
        self.assertEqual(_pending_timers(self.root), ())
        detector.released.set()
        tm._detector.join(5)
        for _ in range(20):
            self.root.update()
            time.sleep(0.01)
        self.assertIs(tm.palette, before)
        self.on_system_dark.assert_not_called()
        self.on_reapplied.assert_not_called()
        # A closed manager starts no new probe.
        tm.apply({"ui_theme": "graphite"}, recolor=True)
        tm.apply({"ui_theme": "auto"}, recolor=True)
        self.assertEqual(len(detector.threads), 1)
        self.assertEqual(_pending_timers(self.root), ())

    def test_answer_for_a_destroyed_root_touches_nothing(self):
        root = tk.Tk()
        root.withdraw()
        detector = self._gated(False)
        tm = self._manager(detector, root=root)
        before = tm.apply({"ui_theme": "auto"}, recolor=False)
        detector.released.set()
        tm._detector.join(5)
        # Destroyed without close(): drop its timer so it cannot fire in a
        # later test, then run by hand what that timer would have run.
        for after_id in _pending_timers(root):
            root.after_cancel(after_id)
        root.destroy()
        tm._poll_system_dark()
        self.assertIs(tm.palette, before)
        self.on_system_dark.assert_not_called()
        self.on_reapplied.assert_not_called()


class ScaledSizeTests(unittest.TestCase):
    def test_scaled_rounds_and_has_a_floor(self):
        from videotranslator.ui_theme_tk import _scaled
        self.assertEqual(_scaled(9, 1.0), 9)
        self.assertEqual(_scaled(9, 1.3), 12)
        self.assertEqual(_scaled(8, 0.9), 7)
        self.assertEqual(_scaled(4, 0.9), 6)


class ColorMappingTests(unittest.TestCase):
    def test_mapping_covers_all_roles(self):
        from videotranslator.ui_theme_tk import build_color_mapping
        old, new = resolve_palette("graphite"), resolve_palette("light")
        mapping = build_color_mapping(old, new)
        self.assertEqual(len(mapping), len(old.COLOR_FIELDS))
        self.assertEqual(mapping[old.ACC], new.ACC)
        self.assertEqual(mapping[old.BG], new.BG)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class CanvasContentFitsTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_fits_only_when_content_is_not_taller_than_canvas(self):
        import video_translator_gui as gui

        canvas = tk.Canvas(self.root, height=300, width=200, highlightthickness=0)
        canvas.pack()
        inner = tk.Frame(canvas, height=50, width=100)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        self.root.update_idletasks()
        self.assertTrue(gui.App._canvas_content_fits(canvas))
        inner.configure(height=1000)
        self.root.update_idletasks()
        self.assertFalse(gui.App._canvas_content_fits(canvas))

    def test_empty_canvas_fits(self):
        import video_translator_gui as gui

        canvas = tk.Canvas(self.root, height=300, width=200)
        self.assertTrue(gui.App._canvas_content_fits(canvas))


@contextlib.contextmanager
def built_app(config):
    """Build the whole ``App`` on a temporary config and always tear it down.

    stdout/stderr are saved before ``App()`` and restored in the outermost
    ``finally``, so neither a constructor that raises after installing its
    redirect nor a failing ``destroy()`` can leave later tests writing into
    a dead Tk widget. The app is destroyed while ``CONFIG_PATH`` is still
    patched, so a save triggered at teardown can never reach the real user
    config.
    """
    import json
    import sys
    import tempfile
    from pathlib import Path

    import video_translator_gui as gui

    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            cfg_path.write_text(json.dumps(config), encoding="utf-8")
            with mock.patch.object(gui, "CONFIG_PATH", cfg_path), \
                    mock.patch.object(gui.App, "_check_deps_on_start", lambda self: None), \
                    mock.patch.object(gui.App, "_upgrade_ytdlp_in_background", lambda self: None), \
                    mock.patch.object(gui.App, "_refresh_player_status", lambda self, **kw: None), \
                    mock.patch.object(gui.App, "_fit_to_screen", lambda self: None):
                app = None
                try:
                    app = gui.App()
                    app.withdraw()
                    yield gui, app, cfg_path
                finally:
                    if app is not None:
                        app._destroying = True
                        # Tk timers outlive the app: a later test that runs
                        # the event loop would fire them against its deleted
                        # commands ("invalid command name" on stderr). Cancel
                        # the timers only: app.after_cancel would also delete
                        # the command a widget registered (a tooltip's pending
                        # _show), and that widget's destroy would then fail
                        # with "can't delete Tcl command". destroy() deletes
                        # every command through the widget that owns it.
                        for after_id in app.tk.splitlist(app.tk.call("after", "info")):
                            app.tk.call("after", "cancel", after_id)
                        app.destroy()
                        # Collect its Tk variables now, on the main thread (see
                        # the dialog tests): later a worker thread could hang on them.
                        import gc
                        gc.collect()
    finally:
        sys.stdout, sys.stderr = saved_stdout, saved_stderr


class BuiltAppStreamsTests(unittest.TestCase):
    def test_streams_restored_when_app_constructor_raises(self):
        # M5: App() may install its stdout/stderr redirect and then raise.
        import io
        import sys

        import video_translator_gui as gui

        class ExplodingApp:
            _check_deps_on_start = _upgrade_ytdlp_in_background = _fit_to_screen = \
                _refresh_player_status = lambda self, **kw: None

            def __init__(self):
                sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
                raise RuntimeError("boom")

        before = (sys.stdout, sys.stderr)
        with mock.patch.object(gui, "App", ExplodingApp):
            with self.assertRaises(RuntimeError):
                with built_app({}):
                    pass
        self.assertEqual((sys.stdout, sys.stderr), before)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class SettingsDialogSmokeTests(unittest.TestCase):
    def test_open_apply_reset_close(self):
        import json

        config = {"ui_theme": "slate", "ui_accent": "rose", "ui_scale": "large", "ui_lang": "en"}
        with built_app(config) as (gui, app, cfg_path):
            self.assertEqual(app._theme.palette.name, "slate")
            self.assertEqual(app._ui_lang.get(), "en")
            app._open_settings()
            self.assertTrue(app._settings_win.winfo_exists())
            app._open_settings()
            toplevels = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]
            self.assertEqual(len(toplevels), 1)
            app._ui_theme_var.set("light")
            app._apply_ui_settings()
            self.assertEqual(app._theme.palette.name, "light")
            self.assertEqual(app.cget("bg"), app._theme.palette.BG)
            self.assertEqual(app._settings_win.cget("bg"), app._theme.palette.BG)
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["ui_theme"], "light")
            # an explicit accent dot keeps its own colour across accent changes
            rose_dot = app._accent_dots["rose"]
            app._ui_accent_var.set("teal")
            app._apply_ui_settings()
            self.assertEqual(rose_dot.cget("fg"), gui._ACCENTS["rose"])
            # the default dot shows the theme's own accent, not the selected one
            app._ui_accent_var.set("rose")
            app._apply_ui_settings()
            own_accent = resolve_palette(app._theme.palette.name, "default").ACC
            self.assertEqual(app._accent_dots["default"].cget("fg"), own_accent)
            self.assertNotEqual(own_accent, gui._ACCENTS["rose"])
            # a language switch relabels the open dialog and rebuilds the rows in place
            theme_before = app._ui_theme_var.get()
            fr_index = [code for code, _ in gui.UI_LANG_OPTIONS].index("fr")
            app._ui_lang_combo.current(fr_index)
            app._on_ui_lang_change()
            self.assertEqual(app._settings_win.title(), gui.UI_STRINGS["fr"]["settings_title"])
            self.assertTrue(app._seg_theme.winfo_exists())
            self.assertEqual(app._ui_theme_var.get(), theme_before)
            slaves = app._lbl_settings_theme.master.pack_slaves()
            self.assertIs(slaves[slaves.index(app._lbl_settings_theme) + 1], app._seg_theme)
            en_index = [code for code, _ in gui.UI_LANG_OPTIONS].index("en")
            app._ui_lang_combo.current(en_index)
            app._on_ui_lang_change()
            app._reset_ui_settings()
            self.assertEqual(app._theme.palette.name, "graphite")
            self.assertEqual(app._ui_scale_var.get(), "normal")
            self.assertEqual(app._ui_lang.get(), "en")  # reset keeps the language
            app._close_settings()
            self.assertFalse(getattr(app, "_settings_win", None) and app._settings_win.winfo_exists())


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class AutoThemeStartupTests(unittest.TestCase):
    """M7: the window paints without waiting for the OS dark-mode probe."""

    def _gated(self, value):
        from videotranslator import ui_theme_tk

        detector = _GatedDetector(value)
        self.addCleanup(detector.released.set)
        patcher = mock.patch.object(ui_theme_tk, "detect_system_dark", detector)
        patcher.start()
        self.addCleanup(patcher.stop)
        return detector

    def test_paints_from_a_cached_light_value_then_follows_the_late_answer(self):
        import json

        # Only a cached False is distinguishable from no cache: unknown
        # already paints dark.
        detector = self._gated(True)
        cfg = {"ui_theme": "auto", "ui_accent": "default", "ui_lang": "en",
               "ui_last_system_dark": False}
        with built_app(cfg) as (gui, app, cfg_path):
            self.assertTrue(detector.entered.wait(5))
            self.assertFalse(detector.released.is_set())
            first = app._theme.palette
            self.assertEqual(first.name, "light")
            self.assertEqual(gui.BG, first.BG)
            self.assertEqual(app.cget("bg"), first.BG)
            self.assertEqual(len(detector.threads), 1)
            self.assertIsNot(detector.threads[0], threading.main_thread())
            gear = app._btn_settings
            detector.released.set()
            self.assertTrue(_pump_until(app, lambda: app._theme.palette.name == "graphite"))
            p = app._theme.palette
            self.assertEqual(gui.BG, p.BG)
            self.assertEqual(app.cget("bg"), p.BG)
            self.assertEqual(gear.cget("highlightcolor"), p.ACC)
            self.assertEqual(gear.cget("highlightbackground"), p.BG)
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertIs(saved["ui_last_system_dark"], True)
            self.assertEqual(saved["ui_theme"], "auto")

    def test_late_answer_refreshes_what_the_colour_mapping_cannot_tell_apart(self):
        import json

        detector = self._gated(False)
        with built_app({"ui_theme": "auto", "ui_accent": "default", "ui_lang": "en"}) \
                as (gui, app, cfg_path):
            self.assertEqual(app._theme.palette.name, "graphite")
            app._open_settings()
            gear = app._btn_settings
            detector.released.set()
            self.assertTrue(_pump_until(app, lambda: app._theme.palette.name == "light"))
            p = app._theme.palette
            self.assertEqual(app.cget("bg"), p.BG)
            self.assertEqual(app._settings_win.cget("bg"), p.BG)
            self.assertEqual(gear.cget("highlightcolor"), p.ACC)
            self.assertEqual(gear.cget("highlightbackground"), p.BG)
            # Graphite's own accent is the blue swatch: the colour mapping
            # alone would repaint that dot, the refresh gives it back.
            self.assertEqual(app._accent_dots["blue"].cget("fg"), gui._ACCENTS["blue"])
            self.assertEqual(app._accent_dots["default"].cget("fg"), p.ACC)
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertIs(saved["ui_last_system_dark"], False)

    def test_close_stops_waiting_for_the_answer(self):
        import json

        detector = self._gated(False)
        with built_app({"ui_theme": "auto", "ui_lang": "en"}) as (gui, app, cfg_path):
            before = app._theme.palette
            self.assertEqual(before.name, "graphite")
            with mock.patch.object(app, "destroy") as destroy:
                app._on_close()
            destroy.assert_called_once_with()
            detector.released.set()
            app._theme._detector.join(5)
            for _ in range(20):
                app.update()
                time.sleep(0.01)
            self.assertIs(app._theme.palette, before)
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertNotIn("ui_last_system_dark", saved)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class KeyboardAccessTests(unittest.TestCase):
    """M6: the header gear and the accent dots work without a mouse."""

    # Tk for Windows has no keysym for the keypad Enter: it reports that key
    # as Return ("event generate" finds no keycode for KP_Enter), so there
    # the Return case covers it.
    ACTIVATE_KEYS = (("<Return>", "<space>") if sys.platform == "win32"
                     else ("<Return>", "<KP_Enter>", "<space>"))

    def _show(self, window):
        """Map ``window``: only a mapped window can take the keyboard focus."""
        import time

        window.deiconify()
        deadline = time.monotonic() + 5
        while not window.winfo_viewable() and time.monotonic() < deadline:
            window.update()
            time.sleep(0.01)
        self.assertTrue(window.winfo_viewable())

    def _focus(self, app, widget):
        focus_until(app, widget)
        self.assertIs(app.focus_get(), widget)

    def _press(self, app, widget, key):
        # Key events go to the focus widget. The key is sent right after
        # focus_force, with no event loop in between, so the window manager
        # cannot move the focus elsewhere first.
        self._focus(app, widget)
        widget.event_generate(key)

    def _tab_walk(self, start, steps):
        walk = [start]
        for _ in range(steps):
            walk.append(walk[-1].tk_focusNext())
        return walk

    def test_gear_takes_focus_and_opens_settings_with_each_activation_key(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            self._show(app)
            gear = app._btn_settings
            self.assertEqual(str(gear.cget("takefocus")), "1")
            for key in self.ACTIVATE_KEYS:
                with self.subTest(key=key):
                    app._close_settings()
                    self._press(app, gear, key)
                    self.assertIsNotNone(app._settings_win)
                    self.assertTrue(app._settings_win.winfo_exists())
            app._close_settings()

    def test_accent_dots_take_focus_and_select_with_each_activation_key(self):
        import json

        cfg = {"ui_theme": "graphite", "ui_accent": "default", "ui_lang": "en"}
        with built_app(cfg) as (gui, app, cfg_path):
            self._show(app)
            app._open_settings()
            self._show(app._settings_win)
            for key, value in zip(self.ACTIVATE_KEYS, ("teal", "amber", "default")):
                with self.subTest(key=key, accent=value):
                    dot = app._accent_dots[value]
                    self.assertEqual(str(dot.cget("takefocus")), "1")
                    self._press(app, dot, key)
                    self.assertEqual(app._ui_accent_var.get(), value)
                    self.assertEqual(app._theme.settings["ui_accent"], value)
                    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
                    self.assertEqual(saved["ui_accent"], value)

    def test_flat_buttons_show_a_focus_ring_and_run_on_return(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            self._show(app)
            ran = []
            for primary in (False, True):
                with self.subTest(primary=primary):
                    wrap, btn = app._flat_btn(app._right_pane, text="x", primary=primary,
                                              command=lambda: ran.append(1))
                    wrap.pack()
                    app.update()
                    idle = wrap.cget("bg")
                    self._press(app, btn, "<Return>")
                    app.update()
                    self.assertEqual(wrap.cget("bg"), gui.FG if primary else gui.ACC)
                    self.assertNotEqual(wrap.cget("bg"), idle)
                    app._btn_settings.focus_force()
                    app.update()
                    self.assertEqual(wrap.cget("bg"), idle)
                    wrap.destroy()
            self.assertEqual(ran, [1, 1])

    def test_tab_follows_the_card_order_after_a_reorder(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en",
                        "ui_panel_order": ["profile", "input", "start", "translation",
                                           "settings"]}) as (gui, app, _):
            self._show(app)

            def card_of(widget):
                while widget is not None:
                    for pid, (outer, _opts) in app._panels.items():
                        if widget is outer:
                            return pid
                    widget = widget.master
                return None
            first = next(w for w in self._tab_walk(app._panels["profile"][0], 1)[1:])
            seen = []
            widget = first
            for _ in range(400):
                pid = card_of(widget)
                if pid and (not seen or seen[-1] != pid):
                    seen.append(pid)
                widget = widget.tk_focusNext()
                if widget is None or widget is first:
                    break
            order = [pid for pid in seen if pid in app._panel_order]
            deduped = [pid for i, pid in enumerate(order) if pid not in order[:i]]
            # Cards with nothing focusable (settings, all sections closed) are
            # skipped by Tab; the others follow the order on screen.
            self.assertGreaterEqual(len(deduped), 4)
            self.assertEqual(deduped, [p for p in app._panel_order if p in deduped])
            self.assertEqual(deduped[0], "profile")

    def test_focus_rings_follow_theme_and_accent_changes_while_focused(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            self._show(app)
            gear = app._btn_settings
            self._focus(app, gear)
            for theme, accent in (("graphite", "default"), ("light", "amber"), ("neon", "rose")):
                app._ui_theme_var.set(theme)
                app._ui_accent_var.set(accent)
                app._apply_ui_settings()
                p = app._theme.palette
                with self.subTest(widget="gear", theme=theme, accent=accent):
                    self.assertIs(app.focus_get(), gear)
                    self.assertGreaterEqual(int(gear.cget("highlightthickness")), 2)
                    self.assertEqual(gear.cget("highlightcolor"), p.ACC)
                    self.assertEqual(gear.cget("highlightbackground"), p.BG)
            app._open_settings()
            self._show(app._settings_win)
            focused_dot = app._accent_dots["teal"]
            self._focus(app, focused_dot)
            for theme, accent in (("slate", "violet"), ("light", "default"), ("graphite", "teal")):
                app._ui_theme_var.set(theme)
                app._ui_accent_var.set(accent)
                app._apply_ui_settings()
                p = app._theme.palette
                self.assertIs(app.focus_get(), focused_dot)
                for value, dot in app._accent_dots.items():
                    with self.subTest(dot=value, theme=theme, accent=accent):
                        self.assertGreaterEqual(int(dot.cget("highlightthickness")), 2)
                        self.assertEqual(dot.cget("highlightcolor"), p.ACC)
                        self.assertEqual(dot.cget("highlightbackground"),
                                         p.FG if value == accent else p.SURFACE)
                self.assertEqual(gear.cget("highlightcolor"), p.ACC)
                self.assertEqual(gear.cget("highlightbackground"), p.BG)

    def test_tab_reaches_the_gear_first_and_walks_the_settings_in_reading_order(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            self._show(app)
            # The header is the first row of the window: its gear is the first stop.
            self.assertIs(app.tk_focusNext(), app._btn_settings)
            app._open_settings()
            self._show(app._settings_win)

            def expected():
                return (list(app._seg_theme.winfo_children())
                        + list(app._seg_skin.winfo_children())
                        + [app._accent_dots[v] for v in gui._ACCENT_CHOICES]
                        + list(app._seg_scale.winfo_children())
                        + [app._ui_lang_combo, app._chk_player_autoload,
                           app._chk_keep_original_audio, app._btn_settings_reset,
                           app._btn_settings_close])

            def mapped(order):
                # Tab skips a widget not mapped yet, and on Windows a window's
                # widgets appear a moment after the window itself.
                return _pump_until(app, lambda: all(w.winfo_viewable() for w in order))

            order = expected()
            self.assertTrue(mapped(order))
            self.assertEqual(self._tab_walk(order[0], len(order)), order + [order[0]])
            # A UI language change rebuilds the two segmented rows: they must
            # keep their place in the Tab order, not move after the dots.
            fr_index = [code for code, _ in gui.UI_LANG_OPTIONS].index("fr")
            app._ui_lang_combo.current(fr_index)
            app._on_ui_lang_change()
            app.update()
            order = expected()
            self.assertTrue(mapped(order))
            self.assertEqual(self._tab_walk(order[0], len(order)), order + [order[0]])


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class SkinTests(unittest.TestCase):
    def test_skin_row_switches_theme_frames_and_hover(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            app._open_settings()
            labels = [b.cget("text") for b in app._seg_skin.winfo_children()]
            self.assertEqual(labels, ["Dex", "Handheld", "CRT", "CRT Amber"])
            self.assertEqual(len(app._seg_theme.winfo_children()), len(gui._BASE_THEMES))
            self.assertEqual(app._lbl_settings_skin.cget("text"),
                             gui.UI_STRINGS["en"]["settings_skin"])
            cards = [f for f in app._card_frames if f.winfo_exists()]
            self.assertGreaterEqual(len(cards), 5)
            self.assertTrue(all(int(f.cget("highlightthickness")) == 1 for f in cards))
            app._seg_skin.winfo_children()[0].invoke()          # Dex
            p = app._theme.palette
            self.assertEqual((p.name, gui.BORDER_PX), ("dex", 3))
            self.assertTrue(all(int(f.cget("highlightthickness")) == 3 for f in cards))
            selected = app._seg_skin.winfo_children()[0]
            self.assertEqual(selected.cget("bg"), p.ACC_SOFT)
            self.assertEqual(app._hover_bg(), p.SEL)      # dark text on red is hard to read
            # A window of its own: packed below the settings, the key may find
            # no room (Windows keeps that window's size) and stay unmapped.
            host = tk.Toplevel(app)
            wrap, button = app._flat_btn(host, text="x")
            wrap.pack()
            # A widget not mapped yet drops the <Enter> (on Windows the button
            # appears a moment after its window).
            self.assertTrue(_pump_until(app, button.winfo_viewable))
            # The binding runs inside event_generate: no event loop turn before
            # the check, or the real pointer's <Leave> would undo the hover.
            button.event_generate("<Enter>")
            self.assertEqual(button.cget("bg"), p.SEL)
            host.destroy()
            app._seg_theme.winfo_children()[1].invoke()         # back to Graphite
            self.assertEqual((app._theme.palette.name, gui.BORDER_PX), ("graphite", 1))
            self.assertTrue(all(int(f.cget("highlightthickness")) == 1 for f in cards))
            self.assertEqual(app._hover_bg(), app._theme.palette.BORDER)


    def test_crt_skins_put_the_monitor_shader_on_the_video(self):
        from videotranslator.player_engine import InMemoryBackend
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            backend = InMemoryBackend()
            app._player_backend = backend
            app._video_shader_applied = None
            app._apply_video_effect()
            self.assertEqual(backend.calls, [])          # nothing to clear
            app._ui_theme_var.set("crt")
            app._apply_ui_settings()
            self.assertEqual(backend.calls[-1][0], "set_shader")
            self.assertTrue(backend.calls[-1][1].endswith("crt.glsl"))
            app._apply_ui_settings()                     # unchanged: not sent again
            self.assertEqual(len(backend.calls), 1)
            app._ui_theme_var.set("crt_amber")
            app._apply_ui_settings()
            self.assertTrue(backend.calls[-1][1].endswith("crt_amber.glsl"))
            app._ui_theme_var.set("dex")
            app._apply_ui_settings()
            self.assertEqual(backend.calls[-1], ("set_shader", None))
            app._player_backend = None


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class TalkingLogTests(unittest.TestCase):
    """Every click, choice and error reaches the Log panel and the log file."""

    def _panel(self, app):
        app.update()
        app.after(150)
        app.update()
        return app._log.get("1.0", "end")

    def test_clicks_toggles_disabled_controls_and_errors_are_logged(self):
        import threading
        with built_app({"ui_theme": "graphite", "ui_lang": "it"}) as (gui, app, cfg_path):
            it = gui.UI_STRINGS["it"]
            log_path = cfg_path.parent / "logs" / "videotranslator.log"
            self.assertIn(it["log_file"].split("{")[0].strip(), self._panel(app))
            app.deiconify()
            host = tk.Toplevel(app)
            host.title("Voicebox")
            button = tk.Button(host, text="Verifica",
                               command=lambda: app._log_line("voicebox", "RESULT"))
            check_var = tk.BooleanVar(value=False)
            check = tk.Checkbutton(host, text="Voicebox", variable=check_var)
            off = tk.Button(host, text="Scarica", state="disabled")
            for w in (button, check, off):
                w.pack()
            app.update()
            for w in (button, check, off):
                # The key goes to the focus widget: no event loop turn between
                # the focus and the key (a real <Leave>, a window manager).
                focus_until(app, w)
                w.event_generate("<Key-space>")
            text = self._panel(app)
            # every line: time, level, area, message
            self.assertRegex(text, r"\d{2}:\d{2}:\d{2} INFO +\[ui\] " + re.escape(
                it["log_click"].format(name="Voicebox > Verifica")))
            self.assertRegex(text, r"\[app\] Video Translator AI \d")
            self.assertIn(it["log_click"].format(name="Voicebox > Verifica"), text)
            # the click comes before its result
            self.assertTrue(check_var.get())
            self.assertLess(text.index(it["log_click"].format(name="Voicebox > Verifica")),
                            text.index("RESULT"))
            self.assertIn(it["log_on"].format(name="Voicebox > Voicebox"), text)
            self.assertTrue(check_var.get())
            self.assertIn(it["log_click_disabled"].format(name="Voicebox > Scarica"), text)
            host.destroy()
            # print() from the Tk thread reaches the panel (it used to go to the terminal)
            print("main-thread line")
            self.assertIn("main-thread line", self._panel(app))
            # an error inside a Tk callback is logged with its traceback
            app.report_callback_exception(ValueError, ValueError("boom"), None)
            text = self._panel(app)
            self.assertIn("ValueError: boom", text)
            self.assertRegex(text, it["log_level_error"] + r" +\[app\] ")
            self.assertTrue(app._log.tag_ranges("lvl_error"))
            self.assertEqual(app._log.tag_cget("lvl_error", "foreground"), app._theme.palette.ERR)
            # a command echoed right after its click is not written twice
            count = text.count(it["log_live"].split(":")[0])
            app._last_click_at = __import__("time").monotonic()
            app._log_event("log_live", command="start", value="source=file")
            self.assertEqual(self._panel(app).count(it["log_live"].split(":")[0]), count)
            # the system part of the session header
            from types import SimpleNamespace as NS
            app._log_system({"os": "Kali GNU/Linux Rolling", "locale": "it_IT.UTF-8",
                             "libs": "torch 2.6.0", "smi": ("580.1", "13.0"),
                             "ffmpeg": "8.1.2",
                             "hw": NS(cpu_name="i7", cpu_cores=16, ram_gb=31.2, gpus=(),
                                      disk_free_gb=266.8)})
            text = self._panel(app)
            for line in (it["log_sys_os"].format(os="Kali GNU/Linux Rolling", locale="it_IT.UTF-8"),
                         it["log_sys_gpu"].format(driver="580.1", cuda="13.0"),
                         it["log_sys_libs"].format(libs="torch 2.6.0"),
                         it["log_sys_tools"].format(tools="ffmpeg 8.1.2"),
                         it["mdl_hw_disk"].format(free="266.8")):
                self.assertIn(line, text)
            self.assertIn("[sys] " + it["log_sys_screen"].split(":")[0], text)
            # raw pipeline lines get their level too
            print("[!] Voicebox not available")
            self.assertRegex(self._panel(app), it["log_level_warn"] + r" +\[app\] Voicebox not")
            # an uncaught error in a worker thread too (the hook is called here on
            # the Tk thread: without a running mainloop a worker cannot reach Tk)
            self.assertEqual(threading.excepthook, app._log_thread_exception)
            try:
                1 / 0
            except ZeroDivisionError as exc:
                args = threading.ExceptHookArgs(
                    (type(exc), exc, exc.__traceback__, threading.Thread(name="unit-worker")))
            app._saved_thread_excepthook = lambda _args: None
            app._log_thread_exception(args)
            text = self._panel(app)
            self.assertIn("unit-worker", text)
            self.assertIn("ZeroDivisionError", text)
            app._log_file._handler.flush()
            on_disk = log_path.read_text(encoding="utf-8")
            self.assertIn(it["log_click"].format(name="Voicebox > Verifica"), on_disk)
            self.assertIn("main-thread line", on_disk)
            hook = app._log_thread_exception
        # after destroy nothing points at the dead app any more
        self.assertIsNone(gui._DEFAULT_REDIRECT)
        self.assertNotEqual(threading.excepthook, hook)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class LogToggleStartupTests(unittest.TestCase):
    def test_visible_log_at_startup_shows_hide_label(self):
        with built_app({"ui_lang": "it", "ui_log_visible": True}) as (gui, app, _):
            self.assertTrue(app._log_visible)
            self.assertEqual(app._btn_log_toggle.cget("text"),
                             gui.UI_STRINGS["it"]["btn_log_hide"])


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class GuiThemedDefaultsTests(unittest.TestCase):
    """I2b: the GUI sets the colour options it used to leave at Tk defaults."""

    def test_fields_toggles_and_focus_rings_follow_the_palette(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            app._open_settings()
            app._ui_theme_var.set("slate")
            app._apply_ui_settings()
            p = app._theme.palette
            fields, toggles = [], []
            stack = [app]
            while stack:
                w = stack.pop()
                stack.extend(w.winfo_children())
                if isinstance(w, (tk.Entry, tk.Text)) and not isinstance(w, ttk.Entry):
                    fields.append(w)
                elif isinstance(w, (tk.Checkbutton, tk.Radiobutton)):
                    toggles.append(w)
            self.assertGreaterEqual(len(fields), 7)
            self.assertGreaterEqual(len(toggles), 8)
            for w in fields:
                with self.subTest(field=str(w)):
                    self.assertEqual(w.cget("selectbackground"), p.SEL)
                    self.assertEqual(w.cget("selectforeground"), p.FG)
                    self.assertEqual(w.cget("insertbackground"), p.FG)
            for w in toggles:
                with self.subTest(toggle=str(w)):
                    # Hover keeps the widget's own text colour: FG, or the
                    # ERR hint used on the large Whisper models.
                    self.assertIn(w.cget("fg"), (p.FG, p.ERR))
                    self.assertEqual(w.cget("activeforeground"), w.cget("fg"))
                    self.assertEqual(w.cget("activebackground"),
                                     p.ACC_SOFT if w.cget("indicatoron") in (0, "0")
                                     else w.cget("bg"))
            ringed = list(app._profile_btns.values()) \
                + list(app._seg_theme.winfo_children()) \
                + list(app._seg_scale.winfo_children())
            for b in ringed:
                with self.subTest(button=str(b)):
                    self.assertEqual(b.cget("highlightcolor"), p.ACC)

    def test_small_status_texts_do_not_use_the_accent(self):
        # M1: accent text on SURFACE at 8-9 pt is 2.57:1 on light+amber.
        with built_app({"ui_theme": "light", "ui_accent": "amber", "ui_lang": "en"}) as (gui, app, _):
            p = app._theme.palette
            self.assertEqual(app._rate_lbl.cget("fg"), p.FG)
            self.assertEqual(app._lbl_status.cget("fg"), p.FG2)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class LayoutTests(unittest.TestCase):
    def test_every_card_sits_in_the_right_pane_and_the_left_is_the_player_area(self):
        # The operator asked for every card on the right (input first, the
        # settings accordion last, under Start), leaving the whole left pane
        # to the future video player.
        with built_app({"ui_theme": "graphite", "ui_lang": "it"}) as (gui, app, _):
            cards = app._right_pane.pack_slaves()
            self.assertGreaterEqual(len(cards), 5)
            self.assertIs(cards[0], _card_of(app._batch_listbox, app._right_pane))
            self.assertIs(cards[-1], app._advanced_card.master)
            self.assertEqual(app._left_pane.pack_slaves(), [app._player_area])
            p = app._theme.palette
            self.assertEqual(app._player_area.cget("bg"), p.FIELD)
            # P0 layout: the cards live in the right column's own scroll
            # canvas, at least 460 px wide; the left pane is a body cell.
            self.assertIs(app._right_pane.master, app._right_canvas)
            self.assertGreaterEqual(int(app._right_canvas.cget("width")), 460)
            self.assertIs(app._left_pane.master, app._body)
            # Tk reports sticky in its own letter order: compare as sets.
            self.assertEqual(set(app._left_pane.grid_info()["sticky"]), set("nsew"))

    def test_panels_follow_the_saved_order_and_drag_reorders_and_persists(self):
        import json
        import types

        cfg = {"ui_theme": "graphite", "ui_lang": "it",
               "ui_panel_order": ["start", "input"]}
        with built_app(cfg) as (gui, app, cfg_path):
            by_outer = {outer: pid for pid, (outer, _) in app._panels.items()}

            def ids():
                return [by_outer[w] for w in app._right_pane.pack_slaves()
                        if w in by_outer]

            self.assertEqual(ids(), ["start", "input", "translation", "profile", "settings"])
            # Drag "settings" to the top. Spans and the column test are
            # injected so the test needs no real geometry (the app is withdrawn).
            app._panel_spans = lambda exclude: [(0, 100), (100, 200), (200, 300), (300, 400)]
            app._pointer_over_column = lambda x_root, slack=40: True
            ev = lambda y: types.SimpleNamespace(x_root=500, y_root=y)  # noqa: E731
            app._panel_drag_start("settings", ev(350))
            app._panel_drag_motion(ev(10))
            self.assertTrue(app._drag_indicator.winfo_manager())
            self.assertEqual(app._drag_indicator.cget("bg"), app._theme.palette.ACC)
            app._panel_drag_end(ev(10))
            expected = ["settings", "start", "input", "translation", "profile"]
            self.assertEqual(ids(), expected)
            self.assertFalse(app._drag_indicator.winfo_manager())
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["ui_panel_order"], expected)
            # A click without movement changes nothing.
            app._panel_drag_start("input", ev(150))
            app._panel_drag_end(ev(151))
            self.assertEqual(ids(), expected)
            # Dropping below the last panel packs the line after it, then
            # moves the card to the end.
            app._panel_drag_start("settings", ev(50))
            app._panel_drag_motion(ev(999))
            self.assertIs(app._right_pane.pack_slaves()[-1], app._drag_indicator)
            app._panel_drag_end(ev(999))
            self.assertEqual(ids(), ["start", "input", "translation", "profile", "settings"])
            # Leaving the column sideways cancels the drop.
            app._pointer_over_column = lambda x_root, slack=40: False
            app._panel_drag_start("start", ev(50))
            app._panel_drag_motion(ev(999))
            self.assertFalse(app._drag_indicator.winfo_manager())
            app._panel_drag_end(ev(999))
            self.assertEqual(ids(), ["start", "input", "translation", "profile", "settings"])
            # "Restore defaults" in the Settings window also restores the order.
            app._open_settings()
            app._reset_ui_settings()
            self.assertEqual(ids(), list(gui._PANEL_IDS))
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["ui_panel_order"], list(gui._PANEL_IDS))

    def test_every_header_widget_starts_a_drag(self):
        # The title text is nested one level below the header row: the
        # bindings must reach every descendant, not only the direct children.
        with built_app({"ui_theme": "graphite", "ui_lang": "it"}) as (gui, app, _):
            for pid, (outer, _) in app._panels.items():
                inner = outer.winfo_children()[0]
                hdr = inner.winfo_children()[0]
                stack = [hdr]
                seen = 0
                while stack:
                    w = stack.pop()
                    stack.extend(w.winfo_children())
                    seen += 1
                    with self.subTest(panel=pid, widget=str(w)):
                        for seq in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"):
                            self.assertTrue(w.bind(seq), seq)
                self.assertGreaterEqual(seen, 2)


def _card_of(widget, pane):
    """Walk up from ``widget`` to the child of ``pane`` that contains it."""
    w = widget
    while w.master is not pane:
        w = w.master
    return w


if __name__ == "__main__":
    unittest.main()
