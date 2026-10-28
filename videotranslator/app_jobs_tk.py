"""Inputs, downloads, audio extraction, editor and batch runs (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class JobsMixin:
    def _on_diarization_toggle(self):
        if self._use_diarization.get():
            self._hf_row.grid()
        else:
            self._hf_row.grid_remove()

    def _on_no_subs(self):
        if self._no_subs.get():
            self._subs_only.set(False)

    # ── File management ──────────────────────────────────────────────────────

    # ── URL field helpers ────────────────────────────────────────────────────

    def _url_focus_in(self, _=None):
        if self._url_placeholder_active:
            self._url_text.delete("1.0", "end")
            self._url_text.configure(fg=_g.FG)
            self._url_placeholder_active = False

    def _url_focus_out(self, _=None):
        if not self._url_text.get("1.0", "end").strip():
            self._url_text.insert("1.0", self._s("url_placeholder"))
            self._url_text.configure(fg=_g.FG2)
            self._url_placeholder_active = True

    def _get_urls(self) -> list[str]:
        if self._url_placeholder_active:
            return []
        raw = self._url_text.get("1.0", "end").strip()
        if not raw:
            return []
        return [u.strip() for u in raw.splitlines() if u.strip()]

    def _start_download(self):
        if self._running or self._ollama_setup_in_flight or self._player_release_pending:
            return
        if self._block_if_live_active():
            return
        urls = self._get_urls()
        if not urls:
            _g.messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_url"))
            return
        # Ollama auto-setup before download (same logic as _start)
        if self._translation_engine.get() == "llm_ollama":
            self._ollama_setup_in_flight = True
            self._btn.configure(state="disabled")
            self._btn_download.configure(state="disabled",
                                         text=self._s("btn_installing"))
            self._log.configure(state="normal")
            self._log.delete("1.0", "end")
            self._log.configure(state="disabled")
            self._log_write("[*] Verifica Ollama in corso...\n")
            self._ensure_ollama_ready_async(
                on_ready=lambda ok: self._start_download_after_ollama(ok, urls)
            )
            return
        self._release_player_then(lambda: self._dispatch_download(urls))

    def _start_download_after_ollama(self, ok: bool, urls: list[str]) -> None:
        # Release the pre-flight guard whether we proceed (dispatch will
        # re-enable at end of pipeline) or return to idle.
        self._ollama_setup_in_flight = False
        if self._destroying or self._running:
            # GUI closed or pipeline already started elsewhere → restore UI state.
            try:
                self._btn.configure(state="normal", text=self._s("btn_start"))
                self._btn_download.configure(state="normal",
                                             text=self._s("btn_download"))
            except _g.tk.TclError:
                pass
            return
        if not ok:
            self._log_write("[i] Ollama non pronto: la pipeline usera' il fallback Google.\n")
        self._release_player_then(lambda: self._dispatch_download(urls))

    def _dispatch_download(self, urls: list[str]) -> None:
        self._running = True
        self._btn.configure(state="disabled")
        self._btn_download.configure(state="disabled", text=self._s("msg_downloading"))
        self._progress.start(12)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        p = self._snapshot_params()

        # Subtitle editor is only supported for a single URL (2-phase pipeline
        # with a blocking UI: it would not make sense in batch mode with multiple URLs).
        editor_requested = bool(self._edit_subs.get())
        use_editor_for_single_url = editor_requested and len(urls) == 1
        if editor_requested and len(urls) > 1:
            self._log_write(
                "[i] Editor sottotitoli supportato solo su singolo URL "
                "- skipping editor for batch URLs.\n"
            )

        def run():
            _g._thread_local.redirect = _g._TkStreamRedirect(self, self._log_write)
            all_ok = True
            error_keys = []
            fallback_count = 0
            from videotranslator.jobs import JobOutput
            outputs = []
            handed_off_to_editor = False
            try:
                for url in urls:
                    self.after(0, self._log_write,
                               f"\n{'─'*50}\n{self._s('log_downloading').format(url)}\n{'─'*50}\n")
                    stable = None
                    try:
                        with _g.tempfile.TemporaryDirectory(prefix="ytdl_") as tmp_dl:
                            video_path = _g.download_youtube(url, tmp_dl)
                            self.after(0, self._log_write,
                                       self._s("log_dl_done").format(_g.Path(video_path).name) + "\n")
                            # Move to a stable path outside the TemporaryDirectory
                            # shutil.move overwrites the placeholder atomically via os.rename
                            fd, stable = _g.tempfile.mkstemp(suffix=".mp4", prefix="yt_")
                            _g.os.close(fd)
                            _g.shutil.move(video_path, stable)
                        # Editor branch: schedule phase 1 (transcribe+translate)
                        # on the main thread and let _start_with_editor /
                        # _run_with_segments / _open_editor (cancel) take care
                        # of cleaning up `stable`. Skip _on_done here - it will
                        # be called by the editor flow when done/aborted.
                        if use_editor_for_single_url:
                            self.after(0, self._log_write,
                                       "[i] Opening subtitle editor - "
                                       "pipeline paused, waiting for user...\n")
                            self.after(0, self._start_with_editor,
                                       stable, stable)
                            handed_off_to_editor = True
                            # Don't delete `stable` in finally: editor owns it.
                            stable = None
                            return
                        cfg = _g.dataclasses.replace(
                            p,
                            video_in=stable,
                            output=p.output if len(urls) == 1 else None,
                        )
                        result = _g.translate_video(**cfg.to_translate_video_kwargs())
                        fallback_count += _g._count_fallback_segments(result)
                        output = JobOutput.from_result(result)
                        if output.video_path:
                            outputs.append(output)
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {type(e).__name__}: {e}\n{_g.traceback.format_exc()}\n")
                        all_ok = False
                        error_keys.append(_g._error_key_for(e))
                    finally:
                        if stable and _g.os.path.exists(stable):
                            try:
                                _g.os.remove(stable)
                            except OSError:
                                pass
            finally:
                _g._thread_local.redirect = None
            if not handed_off_to_editor:
                if outputs:
                    self.after(0, self._on_job_outputs, outputs)
                self.after(0, self._on_done, all_ok,
                           _g._shared_error_key(error_keys), fallback_count)

        _g.threading.Thread(target=run, daemon=True).start()

    def _input_start_dir(self) -> str:
        """Where "Add" opens: the output folder (configured or default), where
        the translated videos are; else the system Videos folder; else home."""
        candidates = []
        with _g.contextlib.suppress(Exception):
            candidates.append(_g._platforms.resolve_output_dir(
                self._output_dir_var.get().strip() or None))
        with _g.contextlib.suppress(Exception):
            candidates.append(_g._platforms.default_videos_dir())
        candidates.append(_g.Path.home())
        for folder in candidates:
            with _g.contextlib.suppress(OSError):
                if folder.is_dir():
                    return str(folder)
        return str(_g.Path.home())

    def _add_files(self):
        start = self._input_start_dir()
        paths = _g.filedialog.askopenfilenames(
            title=self._s("label_video"), initialdir=start,
            filetypes=[("Video", "*.mp4 *.mkv *.webm *.avi *.mov"), ("All", "*.*")]
        )
        for p in paths:
            self._log_event("log_choice", name=self._s("label_video").rstrip(": "), value=p)
            if p not in self._batch_files:
                self._batch_files.append(p)
                self._batch_listbox.insert("end", _g.Path(p).name)
        self._sync_player_playlist()

    def _remove_file(self):
        indexes = tuple(self._batch_listbox.curselection())
        removed = [self._batch_files[i] for i in indexes]
        self._player_controller.remove_items(removed)
        for i in reversed(indexes):
            self._batch_files.pop(i)
            self._batch_listbox.delete(i)
        self._sync_player_playlist()

    def _clear_files(self):
        self._player_controller.remove_items(tuple(self._batch_files))
        self._batch_files.clear()
        self._batch_listbox.delete(0, "end")
        self._sync_player_playlist()

    def _browse_output(self):
        p = _g.filedialog.asksaveasfilename(
            title=self._s("label_output"),
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("All", "*.*")]
        )
        if p:
            self._output_var.set(p)

    def _browse_output_dir(self):
        """Pick the single folder where translated files are written."""
        initial = self._output_dir_var.get().strip() or str(
            _g._platforms.default_output_dir())
        chosen = _g.filedialog.askdirectory(title=self._s("label_output_dir"),
                                         initialdir=initial, mustexist=False)
        if chosen:
            self._output_dir_var.set(chosen)
            self._persist_output_dir()

    def _persist_output_dir(self):
        """Save the configured output folder (empty string means the default)."""
        _g.save_config({"output_dir": self._output_dir_var.get().strip()})

    # ── Audio/music extraction ────────────────────────────────────────────────

    def _current_audio_format_key(self) -> str:
        """Map the selected format label back to its catalogue key."""
        return self._audio_fmt_label_to_key.get(
            self._audio_format_var.get(), "mp3")

    def _on_audio_format_change(self, _event=None) -> None:
        """Enable the bitrate combo only for lossy formats and refill its values."""
        from videotranslator import audio_extract
        fmt_key = self._current_audio_format_key()
        if audio_extract.is_lossy(fmt_key):
            rates = [str(b) for b in audio_extract.allowed_bitrates(fmt_key)]
            self._audio_bitrate_combo.configure(values=rates, state="readonly")
            current = self._audio_bitrate_var.get()
            if current not in rates:
                self._audio_bitrate_var.set(str(audio_extract.default_bitrate(fmt_key)))
        else:
            self._audio_bitrate_var.set("")
            self._audio_bitrate_combo.configure(values=[], state="disabled")

    def _extract_audio(self) -> None:
        """Extract audio from every selected file and every entered URL into the
        output folder, in a worker thread so the UI stays responsive."""
        if self._running or self._ollama_setup_in_flight or self._player_release_pending:
            return
        if self._block_if_live_active():
            return
        from videotranslator import audio_extract

        sources = list(self._batch_files) + self._get_urls()
        if not sources:
            _g.messagebox.showerror(self._s("msg_error_t"),
                                 self._s("msg_no_input_extract"))
            return

        fmt_key = self._current_audio_format_key()
        bitrate = None
        if audio_extract.is_lossy(fmt_key):
            try:
                bitrate = int(self._audio_bitrate_var.get())
            except (ValueError, _g.tk.TclError):
                bitrate = None
        instrumental = bool(self._instrumental_var.get())
        try:
            out_dir = str(_g._platforms.resolve_output_dir(
                self._output_dir_var.get().strip() or None))
        except Exception:
            out_dir = str(_g._platforms.default_output_dir())

        self._running = True
        self._btn.configure(state="disabled")
        self._btn_download.configure(state="disabled")
        self._btn_extract_audio.configure(state="disabled")
        self._progress.start(12)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

        def run():
            _g._thread_local.redirect = _g._TkStreamRedirect(self, self._log_write)
            ok = 0
            fail = 0
            try:
                for src in sources:
                    self.after(0, self._log_write,
                               f"\n{'-'*50}\n"
                               f"{self._s('log_extracting').format(src)}\n"
                               f"{'-'*50}\n")
                    try:
                        out_path = audio_extract.extract_music(
                            src, out_dir, fmt=fmt_key, bitrate=bitrate,
                            instrumental=instrumental,
                            log_cb=lambda line: self.after(
                                0, self._log_write, line + "\n"),
                        )
                        self.after(0, self._log_write, f"[+] {out_path}\n")
                        ok += 1
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {type(e).__name__}: {e}\n")
                        fail += 1
            finally:
                _g._thread_local.redirect = None
            self.after(0, self._on_extract_done, ok, fail)

        _g.threading.Thread(target=run, name="extract-audio", daemon=True).start()

    def _on_extract_done(self, ok: int, fail: int) -> None:
        if self._destroying:
            return
        self._running = False
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        self._btn_download.configure(state="normal", text=self._s("btn_download"))
        self._btn_extract_audio.configure(state="normal",
                                          text=self._s("btn_extract_audio"))
        if fail == 0:
            self._log_write("\n✓ Done!\n")
            _g.messagebox.showinfo(self._s("msg_completed_t"),
                                self._s("msg_extract_done"))
        else:
            _g.messagebox.showerror(self._s("msg_error_t"), self._s("msg_error"))

    # ── Translation start ─────────────────────────────────────────────────────

    def _start(self):
        if self._running or self._ollama_setup_in_flight or self._player_release_pending:
            return
        if self._block_if_live_active():
            return
        if not self._batch_files:
            _g.messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_video"))
            return
        # If engine = llm_ollama, run the setup before starting the real
        # pipeline. On failure (user refuses install, download aborted,
        # daemon won't start) translate_segments automatically falls back
        # to Google - so we proceed regardless.
        if self._translation_engine.get() == "llm_ollama":
            self._ollama_setup_in_flight = True
            self._btn.configure(state="disabled", text=self._s("btn_installing"))
            self._btn_download.configure(state="disabled")
            self._log.configure(state="normal")
            self._log.delete("1.0", "end")
            self._log.configure(state="disabled")
            self._log_write("[*] Verifica Ollama in corso...\n")
            self._ensure_ollama_ready_async(on_ready=lambda ok: self._start_after_ollama(ok))
            return
        self._dispatch_start()

    def _start_after_ollama(self, ok: bool) -> None:
        """Callback after Ollama setup: proceed regardless (Google fallback
        is handled inside the pipeline). If the user closed the window in the
        meantime, skip.
        """
        self._ollama_setup_in_flight = False
        if self._destroying or self._running:
            try:
                self._btn.configure(state="normal", text=self._s("btn_start"))
                self._btn_download.configure(state="normal",
                                             text=self._s("btn_download"))
            except _g.tk.TclError:
                pass
            return
        if not ok:
            self._log_write("[i] Ollama non pronto: la pipeline usera' il fallback Google.\n")
        self._dispatch_start()

    def _dispatch_start(self) -> None:
        """Route to editor or batch - common entry point for _start and
        _start_after_ollama."""
        self._release_player_then(self._dispatch_start_now)

    def _dispatch_start_now(self) -> None:
        if self._edit_subs.get() and len(self._batch_files) == 1:
            self._start_with_editor(self._batch_files[0])
        else:
            self._run_batch(self._batch_files)

    def _release_player_then(self, dispatch) -> None:
        """Release a dubbed output before a job may overwrite it, without blocking Tk."""
        if self._player_release_pending:
            return
        if not self._player_controller.release_for_job():
            dispatch()
            return
        self._player_release_pending = True
        deadline = _g.time.monotonic() + 2.0

        def poll():
            if self._destroying:
                return
            if (self._player_controller.is_released({
                    "idle-active": self._player_bridge.latest("idle-active")})
                    or _g.time.monotonic() >= deadline):
                self._player_release_pending = False
                dispatch()
            else:
                self.after(50, poll)

        poll()

    def _snapshot_params(self, video_in: str = "") -> "TranslationJobConfig":
        """Reads all Tk vars on the main thread and returns an immutable TranslationJobConfig."""
        from videotranslator.jobs import TranslationJobConfig
        try:
            rate = int(round(self._tts_rate.get()))
        except (ValueError, _g.tk.TclError):
            rate = 0
        cfg = _g.load_config()
        # xtts_speed: if the key exists in the JSON config it is an explicit
        # user override; if absent we pass None so that autotune chooses
        # based on the language pair.
        if "xtts_speed" in cfg:
            try:
                xtts_speed = float(cfg["xtts_speed"])
            except (TypeError, ValueError):
                xtts_speed = None
        else:
            xtts_speed = None
        hf_token = self._hf_token_var.get().strip()
        use_diarization = self._use_diarization.get()
        translation_engine = self._translation_engine.get()
        ollama_model = self._ollama_model_var.get().strip() or "qwen3:8b"
        ollama_url = self._ollama_url_var.get().strip() or "http://localhost:11434"
        ollama_slot_aware = bool(self._ollama_slot_aware.get())
        ollama_thinking = bool(self._ollama_thinking.get())
        # Persist HF token for next launch
        if hf_token and use_diarization and _g.save_hf_token(hf_token) == "session":
            self._log_line("app", self._s("msg_secret_session_only"), level="warn")
        # Persist Ollama prefs (model/url/slot_aware/thinking) when the user
        # has selected this engine - so the fields are pre-filled on next launch.
        if self._use_voicebox.get():
            self._save_voicebox_settings()      # the address/engine used last
            self._warn_if_voicebox_down()
        if translation_engine == "llm_ollama":
            try:
                _g.save_config({
                    "ollama_model": ollama_model,
                    "ollama_url": ollama_url,
                    "ollama_slot_aware": ollama_slot_aware,
                    "ollama_thinking": ollama_thinking,
                })
            except Exception as e:
                print(f"[i] Warning: could not persist Ollama prefs: {e}", flush=True)
        return TranslationJobConfig(
            video_in=video_in,
            output=self._output_var.get().strip() or None,
            output_dir=(cfg.get("output_dir") or None),
            model=self._model.get(),
            lang_source=self._lang_src.get(),
            lang_target=self._lang_tgt.get(),
            voice=self._voice.get(),
            tts_rate=f"{rate:+d}%",
            subs_only=self._subs_only.get(),
            no_subs=self._no_subs.get(),
            no_demucs=self._no_demucs.get(),
            tts_engine=("voicebox" if self._use_voicebox.get()
                        else "xtts" if self._use_xtts.get() else "edge"),
            voicebox_url=self._voicebox_url_var.get().strip() or "http://127.0.0.1:17493",
            voicebox_engine=self._voicebox_engine_var.get() or "chatterbox",
            translation_engine=translation_engine,
            deepl_key=self._deepl_key_var.get().strip(),
            use_diarization=use_diarization,
            hf_token=hf_token,
            use_lipsync=self._use_lipsync.get(),
            xtts_speed=xtts_speed,
            # Hotwords parsed to normalized list (None if empty), so
            # translate_video keeps the unbiased decoder default.
            hotwords=_g._parse_hotwords_gui(self._hotwords_var.get()) or None,
            ollama_model=ollama_model,
            ollama_url=ollama_url,
            ollama_slot_aware=ollama_slot_aware,
            ollama_thinking=ollama_thinking,
            keep_original_audio=self._player_settings.keep_original_audio,
        )

    def _start_with_editor(self, video_path: str,
                           cleanup_path: str | None = None):
        """Phase 1: transcribe + translate, then open subtitle editor.

        ``cleanup_path``: path of a temporary file (typically the YouTube
        download moved to a stable path) that the editor flow must remove
        at the end of the pipeline (both on confirm and on cancel/error).
        For local files opened by the user it is ``None`` - the file is
        left untouched.
        """
        self._log_write("Phase 1: Transcription + translation (no dubbing)...\n")
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_transcribing"))
        self._btn_download.configure(state="disabled")
        self._progress.start(12)
        p = self._snapshot_params()

        def phase1():
            _g._thread_local.redirect = _g._TkStreamRedirect(self, self._log_write)
            try:
                # voice passed even though phase 1 is subs_only (no TTS):
                # avoids the misleading log "[i] yt_xxx | auto->it |
                # it-IT-ElsaNeural" that defaulted to LANGUAGES[lang]["voices"][0]
                # when voice was None. Now phase 1 log reflects user's actual
                # voice selection (used for real in phase 2 _run_with_segments).
                cfg = _g.dataclasses.replace(p, video_in=video_path, subs_only=True)
                result = _g.translate_video(**cfg.to_translate_video_kwargs())
                self.after(0, self._open_editor, video_path,
                           result["segments"], cleanup_path,
                           _g._count_fallback_segments(result))
            except Exception as e:
                self.after(0, self._log_write, f"[x] Error: {e}\n{_g.traceback.format_exc()}\n")
                # Clean up the downloaded temp file even on phase-1 error
                self._cleanup_editor_tempfile(cleanup_path)
                self.after(0, self._on_done, False, _g._error_key_for(e))
            finally:
                _g._thread_local.redirect = None

        _g.threading.Thread(target=phase1, daemon=True).start()

    def _cleanup_editor_tempfile(self, cleanup_path: str | None) -> None:
        """Remove the temporary file associated with the editor flow (URL download).
        Safe no-op if ``cleanup_path`` is None or does not exist."""
        if not cleanup_path:
            return
        try:
            if _g.os.path.exists(cleanup_path):
                _g.os.remove(cleanup_path)
        except OSError:
            pass

    def _open_editor(self, video_path: str, segments: list[dict],
                     cleanup_path: str | None = None,
                     fallback_count: int = 0):
        self._progress.stop()
        self._running = False
        self._btn.configure(state="normal", text=self._s("btn_start"))
        self._btn_download.configure(state="normal", text=self._s("btn_download"))
        self._log_write(f"[i] {len(segments)} segments ready. Opening editor...\n")
        if not segments:
            _g.messagebox.showwarning(self._s("warn_editor"), self._s("msg_no_segments"))
            self._cleanup_editor_tempfile(cleanup_path)
            return
        if fallback_count:
            _g.messagebox.showwarning(
                self._s("warn_editor"),
                self._s("msg_translation_partial").format(n=fallback_count),
            )

        # Shared state between the _confirm callback and the window close
        # handler: prevents duplicate cleanup when the user confirms
        # (in that case cleanup is owned by _run_with_segments) and avoids
        # removing the file while phase 2 is still using it.
        confirmed = {"flag": False}

        def on_confirm(edited):
            confirmed["flag"] = True
            self._log_write("[i] Subtitles confirmed. Starting dubbing...\n")
            self._run_with_segments(video_path, edited, cleanup_path)

        self._editor_open = True
        fd, self._editor_preview_srt = _g.tempfile.mkstemp(
            suffix=".srt", prefix="vtai_editor_preview_")
        _g.os.close(fd)
        preview_path = _g.Path(self._editor_preview_srt)
        preview_path.write_text(
            _g.segments_to_srt(segments), encoding="utf-8")
        preview_item = _g._player_core.MediaItem(
            video_path, "source", _g.Path(video_path).name,
            srt_path=str(preview_path), temp=bool(cleanup_path),
        )
        self._player_controller.load(preview_item, paused=True)
        self._ensure_or_show_player_status()

        def on_seek(seconds):
            # Ignore callbacks that fire after the editor is gone (the debounce
            # is also cancelled in SubtitleEditor.destroy, this is the backstop).
            if not self._editor_open:
                return
            self._player_controller.seek(seconds)

        def on_change(changed_segments):
            if not self._editor_open:
                return
            self._player_controller.update_segments_as_subtitles(
                changed_segments, preview_path)

        editor = _g.SubtitleEditor(self, segments, on_confirm, ui_s=self._s,
                                on_seek=on_seek, on_change=on_change)
        editor.transient(self)
        self._right_pane.update_idletasks()
        editor_x, editor_y, editor_w, editor_h = _g._player_core.editor_geometry(
            self._right_pane.winfo_rootx(), self._right_pane.winfo_width(),
            self.winfo_rootx(), self.winfo_rooty(), self.winfo_height(),
            self.winfo_screenwidth(), self.winfo_screenheight(),
        )
        editor.geometry(f"{editor_w}x{editor_h}+{editor_x}+{editor_y}")

        # Tkinter propagates <Destroy> to all child widgets; we filter to
        # react only to the destruction of the Toplevel itself (idempotency
        # is also guaranteed by the `confirmed` flag).
        def on_editor_destroyed(evt):
            if evt.widget is not editor:
                return
            if not confirmed["flag"]:
                self._log_write("[i] Editor closed without confirmation - "
                                "discarding download.\n")
                self._cleanup_editor_tempfile(cleanup_path)
            self._editor_open = False
            self._player_controller.stop()
            if self._editor_preview_srt:
                with _g.contextlib.suppress(OSError):
                    _g.os.remove(self._editor_preview_srt)
                self._editor_preview_srt = None

        editor.bind("<Destroy>", on_editor_destroyed)

    def _run_with_segments(self, video_path: str, segments: list[dict],
                           cleanup_path: str | None = None):
        """Phase 2: dubbing with editor segments.

        ``cleanup_path`` is removed in the worker's ``finally`` block: the
        downloaded file is no longer needed after the final mux.
        """
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_dubbing"))
        self._btn_download.configure(state="disabled")
        self._progress.start(12)
        p = self._snapshot_params()

        def do():
            _g._thread_local.redirect = _g._TkStreamRedirect(self, self._log_write)
            try:
                cfg = _g.dataclasses.replace(
                    p,
                    video_in=video_path,
                    segments_override=segments,
                )
                result = _g.translate_video(**cfg.to_translate_video_kwargs())
                from videotranslator.jobs import JobOutput
                output = JobOutput.from_result(
                    result, source_path=video_path if cleanup_path is None else None)
                if output.video_path:
                    self.after(0, self._on_job_outputs, [output])
                self.after(0, self._on_done, True)
            except Exception as e:
                self.after(0, self._log_write, f"[x] {e}\n{_g.traceback.format_exc()}\n")
                self.after(0, self._on_done, False)
            finally:
                _g._thread_local.redirect = None
                self._cleanup_editor_tempfile(cleanup_path)

        _g.threading.Thread(target=do, daemon=True).start()

    def _run_batch(self, files: list[str]):
        """Batch translation - calls translate_video() directly in a worker thread."""
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_processing"))
        self._progress.start(12)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        p = self._snapshot_params()

        def run_all():
            _g._thread_local.redirect = _g._TkStreamRedirect(self, self._log_write)
            total  = len(files)
            all_ok = True
            error_keys = []
            fallback_count = 0
            from videotranslator.jobs import JobOutput
            outputs = []
            try:
                for i, f in enumerate(files):
                    self.after(0, self._log_write,
                               f"\n{'-'*50}\n[{i+1}/{total}] {_g.Path(f).name}\n{'-'*50}\n")
                    try:
                        cfg = _g.dataclasses.replace(
                            p,
                            video_in=f,
                            output=p.output if len(files) == 1 else None,
                        )
                        result = _g.translate_video(**cfg.to_translate_video_kwargs())
                        fallback_count += _g._count_fallback_segments(result)
                        output = JobOutput.from_result(result, source_path=f)
                        if output.video_path:
                            outputs.append(output)
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {e}\n{_g.traceback.format_exc()}\n")
                        all_ok = False
                        error_keys.append(_g._error_key_for(e))
            finally:
                _g._thread_local.redirect = None
            if outputs:
                self.after(0, self._on_job_outputs, outputs)
            self.after(0, self._on_done, all_ok,
                       _g._shared_error_key(error_keys), fallback_count)

        _g.threading.Thread(target=run_all, daemon=True).start()
