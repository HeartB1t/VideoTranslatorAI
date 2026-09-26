"""Tk glue of the live-translation bar (spec 2.3, 4.2, 5.9).

A fixed-height strip under the player pane with two mutually exclusive rows:
an IDLE row (mode / delay / engine / dubbed / subtitles / privacy tip / Start)
shown when a session can be started, and a RUNNING row (status text, LIVE badge,
behind-live readout, Stop) shown while a session runs, plus a one-line banner for
warnings and info.

Like ``player_panel_tk.PlayerPanel`` this widget owns no globals: the App injects
``ui_s`` (i18n), ``make_button`` (button factory), ``on_command`` (the single
intent bus) and ``theme`` (``.palette`` / ``.scale``). Status text is rendered
from the ``live_health`` code maps, so no status string is hard-coded here.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from .live_health import ERROR_KEYS, STATUS_KEYS, WARN_KEYS
from .player_settings import LIVE_ENGINES
from .ui_theme import resolve_palette

_MODES = ("delayed", "live")
# Explicit full i18n keys (no f-string prefixes, so the literal-key scanner sees
# real keys that exist in all 26 languages).
_MODE_KEYS = {"delayed": "live_mode_delayed", "live": "live_mode_live"}
_ENGINE_KEYS = {
    "marian": "live_engine_marian", "ollama": "live_engine_ollama",
    "google": "live_engine_google", "deepl": "live_engine_deepl",
}
# Delay slider range and default per source kind (design 5.3 / 5.5).
_DELAY_RANGE = {"file": (4.0, 30.0, 8.0), "url": (6.0, 30.0, 12.0)}


class _SafeDict(dict):
    """format_map helper: missing placeholders render as empty, never KeyError."""

    def __missing__(self, key: str) -> str:
        return ""


class LiveBar(tk.Frame):
    """Idle/running control strip for real-time translation."""

    def __init__(self, parent: tk.Misc, *, ui_s: Callable[[str], str],
                 make_button: Callable[..., tuple[tk.Widget, tk.Button]],
                 on_command: Callable[[str, dict], None], theme: Any = None,
                 keyboard_operable: Callable[[tk.Widget, Callable], None] | None = None,
                 log: Callable[[str], None] | None = None) -> None:
        self._theme = theme or SimpleNamespace(
            palette=resolve_palette("graphite", "default"), scale=1.0)
        super().__init__(parent, bg=self._palette.SURFACE, bd=0, highlightthickness=0)
        self._s = ui_s
        self._make_button = make_button
        self._on_command = on_command
        self._keyboard_operable = keyboard_operable or (lambda w, a: None)
        self._log = log or (lambda _m: None)
        self._active = False
        self._source_kind = "file"
        self._banner_key: str | None = None
        self._banner_params: dict = {}
        self._banner_is_error = False

        self._mode_var = tk.StringVar(value="delayed")
        self._delay_var = tk.DoubleVar(value=_DELAY_RANGE["file"][2])
        self._engine_var = tk.StringVar(value="marian")
        self._dub_var = tk.BooleanVar(value=True)
        self._subs_var = tk.BooleanVar(value=True)

        self._build_idle()
        self._build_running()
        self._build_banner()
        self.show_idle()
        self.apply_theme()

    # -- palette helpers ----------------------------------------------------

    @property
    def _palette(self):
        return self._theme.palette

    @property
    def _scale(self) -> float:
        return float(getattr(self._theme, "scale", 1.0))

    def _emit(self, intent: str, **params: object) -> None:
        self._on_command(intent, dict(params))

    # -- construction -------------------------------------------------------

    def _build_idle(self) -> None:
        pal = self._palette
        self._idle = tk.Frame(self, bg=pal.SURFACE)
        row = tk.Frame(self._idle, bg=pal.SURFACE)
        row.pack(fill="x", padx=8, pady=(6, 2))

        self._mode_buttons: dict[str, tk.Radiobutton] = {}
        for mode in _MODES:
            rb = tk.Radiobutton(
                row, text=self._s(_MODE_KEYS[mode]), value=mode,
                variable=self._mode_var, command=self._on_mode,
                bg=pal.SURFACE, fg=pal.FG, selectcolor=pal.FIELD,
                activebackground=pal.SURFACE, activeforeground=pal.FG,
                font="VT.Small", takefocus=1)
            rb.pack(side="left", padx=(0, 6))
            self._mode_buttons[mode] = rb

        self._delay_label = tk.Label(row, text="", bg=pal.SURFACE, fg=pal.FG2,
                                     font="VT.Small")
        self._delay_label.pack(side="left", padx=(8, 4))
        from tkinter import ttk
        lo, hi, default = _DELAY_RANGE[self._source_kind]
        self._delay_scale = ttk.Scale(row, from_=lo, to=hi, orient="horizontal",
                                      length=110, command=self._on_delay)
        self._delay_scale.set(default)
        self._delay_scale.pack(side="left", padx=(0, 8))
        self._render_delay_label()

        row2 = tk.Frame(self._idle, bg=pal.SURFACE)
        row2.pack(fill="x", padx=8, pady=(0, 2))
        self._engine_label = tk.Label(row2, text=self._s("live_label_engine"),
                                      bg=pal.SURFACE, fg=pal.FG2, font="VT.Small")
        self._engine_label.pack(side="left", padx=(0, 6))
        self._engine_combo = ttk.Combobox(
            row2, state="readonly", width=26,
            values=[self._s(_ENGINE_KEYS[code]) for code in LIVE_ENGINES])
        self._engine_combo.current(0)
        self._engine_combo.bind("<<ComboboxSelected>>", self._on_engine)
        self._engine_combo.pack(side="left", padx=(0, 8))

        self._chk_dub = tk.Checkbutton(
            row2, text=self._s("live_opt_dub"), variable=self._dub_var,
            command=self._on_dub, bg=pal.SURFACE, fg=pal.FG, selectcolor=pal.FIELD,
            activebackground=pal.SURFACE, activeforeground=pal.FG, font="VT.Small")
        self._chk_dub.pack(side="left", padx=(0, 4))
        self._chk_subs = tk.Checkbutton(
            row2, text=self._s("live_opt_subs"), variable=self._subs_var,
            command=self._on_subs, bg=pal.SURFACE, fg=pal.FG, selectcolor=pal.FIELD,
            activebackground=pal.SURFACE, activeforeground=pal.FG, font="VT.Small")
        self._chk_subs.pack(side="left", padx=(0, 4))

        row3 = tk.Frame(self._idle, bg=pal.SURFACE)
        row3.pack(fill="x", padx=8, pady=(0, 6))
        self._privacy_label = tk.Label(
            row3, text=self._s("live_tip_privacy"), bg=pal.SURFACE, fg=pal.FG2,
            font="VT.Small", justify="left", wraplength=380, anchor="w")
        self._privacy_label.pack(side="left", fill="x", expand=True)
        self._start_wrap, self._start_button = self._make_button(
            row3, primary=True, text=self._s("player_btn_live"),
            command=lambda: self._emit("start", source=self._source_kind))
        self._start_wrap.pack(side="right", padx=(6, 0))

    def _build_running(self) -> None:
        pal = self._palette
        self._running = tk.Frame(self, bg=pal.SURFACE)
        row = tk.Frame(self._running, bg=pal.SURFACE)
        row.pack(fill="x", padx=8, pady=6)
        self._badge = tk.Label(row, text=self._s("live_badge"), bg=pal.WARN,
                               fg=pal.SURFACE, font="VT.Small", padx=6)
        # packed only for stream sessions (see render)
        self._status_label = tk.Label(row, text="", bg=pal.SURFACE, fg=pal.FG,
                                      font="VT.Small", anchor="w")
        self._status_label.pack(side="left", fill="x", expand=True)
        self._stop_wrap, self._stop_button = self._make_button(
            row, primary=False, text=self._s("live_btn_stop"),
            command=lambda: self._emit("stop"))
        self._stop_wrap.pack(side="right", padx=(6, 0))

    def _build_banner(self) -> None:
        pal = self._palette
        self._banner = tk.Frame(self, bg=pal.FIELD)
        self._banner_label = tk.Label(self._banner, text="", bg=pal.FIELD, fg=pal.FG,
                                      font="VT.Small", justify="left", wraplength=360,
                                      anchor="w")
        self._banner_label.pack(side="left", fill="x", expand=True, padx=8, pady=4)
        self._switch_wrap, self._switch_button = self._make_button(
            self._banner, primary=False, text=self._s("live_btn_switch_marian"),
            command=lambda: self._emit("switch_marian"))
        self._banner_close = tk.Button(
            self._banner, text="✕", command=self._on_banner_close,
            relief="flat", bd=0, padx=6, font="VT.Small",
            bg=pal.FIELD, fg=pal.FG2, activebackground=pal.FIELD,
            activeforeground=pal.FG)
        self._banner_close.pack(side="right", padx=(0, 6))

    # -- intent handlers ----------------------------------------------------

    def _on_mode(self) -> None:
        self._emit("mode", mode=self._mode_var.get())

    def _on_delay(self, _value: str = "") -> None:
        self._render_delay_label()
        self._emit("delay", seconds=round(float(self._delay_scale.get()), 1))

    def _on_engine(self, _event: Any = None) -> None:
        code = LIVE_ENGINES[self._engine_combo.current()]
        self._engine_var.set(code)
        self._emit("engine", engine=code)
        if code in ("google", "deepl"):
            self.show_banner("live_warn_online_engine", {"engine": self._s(_ENGINE_KEYS[code])})

    def _on_dub(self) -> None:
        self._emit("dub", enabled=bool(self._dub_var.get()))

    def _on_subs(self) -> None:
        self._emit("subs", enabled=bool(self._subs_var.get()))

    def _on_banner_close(self) -> None:
        self.clear_banner()
        self._emit("banner_close")

    # -- public API ---------------------------------------------------------

    def set_source_kind(self, kind: str) -> None:
        """"file" or "url": re-ranges the delay slider (design 5.9)."""
        if kind not in _DELAY_RANGE:
            return
        self._source_kind = kind
        lo, hi, default = _DELAY_RANGE[kind]
        current = float(self._delay_scale.get())
        self._delay_scale.configure(from_=lo, to=hi)
        self._delay_scale.set(min(max(current, lo), hi) if lo <= current <= hi else default)
        self._render_delay_label()

    def config_values(self) -> dict:
        """Current idle-row selections, for build_live_config at Start."""
        return {
            "sync_mode": self._mode_var.get(),
            "delay_s": round(float(self._delay_scale.get()), 1),
            "engine": self._engine_var.get(),
            "dub_enabled": bool(self._dub_var.get()),
            "subs_enabled": bool(self._subs_var.get()),
        }

    def set_config_values(self, settings: Any) -> None:
        """Preselect the idle row from a LiveSettings-like object."""
        self._mode_var.set(getattr(settings, "sync_mode", "delayed"))
        engine = getattr(settings, "engine", "marian")
        if engine in LIVE_ENGINES:
            self._engine_var.set(engine)
            self._engine_combo.current(LIVE_ENGINES.index(engine))
        self._dub_var.set(bool(getattr(settings, "dub_enabled", True)))
        self._subs_var.set(bool(getattr(settings, "subs_enabled", True)))
        ahead = getattr(settings, "file_ahead_s", None) if self._source_kind == "file" \
            else getattr(settings, "delay_s", None)
        if ahead is not None:
            self._delay_scale.set(float(ahead))
        self._render_delay_label()

    def show_idle(self) -> None:
        self._active = False
        self._running.pack_forget()
        self._idle.pack(fill="x")

    def show_running(self) -> None:
        self._active = True
        self._idle.pack_forget()
        self._running.pack(fill="x")

    def set_active(self, active: bool) -> None:
        self.show_running() if active else self.show_idle()

    def set_start_enabled(self, enabled: bool, *, tooltip_key: str | None = None) -> None:
        self._start_button.configure(state="normal" if enabled else "disabled")
        if tooltip_key and not enabled:
            self._log(self._s(tooltip_key))

    def current_settings(self) -> dict:
        """The idle-row choices with plain keys (mode/delay/engine/dub/subs).

        Plain keys, not the ``live_*`` config keys, so the i18n literal-key
        scanner does not mistake them for UI strings; the App maps them onto the
        config dict for ``normalize_live_settings``.
        """
        return {
            "mode": self._mode_var.get(),
            "delay": round(float(self._delay_scale.get()), 1),
            "engine": LIVE_ENGINES[self._engine_combo.current()],
            "dub": bool(self._dub_var.get()),
            "subs": bool(self._subs_var.get()),
        }

    def render(self, status: Any) -> None:
        """Update the running row and banner from a LiveStatus-like object."""
        state = getattr(status, "state", "stopped")
        params = _SafeDict(getattr(status, "status_params", {}) or {})
        if getattr(status, "lag_s", None) is not None:
            params.setdefault("s", round(float(status.lag_s)))
        key = STATUS_KEYS.get(state, "live_status_stopped")
        self._status_label.configure(text=self._s(key).format_map(params))
        if self._source_kind == "url":
            if not self._badge.winfo_manager():
                self._badge.pack(side="left", padx=(0, 8))
        elif self._badge.winfo_manager():
            self._badge.pack_forget()
        error_key = getattr(status, "error_key", None)
        warning_key = getattr(status, "warning_key", None)
        if error_key:
            self.show_banner(ERROR_KEYS.get(error_key, error_key),
                             getattr(status, "error_params", {}) or {}, is_error=True)
        elif warning_key:
            action = getattr(status, "warning_action", None)
            self.show_banner(WARN_KEYS.get(warning_key, warning_key),
                             getattr(status, "warning_params", {}) or {},
                             with_switch=(action == "live_btn_switch_marian"))
        elif self._banner_key is not None and not self._banner_is_error:
            # a transient warning (e.g. a slow engine) recovered: drop its banner
            # instead of leaving it up until the user closes it by hand.
            self.clear_banner()

    def show_banner(self, key: str, params: dict | None = None, *,
                    with_switch: bool = False, is_error: bool = False) -> None:
        self._banner_key = key
        self._banner_params = dict(params or {})
        self._banner_is_error = is_error
        pal = self._palette
        self._banner_label.configure(
            text=self._s(key).format_map(_SafeDict(self._banner_params)),
            fg=pal.SURFACE if is_error else pal.FG,
            bg=pal.WARN if is_error else pal.FIELD)
        self._banner.configure(bg=pal.WARN if is_error else pal.FIELD)
        if with_switch:
            self._switch_wrap.pack(side="right", padx=(0, 6))
        else:
            self._switch_wrap.pack_forget()
        if not self._banner.winfo_manager():
            self._banner.pack(fill="x", before=self._idle if not self._active else self._running)

    def clear_banner(self) -> None:
        self._banner_key = None
        self._banner_params = {}
        if self._banner.winfo_manager():
            self._banner.pack_forget()

    def relabel(self) -> None:
        for mode, rb in self._mode_buttons.items():
            rb.configure(text=self._s(_MODE_KEYS[mode]))
        self._engine_label.configure(text=self._s("live_label_engine"))
        self._engine_combo.configure(
            values=[self._s(_ENGINE_KEYS[code]) for code in LIVE_ENGINES])
        self._engine_combo.current(LIVE_ENGINES.index(self._engine_var.get()))
        self._chk_dub.configure(text=self._s("live_opt_dub"))
        self._chk_subs.configure(text=self._s("live_opt_subs"))
        self._privacy_label.configure(text=self._s("live_tip_privacy"))
        self._start_button.configure(text=self._s("player_btn_live"))
        self._badge.configure(text=self._s("live_badge"))
        self._stop_button.configure(text=self._s("live_btn_stop"))
        self._switch_button.configure(text=self._s("live_btn_switch_marian"))
        self._render_delay_label()
        if self._banner_key:
            self._banner_label.configure(
                text=self._s(self._banner_key).format_map(_SafeDict(self._banner_params)))

    def _render_delay_label(self) -> None:
        self._delay_label.configure(
            text=self._s("live_label_delay").format(s=round(float(self._delay_scale.get()))))

    def apply_theme(self) -> None:
        pal = self._palette
        for frame in (self, self._idle, self._running, self._banner):
            frame.configure(bg=pal.SURFACE if frame is not self._banner else pal.FIELD)
        for child in (*self._idle.winfo_children(), *self._running.winfo_children()):
            child.configure(bg=pal.SURFACE)
            for gc in child.winfo_children():
                if isinstance(gc, (tk.Label, tk.Radiobutton, tk.Checkbutton)):
                    opts = {"bg": pal.SURFACE}
                    if isinstance(gc, tk.Label):
                        opts["fg"] = pal.FG2
                    else:
                        opts.update(fg=pal.FG, selectcolor=pal.FIELD,
                                    activebackground=pal.SURFACE, activeforeground=pal.FG)
                    gc.configure(**opts)
        self._status_label.configure(bg=pal.SURFACE, fg=pal.FG)
        self._badge.configure(bg=pal.WARN, fg=pal.SURFACE)
        self._banner_label.configure(bg=pal.FIELD, fg=pal.FG)
        self._banner_close.configure(bg=pal.FIELD, fg=pal.FG2, activebackground=pal.FIELD,
                                     activeforeground=pal.FG)
