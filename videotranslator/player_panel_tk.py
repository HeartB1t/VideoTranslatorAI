"""Tk glue of the integrated player pane (spec 2.3).

P1 builds the video host and the placeholder that explains the player
status: the logo, a title and the reason when the player is unavailable (or
the "ready" line with the credits), the install state and an Install
button. P2 adds the seek bar, the controls, the theme hook and playback.

Only colours reserved in ui_theme.TK_DEFAULT_COLORS are used here (#000000,
#a3a3a3, #c3c3c3), so the live recolour walk never remaps them; the Install
button comes from the GUI's own button factory and follows the theme
through that walk.
"""

from __future__ import annotations

import sys
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from tkinter import ttk

from . import libmpv_runtime
from .libmpv_runtime import LibmpvStatus
from .player_core import (
    STATUS_KEYS,
    MediaItem,
    PlayerState,
    controls_visible,
    format_clock,
    playlist_groups,
    x_to_seconds,
)
from .ui_theme import resolve_palette

VIDEO_BG = "#000000"
TEXT_FG = "#a3a3a3"
LOGO_FG = "#c3c3c3"
INSTALL_STATE_KEYS = {
    "installing": "player_installing",
    "ok": "player_install_ok",
    "failed": "player_install_failed",
}
_MIN_WRAP = 200


_ICON_UNITS: dict[str, tuple[tuple[str, tuple[float, ...]], ...]] = {
    "previous": (("rect", (0.12, 0.16, 0.24, 0.84)),
                 ("poly", (0.82, 0.14, 0.30, 0.50, 0.82, 0.86))),
    "back": (("poly", (0.82, 0.14, 0.30, 0.50, 0.82, 0.86)),),
    "stop": (("rect", (0.18, 0.18, 0.82, 0.82)),),
    "play": (("poly", (0.24, 0.12, 0.24, 0.88, 0.86, 0.50)),),
    "pause": (("rect", (0.20, 0.14, 0.42, 0.86)),
              ("rect", (0.58, 0.14, 0.80, 0.86))),
    "forward": (("poly", (0.18, 0.14, 0.70, 0.50, 0.18, 0.86)),),
    "next": (("poly", (0.18, 0.14, 0.70, 0.50, 0.18, 0.86)),
             ("rect", (0.76, 0.16, 0.88, 0.84))),
    "snapshot": (("rect", (0.08, 0.25, 0.92, 0.82)),
                 ("rect", (0.28, 0.13, 0.58, 0.28)),
                 ("oval", (0.34, 0.34, 0.70, 0.70))),
    "open_folder": (("poly", (0.06, 0.28, 0.42, 0.28, 0.52, 0.40,
                                0.94, 0.40, 0.82, 0.82, 0.08, 0.82)),),
    "volume": (("poly", (0.08, 0.38, 0.34, 0.38, 0.58, 0.16,
                           0.58, 0.84, 0.34, 0.62, 0.08, 0.62)),
               ("line", (0.68, 0.34, 0.86, 0.50, 0.68, 0.66))),
    "muted": (("poly", (0.08, 0.38, 0.34, 0.38, 0.58, 0.16,
                          0.58, 0.84, 0.34, 0.62, 0.08, 0.62)),
              ("line", (0.68, 0.34, 0.90, 0.66)),
              ("line", (0.90, 0.34, 0.68, 0.66))),
    "fullscreen": (("line", (0.08, 0.38, 0.08, 0.08, 0.38, 0.08)),
                   ("line", (0.62, 0.08, 0.92, 0.08, 0.92, 0.38)),
                   ("line", (0.92, 0.62, 0.92, 0.92, 0.62, 0.92)),
                   ("line", (0.38, 0.92, 0.08, 0.92, 0.08, 0.62))),
    "exit_fullscreen": (("line", (0.08, 0.38, 0.38, 0.38, 0.38, 0.08)),
                        ("line", (0.62, 0.08, 0.62, 0.38, 0.92, 0.38)),
                        ("line", (0.92, 0.62, 0.62, 0.62, 0.62, 0.92)),
                        ("line", (0.38, 0.92, 0.38, 0.62, 0.08, 0.62))),
}


