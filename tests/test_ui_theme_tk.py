import contextlib
import tkinter as tk
import unittest
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

    def test_auto_theme_caches_system_dark_detection(self):
        with mock.patch.object(self.mod, "detect_system_dark", return_value=False) as stub:
            p1 = self.tm.apply({"ui_theme": "auto"}, recolor=False)
            p2 = self.tm.apply({"ui_theme": "auto"}, recolor=False)
            self.assertEqual(stub.call_count, 1)
            self.assertEqual(p1.name, "light")
            self.assertEqual(p2.name, "light")

            self.tm.apply({"ui_theme": "graphite"}, recolor=False)
            self.tm.apply({"ui_theme": "auto"}, recolor=False)
            self.assertEqual(stub.call_count, 2)


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
                    mock.patch.object(gui.App, "_fit_to_screen", lambda self: None):
                app = None
                try:
                    app = gui.App()
                    app.withdraw()
                    yield gui, app, cfg_path
                finally:
                    if app is not None:
                        app._destroying = True
                        app.destroy()
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
                lambda self: None

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
            content = app._right_pane.master
            self.assertGreaterEqual(int(content.grid_columnconfigure(1)["minsize"]), 460)
            # Tk reports sticky in its own letter order: compare as sets.
            self.assertEqual(set(app._right_pane.grid_info()["sticky"]), set("new"))
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
