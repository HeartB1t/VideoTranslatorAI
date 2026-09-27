"""'AI models for this PC' window (hardware-aware model selection, step 6).

Shows the detected hardware, one recommendation per pipeline stage for the
chosen priority (speed / balanced / quality) with the evidence behind it, and
every other option rated for this PC, so users on weaker or stronger machines
can pick by hand. Nothing is downloaded or changed until the user presses
Download or Apply; Restore previous brings back the choices made before the
last Apply.

Hardware probing, downloads and the benchmark run on worker threads; their
results reach Tk through a queue polled with ``after`` (Tk is not thread-safe).
"""

from __future__ import annotations

import dataclasses
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .hardware_profile import HardwareInfo, detect_hardware
from .model_catalog import (PREFERENCES, STAGE_OPTIONS, WHISPER, ModelOption, assess,
                            recommend)
from .model_manager import WhisperDownload, benchmark_whisper, cached_whisper_models

STAGES = ("asr", "asr_live", "mt", "tts")
_STAGE_KEYS = {"asr": "mdl_stage_asr", "asr_live": "mdl_stage_asr_live",
               "mt": "mdl_stage_mt", "tts": "mdl_stage_tts"}
_PREF_KEYS = {"speed": "mdl_pref_speed", "balanced": "mdl_pref_balanced",
              "quality": "mdl_pref_quality"}
_FIT_MARK = {"ok": "✓", "tight": "!", "too_big": "✗", "no_disk": "✗",
             "online": "○"}


def _fmt_gb(value: float | None) -> str:
    return "?" if value is None else f"{value:.1f}"


def hardware_lines(hw: HardwareInfo, ui_s: Callable[[str], str]) -> list[str]:
    """The hardware summary shown at the top of the window."""
    lines = [ui_s("mdl_hw_cpu").format(name=hw.cpu_name, cores=hw.cpu_cores or "?"),
             ui_s("mdl_hw_ram").format(ram=_fmt_gb(hw.ram_gb))]
    gpu = hw.best_gpu
    if hw.vram_gb is not None and gpu is not None:
        lines.append(ui_s("mdl_hw_gpu").format(gpu=gpu.name, vram=_fmt_gb(hw.vram_gb)))
    elif gpu is not None:
        lines.append(ui_s("mdl_hw_gpu_unusable").format(gpu=gpu.name))
    else:
        lines.append(ui_s("mdl_hw_no_gpu"))
    lines.append(ui_s("mdl_hw_disk").format(free=_fmt_gb(hw.disk_free_gb)))
    return lines


def option_text(opt: ModelOption, hw: HardwareInfo, cached: set[str],
                ui_s: Callable[[str], str]) -> str:
    """One combobox entry: name, fit for this PC and download state."""
    fit = assess(opt, hw, cached=cached)
    parts = [f"{_FIT_MARK[fit]} {opt.label}", ui_s(f"mdl_fit_{fit}")]
    if opt.stage in ("asr", "asr_live"):
        parts.append(ui_s("mdl_status_cached") if opt.key in cached
                     else ui_s("mdl_status_download").format(mb=opt.download_mb))
    elif opt.key.startswith("qwen3"):
        parts.append(ui_s("mdl_status_ollama"))
    elif opt.key == "voicebox":
        parts.append(ui_s("mdl_status_voicebox"))
    elif opt.local:
        parts.append(ui_s("mdl_status_first_use"))
    return " · ".join(parts)


def reason_text(reasons, ui_s: Callable[[str], str]) -> str:
    out = []
    for key, params in reasons:
        try:
            out.append(ui_s(key).format(**params))
        except (KeyError, IndexError, ValueError):
            out.append(ui_s(key))
    return "; ".join(out)


def _ask_media_file(parent: tk.Misc, title: str) -> str:
    from tkinter import filedialog
    return filedialog.askopenfilename(
        parent=parent, title=title,
        filetypes=[("Video / audio", "*.mp4 *.mkv *.webm *.mov *.avi *.mp3 *.wav *.m4a *.flac "
                                     "*.ogg *.opus"), ("*", "*")]) or ""