def icon_shapes(name: str, size: int) -> list[tuple[str, list[float]]]:
    """Return scalable Canvas primitives for one transport icon."""
    if name not in _ICON_UNITS:
        raise ValueError(f"unknown player icon: {name!r}")
    extent = max(1, int(size))
    return [(kind, [round(value * extent, 3) for value in coords])
            for kind, coords in _ICON_UNITS[name]]


class HoverTip:
    """A small borderless window that shows text while the pointer rests on a widget.

    The text and the colours are read when the tip opens, so they follow
    language and theme changes without a refresh call.
    """

    def __init__(self, widget: tk.Misc, text_fn: Callable[[], str], *,
                 colors_fn: Callable[[], tuple[str, str]], delay_ms: int = 500) -> None:
        self._widget = widget
        self._text_fn = text_fn
        self._colors_fn = colors_fn
        self._delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        for target in (widget, *widget.winfo_children()):
            target.bind("<Enter>", self._schedule, add="+")
            target.bind("<Leave>", self.hide, add="+")
            target.bind("<ButtonPress>", self.hide, add="+")

    def _schedule(self, _event: Any = None) -> None:
        self._cancel()
        self._after_id = self._widget.after(self._delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        text = self._text_fn()
        if not text or self._tip is not None:
            return
        bg, fg = self._colors_fn()
        tip = tk.Toplevel(self._widget)
        tip.wm_overrideredirect(True)
        tk.Label(tip, text=text, bg=bg, fg=fg, font="VT.Small", justify="left",
                 wraplength=360, padx=6, pady=4).pack()
        x = self._widget.winfo_rootx()
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip

    def hide(self, _event: Any = None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


class _P1PlayerPanel(tk.Frame):
    """The left pane of the main window: the video host and the status placeholder."""

    def __init__(self, parent: tk.Misc, *, ui_s: Callable[[str], str],
                 make_button: Callable[..., tuple[tk.Widget, tk.Button]],
                 on_command: Callable[[str, dict], None], logo_path: Path | None,
                 sys_platform: str = sys.platform) -> None:
        super().__init__(parent, bg=VIDEO_BG, highlightthickness=0, bd=0)
        self._ui_s = ui_s
        self._on_command = on_command
        self._sys_platform = sys_platform
        self._status: LibmpvStatus | None = None
        self._install_cmd: str | None = None
        self._install_state: str | None = None
        # From P2 on, mpv's child window covers video_host (spec 2.3).
        self.video_host = tk.Frame(self, bg=VIDEO_BG, highlightthickness=0, bd=0)
        self.video_host.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.placeholder = tk.Frame(self, bg=VIDEO_BG, highlightthickness=0, bd=0)
        self.placeholder.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.placeholder.lift()
        box = tk.Frame(self.placeholder, bg=VIDEO_BG)
        box.place(relx=0.5, rely=0.5, anchor="center")
        self._logo_base = self._load_logo(logo_path)
        self._logo_factor = 1
        self._logo_image = None
        if self._logo_base is not None:
            self._logo_factor = 2
            self._logo_image = self._logo_base.subsample(2)
            self.logo: tk.Widget = tk.Label(box, image=self._logo_image, bg=VIDEO_BG, bd=0)
        else:  # spec 2.3 [CC] G28: a canvas play mark when the PNG is missing or unreadable
            self.logo = tk.Canvas(box, width=96, height=96, bg=VIDEO_BG, highlightthickness=0, bd=0)
            self.logo.create_polygon(32, 20, 32, 76, 80, 48, fill=LOGO_FG, outline="")
        self.logo.pack(pady=(0, 12))
        self.title_label = tk.Label(box, text="", bg=VIDEO_BG, fg=LOGO_FG, font="VT.Bold")
        self.title_label.pack()
        self.message_label = tk.Label(box, text="", bg=VIDEO_BG, fg=TEXT_FG, font="VT.Base",
                                      justify="center", wraplength=360)
        self.message_label.pack(pady=(6, 0))
        self.install_label = tk.Label(box, text="", bg=VIDEO_BG, fg=TEXT_FG, font="VT.Small",
                                      justify="center", wraplength=360)
        self.install_label.pack(pady=(4, 0))
        self._install_wrap, self.install_button = make_button(
            box, primary=True, text=ui_s("player_install_btn"), command=self._request_install)
        self.bind("<Configure>", self._on_resize)
        self._render()

    # -- public API ---------------------------------------------------------

    def show_unavailable(self, status: LibmpvStatus, *, install_cmd: str | None) -> None:
        self._status = status
        self._install_cmd = install_cmd
        self._render()

    def show_ready(self, status: LibmpvStatus) -> None:
        self._status = status
        self._install_cmd = None
        self._render()

    def show_install_progress(self, state: str | None) -> None:
        """``state``: "installing", "ok", "failed" or None (no install line)."""
        self._install_state = state
        self._render()

    def relabel(self) -> None:
        """Called by App._apply_lang after a language switch."""
        self._render()

    def status_text(self) -> str:
        """The translated status: the placeholder message and the badge tooltip."""
        status = self._status
        if status is None:
            return self._ui_s("player_badge")
        key, params = libmpv_runtime.status_message(
            status, sys_platform=self._sys_platform, install_cmd=self._install_cmd)
        text = self._ui_s(key).format(**params)
        if status.ok:
            licence = status.build.get("licence") or self._ui_s("player_license_system")
            text += "\n" + self._ui_s("player_credits").format(license=licence)
        return text

    # -- internals ----------------------------------------------------------

    def _load_logo(self, path: Path | None) -> tk.PhotoImage | None:
        if path is None:
            return None
        try:
            return tk.PhotoImage(master=self, file=str(path))
        except (tk.TclError, OSError):
            return None

    def _request_install(self) -> None:
        self._on_command("install", {})

    def _on_resize(self, event: Any) -> None:
        wrap = max(_MIN_WRAP, event.width - 48)
        self.message_label.configure(wraplength=wrap)
        self.install_label.configure(wraplength=wrap)
        if self._logo_base is None:
            return
        limit = max(32, event.height // 3)   # the logo takes at most a third of the pane
        factor = max(1, -(-self._logo_base.height() // limit))
        if factor != self._logo_factor:
            self._logo_factor = factor
            self._logo_image = self._logo_base.subsample(factor)
            self.logo.configure(image=self._logo_image)

    def _render(self) -> None:
        status = self._status
        if status is None:
            title, message = "", ""
        elif status.ok:
            title, message = "", self.status_text()
        else:
            title, message = self._ui_s("player_unavailable_title"), self.status_text()
        self.title_label.configure(text=title)
        self.message_label.configure(text=message)
        state_key = INSTALL_STATE_KEYS.get(self._install_state or "")
        self.install_label.configure(text=self._ui_s(state_key) if state_key else "")
        self.install_button.configure(text=self._ui_s("player_install_btn"))
        show = (status is not None and not status.ok and self._install_state != "installing"
                and libmpv_runtime.offers_install(status, sys_platform=self._sys_platform))
        if show and not self._install_wrap.winfo_manager():
            self._install_wrap.pack(pady=(10, 0))
        elif not show and self._install_wrap.winfo_manager():
            self._install_wrap.pack_forget()


class PlayerPanel(_P1PlayerPanel):
    """Video surface plus file-player controls that emit controller intents."""

    _CONTROL_ORDER = (
        "previous", "back", "stop", "play_pause", "forward", "next",
        "snapshot", "open_folder", "spacer", "volume", "volume_scale", "fullscreen",
    )
    _ACTIONS = {
        "previous": "previous", "back": "back_10", "stop": "stop",
        "play_pause": "play_pause", "forward": "forward_10", "next": "next",
        "snapshot": "snapshot", "open_folder": "open_folder", "volume": "mute",
        "fullscreen": "fullscreen",
    }
    _TIP_KEYS = {
        "previous": "player_tip_previous", "back": "player_tip_rewind",
        "stop": "player_tip_stop", "forward": "player_tip_forward",
        "next": "player_tip_next", "snapshot": "player_tip_snapshot",
        "open_folder": "player_tip_open_folder", "volume": "player_tip_volume",
    }

    def __init__(self, parent: tk.Misc, *, ui_s: Callable[[str], str],
                 make_button: Callable[..., tuple[tk.Widget, tk.Button]],
                 on_command: Callable[[str, dict], None], logo_path: Path | None,
                 sys_platform: str = sys.platform, theme=None,
                 keyboard_operable: Callable[[tk.Widget, Callable], None] | None = None,
                 log: Callable[[str], None] | None = None) -> None:
        self._theme = theme or SimpleNamespace(
            palette=resolve_palette("graphite", "default"), scale=1.0,
        )
        self._keyboard_operable = keyboard_operable or self._bind_keyboard
        self._log = log or (lambda _message: None)
        self._state: PlayerState | None = None
        self._position: float | None = None
        self._live_range = (None, None, None)
        self._dragging = False
        self._last_drag_seek = 0.0
        self._notice: tuple[str, dict] | None = None
        self._notice_after: str | None = None
        self._playlist_popup: tk.Toplevel | None = None
        self._playlist_tip: HoverTip | None = None
        self._playlist_rows: dict[int, MediaItem | None] = {}
        self.fullscreen = False
        self.placeholder_visible = True
        self._rendering_volume = False
        self._tips: list[HoverTip] = []
        super().__init__(
            parent, ui_s=ui_s, make_button=make_button, on_command=on_command,
            logo_path=logo_path, sys_platform=sys_platform,
        )
        self._build_controls()
        self.bind("<Configure>", self._on_panel_resize, add="+")
        self.apply_theme()
        self._layout_video()

    @staticmethod
    def _bind_keyboard(widget: tk.Widget, action: Callable[[], None]) -> None:
        widget.configure(takefocus=1)

        def activate(_event):
            action()
            return "break"

        for sequence in ("<Return>", "<KP_Enter>", "<space>"):
            widget.bind(sequence, activate)

    @property
    def _palette(self):
        return self._theme.palette

    @property
    def _scale(self) -> float:
        return float(getattr(self._theme, "scale", 1.0))

    def _build_controls(self) -> None:
        palette = self._palette
        self.controls_frame = tk.Frame(self, bg=palette.SURFACE, bd=0, highlightthickness=0)
        self.controls_frame.pack(side="bottom", fill="x")

        seek_row = tk.Frame(self.controls_frame, bg=palette.SURFACE)
        seek_row.pack(fill="x", padx=8, pady=(6, 2))
        self.elapsed_label = tk.Label(
            seek_row, text="00:00", bg=palette.SURFACE, fg=palette.FG2, font="VT.Mono",
        )
        self.elapsed_label.pack(side="left")
        self.seek_canvas = tk.Canvas(
            seek_row, width=180, height=14, bg=palette.SURFACE, bd=0,
            highlightthickness=2, highlightbackground=palette.SURFACE,
            highlightcolor=palette.ACC, takefocus=1,
        )
        self.seek_canvas.pack(side="left", fill="x", expand=True, padx=6)
        self.duration_label = tk.Label(
            seek_row, text="--:--", bg=palette.SURFACE, fg=palette.FG2, font="VT.Mono",
        )
        self.duration_label.pack(side="left")
        self.seek_canvas.bind("<Button-1>", self._seek_press)
        self.seek_canvas.bind("<B1-Motion>", self._seek_motion)
        self.seek_canvas.bind("<ButtonRelease-1>", self._seek_release)
        self.seek_canvas.bind("<Left>", lambda _event: self._seek_key("back_10"))
        self.seek_canvas.bind("<Right>", lambda _event: self._seek_key("forward_10"))
        self.seek_canvas.bind("<Home>", lambda _event: self._seek_edge(0.0))
        self.seek_canvas.bind("<End>", lambda _event: self._seek_edge(self._duration()))
        self.seek_canvas.bind("<Configure>", lambda _event: self._draw_seek())

        info = tk.Frame(self.controls_frame, bg=palette.SURFACE)
        info.pack(fill="x", padx=8, pady=2)
        self.now_playing_label = tk.Label(
            info, text=self._ui_s("player_nothing_loaded"), anchor="w",
            bg=palette.SURFACE, fg=palette.FG2, font="VT.Small", width=1,
        )
        self.now_playing_label.pack(side="left", fill="x", expand=True)
        self.playlist_button = tk.Button(
            info, text=self._ui_s("player_btn_playlist"), command=lambda: self._activate("playlist"),
            relief="flat", bd=0, padx=7, pady=2, font="VT.Small",
            bg=palette.BTN, fg=palette.FG, activebackground=palette.ACC_HOVER,
            activeforeground=palette.ACC_FG, highlightthickness=2,
            highlightbackground=palette.SURFACE, highlightcolor=palette.ACC,
        )
        self.playlist_button.pack(side="right", padx=(6, 0))
        self._keyboard_operable(self.playlist_button, lambda: self._activate("playlist"))
        self._tips.append(HoverTip(
            self.playlist_button, lambda: self._ui_s("player_btn_playlist"),
            colors_fn=self._tip_colors,
        ))

        self.transport_row = tk.Frame(self.controls_frame, bg=palette.SURFACE)
        self.transport_row.pack(fill="x", padx=6, pady=(2, 6))
        self._icon_controls: dict[str, tk.Canvas] = {}
        self._transport_widgets: dict[str, tk.Widget] = {}
        for name in ("previous", "back", "stop", "play_pause", "forward", "next",
                     "snapshot", "open_folder"):
            self._transport_widgets[name] = self._make_icon_control(name)
        self._transport_widgets["spacer"] = tk.Frame(self.transport_row, bg=palette.SURFACE)
        self._transport_widgets["volume"] = self._make_icon_control("volume")
        self.volume_scale = ttk.Scale(
            self.transport_row, from_=0, to=130, orient="horizontal",
            command=self._on_volume, takefocus=1, length=100,
        )
        self._transport_widgets["volume_scale"] = self.volume_scale
        self._tips.append(HoverTip(
            self.volume_scale, lambda: self._ui_s("player_tip_volume"),
            colors_fn=self._tip_colors,
        ))
        self._transport_widgets["fullscreen"] = self._make_icon_control("fullscreen")
        self._apply_reflow(700)
        self._draw_seek()

    def _make_icon_control(self, name: str) -> tk.Canvas:
        palette = self._palette
        extent = max(14, round(16 * self._scale))
        canvas = tk.Canvas(
            self.transport_row, width=extent + 8, height=extent + 8,
            bg=palette.SURFACE, bd=0, highlightthickness=2,
            highlightbackground=palette.SURFACE, highlightcolor=palette.ACC,
            takefocus=1, cursor="hand2",
        )
        action = self._ACTIONS[name]
        canvas.bind("<Button-1>", lambda _event, value=action: self._activate(value))
        self._keyboard_operable(canvas, lambda value=action: self._activate(value))
        self._icon_controls[name] = canvas
        self._tips.append(HoverTip(
            canvas, lambda value=name: self._tip_text(value), colors_fn=self._tip_colors,
        ))
        return canvas

    def _tip_colors(self) -> tuple[str, str]:
        return self._palette.BTN, self._palette.FG

    def _tip_text(self, name: str) -> str:
        if name == "play_pause":
            key = "player_tip_pause" if self._state and self._state.status == "playing" else "player_tip_play"
        elif name == "volume":
            key = "player_tip_unmute" if self._state and self._state.muted else "player_tip_mute"
        elif name == "fullscreen":
            key = "player_tip_exit_fullscreen" if self.fullscreen else "player_tip_fullscreen"
        else:
            key = self._TIP_KEYS[name]
        return self._ui_s(key)

    def _icon_name(self, control: str) -> str:
        if control == "play_pause":
            return "pause" if self._state and self._state.status == "playing" else "play"
        if control == "volume":
            return "muted" if self._state and self._state.muted else "volume"
        if control == "fullscreen":
            return "exit_fullscreen" if self.fullscreen else "fullscreen"
        return control

    def _draw_icon(self, control: str) -> None:
        canvas = self._icon_controls[control]
        canvas.delete("icon")
        size = max(14, round(16 * self._scale))
        canvas.configure(width=size + 8, height=size + 8)
        offset = 4.0
        color = self._palette.FG
        for kind, raw in icon_shapes(self._icon_name(control), size):
            coords = [value + offset for value in raw]
            if kind == "line":
                canvas.create_line(*coords, fill=color, width=max(1, round(1.5 * self._scale)),
                                   capstyle="round", joinstyle="round", tags="icon")
            elif kind == "rect":
                canvas.create_rectangle(*coords, fill=color, outline=color, tags="icon")
            elif kind == "oval":
                canvas.create_oval(*coords, fill="", outline=color,
                                   width=max(1, round(1.5 * self._scale)), tags="icon")
            else:
                canvas.create_polygon(*coords, fill=color, outline=color, tags="icon")

    def _redraw_icons(self) -> None:
        for name in self._icon_controls:
            self._draw_icon(name)

    def _activate(self, action: str, **args: object) -> None:
        self._on_command(action, dict(args))

    def _on_volume(self, value: str) -> None:
        if not self._rendering_volume:
            self._activate("volume", value=round(float(value)))

    def _duration(self) -> float:
        if self._state is None or self._state.duration is None:
            return 0.0
        return max(0.0, float(self._state.duration))

    def _seek_width(self) -> int:
        width = self.seek_canvas.winfo_width()
        return width if width > 2 else int(self.seek_canvas.cget("width"))

    def _seek_value(self, x: float) -> float | None:
        duration = self._duration()
        if duration <= 0:
            return None
        return x_to_seconds(float(x), float(self._seek_width()), 0.0, duration)

    def _send_seek(self, x: float, *, dragging: bool) -> None:
        seconds = self._seek_value(x)
        if seconds is not None:
            self._position = seconds
            self._draw_seek()
            self._activate("seek", seconds=seconds, dragging=dragging)

    def _seek_press(self, event: Any) -> str:
        self._dragging = True
        self._last_drag_seek = time.monotonic()
        self._send_seek(event.x, dragging=True)
        return "break"

    def _seek_motion(self, event: Any) -> str:
        now = time.monotonic()
        if self._dragging and now - self._last_drag_seek >= 0.1:
            self._last_drag_seek = now
            self._send_seek(event.x, dragging=True)
        return "break"

    def _seek_release(self, event: Any) -> str:
        self._send_seek(event.x, dragging=False)
        self._dragging = False
        return "break"

    def _seek_key(self, action: str) -> str:
        self._activate(action)
        return "break"

    def _seek_edge(self, seconds: float) -> str:
        self._activate("seek", seconds=seconds, dragging=False)
        return "break"

    def _draw_seek(self) -> None:
        canvas = self.seek_canvas
        canvas.delete("all")
        width = self._seek_width()
        y = max(5, int(canvas.cget("height")) // 2)
        palette = self._palette
        canvas.create_line(2, y, max(2, width - 2), y, fill=palette.BORDER, width=3,
                           capstyle="round", tags="trough")
        duration = self._duration()
        position = max(0.0, float(self._position or 0.0))
        x = 2.0 if duration <= 0 else 2.0 + min(position / duration, 1.0) * max(0, width - 4)
        canvas.create_line(2, y, x, y, fill=palette.ACC, width=3,
                           capstyle="round", tags="played")
        start, played, edge = self._live_range
        if start is not None and edge is not None and edge > start:
            px0 = 2.0
            px1 = max(2.0, width - 2.0)
            canvas.create_line(px0, y + 4, px1, y + 4, fill=palette.WARN, width=2,
                               tags="live-range")
            if played is not None:
                live_x = px0 + min(max((played - start) / (edge - start), 0.0), 1.0) * (px1 - px0)
                canvas.create_oval(live_x - 2, y + 2, live_x + 2, y + 6,
                                   fill=palette.WARN, outline=palette.WARN, tags="live-played")
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=palette.FG,
                           outline=palette.FG, tags="knob")

    def _show_placeholder(self, visible: bool) -> None:
        self.placeholder_visible = bool(visible)
        if visible:
            self.placeholder.lift()
        else:
            self.placeholder.lower(self.video_host)
        self.controls_frame.lift()

    def render(self, state: PlayerState, *, position: float | None) -> None:
        self._state = state
        if not self._dragging:
            self._position = position
        hours = bool(state.duration is not None and state.duration >= 3600)
        self.elapsed_label.configure(text=format_clock(self._position, hours=hours))
        self.duration_label.configure(text=format_clock(state.duration, hours=hours))
        self._rendering_volume = True
        try:
            self.volume_scale.set(state.volume)
        finally:
            self._rendering_volume = False
        self._render_now_playing()
        if state.status in ("playing", "paused", "live") and state.item is not None:
            self._show_placeholder(False)
        else:
            key = state.message_key
            if key in STATUS_KEYS:
                key = STATUS_KEYS[key]
            if not key:
                if state.status == "initializing":
                    key = "player_initializing"
                elif state.status == "error":
                    key = "player_err_load"
                else:
                    key = "player_idle_hint" if state.item is None else "player_initializing"
            params = dict(state.message_params)
            if key == "player_err_load" and "name" not in params:
                params["name"] = state.item.title if state.item else ""
            self.title_label.configure(text="")
            self.message_label.configure(text=self._ui_s(key).format(**params))
            self.install_label.configure(text="")
            if self._install_wrap.winfo_manager():
                self._install_wrap.pack_forget()
            self._show_placeholder(True)
        self._redraw_icons()
        if not self._dragging:
            self._draw_seek()

    def _render_now_playing(self) -> None:
        if self._notice is not None:
            key, params = self._notice
            text = self._ui_s(key).format(**params)
        elif self._state is not None and self._state.item is not None:
            text = self._ui_s("player_now_playing").format(name=self._state.item.title)
        else:
            text = self._ui_s("player_nothing_loaded")
        self.now_playing_label.configure(text=text)

    def notify(self, key: str, params: dict, *, seconds: float = 4.0) -> None:
        if self._notice_after is not None:
            try:
                self.after_cancel(self._notice_after)
            except tk.TclError:
                pass
        self._notice = (key, dict(params))
        self._render_now_playing()

        def restore() -> None:
            self._notice_after = None
            self._notice = None
            self._render_now_playing()

        self._notice_after = self.after(max(1, round(float(seconds) * 1000)), restore)

    def render_live_range(self, start: float | None, played: float | None,
                          edge: float | None) -> None:
        self._live_range = (start, played, edge)
        self._draw_seek()

    def show_unavailable(self, status: LibmpvStatus, *, install_cmd: str | None) -> None:
        super().show_unavailable(status, install_cmd=install_cmd)
        self._show_placeholder(True)

    def show_ready(self, status: LibmpvStatus) -> None:
        super().show_ready(status)
        self._show_placeholder(True)

    def host_wid(self) -> int:
        self.update_idletasks()
        value = int(self.video_host.winfo_id())
        return value & 0xFFFFFFFF if self._sys_platform == "win32" else value

    def relabel(self) -> None:
        super().relabel()
        self.playlist_button.configure(text=self._ui_s("player_btn_playlist"))
        if self._state is not None:
            self.render(self._state, position=self._position)
        else:
            self._render_now_playing()

    def apply_theme(self) -> None:
        palette = self._palette
        for frame in (self.controls_frame, self.transport_row):
            frame.configure(bg=palette.SURFACE)
        for child in self.controls_frame.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=palette.SURFACE)
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, (tk.Frame, tk.Label, tk.Canvas)):
                        options = {"bg": palette.SURFACE}
                        if isinstance(grandchild, tk.Label):
                            options["fg"] = palette.FG2
                        grandchild.configure(**options)
        for canvas in self._icon_controls.values():
            canvas.configure(bg=palette.SURFACE, highlightbackground=palette.SURFACE,
                             highlightcolor=palette.ACC)
        self.seek_canvas.configure(bg=palette.SURFACE,
                                   highlightbackground=palette.SURFACE,
                                   highlightcolor=palette.ACC)
        self.playlist_button.configure(
            bg=palette.BTN, fg=palette.FG, activebackground=palette.ACC_HOVER,
            activeforeground=palette.ACC_FG, highlightbackground=palette.SURFACE,
            highlightcolor=palette.ACC,
        )
        self.now_playing_label.configure(bg=palette.SURFACE, fg=palette.FG2)
        self.elapsed_label.configure(bg=palette.SURFACE, fg=palette.FG2)
        self.duration_label.configure(bg=palette.SURFACE, fg=palette.FG2)
        self._redraw_icons()
        self._draw_seek()

    def set_fullscreen_layout(self, on: bool) -> None:
        self.fullscreen = bool(on)
        self._draw_icon("fullscreen")

    def _layout_video(self) -> None:
        reserved = max(1, self.controls_frame.winfo_reqheight())
        for widget in (self.video_host, self.placeholder):
            widget.place_configure(relx=0, rely=0, relwidth=1, relheight=1, height=-reserved)
        self.controls_frame.lift()

    def _on_panel_resize(self, event: Any) -> None:
        self._layout_video()
        self._apply_reflow(event.width)

    def _apply_reflow(self, width: int) -> None:
        visible = controls_visible(int(width), self._scale)
        for widget in self._transport_widgets.values():
            widget.pack_forget()
        for name in self._CONTROL_ORDER:
            if name in ("back", "forward", "snapshot", "open_folder") and name not in visible:
                continue
            widget = self._transport_widgets[name]
            if name == "spacer":
                widget.pack(side="left", fill="x", expand=True)
            elif name == "volume_scale":
                widget.pack(side="left", padx=(0, 4))
            else:
                widget.pack(side="left", padx=1)
        self._layout_video()

    def show_playlist(self, sources: list[MediaItem], results: list[MediaItem], *,
                      job_running: bool) -> tk.Toplevel:
        if self._playlist_popup is not None:
            try:
                self._playlist_popup.destroy()
            except tk.TclError:
                pass
        palette = self._palette
        popup = tk.Toplevel(self)
        popup.transient(self.winfo_toplevel())
        popup.title(self._ui_s("player_btn_playlist"))
        popup.configure(bg=palette.SURFACE)
        listing = tk.Listbox(
            popup, width=38, height=10, exportselection=False,
            bg=palette.FIELD, fg=palette.FG, selectbackground=palette.SEL,
            selectforeground=palette.FG, relief="flat", bd=0,
            highlightthickness=1, highlightbackground=palette.BORDER,
            highlightcolor=palette.ACC, font="VT.Base",
        )
        listing.pack(fill="both", expand=True, padx=8, pady=8)
        self._playlist_rows = {}
        row = 0
        item_count = 0
        for key, items, enabled in playlist_groups(sources, results, job_running=job_running):
            listing.insert("end", self._ui_s(key))
            listing.itemconfigure(row, foreground=palette.FG2, selectbackground=palette.FIELD)
            self._playlist_rows[row] = None
            row += 1
            for item in items:
                listing.insert("end", f"  {item.title}")
                self._playlist_rows[row] = item if enabled else None
                if not enabled:
                    listing.itemconfigure(row, foreground=palette.FG2)
                row += 1
                item_count += 1
        if item_count == 0:
            listing.insert("end", self._ui_s("player_playlist_empty"))
            self._playlist_rows[row] = None
        listing.bind("<Double-Button-1>", lambda _event: self._choose_playlist_item())
        listing.bind("<Return>", lambda _event: self._choose_playlist_item())
        popup.bind("<Escape>", lambda _event: popup.destroy())
        popup.bind("<FocusOut>", lambda _event: popup.after_idle(self._close_playlist_if_unfocused))
        self._playlist_popup = popup
        self._playlist_list = listing
        if job_running:
            self._playlist_tip = HoverTip(
                listing, lambda: self._ui_s("player_tip_results_busy"),
                colors_fn=self._tip_colors,
            )
        listing.focus_set()
        return popup

    def _close_playlist_if_unfocused(self) -> None:
        popup = self._playlist_popup
        if popup is None:
            return
        try:
            focus = popup.focus_get()
            if focus is None or not str(focus).startswith(str(popup)):
                popup.destroy()
                self._playlist_popup = None
        except tk.TclError:
            self._playlist_popup = None

    def _choose_playlist_item(self) -> str:
        try:
            selected = self._playlist_list.curselection()
        except (AttributeError, tk.TclError):
            return "break"
        if not selected:
            return "break"
        item = self._playlist_rows.get(int(selected[0]))
        if item is None:
            return "break"
        self._activate("load_item", item=item)
        if self._playlist_popup is not None:
            self._playlist_popup.destroy()
            self._playlist_popup = None
        return "break"
