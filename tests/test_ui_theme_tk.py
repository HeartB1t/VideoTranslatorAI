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


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class SettingsDialogSmokeTests(unittest.TestCase):
    def test_open_apply_reset_close(self):
        import json
        import sys
        import tempfile
        from pathlib import Path

        import video_translator_gui as gui

        saved_stdout, saved_stderr = sys.stdout, sys.stderr
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            cfg_path.write_text(json.dumps({"ui_theme": "slate", "ui_accent": "rose",
                                            "ui_scale": "large", "ui_lang": "en"}), encoding="utf-8")
            with mock.patch.object(gui, "CONFIG_PATH", cfg_path), \
                    mock.patch.object(gui.App, "_check_deps_on_start", lambda self: None), \
                    mock.patch.object(gui.App, "_upgrade_ytdlp_in_background", lambda self: None), \
                    mock.patch.object(gui.App, "_fit_to_screen", lambda self: None):
                app = gui.App()
                try:
                    app.withdraw()
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
                finally:
                    app._destroying = True
                    app.destroy()
                    sys.stdout, sys.stderr = saved_stdout, saved_stderr


if __name__ == "__main__":
    unittest.main()
