"""Tk side of theming: named fonts, ttk styles and live recolouring.

``ThemeManager`` is created once by the GUI before any widget exists. On each
``apply()`` it rewrites the colour globals of the GUI module (so code that
reads ``BG``, ``ACC``, ``CARD``... keeps working), reconfigures the named
fonts (Tk then updates every widget that uses them) and, when widgets
already exist, walks the widget tree replacing every colour option whose
value belongs to the previous palette with the same role in the new one.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont, ttk

from videotranslator.ui_theme import (
    SCALES,
    Palette,
    detect_system_dark,
    normalize_ui_settings,
    resolve_palette,
)

# name -> (family role, base point size, weight, slant)
FONT_ROLES: dict[str, tuple[str, int, str, str]] = {
    "VT.Small":     ("ui",   8,  "normal", "roman"),
    "VT.SmallBold": ("ui",   8,  "bold",   "roman"),
    "VT.Base":      ("ui",   9,  "normal", "roman"),
    "VT.Bold":      ("ui",   9,  "bold",   "roman"),
    "VT.Italic":    ("ui",   8,  "normal", "italic"),
    "VT.Large":     ("ui",   11, "bold",   "roman"),
    "VT.Title":     ("ui",   15, "bold",   "roman"),
    "VT.Mono":      ("mono", 9,  "normal", "roman"),
}

SANS_CANDIDATES = ("Segoe UI", "Inter", "Noto Sans", "Cantarell", "DejaVu Sans", "Helvetica")
MONO_CANDIDATES = ("Cascadia Mono", "JetBrains Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "Courier")

# GUI module global -> Palette field. Old aliases are kept on purpose so the
# ~300 existing call sites in video_translator_gui.py need no edit.
GLOBAL_ALIASES: dict[str, str] = {
    "BG": "BG", "SURFACE": "SURFACE", "CARD": "SURFACE", "FIELD": "FIELD",
    "BORDER": "BORDER", "FG": "FG", "FG2": "FG2", "SEL": "SEL",
    "BTN": "BTN", "PILL": "BTN",
    "ACC": "ACC", "ACC_HOVER": "ACC_HOVER", "ACC_SOFT": "ACC_SOFT", "ACC_FG": "ACC_FG",
    "OK": "OK", "GRN": "OK", "WARN": "WARN", "ACC2": "WARN", "ERR": "ERR", "RED": "ERR",
}

# Classic Tk options that carry a colour.
COLOR_OPTIONS = (
    "background", "foreground", "activebackground", "activeforeground",
    "highlightbackground", "highlightcolor", "insertbackground",
    "selectbackground", "selectforeground", "disabledforeground",
    "troughcolor", "selectcolor", "readonlybackground",
)


def pick_family(root: tk.Misc, candidates, fallback_font: str) -> str:
    """First installed family among ``candidates``, else the Tk default's."""
    installed = set(tkfont.families(root))
    for fam in candidates:
        if fam in installed:
            return fam
    return tkfont.nametofont(fallback_font, root=root).actual("family")


def _scaled(size: int, scale: float) -> int:
    """Point size for ``size`` at ``scale``, never below 6 pt."""
    return max(6, int(round(size * scale)))


def build_color_mapping(old: Palette, new: Palette) -> dict[str, str]:
    """old hex (lower) -> new hex, one entry per colour role."""
    return {getattr(old, f).lower(): getattr(new, f) for f in Palette.COLOR_FIELDS}


def normalize_color(widget: tk.Misc, value) -> str | None:
    """Return ``#rrggbb`` (lower) for a Tk colour value, or ``None``."""
    if not value:
        return None
    v = str(value)
    if v.startswith("#") and len(v) == 7:
        return v.lower()
    try:
        r, g, b = widget.winfo_rgb(v)
    except tk.TclError:
        return None
    return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)


