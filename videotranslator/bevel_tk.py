"""Raised, key-like tk.Buttons that look the same on Linux and Windows.

Tk's ``relief="raised"`` is drawn by each platform in its own way, with
shades derived from the background by fixed rules that on the dark themes
give an edge hard to see. Here two plain frames paint the edge instead:
``outer`` shows on the right and at the bottom (the lower side, thicker at
the bottom: the key's depth) and the inner frame on the top and left (the
upper side). The colours come from ``ui_theme.bevel_colors`` of the face
the button shows right now, so a hover colour, a selected state and a theme
change all repaint it.
"""

from __future__ import annotations

import tkinter as tk
import weakref
from collections.abc import Callable

from .ui_theme import Palette, bevel_colors, bevel_edges

BINDTAG = "VTBevelButton"
# Options whose change alters the face or the state, so the edge.
_PAINT_OPTIONS = frozenset({"bg", "background", "activebackground", "state"})
_live: "weakref.WeakSet[_Bevel]" = weakref.WeakSet()


class _EdgeFrame(tk.Frame):
    """One of the two frames of the edge; knows when it is going away."""

    dying = False

    def destroy(self) -> None:
        self.dying = True
        super().destroy()


class _Bevel:
    """Mixin that draws a Tk button-like widget as a raised key.

    Geometry calls (pack, grid, place, their forget and info) act on
    ``outer``, the frame that carries the edge, so a call site places it
    like any button. ``set_selected(True)`` keeps the key sunk (a chosen
    profile or voice). ``primary`` picks the keyboard focus ring: FG around
    an accent-filled key, the accent around the others.
    """

    def __init__(self, parent: tk.Misc, *, palette_fn: Callable[[], Palette],
                 scale_fn: Callable[[], float] | None = None, primary: bool = False,
                 **options) -> None:
        self._ready = False
        self._palette_fn = palette_fn
        self._scale_fn = scale_fn or (lambda: 1.0)
        self._primary = primary
        self._hovered = self._pressed = self._focused = self._selected = False
        self._edges: tuple[int, int] | None = None
        self.outer = _EdgeFrame(parent, bd=0, highlightthickness=0)
        self._inner = _EdgeFrame(self.outer, bd=0, highlightthickness=0)
        for name, value in (("relief", "flat"), ("bd", 0), ("highlightthickness", 0)):
            options.setdefault(name, value)
        super().__init__(self._inner, **options)
        tags = self.bindtags()
        self.bindtags((tags[0], BINDTAG) + tags[1:])
        _bind_class(self)
        _live.add(self)
        self._ready = True
        self.repaint()

    # -- state -------------------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.repaint()

    def _set(self, **flags: bool) -> None:
        for name, value in flags.items():
            setattr(self, name, value)
        self.repaint()

    def configure(self, cnf=None, **kw):
        result = super().configure(cnf, **kw)
        keys = set(kw) | (set(cnf) if isinstance(cnf, dict) else set())
        if self._ready and keys & _PAINT_OPTIONS:
            self.repaint()
        return result

    config = configure

    def repaint(self) -> None:
        """Paint the edge for the current face, state and theme."""
        if not self._ready:
            return
        try:
            palette = self._palette_fn()
            self._layout(palette)
            if self._focused:
                ring = palette.FG if self._primary else palette.ACC
                self.outer.configure(bg=ring)
                self._inner.configure(bg=ring)
                return
            enabled = str(self.cget("state")) != "disabled"
            option = "activebackground" if self._hovered and enabled else "bg"
            colors = bevel_colors(_hex(self, self.cget(option)), enabled=enabled,
                                  pressed=self._selected or (self._pressed and enabled))
            self.outer.configure(bg=colors.bottom_right)
            self._inner.configure(bg=colors.top_left)
        except tk.TclError:
            pass                                  # already destroyed

    def _layout(self, palette: Palette) -> None:
        edges = bevel_edges(palette, self._scale_fn())
        if edges == self._edges:
            return
        self._edges = edge, depth = edges
        self._inner.pack(fill="both", expand=True, padx=(0, edge), pady=(0, depth))
        tk.Pack.pack_configure(self, fill="both", expand=True, padx=(edge, 0), pady=(edge, 0))

    def destroy(self) -> None:
        _live.discard(self)
        outer = self.outer
        super().destroy()
        if not outer.dying:
            outer.destroy()

    # -- geometry acts on the edge, so call sites place the whole key --------

    def pack_configure(self, cnf=None, **kw):
        return self.outer.pack_configure(cnf or {}, **kw)

    pack = pack_configure

    def pack_forget(self) -> None:
        self.outer.pack_forget()

    forget = pack_forget

    def pack_info(self):
        return self.outer.pack_info()

    info = pack_info

    def grid_configure(self, cnf=None, **kw):
        return self.outer.grid_configure(cnf or {}, **kw)

    grid = grid_configure

    def grid_forget(self) -> None:
        self.outer.grid_forget()

    def grid_remove(self) -> None:
        self.outer.grid_remove()

    def grid_info(self):
        return self.outer.grid_info()

    def place_configure(self, cnf=None, **kw):
        return self.outer.place_configure(cnf or {}, **kw)

    place = place_configure

    def place_forget(self) -> None:
        self.outer.place_forget()

    def place_info(self):
        return self.outer.place_info()


class BevelButton(_Bevel, tk.Button):
    """A tk.Button drawn as a raised key (see ``_Bevel``)."""


class BevelRadiobutton(_Bevel, tk.Radiobutton):
    """A push-style tk.Radiobutton (``indicatoron=False``) drawn as a raised
    key; the caller marks the chosen one with ``set_selected``."""


def repaint_all() -> None:
    """Repaint every live key: call it after a theme change."""
    for button in list(_live):
        button.repaint()


def _hex(widget: tk.Misc, value) -> str:
    text = str(value)
    if text.startswith("#") and len(text) == 7:
        return text.lower()
    r, g, b = widget.winfo_rgb(text)
    return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)


def _flag(**flags: bool):
    def handler(event):
        if isinstance(event.widget, _Bevel):
            event.widget._set(**flags)
    return handler


def _press(event):
    button = event.widget
    if isinstance(button, _Bevel) and str(button.cget("state")) != "disabled":
        button._set(_pressed=True)


_HANDLERS = {
    "<Enter>": _flag(_hovered=True),
    "<Leave>": _flag(_hovered=False, _pressed=False),
    "<ButtonPress-1>": _press,
    "<ButtonRelease-1>": _flag(_pressed=False),
    "<FocusIn>": _flag(_focused=True),
    "<FocusOut>": _flag(_focused=False),
}


def _bind_class(widget: tk.Misc) -> None:
    """Bind the key events once per Tk interpreter, on the root: a binding
    registered through a button would die with that button."""
    root = widget._root()
    if getattr(root, "_vt_bevel_bound", False):
        return
    root._vt_bevel_bound = True
    for sequence, handler in _HANDLERS.items():
        root.bind_class(BINDTAG, sequence, handler)
