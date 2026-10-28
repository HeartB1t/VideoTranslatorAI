"""Real-time translation session (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class LiveMixin:
    def _schedule_live_save(self) -> None:
        """Save the live bar choices shortly after the last change.

        Debounced so dragging the delay slider writes the config once, not at
        every step of the drag.
        """
        if self._live_save_after is not None:
            with _g.contextlib.suppress(Exception):
                self.after_cancel(self._live_save_after)
        self._live_save_after = self.after(400, self._save_live_choices)

    def _save_live_choices(self) -> None:
        """Write the live bar choices to the config (read back at startup)."""
        self._live_save_after = None
        try:
            raw = self._live_bar.current_settings()
            delay_key = ("live_file_ahead_s" if self._live_bar.source_kind == "file"
                         else "live_delay_s")
            _g.save_config({
                "live_sync_mode": raw["mode"], "live_engine": raw["engine"],
                "live_dub_enabled": raw["dub"], "live_subs_enabled": raw["subs"],
                delay_key: raw["delay"],
            })
        except Exception as exc:                     # noqa: BLE001
            print(f"     ! Could not save live settings: {exc}", flush=True)

    def _start_live_session(self) -> None:
        if self._live_session is not None or self._live_resolving:
            return
        if self._running:
            self._live_bar.show_banner("live_err_busy_job", is_error=True)
            return
        if self._editor_open:
            self._live_bar.show_banner("live_err_editor_open", is_error=True)
            return
        urls = self._get_urls()
        if urls:                       # a link takes priority over a loaded file
            self._start_live_from_url(urls[0])
            return
        source = self._live_media_path()
        if source is not None:
            # Il live rende i sottotitoli/voce sul player integrato: se manca,
            # non avviare una sessione monca. Avvia (o riprendi) l'auto-install
            # e di' all'utente di riprovare a player pronto, invece di fallire
            # in silenzio.
            if self._player_status is not None and not self._player_status.ok:
                self._maybe_auto_install_player(self._player_status)
                if self._installing:
                    self._live_bar.show_banner("live_player_installing", is_error=False)
                else:
                    self._live_bar.show_banner("player_unavailable_title", is_error=True)
                self._refresh_live_bar_enabled()
                return
            was_paused = self._player_controller.paused
            if not was_paused:
                self._player_controller.play_pause()
            self._launch_live_session(source, "file", title=None,
                                      initial_user_paused=was_paused)
            return
        # Nothing to translate: tell the user instead of doing nothing.
        self._live_bar.show_banner("live_err_no_source", is_error=True)

    def _start_live_from_url(self, url: str) -> None:
        """Resolve a link to a progressive stream, play it, then translate it live."""
        self._live_resolving = True
        self._live_bar.clear_banner()
        self._live_bar.set_start_enabled(False)
        self._player_log(self._s("live_status_connecting"))

        def work():
            try:
                from videotranslator import input_source
                stream_url, title = input_source.resolve_stream_url(
                    url, log_cb=self._player_log)
            except Exception as exc:                 # noqa: BLE001
                self.after(0, self._on_live_resolve_failed, str(exc))
                return
            self.after(0, self._on_live_resolved, stream_url, title)

        self._redirecting_thread_factory(work, name="live-resolve").start()

    def _on_live_resolve_failed(self, detail: str) -> None:
        self._live_resolving = False
        self._player_log(f"[live] resolve failed: {detail}")
        self._live_bar.show_banner("live_err_resolve", {"detail": detail},
                                   is_error=True)
        self._refresh_live_bar_enabled()

    def _on_live_resolved(self, stream_url: str, title: str) -> None:
        # Keep _live_resolving True until _launch_live_session: loading the stream
        # below re-enters _on_player_state/_refresh_live_bar_enabled, which would
        # otherwise re-enable Start while the launch is still pending (a second
        # click reruns yt-dlp). It is cleared in _launch_live_session and on the
        # unavailable/deadline exit of _await_backend_and_launch.
        if self._destroying:
            self._live_resolving = False
            return
        # Load the resolved stream paused while the same URL is translated. The
        # mpv backend is created lazily on first load, so start the session only
        # once it exists (below), not synchronously here.
        item = _g._player_core.MediaItem(path=stream_url, kind="source", title=title)
        self._player_controller.set_playlist([item], index=0)
        # Resolve and load first, but keep the playhead fixed while Whisper,
        # translation and the first dubbed clip warm up.
        self._player_controller.load(item, paused=True)
        self._ensure_or_show_player_status()
        self._pending_live_source = (stream_url, "url", title)
        self._await_backend_and_launch(_g.time.monotonic() + 20.0)

    def _await_backend_and_launch(self, deadline: float) -> None:
        """Wait for the lazily-created mpv backend, then launch the live session."""
        pending = self._pending_live_source
        if self._destroying or pending is None:
            return
        if self._player_backend is not None:
            self._pending_live_source = None
            source, kind, title = pending
            self._launch_live_session(source, kind, title=title)
            return
        unavailable = self._player_status is not None and not self._player_status.ok
        if unavailable or _g.time.monotonic() >= deadline:
            self._pending_live_source = None
            self._live_resolving = False
            # _on_live_resolved -> _ensure_or_show_player_status ha gia' potuto
            # avviare l'auto-install: se e' in corso, dillo (riprova a player
            # pronto) invece del secco "non disponibile".
            if self._installing:
                self._live_bar.show_banner("live_player_installing", is_error=False)
            else:
                self._live_bar.show_banner("player_unavailable_title", is_error=True)
            self._refresh_live_bar_enabled()
            return
        if not self._player_init_running:
            self._ensure_or_show_player_status()   # (re)trigger backend creation
        self.after(150, lambda: self._await_backend_and_launch(deadline))

    def _launch_live_session(self, source: str, source_kind: str, *,
                             title: str | None,
                             initial_user_paused: bool = False) -> None:
        # The launch is the terminal step of a start: clear the resolving flag so
        # the bar reflects the session (or, on failure below, re-enables Start).
        self._live_resolving = False
        raw = self._live_bar.current_settings()
        tgt = self._lang_tgt.get()
        values = {
            "source": source, "source_kind": source_kind,
            "start_at": max(0.0, self._player_controller.state.position - 0.5),
            "lang_source": self._lang_src.get(),
            "lang_target": tgt,
            "voice": self._live_voice_for(tgt),
            "engine": raw["engine"],
            "deepl_key": self._deepl_key_var.get().strip(),
            "ollama_url": self._ollama_url_var.get().strip(),
            "ollama_model": self._ollama_model_var.get().strip(),
            "tts_opts": self._live_tts_opts(),
        }
        # The slider is the file buffer (4-30 s) on files, the stream delay
        # (6-30 s) on links: each has its own key and range.
        delay_key = "live_file_ahead_s" if source_kind == "file" else "live_delay_s"
        settings = _g._player_settings_module.normalize_live_settings({
            "live_sync_mode": raw["mode"], delay_key: raw["delay"],
            "live_engine": raw["engine"], "live_dub_enabled": raw["dub"],
            "live_subs_enabled": raw["subs"],
            # Chosen in the 'Models for this PC' window (not on the bar).
            "live_asr_model": _g.load_config().get("live_asr_model", "auto"),
        })
        cache_dir = _g._platforms.private_temp_dir() / "live"
        # Sweep leftover session dirs from crashed or killed runs so they do not
        # pile up in TEMP (best effort; never blocks a new session).
        with _g.contextlib.suppress(Exception):
            _g._live_session_module.cleanup_stale_sessions(
                cache_dir, owner_alive=_g._live_session_module.default_owner_alive)
        try:
            cfg = _g._live_session_module.build_live_config(
                values, settings=settings, cache_dir=cache_dir, now=_g.time.time())
            factories = _g._live_session_module.build_live_factories(
                cfg, log=self._player_log)
            # The voice mpv is built on a worker: if it is not ready yet, the
            # session starts with the dub pending and receives it later.
            voice_backend = self._voice_backend if raw["dub"] else None
            voice_pending = bool(raw["dub"]) and voice_backend is None
            self._live_session = _g._live_session_module.LiveSession(
                cfg, video=self._player_backend, clock_view=self._player_clock,
                factories=factories, voice=voice_backend,
                voice_pending=voice_pending, log=self._player_log,
                thread_factory=self._redirecting_thread_factory)
            self._live_session.notify_user_pause(initial_user_paused)
            self._live_session.set_original_muted(raw.get("original_mute", False))
            self._live_session.start(startup_hold=True)
        except Exception as exc:                     # noqa: BLE001
            self._player_log(f"[live] start failed: {exc}")
            self._live_session = None
            if not initial_user_paused and self._player_controller.paused:
                self._player_controller.play_pause()
            self._live_bar.show_banner("live_err_internal",
                                       {"detail": str(exc)}, is_error=True)
            self._refresh_live_bar_enabled()
            return
        self._live_bar.clear_banner()
        self._log_event(
            "log_live_start", mode=raw["mode"], engine=raw["engine"],
            asr=getattr(settings, "asr_model", "auto"),
            voice=self._live_voice_info_text())
        self._live_last_status = None
        self._live_startup_pending = True
        self._live_poll_warned = False
        self._live_bar.set_active(True)
        self._live_bar.set_start_enabled(False)
        # A session is running now: drop the proactive heavy-model hint at once
        # (the banner belongs to the session's own warnings from here on).
        self._refresh_live_heavy_model_hint()
        self._schedule_live_poll()
        if voice_pending:
            self._request_voice_backend()        # attached to the session when ready

    def _schedule_live_poll(self) -> None:
        if self._destroying or self._live_session is None:
            return
        self._live_poll_after = self.after(250, self._poll_live_status)

    def _poll_live_status(self) -> None:
        self._live_poll_after = None
        session = self._live_session
        if session is None or self._destroying:
            return
        # A failure in status() or render() must never break the after() chain:
        # otherwise a terminal state is never read, _finish_live_session never
        # runs, the bar stays active and the worker threads are never joined.
        # Log once (the poll repeats at 4 Hz) and keep polling regardless.
        terminal = False
        try:
            status = session.status()
            self._live_last_status = status
            self._live_bar.render(status)
            if getattr(self, "_live_startup_pending", False) and status.startup_ready:
                session.release_startup_hold()
                self._live_startup_pending = False
            terminal = status.state in ("stopped", "failed", "ended")
        except Exception as exc:                     # noqa: BLE001
            if not getattr(self, "_live_poll_warned", False):
                self._live_poll_warned = True
                self._player_log(f"[live] status poll error: {exc}")
        if terminal:
            self._finish_live_session()
            return
        self._schedule_live_poll()

    def _stop_live_session(self) -> None:
        session = self._live_session
        if session is None or self._live_stopping:
            return
        self._live_stopping = True
        session.request_stop()

        def work():
            session.join(5.0)

        self._redirecting_thread_factory(work, name="live-stop").start()

    def _finish_live_session(self) -> None:
        session = self._live_session
        last = getattr(self, "_live_last_status", None)
        if session is not None and last is not None:
            self._log_event("log_live_end", spoken=getattr(last, "voiced", 0),
                            lost=getattr(last, "voice_dropped", 0))
        self._live_last_status = None
        self._live_session = None
        self._live_stopping = False
        if self._live_poll_after is not None:
            with _g.contextlib.suppress(_g.tk.TclError):
                self.after_cancel(self._live_poll_after)
            self._live_poll_after = None
        if session is not None:
            def work():
                session.join(5.0)
            self._redirecting_thread_factory(work, name="live-stop").start()
        self._live_bar.drop_session_warning()
        self._live_bar.set_active(False)
        self._refresh_live_bar_enabled()
        # Back to the choosing state: if a heavy Ollama model is still selected,
        # the proactive hint reappears (guarded by _live_session being None now),
        # unless the session failed: its error, kept above, stays in its place.
        self._refresh_live_heavy_model_hint()