def recolor_widget_tree(root: tk.Misc, mapping: dict[str, str]) -> int:
    """Replace mapped colours on every widget below ``root``, ``root`` included.

    For each widget, every option of ``COLOR_OPTIONS`` that the widget
    exposes is recoloured when its current value is a key of ``mapping``;
    for ``tk.Text`` the background and foreground of every tag are handled
    the same way. ttk widgets are walked too, but they expose none of these
    options, so in practice they follow the ttk styles instead. Unknown
    colours are left alone. Returns the number of options changed.
    """
    changed = 0
    stack: list[tk.Misc] = [root]
    while stack:
        w = stack.pop()
        try:
            keys = set(w.keys())
        except tk.TclError:
            continue
        for opt in COLOR_OPTIONS:
            if opt not in keys:
                continue
            try:
                cur = normalize_color(w, w.cget(opt))
            except tk.TclError:
                continue
            new = mapping.get(cur) if cur else None
            if new and new != cur:
                try:
                    w.configure({opt: new})
                    changed += 1
                except tk.TclError:
                    pass
        if isinstance(w, tk.Text):
            for tag in w.tag_names():
                for opt in ("background", "foreground"):
                    try:
                        cur = normalize_color(w, w.tag_cget(tag, opt))
                    except tk.TclError:
                        continue
                    new = mapping.get(cur) if cur else None
                    if new and new != cur:
                        try:
                            w.tag_configure(tag, {opt: new})
                            changed += 1
                        except tk.TclError:
                            pass
        try:
            stack.extend(w.winfo_children())
        except tk.TclError:
            pass
    return changed