class ModelsDialog:
    """The window. ``on_apply(choices)`` gets {stage: option key} on Apply;
    ``on_revert()`` restores the previous choices and returns them (or None);
    ``media_path()`` gives the loaded local media for the benchmark;
    ``busy()`` is True while a translation or live session runs."""

    def __init__(self, parent: tk.Misc, *, ui_s: Callable[[str], str], theme: Any,
                 make_button: Callable[..., tuple[tk.Widget, tk.Button]],
                 current: dict[str, str], on_apply: Callable[[dict[str, str]], None],
                 on_revert: Callable[[], dict[str, str] | None],
                 media_path: Callable[[], str | None], busy: Callable[[], bool],
                 detect: Callable[[], HardwareInfo] = detect_hardware,
                 cached: Callable[[], set[str]] = cached_whisper_models,
                 log: Callable[[str], None] | None = None,
                 ask_media: Callable[[tk.Misc, str], str] | None = None) -> None:
        self._s = ui_s
        self._ask_media = ask_media or _ask_media_file
        self._log = log
        self._last_logged = ""
        self._last_progress_log = 0.0
        self._pal = theme.palette
        self._on_apply = on_apply
        self._on_revert = on_revert
        self._media_path = media_path
        self._busy = busy
        self._detect = detect
        self._cached_fn = cached
        self._current = dict(current)
        self._hw: HardwareInfo | None = None
        self._cached: set[str] = set()
        self._results: queue.Queue = queue.Queue()
        self._download: WhisperDownload | None = None
        self._bench_cancel: threading.Event | None = None
        self._poll_after: str | None = None
        self._closed = False
        self._choice_keys: dict[str, list[str]] = {}
        self._last_busy: bool | None = None
        pal = self._pal

        win = tk.Toplevel(parent, bg=pal.BG)
        self.win = win
        win.title(ui_s("mdl_title"))
        win.transient(parent)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.close)
        body = tk.Frame(win, bg=pal.BG, padx=18, pady=14)
        body.pack(fill="both", expand=True)

        self._hw_label = tk.Label(body, text=ui_s("mdl_detecting"), bg=pal.BG, fg=pal.FG,
                                  justify="left", anchor="w", font="VT.Base")
        self._hw_label.pack(fill="x")

        prefs = tk.Frame(body, bg=pal.BG)
        prefs.pack(fill="x", pady=(10, 6))
        tk.Label(prefs, text=ui_s("mdl_pref_label"), bg=pal.BG, fg=pal.FG2,
                 font="VT.Small").pack(side="left", padx=(0, 8))
        self._pref_var = tk.StringVar(value="balanced")
        self._pref_buttons = []
        for pref in PREFERENCES:
            rb = tk.Radiobutton(prefs, text=ui_s(_PREF_KEYS[pref]), value=pref,
                                variable=self._pref_var, command=self._select_recommended,
                                indicatoron=False, bg=pal.BTN, fg=pal.FG,
                                selectcolor=pal.ACC_SOFT, activebackground=pal.ACC_SOFT,
                                activeforeground=pal.FG, relief="flat", padx=10, pady=3,
                                font="VT.Base", state="disabled")
            rb.pack(side="left", padx=2)
            self._pref_buttons.append(rb)

        self._combos: dict[str, ttk.Combobox] = {}
        self._reason_labels: dict[str, tk.Label] = {}
        grid = tk.Frame(body, bg=pal.BG)
        grid.pack(fill="x", pady=(4, 4))
        for row, stage in enumerate(STAGES):
            tk.Label(grid, text=ui_s(_STAGE_KEYS[stage]), bg=pal.BG, fg=pal.FG,
                     font="VT.SmallBold", anchor="w").grid(row=row * 2, column=0,
                                                           sticky="w", pady=(6, 0))
            combo = ttk.Combobox(grid, state="disabled", width=58)
            combo.grid(row=row * 2, column=1, sticky="w", padx=(10, 0), pady=(6, 0))
            combo.bind("<<ComboboxSelected>>", lambda _e, st=stage: self._on_pick(st))
            self._combos[stage] = combo
            reason = tk.Label(grid, text="", bg=pal.BG, fg=pal.FG2, font="VT.Small",
                              justify="left", anchor="w", wraplength=520)
            reason.grid(row=row * 2 + 1, column=1, sticky="w", padx=(10, 0))
            self._reason_labels[stage] = reason

        tk.Label(body, text=ui_s("mdl_note"), bg=pal.BG, fg=pal.FG2, font="VT.Small",
                 justify="left", anchor="w", wraplength=640).pack(fill="x", pady=(8, 4))
        self._status = tk.Label(body, text="", bg=pal.BG, fg=pal.FG, font="VT.Small",
                                justify="left", anchor="w", wraplength=640)
        self._status.pack(fill="x", pady=(2, 8))

        buttons = tk.Frame(body, bg=pal.BG)
        buttons.pack(fill="x")
        self._buttons: dict[str, tk.Button] = {}
        for name, key, cmd, primary in (
                ("download", "mdl_btn_download", self._start_download, False),
                ("benchmark", "mdl_btn_benchmark", self._start_benchmark, False),
                ("cancel", "mdl_btn_cancel", self._cancel_work, False),
                ("revert", "mdl_btn_revert", self._revert, False),
                ("apply", "mdl_btn_apply", self._apply, True),
                ("close", "mdl_btn_close", self.close, False)):
            wrap, btn = make_button(buttons, text=ui_s(key), command=cmd, primary=primary)
            wrap.pack(side="left", padx=(0, 6))
            self._buttons[name] = btn
        tk.Label(body, text=ui_s("mdl_bench_hint"), bg=pal.BG, fg=pal.FG2, font="VT.Small",
                 justify="left", anchor="w", wraplength=640).pack(fill="x", pady=(8, 0))
        self._set_buttons()

        threading.Thread(target=self._probe, name="models-probe", daemon=True).start()
        self._schedule_poll()

    # -- worker plumbing -----------------------------------------------------

    def _probe(self) -> None:
        try:
            hw = self._detect()
            cached = self._cached_fn()
            self._results.put(("hw", (hw, cached)))
        except Exception as exc:              # noqa: BLE001 (shown, not raised)
            self._results.put(("hw_error", str(exc)))

    def _schedule_poll(self) -> None:
        if not self._closed:
            self._poll_after = self.win.after(150, self._poll)

    def _poll(self) -> None:
        self._poll_after = None
        while True:
            try:
                kind, value = self._results.get_nowait()
            except queue.Empty:
                break
            self._handle(kind, value)
        self._poll_download()
        if self._busy() != self._last_busy:     # a job or live session started/ended
            self._set_buttons()
        self._schedule_poll()

    def _handle(self, kind: str, value: Any) -> None:
        if kind == "hw":
            self._hw, self._cached = value
            self._hw_label.configure(text="\n".join(hardware_lines(self._hw, self._s)))
            if self._log is not None:
                for line in hardware_lines(self._hw, self._s):
                    self._log(line)
            for rb in self._pref_buttons:
                rb.configure(state="normal")
            self._fill_combos()
            self._select_current()
        elif kind == "hw_error":
            self._hw_label.configure(text=value)
        elif kind == "bench":
            self._bench_cancel = None
            if value is not None:
                speed = (1.0 / value.realtime_factor) if value.realtime_factor else 0.0
                first = "?" if value.first_segment_s is None else f"{value.first_segment_s:.1f}"
                self._set_status(self._s("mdl_bench_result").format(
                    model=value.model, device=value.device, load=f"{value.load_s:.1f}",
                    first=first, speed=f"{speed:.1f}"))
            else:
                self._set_status("")
        elif kind == "bench_error":
            self._bench_cancel = None
            self._set_status(self._s("mdl_bench_failed").format(error=value), level="warn")
        self._set_buttons()

    # -- choices -------------------------------------------------------------

    def _fill_combos(self) -> None:
        assert self._hw is not None
        for stage in STAGES:
            options = list(STAGE_OPTIONS[stage].values())
            self._choice_keys[stage] = [opt.key for opt in options]
            combo = self._combos[stage]
            combo.configure(values=[option_text(
                dataclasses.replace(opt, stage=stage), self._hw, self._cached,
                self._s) for opt in options], state="readonly")

    def _set_choice(self, stage: str, key: str) -> None:
        keys = self._choice_keys.get(stage, [])
        if key in keys:
            self._combos[stage].current(keys.index(key))

    def _select_current(self) -> None:
        """Show the settings in use; the reasons still explain the recommendation."""
        recs = recommend(self._hw, self._pref_var.get(), cached=self._cached)
        for stage in STAGES:
            self._set_choice(stage, self._current.get(stage, recs[stage].option.key))
            self._reason_labels[stage].configure(text=self._reason_for(stage, recs))

    def _select_recommended(self) -> None:
        if self._hw is None:
            return
        recs = recommend(self._hw, self._pref_var.get(), cached=self._cached)
        for stage in STAGES:
            self._set_choice(stage, recs[stage].option.key)
            self._reason_labels[stage].configure(text=self._reason_for(stage, recs))
        self._set_buttons()

    def _reason_for(self, stage: str, recs) -> str:
        rec = recs[stage]
        return self._s("mdl_recommended").format(model=rec.option.label) + ": " + \
            reason_text(rec.reasons, self._s)

    def _on_pick(self, _stage: str) -> None:
        self._set_buttons()

    def choices(self) -> dict[str, str]:
        out = {}
        for stage in STAGES:
            index = self._combos[stage].current()
            keys = self._choice_keys.get(stage, [])
            if 0 <= index < len(keys):
                out[stage] = keys[index]
        return out

    def _missing_whisper(self) -> list[str]:
        picked = self.choices()
        return [key for key in dict.fromkeys((picked.get("asr"), picked.get("asr_live")))
                if key in WHISPER and key not in self._cached]

    # -- actions ---------------------------------------------------------------

    def _working(self) -> bool:
        return self._download is not None or self._bench_cancel is not None

    def _set_buttons(self) -> None:
        ready = self._hw is not None
        working = self._working()
        busy = self._busy()
        states = {
            "download": ready and not working and bool(self._missing_whisper()),
            "benchmark": ready and not working and not busy,
            "cancel": working,
            "apply": ready and not working and not busy,
            "revert": not working and not busy,
            "close": True,
        }
        for name, enabled in states.items():
            self._buttons[name].configure(state="normal" if enabled else "disabled")
        # The accent-filled Apply looks the same when disabled: grey it out.
        pal = self._pal
        if states["apply"]:
            self._buttons["apply"].configure(bg=pal.ACC)
        else:
            self._buttons["apply"].configure(bg=pal.BTN, disabledforeground=pal.FG2)
        # Say why the actions are off, instead of leaving grey buttons.
        self._last_busy = busy
        current = self._status.cget("text")
        if ready and busy and not working and not current:
            self._set_status(self._s("mdl_busy"), level="warn")
        elif not busy and current == self._s("mdl_busy"):
            self._set_status("")

    def _set_status(self, text: str, *, progress: bool = False, level: str = "info") -> None:
        self._status.configure(text=text)
        # Every message goes to the app log (again if a new click repeats it);
        # download progress only when it changes, at most every 5 s.
        if self._log is None or not text:
            return
        now = time.monotonic()
        if progress and (text == self._last_logged or now - self._last_progress_log < 5.0):
            return
        self._last_progress_log = now if progress else 0.0
        self._last_logged = text
        try:
            self._log(text, level)
        except Exception:                      # noqa: BLE001
            pass

    def _start_download(self) -> None:
        missing = self._missing_whisper()
        if not missing or self._working():
            return
        self._download = WhisperDownload(missing[0])
        self._download.start()
        self._set_buttons()

    def _poll_download(self) -> None:
        dl = self._download
        if dl is None:
            return
        label = WHISPER[dl.key].label
        if dl.state in ("idle", "running"):
            self._set_status(self._s("mdl_dl_running").format(
                model=label, done=f"{dl.progress_mb():.0f}", total=dl.expected_mb), progress=True)
            return
        if dl.state == "verifying":
            self._set_status(self._s("mdl_dl_verifying").format(model=label))
            return
        self._download = None
        if dl.state == "done":
            self._cached.add(dl.key)
            self._set_status(self._s("mdl_dl_done").format(model=label))
            keep = self.choices()
            self._fill_combos()
            for stage, key in keep.items():
                self._set_choice(stage, key)
        elif dl.state == "cancelled":
            self._set_status(self._s("mdl_dl_cancelled"))
        else:
            self._set_status(self._s("mdl_dl_failed").format(model=label, error=dl.error), level="warn")
        self._set_buttons()

    def _start_benchmark(self) -> None:
        if self._working() or self._hw is None:
            return
        if self._busy():
            self._set_status(self._s("mdl_busy"), level="warn")
            return
        media = self._media_path()
        if not media:
            # Nothing loaded in the player: let the user pick a file instead.
            media = self._ask_media(self.win, self._s("mdl_bench_pick"))
            if not media:
                self._set_status(self._s("mdl_bench_no_file"), level="warn")
                return
        key = self.choices().get("asr", "small")
        cancel = threading.Event()
        self._bench_cancel = cancel
        use_gpu = self._hw.vram_gb is not None
        self._set_status(self._s("mdl_bench_running").format(model=WHISPER[key].label))
        self._set_buttons()

        def work() -> None:
            try:
                result = benchmark_whisper(key, media, use_gpu=use_gpu, cancel=cancel)
                self._results.put(("bench", result))
            except Exception as exc:          # noqa: BLE001
                self._results.put(("bench_error", str(exc) or type(exc).__name__))

        threading.Thread(target=work, name="models-benchmark", daemon=True).start()

    def _cancel_work(self) -> None:
        if self._download is not None:
            self._download.cancel()
        if self._bench_cancel is not None:
            self._bench_cancel.set()

    def _apply(self) -> None:
        if self._busy():
            self._set_status(self._s("mdl_busy"), level="warn")
            return
        picked = self.choices()
        if not picked:
            return
        self._on_apply(picked)
        self._current = dict(picked)
        self._set_status(self._s("mdl_applied") + " " + ", ".join(
            f"{stage}={key}" for stage, key in picked.items()))
        self._set_buttons()

    def _revert(self) -> None:
        if self._busy():
            self._set_status(self._s("mdl_busy"), level="warn")
            return
        restored = self._on_revert()
        if not restored:
            self._set_status(self._s("mdl_nothing_to_revert"))
            return
        self._current = dict(restored)
        if self._hw is not None:
            for stage, key in restored.items():
                self._set_choice(stage, key)
        self._set_status(self._s("mdl_reverted"))
        self._set_buttons()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._cancel_work()
        if self._poll_after is not None:
            try:
                self.win.after_cancel(self._poll_after)
            except tk.TclError:
                pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    @property
    def closed(self) -> bool:
        return self._closed
