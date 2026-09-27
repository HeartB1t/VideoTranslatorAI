"""Tk side of the voice preview: the speaker icon and the hub that owns the player.

``PreviewHub`` wraps one :class:`VoicePreview` for the whole app (one preview
at a time, main window and dialogs alike) and hands its worker callbacks to
the Tk thread through ``post``. ``SpeakerButton`` is the small icon next to a
voice: a speaker when idle, a stop square while the sample loads or plays.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

from .player_panel_tk import HoverTip, icon_shapes
from .voice_preview import VoicePreview

Listener = Callable[[str, str, "str | None"], None]

ERROR_KEYS = {"network": "vp_err_network", "no_sample": "vp_err_no_sample",
              "no_player": "vp_err_no_player", "failed": "vp_err_failed"}


def error_key(kind: str | None) -> str:
    return ERROR_KEYS.get(kind or "", "vp_err_failed")


class PreviewHub:
    """App-wide owner of the preview player; listeners run on the Tk thread."""

    def __init__(self, post: Callable[[Callable[[], None]], None], *,
                 make_preview: Callable[..., Any] = VoicePreview) -> None:
        self._post = post
        self._make_preview = make_preview
        self._preview = None
        self._listeners: list[Listener] = []
        self._labels: dict[str, str] = {}
        self._closed = False

    def _on_state(self, key: str, state: str, kind: str | None) -> None:
        # Worker thread: hand the event to Tk.
        self._post(lambda: self._dispatch(key, state, kind))

    def _dispatch(self, key: str, state: str, kind: str | None) -> None:
        for listener in list(self._listeners):
            try:
                listener(key, state, kind)
            except tk.TclError:              # its widget is gone
                self.remove_listener(listener)

    def add_listener(self, listener: Listener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def label(self, key: str) -> str:
        """The readable name given with the key (a voice name, not its id)."""
        return self._labels.get(key, "")

    def toggle(self, key: str, loader: Callable[[], bytes], *, label: str = "") -> None:
        if self._closed:
            return
        if label:
            self._labels[key] = label
        if self._preview is None:
            self._preview = self._make_preview(self._on_state)
        self._preview.toggle(key, loader)

    def active_key(self) -> str | None:
        return self._preview.active_key() if self._preview is not None else None

    def stop_if(self, prefix: str) -> None:
        """Stop the running preview when its key starts with ``prefix``."""
        key = self.active_key()
        if key is not None and key.startswith(prefix):
            self._preview.stop()

    def close(self, timeout_s: float = 2.0) -> None:
        self._closed = True
        self._listeners.clear()
        if self._preview is not None:
            self._preview.close(timeout_s)


class SpeakerButton:
    """A speaker icon that starts and stops a preview.

    ``on_click`` does the work (it usually calls ``PreviewHub.toggle``);
    ``set_state`` follows the hub: ``loading``/``playing`` draw a stop square,
    ``idle`` the speaker, ``error`` the speaker in the error colour with the
    reason as tooltip until the next click.
    """

    def __init__(self, parent: tk.Misc, *, palette: Any, bg_role: str,
                 ui_s: Callable[[str], str], on_click: Callable[[], None],
                 tip_key: str = "vp_tip_play", scale: float = 1.0) -> None:
        self._palette = palette
        self._bg_role = bg_role
        self._s = ui_s
        self._on_click = on_click
        self._tip_key = tip_key
        self._scale = scale
        self._hovered = False
        self.state = "idle"
        self.error_text = ""
        size = self._size()
        bg = getattr(palette, bg_role)
        self.canvas = tk.Canvas(parent, width=size + 8, height=size + 8, bg=bg, bd=0,
                                highlightthickness=2, highlightbackground=bg,
                                highlightcolor=palette.ACC, takefocus=1, cursor="hand2")
        self.canvas.bind("<Button-1>", lambda _e: self.click())
        for sequence in ("<Return>", "<space>", "<KP_Enter>"):
            self.canvas.bind(sequence, lambda _e: (self.click(), "break")[1])
        self.canvas.bind("<Enter>", lambda _e: self._hover(True), add="+")
        self.canvas.bind("<Leave>", lambda _e: self._hover(False), add="+")
        self._tip = HoverTip(self.canvas, self.tip_text,
                             colors_fn=lambda: (self._palette.BTN, self._palette.FG))
        self.draw()

    def _size(self) -> int:
        return max(14, round(16 * self._scale))

    def tip_text(self) -> str:
        if self.state in ("loading", "playing"):
            return self._s("vp_loading" if self.state == "loading" else "vp_tip_stop")
        if self.state == "error" and self.error_text:
            return self.error_text
        return self._s(self._tip_key)

    def click(self) -> None:
        self.error_text = ""
        if self.state == "error":
            self.set_state("idle")
        self._on_click()

    def set_state(self, state: str, error_text: str = "") -> None:
        self.state = state
        self.error_text = error_text if state == "error" else ""
        self.draw()

    def apply_palette(self, palette: Any, scale: float | None = None) -> None:
        self._palette = palette
        if scale is not None:
            self._scale = scale
        self.draw()

    def _hover(self, inside: bool) -> None:
        self._hovered = inside
        self.draw()

    def draw(self) -> None:
        pal = self._palette
        canvas = self.canvas
        size = self._size()
        bg = pal.BTN if self._hovered else getattr(pal, self._bg_role)
        canvas.configure(width=size + 8, height=size + 8, bg=bg, highlightbackground=bg,
                         highlightcolor=pal.ACC)
        canvas.delete("icon")
        busy = self.state in ("loading", "playing")
        if busy:
            color = pal.ACC if self.state == "playing" else pal.FG2
        else:
            color = pal.ERR if self.state == "error" else pal.FG
        width = max(1, round(1.5 * self._scale))
        for kind, raw in icon_shapes("stop" if busy else "volume", size):
            coords = [value + 4.0 for value in raw]
            if kind == "line":
                canvas.create_line(*coords, fill=color, width=width, capstyle="round",
                                   joinstyle="round", tags="icon")
            elif kind == "rect":
                canvas.create_rectangle(*coords, fill=color, outline=color, tags="icon")
            else:
                canvas.create_polygon(*coords, fill=color, outline=color, tags="icon")