class ThemeManager:
    def __init__(self, root: tk.Misc, module_globals: dict):
        self.root = root
        self._globals = module_globals
        self.palette: Palette | None = None
        self.settings: dict = normalize_ui_settings({})
        self.scale: float = 1.0
        self._system_dark: bool | None = None
        self._last_theme: str | None = None
        self._fonts: dict[str, tkfont.Font] = {}
        self._sans = pick_family(root, SANS_CANDIDATES, "TkDefaultFont")
        self._mono = pick_family(root, MONO_CANDIDATES, "TkFixedFont")

    # -- public ------------------------------------------------------

    def apply(self, settings: dict, recolor: bool = True) -> Palette:
        """Resolve ``settings`` and apply them to fonts, styles and widgets."""
        merged = dict(self.settings)
        merged.update(settings if isinstance(settings, dict) else {})
        self.settings = normalize_ui_settings(merged)
        theme = self.settings["ui_theme"]
        if theme == "auto" and self._last_theme != "auto":
            self._system_dark = detect_system_dark()
        system_dark = self._system_dark if theme == "auto" else None
        new = resolve_palette(theme, self.settings["ui_accent"], system_dark)
        old = self.palette
        self.scale = SCALES[self.settings["ui_scale"]]

        self._apply_globals(new)
        self._apply_fonts(new, self.scale)
        self._apply_ttk(new, self.scale)
        if recolor and old is not None:
            recolor_widget_tree(self.root, build_color_mapping(old, new))
            self._recolor_combobox_popdowns(new)
        self.palette = new
        self._last_theme = theme
        return new

    # -- internals -----------------------------------------------------

    def _apply_globals(self, p: Palette) -> None:
        self._globals.update({name: getattr(p, field) for name, field in GLOBAL_ALIASES.items()})

    def _apply_fonts(self, p: Palette, scale: float) -> None:
        ui_family = self._mono if p.font_family == "mono" else self._sans
        existing = set(tkfont.names(self.root))
        for name, (role, size, weight, slant) in FONT_ROLES.items():
            family = self._mono if role == "mono" else ui_family
            px = _scaled(size, scale)
            if name in existing:
                tkfont.Font(root=self.root, name=name, exists=True).configure(
                    family=family, size=px, weight=weight, slant=slant)
            else:
                # Keep a reference: a Font created here has delete_font=True,
                # so if the object is garbage collected, its __del__ deletes
                # the named Tcl font it just created.
                self._fonts[name] = tkfont.Font(
                    root=self.root, name=name, family=family, size=px,
                    weight=weight, slant=slant)
        # ttk Entry/Combobox text and dropdown lists use Tk's standard fonts,
        # so they follow the text size only if these are scaled too.
        std_px = _scaled(FONT_ROLES["VT.Base"][1], scale)
        for name in ("TkDefaultFont", "TkTextFont"):
            tkfont.nametofont(name, root=self.root).configure(
                family=ui_family, size=std_px, weight="normal")

    def _apply_ttk(self, p: Palette, scale: float) -> None:
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=p.FIELD, background=p.BTN, foreground=p.FG,
                    selectbackground=p.FIELD, selectforeground=p.FG,
                    arrowcolor=p.FG2, bordercolor=p.BORDER, lightcolor=p.BORDER,
                    darkcolor=p.BORDER, insertcolor=p.FG, padding=3, font="VT.Base")
        s.map("TCombobox",
              fieldbackground=[("readonly", p.FIELD)],
              foreground=[("readonly", p.FG)],
              selectbackground=[("readonly", p.FIELD)],
              selectforeground=[("readonly", p.FG)],
              arrowcolor=[("active", p.FG)])
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar",
                        background=p.BTN, troughcolor=p.SURFACE, bordercolor=p.SURFACE,
                        arrowcolor=p.FG2, lightcolor=p.BTN, darkcolor=p.BTN, gripcount=0)
            s.map(f"{orient}.TScrollbar", background=[("active", p.BORDER)])
        s.configure("Horizontal.TScale",
                    background=p.ACC, troughcolor=p.BORDER, bordercolor=p.SURFACE,
                    lightcolor=p.ACC, darkcolor=p.ACC, sliderlength=14, sliderthickness=14)
        s.configure("Horizontal.TProgressbar",
                    background=p.ACC, troughcolor=p.BORDER, bordercolor=p.BORDER,
                    lightcolor=p.ACC, darkcolor=p.ACC)
        s.configure("Treeview",
                    background=p.FIELD, fieldbackground=p.FIELD, foreground=p.FG,
                    bordercolor=p.BORDER, font="VT.Base",
                    rowheight=max(18, int(round(22 * scale))))
        s.configure("Treeview.Heading",
                    background=p.BTN, foreground=p.FG, bordercolor=p.BORDER,
                    font="VT.Bold", relief="flat")
        s.map("Treeview", background=[("selected", p.SEL)], foreground=[("selected", p.FG)])
        s.map("Treeview.Heading", background=[("active", p.BORDER)])
        # The combobox drop-down list is a plain Listbox created lazily by Tk;
        # the option database covers lists created after this point.
        self.root.option_add("*TCombobox*Listbox.background", p.FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", p.FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", p.SEL)
        self.root.option_add("*TCombobox*Listbox.selectForeground", p.FG)
        self.root.option_add("*TCombobox*Listbox.font", "VT.Base")

    def _recolor_combobox_popdowns(self, p: Palette) -> None:
        """Restyle the drop-down lists that Tk already created.

        Only existing popdowns are touched: ``ttk::combobox::PopdownWindow``
        would create one for every combobox never opened. Popdowns created
        later read the option database entries set by ``_apply_ttk``.
        """
        stack: list[tk.Misc] = [self.root]
        while stack:
            w = stack.pop()
            if isinstance(w, ttk.Combobox):
                pd = f"{w}.popdown"
                try:
                    if int(w.tk.call("winfo", "exists", pd)):
                        w.tk.call(f"{pd}.f.l", "configure",
                                  "-background", p.FIELD, "-foreground", p.FG,
                                  "-selectbackground", p.SEL, "-selectforeground", p.FG,
                                  "-font", "VT.Base")
                except tk.TclError:
                    pass
            try:
                stack.extend(w.winfo_children())
            except tk.TclError:
                pass
