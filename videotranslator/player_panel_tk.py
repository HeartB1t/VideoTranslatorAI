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
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import libmpv_runtime
from .libmpv_runtime import LibmpvStatus

VIDEO_BG = "#000000"
TEXT_FG = "#a3a3a3"
LOGO_FG = "#c3c3c3"
INSTALL_STATE_KEYS = {
    "installing": "player_installing",
    "ok": "player_install_ok",
    "failed": "player_install_failed",
}
_MIN_WRAP = 200


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


class PlayerPanel(tk.Frame):
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
