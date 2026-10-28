"""Settings window, theme, UI language and voice pickers (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class SettingsMixin:
    # ── Language switcher ────────────────────────────────────────────────────

    def _on_ui_lang_change(self, _=None):
        idx = self._ui_lang_combo.current()
        if idx < 0:
            return
        self._ui_lang.set(_g.UI_LANG_OPTIONS[idx][0])
        _g.save_config({"ui_lang": self._ui_lang.get()})
        self._apply_lang()

    # ── Settings window ─────────────────────────────────────────────────────

    def _segmented(self, parent, options, variable, command):
        """Row of flat toggle buttons bound to ``variable``.

        ``options`` is a list of ``(value, label)``. The returned row exposes
        ``_refresh()`` to re-read the selection colours after a theme change.
        """
        row = _g.tk.Frame(parent, bg=parent.cget("bg"))
        buttons = {}

        def refresh(*_):
            cur = variable.get()
            for value, b in buttons.items():
                if value == cur:
                    b.configure(bg=_g.ACC_SOFT, fg=_g.FG, highlightbackground=_g.ACC)
                else:
                    b.configure(bg=_g.BTN, fg=_g.FG, highlightbackground=_g.BORDER)

        def choose(value):
            variable.set(value)
            refresh()
            command()

        for value, label in options:
            b = _g.tk.Button(row, text=label, bg=_g.BTN, fg=_g.FG, font="VT.Base",
                          relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                          activebackground=_g.ACC_SOFT, activeforeground=_g.FG,
                          highlightthickness=1, highlightbackground=_g.BORDER,
                          highlightcolor=_g.ACC,
                          command=lambda v=value: choose(v))
            b.pack(side="left", padx=(0, 4))
            buttons[value] = b
        refresh()
        row._refresh = refresh
        return row

    def _theme_options(self):
        """(value, label) pairs for the theme row; Graphite/Slate/Neon are proper nouns."""
        labels = {"auto": self._s("theme_auto"), "light": self._s("theme_light")}
        return [(k, labels.get(k, k.capitalize())) for k in _g._BASE_THEMES]

    @staticmethod
    def _skin_options():
        """(value, label) pairs for the skin row: names, not translated."""
        labels = {"dex": "Dex", "handheld": "Handheld", "crt": "CRT",
                  "crt_amber": "CRT Amber"}
        return [(k, labels.get(k, k)) for k in _g._SKIN_CHOICES]

    def _scale_options(self):
        return [(k, self._s(f"size_{k}")) for k in _g._SCALES]

    def _accent_dot_colour(self, value):
        """Swatch colour: the theme's own accent for "default", the fixed accent otherwise."""
        if value == "default":
            return _g._resolve_palette(self._theme.palette.name, "default").ACC
        return _g._ACCENTS[value]

    def _refresh_accent_dots(self):
        """Re-paint the accent dots after a theme or accent change.

        Own colour (the theme accent for "default"), FG ring on the
        selection, ACC ring on the dot that has the keyboard focus.
        """
        if not getattr(self, "_accent_dots", None):
            return
        cur = self._ui_accent_var.get()
        for value, d in self._accent_dots.items():
            if not d.winfo_exists():
                continue
            d.configure(fg=self._accent_dot_colour(value),
                        bg=_g.SURFACE,
                        highlightbackground=_g.FG if value == cur else _g.SURFACE,
                        highlightcolor=_g.ACC)

    def _open_settings(self):
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return
        win = _g.tk.Toplevel(self, bg=_g.BG)
        self._settings_win = win
        win.title(self._s("settings_title"))
        self._log_event("log_window", title=self._s("settings_title"))
        win.resizable(False, False)
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", self._close_settings)
        body = _g.tk.Frame(win, bg=_g.BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Appearance
        self._lbl_settings_appearance = _g.tk.Label(
            body, text=self._s("settings_appearance").upper(), bg=_g.BG, fg=_g.FG2, font="VT.SmallBold")
        self._lbl_settings_appearance.pack(anchor="w")
        card = self._card(body, pady=(6, 14))

        self._lbl_settings_theme = _g.tk.Label(card, text=self._s("settings_theme"),
                                            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_settings_theme.pack(anchor="w")
        self._seg_theme = self._segmented(card, self._theme_options(),
                                          self._ui_theme_var, self._apply_ui_settings)
        self._seg_theme.pack(anchor="w", pady=(4, 12))

        self._lbl_settings_skin = _g.tk.Label(card, text=self._s("settings_skin"),
                                           bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_settings_skin.pack(anchor="w")
        self._seg_skin = self._segmented(card, self._skin_options(),
                                         self._ui_theme_var, self._apply_ui_settings)
        self._seg_skin.pack(anchor="w", pady=(4, 12))

        self._lbl_settings_accent = _g.tk.Label(card, text=self._s("settings_accent"),
                                             bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_settings_accent.pack(anchor="w")
        dots = _g.tk.Frame(card, bg=_g.SURFACE)
        dots.pack(anchor="w", pady=(4, 12))
        self._accent_dots = {}

        def choose_accent(value):
            self._ui_accent_var.set(value)
            self._apply_ui_settings()

        for value in _g._ACCENT_CHOICES:
            d = _g.tk.Label(dots, text="●", bg=_g.SURFACE, fg=self._accent_dot_colour(value),
                         font="VT.Title", cursor="hand2",
                         padx=4, highlightthickness=2, highlightbackground=_g.SURFACE,
                         highlightcolor=_g.ACC)
            d.pack(side="left", padx=(0, 2))
            d.bind("<Button-1>", lambda e, v=value: choose_accent(v))
            self._keyboard_operable(d, lambda v=value: choose_accent(v))
            self._accent_dots[value] = d
            if value == "default":
                # Caption sits next to its own dot, before the fixed accents
                self._lbl_accent_default = _g.tk.Label(dots, text=self._s("accent_default"),
                                                    bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
                self._lbl_accent_default.pack(side="left", padx=(2, 14))
        self._refresh_accent_dots()

        self._lbl_settings_size = _g.tk.Label(card, text=self._s("settings_text_size"),
                                           bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_settings_size.pack(anchor="w")
        self._seg_scale = self._segmented(card, self._scale_options(),
                                          self._ui_scale_var, self._apply_ui_settings)
        self._seg_scale.pack(anchor="w", pady=(4, 0))

        # Language
        self._lbl_settings_language = _g.tk.Label(
            body, text=self._s("settings_language").upper(), bg=_g.BG, fg=_g.FG2, font="VT.SmallBold")
        self._lbl_settings_language.pack(anchor="w")
        lang_card = self._card(body, pady=(6, 14))
        self._lbl_ui_lang = _g.tk.Label(lang_card, text=self._s("label_ui_lang"),
                                     bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_ui_lang.pack(anchor="w")
        self._ui_lang_combo = _g.ttk.Combobox(
            lang_card, values=[lbl for _, lbl in _g.UI_LANG_OPTIONS], state="readonly", width=24)
        _codes = [code for code, _ in _g.UI_LANG_OPTIONS]
        self._ui_lang_combo.current(_codes.index(self._ui_lang.get()) if self._ui_lang.get() in _codes else 0)
        self._ui_lang_combo.pack(anchor="w", pady=(4, 0))
        self._ui_lang_combo.bind("<<ComboboxSelected>>", self._on_ui_lang_change)

        # Player options: keep these separate from appearance preferences so
        # they remain available even when the integrated player is offline.
        self._lbl_settings_player = _g.tk.Label(
            body, text=self._s("settings_player").upper(), bg=_g.BG, fg=_g.FG2,
            font="VT.SmallBold")
        self._lbl_settings_player.pack(anchor="w")
        player_card = self._card(body, pady=(6, 14))
        self._player_autoload_var = _g.tk.BooleanVar(value=self._player_settings.autoload_result)
        self._keep_original_audio_var = _g.tk.BooleanVar(
            value=self._player_settings.keep_original_audio)
        self._chk_player_autoload = _g.tk.Checkbutton(
            player_card, text=self._s("opt_player_autoload"),
            variable=self._player_autoload_var,
            command=self._save_player_options,
            bg=_g.SURFACE, fg=_g.FG, activebackground=_g.SURFACE, activeforeground=_g.FG,
            selectcolor=_g.BG, relief="flat", borderwidth=0, font="VT.Base",
        )
        self._chk_player_autoload.pack(anchor="w")
        self._chk_keep_original_audio = _g.tk.Checkbutton(
            player_card, text=self._s("opt_keep_original_audio"),
            variable=self._keep_original_audio_var,
            command=self._save_player_options,
            bg=_g.SURFACE, fg=_g.FG, activebackground=_g.SURFACE, activeforeground=_g.FG,
            selectcolor=_g.BG, relief="flat", borderwidth=0, font="VT.Base",
        )
        self._chk_keep_original_audio.pack(anchor="w")
        self._player_credits_label = _g.tk.Label(
            player_card, text=self._player_panel.status_text(), bg=_g.SURFACE,
            fg=_g.FG2, font="VT.Small", justify="left", wraplength=420,
        )
        self._player_credits_label.pack(anchor="w", pady=(4, 0))

        # Buttons
        btns = _g.tk.Frame(body, bg=_g.BG)
        btns.pack(fill="x")
        _wr, self._btn_settings_reset = self._flat_btn(
            btns, text=self._s("btn_reset"), command=self._reset_ui_settings)
        _wr.pack(side="left")
        _wc, self._btn_settings_close = self._flat_btn(
            btns, text=self._s("btn_close"), primary=True, command=self._close_settings)
        _wc.pack(side="right")

        # Centre over the main window
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_reqwidth()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_reqheight()) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
        win.focus_force()

    def _save_player_options(self):
        self._player_settings = _g.dataclasses.replace(
            self._player_settings,
            autoload_result=bool(self._player_autoload_var.get()),
            keep_original_audio=bool(self._keep_original_audio_var.get()),
        )
        _g.save_config({
            _g._player_settings_module.PLAYER_AUTOLOAD_KEY:
                self._player_settings.autoload_result,
            _g._player_settings_module.KEEP_ORIGINAL_AUDIO_KEY:
                self._player_settings.keep_original_audio,
        })

    def _apply_ui_settings(self):
        """Apply the dialog's current choices live and persist them."""
        settings = {
            "ui_theme": self._ui_theme_var.get(),
            "ui_accent": self._ui_accent_var.get(),
            "ui_scale": self._ui_scale_var.get(),
            "ui_lang": self._ui_lang.get(),
        }
        self._theme.apply(settings, recolor=True)
        self._ui_settings = dict(self._theme.settings)
        _g.save_config({k: self._ui_settings[k] for k in ("ui_theme", "ui_accent", "ui_scale")})
        self._refresh_theme_dependents()
        self._log_event("log_settings", theme=self._ui_settings["ui_theme"],
                        accent=self._ui_settings["ui_accent"], scale=self._ui_settings["ui_scale"])

    def _refresh_theme_dependents(self):
        """Repaint what the colour mapping of a theme change cannot handle.

        Selection states re-read the (new) globals: the colour mapping alone
        cannot tell a selected dot from one that merely shares the old accent.
        """
        if self._settings_win is not None and self._settings_win.winfo_exists():
            for row in (self._seg_theme, self._seg_skin, self._seg_scale):
                row._refresh()
            self._refresh_accent_dots()
        self._update_profile_buttons()
        player_panel = getattr(self, "_player_panel", None)
        if player_panel is not None:
            player_panel.apply_theme()
        live_bar = getattr(self, "_live_bar", None)
        if live_bar is not None:
            live_bar.apply_theme()
        alive = []
        for frame in self._card_frames:
            with _g.contextlib.suppress(_g.tk.TclError):
                frame.configure(highlightthickness=_g.BORDER_PX)
                alive.append(frame)
        self._card_frames = alive
        # Last: the loops above may repaint a key's frames with a plain colour.
        _g._bevel_tk.repaint_all()
        self._gear_images.clear()                 # drawn over the old background
        self._paint_gear()
        speaker = getattr(self, "_voice_speaker", None)
        if speaker is not None:
            speaker.apply_palette(self._theme.palette, self._theme.scale)
        self._apply_video_effect()
        # Another text size changes the cards' width, and a large shrink can
        # leave the view below the content without any <Configure>.
        self.after_idle(self._sync_right_column_settled)

    def _remember_system_dark(self, value):
        """Cache the OS dark-mode answer so the next start paints with it."""
        _g.save_config({_g._SYSTEM_DARK_KEY: value})

    def _reset_ui_settings(self):
        if self._panel_order != list(_g._PANEL_IDS):
            self._panel_order = list(_g._PANEL_IDS)
            self._repack_panels()
            _g.save_config({"ui_panel_order": self._panel_order})
        self._ui_theme_var.set(_g._DEFAULT_THEME)
        self._ui_accent_var.set(_g._DEFAULT_ACCENT)
        self._ui_scale_var.set(_g._DEFAULT_SCALE)
        self._apply_ui_settings()
        # Spec 2.5: Reset also forgets the cached libmpv probe, so the next
        # status check probes the library again. save_config merges and cannot
        # delete a key, hence the raw write of the whole file.
        cfg = _g.load_config()
        player_keys = ("player_probe", "player_vo_profile")
        if any(key in cfg for key in player_keys):
            for key in player_keys:
                cfg.pop(key, None)
            try:
                _g._write_config_raw(cfg)
            except OSError as exc:
                self._log_write(f"[!] Could not reset the player probe cache: {exc}\n")

    def _close_settings(self):
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.destroy()
        self._settings_win = None

    def _relabel_settings(self):
        """Refresh the dialog's texts after a UI language change."""
        if self._settings_win is None or not self._settings_win.winfo_exists():
            return
        self._settings_win.title(self._s("settings_title"))
        self._lbl_settings_appearance.configure(text=self._s("settings_appearance").upper())
        self._lbl_settings_theme.configure(text=self._s("settings_theme"))
        self._lbl_settings_skin.configure(text=self._s("settings_skin"))
        self._lbl_settings_accent.configure(text=self._s("settings_accent"))
        self._lbl_accent_default.configure(text=self._s("accent_default"))
        self._lbl_settings_size.configure(text=self._s("settings_text_size"))
        self._lbl_settings_language.configure(text=self._s("settings_language").upper())
        self._lbl_settings_player.configure(text=self._s("settings_player").upper())
        self._chk_player_autoload.configure(text=self._s("opt_player_autoload"))
        self._chk_keep_original_audio.configure(text=self._s("opt_keep_original_audio"))
        self._lbl_ui_lang.configure(text=self._s("label_ui_lang"))
        self._btn_settings_reset.configure(text=self._s("btn_reset"))
        self._btn_settings_close.configure(text=self._s("btn_close"))
        # Rebuild the two segmented rows so their labels are translated
        theme_parent, scale_parent = self._seg_theme.master, self._seg_scale.master
        self._seg_theme.destroy()
        self._seg_theme = self._segmented(theme_parent, self._theme_options(),
                                          self._ui_theme_var, self._apply_ui_settings)
        self._seg_theme.pack(anchor="w", pady=(4, 12), after=self._lbl_settings_theme)
        self._seg_scale.destroy()
        self._seg_scale = self._segmented(scale_parent, self._scale_options(),
                                          self._ui_scale_var, self._apply_ui_settings)
        self._seg_scale.pack(anchor="w", pady=(4, 0), after=self._lbl_settings_size)
        # Tab follows the stacking order, where a new widget comes last:
        # put each row back right after its label, before the accent dots.
        self._seg_theme.lift(self._lbl_settings_theme)
        self._seg_scale.lift(self._lbl_settings_size)

    def _apply_lang(self):
        self._relabel_settings()
        self._player_badge_label.configure(text=self._s("player_badge"))
        self._player_panel.relabel()
        self._live_bar.relabel()
        self._refresh_live_voice_info()
        lang = self._ui_lang.get()
        self._lbl_panel_input.configure(text=self._title_upper(self._s("panel_input"), lang))
        self._lbl_panel_translation.configure(text=self._title_upper(self._s("panel_translation"), lang))
        self._lbl_panel_profile.configure(text=self._title_upper(self._s("panel_profile"), lang))
        self._lbl_panel_settings.configure(
            text=self._title_upper(self._s("panel_settings"), lang))
        self._lbl_panel_start.configure(text=self._title_upper(self._s("panel_start"), lang))
        self._lbl_video.configure(text=self._s("label_video"))
        self._lbl_output.configure(text=self._s("label_output"))
        self._lbl_output_dir.configure(text=self._s("label_output_dir"))
        self._lbl_section_model.configure(text=self._s("section_model"))
        self._lbl_model_hint.configure(text=self._s("label_model_hint"))
        self._btn_models.configure(text=self._s("mdl_button"))
        self._lbl_from.configure(text=self._s("label_from"))
        self._lbl_to.configure(text=self._s("label_to"))
        self._lbl_voice.configure(text=self._s("label_voice"))
        self._lbl_tts_rate.configure(text=self._s("label_tts_rate"))
        self._lbl_url.configure(text=self._s("label_url"))
        if not self._running:
            self._btn_download.configure(text=self._s("btn_download"))
        if self._url_placeholder_active:
            self._url_text.delete("1.0", "end")
            self._url_text.insert("1.0", self._s("url_placeholder"))
            self._url_text.configure(fg=_g.FG2)
        self._btn_add.configure(text=self._s("btn_add"))
        self._btn_remove.configure(text=self._s("btn_remove"))
        self._btn_clear.configure(text=self._s("btn_clear"))
        self._btn_browse.configure(text=self._s("btn_browse"))
        self._btn_output_dir.configure(text=self._s("btn_browse"))
        self._lbl_section_extract.configure(text=self._s("section_extract_audio"))
        self._lbl_audio_format.configure(text=self._s("label_audio_format"))
        self._lbl_audio_bitrate.configure(text=self._s("label_audio_bitrate"))
        self._chk_instrumental.configure(text=self._s("opt_instrumental"))
        if not self._running:
            self._btn_extract_audio.configure(text=self._s("btn_extract_audio"))
        if not self._running:
            self._btn.configure(text=self._s("btn_start"))
        self._lbl_section_subtitles.configure(text=self._s("section_subtitles"))
        self._chk_subs_only.configure(text=self._s("opt_subs_only"))
        self._chk_no_subs.configure(text=self._s("opt_no_subs"))
        self._lbl_section_audio.configure(text=self._s("section_audio"))
        self._chk_no_demucs.configure(text=self._s("opt_no_demucs"))
        self._chk_edit_subs.configure(text=self._s("opt_edit_subs"))
        self._lbl_section_voice_cloning.configure(text=self._s("section_voice_cloning"))
        self._chk_xtts.configure(text=self._s("opt_xtts"))
        self._btn_elevenlabs.configure(text=self._s("el_button"))
        self._chk_voicebox.configure(text=self._s("vb_use"))
        self._lbl_vb_url.configure(text=self._s("vb_url"))
        self._lbl_vb_engine.configure(text=self._s("vb_engine"))
        self._btn_vb_check.configure(text=self._s("vb_check"))
        self._btn_ollama_check.configure(text=self._s("ollama_check"))
        self._lbl_vb_note.configure(text=self._s("vb_note"))
        self._lbl_vb_scope.configure(text=self._s("vb_scope"))
        self._lbl_el_caption.configure(text=self._s("el_caption"))
        self._lbl_section_lip_sync.configure(text=self._s("section_lip_sync"))
        self._chk_lipsync.configure(text=self._s("opt_lipsync"))
        self._lbl_section_engine.configure(text=self._s("section_engine"))
        self._lbl_engine.configure(text=self._s("label_engine"))
        self._rb_eng_google.configure(text=self._s("engine_google"))
        self._rb_eng_deepl.configure(text=self._s("engine_deepl"))
        self._rb_eng_marian.configure(text=self._s("engine_marian"))
        self._rb_eng_ollama.configure(text=self._s("engine_ollama"))
        self._lbl_ollama_model.configure(text=self._s("label_ollama_model"))
        self._lbl_ollama_url.configure(text=self._s("label_ollama_url"))
        self._chk_ollama_thinking.configure(text=self._s("opt_ollama_thinking"))
        self._lbl_ollama_thinking_hint.configure(text=self._s("hint_ollama_thinking"))
        self._lbl_deepl_key.configure(text=self._s("label_deepl_key"))
        self._lbl_section_diarization.configure(text=self._s("section_diarization"))
        self._chk_diar.configure(text=self._s("opt_diarization"))
        self._lbl_hf_token.configure(text=self._s("label_hf_token"))
        self._lbl_hf_hint.configure(text=self._s("hint_hf_token"))
        self._lbl_section_hotwords.configure(text=self._s("section_hotwords"))
        self._lbl_hotwords.configure(text=self._s("label_hotwords"))
        self._lbl_hotwords_hint.configure(text=self._s("hint_hotwords"))
        self._lbl_section_cookies.configure(text=self._s("section_cookies"))
        self._lbl_cookies_file.configure(text=self._s("label_cookies_file"))
        self._lbl_cookies_hint.configure(text=self._s("hint_cookies_file"))
        self._btn_cookies_browse.configure(text=self._s("btn_browse"))
        # Log panel labels
        self._lbl_log_panel.configure(text=self._s("label_log_panel"))
        self._btn_log_toggle.configure(
            text=self._s("btn_log_hide" if getattr(self, "_log_visible", True) else "btn_log_show"))
        self._btn_log_copy.configure(text=self._s("btn_log_copy"))
        self._btn_log_save.configure(text=self._s("btn_log_save"))
        self._btn_log_clear.configure(text=self._s("btn_log_clear"))
        self._btn_preflight.configure(text=self._s("btn_preflight"))
        # Update source language combo labels ("auto" is translated)
        src_keys = list(_g.SOURCE_LANG_CODES)
        cur_key  = self._lang_src.get()
        self._src_combo["values"] = self._source_lang_labels()
        try:
            self._src_combo.current(src_keys.index(cur_key))
        except ValueError:
            self._src_combo.current(0)
        self._src_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, k=src_keys: (
                self._lang_src.set(k[self._src_combo.current()]),
                self._update_start_summary(),
            ))
        self._update_start_summary()
        # A relabel can change what the cards ask for (closed accordion
        # sections included) without changing their height, and then no
        # <Configure> reaches _sync_right_column.
        self.after_idle(self._sync_right_column_settled)

    # ── Voice buttons ────────────────────────────────────────────────────────

    def _build_voice_buttons(self):
        """Rebuild voice pill-buttons for the selected target language."""
        for w in self._voice_frame.winfo_children():
            w.destroy()
        lang_key = list(_g.LANGUAGES.keys())[self._tgt_combo.current()]
        voices   = _g.LANGUAGES[lang_key]["voices"]
        self._voice.set(voices[0])

        def _refresh_pills(*_):
            """Re-color all pill buttons to reflect selection."""
            cur = self._voice.get()
            self._voice_preview_hub.stop_if("edge:")
            self._refresh_live_voice_info()
            for btn_v, btn_w in _pill_map.items():
                btn_w.configure(bg=_g.ACC_SOFT if btn_v == cur else _g.BTN, fg=_g.FG)
                btn_w.set_selected(btn_v == cur)

        _pill_map = {}
        for v in voices:
            label = v.split("-")[2].replace("Neural", "").replace("Multilingual", "ML")
            btn = _g._bevel_tk.BevelRadiobutton(
                self._voice_frame, palette_fn=lambda: self._theme.palette,
                scale_fn=lambda: self._theme.scale,
                text=label,
                variable=self._voice, value=v,
                indicatoron=False,
                bg=_g.BTN, fg=_g.FG,
                selectcolor=_g.ACC_SOFT,
                activebackground=_g.ACC_SOFT, activeforeground=_g.FG,
                font="VT.Base",
                padx=10, pady=4,
                highlightcolor=_g.ACC,
                cursor="hand2",
                command=_refresh_pills,
            )
            btn.pack(side="left", padx=(0, 4))
            _pill_map[v] = btn

        # Apply initial coloring
        _refresh_pills()
        self._update_start_summary()

    def _preview_edge_voice(self) -> None:
        """Speaker icon: say a short sentence in the target language with the
        selected Edge-TTS voice and speed (free, online); click again to stop."""
        voice = self._voice.get()
        rate = int(round(self._tts_rate.get()))
        text = _g._preview_sentence(self._lang_tgt.get())
        key = f"edge:{voice}:{rate}"
        self._voice_preview_key = key
        self._voice_preview_hub.toggle(
            key, lambda: _g._synthesize_edge_preview(text, voice, rate))

    def _on_voice_preview_state(self, key, state, kind) -> None:
        voice = (self._voice_preview_hub.label(key)
                 or (key.split(":")[1] if key.count(":") >= 1 else key))
        if state == "error":
            self._log_event("log_vp", voice=voice, state=self._s(_g._preview_error_key(kind)))
        else:
            state_key = {"loading": "log_state_loading", "playing": "log_state_playing",
                         "idle": "log_state_idle"}.get(state, "log_state_idle")
            self._log_event("log_vp", voice=voice, state=self._s(state_key))
        speaker = self._voice_speaker
        if speaker is None:
            return
        if key != self._voice_preview_key:
            if speaker.state != "error":
                speaker.set_state("idle")
            return
        if state == "error":
            text = self._s(_g._preview_error_key(kind))
            speaker.set_state("error", text)
        else:
            speaker.set_state(state)

    def _on_lang_tgt_change(self, _=None):
        self._lang_tgt.set(list(_g.LANGUAGES.keys())[self._tgt_combo.current()])
        self._build_voice_buttons()
        # Re-bind mousewheel to newly created voice pill buttons
        try:
            self._bind_mousewheel(self._voice_frame)
        except Exception:
            pass
        self._update_start_summary()
        # New voice chips can change the cards' width.
        self.after_idle(self._sync_right_column_settled)

    def _update_rate_label(self, *_):
        try:
            v = int(round(self._tts_rate.get()))
        except (ValueError, _g.tk.TclError):
            v = 0
        self._rate_lbl.configure(text=f"{v:+d}%")

    def _on_subs_only(self):
        if self._subs_only.get():
            self._no_subs.set(False)

    def _on_engine_change(self):
        eng = self._translation_engine.get()
        if eng == "deepl":
            self._deepl_row.grid()
        else:
            self._deepl_row.grid_remove()
        if eng == "llm_ollama":
            self._ollama_row.grid()
            self._ollama_row2.grid()
            # Auto-setup: binary detection → install → daemon → model pull.
            # All in a daemon thread; popups routed via self.after for thread safety.
            # Respect `ollama_auto_install` config flag (default True).
            self._ensure_ollama_ready_async(on_ready=None)
        else:
            self._ollama_row.grid_remove()
            self._ollama_row2.grid_remove()
        if eng == "marian":
            self._check_marian_deps()
