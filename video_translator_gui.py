#!/usr/bin/env python3
"""
video_translator_gui.py v2 — GUI per Video Translator AI
Nuove feature: faster-whisper GPU, Demucs, lingua sorgente, editor sottotitoli,
               velocità TTS, batch processing, controllo dipendenze, UI multilingua.
"""

import importlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

LANGUAGES = {
    "ar":    {"name": "🇸🇦 Arabo",       "voices": ["ar-SA-ZariyahNeural", "ar-SA-HamedNeural", "ar-EG-SalmaNeural"]},
    "zh-CN": {"name": "🇨🇳 Cinese",      "voices": ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural"]},
    "cs":    {"name": "🇨🇿 Ceco",        "voices": ["cs-CZ-VlastaNeural", "cs-CZ-AntoninNeural"]},
    "da":    {"name": "🇩🇰 Danese",      "voices": ["da-DK-ChristelNeural", "da-DK-JeppeNeural"]},
    "de":    {"name": "🇩🇪 Tedesco",     "voices": ["de-DE-KatjaNeural", "de-DE-ConradNeural", "de-DE-AmalaNeural"]},
    "el":    {"name": "🇬🇷 Greco",       "voices": ["el-GR-AthinaNeural", "el-GR-NestorasNeural"]},
    "en":    {"name": "🇬🇧 Inglese",     "voices": ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural"]},
    "es":    {"name": "🇪🇸 Spagnolo",    "voices": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-MX-DaliaNeural"]},
    "fi":    {"name": "🇫🇮 Finlandese",  "voices": ["fi-FI-NooraNeural", "fi-FI-HarriNeural"]},
    "fr":    {"name": "🇫🇷 Francese",    "voices": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural", "fr-FR-EloiseNeural"]},
    "hi":    {"name": "🇮🇳 Hindi",       "voices": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"]},
    "hu":    {"name": "🇭🇺 Ungherese",   "voices": ["hu-HU-NoemiNeural", "hu-HU-TamasNeural"]},
    "id":    {"name": "🇮🇩 Indonesiano", "voices": ["id-ID-GadisNeural", "id-ID-ArdiNeural"]},
    "it":    {"name": "🇮🇹 Italiano",    "voices": ["it-IT-ElsaNeural", "it-IT-IsabellaNeural", "it-IT-DiegoNeural", "it-IT-GiuseppeMultilingualNeural"]},
    "ja":    {"name": "🇯🇵 Giapponese",  "voices": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"]},
    "ko":    {"name": "🇰🇷 Coreano",     "voices": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"]},
    "nl":    {"name": "🇳🇱 Olandese",    "voices": ["nl-NL-ColetteNeural", "nl-NL-MaartenNeural"]},
    "no":    {"name": "🇳🇴 Norvegese",   "voices": ["nb-NO-PernilleNeural", "nb-NO-FinnNeural"]},
    "pl":    {"name": "🇵🇱 Polacco",     "voices": ["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"]},
    "pt":    {"name": "🇧🇷 Portoghese",  "voices": ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-PT-RaquelNeural"]},
    "ro":    {"name": "🇷🇴 Rumeno",      "voices": ["ro-RO-AlinaNeural", "ro-RO-EmilNeural"]},
    "ru":    {"name": "🇷🇺 Russo",       "voices": ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]},
    "sv":    {"name": "🇸🇪 Svedese",     "voices": ["sv-SE-SofieNeural", "sv-SE-MattiasNeural"]},
    "tr":    {"name": "🇹🇷 Turco",       "voices": ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]},
    "uk":    {"name": "🇺🇦 Ucraino",     "voices": ["uk-UA-PolinaNeural", "uk-UA-OstapNeural"]},
    "vi":    {"name": "🇻🇳 Vietnamita",  "voices": ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]},
}

SOURCE_LANGS = {"auto": "🔍 Rilevamento automatico", "en": "🇬🇧 Inglese", "it": "🇮🇹 Italiano",
                "es": "🇪🇸 Spagnolo", "fr": "🇫🇷 Francese", "de": "🇩🇪 Tedesco",
                "pt": "🇧🇷 Portoghese", "ru": "🇷🇺 Russo", "zh-CN": "🇨🇳 Cinese",
                "ja": "🇯🇵 Giapponese", "ko": "🇰🇷 Coreano", "ar": "🇸🇦 Arabo"}

SOURCE_LANGS_EN = {"auto": "🔍 Auto detect", "en": "🇬🇧 English", "it": "🇮🇹 Italian",
                   "es": "🇪🇸 Spanish", "fr": "🇫🇷 French", "de": "🇩🇪 German",
                   "pt": "🇧🇷 Portuguese", "ru": "🇷🇺 Russian", "zh-CN": "🇨🇳 Chinese",
                   "ja": "🇯🇵 Japanese", "ko": "🇰🇷 Korean", "ar": "🇸🇦 Arabic"}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
TRANSLATOR_SCRIPT = Path(__file__).parent / "video_translator.py"

REQUIRED_PACKAGES = {
    "faster_whisper": "faster-whisper",
    "edge_tts":       "edge-tts",
    "deep_translator":"deep-translator",
    "pydub":          "pydub",
    "demucs":         "demucs",
}
if sys.version_info >= (3, 13):
    REQUIRED_PACKAGES["audioop"] = "audioop-lts"

BG = "#1e1e2e"
FG = "#cdd6f4"
FG2 = "#6c7086"
ACC = "#89b4fa"
SEL = "#313244"
RED = "#f38ba8"
GRN = "#a6e3a1"

UI_STRINGS = {
    "it": {
        "label_video":        "Video:",
        "label_output":       "Output:",
        "label_model":        "Modello:",
        "label_from":         "Da:",
        "label_to":           "A:",
        "label_voice":        "Voce:",
        "label_tts_rate":     "Velocità TTS:",
        "label_options":      "Opzioni:",
        "label_model_hint":   "← veloce / preciso →",
        "label_ui_lang":      "🌐 Lingua UI:",
        "btn_add":            "+ Aggiungi",
        "btn_remove":         "- Rimuovi",
        "btn_clear":          "✗ Svuota",
        "btn_browse":         "Sfoglia…",
        "btn_start":          "▶  Avvia Traduzione",
        "btn_processing":     "⏳  In elaborazione...",
        "btn_transcribing":   "⏳ Trascrizione...",
        "btn_dubbing":        "⏳ Doppiaggio...",
        "btn_installing":     "⏳  Installazione...",
        "opt_subs_only":      "Solo sottotitoli .srt (no doppiaggio)",
        "opt_no_subs":        "Non voglio sottotitoli",
        "opt_no_demucs":      "Salta separazione voce/musica (Demucs)",
        "opt_edit_subs":      "Mostra editor sottotitoli prima del doppiaggio",
        "msg_no_video":       "Aggiungi almeno un video.",
        "msg_script_missing": "Script non trovato:\n{}",
        "msg_completed":      "Traduzione completata!",
        "msg_error":          "Qualcosa è andato storto. Controlla il log.",
        "msg_confirm_stop":   "Elaborazione in corso. Interrompere?",
        "msg_confirm":        "Conferma",
        "msg_completed_t":    "Completato",
        "msg_error_t":        "Errore",
        "msg_deps_missing":   "Dipendenze mancanti",
        "msg_deps_python":    "Pacchetti Python mancanti:\n  • ",
        "msg_deps_bins":      "Programmi mancanti:\n  • ",
        "msg_deps_ffmpeg":    "\n\nInstalla ffmpeg:\n  sudo apt install ffmpeg",
        "msg_deps_install":   "\n\nInstalla automaticamente?",
        "msg_installed":      "Pacchetti installati.",
        "msg_install_failed": "Installazione fallita:\n{}",
        "msg_no_segments":    "Nessun segmento trascritto.",
        "editor_title":       "Editor Sottotitoli",
        "editor_hint":        "Rivedi e correggi i sottotitoli prima del doppiaggio",
        "editor_col_num":     "#",
        "editor_col_start":   "Inizio",
        "editor_col_end":     "Fine",
        "editor_col_orig":    "Originale",
        "editor_col_trans":   "Traduzione",
        "editor_btn_confirm": "✓  Conferma e avvia doppiaggio",
        "editor_btn_cancel":  "✗  Annulla",
        "editor_edit_title":  "Modifica",
        "editor_seg_label":   "Segmento {} —",
        "editor_btn_save":    "Salva",
        "warn_editor":        "Editor",
    },
    "en": {
        "label_video":        "Video:",
        "label_output":       "Output:",
        "label_model":        "Model:",
        "label_from":         "From:",
        "label_to":           "To:",
        "label_voice":        "Voice:",
        "label_tts_rate":     "TTS Speed:",
        "label_options":      "Options:",
        "label_model_hint":   "← fast / accurate →",
        "label_ui_lang":      "🌐 UI Language:",
        "btn_add":            "+ Add",
        "btn_remove":         "- Remove",
        "btn_clear":          "✗ Clear",
        "btn_browse":         "Browse…",
        "btn_start":          "▶  Start Translation",
        "btn_processing":     "⏳  Processing...",
        "btn_transcribing":   "⏳ Transcribing...",
        "btn_dubbing":        "⏳ Dubbing...",
        "btn_installing":     "⏳  Installing...",
        "opt_subs_only":      "Subtitles only .srt (no dubbing)",
        "opt_no_subs":        "I don't want subtitles",
        "opt_no_demucs":      "Skip voice/music separation (Demucs)",
        "opt_edit_subs":      "Show subtitle editor before dubbing",
        "msg_no_video":       "Add at least one video.",
        "msg_script_missing": "Script not found:\n{}",
        "msg_completed":      "Translation completed!",
        "msg_error":          "Something went wrong. Check the log.",
        "msg_confirm_stop":   "Processing in progress. Stop?",
        "msg_confirm":        "Confirm",
        "msg_completed_t":    "Completed",
        "msg_error_t":        "Error",
        "msg_deps_missing":   "Missing dependencies",
        "msg_deps_python":    "Missing Python packages:\n  • ",
        "msg_deps_bins":      "Missing programs:\n  • ",
        "msg_deps_ffmpeg":    "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
        "msg_deps_install":   "\n\nInstall automatically?",
        "msg_installed":      "Packages installed.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments":    "No segments transcribed.",
        "editor_title":       "Subtitle Editor",
        "editor_hint":        "Review and correct subtitles before dubbing",
        "editor_col_num":     "#",
        "editor_col_start":   "Start",
        "editor_col_end":     "End",
        "editor_col_orig":    "Original",
        "editor_col_trans":   "Translation",
        "editor_btn_confirm": "✓  Confirm and start dubbing",
        "editor_btn_cancel":  "✗  Cancel",
        "editor_edit_title":  "Edit",
        "editor_seg_label":   "Segment {} —",
        "editor_btn_save":    "Save",
        "warn_editor":        "Editor",
    },
}

# Displayed in the UI language dropdown
UI_LANG_OPTIONS = [("it", "🇮🇹 Italiano"), ("en", "🇬🇧 English")]


def check_dependencies():
    missing_pkgs = []
    for mod, pip in REQUIRED_PACKAGES.items():
        try:
            found = importlib.util.find_spec(mod) is not None
        except (ValueError, ModuleNotFoundError):
            found = False
        if not found:
            missing_pkgs.append(pip)
    missing_bins = [b for b in ["ffmpeg", "ffprobe"] if not shutil.which(b)]
    return missing_pkgs, missing_bins


class _TkStreamRedirect(io.TextIOBase):
    """File-like che inoltra ogni scrittura a una callback Tk-safe (via after)."""

    def __init__(self, tk_root, on_write):
        super().__init__()
        self._root = tk_root
        self._on_write = on_write

    def writable(self):
        return True

    def write(self, s):
        if s:
            try:
                self._root.after(0, self._on_write, s)
            except RuntimeError:
                pass
        return len(s) if s else 0

    def flush(self):
        pass


def _load_translator_module(script_path: Path):
    """Carica video_translator.py come modulo una volta sola (cached)."""
    if "_vt_module" in _load_translator_module.__dict__:
        return _load_translator_module._vt_module
    spec = importlib.util.spec_from_file_location("video_translator_lib", str(script_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossibile caricare {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["video_translator_lib"] = module
    spec.loader.exec_module(module)
    _load_translator_module._vt_module = module
    return module


class SubtitleEditor(tk.Toplevel):
    """Finestra per rivedere e correggere i sottotitoli prima del doppiaggio."""

    def __init__(self, parent, segments: list[dict], on_confirm, ui_s=None):
        super().__init__(parent)
        # ui_s is a callable(key) -> str for UI language support
        self._s = ui_s if callable(ui_s) else (lambda k: UI_STRINGS["it"].get(k, k))
        self.title(self._s("editor_title"))
        self.configure(bg=BG)
        self.geometry("900x600")
        self.segments = [s.copy() for s in segments]
        self.on_confirm = on_confirm

        tk.Label(self, text=self._s("editor_hint"),
                 bg=BG, fg=FG2, font=("Helvetica", 9)).pack(pady=(10, 4))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=12, pady=4)

        cols = (self._s("editor_col_num"), self._s("editor_col_start"),
                self._s("editor_col_end"), self._s("editor_col_orig"), self._s("editor_col_trans"))
        self._tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for c, w in zip(cols, [40, 80, 80, 350, 350]):
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, minwidth=w)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._populate()
        self._tree.bind("<Double-1>", self._on_edit)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text=self._s("editor_btn_confirm"),
                  command=self._confirm,
                  bg=ACC, fg=BG, font=("Helvetica", 11, "bold"),
                  relief="flat", padx=16, pady=6).pack(side="left", padx=8)
        tk.Button(btn_frame, text=self._s("editor_btn_cancel"),
                  command=self.destroy,
                  bg=SEL, fg=FG, relief="flat", padx=12, pady=6).pack(side="left")

    def _populate(self):
        self._tree.delete(*self._tree.get_children())
        for i, s in enumerate(self.segments):
            self._tree.insert("", "end", iid=str(i), values=(
                i + 1,
                f"{s['start']:.1f}s",
                f"{s['end']:.1f}s",
                s.get("text_src", s.get("text", "")),
                s["text_tgt"],
            ))

    def _on_edit(self, event):
        item = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)
        if not item or col not in ("#4", "#5"):
            return
        idx = int(item)
        field = "text_src" if col == "#4" else "text_tgt"
        current = self.segments[idx].get(field, self.segments[idx].get("text", ""))
        col_name = self._s("editor_col_orig") if col == "#4" else self._s("editor_col_trans")

        win = tk.Toplevel(self)
        win.title(self._s("editor_edit_title"))
        win.configure(bg=BG)
        win.geometry("500x120")
        tk.Label(win, text=f"{self._s('editor_seg_label').format(idx+1)} {col_name}:",
                 bg=BG, fg=FG).pack(pady=6)
        entry = tk.Entry(win, width=60, bg=SEL, fg=FG, insertbackground=FG,
                         font=("Helvetica", 10), relief="flat")
        entry.insert(0, current)
        entry.pack(padx=10)
        entry.focus()

        def save(_=None):
            self.segments[idx][field] = entry.get()
            self._populate()
            win.destroy()

        entry.bind("<Return>", save)
        tk.Button(win, text=self._s("editor_btn_save"), command=save,
                  bg=ACC, fg=BG, relief="flat", padx=10).pack(pady=6)

    def _confirm(self):
        self.on_confirm(self.segments)
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Translator AI")
        self.resizable(False, False)
        self.configure(bg=BG)

        self._ui_lang = tk.StringVar(value="it")
        self._model = tk.StringVar(value="small")
        self._lang_src = tk.StringVar(value="auto")
        self._lang_tgt = tk.StringVar(value="it")
        self._voice = tk.StringVar(value=LANGUAGES["it"]["voices"][0])
        self._tts_rate = tk.IntVar(value=0)
        self._subs_only = tk.BooleanVar(value=False)
        self._no_subs = tk.BooleanVar(value=False)
        self._no_demucs = tk.BooleanVar(value=False)
        self._edit_subs = tk.BooleanVar(value=False)
        self._running = False
        self._process = None
        self._batch_files: list[str] = []

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._check_deps_on_start)

    def _s(self, key: str) -> str:
        """Returns the UI string for the current language."""
        lang = self._ui_lang.get()
        return UI_STRINGS.get(lang, UI_STRINGS["it"]).get(key, key)

    # ── Deps check ───────────────────────────────────────────────────────────

    def _check_deps_on_start(self):
        missing_pkgs, missing_bins = check_dependencies()
        if not missing_pkgs and not missing_bins:
            return
        msg_parts = []
        if missing_pkgs:
            msg_parts.append(self._s("msg_deps_python") + "\n  • ".join(missing_pkgs))
        if missing_bins:
            msg_parts.append(self._s("msg_deps_bins") + "\n  • ".join(missing_bins))
        msg = "\n\n".join(msg_parts)
        if missing_bins:
            messagebox.showerror(self._s("msg_deps_missing"),
                                 msg + self._s("msg_deps_ffmpeg"))
        elif messagebox.askyesno(self._s("msg_deps_missing"),
                                 msg + self._s("msg_deps_install")):
            self._install_deps(missing_pkgs)

    def _install_deps(self, packages):
        self._btn.configure(state="disabled", text=self._s("btn_installing"))
        self._progress.start(12)
        self._log_write(f"[*] Installing: {', '.join(packages)}\n")

        def do():
            cmd = [sys.executable, "-m", "pip", "install",
                   "--break-system-packages", "--quiet"] + packages
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.after(0, self._install_done, proc.returncode == 0,
                       packages if proc.returncode == 0 else proc.stderr)

        threading.Thread(target=do, daemon=True).start()

    def _install_done(self, ok, info):
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        if ok:
            self._log_write(f"[✓] Installed: {', '.join(info)}\n")
            messagebox.showinfo(self._s("msg_completed_t"), self._s("msg_installed"))
        else:
            self._log_write(f"[✗] Error:\n{info}\n")
            messagebox.showerror(self._s("msg_error_t"),
                                 self._s("msg_install_failed").format(info))

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 5}

        # ── Header row: title + UI language selector ──
        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(16, 2))
        header.columnconfigure(0, weight=1)

        tk.Label(header, text="🎬 Video Translator AI",
                 font=("Helvetica", 16, "bold"), bg=BG, fg=FG).grid(
            row=0, column=0, sticky="w")

        lang_sel_frame = tk.Frame(header, bg=BG)
        lang_sel_frame.grid(row=0, column=1, sticky="e")
        self._lbl_ui_lang = tk.Label(lang_sel_frame, text=self._s("label_ui_lang"),
                                     bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_ui_lang.pack(side="left", padx=(0, 4))
        lang_display = [label for _, label in UI_LANG_OPTIONS]
        self._ui_lang_combo = ttk.Combobox(lang_sel_frame, values=lang_display,
                                            state="readonly", width=12, font=("Helvetica", 8))
        # Set current selection
        current_idx = next((i for i, (k, _) in enumerate(UI_LANG_OPTIONS)
                            if k == self._ui_lang.get()), 0)
        self._ui_lang_combo.current(current_idx)
        self._ui_lang_combo.pack(side="left")
        self._ui_lang_combo.bind("<<ComboboxSelected>>", self._on_ui_lang_change)

        tk.Label(self, text="faster-whisper  •  Demucs  •  Google Translate  •  Edge-TTS",
                 font=("Helvetica", 9), bg=BG, fg=FG2).grid(row=1, column=0, columnspan=3)

        ttk.Separator(self, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=6)

        # ── Batch file list ──
        self._lbl_video = self._row_label(3, self._s("label_video"))
        batch_frame = tk.Frame(self, bg=BG)
        batch_frame.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)
        self._batch_listbox = tk.Listbox(batch_frame, height=4, width=52,
                                         bg=SEL, fg=FG, selectbackground=ACC,
                                         font=("Monospace", 8), relief="flat")
        self._batch_listbox.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(batch_frame, command=self._batch_listbox.yview)
        self._batch_listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="left", fill="y")
        btn_col = tk.Frame(batch_frame, bg=BG)
        btn_col.pack(side="left", padx=(6, 0))
        self._btn_add = tk.Button(btn_col, text=self._s("btn_add"), command=self._add_files,
                                   bg=SEL, fg=FG, relief="flat", width=10)
        self._btn_add.pack(pady=2)
        self._btn_remove = tk.Button(btn_col, text=self._s("btn_remove"), command=self._remove_file,
                                      bg=SEL, fg=FG, relief="flat", width=10)
        self._btn_remove.pack(pady=2)
        self._btn_clear = tk.Button(btn_col, text=self._s("btn_clear"), command=self._clear_files,
                                     bg=SEL, fg=FG, relief="flat", width=10)
        self._btn_clear.pack(pady=2)

        # Output
        self._lbl_output = self._row_label(4, self._s("label_output"))
        self._output_var = tk.StringVar()
        out_entry = tk.Entry(self, textvariable=self._output_var, width=42,
                             bg=SEL, fg=FG, insertbackground=FG,
                             relief="flat", font=("Helvetica", 9))
        out_entry.grid(row=4, column=1, sticky="ew", padx=(0, 6), pady=5)
        self._btn_browse = tk.Button(self, text=self._s("btn_browse"), command=self._browse_output,
                                      bg="#45475a", fg=FG, relief="flat")
        self._btn_browse.grid(row=4, column=2, padx=(0, 16))

        ttk.Separator(self, orient="horizontal").grid(
            row=5, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # ── Modello Whisper ──
        self._lbl_model = self._row_label(6, self._s("label_model"))
        mf = tk.Frame(self, bg=BG)
        mf.grid(row=6, column=1, columnspan=2, sticky="w", **pad)
        for m in WHISPER_MODELS:
            color = RED if "large" in m else FG
            tk.Radiobutton(mf, text=m, variable=self._model, value=m,
                           bg=BG, fg=color, selectcolor=SEL,
                           activebackground=BG, font=("Helvetica", 9)).pack(side="left", padx=3)
        self._lbl_model_hint = tk.Label(mf, text=self._s("label_model_hint"),
                                         bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_model_hint.pack(side="left", padx=6)

        # ── Lingua sorgente ──
        self._lbl_from = self._row_label(7, self._s("label_from"))
        src_frame = tk.Frame(self, bg=BG)
        src_frame.grid(row=7, column=1, columnspan=2, sticky="w", **pad)
        src_names = list(SOURCE_LANGS.values())
        src_keys = list(SOURCE_LANGS.keys())
        self._src_combo = ttk.Combobox(src_frame, values=src_names,
                                        state="readonly", width=22, font=("Helvetica", 9))
        self._src_combo.current(0)
        self._src_combo.pack(side="left")
        self._src_combo.bind("<<ComboboxSelected>>",
                              lambda e: self._lang_src.set(src_keys[self._src_combo.current()]))

        # ── Lingua destinazione ──
        self._lbl_to = self._row_label(8, self._s("label_to"))
        tgt_frame = tk.Frame(self, bg=BG)
        tgt_frame.grid(row=8, column=1, columnspan=2, sticky="w", **pad)
        tgt_names = [v["name"] for v in LANGUAGES.values()]
        self._tgt_combo = ttk.Combobox(tgt_frame, values=tgt_names,
                                        state="readonly", width=22, font=("Helvetica", 9))
        it_idx = list(LANGUAGES.keys()).index("it")
        self._tgt_combo.current(it_idx)
        self._tgt_combo.pack(side="left")
        self._tgt_combo.bind("<<ComboboxSelected>>", self._on_lang_tgt_change)

        # ── Voce ──
        self._lbl_voice = self._row_label(9, self._s("label_voice"))
        self._voice_frame = tk.Frame(self, bg=BG)
        self._voice_frame.grid(row=9, column=1, columnspan=2, sticky="w", **pad)
        self._build_voice_buttons()

        # ── Velocità TTS ──
        self._lbl_tts_rate = self._row_label(10, self._s("label_tts_rate"))
        rate_frame = tk.Frame(self, bg=BG)
        rate_frame.grid(row=10, column=1, columnspan=2, sticky="w", **pad)
        self._lbl_rate_minus = tk.Label(rate_frame, text="-50%", bg=BG, fg=FG2,
                                         font=("Helvetica", 8))
        self._lbl_rate_minus.pack(side="left")
        self._rate_slider = ttk.Scale(rate_frame, from_=-50, to=50,
                                       variable=self._tts_rate, orient="horizontal", length=200)
        self._rate_slider.pack(side="left", padx=6)
        self._lbl_rate_plus = tk.Label(rate_frame, text="+50%", bg=BG, fg=FG2,
                                        font=("Helvetica", 8))
        self._lbl_rate_plus.pack(side="left")
        self._rate_lbl = tk.Label(rate_frame, text="+0%", bg=BG, fg=ACC,
                                   font=("Helvetica", 9, "bold"), width=6)
        self._rate_lbl.pack(side="left", padx=4)
        self._tts_rate.trace_add("write", self._update_rate_label)

        ttk.Separator(self, orient="horizontal").grid(
            row=11, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # ── Opzioni ──
        self._lbl_options = self._row_label(12, self._s("label_options"))
        opts = tk.Frame(self, bg=BG)
        opts.grid(row=12, column=1, columnspan=2, sticky="w", **pad)

        def cb(parent, text_key, var, cmd=None):
            w = tk.Checkbutton(parent, text=self._s(text_key), variable=var, command=cmd,
                               bg=BG, fg=FG, selectcolor=SEL,
                               activebackground=BG, font=("Helvetica", 9))
            w._text_key = text_key
            return w

        self._chk_subs_only = cb(opts, "opt_subs_only", self._subs_only, self._on_subs_only)
        self._chk_subs_only.grid(row=0, column=0, sticky="w")
        self._chk_no_subs = cb(opts, "opt_no_subs", self._no_subs, self._on_no_subs)
        self._chk_no_subs.grid(row=1, column=0, sticky="w")
        self._chk_no_demucs = cb(opts, "opt_no_demucs", self._no_demucs)
        self._chk_no_demucs.grid(row=0, column=1, sticky="w", padx=16)
        self._chk_edit_subs = cb(opts, "opt_edit_subs", self._edit_subs)
        self._chk_edit_subs.grid(row=1, column=1, sticky="w", padx=16)

        ttk.Separator(self, orient="horizontal").grid(
            row=13, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # ── Bottone avvia ──
        self._btn = tk.Button(self, text=self._s("btn_start"),
                              command=self._start,
                              bg=ACC, fg=BG, font=("Helvetica", 12, "bold"),
                              relief="flat", padx=20, pady=8, cursor="hand2",
                              activebackground="#74c7ec")
        self._btn.grid(row=14, column=0, columnspan=3, pady=8)

        # ── Log ──
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=15, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="ew")
        self._log = tk.Text(log_frame, height=12, width=76,
                            bg="#11111b", fg=GRN, font=("Monospace", 8),
                            relief="flat", state="disabled", wrap="word")
        vsb = tk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=16, column=0, columnspan=3, padx=16, pady=(0, 12))

        self.columnconfigure(1, weight=1)

    def _row_label(self, row, text):
        lbl = tk.Label(self, text=text, bg=BG, fg="#bac2de",
                       font=("Helvetica", 9, "bold"), anchor="e")
        lbl.grid(row=row, column=0, sticky="e", padx=(16, 8), pady=5)
        return lbl

    def _on_ui_lang_change(self, _=None):
        idx = self._ui_lang_combo.current()
        new_lang = UI_LANG_OPTIONS[idx][0]
        self._ui_lang.set(new_lang)
        self._apply_lang()

    def _apply_lang(self):
        """Update all UI widget texts to the current language."""
        self._lbl_ui_lang.configure(text=self._s("label_ui_lang"))
        self._lbl_video.configure(text=self._s("label_video"))
        self._lbl_output.configure(text=self._s("label_output"))
        self._lbl_model.configure(text=self._s("label_model"))
        self._lbl_model_hint.configure(text=self._s("label_model_hint"))
        self._lbl_from.configure(text=self._s("label_from"))
        self._lbl_to.configure(text=self._s("label_to"))
        self._lbl_voice.configure(text=self._s("label_voice"))
        self._lbl_tts_rate.configure(text=self._s("label_tts_rate"))
        self._lbl_options.configure(text=self._s("label_options"))
        self._btn_add.configure(text=self._s("btn_add"))
        self._btn_remove.configure(text=self._s("btn_remove"))
        self._btn_clear.configure(text=self._s("btn_clear"))
        self._btn_browse.configure(text=self._s("btn_browse"))
        # Only update main button text if not currently running
        if not self._running:
            self._btn.configure(text=self._s("btn_start"))
        self._chk_subs_only.configure(text=self._s("opt_subs_only"))
        self._chk_no_subs.configure(text=self._s("opt_no_subs"))
        self._chk_no_demucs.configure(text=self._s("opt_no_demucs"))
        self._chk_edit_subs.configure(text=self._s("opt_edit_subs"))
        # Update source language combo values when language changes
        lang = self._ui_lang.get()
        src_map = SOURCE_LANGS_EN if lang == "en" else SOURCE_LANGS
        src_names = list(src_map.values())
        src_keys = list(src_map.keys())
        cur_key = self._lang_src.get()
        self._src_combo["values"] = src_names
        try:
            self._src_combo.current(src_keys.index(cur_key))
        except ValueError:
            self._src_combo.current(0)
        # Rebind source combo to use updated keys
        self._src_combo.bind("<<ComboboxSelected>>",
                              lambda e, k=src_keys: self._lang_src.set(k[self._src_combo.current()]))

    def _build_voice_buttons(self):
        for w in self._voice_frame.winfo_children():
            w.destroy()
        lang_key = list(LANGUAGES.keys())[self._tgt_combo.current()]
        voices = LANGUAGES[lang_key]["voices"]
        self._voice.set(voices[0])
        for v in voices:
            label = v.split("-")[2].replace("Neural", "").replace("Multilingual", "ML")
            tk.Radiobutton(self._voice_frame, text=label, variable=self._voice, value=v,
                           bg=BG, fg=FG, selectcolor=SEL,
                           activebackground=BG, font=("Helvetica", 9)).pack(side="left", padx=3)

    def _on_lang_tgt_change(self, _=None):
        lang_key = list(LANGUAGES.keys())[self._tgt_combo.current()]
        self._lang_tgt.set(lang_key)
        self._build_voice_buttons()

    def _update_rate_label(self, *_):
        try:
            v = int(round(self._tts_rate.get()))
        except (ValueError, tk.TclError):
            v = 0
        self._rate_lbl.configure(text=f"{v:+d}%")

    def _on_subs_only(self):
        if self._subs_only.get():
            self._no_subs.set(False)

    def _on_no_subs(self):
        if self._no_subs.get():
            self._subs_only.set(False)

    # ── File management ──────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title=self._s("label_video"),
            filetypes=[("Video", "*.mp4 *.mkv *.webm *.avi *.mov"), ("All", "*.*")]
        )
        for p in paths:
            if p not in self._batch_files:
                self._batch_files.append(p)
                self._batch_listbox.insert("end", Path(p).name)

    def _remove_file(self):
        sel = self._batch_listbox.curselection()
        for i in reversed(sel):
            self._batch_files.pop(i)
            self._batch_listbox.delete(i)

    def _clear_files(self):
        self._batch_files.clear()
        self._batch_listbox.delete(0, "end")

    def _browse_output(self):
        p = filedialog.asksaveasfilename(
            title=self._s("label_output"),
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("All", "*.*")]
        )
        if p:
            self._output_var.set(p)

    # ── Avvio ────────────────────────────────────────────────────────────────

    def _start(self):
        if self._running:
            return
        if not self._batch_files:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_video"))
            return
        if not TRANSLATOR_SCRIPT.exists():
            messagebox.showerror(self._s("msg_error_t"),
                                 self._s("msg_script_missing").format(TRANSLATOR_SCRIPT))
            return

        if self._edit_subs.get() and len(self._batch_files) == 1:
            self._start_with_editor(self._batch_files[0])
        else:
            self._run_batch(self._batch_files)

    def _build_cmd(self, video_path: str, output: str | None = None) -> list[str]:
        cmd = [sys.executable, str(TRANSLATOR_SCRIPT), video_path]
        out = output or self._output_var.get().strip()
        if out and len(self._batch_files) == 1:
            cmd += ["-o", out]
        cmd += ["--model", self._model.get()]
        cmd += ["--lang-source", self._lang_src.get()]
        cmd += ["--lang-target", self._lang_tgt.get()]
        cmd += ["--voice", self._voice.get()]
        try:
            rate = int(round(self._tts_rate.get()))
        except (ValueError, tk.TclError):
            rate = 0
        cmd += ["--tts-rate", f"{rate:+d}%"]
        if self._subs_only.get():
            cmd.append("--subs-only")
        if self._no_subs.get():
            cmd.append("--no-subs")
        if self._no_demucs.get():
            cmd.append("--no-demucs")
        return cmd

    def _start_with_editor(self, video_path: str):
        """Fase 1: trascrizione+traduzione, poi apre editor prima del doppiaggio."""
        self._log_write("Phase 1: Transcription + translation (no dubbing)...\n")
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_transcribing"))
        self._progress.start(12)

        def phase1():
            redirect = _TkStreamRedirect(self, self._log_write)
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = redirect
            sys.stderr = redirect
            try:
                vt = _load_translator_module(TRANSLATOR_SCRIPT)
                result = vt.translate_video(
                    video_in=video_path,
                    model=self._model.get(),
                    lang_source=self._lang_src.get(),
                    lang_target=self._lang_tgt.get(),
                    subs_only=True,
                    no_demucs=self._no_demucs.get(),
                )
                self.after(0, self._open_editor, video_path, result["segments"])
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.after(0, self._log_write, f"[x] Error: {e}\n{tb}\n")
                self.after(0, self._on_done, False)
            finally:
                sys.stdout, sys.stderr = old_out, old_err

        threading.Thread(target=phase1, daemon=True).start()

    def _open_editor(self, video_path: str, segments: list[dict]):
        self._progress.stop()
        self._running = False
        self._btn.configure(state="normal", text=self._s("btn_start"))
        self._log_write(f"[i] {len(segments)} segments ready. Opening editor...\n")

        if not segments:
            messagebox.showwarning(self._s("warn_editor"), self._s("msg_no_segments"))
            return

        def on_confirm(edited_segments):
            self._log_write("[i] Subtitles confirmed. Starting dubbing...\n")
            self._run_batch_with_segments(video_path, edited_segments)

        SubtitleEditor(self, segments, on_confirm, ui_s=self._s)

    def _run_batch_with_segments(self, video_path: str, segments: list[dict]):
        """Fase 2: doppiaggio con segmenti dall'editor."""
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_dubbing"))
        self._progress.start(12)

        try:
            rate_int = int(round(self._tts_rate.get()))
        except (ValueError, tk.TclError):
            rate_int = 0
        params = {
            "model": self._model.get(),
            "lang_source": self._lang_src.get(),
            "lang_target": self._lang_tgt.get(),
            "voice": self._voice.get(),
            "tts_rate": f"{rate_int:+d}%",
            "no_subs": self._no_subs.get(),
            "no_demucs": self._no_demucs.get(),
        }

        def do():
            redirect = _TkStreamRedirect(self, self._log_write)
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = redirect
            sys.stderr = redirect
            try:
                vt = _load_translator_module(TRANSLATOR_SCRIPT)
                vt.translate_video(
                    video_in=video_path,
                    model=params["model"],
                    lang_source=params["lang_source"],
                    lang_target=params["lang_target"],
                    voice=params["voice"],
                    tts_rate=params["tts_rate"],
                    no_subs=params["no_subs"],
                    no_demucs=params["no_demucs"],
                    segments_override=segments,
                )
                self.after(0, self._on_done, True)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.after(0, self._log_write, f"[x] {e}\n{tb}\n")
                self.after(0, self._on_done, False)
            finally:
                sys.stdout, sys.stderr = old_out, old_err

        threading.Thread(target=do, daemon=True).start()

    def _run_batch(self, files: list[str]):
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_processing"))
        self._progress.start(12)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

        total = len(files)
        cmds = [(i, f, self._build_cmd(f)) for i, f in enumerate(files)]

        def run_all():
            all_ok = True
            for i, f, cmd in cmds:
                self.after(0, self._log_write,
                           f"\n{'-'*50}\n[{i+1}/{total}] {Path(f).name}\n{'-'*50}\n")
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, bufsize=0, env=env)
                except FileNotFoundError as e:
                    self.after(0, self._log_write, f"[x] {e}\n")
                    all_ok = False
                    continue
                self._process = proc
                buf = bytearray()
                in_progress = False
                try:
                    while True:
                        chunk = proc.stdout.read(64)
                        if not chunk:
                            break
                        for b in chunk:
                            if b == 0x0D:
                                line = bytes(buf).decode("utf-8", errors="replace")
                                buf.clear()
                                if in_progress:
                                    self.after(0, self._log_replace_last, line)
                                else:
                                    self.after(0, self._log_write, line)
                                    in_progress = True
                            elif b == 0x0A:
                                line = bytes(buf).decode("utf-8", errors="replace")
                                buf.clear()
                                if in_progress:
                                    if line:
                                        self.after(0, self._log_replace_last, line)
                                    self.after(0, self._log_write, "\n")
                                    in_progress = False
                                else:
                                    self.after(0, self._log_write, line + "\n")
                            else:
                                buf.append(b)
                    if buf:
                        self.after(0, self._log_write,
                                   bytes(buf).decode("utf-8", errors="replace"))
                        buf.clear()
                finally:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
                rc = proc.wait()
                if rc != 0:
                    all_ok = False
                    self.after(0, self._log_write, f"\n[x] Exit code {rc} for {Path(f).name}\n")
            self._process = None
            self.after(0, self._on_done, all_ok)

        threading.Thread(target=run_all, daemon=True).start()

    # ── Log ─────────────────────────────────────────────────────────────────

    def _log_write(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _log_replace_last(self, text: str):
        self._log.configure(state="normal")
        self._log.delete("end-1c linestart", "end-1c lineend")
        self._log.insert("end-1c linestart", text.rstrip("\r\n"))
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Fine ─────────────────────────────────────────────────────────────────

    def _on_done(self, success: bool):
        self._running = False
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        if success:
            self._log_write("\n✓ Done!\n")
            messagebox.showinfo(self._s("msg_completed_t"), self._s("msg_completed"))
        else:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_error"))

    def _on_close(self):
        if self._running and self._process:
            if messagebox.askyesno(self._s("msg_confirm"), self._s("msg_confirm_stop")):
                try:
                    self._process.terminate()
                    self._process.wait(timeout=3)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
            else:
                return
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
