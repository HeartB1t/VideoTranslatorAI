"""Log panel and UI activity logging (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class LogMixin:
    # ── Log ──────────────────────────────────────────────────────────────────

    _LOG_MAX_LINES = 5000

    def _log_write(self, text: str):
        """Raw text (print, pipeline, libraries, player modules): every new line
        gets time, level and area in front (``app_log.classify``).

        Progress bars stay one line: ``\\r`` rewrites the current line (as a
        terminal does), and an update of the activity shown on the previous
        line (``app_log.progress_of``) replaces that line instead of adding one.
        """
        if self._log_pending_cr:
            text, self._log_pending_cr = "\r" + text, False
        pieces = [piece for piece in _g.re.split(r"(\r\n|\n|\r)", text) if piece]
        if pieces and pieces[-1] == "\r":
            # Maybe the first half of a split \r\n: decide with the next text.
            pieces.pop()
            self._log_pending_cr = True
        segments: list[tuple[str, str | None]] = []
        for piece in pieces:
            if piece in ("\n", "\r\n"):
                segments.append(("\n", None))
                self._log_bol = True
                continue
            if piece == "\r":
                segments.append(("\r", _g._LOG_CUT_LINE))
                self._log_bol = True
                self._log_progress_key = None
                continue
            if not self._log_bol:
                segments.append((piece, None))
                continue
            self._log_bol = False
            level, area, message = _g._app_log.classify(piece)
            if level is None:                        # a traceback frame and the like
                self._log_progress_key = None
                segments.append((piece, None))
                continue
            progress = _g._app_log.progress_of(message)
            key = progress.key if progress is not None else None
            if key is not None and key == self._log_progress_key:
                segments.append(("", _g._LOG_DROP_PREVIOUS_LINE))
            self._log_progress_key = key
            self._log_level_now = level
            segments.extend(self._log_prefix(level, area))
            segments.append((message, None))
        self._log_insert(segments)

    def _log_words(self) -> dict:
        try:
            words = {"info": self._s("log_level_info"), "warn": self._s("log_level_warn"),
                     "error": self._s("log_level_error")}
        except Exception:                                # noqa: BLE001
            words = {"info": "INFO", "warn": "WARNING", "error": "ERROR"}
        return _g._app_log.level_words(words)

    def _log_prefix(self, level: str, area: str) -> list:
        """``HH:MM:SS LEVEL [area] `` as segments; only the level word is coloured."""
        return [(_g.time.strftime("%H:%M:%S "), None),
                (self._log_words().get(level, level), f"lvl_{level}"),
                (f" [{area}] ", None)]

    def _log_emit(self, message: str, area: str = "app", level: str = "info") -> None:
        """One formatted line from the app itself. Callable from any thread."""
        if _g.threading.current_thread() is not _g.threading.main_thread():
            if not self._destroying:
                with _g.contextlib.suppress(RuntimeError):
                    self.after(0, self._log_emit, message, area, level)
            return
        message = " ".join(str(message or "").split())
        if not message:
            return
        segments = [] if self._log_bol else [("\n", None)]
        segments.extend(self._log_prefix(level, area))
        segments.extend([(message, None), ("\n", None)])
        self._log_bol = True
        self._log_level_now = level
        self._log_progress_key = None
        self._log_insert(segments)

    def _log_insert(self, segments: list) -> None:
        """Write segments to the log file and the panel (level word coloured).

        Two control segments edit the panel instead of adding text: a cut
        (``\\r``, also sent to the file, which keeps the last state) empties
        the current line, a drop removes the previous line (a progress bar
        about to be rewritten).
        """
        text = "".join(chunk for chunk, _tag in segments)
        log_file = getattr(self, "_log_file", None)
        if log_file is not None:
            log_file.write(text)
        if self._destroying or not text:
            return
        # Smart auto-scroll: only follow tail if user hasn't scrolled up
        try:
            yview_bottom = self._log.yview()[1]
        except Exception:
            yview_bottom = 1.0
        at_bottom = yview_bottom >= 0.95
        self._log.configure(state="normal")
        for chunk, tag in segments:
            if tag == _g._LOG_CUT_LINE:
                self._log.delete("end-1c linestart", "end-1c")
            elif tag == _g._LOG_DROP_PREVIOUS_LINE:
                # Only a progress line goes: a mismatch (the panel was cleared
                # meanwhile) must never eat an ordinary line.
                previous = self._log.get("end-2c linestart", "end-1c")
                if _g._app_log.progress_of(previous) is not None:
                    self._log.delete("end-2c linestart", "end-1c")
            elif tag and tag != "lvl_info":
                self._log.insert("end", chunk, tag)
            else:
                self._log.insert("end", chunk)
        # Hard cap to prevent RAM blowup on long pipelines
        try:
            line_count = int(self._log.index("end-1c").split(".")[0])
            if line_count > self._LOG_MAX_LINES:
                self._log.delete("1.0", f"{line_count - self._LOG_MAX_LINES}.0")
        except Exception:
            pass
        if at_bottom:
            self._log.see("end")
        self._log.configure(state="disabled")

    # -- Talking log: clicks, choices, results and errors ---------------------

    def _log_event(self, key: str, **fields) -> None:
        """Write one event line, in the UI language, with the time in front.

        Callable from any thread. Never raises: a broken format string still
        logs the raw key and fields.
        """
        if _g.threading.current_thread() is not _g.threading.main_thread():
            # The UI language is a Tk variable: format on the Tk thread.
            if not self._destroying:
                with _g.contextlib.suppress(RuntimeError):
                    self.after(0, lambda: self._log_event(key, **fields))
            return
        # A command echoed right after the click that sent it says nothing new.
        if key in ("log_player", "log_live") and _g.time.monotonic() - self._last_click_at < 1.0:
            return
        try:
            text = self._s(key).format(**fields)
        except Exception:                                # noqa: BLE001
            text = f"{key} {fields}"
        self._log_emit(text, _g._app_log.EVENT_AREAS.get(key, "app"),
                       _g._app_log.EVENT_LEVELS.get(key, "info"))

    def _log_line(self, area: str, text: str, level: str = "info") -> None:
        """Log a result already written in the UI language (what the user sees)."""
        self._log_emit(text, area, level)

    def _log_session_header(self) -> None:
        """What a bug report needs first: version, system, hardware, settings."""
        from videotranslator import __version__ as version
        commit = _g._app_log.git_commit(_g.Path(_g.__file__).resolve().parent)
        self._log_file.write("=" * 72 + "\n")            # session separator (file only)
        self._log_event("log_started", version=version + (f" ({commit})" if commit else ""),
                        py=_g.platform.python_version(),
                        os=f"{_g.platform.system()} {_g.platform.release()} {_g.platform.machine()}")
        note = self._relaunch_note()
        if note:
            self._log_line("app", note)
        if self._log_file.ok:
            self._log_event("log_file", days=_g._app_log.KEEP_DAYS, path=self._log_file.path)
        with _g.contextlib.suppress(Exception):
            s = self._ui_settings
            self._log_event("log_settings", theme=s["ui_theme"], accent=s["ui_accent"],
                            scale=s["ui_scale"])
        with _g.contextlib.suppress(Exception):
            self._log_line("job", self._summary_var.get())
            out = _g._platforms.resolve_output_dir(self._output_dir_var.get().strip() or None)
            self._log_line("job", f"{self._s('label_output_dir')} {out}")
        with _g.contextlib.suppress(Exception):
            raw = self._live_bar.current_settings()
            self._log_event("log_session_live", mode=raw["mode"], engine=raw["engine"],
                            asr=_g.load_config().get("live_asr_model", "auto"),
                            voice=self._live_voice_info_text())

        found: list = []

        ollama_url = self._ollama_url_var.get().strip() or "http://localhost:11434"
        ollama_model = self._ollama_model_var.get().strip() or "qwen3:8b"

        def probe() -> None:
            # Cheap facts only: nvidia-smi and metadata, never torch at startup.
            facts: dict = {}
            with _g.contextlib.suppress(Exception):
                # Read only (starts, installs and pulls nothing): the header dot.
                facts["ollama"] = (ollama_url, ollama_model,
                                   _g._check_ollama_status(ollama_url, ollama_model, timeout=3.0))
            with _g.contextlib.suppress(Exception):
                from videotranslator.hardware_profile import detect_hardware
                facts["hw"] = detect_hardware(use_torch=False)
            with _g.contextlib.suppress(Exception):
                facts["os"] = _g._app_log.os_description()
            with _g.contextlib.suppress(Exception):
                loc = _g.locale.getlocale()
                facts["locale"] = ".".join(part for part in loc if part) or "?"
            with _g.contextlib.suppress(Exception):
                facts["libs"] = _g._app_log.library_versions()
            with _g.contextlib.suppress(Exception):
                facts["smi"] = _g._app_log.parse_nvidia_smi_banner(
                    _g._app_log.tool_output(["nvidia-smi"]))
            with _g.contextlib.suppress(Exception):
                facts["ffmpeg"] = _g._app_log.ffmpeg_version(
                    _g._app_log.tool_first_line(["ffmpeg", "-version"]))
            found.append(facts)

        def collect(tries: int = 100) -> None:
            # The Tk thread picks the result up: the worker never touches Tk.
            if self._destroying:
                return
            if found:
                self._log_system(found[0])
                if found[0].get("ollama"):
                    with _g.contextlib.suppress(Exception):
                        self._ollama_badge_from_check(*found[0]["ollama"])
            elif tries > 0:
                self.after(200, collect, tries - 1)

        self._spawn_header_probe(probe)
        self.after(200, collect)

    def _spawn_header_probe(self, probe) -> None:
        """Run the session-header probe off the Tk thread (tests run it inline)."""
        _g.threading.Thread(target=probe, name="log-hardware", daemon=True).start()

    def _log_system(self, facts: dict) -> None:
        """System lines of the session header (on the Tk thread)."""
        s = self._s
        with _g.contextlib.suppress(Exception):
            self._log_emit(s("log_sys_os").format(os=facts.get("os") or _g.platform.platform(),
                                                  locale=facts.get("locale", "?")), "sys")
        with _g.contextlib.suppress(Exception):
            dpi = float(self.tk.call("tk", "scaling")) * 72
            session = self.tk.call("tk", "windowingsystem")
            if _g.sys.platform.startswith("linux"):
                kind = _g.os.environ.get("XDG_SESSION_TYPE") or ""
                desktop = _g.os.environ.get("XDG_CURRENT_DESKTOP") or ""
                parts = []
                for part in (str(session), kind, desktop):
                    if part and part.lower() not in (p.lower() for p in parts):
                        parts.append(part)
                session = " ".join(parts)
            self._log_emit(s("log_sys_screen").format(
                size=f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}",
                scale=f"{dpi:.0f} DPI", session=session), "sys")
        hw = facts.get("hw")
        if hw is not None:
            self._log_hardware(hw)
        driver, cuda = facts.get("smi") or ("", "")
        if driver:
            self._log_emit(s("log_sys_gpu").format(driver=driver, cuda=cuda or "?"), "sys")
        if facts.get("libs"):
            self._log_emit(s("log_sys_libs").format(libs=facts["libs"]), "sys")
        tools = [f"ffmpeg {facts['ffmpeg']}" if facts.get("ffmpeg") else "ffmpeg -"]
        self._log_emit(s("log_sys_tools").format(tools=", ".join(tools)), "sys")

    def _log_hardware(self, hw) -> None:
        s = self._s
        lines = [s("mdl_hw_cpu").format(name=hw.cpu_name, cores=hw.cpu_cores or "?"),
                 s("mdl_hw_ram").format(ram=f"{hw.ram_gb:.1f}" if hw.ram_gb else "?")]
        for gpu in hw.gpus or ():
            vram = f"{gpu.vram_gb:.1f}" if gpu.vram_gb else "?"
            lines.append(s("mdl_hw_gpu").format(gpu=gpu.name, vram=vram))
        if not hw.gpus:
            lines.append(s("mdl_hw_no_gpu"))
        if hw.disk_free_gb is not None:
            lines.append(s("mdl_hw_disk").format(free=f"{hw.disk_free_gb:.1f}"))
        for line in lines:
            self._log_line("sys", line)

    def _widget_context(self, widget) -> str:
        """``name`` of a control, with its window title when not the main one."""
        try:
            name = widget.cget("text")
        except _g.tk.TclError:
            name = ""
        name = _g._app_log.short(name) or widget.winfo_class()
        try:
            top = widget.winfo_toplevel()
            if top is not self and top.title():
                return f"{_g._app_log.short(top.title(), 40)} > {name}"
        except _g.tk.TclError:
            pass
        return name

    def _log_widget_click(self, event) -> None:
        widget = event.widget
        try:
            inside = widget.winfo_containing(event.x_root, event.y_root) is widget
        except (_g.tk.TclError, KeyError):
            inside = True
        if inside:
            self._log_widget_activation(widget)

    def _log_widget_key(self, event) -> None:
        self._log_widget_activation(event.widget)

    @staticmethod
    def _is_on(value, onvalue) -> bool:
        if str(value) == str(onvalue):
            return True
        return str(onvalue) == "1" and str(value).lower() in ("true", "1")

    def _log_widget_activation(self, widget) -> None:
        """Log a button (before Tk runs its command, so the click precedes its
        result), a check box or a radio button (its value once applied)."""
        self._last_click_at = _g.time.monotonic()
        try:
            name = self._widget_context(widget)
            if str(widget.cget("state")) == "disabled":
                self._log_event("log_click_disabled", name=name)
                return
            cls = widget.winfo_class()
            variable = str(widget.cget("variable")) if cls in ("Checkbutton", "Radiobutton") else ""
            if cls in ("Checkbutton", "Radiobutton") and variable:
                # Tk toggles a check box at a different point for mouse and
                # keyboard: read the value once the click has been applied.
                def log_value(w=widget, v=variable, n=name, c=cls):
                    with _g.contextlib.suppress(Exception):
                        if c == "Checkbutton":
                            on = self._is_on(self.getvar(v), w.cget("onvalue"))
                            self._log_event("log_on" if on else "log_off", name=n)
                        else:
                            self._log_event("log_choice", name=n, value=self.getvar(v))
                self.after_idle(log_value)
            else:
                self._log_event("log_click", name=name)
        except Exception:                                # noqa: BLE001 - logging must not break a click
            pass

    def _log_combo_choice(self, event) -> None:
        self._last_click_at = _g.time.monotonic()
        with _g.contextlib.suppress(Exception):
            widget = event.widget
            top = widget.winfo_toplevel()
            where = _g._app_log.short(top.title(), 40) if top is not self else "combobox"
            self._log_event("log_choice", name=where, value=_g._app_log.short(widget.get()))

    def _log_scale_choice(self, event) -> None:
        self._last_click_at = _g.time.monotonic()
        with _g.contextlib.suppress(Exception):
            widget = event.widget
            self._log_event("log_choice", name="slider", value=round(float(widget.get()), 2))

    def _log_thread_exception(self, args) -> None:
        """An uncaught error in a worker thread: to the log (the old hook only if
        logging it fails, so the traceback is not written twice)."""
        try:
            name = args.thread.name if args.thread is not None else "thread"
            self._log_event("log_error", where=name,
                            error=f"{args.exc_type.__name__}: {args.exc_value}")
            self._log_async("".join(_g.traceback.format_exception(
                args.exc_type, args.exc_value, args.exc_traceback)))
        except Exception:                                # noqa: BLE001
            with _g.contextlib.suppress(Exception):
                self._saved_thread_excepthook(args)

    def _log_copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._log.get("1.0", "end-1c"))
        except Exception:
            pass

    def _log_save(self):
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                initialfile="video_translator.log",
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._log.get("1.0", "end-1c"))
        except Exception as e:
            try:
                _g.messagebox.showerror(self._s("msg_error_t"), str(e))
            except Exception:
                pass

    def _log_clear(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._log_progress_key = None

    def _toggle_log(self):
        self._log_visible = not getattr(self, "_log_visible", True)
        if self._log_visible:
            self._log_container.grid()
            self._btn_log_toggle.configure(text=self._s("btn_log_hide"))
        else:
            self._log_container.grid_remove()
            self._btn_log_toggle.configure(text=self._s("btn_log_show"))
        try:
            _g.save_config({"ui_log_visible": self._log_visible})
        except Exception:
            pass
