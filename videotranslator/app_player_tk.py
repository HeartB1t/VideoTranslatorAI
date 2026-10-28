"""Embedded player: status, commands, fallback and install (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class PlayerMixin:
    def _log_async(self, text: str) -> None:
        """Thread-safe helper: schedula log_write sul main thread."""
        if not self._destroying:
            self.after(0, self._log_write, text)

    def _redirecting_thread_factory(self, target, name=None, daemon=True):
        """Return a Thread that runs ``target`` with the GUI log redirect installed.

        Library output of worker threads (pip, tqdm, warnings) then reaches
        the log panel instead of the original stream, which is None under
        pythonw (spec 2.4, R9). Call-compatible with threading.Thread.
        """
        def run():
            _g._thread_local.redirect = _g._TkStreamRedirect(self, self._log_write)
            try:
                target()
            finally:
                _g._thread_local.redirect = None

        return _g.threading.Thread(target=run, name=name, daemon=daemon)


    # -- Integrated player: availability and install (spec 9 P1) ------------

    def _live_bar_log(self, text: str, level: str = "info") -> None:
        """Messages of the real-time bar (warnings and errors with their level)."""
        self._log_line("live", text, level)

    def _player_log(self, *parts) -> None:
        """Log callback of the player modules: one English line without newline."""
        line = str(parts[-1]) if parts else ""
        self._log_async(line + "\n")

    def _post_if_alive(self, fn) -> None:
        """Run ``fn`` on the Tk thread unless the window is closing.

        Called from worker threads. Tkinter raises RuntimeError ("main thread
        is not in main loop") once mainloop has ended during shutdown; the
        result is then dropped, as _TkStreamRedirect already does.
        """
        if not self._destroying:
            with _g.contextlib.suppress(RuntimeError):
                self.after(0, fn)

    def _player_status_text(self) -> str:
        panel = getattr(self, "_player_panel", None)
        return panel.status_text() if panel is not None else self._s("player_badge")

    def _refresh_player_status(self, *, force_probe: bool = False) -> None:
        """Check libmpv and python-mpv on a worker. libmpv is never loaded here.

        quick_presence only looks for the files; the probe runs in a child
        process (a crashing library cannot take the app down) and only when
        the cached result does not match the library on disk, or after an
        install (plan decision 2).
        """
        cached = _g.load_config().get("player_probe")

        def work():
            try:
                status = _g._libmpv_runtime.resolve_status(cached=cached, force_probe=force_probe)
                request = _g._system_packages.player_install_request(
                    status, sys_platform=_g.sys.platform,
                    mpv_importable=_g.importlib.util.find_spec("mpv") is not None)
            except Exception as exc:  # the badge must never stay grey without a reason
                status = _g._libmpv_runtime.LibmpvStatus(
                    ok=False, reason="probe-crashed", detail=f"status check failed: {exc}")
                request = _g._system_packages.PlayerInstallRequest()
            self._post_if_alive(lambda: self._on_player_status(status, request))

        self._redirecting_thread_factory(work, name="player-status").start()

    def _on_player_status(self, status, request) -> None:
        self._player_status = status
        self._player_install_request = request
        entry = _g._libmpv_runtime.cache_entry(status)
        if entry is not None and _g.load_config().get("player_probe") != entry:
            _g.save_config({"player_probe": entry})  # config writes stay on the Tk thread
        self._update_player_badge()
        if (self._settings_win is not None and self._settings_win.winfo_exists()
                and hasattr(self, "_player_credits_label")):
            self._player_credits_label.configure(text=self._player_panel.status_text())
        if status.ok:
            if self._player_controller.state.item is None:
                self._player_panel.show_ready(status)
            else:
                self._player_panel.render(
                    self._player_controller.state,
                    position=self._player_controller.state.position)
                self._ensure_player()
        else:
            self._player_panel.show_unavailable(status, install_cmd=request.manual_command)

    def _maybe_auto_install_player(self, status) -> bool:
        """Avvia da solo l'install del player quando l'utente mostra l'intento
        di usarlo (seleziona/carica un media, avvia il live) e il player manca
        ed e' installabile. Stesso spirito di ``ollama_auto_install``, che parte
        solo quando l'utente sceglie il motore Ollama, non all'avvio. Il bottone
        "Installa player" resta come fallback manuale.

        Chiamata SEMPRE dai punti di intento (``_ensure_or_show_player_status``,
        avvio live), MAI dal refresh del badge all'avvio: cosi' non si scarica
        nulla ne' si lancia ``pkexec`` senza che l'utente voglia il player.

        Gira sul thread Tk; l'install parte off-thread dentro ``_install_player``,
        quindi la UI non si blocca. Ritorna True se ha avviato un install.
        """
        # Guardie a basso costo prima: gia' tentato o install in corso.
        if self._player_auto_tried or self._installing:
            return False
        # Criterio "installabile": la stessa API che governa il bottone nel
        # pannello (player_panel_tk._render -> offers_install). Cosi' l'auto
        # parte esattamente nei casi in cui il bottone sarebbe cliccabile.
        if not _g._libmpv_runtime.offers_install(status, sys_platform=_g.sys.platform):
            return False
        if not _g.load_config().get("player_auto_install", True):
            return False
        # Segna il tentativo PRIMA di avviare: una volta per sessione, anche se
        # l'install fallisce e lo stato non-ok viene riletto (niente loop).
        self._player_auto_tried = True
        self._player_log("[*] Video player missing: starting automatic installation...")
        self._install_player(auto=True)
        return True

    def _update_player_badge(self) -> None:
        level = _g._libmpv_runtime.badge_level(self._player_status) if self._player_status else None
        self._player_badge_dot.configure(fg={"ok": _g.OK, "warn": _g.WARN, "error": _g.ERR}.get(level, _g.FG2))

    def _on_player_command(self, name: str, args: dict) -> None:
        """Route PlayerPanel intents on Tk; the controller owns player state."""
        detail = " ".join(f"{k}={v}" for k, v in (args or {}).items())
        self._log_event("log_player", command=f"{name} {detail}".strip())
        if name == "install":
            self._install_player()
            return
        controller = self._player_controller
        session = self._live_session
        # Transport buttons do nothing without media: say why instead of
        # staying silent (previous/next still load from a non-empty playlist).
        needs_media = name in ("play_pause", "stop", "back_10", "forward_10", "seek",
                               "snapshot", "toggle_audio", "toggle_subtitles")
        if (session is None and controller.state.item is None
                and (needs_media or (name in ("previous", "next")
                                     and not controller.has_playlist))):
            self._player_log(self._s("player_no_media_hint"))
            return
        if name == "play_pause":
            if session is not None:
                session.toggle_user_pause()
            else:
                controller.play_pause()
        elif name == "stop":
            if session is not None:
                self._stop_live_session()
            controller.stop()
        elif name == "previous":
            controller.previous()
        elif name == "next":
            controller.next()
        elif name == "back_10":
            self._player_clock.expect_restart()
            if session is not None:
                target = max(0.0, controller.state.position - 10.0)
                session.notify_user_seek(target)
                controller.seek(target)
            else:
                controller.seek_relative(-10.0)
        elif name == "forward_10":
            self._player_clock.expect_restart()
            if session is not None:
                target = controller.state.position + 10.0
                if controller.state.duration is not None:
                    target = min(target, controller.state.duration)
                session.notify_user_seek(target)
                controller.seek(target)
            else:
                controller.seek_relative(10.0)
        elif name == "seek":
            target = max(0.0, float(args.get("seconds", 0.0)))
            dragging = bool(args.get("dragging", False))
            if session is not None and not dragging:
                session.notify_user_seek(target)
            # Live dragging previews only the bar; one exact seek on release
            # prevents ASR restarts and intermediate playback-restart events.
            # Arm the restart wait only when a seek is actually sent, or a drag
            # with no seek would leave the clock invalid until the next real one.
            if session is None or not dragging:
                self._player_clock.expect_restart()
                controller.seek(target, dragging=dragging)
        elif name == "volume":
            controller.set_volume(int(args.get("value", controller.state.volume)))
        elif name == "toggle_audio":
            target = "original" if controller.state.audio == "dubbed" else "dubbed"
            controller.select_audio(target)
        elif name == "toggle_subtitles":
            controller.set_subtitles_visible(not controller.state.subs_visible)
        elif name == "mute":
            controller.toggle_mute()
        elif name == "snapshot":
            try:
                controller.snapshot(_g._platforms.default_videos_dir(), _g.datetime.datetime.now())
            except (OSError, RuntimeError) as exc:
                self._player_panel.notify(
                    "player_snapshot_failed", {"detail": str(exc), "path": ""})
        elif name == "open_folder":
            item = controller.state.item
            if item is not None and item.kind != "live":
                _g._platforms.reveal_in_file_manager(_g.Path(item.path))
        elif name == "playlist":
            self._player_panel.show_playlist(
                self._source_media_items(), self._player_results,
                job_running=self._running)
        elif name == "load_item":
            item = args.get("item")
            if isinstance(item, _g._player_core.MediaItem):
                items = self._source_media_items() + list(self._player_results)
                index = next((i for i, candidate in enumerate(items)
                              if candidate.path == item.path), None)
                self._player_controller.set_playlist(items, index=index)
                controller.load(item, paused=True)
                self._ensure_or_show_player_status()
        elif name == "fullscreen":
            self._toggle_player_fullscreen(not self._player_fullscreen)

    def _on_player_state(self, state) -> None:
        if state.status == "loading":
            # A new media load ends a running live session: otherwise it keeps
            # decoding the old source and paints its captions on the new video.
            # (At URL-session start the load happens before the session exists,
            # so _live_session is still None here and nothing is stopped.)
            if self._live_session is not None:
                self._stop_live_session()
            self._player_clock.expect_restart()
            self._player_loaded_at = None
            self._player_video_params_seen = False
            self._player_log_lines.clear()
        panel = getattr(self, "_player_panel", None)
        if panel is not None:
            panel.render(state, position=state.position)
        self._refresh_live_bar_enabled()
        if state.item is not None and self._player_backend is not None:
            self._start_player_poll()

    # -- live real-time translation (spec 4, 5.9) ---------------------------

    def _live_media_path(self) -> str | None:
        """The loadable local file currently in the player, or None."""
        if self._player_backend is None:
            return None
        item = self._player_controller.state.item
        if item is None or getattr(item, "kind", None) == "live":
            return None
        return item.path

    def _refresh_live_bar_enabled(self) -> None:
        """Keep Start clickable while idle so a press always gets a response.

        Rather than greying the button when nothing is loaded (a silent dead end),
        it stays enabled and _start_live_session shows a banner telling the user
        to load a video or paste a link.
        """
        bar = getattr(self, "_live_bar", None)
        if bar is None:
            return
        if self._live_session is not None or self._live_resolving:
            return  # a session is running/starting; the bar shows its Stop row
        bar.set_start_enabled(not self._running)

    def _block_if_live_active(self) -> bool:
        """True (and warns) when a live session forbids starting a batch job."""
        if self._live_session is not None:
            _g.messagebox.showwarning(self._s("msg_error_t"), self._s("live_err_busy_job"))
            return True
        return False

    def _on_live_command(self, intent: str, params: dict) -> None:
        """Route LiveBar intents on the Tk thread (mirrors _on_player_command)."""
        self._log_event("log_live", command=intent,
                        value=" ".join(f"{k}={v}" for k, v in (params or {}).items()))
        if intent == "elevenlabs":
            self._open_elevenlabs_dialog()
            return
        if intent == "dub":
            self._refresh_live_voice_info()
        if intent == "start":
            self._start_live_session()
            return
        if intent == "stop":
            self._stop_live_session()
            return
        if intent == "banner_close":
            self._live_bar.clear_banner()
            return
        session = self._live_session
        if intent == "switch_marian":
            # The banner's button: this session goes on with MarianMT (offline,
            # fast on a CPU); the saved engine choice is not touched.
            if session is not None:
                session.set_engine("marian")
                self._live_bar.set_engine_code("marian")
                self._live_bar.clear_banner()
            return
        if intent in ("mode", "delay", "engine", "dub", "subs"):
            # Remember the choice for the next launch (the original mute is
            # deliberately not persisted: it resets with every session).
            self._schedule_live_save()
        if intent == "engine":
            # A heavy Ollama model warrants the proactive hint; any other engine
            # drops it.
            self._refresh_live_heavy_model_hint()
        if session is None:
            return  # settings changed while idle are read at start()
        if intent == "mode":
            session.set_sync_mode(params.get("mode", "delayed"))
        elif intent == "delay":
            session.set_delay(float(params.get("seconds", 0.0)))
        elif intent == "engine":
            session.set_engine(params.get("engine", "marian"))
        elif intent == "dub":
            enabled = bool(params.get("enabled", True))
            session.set_dub_enabled(enabled)
            if enabled:
                # A session started with the dub off has no voice backend: hand it
                # the existing one, or build it (attached when ready).
                if self._voice_backend is not None:
                    session.attach_voice(self._voice_backend)
                else:
                    self._request_voice_backend()
        elif intent == "subs":
            session.set_subs_enabled(bool(params.get("enabled", True)))
        elif intent == "original_mute":
            session.set_original_muted(bool(params.get("muted", False)))

    def _source_media_items(self) -> list[_g._player_core.MediaItem]:
        return [
            _g._player_core.MediaItem(path, "source", _g.Path(path).name)
            for path in self._batch_files
        ]

    def _sync_player_playlist(self) -> None:
        current = self._player_controller.state.item
        items = self._source_media_items() + list(self._player_results)
        index = next((i for i, item in enumerate(items)
                      if current is not None and item.path == current.path), None)
        self._player_controller.set_playlist(items, index=index)

    def _on_job_outputs(self, outputs) -> None:
        """Add completed artifacts to Results and optionally preview the first."""
        if self._destroying or not outputs:
            return
        # With keep_original_audio the dubbed file already carries the original
        # as an embedded track, so A/B switches between the two internal tracks.
        # Passing the source as an external Original track too would be
        # redundant and, if mpv reports the track list after file-loaded, could
        # add a third track. Only offer the external source when NOT embedded;
        # player_core still guards against a double add as a backstop.
        embed_original = self._player_settings.keep_original_audio
        for output in outputs:
            video = getattr(output, "video_path", None)
            if not video:
                continue
            item = _g._player_core.MediaItem(
                path=str(video), kind="dubbed",
                title=getattr(output, "title", None) or _g.Path(video).name,
                source_path=(None if embed_original
                             else getattr(output, "source_path", None)),
                srt_path=getattr(output, "subtitle_path", None),
            )
            self._player_results = [x for x in self._player_results if x.path != item.path]
            self._player_results.append(item)
        self._sync_player_playlist()
        if self._player_settings.autoload_result and outputs:
            first = next((x for x in outputs if getattr(x, "video_path", None)), None)
            if first is not None:
                path = str(first.video_path)
                item = next((x for x in self._player_results if x.path == path), None)
                if item is not None:
                    items = self._source_media_items() + list(self._player_results)
                    index = next((i for i, candidate in enumerate(items)
                                  if candidate.path == item.path), None)
                    self._player_controller.set_playlist(items, index=index)
                    self._player_controller.load(item, paused=True)
                    self._ensure_or_show_player_status()

    def _on_input_select(self, _event=None) -> None:
        selected = self._batch_listbox.curselection()
        if not selected or self._running:
            return
        index = int(selected[0])
        if not 0 <= index < len(self._batch_files):
            return
        self._sync_player_playlist()
        item = self._player_controller.playlist[index]
        self._player_controller.load(item, paused=True)
        self._ensure_or_show_player_status()

    def _ensure_or_show_player_status(self) -> None:
        # Unico punto in cui un'azione dell'utente richiede il player (selezione
        # input, load_item, preview editor, autoload di un risultato, stream live
        # risolto): qui l'intento e' esplicito, quindi e' il posto giusto per
        # avviare l'auto-install se il player manca (non all'avvio).
        if self._player_status is not None and not self._player_status.ok:
            request = self._player_install_request or _g._system_packages.PlayerInstallRequest()
            self._player_panel.show_unavailable(
                self._player_status, install_cmd=request.manual_command)
            self._maybe_auto_install_player(self._player_status)
            return
        self._ensure_player()

    @staticmethod
    def _load_libx11():
        name = _g.ctypes.util.find_library("X11") or "libX11.so.6"
        return _g.ctypes.CDLL(name)

    def _ensure_player(self) -> None:
        if self._destroying or self._player_backend is not None or self._player_init_running:
            return
        status = self._player_status
        if status is None:
            self._refresh_player_status()
            return
        if not status.ok:
            return
        accepted = tuple(status.vo_profiles_ok or ())
        profile = self._player_vo_profile
        if profile not in accepted:
            profile = accepted[0] if accepted else None
        if profile is None:
            return
        wid = self._player_panel.host_wid()
        if (_g.sys.platform.startswith("linux")
                and self.tk.call("tk", "windowingsystem") == "x11"):
            if self._player_guard is None:
                self._player_guard = _g._player_engine.X11ErrorGuard(
                    load_libx11=self._load_libx11)
            self._player_guard.capture()
        self._player_init_running = True

        def work():
            try:
                module = _g._libmpv_runtime.load_mpv()
                backend = _g._player_engine.create_video_backend(
                    wid=wid, bridge=self._player_bridge, mixer=self._player_mixer,
                    vo_profile=profile, mpv_module=module,
                    sys_platform="win32" if _g.sys.platform == "win32" else "linux",
                    log=None)
            except Exception as exc:
                self._post_if_alive(lambda error=exc: self._on_player_init_failed(error))
                return
            if self._destroying:
                backend.terminate(3.0)
                if self._player_guard is not None:
                    self._player_guard.restore()
                return
            self._post_if_alive(lambda: self._on_player_ready(backend, profile))

        self._player_init_thread = self._redirecting_thread_factory(
            work, name="player-init")
        self._player_init_thread.start()

    def _on_player_init_failed(self, exc: BaseException) -> None:
        self._player_init_running = False
        status = _g._libmpv_runtime.LibmpvStatus(
            ok=False, reason="libmpv-load-failed",
            detail=f"player initialization failed: {exc}")
        self._on_player_status(status, _g._system_packages.PlayerInstallRequest())
        self._player_log(f"[!] Player initialization failed: {exc}")

    def _on_player_ready(self, backend, profile: str) -> None:
        self._player_init_running = False
        if self._destroying:
            self._redirecting_thread_factory(
                lambda: backend.terminate(3.0), name="player-late-close").start()
            return
        self._player_backend = backend
        self._player_vo_profile = profile
        self._player_controller.attach_backend(backend)
        with _g.contextlib.suppress(Exception):
            version = ".".join(str(part) for part in (backend.mpv_version or ())) or "?"
            text = self._s("log_sys_player").format(version=version, vo=profile)
            # Technical suffix (no translation): "no" means software decoding,
            # chosen when no real GPU was detected (player_engine.choose_hwdec).
            hwdec = dict(getattr(backend, "options", None) or {}).get("hwdec")
            if hwdec:
                text = f"{text} · hwdec {hwdec}"
            self._log_emit(text, "player")
        self._video_shader_applied = None
        self._apply_video_effect()
        self._start_player_poll()

    def _apply_video_effect(self) -> None:
        """The CRT skins also give the video an 80s monitor look (mpv shader).

        Sent only when it changes for the current backend: a new backend (VO
        fallback) starts without shaders, so it gets it again.
        """
        backend = getattr(self, "_player_backend", None)
        if backend is None or self._theme.palette is None:
            return
        path = _g._shader_for_theme(self._theme.palette.name)
        if getattr(self, "_video_shader_applied", None) == (backend, path):
            return
        if path is None and getattr(self, "_video_shader_applied", None) is None:
            self._video_shader_applied = (backend, None)     # nothing to clear
            return
        with _g.contextlib.suppress(Exception):
            backend.set_shader(path)
        self._video_shader_applied = (backend, path)

    def _live_voice_for(self, tgt: str) -> str:
        """Pick the edge-tts voice for the live dub: the user's if it fits the
        target language, otherwise the language's first catalog voice."""
        voices = _g.LANGUAGES.get(tgt, {}).get("voices", [])
        current = self._voice.get()
        if current in voices:
            return current
        return voices[0] if voices else current

    def _request_voice_backend(self) -> None:
        """Build the second, video-less mpv for the live dub on a worker.

        libmpv never runs on the Tk thread (spec 2.4). One build at a time, once
        per player bridge: the backend shares the player bridge (it writes only
        namespaced values and voice-* events). The result is adopted on Tk only if
        the player backend and bridge are still those it was built for; a running
        session receives it through attach_voice(). A failure turns the session's
        dub off with the TTS warning, subtitles keep working.
        """
        if (self._destroying or self._player_backend is None
                or self._voice_backend is not None):
            return
        with self._voice_lock:
            if self._voice_build_token is not None:
                return                               # a build is already running
            token = object()
            self._voice_build_token = token
        bridge = self._player_bridge
        backend = self._player_backend
        platform_key = "win32" if _g.sys.platform == "win32" else "linux"

        def work():
            try:
                module = _g._libmpv_runtime.load_mpv()
                voice = _g._player_engine.create_voice_backend(
                    bridge=bridge, mpv_module=module, sys_platform=platform_key,
                    log=None)
            except Exception as exc:                 # noqa: BLE001
                with self._voice_lock:
                    current = self._voice_build_token is token
                    if current:
                        self._voice_build_token = None
                if current:
                    self._post_if_alive(
                        lambda error=exc: self._on_voice_backend_failed(error))
                return
            with self._voice_lock:
                adopt = self._voice_build_token is token
                if adopt:
                    self._voice_built = (bridge, backend, voice)
            if not adopt:                            # closed or invalidated meanwhile
                voice.terminate(3.0)
                return
            self._post_if_alive(self._on_voice_backend_ready)

        self._voice_init_thread = self._redirecting_thread_factory(
            work, name="voice-init")
        self._voice_init_thread.start()

    def _take_voice_build(self):
        """Invalidate the build under way and take any result not adopted yet."""
        with self._voice_lock:
            built, self._voice_built = self._voice_built, None
            self._voice_build_token = None
        return None if built is None else built[2]

    def _on_voice_backend_ready(self) -> None:
        with self._voice_lock:
            built, self._voice_built = self._voice_built, None
            self._voice_build_token = None
        if built is None:
            return                                   # taken by close or fallback
        bridge, backend, voice = built
        if (self._destroying or bridge is not self._player_bridge
                or backend is not self._player_backend):
            self._terminate_voice_async(voice)       # built for a replaced player
            return
        self._voice_backend = voice
        session = self._live_session
        if session is not None:
            session.attach_voice(voice)

    def _on_voice_backend_failed(self, exc: BaseException) -> None:
        self._player_log(f"[live] dubbed voice unavailable: {exc}")
        session = self._live_session
        if session is not None:
            session.voice_unavailable()

    def _terminate_voice_async(self, voice) -> None:
        """Terminate a voice mpv off the Tk thread (terminate blocks)."""
        def work():
            with _g.contextlib.suppress(Exception):
                voice.terminate(3.0)
        self._redirecting_thread_factory(work, name="voice-stop").start()

    def _start_player_poll(self) -> None:
        if self._destroying or self._player_poll_after is not None:
            return
        self._player_poll_after = self.after(50, self._player_tick)

    @staticmethod
    def _bridge_value(bridge, name: str, default=None):
        value = bridge.latest(name)
        return default if value is None else value[0]

    def _player_tick(self) -> None:
        self._player_poll_after = None
        if self._destroying or self._player_backend is None:
            return
        now = _g.time.monotonic()
        snapshot = self._player_bridge.drain()
        for event in snapshot.events:
            if event.kind == "playback-restart":
                self._player_clock.on_playback_restart(now)
            elif event.kind == "file-loaded":
                self._player_loaded_at = now
                self._player_video_params_seen = False
            elif event.kind == "mouse" and isinstance(event.payload, tuple):
                action = _g._player_core.mouse_action(*event.payload)
                if action is not None:
                    self._on_player_mouse_action(action)
            elif event.kind == "snapshot-saved":
                self._player_panel.notify("player_snapshot_saved", dict(event.payload or {}))
            elif event.kind == "snapshot-failed":
                self._player_panel.notify("player_snapshot_failed", dict(event.payload or {}))
            elif event.kind == "adapter-error":
                self._player_log(f"[!] mpv adapter: {event.payload}")
            elif event.kind == "log":
                self._log_mpv_line(str(event.payload))
        video_params = snapshot.changed.get("video-params")
        if video_params is not None and video_params[0]:
            self._player_video_params_seen = True
            if self._player_fallback_notice_pending:
                self._player_fallback_notice_pending = False
                _g.save_config({"player_vo_profile": self._player_vo_profile})
                self._player_panel.notify("player_vo_fallback_used", {})
        position_entry = self._player_bridge.latest("time-pos")
        position = None if position_entry is None else position_entry[0]
        stamp = now if position_entry is None else position_entry[1]
        paused = bool(self._bridge_value(self._player_bridge, "pause", True))
        cached = bool(self._bridge_value(self._player_bridge, "paused-for-cache", False))
        seeking = bool(self._bridge_value(self._player_bridge, "seeking", False))
        speed = self._bridge_value(self._player_bridge, "speed", 1.0)
        try:
            speed = float(speed)
        except (TypeError, ValueError):
            speed = 1.0
        self._player_clock.observe(
            position, stamp, speed=speed, running=not paused and not cached,
            seeking=seeking, seen=now)
        clock_now = self._player_clock.now(now)
        self._player_controller.apply_events(snapshot, clock_now)
        self._player_panel.render(self._player_controller.state, position=clock_now)
        if self._player_vo_failed(now):
            self._begin_player_vo_fallback()
            return
        if self._player_controller.state.item is not None:
            self._start_player_poll()

    def _log_mpv_line(self, line: str) -> None:
        """Write one mpv log line to the log panel, collapsing harmless noise."""
        if _g._is_noisy_x11_log(line):
            # mpv floods the log with harmless X11 BadWindow errors while
            # embedded on X11 (its process-global Xlib handler reports
            # expected X errors from Tk or the GL stack); the video
            # renders fine. Log the first full block verbatim (resourceid
            # + request code for diagnosis), then collapse the rest into a
            # periodic summary instead of a line each.
            self._mpv_x11_noise += 1
            stamp = _g.time.monotonic()
            if self._mpv_x11_noise <= 3:
                self._log_write(f"[mpv] {line}\n")
            elif (self._mpv_x11_noise == 4
                    or stamp - self._mpv_x11_noise_at >= 60.0):
                self._mpv_x11_noise_at = stamp
                self._log_write(
                    f"[mpv] harmless X11 window errors during playback "
                    f"({self._mpv_x11_noise} so far, repeats suppressed)\n")
            return
        kind = _g._harmless_mpv_log_kind(line)
        if kind is not None:
            # A known notice that does not affect playback: show it once so it
            # stays visible for diagnosis, then keep it out of the log.
            if kind not in self._mpv_quiet_seen:
                self._mpv_quiet_seen.add(kind)
                self._log_write(f"[mpv] {line}\n")
                self._log_write("[mpv] (harmless: further repeats of this message "
                                "are hidden)\n")
            return
        self._player_log_lines.append(line)
        del self._player_log_lines[:-100]
        self._log_write(f"[mpv] {line}\n")

    def _player_vo_failed(self, now: float) -> bool:
        if self._player_init_running:
            return False
        tracks = self._bridge_value(self._player_bridge, "track-list", [])
        has_video = any(
            isinstance(track, dict) and track.get("type") == "video"
            for track in (tracks or []))
        return _g._player_engine.detect_vo_failure(
            self._player_log_lines,
            video_params_seen=self._player_video_params_seen,
            has_video_track=has_video,
            seconds_since_loaded=(
                0.0 if self._player_loaded_at is None
                else now - self._player_loaded_at))

    def _begin_player_vo_fallback(self) -> None:
        backend = self._player_backend
        if backend is None:
            return
        accepted = tuple(self._player_status.vo_profiles_ok or ()) if self._player_status else ()
        platform_key = "win32" if _g.sys.platform == "win32" else "linux"
        next_profile = _g._player_engine.next_vo_profile(
            platform_key, self._player_vo_profile or "", accepted)
        # Every branch below retires these on its worker before terminating the
        # old backend and closing its bridge; a voice bound to that bridge is
        # never reused (its end-of-clip markers would be lost).
        live, voices = self._detach_live_outputs()
        self._player_controller.detach_backend()
        self._player_backend = None
        self._player_init_running = True
        # The X11 guard must be restored only AFTER the mpv backend is terminated:
        # while mpv is alive its process-global Xlib handler is installed, and
        # restoring Tk's handler now would let an X error on mpv's display reach
        # Tk's default handler (exit(1), no traceback). Every subpath below
        # restores after terminate (_terminate_failed_player, work()).
        if next_profile is None or self._player_vo_retries >= 2:
            self._terminate_failed_player(
                backend, lambda: self._finish_player_vo_failure("video-output-error"),
                live=live, voices=voices)
            return
        if (platform_key == "linux"
                and (self._player_guard is None or not self._player_guard.captured)):
            _g.save_config({"player_vo_profile": next_profile})
            self._terminate_failed_player(
                backend, lambda: self._finish_player_vo_restart_required(next_profile),
                live=live, voices=voices)
            return
        self._player_vo_retries += 1
        wid = self._player_panel.host_wid()

        def work():
            try:
                self._retire_live_outputs(live, voices)
                backend.terminate(3.0)
                self._player_bridge.close()
                if self._player_guard is not None:
                    self._player_guard.restore()
                module = _g._libmpv_runtime.load_mpv()
                replacement_bridge = _g._player_engine.EventBridge()
                replacement = _g._player_engine.create_video_backend(
                    wid=wid, bridge=replacement_bridge, mixer=self._player_mixer,
                    vo_profile=next_profile, mpv_module=module,
                    sys_platform=platform_key, log=None)
            except Exception as exc:
                self._post_if_alive(
                    lambda error=exc: self._on_player_init_failed(error))
                return
            # Hand over under the lock: either a close already started (terminate
            # here, then restore the guard), or the slot holds the replacement
            # until Tk adopts it or a close takes and terminates it.
            with self._fallback_lock:
                adopt = not self._destroying
                if adopt:
                    self._fallback_ready = (replacement, replacement_bridge,
                                            next_profile)
            if not adopt:
                replacement.terminate(3.0)
                if self._player_guard is not None:
                    self._player_guard.restore()
                return
            self._post_if_alive(self._adopt_fallback_player)

        self._player_init_thread = self._redirecting_thread_factory(
            work, name="player-init")
        self._player_init_thread.start()

    def _take_fallback_ready(self):
        with self._fallback_lock:
            ready, self._fallback_ready = self._fallback_ready, None
        return ready

    def _adopt_fallback_player(self) -> None:
        ready = self._take_fallback_ready()
        if ready is not None:                    # else a close already took it
            self._on_player_fallback_ready(*ready)

    def _detach_live_outputs(self):
        """Tk side of a VO fallback: detach what is bound to the old player.

        The live session writes to the old backend and reads the old bridge, and
        the voice mpv posts its end markers on that bridge, which is about to be
        closed and replaced: stop the session (no blocking join on Tk) and take
        every voice backend, adopted or still being built, so none is reused.
        Returns ``(live, voices)`` for _retire_live_outputs on the worker.
        """
        live = self._live_session
        if live is not None:
            self._live_session = None
            self._live_stopping = False
            self._live_startup_pending = False
            if self._live_poll_after is not None:
                with _g.contextlib.suppress(_g.tk.TclError):
                    self.after_cancel(self._live_poll_after)
                self._live_poll_after = None
            with _g.contextlib.suppress(Exception):
                live.request_stop()
            self._live_bar.set_active(False)
            self._refresh_live_bar_enabled()
            self._player_log("[live] stopped: the video output was replaced")
        voices = [v for v in (self._voice_backend, self._take_voice_build())
                  if v is not None]
        self._voice_backend = None
        return live, voices

    @staticmethod
    def _retire_live_outputs(live, voices) -> None:
        """Worker side: the session's threads and the voices go before the backend."""
        if live is not None:
            with _g.contextlib.suppress(Exception):
                live.join(4.0)
        for voice in voices:
            with _g.contextlib.suppress(Exception):
                voice.terminate(3.0)

    def _terminate_failed_player(self, backend, on_done, *, live=None,
                                 voices=()) -> None:
        def work():
            try:
                self._retire_live_outputs(live, voices)
                backend.terminate(3.0)
            finally:
                self._player_bridge.close()
                if self._player_guard is not None:
                    self._player_guard.restore()
                self._post_if_alive(on_done)

        self._player_init_thread = self._redirecting_thread_factory(
            work, name="player-init")
        self._player_init_thread.start()

    def _on_player_fallback_ready(self, backend, bridge, profile: str) -> None:
        self._player_bridge = bridge
        self._player_clock = _g._player_engine.PlaybackClock(log=self._player_log)
        self._player_fallback_notice_pending = True
        self._player_loaded_at = None
        self._player_log_lines.clear()
        self._on_player_ready(backend, profile)

    def _finish_player_vo_failure(self, message_key: str) -> None:
        self._player_init_running = False
        self._player_controller.report_error(message_key)

    def _finish_player_vo_restart_required(self, profile: str) -> None:
        self._player_init_running = False
        self._player_vo_profile = profile
        status = _g.dataclasses.replace(
            self._player_status, ok=False, reason="restart-required",
            detail="video output fallback will be used after restart")
        self._on_player_status(status, _g._system_packages.PlayerInstallRequest())

    def _on_player_mouse_action(self, action: str) -> None:
        with _g.contextlib.suppress(_g.tk.TclError):
            self._player_panel.video_host.focus_set()
        command = {
            "toggle_pause": "play_pause",
            "toggle_fullscreen": "fullscreen",
            "volume_up": "volume_up",
            "volume_down": "volume_down",
        }.get(action)
        if command is not None:
            self._dispatch_player_key_action(command)

    def _widget_is_in_player(self, widget) -> bool:
        current = widget
        while current is not None:
            if current is self._player_panel:
                return True
            current = getattr(current, "master", None)
        return False

    def _on_player_key(self, event):
        focus_in_player = self._widget_is_in_player(getattr(event, "widget", None))
        widget_class = None
        with _g.contextlib.suppress(_g.tk.TclError, AttributeError):
            widget_class = event.widget.winfo_class()
        if not _g._player_core.handles_player_key(
                widget_class, event.keysym, focus_in_player=focus_in_player):
            return None
        action = _g._player_core.PLAYER_KEYS[event.keysym]
        if action == "exit_fullscreen" and not self._player_fullscreen:
            return None
        self._dispatch_player_key_action(action)
        return "break"

    def _dispatch_player_key_action(self, action: str) -> None:
        if action == "volume_up":
            self._on_player_command("volume", {
                "value": self._player_controller.state.volume + 5})
        elif action == "volume_down":
            self._on_player_command("volume", {
                "value": self._player_controller.state.volume - 5})
        elif action == "exit_fullscreen":
            self._toggle_player_fullscreen(False)
        else:
            self._on_player_command(action, {})

    def _toggle_player_fullscreen(self, on: bool) -> None:
        on = bool(on)
        if on == self._player_fullscreen:
            return
        self._player_fullscreen = on
        if on:
            self._header_frame.grid_remove()
            self._right_column.grid_remove()
            self._log_frame.grid_remove()
            self._progress.grid_remove()
            self._body.grid_configure(padx=0, pady=0)
            self._left_pane.grid_configure(padx=0)
            self._player_area.configure(highlightthickness=0)
        else:
            self._header_frame.grid()
            self._right_column.grid()
            self._log_frame.grid()
            self._progress.grid()
            self._body.grid_configure(padx=(16, 0), pady=(8, 8))
            self._left_pane.grid_configure(padx=(0, 16))
            self._player_area.configure(highlightthickness=1)
            if not self._log_visible:
                self._log_container.grid_remove()
        with _g.contextlib.suppress(_g.tk.TclError):
            self.attributes("-fullscreen", on)
        self._player_panel.set_fullscreen_layout(on)

    def _install_player(self, auto: bool = False) -> None:
        # auto=True: chiamata automatica (self-heal), salta le conferme e i
        # popup di errore, coerente con ollama_auto_install che con il flag
        # attivo non chiede conferma a ogni avvio. auto=False (click sul
        # bottone) mantiene il comportamento attuale, conferma inclusa.
        if self._installing:
            if not auto:
                _g.messagebox.showerror(self._s("msg_error_t"), self._s("live_err_busy_install"),
                                     parent=self)
            return
        request = self._player_install_request
        if request is None or request.empty:
            self._refresh_player_status(force_probe=True)
            return
        windows_install = None
        if request.windows_dest is not None:
            if not auto:
                question = self._s("player_install_confirm").format(size=request.download_mb)
                if not _g.messagebox.askyesno(self._s("msg_confirm"), question, parent=self):
                    return
            else:
                self._player_log(
                    f"[*] Auto-install: downloading player components (~{request.download_mb} MB)...")
            dest = request.windows_dest

            def windows_install():
                return _g._libmpv_runtime.install_windows(dest, log=self._player_log)

        self._installing = True
        self._player_panel.show_install_progress("installing")
        self._player_log("[*] Installing the integrated video player...")
        self._player_installer().install(
            pip_packages=request.pip_packages, system_plans=request.system_plans,
            windows_install=windows_install, expect_modules=("mpv",),
            on_done=self._on_player_install_done)

    def _player_installer(self):
        return _g._system_packages.ComponentInstaller(
            runner=lambda cmd: _g._system_packages.run_streaming(cmd, log=self._player_log),
            thread_factory=self._redirecting_thread_factory,
            find_spec=_g.importlib.util.find_spec,
            refresh=_g._system_packages.refresh_import_paths,
            log=self._player_log,
            post=self._post_if_alive)

    def _on_player_install_done(self, result) -> None:
        self._installing = False
        if not result.ok:
            # The placeholder keeps the reason and, on Linux, the manual command.
            self._player_panel.show_install_progress("failed")
            self._player_log(f"[!] Player installation failed at step: {result.failed_step}")
            return
        self._player_panel.show_install_progress("ok")
        if result.restart_required:
            status = _g.dataclasses.replace(
                self._player_status, ok=False, reason="restart-required",
                detail="installed, but not importable until the application restarts")
            self._on_player_status(status, _g._system_packages.PlayerInstallRequest())
            return
        self._refresh_player_status(force_probe=True)
