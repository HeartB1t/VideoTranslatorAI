"""Translation and voice engines: Ollama, Voicebox, ElevenLabs, model choices (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class EnginesMixin:
    # ── TTS engine mutual exclusion (v2.3) ────────────────────────────────
    # ── Ollama auto-setup (v2.0.1) ────────────────────────────────────────
    #
    # Flow (all off-thread, UI always responsive):
    #   1. Binary → if missing: popup [Yes/No] → _ollama_install
    #   2. Daemon → if down: start in background, wait up to 15 s
    #   3. Model → the chosen one missing: popup [Yes/No] → ollama pull
    #      (No: an installed compatible model, else Google; not asked again)
    #   4. Ready
    # Edge: if config `ollama_auto_install=false`, skip install/pull and
    # fall back to Google without a popup.
    #
    # `on_ready` is an optional callback invoked on the main thread when
    # Ollama is ready (useful for chaining the translation pipeline).
    # If Ollama is not ready at the end, `on_ready(False)` is called.

    def _ensure_ollama_ready_async(self, on_ready=None):
        """Entry point: spawn the setup worker in a daemon thread.

        `on_ready`: callback(bool) invoked on the main thread; True if Ollama is
        ready (daemon up + model available), False otherwise. If None,
        the function is used only to "warm up" Ollama (radio select case).
        """
        # One preparation at a time: a second one (the model box changed while
        # a download runs) would ask twice or pull twice. It runs again, with
        # the box's model at that moment, when the current one ends.
        if self._ollama_setup_running:
            self._ollama_setup_pending.append(on_ready)
            return
        self._ollama_setup_running = True
        model = self._ollama_model_var.get().strip() or "qwen3:8b"
        url = self._ollama_url_var.get().strip() or "http://localhost:11434"
        cfg = _g.load_config()
        auto_install = cfg.get("ollama_auto_install", True)
        # The questions in the UI language, read here on the Tk thread.
        texts = {key: self._s(key) for key in self._OLLAMA_QUESTION_KEYS}

        def _setup():
            ok = False
            try:
                ok = self._ollama_setup_worker(model, url, auto_install, texts)
            finally:
                if not self._destroying:
                    self.after(0, self._ollama_setup_done, ok, on_ready)

        _g.threading.Thread(target=_setup, daemon=True).start()

    _OLLAMA_QUESTION_KEYS = ("ollama_install_ask", "ollama_pull_ask", "ollama_pull_size",
                             "ollama_pull_else_model", "ollama_pull_else_google",
                             "ollama_pull_no_disk", "ollama_pull_heavy", "ollama_pull_tight")

    def _ollama_pull_fit(self, model: str, installed: bool = False):
        """Disk (where Ollama keeps its models) and memory check before
        offering ``model``, memory only when it is ``installed``: a
        model_catalog.PullFit, or None when it cannot tell. Worker thread."""
        try:
            from videotranslator.hardware_profile import detect_hardware
            from videotranslator.model_catalog import ollama_pull_fit
            hw = detect_hardware(model_dir=_g._ollama_models_dir())
            return ollama_pull_fit(model, hw, size_gb=_g._ollama_model_size_gb(model),
                                   installed=installed)
        except Exception:                          # noqa: BLE001 - advice, never a failure
            return None

    def _ollama_setup_done(self, ok: bool, on_ready) -> None:
        """Tk thread: the preparation ended; run the one that waited, if any."""
        self._ollama_setup_running = False
        note = getattr(self, "_ollama_ready_note", None)
        if ok and note:
            url, model = note
            self._set_ollama_badge("ok", self._s("ollama_ready").format(
                ollama="Ollama", url=url, model=model))
        elif not ok:
            self._set_ollama_badge(None, "")
        if on_ready is not None:
            on_ready(ok)
        pending, self._ollama_setup_pending = self._ollama_setup_pending, []
        callbacks = [callback for callback in pending if callback is not None]
        if pending:
            self._ensure_ollama_ready_async(
                on_ready=(lambda ready: [callback(ready) for callback in callbacks])
                if callbacks else None)

    def _on_ollama_model_chosen(self) -> None:
        """A model picked in the box is prepared at once (offered for download
        when missing), when Ollama is the translation engine."""
        if self._translation_engine.get() == "llm_ollama":
            self._ensure_ollama_ready_async()
        self._refresh_live_heavy_model_hint()

    def _refresh_live_heavy_model_hint(self) -> None:
        """Proactive hint on the live bar when a heavy Ollama model is chosen.

        A large model (e.g. qwen3:32b) loads slowly and misses the per-sentence
        timeout, so every subtitle would stay in the source language. Shown in
        the bar's banner area (never a modal), only while no session is running
        (a running session drives the banner from its own warnings), never in
        place of an error, and dropped as soon as a lighter model or another
        engine is picked.
        """
        bar = getattr(self, "_live_bar", None)
        if bar is None:
            return
        hint_key = "live_hint_heavy_model"
        engine = bar.current_settings().get("engine")
        model = self._ollama_model_var.get().strip()
        heavy = engine == "ollama" and _g._is_model_heavy_for_live(model)
        if heavy and self._live_session is None:
            # An error (a failed session, a refused start) stays up until the
            # user closes it or a new session starts: the hint in its place
            # would hide why the session failed. One rule for every caller.
            if not bar.current_banner_is_error():
                bar.show_banner(hint_key, {"model": model})
        elif bar.current_banner_key() == hint_key:
            bar.clear_banner()

    # -- Hardware-aware model selection ('Models for this PC') -------------------

    def _current_model_choices(self) -> dict:
        """The models in use, per stage, as option keys of the model catalogue."""
        engine = self._translation_engine.get()
        mt = ((self._ollama_model_var.get().strip() or "qwen3:8b")
              if engine == "llm_ollama" else engine)
        live = _g._player_settings_module.normalize_live_settings(_g.load_config()).asr_model
        if live == "auto":                  # PersistentWhisper's own default
            live = "large-v3-turbo" if _g.shutil.which("nvidia-smi") else "small"
        tts = ("voicebox" if self._use_voicebox.get()
               else "xtts" if self._use_xtts.get() else "edge")
        return {"asr": self._model.get(), "asr_live": live, "mt": mt, "tts": tts}

    def _set_model_choices(self, choices: dict) -> None:
        """Put per-stage choices into the GUI variables and the live settings."""
        if choices.get("asr") in _g.WHISPER_MODELS:
            self._model.set(choices["asr"])
        mt = choices.get("mt")
        live_engine = None
        if mt in ("google", "deepl", "marian"):
            self._translation_engine.set(mt)
            live_engine = mt
        elif isinstance(mt, str) and mt.startswith("qwen3"):
            self._translation_engine.set("llm_ollama")
            self._ollama_model_var.set(mt)
            live_engine = "ollama"
        if choices.get("tts") in ("edge", "xtts", "voicebox"):
            self._use_xtts.set(choices["tts"] == "xtts")
            self._use_voicebox.set(choices["tts"] == "voicebox")
        update = {}
        if choices.get("asr_live") in _g._player_settings_module.LIVE_ASR_MODELS:
            update["live_asr_model"] = choices["asr_live"]
        if live_engine is not None:
            update["live_engine"] = live_engine
        if mt and live_engine == "ollama":
            update["ollama_model"] = mt
        if update:
            _g.save_config(update)
            if live_engine is not None:
                self._live_bar.set_config_values(
                    _g._player_settings_module.normalize_live_settings(_g.load_config()))
        self._active_profile.set("custom")    # no preset highlighted
        self._on_engine_change()
        self._update_profile_buttons()
        self._update_start_summary()
        self._refresh_live_heavy_model_hint()

    def _apply_model_choices(self, choices: dict) -> None:
        """Apply from the window, keeping what it replaces for Restore previous."""
        _g.save_config({_g._MODELS_PREVIOUS_KEY: self._current_model_choices(),
                     _g._MODELS_CHOICE_KEY: dict(choices)})
        self._set_model_choices(choices)
        self._models_choice_restored = True

    def _revert_model_choices(self) -> dict | None:
        """Swap back to the choices before the last Apply (None if there are none)."""
        previous = _g.load_config().get(_g._MODELS_PREVIOUS_KEY)
        if not isinstance(previous, dict) or not previous:
            return None
        current = self._current_model_choices()
        self._set_model_choices(previous)
        _g.save_config({_g._MODELS_PREVIOUS_KEY: current, _g._MODELS_CHOICE_KEY: dict(previous)})
        self._models_choice_restored = True
        return dict(previous)

    def _restore_model_choices(self) -> None:
        """At startup: re-apply the models chosen in the window last time."""
        if self._destroying:
            return
        choices = _g.load_config().get(_g._MODELS_CHOICE_KEY)
        if isinstance(choices, dict) and choices:
            try:
                self._set_model_choices(choices)
                self._models_choice_restored = True
            except Exception as exc:                 # noqa: BLE001
                print(f"     ! Could not restore the chosen models: {exc}", flush=True)
                return
            # The session header logged the job before this restore: log what
            # it is now, or the log names an engine the job will not use.
            with _g.contextlib.suppress(Exception):
                self._log_line("job", self._summary_var.get())

    def _benchmark_media_path(self) -> str | None:
        """Local media for the model benchmark: the player's, else the first file."""
        path = self._live_media_path()
        if path:
            return path
        for candidate in self._batch_files:
            if _g.Path(candidate).is_file():
                return candidate
        return None

    # -- Voicebox (voice cloning by a separate local server) ---------------------

    def _on_voice_clone_toggle(self, which: str) -> None:
        """XTTS and Voicebox both clone the voice: only one can be on."""
        if which == "voicebox" and self._use_voicebox.get():
            self._use_xtts.set(False)
            self._save_voicebox_settings()
        elif which == "xtts" and self._use_xtts.get():
            self._use_voicebox.set(False)
        self._update_start_summary()

    def _save_voicebox_settings(self) -> None:
        _g.save_config({"voicebox_url": self._voicebox_url_var.get().strip(),
                     "voicebox_engine": self._voicebox_engine_var.get()})

    def _check_voicebox(self) -> None:
        """Ask the Voicebox server for its health, off the Tk thread."""
        from videotranslator import voicebox_engine as vbe
        url = self._voicebox_url_var.get().strip() or vbe.DEFAULT_URL
        if not vbe.is_local_url(url):
            self._vb_status(self._s("vb_not_local"), "warn")
            return
        self._save_voicebox_settings()
        self._vb_status(self._s("vb_checking") + f" ({url}, {self._voicebox_engine_var.get()})")
        self._btn_vb_check.configure(state="disabled")

        def work() -> None:
            # Network only here; the text is built on the Tk thread (self._s
            # reads a Tk variable).
            try:
                device = vbe.describe_health(vbe.VoiceboxClient(url).health())
            except Exception:                         # noqa: BLE001
                device = None
            self.after(0, self._show_voicebox_check, url, device)

        _g.threading.Thread(target=work, name="voicebox-check", daemon=True).start()

    def _show_voicebox_check(self, url: str, device: str | None) -> None:
        if self._destroying:
            return
        text = (self._s("vb_ok").format(device=device) if device is not None
                else self._s("vb_unreachable").format(url=url))
        self._vb_status(text, "info" if device is not None else "warn")
        self._btn_vb_check.configure(state="normal")

    def _warn_if_voicebox_down(self) -> None:
        """At job start, say at once (not at step 5) if Voicebox is not answering."""
        from videotranslator import voicebox_engine as vbe
        url = self._voicebox_url_var.get().strip() or vbe.DEFAULT_URL
        text = self._s("vb_fallback_warn").format(url=url)   # built on the Tk thread

        def work() -> None:
            try:
                vbe.VoiceboxClient(url).health()
            except Exception:                          # noqa: BLE001
                self._post_if_alive(lambda: self._vb_status(text, "warn"))

        _g.threading.Thread(target=work, name="voicebox-precheck", daemon=True).start()

    def _vb_status(self, text: str, level: str = "info") -> None:
        self._lbl_vb_status.configure(text=text)
        self._log_line("voicebox", text, level)

    # -- Ollama check ------------------------------------------------------------

    _OLLAMA_CHECK_TEXTS = {
        "ready": ("ollama_ready", "info"),
        "fallback": ("ollama_fallback", "warn"),
        "missing": ("ollama_missing", "info"),
        "stopped": ("ollama_stopped", "info"),
        "absent": ("ollama_absent", "info"),
        "unreachable": ("ollama_unreachable", "warn"),
    }

    def _check_ollama(self) -> None:
        """Ask Ollama whether it answers and has the chosen model, off the Tk
        thread. Read only: the translation starts, installs or pulls what is
        missing; this only says what it will find."""
        url = self._ollama_url_var.get().strip() or "http://localhost:11434"
        model = self._ollama_model_var.get().strip()
        self._ollama_status(self._s("ollama_checking") + f" ({url}, {model})")
        self._btn_ollama_check.configure(state="disabled")

        def work() -> None:
            # Network only here; the text is built on the Tk thread (self._s
            # reads a Tk variable).
            try:
                result = _g._check_ollama_status(url, model)
            except Exception:                         # noqa: BLE001
                result = None
            self.after(0, self._show_ollama_check, url, model, result)

        _g.threading.Thread(target=work, name="ollama-check", daemon=True).start()

    # Header dot per check state: ready lights it, another model answers in
    # amber, anything else leaves it off (the tip says why).
    _OLLAMA_BADGE_LEVELS = {"ready": "ok", "fallback": "warn"}

    def _ollama_check_text(self, url: str, model: str, result) -> tuple[str, str, str]:
        """(state, text, level) for a check_ollama answer, in the UI language. Tk thread."""
        state = result.state if result is not None else "unreachable"
        key, level = self._OLLAMA_CHECK_TEXTS.get(state, ("ollama_unreachable", "warn"))
        version = getattr(result, "version", "")
        text = self._s(key).format(
            ollama=f"Ollama {version}" if version else "Ollama", url=url, model=model,
            other=getattr(result, "model", "") or model)
        return state, text, level

    def _set_ollama_badge(self, level: str | None, text: str) -> None:
        """Tk thread: colour the header dot ("ok", "warn", None = off) and keep
        ``text`` for its tip. Safe before the header exists."""
        dot = getattr(self, "_ollama_badge_dot", None)
        if dot is None:
            return
        dot.configure(fg={"ok": _g.OK, "warn": _g.WARN}.get(level, _g.FG2))
        self._ollama_badge_text = text

    def _ollama_badge_from_check(self, url: str, model: str, result) -> None:
        """Tk thread: the startup check reaches the header dot only, no log line."""
        state, text, _level = self._ollama_check_text(url, model, result)
        self._set_ollama_badge(self._OLLAMA_BADGE_LEVELS.get(state), text)

    def _show_ollama_check(self, url: str, model: str, result) -> None:
        if self._destroying:
            return
        state, text, level = self._ollama_check_text(url, model, result)
        self._ollama_status(text, level)
        self._set_ollama_badge(self._OLLAMA_BADGE_LEVELS.get(state), text)
        self._btn_ollama_check.configure(state="normal")

    def _ollama_status(self, text: str, level: str = "info") -> None:
        self._lbl_ollama_status.configure(text=text)
        self._log_line("ollama", text, level)

    # -- ElevenLabs live voice ---------------------------------------------------

    _ELEVENLABS_KEY = "elevenlabs"          # config: settings + catalogue, no secret

    def _elevenlabs_settings(self) -> dict:
        value = _g.load_config().get(self._ELEVENLABS_KEY)
        return dict(value) if isinstance(value, dict) else {}

    def _save_elevenlabs_settings(self, settings: dict, api_key: str) -> None:
        _g.save_config({self._ELEVENLABS_KEY: dict(settings)})
        if api_key and _g.save_elevenlabs_key(api_key) == "session":
            self._log_line("app", self._s("msg_secret_session_only"), level="warn")
        self._refresh_live_voice_info()

    def _live_tts_opts(self) -> dict | None:
        """ElevenLabs options for a live session, or None for Edge-TTS."""
        settings = self._elevenlabs_settings()
        if not settings.get("enabled"):
            return None
        key = _g.load_elevenlabs_key()
        if not (key and settings.get("voice_id") and settings.get("model_id")):
            self._log_line("elevenlabs", self._s("live_voice_el_nokey"))
            return None
        return {"engine": "elevenlabs", "api_key": key,
                "voice_id": settings["voice_id"], "model_id": settings["model_id"],
                "fallback": bool(settings.get("fallback", True))}

    def _live_voice_info_text(self) -> str:
        """Which voice the live dub will use, in the UI language."""
        bar = getattr(self, "_live_bar", None)
        if bar is not None and not bar.current_settings().get("dub", True):
            return self._s("live_voice_off")
        settings = self._elevenlabs_settings()
        if settings.get("enabled"):
            if _g.load_elevenlabs_key() and settings.get("voice_id") and settings.get("model_id"):
                return self._s("live_voice_el").format(
                    voice=settings.get("voice_name") or settings["voice_id"])
            return self._s("live_voice_el_nokey")
        return self._s("live_voice_edge").format(
            voice=self._live_voice_for(self._lang_tgt.get()))

    def _refresh_live_voice_info(self) -> None:
        bar = getattr(self, "_live_bar", None)
        if bar is None:
            return
        with _g.contextlib.suppress(Exception):
            bar.set_voice_info(self._live_voice_info_text())

    def _open_elevenlabs_dialog(self) -> None:
        dialog = getattr(self, "_elevenlabs_dialog", None)
        if dialog is not None and not dialog.closed:
            dialog.win.lift()
            return
        from videotranslator.elevenlabs_dialog_tk import ElevenLabsDialog
        self._log_event("log_window", title=self._s("el_title"))
        self._elevenlabs_dialog = ElevenLabsDialog(
            self, ui_s=self._s, theme=self._theme, make_button=self._flat_btn,
            settings=self._elevenlabs_settings(), api_key=_g.load_elevenlabs_key(),
            target_lang=self._lang_tgt.get(), on_save=self._save_elevenlabs_settings,
            preview_hub=self._voice_preview_hub,
            log=lambda text, level="info": self._log_line("elevenlabs", text, level))

    def _open_models_dialog(self) -> None:
        dialog = self._models_dialog
        if dialog is not None and not dialog.closed:
            dialog.win.lift()
            return
        from videotranslator.models_dialog_tk import ModelsDialog
        self._log_event("log_window", title=self._s("mdl_title"))
        self._models_dialog = ModelsDialog(
            self, ui_s=self._s, theme=self._theme, make_button=self._flat_btn,
            current=self._current_model_choices(), on_apply=self._apply_model_choices,
            on_revert=self._revert_model_choices, media_path=self._benchmark_media_path,
            busy=lambda: bool(self._running) or self._live_session is not None,
            log=lambda text, level="info": self._log_line("models", text, level))
    def _ollama_setup_worker(self, model: str, url: str, auto_install: bool,
                             texts: dict) -> bool:
        """Worker thread: runs steps 1-4. Returns True if Ollama is ready.

        This is the heart of the flow - each step has a precise early-exit
        so that no state accumulates, and every popup is forwarded to the main
        thread via `_ask_yes_no_sync` (blocks the worker until the user
        responds, but the GUI stays fluid).
        """
        # Step 1: binary detection
        binary = _g._ollama_find_binary()
        if not binary:
            self._log_async("[*] Ollama non trovato sul sistema.\n")
            if not auto_install:
                self._log_async(
                    "[i] ollama_auto_install=false → fallback Google se userai llm_ollama.\n"
                )
                return False
            if not self._ask_yes_no_sync("Ollama", texts["ollama_install_ask"]):
                self._log_async("[i] Install rifiutato. Fallback Google attivo.\n")
                return False
            self._log_async("[*] Installazione Ollama in corso...\n")
            ok, msg = _g._ollama_install(log_cb=self._log_async)
            if not ok:
                self._log_async(f"[x] Installazione fallita: {msg}\n")
                return False
            binary = _g._ollama_find_binary()
            if not binary:
                self._log_async(
                    "[x] Ollama installato ma binary non trovato nel PATH. "
                    "Riavvia la GUI per forzare il reload del PATH.\n"
                )
                return False
            self._log_async(f"[+] Ollama installato: {binary}\n")
        else:
            self._log_async(f"[+] Ollama trovato: {binary}\n")

        # Step 2: daemon running?
        # Quick check first (cheap when daemon is already up - common on second runs).
        if _g._ollama_is_daemon_running(url, timeout=2.0):
            self._log_async(f"[+] Ollama daemon gia' attivo su {url}\n")
        else:
            # If we just installed Ollama, the desktop app on Windows starts its
            # embedded daemon with a 5-10s delay. Wait for it before falling back
            # to `ollama serve` (which would EADDRINUSE-fail against the desktop daemon).
            self._log_async(
                "[*] Daemon non ancora attivo, attesa fino a 12s "
                "(Ollama Desktop puo' avviare il proprio daemon in background)...\n"
            )
            if _g._ollama_wait_for_daemon(url, wait_seconds=12.0):
                self._log_async(f"[+] Ollama daemon attivo su {url} (avviato dall'app desktop)\n")
            else:
                self._log_async("[*] Avvio daemon Ollama (ollama serve)...\n")
                ok, msg = _g._ollama_start_daemon(
                    binary, api_url=url, wait_seconds=15.0, log_cb=self._log_async
                )
                # A port already held by a running daemon (Ollama Desktop) is
                # recognised inside _ollama_start_daemon, which then returns ok:
                # this message only carries the log path, never the error text.
                if not ok:
                    self._log_async(f"[x] Daemon non avviato: {msg}\n")
                    return False

        # Step 3: the model. The one in the box is the user's choice: when it
        # is not downloaded, offer it (once a session per model), even when
        # another compatible model is installed. A "No" keeps that model, or
        # Google when there is none.
        health_ok, health_msg, resolved_model = _g._ollama_health_check(url, model, timeout=5.0)
        msg_lower = (health_msg or "").lower()
        if not health_ok and ("not reachable" in msg_lower or "invalid json" in msg_lower):
            self._log_async(f"[x] Ollama non raggiungibile: {health_msg}\n")
            return False
        if not (health_ok and resolved_model == model):
            fallback = resolved_model if health_ok else ""
            ask = auto_install and model not in self._ollama_pull_declined
            # Checked like the models window checks it: a model that does not
            # fit the disk is not offered (it would fill it), one too big for
            # the memory is offered with a warning (it could freeze the PC).
            fit = self._ollama_pull_fit(model) if ask else None
            if fit is not None and fit.verdict == "no_disk":
                warning = _g._ollama_no_disk_text(texts, model, fallback, fit)
                self._log_async(f"[!] {warning.splitlines()[0]}\n")
                self._post_if_alive(
                    lambda: _g.messagebox.showwarning("Ollama", warning, parent=self))
                ask = False
            if fit is not None and fit.verdict in ("too_big", "tight"):
                self._ollama_memory_checked.add(model)     # the question says it
            if ask and self._ask_yes_no_sync("Ollama",
                                             _g._ollama_pull_question(texts, model, fallback, fit)):
                ok, msg = _g._ollama_pull_model(model, binary=binary, log_cb=self._log_async,
                                             api_url=url)
                if ok:
                    health_ok, health_msg, resolved_model = _g._ollama_health_check(
                        url, model, timeout=5.0)
                    if not health_ok:
                        self._log_async(f"[x] Verifica post-pull fallita: {health_msg}\n")
                        return False
                else:
                    self._log_async(f"[x] ollama pull fallito: {msg}\n")
            elif ask:
                self._ollama_pull_declined.add(model)
            if not (health_ok and resolved_model):
                self._log_async(f"[i] {model} non scaricato: fallback Google.\n")
                return False
            if resolved_model != model:
                self._log_async(f"[!] {health_msg}\n")

        # The model is there: warn once a session when it is too big for the
        # memory (the PC would swap until it froze; seen with qwen3:32b on a
        # 12 GB VM without a GPU).
        if resolved_model and resolved_model not in self._ollama_memory_checked:
            self._ollama_memory_checked.add(resolved_model)
            heavy = self._ollama_pull_fit(resolved_model, installed=True)
            if heavy is not None and heavy.verdict == "too_big":
                have = "?" if heavy.have_gb is None else f"{heavy.have_gb:.1f}"
                warning = texts["ollama_pull_heavy"].format(
                    model=resolved_model, need=f"{heavy.need_gb:g}", have=have)
                self._log_async(f"[!] {warning}\n")
                self._post_if_alive(
                    lambda: _g.messagebox.showwarning("Ollama", warning, parent=self))

        self._log_async(f"[+] Ollama pronto: {resolved_model or model} @ {url}\n")
        self._ollama_ready_note = (url, resolved_model or model)   # the header dot, in _ollama_setup_done
        return True

    def _ask_yes_no_now(self, title: str, message: str) -> bool:
        """Tk thread: the Yes/No box, with the question's first line and the
        answer logged (a native dialog leaves no other trace in the log)."""
        answer = bool(_g.messagebox.askyesno(title, message, parent=self))
        first = message.strip().splitlines()[0] if message.strip() else ""
        self._log_line("ui", f"{title}: {first} → {'✓' if answer else '✗'}")
        return answer

    def _ask_yes_no_sync(self, title: str, message: str) -> bool:
        """Call messagebox.askyesno on the main thread and block the worker
        until the user responds. Uses an Event for the rendezvous.
        """
        if self._destroying:
            return False
        result: dict[str, bool] = {"v": False}
        done = _g.threading.Event()

        def _prompt():
            try:
                result["v"] = self._ask_yes_no_now(title, message)
            finally:
                done.set()

        self.after(0, _prompt)
        # Wait up to 5 minutes - beyond that the dialog has likely been lost.
        done.wait(timeout=300)
        return result["v"]

    def _check_marian_deps(self):
        """Check sacremoses/sentencepiece; offer pip install if missing."""
        missing = [
            pkg for pkg in ("sacremoses", "sentencepiece")
            if _g.importlib.util.find_spec(pkg) is None
        ]
        if not missing:
            return
        pkg_list = "\n  • ".join(missing)
        msg = (
            f"MarianMT richiede pacchetti aggiuntivi:\n  • {pkg_list}\n\n"
            f"Verranno installati con pip (--break-system-packages)."
            f"{self._s('msg_deps_install')}"
        )
        if _g.messagebox.askyesno(self._s("msg_deps_missing"), msg):
            self._install_deps(missing)
        else:
            self._translation_engine.set("google")
            self._deepl_row.grid_remove()
