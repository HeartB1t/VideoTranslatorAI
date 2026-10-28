"""Main window construction and the scrolling right column (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class BuildMixin:
    # ── _build_ui sub-methods ───────────────────────────────────────────────

    def _build_header(self, parent):
        """Top header bar: logo, subtitle, status badges, settings gear."""
        # Outer header frame: root row 0, fixed above the body (it never
        # scrolls). Kept as _header_frame so the player's fullscreen can
        # hide it (spec 3.1).
        header_wrap = _g.tk.Frame(parent, bg=_g.BG)
        header_wrap.grid(row=0, column=0, sticky="ew")
        header_wrap.columnconfigure(1, weight=1)
        self._header_frame = header_wrap

        header = _g.tk.Frame(header_wrap, bg=_g.BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew",
                    padx=20, pady=(16, 10))
        header.columnconfigure(1, weight=1)

        # ── Logo block (left) ─────────────────────────────────────────────
        logo_block = _g.tk.Frame(header, bg=_g.BG)
        logo_block.grid(row=0, column=0, sticky="w")
        _g.tk.Label(logo_block, text="Video Translator AI",
                 font="VT.Title", bg=_g.BG, fg=_g.FG).pack(side="left")
        _g.tk.Label(logo_block, text="Open source dubbing studio",
                 font="VT.Small", bg=_g.BG, fg=_g.FG2).pack(side="left", padx=(10, 0), pady=(6, 0))

        # ── Status + settings gear (right) ────────────────────────────────
        right = _g.tk.Frame(header, bg=_g.BG)
        right.grid(row=0, column=1, sticky="e")

        badges = _g.tk.Frame(right, bg=_g.BG)
        badges.pack(side="left", padx=(0, 16))
        gpu_ok = bool(_g.shutil.which("nvidia-smi"))
        self._status_badge(badges, "GPU" if gpu_ok else "CPU",
                           _g.OK if gpu_ok else _g.FG2).pack(side="left", padx=(0, 12))
        # Ollama: grey until something answers for it (the startup check, the
        # preparation before a translation, the Verify button); the tip
        # carries the last answer. It stayed grey forever on Windows and
        # Linux with "Ollama pronto" in the log: nothing ever set it.
        self._ollama_badge = self._status_badge(badges, "Ollama", _g.FG2)
        self._ollama_badge.pack(side="left", padx=(0, 12))
        self._ollama_badge_dot = self._ollama_badge.winfo_children()[0]
        self._ollama_badge_text = ""
        self._ollama_badge_tip = _g._HoverTip(self._ollama_badge,
                                           lambda: self._ollama_badge_text or "Ollama",
                                           colors_fn=lambda: (_g.SEL, _g.FG))
        has_wav2lip = _g.importlib.util.find_spec("dlib") is not None
        self._status_badge(badges, "Wav2Lip",
                           _g.OK if has_wav2lip else _g.FG2).pack(side="left", padx=(0, 4))
        # Integrated player: grey until the background status check reports
        # (_on_player_status); the tooltip gives the reason (spec 2.3).
        self._player_badge = self._status_badge(badges, self._s("player_badge"), _g.FG2)
        self._player_badge.pack(side="left", padx=(8, 4))
        self._player_badge_dot, self._player_badge_label = self._player_badge.winfo_children()
        self._player_badge_tip = _g._HoverTip(self._player_badge, self._player_status_text,
                                           colors_fn=lambda: (_g.SEL, _g.FG))

        # Keyboard focus ring: bd/pady 0 offset its 2 px, so the header keeps its height.
        # The gear is an image drawn by gear_icon: the "⚙" glyph came from the
        # system font, a thin uneven outline on Windows.
        self._btn_settings = _g.tk.Label(right, bg=_g.BG, fg=_g.FG2,
                                      cursor="hand2", padx=4, pady=0, bd=0,
                                      highlightthickness=2,
                                      highlightbackground=_g.BG, highlightcolor=_g.ACC)
        self._gear_images = {}
        self._paint_gear()
        self._btn_settings.pack(side="left")
        self._btn_settings.bind("<Button-1>", lambda e: self._open_settings())
        self._keyboard_operable(self._btn_settings, self._open_settings)
        self._btn_settings.bind("<Enter>", lambda e: self._paint_gear(hover=True))
        self._btn_settings.bind("<Leave>", lambda e: self._paint_gear())
        # Caption under the pointer, in the UI language (read when it opens).
        self._btn_settings_tip = _g._HoverTip(self._btn_settings, lambda: self._s("settings_title"),
                                           colors_fn=lambda: (_g.SEL, _g.FG))

        # Thin border line under header
        _g.tk.Frame(header_wrap, bg=_g.BORDER, height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew")

    def _build_input_section(self, parent):
        """Right-column INPUT card: batch list, output path, URL download."""
        inner, self._lbl_panel_input = self._panel(
            parent, "input", self._s("panel_input"), pady=(0, 10))

        # Hidden label refs required by _apply_lang (configure(text=...))
        self._lbl_video  = _g.tk.Label(inner, text="", bg=_g.CARD)
        self._lbl_output = _g.tk.Label(inner, text="", bg=_g.CARD)
        self._lbl_url    = _g.tk.Label(inner, text="", bg=_g.CARD)

        # ── Batch file list ────────────────────────────────────────────────
        batch_outer = _g.tk.Frame(inner, bg=_g.CARD)
        batch_outer.pack(fill="x", pady=(0, 4))
        batch_frame = _g.tk.Frame(batch_outer, bg=_g.CARD)
        batch_frame.pack(side="left", fill="both", expand=True)
        self._batch_listbox = _g.tk.Listbox(
            batch_frame, height=4,
            bg=_g.FIELD, fg=_g.FG, selectbackground=_g.ACC,
            selectforeground=_g.ACC_FG,
            font="VT.Mono", relief="flat",
            highlightthickness=1,
            highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            activestyle="none", exportselection=False)
        self._batch_listbox.pack(side="left", fill="both", expand=True)
        self._batch_listbox.bind("<<ListboxSelect>>", self._on_input_select)
        _sb = _g.ttk.Scrollbar(batch_frame, command=self._batch_listbox.yview)
        self._batch_listbox.configure(yscrollcommand=_sb.set)
        _sb.pack(side="left", fill="y")
        btn_col = _g.tk.Frame(batch_outer, bg=_g.CARD)
        btn_col.pack(side="left", padx=(6, 0), anchor="n")
        w, self._btn_add = self._flat_btn(
            btn_col, text=self._s("btn_add"), command=self._add_files,
            width=10)
        w.pack(pady=2)
        w, self._btn_remove = self._flat_btn(
            btn_col, text=self._s("btn_remove"), command=self._remove_file,
            width=10)
        w.pack(pady=2)
        w, self._btn_clear = self._flat_btn(
            btn_col, text=self._s("btn_clear"), command=self._clear_files,
            width=10)
        w.pack(pady=2)

        # ── Output path ────────────────────────────────────────────────────
        _g.tk.Frame(inner, bg=_g.BORDER, height=1).pack(fill="x", pady=(4, 6))
        out_row = _g.tk.Frame(inner, bg=_g.CARD)
        out_row.pack(fill="x", pady=(0, 6))
        _g.tk.Label(out_row, text=self._s("label_output"),
                 bg=_g.CARD, fg=_g.FG2, font="VT.Small").pack(side="left", padx=(0, 6))
        self._output_var = _g.tk.StringVar()
        _g.tk.Entry(out_row, textvariable=self._output_var,
                 bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
                 highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
                 font="VT.Base").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        _w, self._btn_browse = self._flat_btn(
            out_row, text=self._s("btn_browse"), command=self._browse_output,
            padx=8, pady=2)
        _w.pack(side="left")

        # ── Output folder (one place for every translated file) ──────────────
        dir_row = _g.tk.Frame(inner, bg=_g.CARD)
        dir_row.pack(fill="x", pady=(0, 6))
        self._lbl_output_dir = _g.tk.Label(dir_row, text=self._s("label_output_dir"),
                                        bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_output_dir.pack(side="left", padx=(0, 6))
        self._output_dir_var = _g.tk.StringVar(value=_g.load_config().get("output_dir", ""))
        _dir_entry = _g.tk.Entry(dir_row, textvariable=self._output_dir_var,
                              bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
                              highlightthickness=1, highlightbackground=_g.BORDER,
                              highlightcolor=_g.ACC, font="VT.Base")
        _dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        # Persist manual edits when the field loses focus.
        _dir_entry.bind("<FocusOut>", lambda _e: self._persist_output_dir())
        _wdir, self._btn_output_dir = self._flat_btn(
            dir_row, text=self._s("btn_browse"), command=self._browse_output_dir,
            padx=8, pady=2)
        _wdir.pack(side="left")

        # ── URL download ───────────────────────────────────────────────────
        _g.tk.Frame(inner, bg=_g.BORDER, height=1).pack(fill="x", pady=(0, 6))
        _g.tk.Label(inner, text=self._s("label_url"),
                 bg=_g.CARD, fg=_g.FG2, font="VT.Small").pack(anchor="w", pady=(0, 2))
        url_row = _g.tk.Frame(inner, bg=_g.CARD)
        url_row.pack(fill="x", pady=(0, 2))
        # width=30: a small request, so the Text stretches with fill="x"
        # instead of forcing the column to its 80-column default.
        self._url_text = _g.tk.Text(
            url_row, height=2, width=20,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono", wrap="none")
        self._url_text.insert("1.0", self._s("url_placeholder"))
        self._url_text.configure(fg=_g.FG2)
        self._url_text.bind("<FocusIn>",  self._url_focus_in)
        self._url_text.bind("<FocusOut>", self._url_focus_out)
        _wd, self._btn_download = self._flat_btn(
            url_row, primary=True, text=self._s("btn_download"),
            command=self._start_download)
        # Packed before the text field so the fixed-size button keeps its width
        _wd.pack(side="right", padx=(6, 0))
        self._url_text.pack(side="left", fill="both", expand=True)
        # Keyboard traversal follows stacking order: keep the field before the button
        self._url_text.lift(_wd)

        # ── Audio/music extraction ──────────────────────────────────────────
        from videotranslator import audio_extract
        _g.tk.Frame(inner, bg=_g.BORDER, height=1).pack(fill="x", pady=(6, 6))
        self._lbl_section_extract = _g.tk.Label(
            inner, text=self._s("section_extract_audio"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_section_extract.pack(anchor="w", pady=(0, 2))

        # Format labels are brand/codec names, the same in every language.
        self._audio_fmt_label_to_key = {
            audio_extract.format_label(k): k for k in audio_extract.format_keys()
        }
        ext_row = _g.tk.Frame(inner, bg=_g.CARD)
        ext_row.pack(fill="x", pady=(0, 4))
        self._lbl_audio_format = _g.tk.Label(
            ext_row, text=self._s("label_audio_format"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_audio_format.pack(side="left", padx=(0, 4))
        self._audio_format_var = _g.tk.StringVar(
            value=audio_extract.format_label(audio_extract.format_keys()[0]))
        self._audio_format_combo = _g.ttk.Combobox(
            ext_row, textvariable=self._audio_format_var,
            values=list(self._audio_fmt_label_to_key.keys()),
            state="readonly", width=14)
        self._audio_format_combo.pack(side="left", padx=(0, 8))
        self._audio_format_combo.bind(
            "<<ComboboxSelected>>", self._on_audio_format_change)
        self._lbl_audio_bitrate = _g.tk.Label(
            ext_row, text=self._s("label_audio_bitrate"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_audio_bitrate.pack(side="left", padx=(0, 4))
        self._audio_bitrate_var = _g.tk.StringVar(value="")
        self._audio_bitrate_combo = _g.ttk.Combobox(
            ext_row, textvariable=self._audio_bitrate_var,
            values=[], state="disabled", width=6)
        self._audio_bitrate_combo.pack(side="left")

        ext_row2 = _g.tk.Frame(inner, bg=_g.CARD)
        ext_row2.pack(fill="x", pady=(0, 2))
        self._instrumental_var = _g.tk.BooleanVar(value=False)
        self._chk_instrumental = _g.tk.Checkbutton(
            ext_row2, text=self._s("opt_instrumental"),
            variable=self._instrumental_var,
            wraplength=_g._HINT_WRAP, justify="left",
            bg=_g.CARD, fg=_g.FG, selectcolor=_g.SEL,
            activebackground=_g.CARD, activeforeground=_g.FG,
            highlightbackground=_g.CARD, highlightcolor=_g.ACC, font="VT.Small")
        self._chk_instrumental.pack(side="left")
        _we, self._btn_extract_audio = self._flat_btn(
            ext_row2, primary=True, text=self._s("btn_extract_audio"),
            command=self._extract_audio, padx=8, pady=2)
        _we.pack(side="right")

        # Fill the bitrate combo for the default (lossy) format.
        self._on_audio_format_change()

    def _build_advanced_panel(self, parent):
        """Right-pane card, below Start: collapsible accordion sections for
        all advanced options."""
        adv, self._lbl_panel_settings = self._panel(
            parent, "settings", self._s("panel_settings"), pady=(4, 0))
        self._advanced_card = adv

        def cb(par, text_key, var, cmd=None):
            w = _g.tk.Checkbutton(
                par, text=self._s(text_key), variable=var, command=cmd,
                wraplength=_g._HINT_WRAP, justify="left",
                bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL,
                activebackground=_g.SURFACE, activeforeground=_g.FG,
                highlightbackground=_g.SURFACE, highlightcolor=_g.ACC, font="VT.Base")
            w._text_key = text_key
            return w

        # ── 1. WHISPER MODEL ──────────────────────────────────────────────
        sect, body, _, self._lbl_section_model = self._make_accordion_section(
            adv, self._s("section_model"))
        sect.pack(fill="x")
        mf = _g.tk.Frame(body, bg=_g.SURFACE)
        mf.pack(anchor="w", pady=4)
        # Four radios per row: the settings column is 460 px wide.
        for i, m in enumerate(_g.WHISPER_MODELS):
            _g.tk.Radiobutton(
                mf, text=m, variable=self._model, value=m,
                bg=_g.SURFACE, fg=_g.RED if "large" in m else _g.FG,
                selectcolor=_g.SEL, activebackground=_g.SURFACE,
                activeforeground=_g.RED if "large" in m else _g.FG,
                highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
                font="VT.Base").grid(row=i // 4, column=i % 4, sticky="w", padx=3)
        self._lbl_model_hint = _g.tk.Label(
            body, text=self._s("label_model_hint"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small",
            wraplength=_g._HINT_WRAP, justify="left")
        self._lbl_model_hint.pack(anchor="w", padx=4, pady=(0, 4))
        # Hardware-aware model selection: recommendations for this PC, manual
        # choice of every option, verified downloads and a benchmark.
        models_wrap, self._btn_models = self._flat_btn(
            body, text=self._s("mdl_button"), command=self._open_models_dialog)
        models_wrap.pack(anchor="w", padx=4, pady=(2, 6))

        # ── 2. TRANSLATION ENGINE ─────────────────────────────────────────
        # body2 uses grid layout so _ollama_row/_deepl_row work with
        # grid_remove()/grid() as called by _on_engine_change().
        sect2, body2, _, self._lbl_section_engine = self._make_accordion_section(
            adv, self._s("section_engine"))
        sect2.pack(fill="x")
        body2.columnconfigure(0, weight=1)

        # Engines on two rows (two per row) so the section fits the column.
        self._lbl_engine = _g.tk.Label(
            body2, text=self._s("label_engine"),
            bg=_g.SURFACE, fg=_g.FG, font="VT.Bold")
        self._lbl_engine.grid(row=0, column=0, sticky="w", pady=(4, 0))
        engine_row = _g.tk.Frame(body2, bg=_g.SURFACE)
        engine_row.grid(row=1, column=0, sticky="w")
        self._rb_eng_google = _g.tk.Radiobutton(
            engine_row, text=self._s("engine_google"),
            variable=self._translation_engine, value="google",
            command=self._on_engine_change,
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Base")
        self._rb_eng_google.pack(side="left")
        self._rb_eng_deepl = _g.tk.Radiobutton(
            engine_row, text=self._s("engine_deepl"),
            variable=self._translation_engine, value="deepl",
            command=self._on_engine_change,
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Base")
        self._rb_eng_deepl.pack(side="left", padx=(6, 0))
        # Two engines per row keep the column at its 460 px minimum in
        # every UI language and text size.
        engine_row_b = _g.tk.Frame(body2, bg=_g.SURFACE)
        engine_row_b.grid(row=2, column=0, sticky="w")
        self._rb_eng_marian = _g.tk.Radiobutton(
            engine_row_b, text=self._s("engine_marian"),
            variable=self._translation_engine, value="marian",
            command=self._on_engine_change,
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Base")
        self._rb_eng_marian.pack(side="left")
        # The Ollama label is long: own row, wrapped.
        engine_row2 = _g.tk.Frame(body2, bg=_g.SURFACE)
        engine_row2.grid(row=3, column=0, sticky="w")
        self._rb_eng_ollama = _g.tk.Radiobutton(
            engine_row2, text=self._s("engine_ollama"),
            variable=self._translation_engine, value="llm_ollama",
            command=self._on_engine_change,
            wraplength=_g._HINT_WRAP, justify="left",
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Base")
        self._rb_eng_ollama.pack(anchor="w")

        # Ollama config row (toggled by _on_engine_change). Two lines inside
        # one container so grid()/grid_remove() keep working on the container.
        self._ollama_row = _g.tk.Frame(body2, bg=_g.SURFACE)
        self._ollama_row.grid(row=4, column=0, sticky="w", pady=(2, 0))
        _ol_line1 = _g.tk.Frame(self._ollama_row, bg=_g.SURFACE)
        _ol_line1.pack(anchor="w")
        _ol_line2 = _g.tk.Frame(self._ollama_row, bg=_g.SURFACE)
        _ol_line2.pack(anchor="w", pady=(2, 0))
        self._lbl_ollama_model = _g.tk.Label(
            _ol_line1, text=self._s("label_ollama_model"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_ollama_model.pack(side="left")
        self._ollama_model_combo = _g.ttk.Combobox(
            _ol_line1, textvariable=self._ollama_model_var, width=22,
            values=[
                "qwen3:8b",
                "qwen3:14b",
                "qwen2.5:7b-instruct",
                "qwen3:4b",
            ],
            font="VT.Mono",
        )
        self._ollama_model_combo.pack(side="left", padx=(4, 0))
        self._ollama_model_combo.bind("<<ComboboxSelected>>",
                                      lambda _e: self._on_ollama_model_chosen(), add="+")
        self._lbl_ollama_url = _g.tk.Label(
            _ol_line2, text=self._s("label_ollama_url"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_ollama_url.pack(side="left")
        self._ollama_url_entry = _g.tk.Entry(
            _ol_line2, textvariable=self._ollama_url_var, width=22,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono")
        self._ollama_url_entry.pack(side="left", padx=(4, 8))
        self._chk_ollama_slot = _g.tk.Checkbutton(
            _ol_line2, text="slot-aware",
            variable=self._ollama_slot_aware,
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Small")
        self._chk_ollama_slot.pack(side="left", padx=(4, 0))
        # Verify: says whether Ollama answers and has the model, like the
        # Voicebox and ElevenLabs checks (read only, nothing is started).
        _ol_line3 = _g.tk.Frame(self._ollama_row, bg=_g.SURFACE)
        _ol_line3.pack(anchor="w", pady=(4, 0))
        ol_wrap, self._btn_ollama_check = self._flat_btn(
            _ol_line3, text=self._s("ollama_check"), command=self._check_ollama)
        ol_wrap.pack(side="left")
        self._lbl_ollama_status = _g.tk.Label(self._ollama_row, text="", bg=_g.SURFACE, fg=_g.FG2,
                                           font="VT.Small", wraplength=_g._HINT_WRAP - 30,
                                           justify="left")
        self._lbl_ollama_status.pack(anchor="w", pady=(2, 0))
        self._ollama_row.grid_remove()

        # Ollama thinking row (toggled by _on_engine_change)
        self._ollama_row2 = _g.tk.Frame(body2, bg=_g.SURFACE)
        self._ollama_row2.grid(row=5, column=0, sticky="w", pady=(2, 0))
        self._chk_ollama_thinking = _g.tk.Checkbutton(
            self._ollama_row2, text=self._s("opt_ollama_thinking"),
            variable=self._ollama_thinking,
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Small")
        self._chk_ollama_thinking.pack(anchor="w")
        self._lbl_ollama_thinking_hint = _g.tk.Label(
            self._ollama_row2,
            text=self._s("hint_ollama_thinking"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Italic",
            wraplength=_g._HINT_WRAP, justify="left")
        self._lbl_ollama_thinking_hint.pack(anchor="w", padx=(24, 0))
        self._ollama_row2.grid_remove()

        # DeepL key row (toggled by _on_engine_change)
        self._deepl_row = _g.tk.Frame(body2, bg=_g.SURFACE)
        self._deepl_row.grid(row=6, column=0, sticky="w", pady=(2, 4))
        self._lbl_deepl_key = _g.tk.Label(
            self._deepl_row, text=self._s("label_deepl_key"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_deepl_key.pack(side="left")
        self._deepl_key_entry = _g.tk.Entry(
            self._deepl_row, textvariable=self._deepl_key_var, width=28,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono", show="*")
        self._deepl_key_entry.pack(side="left", padx=(4, 0))
        self._deepl_row.grid_remove()

        # ── 3. AUDIO ──────────────────────────────────────────────────────
        sect3, body3, _, self._lbl_section_audio = self._make_accordion_section(
            adv, self._s("section_audio"))
        sect3.pack(fill="x")
        self._chk_no_demucs = cb(body3, "opt_no_demucs", self._no_demucs)
        self._chk_no_demucs.pack(anchor="w", pady=4)

        # ── 4. VOICE CLONING ──────────────────────────────────────────────
        sect4, body4, _, self._lbl_section_voice_cloning = self._make_accordion_section(
            adv, self._s("section_voice_cloning"))
        sect4.pack(fill="x")
        self._chk_xtts = cb(body4, "opt_xtts", self._use_xtts,
                            cmd=lambda: self._on_voice_clone_toggle("xtts"))
        self._chk_xtts.pack(anchor="w", pady=4)
        # Voicebox (separate local server): exclusive with XTTS.
        self._chk_voicebox = cb(body4, "vb_use", self._use_voicebox,
                                cmd=lambda: self._on_voice_clone_toggle("voicebox"))
        self._chk_voicebox.pack(anchor="w", pady=(2, 0))
        self._lbl_vb_scope = _g.tk.Label(body4, text=self._s("vb_scope"), bg=_g.SURFACE, fg=_g.FG2,
                                      font="VT.Small", wraplength=_g._HINT_WRAP - 30,
                                      justify="left")
        self._lbl_vb_scope.pack(anchor="w", padx=(22, 0))
        # Compact rows: the settings column is 460 px wide (P0 layout).
        vb_row = _g.tk.Frame(body4, bg=_g.SURFACE)
        vb_row.pack(anchor="w", padx=(22, 0), pady=(2, 0))
        self._lbl_vb_url = _g.tk.Label(vb_row, text=self._s("vb_url"), bg=_g.SURFACE, fg=_g.FG2,
                                    font="VT.Small")
        self._lbl_vb_url.pack(side="left")
        self._voicebox_url_entry = _g.tk.Entry(
            vb_row, textvariable=self._voicebox_url_var, width=22,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono")
        self._voicebox_url_entry.pack(side="left", padx=(4, 0))
        vb_row_engine = _g.tk.Frame(body4, bg=_g.SURFACE)
        vb_row_engine.pack(anchor="w", padx=(22, 0), pady=(2, 0))
        self._lbl_vb_engine = _g.tk.Label(vb_row_engine, text=self._s("vb_engine"),
                                       bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_vb_engine.pack(side="left")
        from videotranslator.voicebox_engine import ENGINES as _VB_ENGINES
        _g.ttk.Combobox(vb_row_engine, textvariable=self._voicebox_engine_var,
                     values=_VB_ENGINES, state="readonly",
                     width=16).pack(side="left", padx=(4, 0))
        vb_row2 = _g.tk.Frame(body4, bg=_g.SURFACE)
        vb_row2.pack(anchor="w", fill="x", padx=(22, 0), pady=(4, 0))
        vb_wrap, self._btn_vb_check = self._flat_btn(
            vb_row2, text=self._s("vb_check"), command=self._check_voicebox)
        vb_wrap.pack(side="left")
        self._lbl_vb_status = _g.tk.Label(body4, text="", bg=_g.SURFACE, fg=_g.FG2,
                                       font="VT.Small", wraplength=_g._HINT_WRAP - 30,
                                       justify="left")
        self._lbl_vb_status.pack(anchor="w", padx=(22, 0))
        self._lbl_vb_note = _g.tk.Label(body4, text=self._s("vb_note"), bg=_g.SURFACE, fg=_g.FG2,
                                     font="VT.Small", wraplength=_g._HINT_WRAP - 30,
                                     justify="left")
        self._lbl_vb_note.pack(anchor="w", padx=(22, 0), pady=(2, 4))
        # Optional ElevenLabs voice for the live dub (online, paid, own key).
        el_wrap, self._btn_elevenlabs = self._flat_btn(
            body4, text=self._s("el_button"), command=self._open_elevenlabs_dialog)
        el_wrap.pack(anchor="w", pady=(2, 0))
        self._lbl_el_caption = _g.tk.Label(body4, text=self._s("el_caption"), bg=_g.SURFACE, fg=_g.FG2,
                                        font="VT.Small", wraplength=_g._HINT_WRAP - 30,
                                        justify="left")
        self._lbl_el_caption.pack(anchor="w", pady=(2, 6))

        # ── 5. LIP SYNC ───────────────────────────────────────────────────
        sect5, body5, _, self._lbl_section_lip_sync = self._make_accordion_section(
            adv, self._s("section_lip_sync"))
        sect5.pack(fill="x")
        self._chk_lipsync = cb(body5, "opt_lipsync", self._use_lipsync)
        self._chk_lipsync.pack(anchor="w", pady=4)

        # ── 6. DIARIZATION ────────────────────────────────────────────────
        # body6 uses grid layout so _hf_row works with grid_remove()/grid().
        sect6, body6, _, self._lbl_section_diarization = self._make_accordion_section(
            adv, self._s("section_diarization"))
        sect6.pack(fill="x")
        body6.columnconfigure(0, weight=1)

        diar_f = _g.tk.Frame(body6, bg=_g.SURFACE)
        diar_f.grid(row=0, column=0, sticky="w", pady=(4, 0))
        self._chk_diar = _g.tk.Checkbutton(
            diar_f, text=self._s("opt_diarization"),
            variable=self._use_diarization,
            command=self._on_diarization_toggle,
            bg=_g.SURFACE, fg=_g.FG, selectcolor=_g.SEL, activebackground=_g.SURFACE, activeforeground=_g.FG,
            highlightbackground=_g.SURFACE, highlightcolor=_g.ACC,
            font="VT.Base")
        self._chk_diar.pack(side="left")

        # Token line plus a wrapped hint line, inside one container so
        # grid()/grid_remove() keep working on the container.
        self._hf_row = _g.tk.Frame(body6, bg=_g.SURFACE)
        self._hf_row.grid(row=1, column=0, sticky="w", pady=(2, 4))
        _hf_line = _g.tk.Frame(self._hf_row, bg=_g.SURFACE)
        _hf_line.pack(anchor="w")
        self._lbl_hf_token = _g.tk.Label(
            _hf_line, text=self._s("label_hf_token"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_hf_token.pack(side="left")
        self._hf_token_entry = _g.tk.Entry(
            _hf_line, textvariable=self._hf_token_var, width=28,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono", show="*")
        self._hf_token_entry.pack(side="left", padx=(4, 0))
        self._lbl_hf_hint = _g.tk.Label(
            self._hf_row, text=self._s("hint_hf_token"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Italic",
            wraplength=_g._HINT_WRAP, justify="left")
        self._lbl_hf_hint.pack(anchor="w", pady=(2, 0))
        self._hf_row.grid_remove()

        # ── 7. SUBTITLES ──────────────────────────────────────────────────
        sect7, body7, _, self._lbl_section_subtitles = self._make_accordion_section(
            adv, self._s("section_subtitles"))
        sect7.pack(fill="x")
        _opy = {"pady": (4, 0)}
        self._chk_subs_only = cb(body7, "opt_subs_only",
                                 self._subs_only, self._on_subs_only)
        self._chk_subs_only.pack(anchor="w", **_opy)
        self._chk_no_subs = cb(body7, "opt_no_subs",
                               self._no_subs, self._on_no_subs)
        self._chk_no_subs.pack(anchor="w", **_opy)
        self._chk_edit_subs = cb(body7, "opt_edit_subs", self._edit_subs)
        self._chk_edit_subs.pack(anchor="w", pady=(4, 4))

        # ── 8. HOTWORDS ───────────────────────────────────────────────────
        sect8, body8, _, self._lbl_section_hotwords = self._make_accordion_section(
            adv, self._s("section_hotwords"))
        sect8.pack(fill="x")
        self._hotwords_row = _g.tk.Frame(body8, bg=_g.SURFACE)
        self._hotwords_row.pack(anchor="w", fill="x", pady=4)
        self._lbl_hotwords = _g.tk.Label(
            self._hotwords_row, text=self._s("label_hotwords"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_hotwords.pack(side="left")
        self._hotwords_entry = _g.tk.Entry(
            self._hotwords_row, textvariable=self._hotwords_var, width=28,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono")
        self._hotwords_entry.pack(side="left", padx=(4, 0), fill="x", expand=True)
        self._lbl_hotwords_hint = _g.tk.Label(
            body8, text=self._s("hint_hotwords"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Italic",
            wraplength=_g._HINT_WRAP, justify="left")
        self._lbl_hotwords_hint.pack(anchor="w", pady=(0, 4))

        # ── 9. YOUTUBE COOKIES ────────────────────────────────────────────
        sect9, body9, _, self._lbl_section_cookies = self._make_accordion_section(
            adv, self._s("section_cookies"))
        sect9.pack(fill="x")
        self._cookies_file_var = _g.tk.StringVar(
            value=_g.load_config().get("yt_dlp_cookies_file", ""))
        cookies_row = _g.tk.Frame(body9, bg=_g.SURFACE)
        cookies_row.pack(anchor="w", fill="x", pady=4)
        self._lbl_cookies_file = _g.tk.Label(
            cookies_row, text=self._s("label_cookies_file"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Small")
        self._lbl_cookies_file.pack(side="left")
        self._cookies_file_entry = _g.tk.Entry(
            cookies_row, textvariable=self._cookies_file_var, width=22,
            bg=_g.FIELD, fg=_g.FG, **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            font="VT.Mono")
        self._cookies_file_entry.pack(side="left", padx=(4, 0), fill="x", expand=True)
        self._cookies_file_entry.bind("<FocusOut>", lambda _e: self._persist_cookies_file())
        _wc, self._btn_cookies_browse = self._flat_btn(
            cookies_row, text=self._s("btn_browse"), command=self._browse_cookies_file,
            padx=8, pady=2)
        _wc.pack(side="left", padx=(4, 0))
        self._lbl_cookies_hint = _g.tk.Label(
            body9, text=self._s("hint_cookies_file"),
            bg=_g.SURFACE, fg=_g.FG2, font="VT.Italic",
            wraplength=_g._HINT_WRAP, justify="left")
        self._lbl_cookies_hint.pack(anchor="w", pady=(0, 4))

    def _build_lang_voice_section(self, parent):
        """Right-pane card: language pair + voice chips + TTS rate slider."""
        inner, self._lbl_panel_translation = self._panel(
            parent, "translation", self._s("panel_translation"), pady=(0, 10))

        # Source language
        from_row = _g.tk.Frame(inner, bg=_g.CARD)
        from_row.pack(fill="x", pady=2)
        self._lbl_from = _g.tk.Label(
            from_row, text=self._s("label_from"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small", width=6, anchor="e")
        self._lbl_from.pack(side="left")
        self._src_combo = _g.ttk.Combobox(
            from_row, values=self._source_lang_labels(),
            state="readonly", width=22)
        self._src_combo.current(0)
        self._src_combo.pack(side="left", padx=(4, 0))
        src_keys = list(_g.SOURCE_LANGS.keys())
        self._src_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, k=src_keys: self._lang_src.set(
                k[self._src_combo.current()]))

        # Target language
        to_row = _g.tk.Frame(inner, bg=_g.CARD)
        to_row.pack(fill="x", pady=2)
        self._lbl_to = _g.tk.Label(
            to_row, text=self._s("label_to"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small", width=6, anchor="e")
        self._lbl_to.pack(side="left")
        self._tgt_combo = _g.ttk.Combobox(
            to_row, values=[v["name"] for v in _g.LANGUAGES.values()],
            state="readonly", width=22)
        self._tgt_combo.current(list(_g.LANGUAGES.keys()).index("it"))
        self._tgt_combo.pack(side="left", padx=(4, 0))
        self._tgt_combo.bind("<<ComboboxSelected>>", self._on_lang_tgt_change)

        # Voice label + chips
        voice_lbl_row = _g.tk.Frame(inner, bg=_g.CARD)
        voice_lbl_row.pack(fill="x", pady=(8, 2))
        self._lbl_voice = _g.tk.Label(
            voice_lbl_row, text=self._s("label_voice"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_voice.pack(side="left")
        self._voice_speaker = _g._SpeakerButton(
            voice_lbl_row, palette=self._theme.palette, bg_role="SURFACE", ui_s=self._s,
            on_click=self._preview_edge_voice, scale=self._theme.scale)
        self._voice_speaker.canvas.pack(side="left", padx=(6, 0))
        self._voice_preview_hub.add_listener(self._on_voice_preview_state)

        self._voice_frame = _g.tk.Frame(inner, bg=_g.CARD)
        self._voice_frame.pack(fill="x", pady=(0, 6))
        self._build_voice_buttons()

        # TTS rate slider
        rate_title_row = _g.tk.Frame(inner, bg=_g.CARD)
        rate_title_row.pack(fill="x", pady=(4, 2))
        self._lbl_tts_rate = _g.tk.Label(
            rate_title_row, text=self._s("label_tts_rate"),
            bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_tts_rate.pack(side="left")

        rate_frame = _g.tk.Frame(inner, bg=_g.CARD)
        rate_frame.pack(fill="x", pady=(0, 4))
        _g.tk.Label(rate_frame, text="-50%", bg=_g.CARD, fg=_g.FG2,
                 font="VT.Small").pack(side="left")
        _g.ttk.Scale(rate_frame, from_=-50, to=50, variable=self._tts_rate,
                  orient="horizontal", length=180).pack(side="left", padx=6)
        _g.tk.Label(rate_frame, text="+50%", bg=_g.CARD, fg=_g.FG2,
                 font="VT.Small").pack(side="left")
        self._rate_lbl = _g.tk.Label(
            rate_frame, text="+0%", bg=_g.CARD, fg=_g.FG,
            font="VT.Bold", width=6)
        self._rate_lbl.pack(side="left", padx=4)
        self._tts_rate.trace_add("write", self._update_rate_label)

    def _build_profile_section(self, parent):
        """Right-pane card: Fast / Balanced / Studio / Cinematic presets."""
        inner, self._lbl_panel_profile = self._panel(
            parent, "profile", self._s("panel_profile"), pady=(0, 10))

        btn_row = _g.tk.Frame(inner, bg=_g.CARD)
        btn_row.pack(fill="x")

        _PROFILE_LABELS = {
            "fast":      "Fast",
            "balanced":  "Balanced",
            "studio":    "Studio",
            "cinematic": "Cinema",
        }
        self._profile_btns = {}
        for name, label in _PROFILE_LABELS.items():
            btn = _g._bevel_tk.BevelButton(
                btn_row, palette_fn=lambda: self._theme.palette,
                scale_fn=lambda: self._theme.scale,
                text=label,
                bg=_g.BTN, fg=_g.FG,
                font="VT.Base",
                padx=6, pady=6,
                cursor="hand2",
                highlightcolor=_g.ACC,
                activebackground=_g.ACC_SOFT, activeforeground=_g.FG,
                command=lambda n=name: self._apply_profile(n),
            )
            btn.pack(side="left", padx=(0, 4), fill="x", expand=True)
            self._profile_btns[name] = btn

        # Hint text (updates when profile changes)
        self._lbl_profile_hint = _g.tk.Label(
            inner, text="", bg=_g.CARD, fg=_g.FG2,
            font="VT.Small", wraplength=_g._HINT_WRAP,
            anchor="w", justify="left")
        self._lbl_profile_hint.pack(fill="x", pady=(6, 0))

        self._update_profile_buttons()

    def _build_start_section(self, parent):
        """Right-pane card: summary line + big Start button + status row."""
        inner, self._lbl_panel_start = self._panel(
            parent, "start", self._s("panel_start"), pady=(0, 10))

        # Summary line (auto-updated on lang/voice/profile changes)
        self._lbl_summary = _g.tk.Label(
            inner, textvariable=self._summary_var,
            bg=_g.CARD, fg=_g.FG2, font="VT.Small",
            wraplength=_g._HINT_WRAP, justify="left")
        self._lbl_summary.pack(anchor="w", pady=(0, 10))

        # Start button - full-width, accent-filled primary
        _ws, self._btn = self._flat_btn(
            inner, primary=True, text=self._s("btn_start"),
            command=self._start, font="VT.Large", padx=24, pady=8)
        _ws.pack(fill="x")

        # Status row below button
        status_row = _g.tk.Frame(inner, bg=_g.CARD)
        status_row.pack(fill="x", pady=(8, 0))
        _g.tk.Label(status_row, text="⚡", bg=_g.CARD, fg=_g.ACC,
                 font="VT.Small").pack(side="left")
        self._lbl_status = _g.tk.Label(
            status_row, text="Ready",
            bg=_g.CARD, fg=_g.FG2, font="VT.Small")
        self._lbl_status.pack(side="left", padx=(2, 0))

    # ── Main _build_ui entry point ─────────────────────────────────────────

    def _build_ui(self):
        # ── Root grid (player design, spec 2026-09-25 section 3.1) ────────
        # row 0 = header, fixed: it never scrolls
        # row 1 = body: column 0 = the player pane, which fills the height
        #         and never scrolls; column 1 = the card column, scrolled
        #         alone by its own canvas
        # row 2 = log panel
        # row 3 = progress bar
        # Only row 1 stretches and no row or column keeps a minimum size, so
        # the player's fullscreen can grid_remove() rows 0, 2, 3 and the card
        # column and hand the whole window to the player.
        for row, weight in ((0, 0), (1, 1), (2, 0), (3, 0)):
            self.grid_rowconfigure(row, weight=weight)
        self.grid_columnconfigure(0, weight=1)

        # Header first: it is also the first Tab stop of the window.
        self._build_header(self)

        # ── Body (root row 1) ─────────────────────────────────────────────
        body = _g.tk.Frame(self, bg=_g.BG)
        body.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(8, 8))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        self._body = body

        # Left pane: the integrated player (P1 shows its status and Install).
        # It sits outside every canvas, so it follows the window height and a
        # wheel over it scrolls nothing.
        left = _g.tk.Frame(body, bg=_g.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._left_pane = left
        self._player_area = _g.tk.Frame(left, bg=_g.FIELD, highlightthickness=1,
                                     highlightbackground=_g.BORDER,
                                     highlightcolor=_g.BORDER)
        self._player_area.pack(fill="both", expand=True)
        self._player_panel = _g._PlayerPanel(
            self._player_area, ui_s=self._s, make_button=self._flat_btn,
            on_command=self._on_player_command,
            logo_path=_g._assets_dir() / "icon_256.png",
            theme=self._theme, keyboard_operable=self._keyboard_operable,
            log=self._player_log)
        # Live-translation strip under the player transport (spec 5.9). It sits
        # inside the player area, below the panel; mpv renders into a deeper child
        # (video_host), so the strip never overlaps the video, and the left pane
        # still holds exactly the player area (P0 layout invariant preserved).
        self._live_save_after = None     # pending debounced save of the bar choices
        self._live_bar = _g._LiveBar(
            self._player_area, ui_s=self._s, make_button=self._flat_btn,
            on_command=self._on_live_command, theme=self._theme,
            keyboard_operable=self._keyboard_operable, log=self._live_bar_log)
        self._live_bar.pack(side="bottom", fill="x")
        # Restore the choices of the previous launch (mode, engine, voice,
        # subtitles, delay), saved by _save_live_choices.
        with _g.contextlib.suppress(Exception):
            self._live_bar.set_config_values(
                _g._player_settings_module.normalize_live_settings(_g.load_config()))
        self._player_panel.pack(side="top", fill="both", expand=True)
        self._refresh_live_bar_enabled()
        self._refresh_live_voice_info()

        # Right column: input, translation, profile, start, then the settings
        # accordion, in a canvas that scrolls only this column. The canvas
        # takes the width of the cards' widest state, never below 460 px
        # (_sync_right_column); its height follows the window.
        column = _g.tk.Frame(body, bg=_g.BG)
        column.grid(row=0, column=1, sticky="ns")
        column.rowconfigure(0, weight=1)
        self._right_column = column
        self._right_canvas = _g.tk.Canvas(column, bg=_g.BG, highlightthickness=0,
                                       width=_g._RIGHT_COLUMN_MIN_WIDTH)
        self._right_canvas.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        self._right_vsb = _g.ttk.Scrollbar(column, orient="vertical",
                                        command=self._right_canvas.yview)
        self._right_vsb.grid(row=0, column=1, sticky="ns")
        self._right_canvas.configure(yscrollcommand=self._right_vsb.set)

        right = _g.tk.Frame(self._right_canvas, bg=_g.BG)
        self._right_pane = right
        self._right_canvas_window = self._right_canvas.create_window(
            (0, 0), window=right, anchor="nw")
        # Keep width, scroll region and top pin in sync with the cards
        # (accordion toggles, drags, relabels) and with the window.
        right.bind("<Configure>", self._sync_right_column)
        self._right_canvas.bind("<Configure>", self._on_right_canvas_configure)

        self._build_input_section(right)
        self._build_lang_voice_section(right)
        self._build_profile_section(right)
        self._build_start_section(right)
        self._build_advanced_panel(right)
        # Built in the default order; apply the order the user saved.
        self._repack_panels()

        # ── Log panel (root row 2) ────────────────────────────────────────
        log_frame = _g.tk.Frame(self, bg=_g.BG)
        log_frame.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="nsew")
        self._log_frame = log_frame
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        log_header = _g.tk.Frame(log_frame, bg=_g.BG)
        log_header.grid(row=0, column=0, sticky="ew")
        self._lbl_log_panel = _g.tk.Label(
            log_header, text=self._s("label_log_panel"),
            bg=_g.BG, fg=_g.FG, font="VT.Bold")
        self._lbl_log_panel.pack(side="left")
        # Default collapsed - log starts hidden (btn_log_show text)
        _wt, self._btn_log_toggle = self._flat_btn(
            log_header, text=self._s("btn_log_show"), command=self._toggle_log,
            padx=8, pady=2)
        _wt.pack(side="left", padx=(8, 0))
        _wc, self._btn_log_clear = self._flat_btn(
            log_header, text=self._s("btn_log_clear"), command=self._log_clear,
            padx=8, pady=2)
        _wc.pack(side="right")
        _ws2, self._btn_log_save = self._flat_btn(
            log_header, text=self._s("btn_log_save"), command=self._log_save,
            padx=8, pady=2)
        _ws2.pack(side="right", padx=(0, 4))
        _wcp, self._btn_log_copy = self._flat_btn(
            log_header, text=self._s("btn_log_copy"), command=self._log_copy,
            padx=8, pady=2)
        _wcp.pack(side="right", padx=(0, 4))
        _wpf, self._btn_preflight = self._flat_btn(
            log_header, text=self._s("btn_preflight"), command=self._run_gui_preflight,
            padx=8, pady=2)
        _wpf.pack(side="right", padx=(0, 4))

        self._log_container = _g.tk.Frame(log_frame, bg=_g.BG)
        self._log_container.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self._log_container.rowconfigure(0, weight=1)
        self._log_container.columnconfigure(0, weight=1)
        self._log = _g.tk.Text(
            self._log_container, height=12, width=76,
            bg=_g.FIELD, fg=_g.FG, font="VT.Mono", **_g._field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=_g.BORDER, highlightcolor=_g.ACC,
            state="disabled", wrap="word")
        # Only the level word is coloured, so every line stays readable in
        # every theme; the theme recolour maps these tag colours too.
        self._log.tag_configure("lvl_warn", foreground=_g.WARN)
        self._log.tag_configure("lvl_error", foreground=_g.ERR)
        vsb = _g.ttk.Scrollbar(self._log_container, command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # ── Progress bar (root row 3) ─────────────────────────────────────
        self._progress = _g.ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=3, column=0, padx=16, pady=(0, 12))

        # ── Mouse-wheel scrolling: the card column only ───────────────────
        # One call covers the canvas and every card (they are its
        # descendants). The header, the player pane and the log stay unbound.
        self._bind_mousewheel(self._right_canvas)
        self.bind("<Key>", self._on_player_key, add="+")

        # Initial summary line
        self._update_start_summary()

    # ── Scrolling of the card column ───────────────────────────────────────

    @staticmethod
    def _canvas_content_fits(canvas) -> bool:
        """True when the canvas content is not taller than the canvas itself.

        Scrolling in that case only shifts the cards down and leaves an empty
        band above the first card, so callers skip the scroll and pin the view.
        """
        bbox = canvas.bbox("all")
        if not bbox:
            return True
        height = canvas.winfo_height()
        if height <= 1:  # not mapped yet
            height = canvas.winfo_reqheight()
        return bbox[3] - bbox[1] <= height

    def _cards_widest_width(self):
        """Width the cards ask for with every accordion section open.

        A closed section's body still computes the size it would ask for
        (Tk propagates the requested size of unmapped frames), so the column
        can take its widest state up front: opening or closing a section
        then never changes the column's width, nor the player's (spec 9, P0).
        """
        widest = self._right_pane.winfo_reqwidth()
        card = getattr(self, "_advanced_card", None)  # settings card, inner frame
        if card is not None:
            # border and padding between that inner frame and the column
            chain = card.master.winfo_reqwidth() - card.winfo_reqwidth()
            for section in card.winfo_children():
                body = getattr(section, "_accordion_body", None)
                if body is not None:
                    widest = max(widest, body.winfo_reqwidth() + chain)
        return widest

    def _sync_right_column(self, _event=None):
        """Fit the card column's canvas to its cards.

        Runs on every size change of the cards (accordion toggles, drags,
        relabels). The canvas takes the width of the cards' widest state,
        never less than 460 px (0216809); the scroll region follows the
        content; a column that fits is pinned to the top, so no empty band
        can open above the first card (fd7eacc).
        """
        canvas = getattr(self, "_right_canvas", None)
        if canvas is None:
            return
        try:
            width = _g._right_column_width(self._cards_widest_width())
            if int(canvas.cget("width")) != width:
                canvas.configure(width=width)
            canvas.configure(scrollregion=canvas.bbox("all"))
            if self._canvas_content_fits(canvas):
                canvas.yview_moveto(0)
        except _g.tk.TclError:
            pass  # the window is being destroyed

    def _sync_right_column_settled(self):
        """_sync_right_column once a relabel's size requests have propagated.

        A label that grows asks its frame for room at idle time, and each frame
        above passes the request on in a later idle round: measured in the
        first round, the cards still report their old width (a German label
        wider than 460 px left the column at 460). update_idletasks runs those
        rounds first.
        """
        try:
            self.update_idletasks()
        except _g.tk.TclError:
            return  # the window is being destroyed
        self._sync_right_column()

    def _on_right_canvas_configure(self, event):
        """Stretch the cards to the canvas width; pin a column that fits."""
        self._right_canvas.itemconfig(self._right_canvas_window, width=event.width)
        if self._canvas_content_fits(self._right_canvas):
            self._right_canvas.yview_moveto(0)

    def _on_mousewheel(self, event):
        """Scroll the card column in response to a wheel event over it.

        ``WheelAccumulator`` turns the event into scroll units on every
        platform (X11 buttons 4/5, ``<MouseWheel>`` deltas on Windows and
        Tk 8.7+, small touchpad deltas summed to whole notches).
        """
        # Over a combobox the wheel must scroll the column only: its class
        # binding would otherwise also change the selected value while the
        # user is just scrolling the settings.
        try:
            on_combobox = event.widget.winfo_class() == "TCombobox"
        except (AttributeError, _g.tk.TclError):
            on_combobox = False
        stop = "break" if on_combobox else None
        canvas = getattr(self, "_right_canvas", None)
        if canvas is None:
            return stop
        wheel = getattr(self, "_wheel", None)
        if wheel is None:
            wheel = self._wheel = _g._WheelAccumulator()
        try:
            if self._canvas_content_fits(canvas):
                return stop
            units = wheel.feed(getattr(event, "num", None),
                               getattr(event, "delta", 0))
            if units:
                canvas.yview_scroll(units, "units")
        except _g.tk.TclError:
            pass  # the window is being destroyed
        return stop

    def _bind_mousewheel(self, widget):
        """Bind wheel scrolling on ``widget`` and all its descendants.

        Tk does not pass wheel events on to parent widgets, so the canvas
        would otherwise stop scrolling as soon as the cursor hovers over an
        inner control (entry, combobox, button, ...). The bindings REPLACE
        any earlier widget-level wheel binding: re-binding a subtree (the
        voice chips after a target change) must not stack a second handler,
        or one notch would scroll twice. No other code binds wheel events at
        widget level; class bindings (Listbox, Text, Combobox) are separate.
        """
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel)  # Windows, Tk 8.7+
            widget.bind("<Button-4>", self._on_mousewheel)    # X11 up
            widget.bind("<Button-5>", self._on_mousewheel)    # X11 down
        except _g.tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_mousewheel(child)
