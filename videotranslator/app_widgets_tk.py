"""Widget factories, cards and draggable panels (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class WidgetsMixin:
    # ── UI builder ───────────────────────────────────────────────────────────

    # ── GUI style helpers ──────────────────────────────────────────────────

    def _status_badge(self, parent, text, color):
        """Discreet status indicator: coloured dot + label (header)."""
        f = _g.tk.Frame(parent, bg=_g.BG)
        _g.tk.Label(f, text="●", bg=_g.BG, fg=color, font="VT.Small").pack(side="left")
        _g.tk.Label(f, text=text, bg=_g.BG, fg=_g.FG2, font="VT.Small").pack(side="left", padx=(3, 0))
        return f

    def _flat_btn(self, parent, primary=False, **kwargs):
        """Button drawn as a raised key. Returns (wrap_frame, button).

        ``wrap_frame`` carries the key's edge (``bevel_tk``) and is what the
        caller places. ``primary`` renders the accent-filled call-to-action
        variant. Hover colours are read from the module globals at event
        time, so they follow live theme changes; the edge repaints itself
        from the face, and turns into the focus ring (accent, or the text
        colour on the accent-filled key) while the button has the keyboard
        focus.
        """
        kwargs.pop("bg", None)
        kwargs.pop("activebackground", None)
        kwargs.pop("activeforeground", None)
        # Compatibility shim: drop the legacy "glow" keyword of old call sites
        kwargs.pop("glow", None)
        fg = kwargs.pop("fg", _g.ACC_FG if primary else _g.FG)
        cursor = kwargs.pop("cursor", "hand2")
        btn = _g._bevel_tk.BevelButton(
            parent, palette_fn=lambda: self._theme.palette,
            scale_fn=lambda: self._theme.scale, primary=primary,
            bg=_g.ACC if primary else _g.BTN,
            fg=fg,
            activebackground=_g.ACC_HOVER if primary else _g.BORDER,
            activeforeground=_g.ACC_FG if primary else _g.FG,
            disabledforeground=_g.ACC_FG if primary else _g.FG2,
            cursor=cursor,
            font=kwargs.pop("font", "VT.Bold" if primary else "VT.Base"),
            padx=kwargs.pop("padx", 10), pady=kwargs.pop("pady", 4),
            **kwargs,
        )

        def _enter(_e, b=btn, p=primary):
            if str(b.cget("state")) != "disabled":
                hover = _g.ACC_HOVER if p else self._hover_bg()
                b.configure(bg=hover, activebackground=hover)

        def _leave(_e, b=btn, p=primary):
            enabled = str(b.cget("state")) != "disabled"
            b.configure(bg=_g.ACC if p and enabled else _g.BTN)

        # Return activates it like the space bar already does.
        def _return(_e, b=btn):
            self._log_widget_activation(b)
            if str(b.cget("state")) != "disabled":
                b.invoke()
            return "break"

        btn.bind("<Enter>", _enter)
        btn.bind("<Leave>", _leave)
        btn.bind("<Return>", _return)
        btn.bind("<KP_Enter>", _return)
        return btn.outer, btn

    def _paint_gear(self, hover: bool = False) -> None:
        """Put the header gear in FG2, or FG under the pointer, over BG and at
        the text size. Images are kept by colour and size: a theme or size
        change makes new ones (``_refresh_theme_dependents``)."""
        size = max(16, round(22 * self._theme.scale))
        key = (size, _g.FG if hover else _g.FG2, _g.BG)
        image = self._gear_images.get(key)
        if image is None:
            image = self._gear_images[key] = _g._gear_icon.gear_image(self, size, key[1], _g.BG)
        self._btn_settings.configure(image=image)

    @staticmethod
    def _hover_bg():
        """Hover colour of a flat button: the border colour, unless the text
        would be hard to read on it (the red frames of the "dex" skin)."""
        return _g.BORDER if _g._contrast_ratio(_g.FG, _g.BORDER) >= 4.5 else _g.SEL

    @staticmethod
    def _keyboard_operable(widget, action):
        """Let a clickable Label take Tab focus and run ``action`` on Return, KP_Enter or space.

        The caller gives the widget its focus ring (``highlightthickness``,
        ``highlightcolor`` ACC, ``highlightbackground`` = its own background),
        so the live recolour follows theme and accent changes.
        """
        def activate(_event):
            action()
            return "break"

        widget.configure(takefocus=1)
        for sequence in ("<Return>", "<KP_Enter>", "<space>"):
            widget.bind(sequence, activate)

    def _card(self, parent, **pack):
        """Surface card with a BORDER_PX border (1 px, 3 on the chunky skins);
        returns the inner padded frame."""
        outer = _g.tk.Frame(parent, bg=_g.SURFACE, highlightthickness=_g.BORDER_PX,
                         highlightbackground=_g.BORDER, highlightcolor=_g.BORDER)
        outer.pack(fill="x", **pack)
        self._card_frames.append(outer)
        inner = _g.tk.Frame(outer, bg=_g.SURFACE)
        inner.pack(fill="both", expand=True, padx=12, pady=10)
        return inner

    @staticmethod
    def _title_upper(text, lang):
        """Upper-case a UI title the way ``lang`` actually capitalizes it.

        Plain ``str.upper()`` gets two languages wrong: Turkish has two
        distinct letters for I (dotted lower-case 'i' upper-cases to 'İ',
        not 'I'), and Greek all-caps text drops the acute accent that
        Python's default upper-casing keeps. Both fixes live here so
        ``_section_title`` (card titles) and ``_apply_lang`` (their
        language-switch refresh) share one implementation.
        """
        if lang == "tr":
            text = text.replace("i", "İ")
        upper = text.upper()
        if lang == "el":
            decomposed = _g.unicodedata.normalize("NFD", upper)
            stripped = "".join(ch for ch in decomposed if ch != "\u0301")
            upper = _g.unicodedata.normalize("NFC", stripped)
        return upper

    def _section_title(self, parent, text):
        """Small upper-case section label in muted colour.

        Returns ``(frame, label)``: the caller keeps ``label`` to retext it
        on a UI language change (``_apply_lang``).
        """
        bg = parent.cget("bg") if "bg" in parent.keys() else _g.SURFACE
        f = _g.tk.Frame(parent, bg=bg)
        lbl = _g.tk.Label(f, text=self._title_upper(text, self._ui_lang.get()), bg=bg, fg=_g.FG2,
                       font="VT.SmallBold")
        lbl.pack(side="left")
        return f, lbl

    # -- Movable panels of the settings column ---------------------------

    def _panel(self, parent, panel_id, title, **pack):
        """A card the user can drag to another position in the column.

        Builds a `_card`, registers its outer frame under ``panel_id`` and
        adds a header row: the section title (when given) on the left and
        a drag handle on the right. Dragging the header moves the card;
        the order is saved as ``ui_panel_order`` and depends only on
        ``panel_id``, never on the (translated) title text. Returns
        ``(inner_frame, title_label_or_None)``: the caller keeps the label
        to retext it on a UI language change.
        """
        inner = self._card(parent, **pack)
        self._panels[panel_id] = (inner.master, dict(pack))
        hdr = _g.tk.Frame(inner, bg=_g.SURFACE, cursor="fleur")
        hdr.pack(fill="x", pady=(0, 8) if title else (0, 2))
        title_lbl = None
        if title:
            title_frame, title_lbl = self._section_title(hdr, title)
            title_frame.pack(side="left")
        grip = _g.tk.Label(hdr, text="≡", bg=_g.SURFACE, fg=_g.FG2,
                        font="VT.Base", cursor="fleur")
        grip.pack(side="right")
        self._bind_panel_drag(hdr, panel_id)
        return inner, title_lbl

    def _bind_panel_drag(self, widget, panel_id):
        """Bind the drag handlers on ``widget`` and every descendant, so the
        whole header row (title text included) starts a drag."""
        widget.bind("<ButtonPress-1>",
                    lambda e, pid=panel_id: self._panel_drag_start(pid, e))
        widget.bind("<B1-Motion>", self._panel_drag_motion)
        widget.bind("<ButtonRelease-1>", self._panel_drag_end)
        for child in widget.winfo_children():
            self._bind_panel_drag(child, panel_id)

    def _pointer_over_column(self, x_root, slack=40):
        """True when ``x_root`` is over the settings column (plus ``slack`` px)."""
        left = self._right_pane.winfo_rootx()
        return left - slack <= x_root <= left + self._right_pane.winfo_width() + slack

    def _panel_spans(self, exclude):
        """(top, bottom) root-y extents of every panel except ``exclude``."""
        spans = []
        for pid in self._panel_order:
            if pid == exclude or pid not in self._panels:
                continue
            outer = self._panels[pid][0]
            top = outer.winfo_rooty()
            spans.append((top, top + outer.winfo_height()))
        return spans

    def _panel_drag_start(self, panel_id, event):
        self._drag = {"pid": panel_id, "y0": event.y_root,
                      "moved": False, "index": None}

    def _panel_drag_motion(self, event):
        d = self._drag
        if d is None:
            return
        if not d["moved"] and abs(event.y_root - d["y0"]) < 4:
            return  # a click with a tiny wobble is not a drag
        d["moved"] = True
        others = [p for p in self._panel_order if p != d["pid"]]
        if not others:
            return
        ind = self._drag_indicator
        if ind is None or not ind.winfo_exists():
            ind = self._drag_indicator = _g.tk.Frame(self._right_pane, height=3)
        if not self._pointer_over_column(event.x_root):
            # Leaving the column sideways cancels the drop (release does nothing).
            d["index"] = None
            ind.pack_forget()
            return
        idx = _g._drop_index(event.y_root, self._panel_spans(d["pid"]))
        d["index"] = idx
        ind.configure(bg=_g.ACC)
        ind.pack_forget()
        if idx < len(others):
            ind.pack(fill="x", before=self._panels[others[idx]][0])
        else:
            ind.pack(fill="x", after=self._panels[others[-1]][0])

    def _panel_drag_end(self, event):
        d, self._drag = self._drag, None
        ind = self._drag_indicator
        if ind is not None and ind.winfo_exists():
            ind.pack_forget()
        if d is None or not d["moved"] or d["index"] is None:
            return
        new_order = _g._move_panel(self._panel_order, d["pid"], d["index"])
        if new_order != self._panel_order:
            self._panel_order = new_order
            self._repack_panels()
            _g.save_config({"ui_panel_order": new_order})

    def _repack_panels(self):
        """Re-pack the registered panels following ``self._panel_order``."""
        ordered = [pid for pid in self._panel_order if pid in self._panels]
        for pid in ordered:
            self._panels[pid][0].pack_forget()
        for pid in ordered:
            outer, opts = self._panels[pid]
            outer.pack(fill="x", **opts)
            # Tab follows the stacking order of siblings: raising each card in
            # turn makes the keyboard order match the order on screen.
            outer.lift()

    def _make_accordion_section(self, parent, title_text):
        """Return (outer_frame, body_frame, arrow_label, title_label). Starts
        collapsed. The caller keeps ``title_label`` to retext it on a UI
        language change (``_apply_lang``).

        A separator is drawn above every section but the first one; the
        card's drag header does not count as a section."""
        first = not any(getattr(c, "_is_accordion_section", False)
                        for c in parent.winfo_children())
        outer = _g.tk.Frame(parent, bg=_g.SURFACE)
        outer._is_accordion_section = True
        outer.pack(fill="x", pady=1)
        if not first:
            _g.tk.Frame(outer, bg=_g.BORDER, height=1).pack(fill="x")
        hdr = _g.tk.Frame(outer, bg=_g.SURFACE, cursor="hand2")
        hdr.pack(fill="x")
        arrow_lbl = _g.tk.Label(hdr, text="▸", bg=_g.SURFACE, fg=_g.FG2, font="VT.Base", width=2)
        arrow_lbl.pack(side="left")
        title_lbl = _g.tk.Label(hdr, text=title_text, bg=_g.SURFACE, fg=_g.FG, font="VT.Base")
        title_lbl.pack(side="left", padx=(2, 0), pady=6)
        body = _g.tk.Frame(outer, bg=_g.SURFACE, padx=24, pady=6)
        outer._accordion_body = body  # measured by _cards_widest_width

        def toggle(e=None):
            if body.winfo_manager():
                body.pack_forget()
                arrow_lbl.configure(text="▸")
            else:
                body.pack(fill="x")
                arrow_lbl.configure(text="▾")

        hdr.bind("<Button-1>", toggle)
        for w in hdr.winfo_children():
            w.bind("<Button-1>", toggle)
        return outer, body, arrow_lbl, title_lbl

    def _apply_profile(self, name):
        """Apply a quality preset by setting existing Tk vars."""
        self._active_profile.set(name)
        self._use_voicebox.set(False)        # presets choose Edge-TTS or XTTS
        # A preset is the newest explicit choice: the models chosen in the
        # 'Models for this PC' window no longer apply at the next launch.
        if getattr(self, "_models_choice_restored", False) or _g.load_config().get(
                _g._MODELS_CHOICE_KEY):
            _g.save_config({_g._MODELS_CHOICE_KEY: None})
            self._models_choice_restored = False
        if name == "fast":
            self._no_demucs.set(True)
            self._use_xtts.set(False)
            self._use_lipsync.set(False)
            self._model.set("small")
            self._translation_engine.set("google")
        elif name == "balanced":
            self._no_demucs.set(False)
            self._use_xtts.set(False)
            self._use_lipsync.set(False)
            self._model.set(_g.DEFAULT_WHISPER_MODEL)
            self._translation_engine.set("google")
        elif name == "studio":
            self._no_demucs.set(False)
            self._use_xtts.set(False)
            self._use_lipsync.set(False)
            self._model.set("large-v3")
            self._translation_engine.set("marian")
        elif name == "cinematic":
            self._no_demucs.set(False)
            self._use_xtts.set(True)
            self._use_lipsync.set(False)
            self._model.set("large-v3-turbo")
            self._translation_engine.set("google")
        self._on_engine_change()
        self._update_profile_buttons()
        self._update_start_summary()

    def _update_profile_buttons(self):
        """Refresh profile button highlight and hint text for the active preset."""
        if not hasattr(self, "_profile_btns"):
            return
        _HINTS = {
            "fast":      "No voice separation · Edge-TTS · small model · fastest",
            "balanced":  "Demucs + Edge-TTS · GPU-tuned model · recommended",
            "studio":    "Demucs · MarianMT offline · large-v3 · no internet",
            "cinematic": "XTTS v2 voice clone · large-v3-turbo · speaker match",
        }
        active = self._active_profile.get()
        for name, btn in self._profile_btns.items():
            # The chosen profile is a sunk key, the others stand raised.
            btn.configure(bg=_g.ACC_SOFT if name == active else _g.BTN, fg=_g.FG)
            btn.set_selected(name == active)
        if hasattr(self, "_lbl_profile_hint"):
            self._lbl_profile_hint.configure(
                text=_HINTS.get(active, ""))

    def _source_lang_labels(self) -> list[str]:
        """Source language choices: automatic detection, then native names."""
        return ["🔍 " + self._s("lang_auto_detect")] + [
            _g.SOURCE_LANGS[code] for code in _g.SOURCE_LANG_CODES[1:]]

    def _update_start_summary(self):
        """Rebuild the summary line shown in the START card."""
        if not hasattr(self, "_summary_var"):
            return
        try:
            src_key  = self._lang_src.get()
            tgt_key  = self._lang_tgt.get()
            src_name = (self._source_lang_labels()[0] if src_key == "auto"
                        else _g.SOURCE_LANGS.get(src_key, src_key))
            tgt_name = _g.LANGUAGES.get(tgt_key, {}).get("name", tgt_key)
            eng = self._translation_engine.get()
            eng_label = {
                "google":     "Google Translate",
                "deepl":      "DeepL",
                "marian":     "MarianMT",
                "llm_ollama": "Ollama LLM",
            }.get(eng, eng)
            tts     = ("Voicebox" if self._use_voicebox.get()
                       else "XTTS v2" if self._use_xtts.get() else "Edge-TTS")
            profile = self._active_profile.get().capitalize()
            self._summary_var.set(
                f"{src_name} → {tgt_name}  ·  {eng_label}"
                f"  ·  {tts}  ·  {profile}"
            )
        except Exception:
            pass
