#!/usr/bin/env python3
"""
Video Translator AI - single-file edition
Pipeline: faster-Whisper (GPU) + Demucs + Google Translate + Edge-TTS
Run with arguments for CLI mode, without for GUI mode.
"""

# ═══════════════════════════════════════════════════════════
#  IMPORTS
# ═══════════════════════════════════════════════════════════

import argparse
import asyncio
import dataclasses
import contextlib
import ctypes
import ctypes.util
import datetime
import importlib.util
import io
import locale
import traceback
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Ensure local package modules resolve even when Python is launched with safe
# path mode or a user environment that omits the script directory from sys.path.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════

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

SOURCE_LANGS = {
    "auto": "🔍 Rilevamento automatico", "en": "🇬🇧 Inglese", "it": "🇮🇹 Italiano",
    "es": "🇪🇸 Spagnolo", "fr": "🇫🇷 Francese", "de": "🇩🇪 Tedesco",
    "pt": "🇧🇷 Portoghese", "ru": "🇷🇺 Russo", "zh-CN": "🇨🇳 Cinese",
    "ja": "🇯🇵 Giapponese", "ko": "🇰🇷 Coreano", "ar": "🇸🇦 Arabo",
}

SOURCE_LANGS_EN = {
    "auto": "🔍 Auto detect", "en": "🇬🇧 English", "it": "🇮🇹 Italian",
    "es": "🇪🇸 Spanish", "fr": "🇫🇷 French", "de": "🇩🇪 German",
    "pt": "🇧🇷 Portuguese", "ru": "🇷🇺 Russian", "zh-CN": "🇨🇳 Chinese",
    "ja": "🇯🇵 Japanese", "ko": "🇰🇷 Korean", "ar": "🇸🇦 Arabic",
}

# Languages supported by XTTS v2 (maps our codes → XTTS codes)
XTTS_LANGS = {
    "ar": "ar", "zh-CN": "zh-cn", "cs": "cs", "de": "de",
    "en": "en", "es": "es", "fr": "fr", "hi": "hi",
    "hu": "hu", "it": "it", "ja": "ja", "ko": "ko",
    "nl": "nl", "pl": "pl", "pt": "pt", "ru": "ru", "tr": "tr",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"]


def _pick_default_whisper_model() -> str:
    # large-v3-turbo (~1.6 GB) has comparable quality to large-v3 but is ~6-8x
    # faster on CUDA GPU. On CPU it is too heavy: fall back to small.
    import shutil as _sh
    return "large-v3-turbo" if _sh.which("nvidia-smi") else "small"


DEFAULT_WHISPER_MODEL = _pick_default_whisper_model()
DEFAULT_LANG = "it"

# Expansion ratio relative to English (≈1.0). Values >1 mean the language uses
# more characters/syllables/seconds than EN to express the same content; <1
# the opposite. Sources: multilingual corpora (UN Parallel, TED, Europarl,
# OPUS), used as approximations for XTTS speed autotune on asymmetric pairs.
LANG_EXPANSION: dict[str, float] = {
    "en": 1.00,
    "zh-CN": 0.70, "zh": 0.70, "ja": 0.85, "ko": 0.90,
    "it": 1.25, "es": 1.25, "pt": 1.22, "fr": 1.27, "de": 1.20,
    "nl": 1.18, "sv": 1.15, "da": 1.12, "no": 1.12, "fi": 1.10,
    "ru": 1.15, "uk": 1.15, "pl": 1.15, "cs": 1.10, "hu": 1.20,
    "ar": 1.08, "hi": 1.10, "tr": 1.10, "el": 1.20, "ro": 1.20,
    "vi": 1.15, "id": 1.10,
}


def _suggest_xtts_speed(
    lang_source: str,
    lang_target: str,
    user_override: float | None = None,
) -> tuple[float, float, bool]:
    """Autotune XTTS v2 speed based on the asymmetry between source and target languages.

    Returns (speed, ratio, auto) where:
    - speed: value to pass to `generate_tts_xtts`, in the range [1.10, 1.40];
    - ratio: expansion of the target relative to the source (target/source);
    - auto: True if the value was computed, False if it is a user override.

    If `user_override` is provided (via CLI --xtts-speed or an explicit JSON
    config key), it is honoured without modification - we trust the user knows
    what they are doing. With `user_override=None` the heuristic picks a higher
    speed when the target is significantly longer than the source (EN→IT, EN→FR…)
    to give XTTS more headroom and reduce audible atempo post-processing.
    An unknown or "auto" source is treated as EN (base ratio 1.0).
    """
    def _norm(code: str) -> str:
        c = (code or "").strip()
        if not c or c.lower() == "auto":
            return "en"
        # Chinese: map all variants to the "zh" entry in the table.
        if c.lower().startswith("zh"):
            # Accept both "zh" and "zh-CN" (both present in the table)
            return c if c in LANG_EXPANSION else "zh"
        return c

    src = _norm(lang_source)
    tgt = _norm(lang_target)
    src_exp = LANG_EXPANSION.get(src, 1.0)
    tgt_exp = LANG_EXPANSION.get(tgt, 1.0)
    # Guard: if either value is 0 (should not happen) avoid div/0.
    ratio = (tgt_exp / src_exp) if src_exp > 0 else 1.0

    if user_override is not None:
        # Always honour the explicit choice, but still return the ratio
        # for the caller's log/debug purposes.
        return float(user_override), ratio, False

    if ratio >= 1.20:
        speed = 1.35   # target much longer (e.g. EN→IT, EN→FR)
    elif ratio >= 1.10:
        speed = 1.30   # target moderately longer
    elif ratio <= 0.75:
        # Target noticeably shorter (e.g. EN→ZH 0.70). Threshold 0.75 (not 0.90
        # as in the first draft) so that IT→EN (ratio 0.80) is NOT touched - the
        # v1.4 empirical tuning already locked it at 1.25. With 0.90 we would
        # have regressed IT→EN to 1.15, violating the "don't break what works"
        # constraint.
        speed = 1.15
    else:
        speed = 1.25   # symmetric / near-symmetric (e.g. IT→EN 0.80, IT→ES, EN→JA 0.85)

    # Safety cap within the useful range (below 1.10 XTTS sounds sluggish;
    # above 1.40 prosody starts to degrade even natively).
    speed = max(1.10, min(speed, 1.40))
    return speed, ratio, True


# Chars/sec baseline for XTTS v2 at speed=1.0 (empirical aggregate from real
# segments in v1.4-v1.6). Used to estimate how long XTTS would take to speak a
# text without time-stretching, and to decide how much native speed is needed
# to fit it into a time slot. Syllabic/logographic languages (ja/zh) have much
# lower chars/sec because 1 character = 1 syllable or concept.
_XTTS_CHARS_PER_SEC = {
    "en": 16.0, "it": 15.0, "es": 15.5, "fr": 15.0, "de": 14.5,
    "pt": 15.0, "nl": 15.0, "ja": 10.0, "zh-CN": 8.0, "zh": 8.0, "ko": 10.5,
    "ru": 13.5, "ar": 13.0, "hi": 13.0, "tr": 14.0, "pl": 13.5,
    "uk": 13.5, "cs": 14.0, "el": 13.0, "hu": 13.0, "fi": 13.5,
    "sv": 14.5, "da": 14.5, "no": 14.5, "ro": 14.5, "vi": 13.0,
    "id": 14.0,
}


def _estimate_tts_duration_s(text: str, lang: str) -> float:
    """Estimate the duration (seconds) XTTS would need to speak `text` in
    `lang` at speed=1.0. Uses the `_XTTS_CHARS_PER_SEC` table; falls back to
    14.0 chars/sec (European average) for languages not in the table. Minimum
    0.5 s to avoid degenerate division on very short texts.

    The lookup is **case-insensitive** because callers pass the code in the
    form expected by XTTS (`zh-cn` lowercase) while the table uses `zh-CN`
    with the short variant `zh`. Without normalisation Chinese would fall
    through to the 14.0 default (European average), underestimating the
    duration by ~1.75x and defeating adaptive speed on the language with the
    most extreme chars/sec gap.
    """
    key = (lang or "").strip()
    rate = _XTTS_CHARS_PER_SEC.get(key)
    if rate is None:
        rate = _XTTS_CHARS_PER_SEC.get(key.lower())
    if rate is None:
        # Strip region suffix (es. "zh-cn" → "zh", "pt-br" → "pt").
        rate = _XTTS_CHARS_PER_SEC.get(key.split("-")[0].lower(), 14.0)
    n = len((text or "").strip())
    return max(0.5, n / rate)


def _compute_segment_speed(
    text: str,
    slot_s: float,
    lang_target: str,
    ceiling: float = 1.40,
) -> float:
    """Compute the adaptive XTTS v2 speed for a single segment.

    Idea: if the text already fits comfortably in the slot at speed=1.0, keep
    the speed low (fewer artifacts); if it would need >40% compression, raise
    it up to `ceiling` to reduce the atempo post-processing that is the main
    source of "metallic" audio.

    Parameters:
      text        : target text to synthesise (may be empty)
      slot_s      : duration of the source slot in seconds
      lang_target : language code for lookup in `_XTTS_CHARS_PER_SEC`
      ceiling     : upper cap (typically the global autotune speed)

    Returns: speed in the range [1.05, min(1.40, ceiling)]. Guard on slot_s<=0.
    """
    hard_cap = min(1.40, max(1.05, ceiling))
    if not text or slot_s <= 0:
        return max(1.05, min(hard_cap, 1.25))
    est = _estimate_tts_duration_s(text, lang_target)
    required = est / slot_s
    return max(1.05, min(required, hard_cap))


# Migration bridge: the legacy single-file entry point keeps its historical
# private names, while new code lives in small importable modules with tests.
from videotranslator.timing import (  # noqa: E402
    compute_segment_speed as _compute_segment_speed,
    estimate_tts_duration_s as _estimate_tts_duration_s,
    suggest_xtts_speed as _suggest_xtts_speed,
)
from videotranslator.preflight import (  # noqa: E402
    find_missing_dependencies as _find_missing_dependencies,
    format_preflight_report as _format_preflight_report,
    libmpv_native_check as _libmpv_native_check,
    run_preflight as _run_preflight,
)
REQUIRED_PACKAGES = {
    "faster_whisper": "faster-whisper",
    "edge_tts":       "edge-tts",
    "deep_translator": "deep-translator",
    "pydub":          "pydub",
    "demucs":         "demucs",
    "yt_dlp":         "yt-dlp",
    "torchcodec":     "torchcodec",
    # `requests` is used by DeepL and the new Ollama engine (v2.0). It is
    # already a transitive dependency of deep-translator, but declaring it
    # explicitly ensures check_dependencies reports it immediately if the
    # install is broken.
    "requests":       "requests",
}
if sys.version_info >= (3, 13):
    REQUIRED_PACKAGES["audioop"] = "audioop-lts"

# Optional packages: improve quality but do not block startup.
# key = Python module name, value = (list of pip requirements, UI description)
# Maintained fork (Idiap): universal pure-Python wheel for Py ≥3.10, avoids
# the broken setup.py of the original `TTS` package on Windows. Pin
# transformers<5.1 (5.x removes isin_mps_friendly; 5.1 breaks coqui-tts - issue #558).
_TTS_PKGS = ["coqui-tts", "transformers<5.1"]
OPTIONAL_PACKAGES: dict[str, tuple[list[str], str]] = {
    "sacremoses":    (["sacremoses"],    "MarianMT tokenizer (traduzione offline)"),
    "sentencepiece": (["sentencepiece"], "MarianMT tokenizer (traduzione offline)"),
    "TTS":           (_TTS_PKGS,         "XTTS v2 (sintesi vocale alta qualità, ~2 GB)"),
    # Key "pyannote" (parent namespace) instead of "pyannote.audio": find_spec
    # on a dotted name raises ModuleNotFoundError when the parent is not
    # installed instead of returning None, which breaks _check_optional_deps.
    # The parent namespace only exists when pyannote.audio is installed.
    # Upper bound <4.0 aligned with install_windows.bat: pyannote 4.x requires
    # torch>=2.8 (CUDA 13), incompatible with the project's torch 2.6 pin
    # (tested: without the upper bound pip installs 4.x and breaks the CUDA env).
    "pyannote":      (["pyannote.audio>=3.1,<4.0"], "Diarization multi-speaker (pyannote, richiede HF token gratuito)"),
    "silero_vad":    (["silero-vad"],    "VAD per reference XTTS (selezione speech continuo)"),
    "keyring":       (["keyring"],       "Storage sicuro HF token (Credential Manager / Keychain / Secret Service)"),
}
# Aliases for modules that may have different names depending on the installed version
_OPTIONAL_ALIASES: dict[str, list[str]] = {
    "TTS": ["TTS", "coqui_tts"],
}

# ── GUI colours and fonts ────────────────────────────────────
# The concrete values are owned by the theme system: ThemeManager.apply()
# rewrites these module globals on every theme change, so code below keeps
# reading BG / FG / ACC / CARD ... and stays theme-agnostic. The values set
# here are only the import-time defaults (Graphite).
from videotranslator.ui_theme import resolve_palette as _resolve_palette  # noqa: E402
from videotranslator.ui_theme import normalize_ui_settings as _normalize_ui_settings  # noqa: E402
from videotranslator.ui_layout import PANEL_IDS as _PANEL_IDS  # noqa: E402
from videotranslator.ui_layout import normalize_panel_order as _normalize_panel_order  # noqa: E402
from videotranslator.ui_layout import move_panel as _move_panel  # noqa: E402
from videotranslator.ui_layout import drop_index as _drop_index  # noqa: E402
from videotranslator.ui_layout import RIGHT_COLUMN_MIN_WIDTH as _RIGHT_COLUMN_MIN_WIDTH  # noqa: E402
from videotranslator.ui_layout import right_column_width as _right_column_width  # noqa: E402
from videotranslator.ui_layout import WheelAccumulator as _WheelAccumulator  # noqa: E402
from videotranslator.ui_theme_tk import GLOBAL_ALIASES as _GLOBAL_ALIASES  # noqa: E402
from videotranslator.ui_theme_tk import ThemeManager as _ThemeManager  # noqa: E402
from videotranslator import libmpv_runtime as _libmpv_runtime  # noqa: E402
from videotranslator import platforms as _platforms  # noqa: E402
from videotranslator import live_session as _live_session_module  # noqa: E402
from videotranslator import player_core as _player_core  # noqa: E402
from videotranslator import player_engine as _player_engine  # noqa: E402
from videotranslator import player_settings as _player_settings_module  # noqa: E402
from videotranslator import system_packages as _system_packages  # noqa: E402
from videotranslator.live_bar_tk import LiveBar as _LiveBar  # noqa: E402
from videotranslator.player_panel_tk import HoverTip as _HoverTip  # noqa: E402
from videotranslator.player_panel_tk import PlayerPanel as _PlayerPanel  # noqa: E402
from videotranslator.ui_theme import (  # noqa: E402
    ACCENTS as _ACCENTS,
    ACCENT_CHOICES as _ACCENT_CHOICES,
    DEFAULT_ACCENT as _DEFAULT_ACCENT,
    DEFAULT_SCALE as _DEFAULT_SCALE,
    DEFAULT_THEME as _DEFAULT_THEME,
    SCALES as _SCALES,
    SYSTEM_DARK_KEY as _SYSTEM_DARK_KEY,
    THEME_CHOICES as _THEME_CHOICES,
    cached_system_dark as _cached_system_dark,
)

_DEFAULT_PALETTE = _resolve_palette("graphite")
for _name, _field in _GLOBAL_ALIASES.items():
    globals()[_name] = getattr(_DEFAULT_PALETTE, _field)
del _name, _field
# Explicit names for linters / readers (values above win at runtime).
BG = globals()["BG"]; FG = globals()["FG"]; FG2 = globals()["FG2"]; ACC = globals()["ACC"]
ACC2 = globals()["ACC2"]; SEL = globals()["SEL"]; RED = globals()["RED"]; GRN = globals()["GRN"]
CARD = globals()["CARD"]; BORDER = globals()["BORDER"]; PILL = globals()["PILL"]
SURFACE = globals()["SURFACE"]; FIELD = globals()["FIELD"]; BTN = globals()["BTN"]
ACC_HOVER = globals()["ACC_HOVER"]; ACC_SOFT = globals()["ACC_SOFT"]; ACC_FG = globals()["ACC_FG"]
OK = globals()["OK"]; WARN = globals()["WARN"]; ERR = globals()["ERR"]


# Pixel width at which hints and long checkbox texts wrap inside the settings
# column (460 px minus card and accordion padding).
_HINT_WRAP = 370


def _field_colors() -> dict:
    """Selection and cursor colours for tk.Entry / tk.Text, read at call time.

    Left unset, these options keep Tk's defaults (grey selection on a dark
    field) instead of following the theme.
    """
    return {"selectbackground": SEL, "selectforeground": FG, "insertbackground": FG}

# Named fonts (created by ThemeManager; Tk updates every widget on change).
# Roles: Small 8, SmallBold 8b, Base 9, Bold 9b, Italic 8i, Large 11b,
# Title 15b, Mono 9 (always monospace: log, paths, tokens).

# ── UI translation strings ───────────────────────────────────
UI_STRINGS = {
    "it": {
        "label_video":        "Video:",
        "label_output":       "Output:",
        "label_output_dir": "Cartella output:",
        "label_from":         "Da:",
        "label_to":           "A:",
        "label_voice":        "Voce:",
        "label_tts_rate":     "Velocità TTS:",
        "panel_input": "Input",
        "panel_translation": "Traduzione",
        "panel_profile": "Profilo di lavoro",
        "panel_start": "Avvio",
        "section_audio": "Audio",
        "section_voice_cloning": "Voice Cloning",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Diarization",
        "section_model": "Modello",
        "section_engine": "Motore traduzione",
        "section_subtitles": "Sottotitoli",
        "section_hotwords": "Parole chiave",
        "label_model_hint":   "← veloce / preciso → (turbo: qualità large-v3, ~6-8× più veloce su GPU)",
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
        "opt_xtts":           "🎙 Voice Cloning (Coqui XTTS v2 - prima esecuzione: download ~1.8GB)",
        "opt_lipsync":        "💋 Lip Sync (Wav2Lip - prima esecuzione: download ~416MB)",
        "label_engine":       "Motore traduzione:",
        "engine_google":      "Google (default)",
        "engine_deepl":       "DeepL Free",
        "engine_marian":      "MarianMT (locale)",
        "engine_ollama":      "LLM Ollama (locale, consigliato - traduzioni concise per doppiaggio)",
        "label_deepl_key":    "API key DeepL:",
        "label_ollama_model": "Modello:",
        "label_ollama_url":   "URL Ollama:",
        "hint_ollama":        (
            "Default: qwen3:8b (raccomandato) - qwen3:4b leggero (~3 GB), "
            "qwen3:14b qualità superiore (~9 GB), qwen2.5:7b-instruct retrocompat. "
            "Richiede Ollama installato"
        ),
        "opt_ollama_thinking":  "🧠 Modalità thinking (più lento, traduzioni migliori)",
        "hint_ollama_thinking": "Delibera passo-passo, ~10x più lento ma riduce errori idiomi e grammatica",
        "msg_ollama_unavailable": (
            "Ollama non disponibile. Per installare:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n\n"
            "Poi scaricare il modello:\n"
            "  ollama pull {model}\n\n"
            "Verrà usato MarianMT/Google come fallback."
        ),
        "opt_diarization":    "👥 Diarization multi-speaker (pyannote)",
        "label_hf_token":     "HF token:",
        "hint_hf_token":      "Token HF gratuito: huggingface.co/settings/tokens",
        "label_hotwords":     "Hotwords:",
        "hint_hotwords":      "Termini tecnici/brand separati da virgola (es. Strix, pipx, Docker). Riduce errori Whisper su parole rare ~43%",
        "msg_xtts_no_lang":   "XTTS v2 non supporta '{lang}'. Verrà usato Edge-TTS.",
        "msg_no_video":       "Aggiungi almeno un video.",
        "msg_completed":      "Traduzione completata!",
        "msg_error":          "Qualcosa è andato storto. Controlla il log.",
        "msg_translation_unavailable": "Traduzione non riuscita: Google Translate, usato come motore o come ripiego, ha bloccato le richieste (limite raggiunto). Riprova più tardi oppure usa MarianMT, DeepL o Ollama, verificando che siano configurati correttamente.",
        "msg_translation_partial": "Segmenti non tradotti dal motore scelto: {n}. Sono rimasti nella lingua originale o hanno una traduzione di ripiego. Controlla il log o rivedili nell'editor sottotitoli.",
        "msg_confirm_stop":   "Elaborazione in corso. Interrompere?",
        "msg_confirm":        "Conferma",
        "msg_completed_t":    "Completato",
        "msg_error_t":        "Errore",
        "msg_deps_missing":   "Dipendenze mancanti",
        "msg_deps_python":    "Pacchetti Python mancanti:\n  • ",
        "msg_deps_bins":      "Programmi mancanti:\n  • ",
        "msg_deps_ffmpeg":    "\n\nffmpeg non trovato. Installalo per continuare.",
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
        "editor_seg_label":   "Segmento {} -",
        "editor_btn_save":    "Salva",
        "editor_filter_show_flagged_only": "Mostra solo segmenti da rivedere",
        "editor_flag_summary": "Segmenti: {total}  ·  Da rivedere: {flagged} (lunghezza: {length}, trascrizione: {whisper}, fallback: {fallback})",
        "editor_tooltip_length_unfit":         "Traduzione lunga: l'audio sarà accelerato - accorcia",
        "editor_tooltip_whisper_suspicious":   "Trascrizione sospetta: token isolati o ripetizioni",
        "editor_tooltip_translation_fallback": "Traduzione fallback: l'engine principale ha fallito",
        "warn_editor":        "Editor",
        "label_url":          "URL:",
        "btn_download":       "⬇  Scarica e Traduci",
        "url_placeholder":    "Incolla link YouTube (o altro sito supportato da yt-dlp)...",
        "msg_no_url":         "Incolla almeno un URL valido.",
        "msg_downloading":    "⏳ Download in corso...",
        "log_downloading":    "Download: {}",
        "log_dl_done":        "Download completato → {}",
        "log_dl_error":       "Errore download: {}",
        "label_log_panel":    "Log:",
        "btn_log_show":       "▼ Mostra log",
        "btn_log_hide":       "▲ Nascondi log",
        "btn_log_copy":       "Copia",
        "btn_log_save":       "Salva...",
        "btn_log_clear":      "Pulisci",
        "btn_preflight":      "Diagnostica",
        "msg_preflight_title": "Diagnostica",
        "msg_preflight_ok":    "Diagnostica completata. Report nel log.",
        "msg_preflight_failed": "Diagnostica completata con problemi richiesti. Controlla il log.",
        # Settings window (appearance)
        "settings_title":      "Impostazioni",
        "settings_appearance": "Aspetto",
        "settings_theme":      "Tema",
        "settings_accent":     "Colore d'accento",
        "settings_text_size":  "Dimensione testo",
        "settings_language":   "Lingua dell'interfaccia",
        "theme_auto":          "Automatico (sistema)",
        "theme_light":         "Chiaro",
        "accent_default":      "Predefinito",
        "size_small":          "Piccolo",
        "size_normal":         "Normale",
        "size_large":          "Grande",
        "size_xlarge":         "Molto grande",
        "btn_close":           "Chiudi",
        "btn_reset":           "Ripristina predefiniti",
    },
    "en": {
        "label_video":        "Video:",
        "label_output":       "Output:",
        "label_output_dir": "Output folder:",
        "label_from":         "From:",
        "label_to":           "To:",
        "label_voice":        "Voice:",
        "label_tts_rate":     "TTS Speed:",
        "panel_input": "Input",
        "panel_translation": "Translation",
        "panel_profile": "Workflow profile",
        "panel_start": "Start",
        "section_audio": "Audio",
        "section_voice_cloning": "Voice Cloning",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Diarization",
        "section_model": "Model",
        "section_engine": "Translation engine",
        "section_subtitles": "Subtitles",
        "section_hotwords": "Hotwords",
        "label_model_hint":   "← fast / accurate → (turbo: large-v3 quality, ~6-8× faster on GPU)",
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
        "opt_xtts":           "🎙 Voice Cloning (Coqui XTTS v2 - first run: downloads ~1.8GB)",
        "opt_lipsync":        "💋 Lip Sync (Wav2Lip - first run: downloads ~416MB)",
        "label_engine":       "Translation engine:",
        "engine_google":      "Google (default)",
        "engine_deepl":       "DeepL Free",
        "engine_marian":      "MarianMT (local)",
        "engine_ollama":      "LLM Ollama (local, recommended - concise translations for dubbing)",
        "label_deepl_key":    "DeepL API key:",
        "label_ollama_model": "Model:",
        "label_ollama_url":   "Ollama URL:",
        "hint_ollama":        (
            "Default: qwen3:8b (recommended) - qwen3:4b lightweight (~3 GB), "
            "qwen3:14b higher quality (~9 GB), qwen2.5:7b-instruct legacy. "
            "Requires Ollama installed"
        ),
        "opt_ollama_thinking":  "🧠 Thinking mode (slower, better translations)",
        "hint_ollama_thinking": "Deliberates step-by-step, ~10x slower but reduces idiom/grammar errors",
        "msg_ollama_unavailable": (
            "Ollama not available. To install:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n\n"
            "Then pull the model:\n"
            "  ollama pull {model}\n\n"
            "Falling back to MarianMT/Google."
        ),
        "opt_diarization":    "👥 Multi-speaker diarization (pyannote)",
        "label_hf_token":     "HF token:",
        "hint_hf_token":      "Free HF token: huggingface.co/settings/tokens",
        "label_hotwords":     "Hotwords:",
        "hint_hotwords":      "Comma-separated technical terms/brand names (e.g. Strix, pipx, Docker). Reduces Whisper errors on rare words ~43%",
        "msg_xtts_no_lang":   "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video":       "Add at least one video.",
        "msg_completed":      "Translation completed!",
        "msg_error":          "Something went wrong. Check the log.",
        "msg_translation_unavailable": "Translation failed: Google Translate, used as the engine or as a fallback, blocked the requests (rate limit reached). Try again later or use MarianMT, DeepL or Ollama, making sure they are configured correctly.",
        "msg_translation_partial": "Segments not translated by the chosen engine: {n}. They stayed in the original language or have a fallback translation. Check the log or review them in the subtitle editor.",
        "msg_confirm_stop":   "Processing in progress. Stop?",
        "msg_confirm":        "Confirm",
        "msg_completed_t":    "Completed",
        "msg_error_t":        "Error",
        "msg_deps_missing":   "Missing dependencies",
        "msg_deps_python":    "Missing Python packages:\n  • ",
        "msg_deps_bins":      "Missing programs:\n  • ",
        "msg_deps_ffmpeg":    "\n\nffmpeg not found. Please install it to continue.",
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
        "editor_seg_label":   "Segment {} -",
        "editor_btn_save":    "Save",
        "editor_filter_show_flagged_only": "Show only segments to review",
        "editor_flag_summary": "Segments: {total}  ·  To review: {flagged} (length: {length}, transcript: {whisper}, fallback: {fallback})",
        "editor_tooltip_length_unfit":         "Translation too long: audio will be sped up - shorten",
        "editor_tooltip_whisper_suspicious":   "Suspicious transcript: isolated tokens or repetitions",
        "editor_tooltip_translation_fallback": "Fallback translation: the primary engine failed",
        "warn_editor":        "Editor",
        "label_url":          "URL:",
        "btn_download":       "⬇  Download & Translate",
        "url_placeholder":    "Paste YouTube link (or other yt-dlp supported site)...",
        "msg_no_url":         "Paste at least one valid URL.",
        "msg_downloading":    "⏳ Downloading...",
        "log_downloading":    "Downloading: {}",
        "log_dl_done":        "Download complete → {}",
        "log_dl_error":       "Download error: {}",
        "label_log_panel":    "Log:",
        "btn_log_show":       "▼ Show log",
        "btn_log_hide":       "▲ Hide log",
        "btn_log_copy":       "Copy",
        "btn_log_save":       "Save...",
        "btn_log_clear":      "Clear",
        "btn_preflight":      "Diagnostics",
        "msg_preflight_title": "Diagnostics",
        "msg_preflight_ok":    "Diagnostics complete. Report written to the log.",
        "msg_preflight_failed": "Diagnostics found required issues. Check the log.",
        # Settings window (appearance)
        "settings_title":      "Settings",
        "settings_appearance": "Appearance",
        "settings_theme":      "Theme",
        "settings_accent":     "Accent colour",
        "settings_text_size":  "Text size",
        "settings_language":   "Interface language",
        "theme_auto":          "Automatic (system)",
        "theme_light":         "Light",
        "accent_default":      "Default",
        "size_small":          "Small",
        "size_normal":         "Normal",
        "size_large":          "Large",
        "size_xlarge":         "Extra large",
        "btn_close":           "Close",
        "btn_reset":           "Reset to defaults",
    },
    "ar": {
        "label_video": "فيديو:",
        "label_output": "الإخراج:",
        "label_output_dir": "مجلد الإخراج:",
        "label_from": "من:",
        "label_to": "ل:",
        "label_voice": "صوت:",
        "label_tts_rate": "سرعة تحويل النص إلى كلام:",
        "panel_input": "الإدخال",
        "panel_translation": "ترجمة",
        "panel_profile": "وضع العمل",
        "panel_start": "البدء",
        "section_audio": "الصوت",
        "section_voice_cloning": "استنساخ الصوت",
        "section_lip_sync": "مزامنة الشفاه",
        "section_diarization": "تمييز المتحدثين",
        "section_model": "نموذج",
        "section_engine": "محرك الترجمة",
        "section_subtitles": "الترجمة النصية",
        "section_hotwords": "كلمات مفتاحية",
        "label_model_hint": "← سريع / دقيق → (turbo: جودة large-v3، أسرع بـ 6-8× على GPU)",
        "label_ui_lang": "لغة واجهة المستخدم:",
        "btn_add": "+ أضف",
        "btn_remove": "- يزيل",
        "btn_clear": "✗ واضح",
        "btn_browse": "تصفح…",
        "btn_start": "◀ ابدأ الترجمة",
        "btn_processing": "⏳ المعالجة...",
        "btn_transcribing": "⏳ النسخ...",
        "btn_dubbing": "⏳ الدوبلاج...",
        "btn_installing": "⏳ التثبيت...",
        "opt_subs_only": "الترجمة فقط .srt (لا يوجد دبلجة)",
        "opt_no_subs": "لا ترجمات",
        "opt_no_demucs": "تخطي فصل الصوت/الموسيقى (Demucs)",
        "opt_edit_subs": "إظهار محرر الترجمة قبل الدبلجة",
        "opt_xtts": "استنساخ الصوت (Coqui XTTS v2 - التشغيل الأول: التنزيلات ~1.8 جيجابايت)",
        "opt_lipsync": "مزامنة الشفاه (Wav2Lip - التشغيل الأول: التنزيل ~416MB)",
        "label_engine": "محرك الترجمة:",
        "engine_google": "Google (افتراضي)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (محلي)",
        "label_deepl_key": "مفتاح API لـ DeepL:",
        "opt_diarization": "تمييز المتحدثين (pyannote)",
        "label_hf_token": "رمز HF:",
        "hint_hf_token": "رمز HF مجاني: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "مصطلحات تقنية/أسماء علامات تجارية مفصولة بفواصل (مثل Strix, pipx, Docker). يقلل أخطاء Whisper في الكلمات النادرة بنسبة ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "أضف مقطع فيديو واحدًا على الأقل.",
        "msg_completed": "اكتملت الترجمة!",
        "msg_error": "حدث خطأ ما. تحقق من السجل.",
        "msg_translation_unavailable": "فشلت الترجمة: حظر Google Translate، المستخدم كمحرك أو كبديل احتياطي، الطلبات (تم بلوغ الحد الأقصى). أعد المحاولة لاحقًا أو استخدم MarianMT أو DeepL أو Ollama مع التأكد من إعدادها بشكل صحيح.",
        "msg_translation_partial": "المقاطع التي لم يترجمها المحرك المختار: {n}. بقيت باللغة الأصلية أو لها ترجمة احتياطية. تحقق من السجل أو راجعها في محرر الترجمة.",
        "msg_confirm_stop": "المعالجة قيد التقدم. قف؟",
        "msg_confirm": "يتأكد",
        "msg_completed_t": "مكتمل",
        "msg_error_t": "خطأ",
        "msg_deps_missing": "التبعيات المفقودة",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nلم يتم العثور على ffmpeg. يرجى تثبيته للمتابعة.",
        "msg_deps_install": "هل تريد التثبيت تلقائيًا؟",
        "msg_installed": "تم تثبيت الحزم.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "لم يتم نسخ أي مقاطع.",
        "editor_title": "محرر الترجمة",
        "editor_hint": "قم بمراجعة الترجمة وتصحيحها قبل الدبلجة",
        "editor_col_num": "#",
        "editor_col_start": "يبدأ",
        "editor_col_end": "نهاية",
        "editor_col_orig": "إبداعي",
        "editor_col_trans": "ترجمة",
        "editor_btn_confirm": "✓ التأكيد وبدء الدبلجة",
        "editor_btn_cancel": "✗ إلغاء",
        "editor_edit_title": "يحرر",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "يحفظ",
        "editor_filter_show_flagged_only": "إظهار الأجزاء التي تحتاج للمراجعة فقط",
        "editor_flag_summary": "الأجزاء: {total}  ·  للمراجعة: {flagged} (الطول: {length}، النص: {whisper}، الاحتياطي: {fallback})",
        "editor_tooltip_length_unfit": "الترجمة طويلة: الصوت سيُسرَّع - اختصر",
        "editor_tooltip_whisper_suspicious": "نص مشبوه: رموز منفصلة أو تكرارات",
        "editor_tooltip_translation_fallback": "ترجمة احتياطية: فشل المحرك الرئيسي",
        "warn_editor": "محرر",
        "label_url": "URL:",
        "btn_download": "⬇ تنزيل وترجمة",
        "url_placeholder": "الصق رابط YouTube (أو أي موقع آخر يدعم yt-dlp)...",
        "msg_no_url": "الصق عنوان URL صالحًا واحدًا على الأقل.",
        "msg_downloading": "⏳ جاري التحميل...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (محلي، موصى به - ترجمات موجزة للدبلجة)",
        "label_ollama_model": "النموذج:",
        "label_ollama_url": "عنوان Ollama:",
        "hint_ollama": "افتراضي: qwen3:8b (موصى به) - qwen3:4b خفيف (~3 جيجابايت)، qwen3:14b جودة أعلى (~9 جيجابايت)، qwen2.5:7b-instruct قديم. يتطلب تثبيت Ollama",
        "opt_ollama_thinking":  "🧠 وضع التفكير (أبطأ، ترجمات أفضل)",
        "hint_ollama_thinking": "يتداول خطوة بخطوة، ~10x أبطأ ولكن يقلل من أخطاء التعابير والقواعد",
        "msg_ollama_unavailable": (
            "Ollama غير متاح. للتثبيت:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "ثم قم بسحب النموذج:\n"
            "  ollama pull {model}\n"
            "\n"
            "سيتم استخدام MarianMT/Google كبديل."
        ),
        "label_log_panel": "السجل:",
        "btn_log_show": "▼ إظهار السجل",
        "btn_log_hide": "▲ إخفاء السجل",
        "btn_log_copy": "نسخ",
        "btn_log_save": "حفظ...",
        "btn_log_clear": "مسح",
        "btn_preflight": "التشخيص",
        "msg_preflight_title": "التشخيص",
        "msg_preflight_ok": "اكتمل التشخيص. التقرير في السجل.",
        "msg_preflight_failed": "اكتمل التشخيص مع مشكلات تتطلب المعالجة. تحقق من السجل.",
        "settings_title": "الإعدادات",
        "settings_appearance": "المظهر",
        "settings_theme": "السمة",
        "settings_accent": "لون التمييز",
        "settings_text_size": "حجم النص",
        "settings_language": "لغة الواجهة",
        "theme_auto": "تلقائي (النظام)",
        "theme_light": "فاتح",
        "accent_default": "افتراضي",
        "size_small": "صغير",
        "size_normal": "عادي",
        "size_large": "كبير",
        "size_xlarge": "كبير جدًا",
        "btn_close": "إغلاق",
        "btn_reset": "استعادة الإعدادات الافتراضية",
    },
    "zh": {
        "label_video": "视频：",
        "label_output": "输出：",
        "label_output_dir": "输出文件夹：",
        "label_from": "从：",
        "label_to": "到：",
        "label_voice": "嗓音：",
        "label_tts_rate": "TTS 速度：",
        "panel_input": "输入",
        "panel_translation": "翻译",
        "panel_profile": "工作流程配置",
        "panel_start": "开始",
        "section_audio": "音频",
        "section_voice_cloning": "语音克隆",
        "section_lip_sync": "唇形同步",
        "section_diarization": "多说话人分离",
        "section_model": "模型",
        "section_engine": "翻译引擎",
        "section_subtitles": "字幕",
        "section_hotwords": "关键词",
        "label_model_hint": "← 快速/准确 → (turbo：large-v3 质量，GPU 上快约 6-8 倍)",
        "label_ui_lang": "用户界面语言：",
        "btn_add": "+ 添加",
        "btn_remove": "- 消除",
        "btn_clear": "✗ 清除",
        "btn_browse": "浏览…",
        "btn_start": "▶ 开始翻译",
        "btn_processing": "⏳ 处理中...",
        "btn_transcribing": "⏳ 正在抄写...",
        "btn_dubbing": "⏳ 配音...",
        "btn_installing": "⏳ 正在安装...",
        "opt_subs_only": "仅字幕 .srt（无配音）",
        "opt_no_subs": "无字幕",
        "opt_no_demucs": "跳过语音/音乐分离 (Demucs)",
        "opt_edit_subs": "配音前显示字幕编辑器",
        "opt_xtts": "语音克隆（Coqui XTTS v2 - 首次运行：下载量约 1.8GB）",
        "opt_lipsync": "唇形同步 (Wav2Lip - 首次运行：下载约 416MB)",
        "label_engine": "翻译引擎：",
        "engine_google": "Google（默认）",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT（本地）",
        "label_deepl_key": "DeepL API 密钥：",
        "opt_diarization": "多说话人分离 (pyannote)",
        "label_hf_token": "HF 令牌：",
        "hint_hf_token": "免费 HF 令牌：huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "以逗号分隔的技术术语/品牌名称(例如 Strix, pipx, Docker)。可将 Whisper 在罕见词汇上的错误降低约 43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "添加至少一个视频。",
        "msg_completed": "翻译完成！",
        "msg_error": "出了点问题。检查日志。",
        "msg_translation_unavailable": "翻译失败：作为翻译引擎或备用引擎的 Google Translate 拒绝了请求（已达到频率限制）。请稍后重试，或改用 MarianMT、DeepL 或 Ollama，并确认其配置正确。",
        "msg_translation_partial": "所选引擎未翻译的片段数：{n}。这些片段仍为原始语言或使用了备用翻译。请查看日志或在字幕编辑器中检查。",
        "msg_confirm_stop": "处理中。停止？",
        "msg_confirm": "确认",
        "msg_completed_t": "完全的",
        "msg_error_t": "错误",
        "msg_deps_missing": "缺少依赖项",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\n未找到 ffmpeg。请安装后继续。",
        "msg_deps_install": "自动安装？",
        "msg_installed": "已安装软件包。",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "没有转录片段。",
        "editor_title": "字幕编辑器",
        "editor_hint": "配音前检查并修正字幕",
        "editor_col_num": "#",
        "editor_col_start": "开始",
        "editor_col_end": "结尾",
        "editor_col_orig": "原来的",
        "editor_col_trans": "翻译",
        "editor_btn_confirm": "✓ 确认并开始配音",
        "editor_btn_cancel": "✗ 取消",
        "editor_edit_title": "编辑",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "节省",
        "editor_filter_show_flagged_only": "仅显示需复查的片段",
        "editor_flag_summary": "片段: {total}  ·  待复查: {flagged} (长度: {length}, 转录: {whisper}, 回退: {fallback})",
        "editor_tooltip_length_unfit": "译文过长: 音频将被加速 - 请缩短",
        "editor_tooltip_whisper_suspicious": "可疑转录: 孤立标记或重复",
        "editor_tooltip_translation_fallback": "回退翻译: 主翻译引擎失败",
        "warn_editor": "编辑",
        "label_url": "URL:",
        "btn_download": "⬇ 下载和翻译",
        "url_placeholder": "粘贴 YouTube 链接（或其他 yt-dlp 支持的网站）...",
        "msg_no_url": "粘贴至少一个有效的 URL。",
        "msg_downloading": "⏳ 正在下载...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM(本地,推荐 - 简洁的配音翻译)",
        "label_ollama_model": "模型:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "默认: qwen3:8b(推荐) - qwen3:4b 轻量级(~3 GB), qwen3:14b 更高质量(~9 GB), qwen2.5:7b-instruct 旧版本。需要安装 Ollama",
        "opt_ollama_thinking":  "🧠 思考模式 (更慢，翻译更好)",
        "hint_ollama_thinking": "逐步推敲，慢约10倍，但能减少习语和语法错误",
        "msg_ollama_unavailable": (
            "Ollama 不可用。安装方法:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "然后拉取模型:\n"
            "  ollama pull {model}\n"
            "\n"
            "将回退到 MarianMT/Google。"
        ),
        "label_log_panel": "日志:",
        "btn_log_show": "▼ 显示日志",
        "btn_log_hide": "▲ 隐藏日志",
        "btn_log_copy": "复制",
        "btn_log_save": "保存...",
        "btn_log_clear": "清除",
        "btn_preflight": "诊断",
        "msg_preflight_title": "诊断",
        "msg_preflight_ok": "诊断完成。报告见日志。",
        "msg_preflight_failed": "诊断发现需要处理的问题。检查日志。",
        "settings_title": "设置",
        "settings_appearance": "外观",
        "settings_theme": "主题",
        "settings_accent": "强调色",
        "settings_text_size": "文字大小",
        "settings_language": "界面语言",
        "theme_auto": "自动（跟随系统）",
        "theme_light": "浅色",
        "accent_default": "默认",
        "size_small": "小",
        "size_normal": "正常",
        "size_large": "大",
        "size_xlarge": "特大",
        "btn_close": "关闭",
        "btn_reset": "恢复默认设置",
    },
    "cs": {
        "label_video": "Video:",
        "label_output": "výstup:",
        "label_output_dir": "Výstupní složka:",
        "label_from": "Z:",
        "label_to": "Na:",
        "label_voice": "Hlas:",
        "label_tts_rate": "Rychlost TTS:",
        "panel_input": "Vstup",
        "panel_translation": "Překlad",
        "panel_profile": "Pracovní profil",
        "panel_start": "Start",
        "section_audio": "Zvuk",
        "section_voice_cloning": "Hlasové klonování",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Rozpoznávání mluvčích",
        "section_model": "Model",
        "section_engine": "Překladač",
        "section_subtitles": "Titulky",
        "section_hotwords": "Klíčová slova",
        "label_model_hint": "← rychlé / přesné → (turbo: kvalita large-v3, ~6-8× rychlejší na GPU)",
        "label_ui_lang": "Jazyk uživatelského rozhraní:",
        "btn_add": "+ Přidat",
        "btn_remove": "- Odstraňte",
        "btn_clear": "✗ Jasné",
        "btn_browse": "Prohlížet…",
        "btn_start": "▶ Spusťte překlad",
        "btn_processing": "⏳ Zpracovává se...",
        "btn_transcribing": "⏳ Přepis...",
        "btn_dubbing": "⏳ Dabing...",
        "btn_installing": "⏳ Instalace...",
        "opt_subs_only": "Pouze titulky .srt (bez dabingu)",
        "opt_no_subs": "Žádné titulky",
        "opt_no_demucs": "Přeskočit oddělení hlasu a hudby (Demucs)",
        "opt_edit_subs": "Před dabováním zobrazit editor titulků",
        "opt_xtts": "Hlasové klonování (Coqui XTTS v2 - první spuštění: stažení ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip - první spuštění: stažení ~416MB)",
        "label_engine": "Překladač:",
        "engine_google": "Google (výchozí)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokální)",
        "label_deepl_key": "API klíč DeepL:",
        "opt_diarization": "Rozpoznávání mluvčích (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Bezplatný HF token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Technické termíny/značky oddělené čárkou (např. Strix, pipx, Docker). Snižuje chyby Whisperu u vzácných slov o ~43 %",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Přidejte alespoň jedno video.",
        "msg_completed": "Překlad dokončen!",
        "msg_error": "Něco se pokazilo. Zkontrolujte protokol.",
        "msg_translation_unavailable": "Překlad se nezdařil: Google Translate, použitý jako překladač nebo jako záložní řešení, zablokoval požadavky (dosažen limit). Zkuste to později nebo použijte MarianMT, DeepL či Ollama a ověřte, že jsou správně nastavené.",
        "msg_translation_partial": "Počet segmentů, které zvolený překladač nepřeložil: {n}. Zůstaly v původním jazyce nebo mají záložní překlad. Zkontrolujte log nebo je projděte v editoru titulků.",
        "msg_confirm_stop": "Probíhá zpracování. Zastávka?",
        "msg_confirm": "Potvrdit",
        "msg_completed_t": "Dokončeno",
        "msg_error_t": "Chyba",
        "msg_deps_missing": "Chybějící závislosti",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg nebyl nalezen. Nainstalujte jej prosím.",
        "msg_deps_install": "Instalovat automaticky?",
        "msg_installed": "Nainstalované balíčky.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Nebyly přepsány žádné segmenty.",
        "editor_title": "Editor titulků",
        "editor_hint": "Před dabováním zkontrolujte a opravte titulky",
        "editor_col_num": "#",
        "editor_col_start": "Start",
        "editor_col_end": "Konec",
        "editor_col_orig": "Originál",
        "editor_col_trans": "Překlad",
        "editor_btn_confirm": "✓ Potvrďte a spusťte kopírování",
        "editor_btn_cancel": "✗ Zrušit",
        "editor_edit_title": "Upravit",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Uložit",
        "editor_filter_show_flagged_only": "Zobrazit pouze segmenty ke kontrole",
        "editor_flag_summary": "Segmenty: {total}  ·  Ke kontrole: {flagged} (délka: {length}, přepis: {whisper}, záloha: {fallback})",
        "editor_tooltip_length_unfit": "Překlad příliš dlouhý: zvuk bude zrychlen - zkraťte",
        "editor_tooltip_whisper_suspicious": "Podezřelý přepis: izolované tokeny nebo opakování",
        "editor_tooltip_translation_fallback": "Záložní překlad: hlavní engine selhal",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Stáhnout a přeložit",
        "url_placeholder": "Vložte odkaz na YouTube (nebo jiný web podporovaný yt-dlp)...",
        "msg_no_url": "Vložte alespoň jednu platnou adresu URL.",
        "msg_downloading": "⏳ Stahování...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokální, doporučeno - stručné překlady pro dabing)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Výchozí: qwen3:8b (doporučeno) - qwen3:4b odlehčený (~3 GB), qwen3:14b vyšší kvalita (~9 GB), qwen2.5:7b-instruct starší. Vyžaduje nainstalovaný Ollama",
        "opt_ollama_thinking":  "🧠 Režim přemýšlení (pomalejší, lepší překlady)",
        "hint_ollama_thinking": "Zvažuje krok za krokem, ~10x pomalejší, ale snižuje chyby v idiomech a gramatice",
        "msg_ollama_unavailable": (
            "Ollama není k dispozici. Pro instalaci:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Poté stáhněte model:\n"
            "  ollama pull {model}\n"
            "\n"
            "Bude použit MarianMT/Google jako záloha."
        ),
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Zobrazit log",
        "btn_log_hide": "▲ Skrýt log",
        "btn_log_copy": "Kopírovat",
        "btn_log_save": "Uložit...",
        "btn_log_clear": "Vymazat",
        "btn_preflight": "Diagnostika",
        "msg_preflight_title": "Diagnostika",
        "msg_preflight_ok": "Diagnostika dokončena. Zpráva v protokolu.",
        "msg_preflight_failed": "Diagnostika nalezla vyžadované problémy. Zkontrolujte protokol.",
        "settings_title": "Nastavení",
        "settings_appearance": "Vzhled",
        "settings_theme": "Téma",
        "settings_accent": "Barva zvýraznění",
        "settings_text_size": "Velikost textu",
        "settings_language": "Jazyk rozhraní",
        "theme_auto": "Automaticky (systém)",
        "theme_light": "Světlé",
        "accent_default": "Výchozí",
        "size_small": "Malé",
        "size_normal": "Normální",
        "size_large": "Velké",
        "size_xlarge": "Velmi velké",
        "btn_close": "Zavřít",
        "btn_reset": "Obnovit výchozí nastavení",
    },
    "da": {
        "label_video": "Video:",
        "label_output": "Produktion:",
        "label_output_dir": "Outputmappe:",
        "label_from": "Fra:",
        "label_to": "Til:",
        "label_voice": "Stemme:",
        "label_tts_rate": "TTS hastighed:",
        "panel_input": "Input",
        "panel_translation": "Oversættelse",
        "panel_profile": "Arbejdsprofil",
        "panel_start": "Start",
        "section_audio": "Lyd",
        "section_voice_cloning": "Stemmekloning",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Taleridentifikation",
        "section_model": "Model",
        "section_engine": "Oversættelsesmotor",
        "section_subtitles": "Undertekster",
        "section_hotwords": "Nøgleord",
        "label_model_hint": "← hurtig / præcis → (turbo: large-v3 kvalitet, ~6-8× hurtigere på GPU)",
        "label_ui_lang": "UI sprog:",
        "btn_add": "+ Tilføj",
        "btn_remove": "- Fjern",
        "btn_clear": "✗ Ryd",
        "btn_browse": "Gennemse...",
        "btn_start": "▶ Start oversættelse",
        "btn_processing": "⏳ Behandler...",
        "btn_transcribing": "⏳ Transskriberer...",
        "btn_dubbing": "⏳ Dubbing...",
        "btn_installing": "⏳ Installerer...",
        "opt_subs_only": "Kun undertekster .srt (ingen dubbing)",
        "opt_no_subs": "Ingen undertekster",
        "opt_no_demucs": "Spring stemme-/musikadskillelse over (demucs)",
        "opt_edit_subs": "Vis underteksteditor før dubbing",
        "opt_xtts": "Stemmekloning (Coqui XTTS v2 - første kørsel: downloads ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip - første kørsel: download ~416MB)",
        "label_engine": "Oversættelsesmotor:",
        "engine_google": "Google (standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-nøgle:",
        "opt_diarization": "Højttalerseparation (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Gratis HF token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Kommaseparerede tekniske termer/mærker (f.eks. Strix, pipx, Docker). Reducerer Whisper-fejl på sjældne ord med ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Tilføj mindst én video.",
        "msg_completed": "Oversættelse afsluttet!",
        "msg_error": "Noget gik galt. Tjek loggen.",
        "msg_translation_unavailable": "Oversættelsen mislykkedes: Google Translate, brugt som motor eller som reserve, blokerede forespørgslerne (grænsen er nået). Prøv igen senere, eller brug MarianMT, DeepL eller Ollama, og kontrollér, at de er konfigureret korrekt.",
        "msg_translation_partial": "Segmenter, der ikke blev oversat af den valgte motor: {n}. De er forblevet på originalsproget eller har en reserveoversættelse. Tjek loggen, eller gennemgå dem i undertekst-editoren.",
        "msg_confirm_stop": "Behandling i gang. Stop?",
        "msg_confirm": "Bekræfte",
        "msg_completed_t": "Afsluttet",
        "msg_error_t": "Fejl",
        "msg_deps_missing": "Manglende afhængigheder",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg blev ikke fundet. Installer det venligst.",
        "msg_deps_install": "Installer automatisk?",
        "msg_installed": "Pakker installeret.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Ingen segmenter transskriberet.",
        "editor_title": "Underteksteditor",
        "editor_hint": "Gennemgå og ret undertekster før dubbing",
        "editor_col_num": "#",
        "editor_col_start": "Starte",
        "editor_col_end": "Ende",
        "editor_col_orig": "Original",
        "editor_col_trans": "Oversættelse",
        "editor_btn_confirm": "✓ Bekræft og start dubbing",
        "editor_btn_cancel": "✗ Annuller",
        "editor_edit_title": "Redigere",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Spare",
        "editor_filter_show_flagged_only": "Vis kun segmenter til gennemgang",
        "editor_flag_summary": "Segmenter: {total}  ·  Til gennemgang: {flagged} (længde: {length}, transskription: {whisper}, reserve: {fallback})",
        "editor_tooltip_length_unfit": "Oversættelsen er for lang: lyden vil blive fremskyndet - forkort",
        "editor_tooltip_whisper_suspicious": "Mistænkelig transskription: isolerede tegn eller gentagelser",
        "editor_tooltip_translation_fallback": "Reserveoversættelse: hovedmotoren fejlede",
        "warn_editor": "Redaktør",
        "label_url": "URL:",
        "btn_download": "⬇ Download og oversæt",
        "url_placeholder": "Indsæt YouTube-link (eller et andet yt-dlp-understøttet websted)...",
        "msg_no_url": "Indsæt mindst én gyldig webadresse.",
        "msg_downloading": "⏳ Downloader...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, anbefalet - koncise oversættelser til dubbing)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Standard: qwen3:8b (anbefalet) - qwen3:4b let (~3 GB), qwen3:14b højere kvalitet (~9 GB), qwen2.5:7b-instruct ældre. Kræver Ollama installeret",
        "opt_ollama_thinking":  "🧠 Tænketilstand (langsommere, bedre oversættelser)",
        "hint_ollama_thinking": "Overvejer trin for trin, ~10x langsommere, men reducerer idiom-/grammatikfejl",
        "msg_ollama_unavailable": (
            "Ollama ikke tilgængelig. For at installere:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Hent derefter modellen:\n"
            "  ollama pull {model}\n"
            "\n"
            "MarianMT/Google bruges som fallback."
        ),
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Vis log",
        "btn_log_hide": "▲ Skjul log",
        "btn_log_copy": "Kopier",
        "btn_log_save": "Gem...",
        "btn_log_clear": "Ryd",
        "btn_preflight": "Diagnostik",
        "msg_preflight_title": "Diagnostik",
        "msg_preflight_ok": "Diagnostik afsluttet. Rapport i loggen.",
        "msg_preflight_failed": "Diagnostikken fandt nødvendige problemer. Tjek loggen.",
        "settings_title": "Indstillinger",
        "settings_appearance": "Udseende",
        "settings_theme": "Tema",
        "settings_accent": "Accentfarve",
        "settings_text_size": "Tekststørrelse",
        "settings_language": "Grænsefladesprog",
        "theme_auto": "Automatisk (system)",
        "theme_light": "Lyst",
        "accent_default": "Standard",
        "size_small": "Lille",
        "size_normal": "Normal",
        "size_large": "Stor",
        "size_xlarge": "Meget stor",
        "btn_close": "Luk",
        "btn_reset": "Gendan standardindstillinger",
    },
    "nl": {
        "label_video": "Video:",
        "label_output": "Uitgang:",
        "label_output_dir": "Uitvoermap:",
        "label_from": "Van:",
        "label_to": "Naar:",
        "label_voice": "Stem:",
        "label_tts_rate": "TTS-snelheid:",
        "panel_input": "Invoer",
        "panel_translation": "Vertaling",
        "panel_profile": "Werkprofiel",
        "panel_start": "Start",
        "section_audio": "Audio",
        "section_voice_cloning": "Spraakklonen",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Sprekerdiarisatie",
        "section_model": "Model",
        "section_engine": "Vertaalengine",
        "section_subtitles": "Ondertiteling",
        "section_hotwords": "Trefwoorden",
        "label_model_hint": "← snel / nauwkeurig → (turbo: large-v3 kwaliteit, ~6-8× sneller op GPU)",
        "label_ui_lang": "UI-taal:",
        "btn_add": "+ Toevoegen",
        "btn_remove": "- Verwijderen",
        "btn_clear": "✗ Duidelijk",
        "btn_browse": "Blader…",
        "btn_start": "▶ Start vertaling",
        "btn_processing": "⏳ Verwerken...",
        "btn_transcribing": "⏳ Transcriberen...",
        "btn_dubbing": "⏳ Dubben...",
        "btn_installing": "⏳ Installeren...",
        "opt_subs_only": "Alleen ondertiteling .srt (geen nasynchronisatie)",
        "opt_no_subs": "Geen ondertitels",
        "opt_no_demucs": "Stem-/muziekscheiding overslaan (Demucs)",
        "opt_edit_subs": "Toon de ondertiteleditor vóór het kopiëren",
        "opt_xtts": "Spraakklonen (Coqui XTTS v2 - eerste keer: downloads ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip - eerste keer: download ~416MB)",
        "label_engine": "Vertaalengine:",
        "engine_google": "Google (standaard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokaal)",
        "label_deepl_key": "DeepL API-sleutel:",
        "opt_diarization": "Sprekerdiarisatie (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Gratis HF token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Door komma's gescheiden technische termen/merknamen (bijv. Strix, pipx, Docker). Vermindert Whisper-fouten bij zeldzame woorden met ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Voeg ten minste één video toe.",
        "msg_completed": "Vertaling voltooid!",
        "msg_error": "Er is iets misgegaan. Controleer het logboek.",
        "msg_translation_unavailable": "Vertaling mislukt: Google Translate, gebruikt als engine of als terugvaloptie, heeft de verzoeken geblokkeerd (limiet bereikt). Probeer het later opnieuw of gebruik MarianMT, DeepL of Ollama en controleer of ze correct zijn ingesteld.",
        "msg_translation_partial": "Segmenten die de gekozen engine niet heeft vertaald: {n}. Ze staan nog in de oorspronkelijke taal of hebben een terugvalvertaling. Controleer het logboek of bekijk ze in de ondertiteleditor.",
        "msg_confirm_stop": "Bezig met verwerken. Stop?",
        "msg_confirm": "Bevestigen",
        "msg_completed_t": "Voltooid",
        "msg_error_t": "Fout",
        "msg_deps_missing": "Ontbrekende afhankelijkheden",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg niet gevonden. Installeer het alstublieft.",
        "msg_deps_install": "Automatisch installeren?",
        "msg_installed": "Pakketten geïnstalleerd.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Er zijn geen segmenten getranscribeerd.",
        "editor_title": "Ondertiteleditor",
        "editor_hint": "Controleer en corrigeer de ondertitels voordat u gaat kopiëren",
        "editor_col_num": "#",
        "editor_col_start": "Begin",
        "editor_col_end": "Einde",
        "editor_col_orig": "Origineel",
        "editor_col_trans": "Vertaling",
        "editor_btn_confirm": "✓ Bevestig en begin met kopiëren",
        "editor_btn_cancel": "✗ Annuleren",
        "editor_edit_title": "Bewerking",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Redden",
        "editor_filter_show_flagged_only": "Alleen segmenten ter controle tonen",
        "editor_flag_summary": "Segmenten: {total}  ·  Te controleren: {flagged} (lengte: {length}, transcriptie: {whisper}, fallback: {fallback})",
        "editor_tooltip_length_unfit": "Vertaling te lang: audio wordt versneld - inkorten",
        "editor_tooltip_whisper_suspicious": "Verdachte transcriptie: losse tokens of herhalingen",
        "editor_tooltip_translation_fallback": "Fallback-vertaling: de hoofdengine faalde",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Downloaden en vertalen",
        "url_placeholder": "Plak de YouTube-link (of een andere door yt-dlp ondersteunde site)...",
        "msg_no_url": "Plak minimaal één geldige URL.",
        "msg_downloading": "⏳ Downloaden...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokaal, aanbevolen - beknopte vertalingen voor nasynchronisatie)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "Ollama-URL:",
        "hint_ollama": "Standaard: qwen3:8b (aanbevolen) - qwen3:4b licht (~3 GB), qwen3:14b hogere kwaliteit (~9 GB), qwen2.5:7b-instruct legacy. Vereist Ollama geïnstalleerd",
        "opt_ollama_thinking":  "🧠 Denkmodus (langzamer, betere vertalingen)",
        "hint_ollama_thinking": "Overweegt stap voor stap, ~10x langzamer maar minder idioom- en grammaticafouten",
        "msg_ollama_unavailable": (
            "Ollama niet beschikbaar. Installeren:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Haal vervolgens het model op:\n"
            "  ollama pull {model}\n"
            "\n"
            "Terugvallen op MarianMT/Google."
        ),
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Log tonen",
        "btn_log_hide": "▲ Log verbergen",
        "btn_log_copy": "Kopiëren",
        "btn_log_save": "Opslaan...",
        "btn_log_clear": "Wissen",
        "btn_preflight": "Diagnose",
        "msg_preflight_title": "Diagnose",
        "msg_preflight_ok": "Diagnose voltooid. Rapport in het logboek.",
        "msg_preflight_failed": "Diagnose heeft problemen gevonden die aandacht vereisen. Controleer het logboek.",
        "settings_title": "Instellingen",
        "settings_appearance": "Weergave",
        "settings_theme": "Thema",
        "settings_accent": "Accentkleur",
        "settings_text_size": "Tekstgrootte",
        "settings_language": "Interfacetaal",
        "theme_auto": "Automatisch (systeem)",
        "theme_light": "Licht",
        "accent_default": "Standaard",
        "size_small": "Klein",
        "size_normal": "Normaal",
        "size_large": "Groot",
        "size_xlarge": "Zeer groot",
        "btn_close": "Sluiten",
        "btn_reset": "Standaardinstellingen herstellen",
    },
    "fi": {
        "label_video": "Video:",
        "label_output": "Lähtö:",
        "label_output_dir": "Tuloskansio:",
        "label_from": "Lähettäjä:",
        "label_to": "Vastaanottaja:",
        "label_voice": "Ääni:",
        "label_tts_rate": "TTS nopeus:",
        "panel_input": "Syöte",
        "panel_translation": "Käännös",
        "panel_profile": "Työnkulun profiili",
        "panel_start": "Aloitus",
        "section_audio": "Ääni",
        "section_voice_cloning": "Äänen kloonaus",
        "section_lip_sync": "Huulisynkka",
        "section_diarization": "Puhujan tunnistus",
        "section_model": "Malli",
        "section_engine": "Käännöskone",
        "section_subtitles": "Tekstitykset",
        "section_hotwords": "Avainsanat",
        "label_model_hint": "← nopea / tarkka → (turbo: large-v3 -laatu, ~6-8× nopeampi GPU:lla)",
        "label_ui_lang": "Käyttöliittymän kieli:",
        "btn_add": "+ Lisää",
        "btn_remove": "- Poista",
        "btn_clear": "✗ Selkeää",
        "btn_browse": "Selaa…",
        "btn_start": "▶ Aloita käännös",
        "btn_processing": "⏳ Käsitellään...",
        "btn_transcribing": "⏳ Litteroidaan...",
        "btn_dubbing": "⏳ Kopiointi...",
        "btn_installing": "⏳ Asennetaan...",
        "opt_subs_only": "Vain tekstitykset .srt (ei jälkiäänitystä)",
        "opt_no_subs": "Ei tekstityksiä",
        "opt_no_demucs": "Ohita äänen ja musiikin erottelu (Demucs)",
        "opt_edit_subs": "Näytä tekstityseditori ennen kopiointia",
        "opt_xtts": "Äänen kloonaus (Coqui XTTS v2 - ensimmäinen käyttökerta: lataukset ~1,8 Gt)",
        "opt_lipsync": "Huulisynkka (Wav2Lip - ensimmäinen ajo: lataa ~416MB)",
        "label_engine": "Käännöskone:",
        "engine_google": "Google (oletus)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (paikallinen)",
        "label_deepl_key": "DeepL API-avain:",
        "opt_diarization": "Puhujan tunnistus (pyannote)",
        "label_hf_token": "HF-tunnus:",
        "hint_hf_token": "Ilmainen HF-tunnus: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Pilkuilla erotetut tekniset termit/tuotemerkit (esim. Strix, pipx, Docker). Vähentää Whisperin virheitä harvinaisissa sanoissa ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Lisää vähintään yksi video.",
        "msg_completed": "Käännös valmis!",
        "msg_error": "Jotain meni pieleen. Tarkista loki.",
        "msg_translation_unavailable": "Käännös epäonnistui: Google Translate, jota käytettiin moottorina tai varamoottorina, esti pyynnöt (raja täynnä). Yritä myöhemmin uudelleen tai käytä MarianMT:tä, DeepL:ää tai Ollamaa ja varmista, että ne on määritetty oikein.",
        "msg_translation_partial": "Segmenttejä, joita valittu moottori ei kääntänyt: {n}. Ne jäivät alkuperäiselle kielelle tai niillä on varakäännös. Tarkista loki tai käy ne läpi tekstityseditorissa.",
        "msg_confirm_stop": "Käsittely käynnissä. Stop?",
        "msg_confirm": "Vahvistaa",
        "msg_completed_t": "Valmis",
        "msg_error_t": "Virhe",
        "msg_deps_missing": "Riippuvuudet puuttuvat",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg ei löytynyt. Asenna se jatkaaksesi.",
        "msg_deps_install": "Asennetaan automaattisesti?",
        "msg_installed": "Paketit asennettu.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Ei litteroituja osia.",
        "editor_title": "Tekstityseditori",
        "editor_hint": "Tarkista ja korjaa tekstitykset ennen kopioimista",
        "editor_col_num": "#",
        "editor_col_start": "Aloita",
        "editor_col_end": "Loppu",
        "editor_col_orig": "Alkuperäinen",
        "editor_col_trans": "Käännös",
        "editor_btn_confirm": "✓ Vahvista ja aloita kopiointi",
        "editor_btn_cancel": "✗ Peruuta",
        "editor_edit_title": "Muokata",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Tallentaa",
        "editor_filter_show_flagged_only": "Näytä vain tarkistettavat segmentit",
        "editor_flag_summary": "Segmentit: {total}  ·  Tarkistettavia: {flagged} (pituus: {length}, transkriptio: {whisper}, varakone: {fallback})",
        "editor_tooltip_length_unfit": "Käännös liian pitkä: ääntä nopeutetaan - lyhennä",
        "editor_tooltip_whisper_suspicious": "Epäilyttävä transkriptio: irrallisia tokeneita tai toistoja",
        "editor_tooltip_translation_fallback": "Varakäännös: pääkone epäonnistui",
        "warn_editor": "Toimittaja",
        "label_url": "URL:",
        "btn_download": "⬇ Lataa ja käännä",
        "url_placeholder": "Liitä YouTube-linkki (tai muu yt-dlp-tuettu sivusto)...",
        "msg_no_url": "Liitä vähintään yksi kelvollinen URL-osoite.",
        "msg_downloading": "⏳ Ladataan...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (paikallinen, suositeltu - tiiviit käännökset dubbaukseen)",
        "label_ollama_model": "Malli:",
        "label_ollama_url": "Ollaman URL:",
        "hint_ollama": "Oletus: qwen3:8b (suositeltu) - qwen3:4b kevyt (~3 GB), qwen3:14b parempi laatu (~9 GB), qwen2.5:7b-instruct vanha. Vaatii Ollaman asennuksen",
        "opt_ollama_thinking":  "🧠 Ajattelutila (hitaampi, parempia käännöksiä)",
        "hint_ollama_thinking": "Harkitsee vaiheittain, ~10x hitaampi mutta vähentää idiomi- ja kielioppivirheitä",
        "msg_ollama_unavailable": (
            "Ollama ei käytettävissä. Asennus:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Hae sitten malli:\n"
            "  ollama pull {model}\n"
            "\n"
            "Käytetään MarianMT/Google varajärjestelmänä."
        ),
        "label_log_panel": "Loki:",
        "btn_log_show": "▼ Näytä loki",
        "btn_log_hide": "▲ Piilota loki",
        "btn_log_copy": "Kopioi",
        "btn_log_save": "Tallenna...",
        "btn_log_clear": "Tyhjennä",
        "btn_preflight": "Diagnostiikka",
        "msg_preflight_title": "Diagnostiikka",
        "msg_preflight_ok": "Diagnostiikka valmis. Raportti lokissa.",
        "msg_preflight_failed": "Diagnostiikka löysi vaadittuja ongelmia. Tarkista loki.",
        "settings_title": "Asetukset",
        "settings_appearance": "Ulkoasu",
        "settings_theme": "Teema",
        "settings_accent": "Korostusväri",
        "settings_text_size": "Tekstin koko",
        "settings_language": "Käyttöliittymän kieli",
        "theme_auto": "Automaattinen (järjestelmä)",
        "theme_light": "Vaalea",
        "accent_default": "Oletus",
        "size_small": "Pieni",
        "size_normal": "Normaali",
        "size_large": "Suuri",
        "size_xlarge": "Erittäin suuri",
        "btn_close": "Sulje",
        "btn_reset": "Palauta oletusasetukset",
    },
    "fr": {
        "label_video": "Vidéo:",
        "label_output": "Sortir:",
        "label_output_dir": "Dossier de sortie:",
        "label_from": "Depuis:",
        "label_to": "À:",
        "label_voice": "Voix:",
        "label_tts_rate": "Vitesse TTS :",
        "panel_input": "Entrée",
        "panel_translation": "Traduction",
        "panel_profile": "Profil de travail",
        "panel_start": "Démarrage",
        "section_audio": "Audio",
        "section_voice_cloning": "Clonage vocal",
        "section_lip_sync": "Synchronisation labiale",
        "section_diarization": "Diarisation",
        "section_model": "Modèle",
        "section_engine": "Moteur de traduction",
        "section_subtitles": "Sous-titres",
        "section_hotwords": "Mots-clés",
        "label_model_hint": "← rapide / précis → (turbo : qualité large-v3, ~6-8× plus rapide sur GPU)",
        "label_ui_lang": "Langue de l'interface utilisateur :",
        "btn_add": "+ Ajouter",
        "btn_remove": "- Retirer",
        "btn_clear": "✗ Effacer",
        "btn_browse": "Parcourir…",
        "btn_start": "▶ Démarrer la traduction",
        "btn_processing": "⏳Traitement...",
        "btn_transcribing": "⏳ Transcription...",
        "btn_dubbing": "⏳ Doublage...",
        "btn_installing": "⏳ Installation...",
        "opt_subs_only": "Sous-titres uniquement .srt (pas de doublage)",
        "opt_no_subs": "Pas de sous-titres",
        "opt_no_demucs": "Passer la séparation voix/musique (Demucs)",
        "opt_edit_subs": "Afficher l'éditeur de sous-titres avant la copie",
        "opt_xtts": "Clonage vocal (Coqui XTTS v2 - première exécution : téléchargements ~ 1,8 Go)",
        "opt_lipsync": "Synchronisation labiale (Wav2Lip - première exécution : téléchargement ~416 Mo)",
        "label_engine": "Moteur de traduction :",
        "engine_google": "Google (par défaut)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Clé API DeepL :",
        "opt_diarization": "Diarisation multi-locuteurs (pyannote)",
        "label_hf_token": "Jeton HF :",
        "hint_hf_token": "Jeton HF gratuit : huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Termes techniques/marques séparés par des virgules (ex. Strix, pipx, Docker). Réduit les erreurs de Whisper sur les mots rares de ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Ajoutez au moins une vidéo.",
        "msg_completed": "Traduction terminée !",
        "msg_error": "Quelque chose s'est mal passé. Vérifiez le journal.",
        "msg_translation_unavailable": "Échec de la traduction : Google Translate, utilisé comme moteur ou comme solution de secours, a bloqué les requêtes (limite atteinte). Réessayez plus tard ou utilisez MarianMT, DeepL ou Ollama en vérifiant qu'ils sont correctement configurés.",
        "msg_translation_partial": "Segments non traduits par le moteur choisi : {n}. Ils sont restés dans la langue d'origine ou ont une traduction de secours. Consultez le journal ou vérifiez-les dans l'éditeur de sous-titres.",
        "msg_confirm_stop": "Traitement en cours. Arrêt?",
        "msg_confirm": "Confirmer",
        "msg_completed_t": "Complété",
        "msg_error_t": "Erreur",
        "msg_deps_missing": "Dépendances manquantes",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg introuvable. Veuillez l'installer.",
        "msg_deps_install": "Installer automatiquement ?",
        "msg_installed": "Paquets installés.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Aucun segment transcrit.",
        "editor_title": "Éditeur de sous-titres",
        "editor_hint": "Vérifiez et corrigez les sous-titres avant la copie",
        "editor_col_num": "#",
        "editor_col_start": "Commencer",
        "editor_col_end": "Fin",
        "editor_col_orig": "Original",
        "editor_col_trans": "Traduction",
        "editor_btn_confirm": "✓ Confirmez et démarrez la copie",
        "editor_btn_cancel": "✗ Annuler",
        "editor_edit_title": "Modifier",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Sauvegarder",
        "editor_filter_show_flagged_only": "Afficher uniquement les segments à revoir",
        "editor_flag_summary": "Segments : {total}  ·  À revoir : {flagged} (longueur : {length}, transcription : {whisper}, secours : {fallback})",
        "editor_tooltip_length_unfit": "Traduction trop longue : l'audio sera accéléré - raccourcissez",
        "editor_tooltip_whisper_suspicious": "Transcription suspecte : jetons isolés ou répétitions",
        "editor_tooltip_translation_fallback": "Traduction de secours : le moteur principal a échoué",
        "warn_editor": "Éditeur",
        "label_url": "URL:",
        "btn_download": "⬇ Télécharger et traduire",
        "url_placeholder": "Collez le lien YouTube (ou tout autre site pris en charge par yt-dlp)...",
        "msg_no_url": "Collez au moins une URL valide.",
        "msg_downloading": "⏳ Téléchargement...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recommandé - traductions concises pour le doublage)",
        "label_ollama_model": "Modèle :",
        "label_ollama_url": "URL Ollama :",
        "hint_ollama": "Par défaut : qwen3:8b (recommandé) - qwen3:4b léger (~3 Go), qwen3:14b qualité supérieure (~9 Go), qwen2.5:7b-instruct hérité. Nécessite Ollama installé",
        "opt_ollama_thinking":  "🧠 Mode réflexif (plus lent, meilleures traductions)",
        "hint_ollama_thinking": "Délibère étape par étape, ~10x plus lent mais réduit les erreurs d'idiomes et de grammaire",
        "msg_ollama_unavailable": (
            "Ollama indisponible. Pour installer :\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Puis récupérez le modèle :\n"
            "  ollama pull {model}\n"
            "\n"
            "Repli vers MarianMT/Google."
        ),
        "label_log_panel": "Journal :",
        "btn_log_show": "▼ Afficher le journal",
        "btn_log_hide": "▲ Masquer le journal",
        "btn_log_copy": "Copier",
        "btn_log_save": "Enregistrer...",
        "btn_log_clear": "Effacer",
        "btn_preflight": "Diagnostic",
        "msg_preflight_title": "Diagnostic",
        "msg_preflight_ok": "Diagnostic terminé. Rapport dans le journal.",
        "msg_preflight_failed": "Le diagnostic a détecté des problèmes à corriger. Vérifiez le journal.",
        "settings_title": "Paramètres",
        "settings_appearance": "Apparence",
        "settings_theme": "Thème",
        "settings_accent": "Couleur d'accent",
        "settings_text_size": "Taille du texte",
        "settings_language": "Langue de l'interface",
        "theme_auto": "Automatique (système)",
        "theme_light": "Clair",
        "accent_default": "Par défaut",
        "size_small": "Petit",
        "size_normal": "Normal",
        "size_large": "Grand",
        "size_xlarge": "Très grand",
        "btn_close": "Fermer",
        "btn_reset": "Réinitialiser les paramètres par défaut",
    },
    "de": {
        "label_video": "Video:",
        "label_output": "Ausgabe:",
        "label_output_dir": "Ausgabeordner:",
        "label_from": "Aus:",
        "label_to": "Zu:",
        "label_voice": "Stimme:",
        "label_tts_rate": "TTS-Geschwindigkeit:",
        "panel_input": "Eingabe",
        "panel_translation": "Übersetzung",
        "panel_profile": "Workflow-Profil",
        "panel_start": "Start",
        "section_audio": "Audio",
        "section_voice_cloning": "Voice Cloning",
        "section_lip_sync": "Lippensynchronisation",
        "section_diarization": "Sprechertrennung",
        "section_model": "Modell",
        "section_engine": "Übersetzungs-Engine",
        "section_subtitles": "Untertitel",
        "section_hotwords": "Schlüsselwörter",
        "label_model_hint": "← schnell / genau → (turbo: large-v3-Qualität, ~6-8× schneller auf GPU)",
        "label_ui_lang": "UI-Sprache:",
        "btn_add": "+ Hinzufügen",
        "btn_remove": "- Entfernen",
        "btn_clear": "✗ Klar",
        "btn_browse": "Durchsuchen…",
        "btn_start": "▶ Übersetzung starten",
        "btn_processing": "⏳ Verarbeitung...",
        "btn_transcribing": "⏳ Transkribieren...",
        "btn_dubbing": "⏳ Überspielen...",
        "btn_installing": "⏳ Installieren...",
        "opt_subs_only": "Nur Untertitel .srt (keine Synchronisation)",
        "opt_no_subs": "Keine Untertitel",
        "opt_no_demucs": "Sprach-/Musiktrennung überspringen (Demucs)",
        "opt_edit_subs": "Untertitel-Editor vor dem Überspielen anzeigen",
        "opt_xtts": "Voice Cloning (Coqui XTTS v2 - erster Durchlauf: Downloads ~1,8 GB)",
        "opt_lipsync": "Lippensynchronisation (Wav2Lip - Erststart: Download ~416MB)",
        "label_engine": "Übersetzungs-Engine:",
        "engine_google": "Google (Standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-Schlüssel:",
        "opt_diarization": "Sprechertrennung (pyannote)",
        "label_hf_token": "HF-Token:",
        "hint_hf_token": "Kostenloser HF-Token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Kommagetrennte Fachbegriffe/Markennamen (z. B. Strix, pipx, Docker). Reduziert Whisper-Fehler bei seltenen Wörtern um ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Fügen Sie mindestens ein Video hinzu.",
        "msg_completed": "Übersetzung abgeschlossen!",
        "msg_error": "Etwas ist schief gelaufen. Überprüfen Sie das Protokoll.",
        "msg_translation_unavailable": "Übersetzung fehlgeschlagen: Google Translate, als Engine oder als Ausweichlösung verwendet, hat die Anfragen blockiert (Limit erreicht). Versuchen Sie es später erneut oder verwenden Sie MarianMT, DeepL oder Ollama und prüfen Sie deren Konfiguration.",
        "msg_translation_partial": "Von der gewählten Engine nicht übersetzte Segmente: {n}. Sie sind in der Originalsprache geblieben oder haben eine Ausweichübersetzung. Prüfen Sie das Protokoll oder kontrollieren Sie sie im Untertitel-Editor.",
        "msg_confirm_stop": "Bearbeitung läuft. Stoppen?",
        "msg_confirm": "Bestätigen",
        "msg_completed_t": "Vollendet",
        "msg_error_t": "Fehler",
        "msg_deps_missing": "Fehlende Abhängigkeiten",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg nicht gefunden. Bitte installieren.",
        "msg_deps_install": "Automatisch installieren?",
        "msg_installed": "Pakete installiert.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Keine Segmente transkribiert.",
        "editor_title": "Untertitel-Editor",
        "editor_hint": "Überprüfen und korrigieren Sie die Untertitel vor dem Überspielen",
        "editor_col_num": "#",
        "editor_col_start": "Start",
        "editor_col_end": "Ende",
        "editor_col_orig": "Original",
        "editor_col_trans": "Übersetzung",
        "editor_btn_confirm": "✓ Bestätigen und mit dem Überspielen beginnen",
        "editor_btn_cancel": "✗ Abbrechen",
        "editor_edit_title": "Bearbeiten",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Speichern",
        "editor_filter_show_flagged_only": "Nur zu prüfende Segmente anzeigen",
        "editor_flag_summary": "Segmente: {total}  ·  Zu prüfen: {flagged} (Länge: {length}, Transkription: {whisper}, Fallback: {fallback})",
        "editor_tooltip_length_unfit": "Übersetzung zu lang: Audio wird beschleunigt - kürzen",
        "editor_tooltip_whisper_suspicious": "Verdächtige Transkription: isolierte Tokens oder Wiederholungen",
        "editor_tooltip_translation_fallback": "Fallback-Übersetzung: die primäre Engine ist gescheitert",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Herunterladen und übersetzen",
        "url_placeholder": "Fügen Sie den YouTube-Link (oder eine andere von YT-DLP unterstützte Website) ein ...",
        "msg_no_url": "Fügen Sie mindestens eine gültige URL ein.",
        "msg_downloading": "⏳ Herunterladen...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, empfohlen - präzise Übersetzungen für Synchronisation)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama-URL:",
        "hint_ollama": "Standard: qwen3:8b (empfohlen) - qwen3:4b leichtgewichtig (~3 GB), qwen3:14b höhere Qualität (~9 GB), qwen2.5:7b-instruct älter. Erfordert installiertes Ollama",
        "opt_ollama_thinking":  "🧠 Denkmodus (langsamer, bessere Übersetzungen)",
        "hint_ollama_thinking": "Überlegt Schritt für Schritt, ~10x langsamer, reduziert aber Idiom- und Grammatikfehler",
        "msg_ollama_unavailable": (
            "Ollama nicht verfügbar. Installation:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Dann Modell laden:\n"
            "  ollama pull {model}\n"
            "\n"
            "Fallback auf MarianMT/Google."
        ),
        "label_log_panel": "Protokoll:",
        "btn_log_show": "▼ Protokoll anzeigen",
        "btn_log_hide": "▲ Protokoll ausblenden",
        "btn_log_copy": "Kopieren",
        "btn_log_save": "Speichern...",
        "btn_log_clear": "Löschen",
        "btn_preflight": "Diagnose",
        "msg_preflight_title": "Diagnose",
        "msg_preflight_ok": "Diagnose abgeschlossen. Bericht im Protokoll.",
        "msg_preflight_failed": "Diagnose hat erforderliche Probleme gefunden. Überprüfen Sie das Protokoll.",
        "settings_title": "Einstellungen",
        "settings_appearance": "Erscheinungsbild",
        "settings_theme": "Design",
        "settings_accent": "Akzentfarbe",
        "settings_text_size": "Textgröße",
        "settings_language": "UI-Sprache",
        "theme_auto": "Automatisch (System)",
        "theme_light": "Hell",
        "accent_default": "Standard",
        "size_small": "Klein",
        "size_normal": "Normal",
        "size_large": "Groß",
        "size_xlarge": "Sehr groß",
        "btn_close": "Schließen",
        "btn_reset": "Auf Standardwerte zurücksetzen",
    },
    "el": {
        "label_video": "Βίντεο:",
        "label_output": "Παραγωγή:",
        "label_output_dir": "Φάκελος εξόδου:",
        "label_from": "Από:",
        "label_to": "Να:",
        "label_voice": "Φωνή:",
        "label_tts_rate": "Ταχύτητα TTS:",
        "panel_input": "Είσοδος",
        "panel_translation": "Μετάφραση",
        "panel_profile": "Προφίλ εργασίας",
        "panel_start": "Έναρξη",
        "section_audio": "Ήχος",
        "section_voice_cloning": "Κλωνοποίηση φωνής",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Διαχωρισμός ομιλητών",
        "section_model": "Μοντέλο",
        "section_engine": "Μηχανή μετάφρασης",
        "section_subtitles": "Υπότιτλοι",
        "section_hotwords": "Λέξεις-κλειδιά",
        "label_model_hint": "← γρήγορο / ακριβές → (turbo: ποιότητα large-v3, ~6-8× ταχύτερο σε GPU)",
        "label_ui_lang": "Γλώσσα διεπαφής χρήστη:",
        "btn_add": "+ Προσθήκη",
        "btn_remove": "- Αφαιρέστε",
        "btn_clear": "✗ Καθαρό",
        "btn_browse": "Ξεφυλλίζω…",
        "btn_start": "▶ Έναρξη μετάφρασης",
        "btn_processing": "⏳ Επεξεργασία...",
        "btn_transcribing": "⏳ Μεταγραφή...",
        "btn_dubbing": "⏳ Μεταγλώττιση...",
        "btn_installing": "⏳ Εγκατάσταση...",
        "opt_subs_only": "Μόνο υπότιτλοι .srt (χωρίς μεταγλώττιση)",
        "opt_no_subs": "Χωρίς υπότιτλους",
        "opt_no_demucs": "Παράλειψη διαχωρισμού φωνής/μουσικής (Demucs)",
        "opt_edit_subs": "Εμφάνιση του επεξεργαστή υποτίτλων πριν από τη μεταγλώττιση",
        "opt_xtts": "Κλωνοποίηση φωνής (Coqui XTTS v2 - πρώτη εκτέλεση: λήψεις ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip - πρώτη εκτέλεση: λήψη ~416MB)",
        "label_engine": "Μηχανή μετάφρασης:",
        "engine_google": "Google (προεπιλογή)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (τοπικό)",
        "label_deepl_key": "Κλειδί API DeepL:",
        "opt_diarization": "Διαχωρισμός ομιλητών (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Δωρεάν HF token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Τεχνικοί όροι/επωνυμίες διαχωρισμένοι με κόμμα (π.χ. Strix, pipx, Docker). Μειώνει τα σφάλματα του Whisper σε σπάνιες λέξεις κατά ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Προσθέστε τουλάχιστον ένα βίντεο.",
        "msg_completed": "Η μετάφραση ολοκληρώθηκε!",
        "msg_error": "Κάτι πήγε στραβά. Ελέγξτε το ημερολόγιο.",
        "msg_translation_unavailable": "Η μετάφραση απέτυχε: το Google Translate, που χρησιμοποιήθηκε ως μηχανή ή ως εφεδρική λύση, μπλόκαρε τα αιτήματα (συμπληρώθηκε το όριο). Δοκιμάστε ξανά αργότερα ή χρησιμοποιήστε MarianMT, DeepL ή Ollama, αφού βεβαιωθείτε ότι έχουν ρυθμιστεί σωστά.",
        "msg_translation_partial": "Τμήματα που δεν μεταφράστηκαν από την επιλεγμένη μηχανή: {n}. Έμειναν στην αρχική γλώσσα ή έχουν εφεδρική μετάφραση. Ελέγξτε το αρχείο καταγραφής ή εξετάστε τα στον επεξεργαστή υποτίτλων.",
        "msg_confirm_stop": "Επεξεργασία σε εξέλιξη. Στάση;",
        "msg_confirm": "Επιβεβαιώνω",
        "msg_completed_t": "Ολοκληρώθηκε το",
        "msg_error_t": "Σφάλμα",
        "msg_deps_missing": "Λείπουν εξαρτήσεις",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nΤο ffmpeg δεν βρέθηκε. Παρακαλώ εγκαταστήστε το.",
        "msg_deps_install": "Αυτόματη εγκατάσταση;",
        "msg_installed": "Εγκατεστημένα πακέτα.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Δεν μεταγράφηκαν τμήματα.",
        "editor_title": "Επεξεργαστής υποτίτλων",
        "editor_hint": "Ελέγξτε και διορθώστε τους υπότιτλους πριν από τη μεταγλώττιση",
        "editor_col_num": "#",
        "editor_col_start": "Αρχή",
        "editor_col_end": "Τέλος",
        "editor_col_orig": "Πρωτότυπο",
        "editor_col_trans": "Μετάφραση",
        "editor_btn_confirm": "✓ Επιβεβαιώστε και ξεκινήστε τη μεταγλώττιση",
        "editor_btn_cancel": "✗ Ακύρωση",
        "editor_edit_title": "Εκδίδω",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Εκτός",
        "editor_filter_show_flagged_only": "Εμφάνιση μόνο τμημάτων προς έλεγχο",
        "editor_flag_summary": "Τμήματα: {total}  ·  Προς έλεγχο: {flagged} (μήκος: {length}, μεταγραφή: {whisper}, εφεδρικό: {fallback})",
        "editor_tooltip_length_unfit": "Μετάφραση πολύ μεγάλη: ο ήχος θα επιταχυνθεί - συντομεύστε",
        "editor_tooltip_whisper_suspicious": "Ύποπτη μεταγραφή: μεμονωμένα tokens ή επαναλήψεις",
        "editor_tooltip_translation_fallback": "Εφεδρική μετάφραση: η κύρια μηχανή απέτυχε",
        "warn_editor": "Συντάκτης",
        "label_url": "URL:",
        "btn_download": "⬇ Λήψη & Μετάφραση",
        "url_placeholder": "Επικόλληση συνδέσμου YouTube (ή άλλου ιστότοπου που υποστηρίζεται από yt-dlp)...",
        "msg_no_url": "Επικολλήστε τουλάχιστον ένα έγκυρο URL.",
        "msg_downloading": "⏳ Λήψη...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (τοπικό, συνιστώμενο - συνοπτικές μεταφράσεις για μεταγλώττιση)",
        "label_ollama_model": "Μοντέλο:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Προεπιλογή: qwen3:8b (συνιστάται) - qwen3:4b ελαφρύ (~3 GB), qwen3:14b υψηλότερη ποιότητα (~9 GB), qwen2.5:7b-instruct παλιό. Απαιτείται εγκατεστημένο Ollama",
        "opt_ollama_thinking":  "🧠 Λειτουργία σκέψης (πιο αργή, καλύτερες μεταφράσεις)",
        "hint_ollama_thinking": "Συλλογίζεται βήμα-βήμα, ~10x πιο αργή αλλά μειώνει λάθη ιδιωμάτων/γραμματικής",
        "msg_ollama_unavailable": (
            "Το Ollama δεν είναι διαθέσιμο. Εγκατάσταση:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Στη συνέχεια λάβετε το μοντέλο:\n"
            "  ollama pull {model}\n"
            "\n"
            "Επιστροφή σε MarianMT/Google."
        ),
        "label_log_panel": "Καταγραφή:",
        "btn_log_show": "▼ Εμφάνιση καταγραφής",
        "btn_log_hide": "▲ Απόκρυψη καταγραφής",
        "btn_log_copy": "Αντιγραφή",
        "btn_log_save": "Αποθήκευση...",
        "btn_log_clear": "Εκκαθάριση",
        "btn_preflight": "Διαγνωστικά",
        "msg_preflight_title": "Διαγνωστικά",
        "msg_preflight_ok": "Τα διαγνωστικά ολοκληρώθηκαν. Αναφορά στο ημερολόγιο.",
        "msg_preflight_failed": "Τα διαγνωστικά εντόπισαν απαιτούμενα προβλήματα. Ελέγξτε το ημερολόγιο.",
        "settings_title": "Ρυθμίσεις",
        "settings_appearance": "Εμφάνιση",
        "settings_theme": "Θέμα",
        "settings_accent": "Χρώμα έμφασης",
        "settings_text_size": "Μέγεθος κειμένου",
        "settings_language": "Γλώσσα διεπαφής",
        "theme_auto": "Αυτόματο (σύστημα)",
        "theme_light": "Ανοιχτόχρωμο",
        "accent_default": "Προεπιλογή",
        "size_small": "Μικρό",
        "size_normal": "Κανονικό",
        "size_large": "Μεγάλο",
        "size_xlarge": "Πολύ μεγάλο",
        "btn_close": "Κλείσιμο",
        "btn_reset": "Επαναφορά προεπιλογών",
    },
    "hi": {
        "label_video": "वीडियो:",
        "label_output": "आउटपुट:",
        "label_output_dir": "आउटपुट फ़ोल्डर:",
        "label_from": "से:",
        "label_to": "को:",
        "label_voice": "आवाज़:",
        "label_tts_rate": "टीटीएस स्पीड:",
        "panel_input": "इनपुट",
        "panel_translation": "अनुवाद",
        "panel_profile": "वर्कफ़्लो प्रोफ़ाइल",
        "panel_start": "प्रारंभ",
        "section_audio": "ऑडियो",
        "section_voice_cloning": "वॉयस क्लोनिंग",
        "section_lip_sync": "लिप सिंक",
        "section_diarization": "वक्ता पहचान",
        "section_model": "मॉडल",
        "section_engine": "अनुवाद इंजन",
        "section_subtitles": "उपशीर्षक",
        "section_hotwords": "मुख्य शब्द",
        "label_model_hint": "← तेज़/सटीक → (turbo: large-v3 गुणवत्ता, GPU पर ~6-8× तेज़)",
        "label_ui_lang": "यूआई भाषा:",
        "btn_add": "+ जोड़ें",
        "btn_remove": "- निकालना",
        "btn_clear": "✗ साफ़ करें",
        "btn_browse": "ब्राउज़ करें...",
        "btn_start": "▶ अनुवाद प्रारंभ करें",
        "btn_processing": "⏳ प्रसंस्करण...",
        "btn_transcribing": "⏳ प्रतिलेखन...",
        "btn_dubbing": "⏳ डबिंग...",
        "btn_installing": "⏳ इंस्टॉल हो रहा है...",
        "opt_subs_only": "केवल उपशीर्षक .srt (कोई डबिंग नहीं)",
        "opt_no_subs": "कोई उपशीर्षक नहीं",
        "opt_no_demucs": "आवाज/संगीत पृथक्करण छोड़ें (डेमुक्स)",
        "opt_edit_subs": "डबिंग से पहले उपशीर्षक संपादक दिखाएँ",
        "opt_xtts": "वॉयस क्लोनिंग (कोक्वी XTTS v2 - पहला रन: डाउनलोड ~1.8GB)",
        "opt_lipsync": "लिप सिंक (Wav2Lip - पहली बार: ~416MB डाउनलोड)",
        "label_engine": "अनुवाद इंजन:",
        "engine_google": "Google (डिफ़ॉल्ट)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (लोकल)",
        "label_deepl_key": "DeepL API कुंजी:",
        "opt_diarization": "वक्ता पहचान (pyannote)",
        "label_hf_token": "HF टोकन:",
        "hint_hf_token": "मुफ़्त HF टोकन: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "अल्पविराम से अलग किए गए तकनीकी शब्द/ब्रांड नाम (जैसे Strix, pipx, Docker)। दुर्लभ शब्दों पर Whisper की त्रुटियाँ ~43% तक कम करता है",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "कम से कम एक वीडियो जोड़ें.",
        "msg_completed": "अनुवाद पूरा हुआ!",
        "msg_error": "कुछ गलत हो गया। लॉग की जाँच करें.",
        "msg_translation_unavailable": "अनुवाद विफल: इंजन या बैकअप के रूप में उपयोग किए गए Google Translate ने अनुरोध रोक दिए (सीमा पूरी हो गई)। बाद में फिर से प्रयास करें या MarianMT, DeepL या Ollama का उपयोग करें और सुनिश्चित करें कि वे सही ढंग से कॉन्फ़िगर हैं।",
        "msg_translation_partial": "चुने गए इंजन द्वारा अनूदित न किए गए खंड: {n}। वे मूल भाषा में रह गए हैं या उनका बैकअप अनुवाद है। लॉग देखें या उपशीर्षक संपादक में उनकी समीक्षा करें।",
        "msg_confirm_stop": "प्रसंस्करण प्रगति पर है. रुकना?",
        "msg_confirm": "पुष्टि करना",
        "msg_completed_t": "पुरा होना।",
        "msg_error_t": "गलती",
        "msg_deps_missing": "गुम निर्भरताएँ",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg नहीं मिला। कृपया इसे इंस्टॉल करें।",
        "msg_deps_install": "स्वचालित रूप से इंस्टॉल करें?",
        "msg_installed": "संकुल स्थापित.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "कोई खंड प्रतिलेखित नहीं.",
        "editor_title": "उपशीर्षक संपादक",
        "editor_hint": "डबिंग से पहले उपशीर्षक की समीक्षा करें और सही करें",
        "editor_col_num": "#",
        "editor_col_start": "शुरू",
        "editor_col_end": "अंत",
        "editor_col_orig": "मूल",
        "editor_col_trans": "अनुवाद",
        "editor_btn_confirm": "✓ पुष्टि करें और डबिंग शुरू करें",
        "editor_btn_cancel": "✗ रद्द करें",
        "editor_edit_title": "संपादन करना",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "बचाना",
        "editor_filter_show_flagged_only": "केवल समीक्षा वाले खंड दिखाएँ",
        "editor_flag_summary": "खंड: {total}  ·  समीक्षा हेतु: {flagged} (लंबाई: {length}, प्रतिलेख: {whisper}, फॉलबैक: {fallback})",
        "editor_tooltip_length_unfit": "अनुवाद बहुत लंबा: ऑडियो तेज होगा - छोटा करें",
        "editor_tooltip_whisper_suspicious": "संदिग्ध प्रतिलेख: एकल टोकन या दोहराव",
        "editor_tooltip_translation_fallback": "फॉलबैक अनुवाद: मुख्य इंजन विफल",
        "warn_editor": "संपादक",
        "label_url": "URL:",
        "btn_download": "⬇ डाउनलोड करें और अनुवाद करें",
        "url_placeholder": "YouTube लिंक चिपकाएँ (या अन्य yt-dlp समर्थित साइट)...",
        "msg_no_url": "कम से कम एक वैध यूआरएल चिपकाएँ.",
        "msg_downloading": "⏳ डाउनलोड हो रहा है...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (स्थानीय, अनुशंसित - डबिंग के लिए संक्षिप्त अनुवाद)",
        "label_ollama_model": "मॉडल:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "डिफ़ॉल्ट: qwen3:8b (अनुशंसित) - qwen3:4b हल्का (~3 GB), qwen3:14b उच्च गुणवत्ता (~9 GB), qwen2.5:7b-instruct पुराना। Ollama स्थापित होना आवश्यक",
        "opt_ollama_thinking":  "🧠 थिंकिंग मोड (धीमा, बेहतर अनुवाद)",
        "hint_ollama_thinking": "चरण-दर-चरण विचार करता है, ~10x धीमा लेकिन मुहावरे/व्याकरण की गलतियाँ कम करता है",
        "msg_ollama_unavailable": (
            "Ollama उपलब्ध नहीं है। स्थापित करने के लिए:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "फिर मॉडल खींचें:\n"
            "  ollama pull {model}\n"
            "\n"
            "MarianMT/Google पर वापस जाएगा।"
        ),
        "label_log_panel": "लॉग:",
        "btn_log_show": "▼ लॉग दिखाएं",
        "btn_log_hide": "▲ लॉग छिपाएं",
        "btn_log_copy": "कॉपी",
        "btn_log_save": "सहेजें...",
        "btn_log_clear": "साफ़ करें",
        "btn_preflight": "निदान",
        "msg_preflight_title": "निदान",
        "msg_preflight_ok": "निदान पूरा हुआ। रिपोर्ट लॉग में है।",
        "msg_preflight_failed": "निदान में आवश्यक समस्याएँ मिलीं। लॉग की जाँच करें।",
        "settings_title": "सेटिंग्स",
        "settings_appearance": "दिखावट",
        "settings_theme": "थीम",
        "settings_accent": "एक्सेंट रंग",
        "settings_text_size": "टेक्स्ट आकार",
        "settings_language": "यूआई भाषा",
        "theme_auto": "स्वचालित (सिस्टम)",
        "theme_light": "हल्का",
        "accent_default": "डिफ़ॉल्ट",
        "size_small": "छोटा",
        "size_normal": "सामान्य",
        "size_large": "बड़ा",
        "size_xlarge": "बहुत बड़ा",
        "btn_close": "बंद करें",
        "btn_reset": "डिफ़ॉल्ट पर रीसेट करें",
    },
    "hu": {
        "label_video": "Videó:",
        "label_output": "Kimenet:",
        "label_output_dir": "Kimeneti mappa:",
        "label_from": "Tól:",
        "label_to": "Címzett:",
        "label_voice": "Hang:",
        "label_tts_rate": "TTS sebesség:",
        "panel_input": "Bemenet",
        "panel_translation": "Fordítás",
        "panel_profile": "Munkafolyamat profil",
        "panel_start": "Indítás",
        "section_audio": "Hang",
        "section_voice_cloning": "Hangklónozás",
        "section_lip_sync": "Ajakszinkron",
        "section_diarization": "Beszélőelkülönítés",
        "section_model": "Modell",
        "section_engine": "Fordítómotor",
        "section_subtitles": "Feliratok",
        "section_hotwords": "Kulcsszavak",
        "label_model_hint": "← gyors / pontos → (turbo: large-v3 minőség, ~6-8× gyorsabb GPU-n)",
        "label_ui_lang": "UI nyelv:",
        "btn_add": "+ Hozzáadás",
        "btn_remove": "- Távolítsa el",
        "btn_clear": "✗ Tiszta",
        "btn_browse": "Tallózás…",
        "btn_start": "▶ Indítsa el a fordítást",
        "btn_processing": "⏳ Feldolgozás...",
        "btn_transcribing": "⏳ Átírás...",
        "btn_dubbing": "⏳ Szinkronizálás...",
        "btn_installing": "⏳ Telepítés...",
        "opt_subs_only": "Csak feliratok .srt (nincs szinkron)",
        "opt_no_subs": "Nincs felirat",
        "opt_no_demucs": "Hang/zene szétválasztásának kihagyása (Demucs)",
        "opt_edit_subs": "Feliratszerkesztő megjelenítése szinkronizálás előtt",
        "opt_xtts": "Hangklónozás (Coqui XTTS v2 - első futtatás: letöltések ~1,8 GB)",
        "opt_lipsync": "Ajakszinkron (Wav2Lip - első futás: letöltés ~416MB)",
        "label_engine": "Fordítómotor:",
        "engine_google": "Google (alapértelmezett)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (helyi)",
        "label_deepl_key": "DeepL API kulcs:",
        "opt_diarization": "Beszélőelkülönítés (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Ingyenes HF token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Vesszővel elválasztott technikai kifejezések/márkanevek (pl. Strix, pipx, Docker). ~43%-kal csökkenti a Whisper hibáit ritka szavaknál",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Adjon hozzá legalább egy videót.",
        "msg_completed": "A fordítás elkészült!",
        "msg_error": "Valami elromlott. Ellenőrizze a naplót.",
        "msg_translation_unavailable": "A fordítás sikertelen: a motorként vagy tartalékként használt Google Translate letiltotta a kéréseket (elérte a korlátot). Próbálja újra később, vagy használja a MarianMT, DeepL vagy Ollama motort, és ellenőrizze, hogy helyesen vannak-e beállítva.",
        "msg_translation_partial": "A választott motor által le nem fordított szegmensek: {n}. Az eredeti nyelven maradtak, vagy tartalékfordítást kaptak. Nézze meg a naplót, vagy ellenőrizze őket a feliratszerkesztőben.",
        "msg_confirm_stop": "Feldolgozás folyamatban. Stop?",
        "msg_confirm": "Erősítse meg",
        "msg_completed_t": "Befejezve",
        "msg_error_t": "Hiba",
        "msg_deps_missing": "Hiányzó függőségek",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg nem található. Kérjük, telepítse.",
        "msg_deps_install": "Automatikus telepítés?",
        "msg_installed": "Csomagok telepítve.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Nincsenek átírva szegmensek.",
        "editor_title": "Feliratszerkesztő",
        "editor_hint": "Szinkronizálás előtt nézze át és javítsa ki a feliratokat",
        "editor_col_num": "#",
        "editor_col_start": "Indul",
        "editor_col_end": "Vége",
        "editor_col_orig": "Eredeti",
        "editor_col_trans": "Fordítás",
        "editor_btn_confirm": "✓ Erősítse meg és indítsa el a szinkronizálást",
        "editor_btn_cancel": "✗ Mégse",
        "editor_edit_title": "Szerkesztés",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Megtakarítás",
        "editor_filter_show_flagged_only": "Csak az átvizsgálandó szegmensek mutatása",
        "editor_flag_summary": "Szegmensek: {total}  ·  Ellenőrzendő: {flagged} (hossz: {length}, átirat: {whisper}, tartalék: {fallback})",
        "editor_tooltip_length_unfit": "A fordítás túl hosszú: a hang fel lesz gyorsítva - rövidítse",
        "editor_tooltip_whisper_suspicious": "Gyanús átirat: izolált tokenek vagy ismétlések",
        "editor_tooltip_translation_fallback": "Tartalékfordítás: a fő motor meghiúsult",
        "warn_editor": "Szerkesztő",
        "label_url": "URL:",
        "btn_download": "⬇ Letöltés és fordítás",
        "url_placeholder": "YouTube link (vagy más yt-dlp által támogatott webhely) beillesztése...",
        "msg_no_url": "Illesszen be legalább egy érvényes URL-t.",
        "msg_downloading": "⏳ Letöltés...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM (helyi, ajánlott - tömör fordítások szinkronizáláshoz)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Alapértelmezett: qwen3:8b (ajánlott) - qwen3:4b könnyű (~3 GB), qwen3:14b jobb minőség (~9 GB), qwen2.5:7b-instruct régi. Telepített Ollama szükséges",
        "opt_ollama_thinking":  "🧠 Gondolkodó mód (lassabb, jobb fordítások)",
        "hint_ollama_thinking": "Lépésről lépésre mérlegel, ~10x lassabb, de csökkenti az idióma- és nyelvtani hibákat",
        "msg_ollama_unavailable": (
            "Ollama nem elérhető. Telepítéshez:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Majd húzza le a modellt:\n"
            "  ollama pull {model}\n"
            "\n"
            "Visszaállás MarianMT/Google használatára."
        ),
        "label_log_panel": "Napló:",
        "btn_log_show": "▼ Napló megjelenítése",
        "btn_log_hide": "▲ Napló elrejtése",
        "btn_log_copy": "Másolás",
        "btn_log_save": "Mentés...",
        "btn_log_clear": "Törlés",
        "btn_preflight": "Diagnosztika",
        "msg_preflight_title": "Diagnosztika",
        "msg_preflight_ok": "Diagnosztika befejezve. Jelentés a naplóban.",
        "msg_preflight_failed": "A diagnosztika szükséges problémákat talált. Ellenőrizze a naplót.",
        "settings_title": "Beállítások",
        "settings_appearance": "Megjelenés",
        "settings_theme": "Téma",
        "settings_accent": "Kiemelő szín",
        "settings_text_size": "Szövegméret",
        "settings_language": "Felület nyelve",
        "theme_auto": "Automatikus (rendszer)",
        "theme_light": "Világos",
        "accent_default": "Alapértelmezett",
        "size_small": "Kicsi",
        "size_normal": "Normál",
        "size_large": "Nagy",
        "size_xlarge": "Extra nagy",
        "btn_close": "Bezárás",
        "btn_reset": "Alapértelmezés visszaállítása",
    },
    "id": {
        "label_video": "Video:",
        "label_output": "Keluaran:",
        "label_output_dir": "Folder keluaran:",
        "label_from": "Dari:",
        "label_to": "Ke:",
        "label_voice": "Suara:",
        "label_tts_rate": "Kecepatan TTS:",
        "panel_input": "Masukan",
        "panel_translation": "Terjemahan",
        "panel_profile": "Profil alur kerja",
        "panel_start": "Mulai",
        "section_audio": "Audio",
        "section_voice_cloning": "Kloning Suara",
        "section_lip_sync": "Sinkronisasi Bibir",
        "section_diarization": "Pemisahan pembicara",
        "section_model": "Model",
        "section_engine": "Mesin terjemahan",
        "section_subtitles": "Subtitle",
        "section_hotwords": "Kata kunci",
        "label_model_hint": "← cepat / akurat → (turbo: kualitas large-v3, ~6-8× lebih cepat di GPU)",
        "label_ui_lang": "Bahasa UI:",
        "btn_add": "+ Tambahkan",
        "btn_remove": "- Menghapus",
        "btn_clear": "✗ Jelas",
        "btn_browse": "Jelajahi…",
        "btn_start": "▶ Mulai Terjemahan",
        "btn_processing": "⏳ Memproses...",
        "btn_transcribing": "⏳ Mentranskripsikan...",
        "btn_dubbing": "⏳ Sulih suara...",
        "btn_installing": "⏳ Memasang...",
        "opt_subs_only": "Subtitle saja .srt (tanpa dubbing)",
        "opt_no_subs": "Tidak ada subtitle",
        "opt_no_demucs": "Lewati pemisahan suara/musik (Demucs)",
        "opt_edit_subs": "Tampilkan editor subtitle sebelum melakukan dubbing",
        "opt_xtts": "Kloning Suara (Coqui XTTS v2 - dijalankan pertama kali: unduh ~1,8GB)",
        "opt_lipsync": "Sinkronisasi Bibir (Wav2Lip - menjalankan pertama: unduh ~416MB)",
        "label_engine": "Mesin terjemahan:",
        "engine_google": "Google (default)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "Kunci API DeepL:",
        "opt_diarization": "Pemisahan pembicara (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratis: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Istilah teknis/nama merek dipisahkan koma (mis. Strix, pipx, Docker). Mengurangi kesalahan Whisper pada kata jarang ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Tambahkan setidaknya satu video.",
        "msg_completed": "Terjemahan selesai!",
        "msg_error": "Ada yang tidak beres. Periksa lognya.",
        "msg_translation_unavailable": "Terjemahan gagal: Google Translate, yang dipakai sebagai mesin atau cadangan, memblokir permintaan (batas tercapai). Coba lagi nanti atau gunakan MarianMT, DeepL, atau Ollama dan pastikan sudah dikonfigurasi dengan benar.",
        "msg_translation_partial": "Segmen yang tidak diterjemahkan oleh mesin yang dipilih: {n}. Segmen tersebut tetap dalam bahasa asli atau memakai terjemahan cadangan. Periksa log atau tinjau di editor subtitle.",
        "msg_confirm_stop": "Pemrosesan sedang berlangsung. Berhenti?",
        "msg_confirm": "Mengonfirmasi",
        "msg_completed_t": "Selesai",
        "msg_error_t": "Kesalahan",
        "msg_deps_missing": "Ketergantungan tidak ada",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg tidak ditemukan. Silakan instal.",
        "msg_deps_install": "Instal secara otomatis?",
        "msg_installed": "Paket diinstal.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Tidak ada segmen yang ditranskripsi.",
        "editor_title": "Editor Subjudul",
        "editor_hint": "Tinjau dan perbaiki subtitle sebelum melakukan dubbing",
        "editor_col_num": "#",
        "editor_col_start": "Awal",
        "editor_col_end": "Akhir",
        "editor_col_orig": "Asli",
        "editor_col_trans": "Terjemahan",
        "editor_btn_confirm": "✓ Konfirmasikan dan mulai dubbing",
        "editor_btn_cancel": "✗ Batal",
        "editor_edit_title": "Sunting",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Menyimpan",
        "editor_filter_show_flagged_only": "Tampilkan hanya segmen yang perlu ditinjau",
        "editor_flag_summary": "Segmen: {total}  ·  Perlu ditinjau: {flagged} (panjang: {length}, transkrip: {whisper}, cadangan: {fallback})",
        "editor_tooltip_length_unfit": "Terjemahan terlalu panjang: audio akan dipercepat - perpendek",
        "editor_tooltip_whisper_suspicious": "Transkrip mencurigakan: token terisolasi atau pengulangan",
        "editor_tooltip_translation_fallback": "Terjemahan cadangan: mesin utama gagal",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Unduh & Terjemahkan",
        "url_placeholder": "Tempel tautan YouTube (atau situs lain yang mendukung yt-dlp)...",
        "msg_no_url": "Tempelkan setidaknya satu URL yang valid.",
        "msg_downloading": "⏳ Mengunduh...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, direkomendasikan - terjemahan ringkas untuk dubbing)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Default: qwen3:8b (direkomendasikan) - qwen3:4b ringan (~3 GB), qwen3:14b kualitas lebih tinggi (~9 GB), qwen2.5:7b-instruct lawas. Memerlukan Ollama terinstal",
        "opt_ollama_thinking":  "🧠 Mode berpikir (lebih lambat, terjemahan lebih baik)",
        "hint_ollama_thinking": "Mempertimbangkan langkah demi langkah, ~10x lebih lambat tetapi mengurangi kesalahan idiom/tata bahasa",
        "msg_ollama_unavailable": (
            "Ollama tidak tersedia. Untuk instal:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Kemudian tarik model:\n"
            "  ollama pull {model}\n"
            "\n"
            "Akan kembali ke MarianMT/Google."
        ),
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Tampilkan log",
        "btn_log_hide": "▲ Sembunyikan log",
        "btn_log_copy": "Salin",
        "btn_log_save": "Simpan...",
        "btn_log_clear": "Bersihkan",
        "btn_preflight": "Diagnostik",
        "msg_preflight_title": "Diagnostik",
        "msg_preflight_ok": "Diagnostik selesai. Laporan ada di log.",
        "msg_preflight_failed": "Diagnostik menemukan masalah yang harus diperbaiki. Periksa lognya.",
        "settings_title": "Pengaturan",
        "settings_appearance": "Tampilan",
        "settings_theme": "Tema",
        "settings_accent": "Warna aksen",
        "settings_text_size": "Ukuran teks",
        "settings_language": "Bahasa antarmuka",
        "theme_auto": "Otomatis (sistem)",
        "theme_light": "Terang",
        "accent_default": "Default",
        "size_small": "Kecil",
        "size_normal": "Normal",
        "size_large": "Besar",
        "size_xlarge": "Sangat besar",
        "btn_close": "Tutup",
        "btn_reset": "Pulihkan default",
    },
    "ja": {
        "label_video": "ビデオ：",
        "label_output": "出力：",
        "label_output_dir": "出力フォルダー：",
        "label_from": "から：",
        "label_to": "に：",
        "label_voice": "声：",
        "label_tts_rate": "TTS速度:",
        "panel_input": "入力",
        "panel_translation": "翻訳",
        "panel_profile": "ワークフロー設定",
        "panel_start": "開始",
        "section_audio": "オーディオ",
        "section_voice_cloning": "音声クローン作成",
        "section_lip_sync": "リップシンク",
        "section_diarization": "話者ダイアライゼーション",
        "section_model": "モデル",
        "section_engine": "翻訳エンジン",
        "section_subtitles": "字幕",
        "section_hotwords": "キーワード",
        "label_model_hint": "← 速い / 正確 → (turbo: large-v3 品質、GPUで約6-8倍高速)",
        "label_ui_lang": "UI言語:",
        "btn_add": "+追加",
        "btn_remove": "- 取り除く",
        "btn_clear": "✗ クリア",
        "btn_browse": "ブラウズ…",
        "btn_start": "▶ 翻訳を開始する",
        "btn_processing": "⏳ 処理中...",
        "btn_transcribing": "⏳ 文字起こし中...",
        "btn_dubbing": "⏳ ダビング中...",
        "btn_installing": "⏳ インストール中...",
        "opt_subs_only": "字幕のみ .srt (吹き替えなし)",
        "opt_no_subs": "字幕なし",
        "opt_no_demucs": "音声と音楽の分離をスキップする (Demucs)",
        "opt_edit_subs": "吹き替え前に字幕エディタを表示",
        "opt_xtts": "音声クローン作成 (Coqui XTTS v2 - 初回実行: ダウンロード ~1.8GB)",
        "opt_lipsync": "リップシンク (Wav2Lip - 初回実行: 約416MBダウンロード)",
        "label_engine": "翻訳エンジン:",
        "engine_google": "Google (デフォルト)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (ローカル)",
        "label_deepl_key": "DeepL APIキー:",
        "opt_diarization": "話者ダイアライゼーション (pyannote)",
        "label_hf_token": "HFトークン:",
        "hint_hf_token": "無料HFトークン: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "カンマ区切りの専門用語/ブランド名(例: Strix, pipx, Docker)。まれな単語でのWhisperのエラーを約43%削減します",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "少なくとも 1 つのビデオを追加します。",
        "msg_completed": "翻訳が完了しました！",
        "msg_error": "何か問題が発生しました。ログを確認してください。",
        "msg_translation_unavailable": "翻訳に失敗しました: 翻訳エンジンまたは代替エンジンとして使われた Google Translate がリクエストをブロックしました (制限に達しました)。後でもう一度試すか、設定が正しいことを確認したうえで MarianMT、DeepL、Ollama のいずれかを使用してください。",
        "msg_translation_partial": "選択したエンジンで翻訳されなかったセグメント: {n}。元の言語のままか、代替の翻訳になっています。ログを確認するか、字幕エディターで確認してください。",
        "msg_confirm_stop": "処理中です。停止？",
        "msg_confirm": "確認する",
        "msg_completed_t": "完了しました",
        "msg_error_t": "エラー",
        "msg_deps_missing": "依存関係が欠落している",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpegが見つかりません。インストールしてください。",
        "msg_deps_install": "自動的にインストールしますか?",
        "msg_installed": "パッケージがインストールされました。",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "転写されたセグメントはありません。",
        "editor_title": "字幕エディター",
        "editor_hint": "吹き替え前に字幕を確認して修正する",
        "editor_col_num": "#",
        "editor_col_start": "始める",
        "editor_col_end": "終わり",
        "editor_col_orig": "オリジナル",
        "editor_col_trans": "翻訳",
        "editor_btn_confirm": "✓ 確認してダビングを開始する",
        "editor_btn_cancel": "✗ キャンセル",
        "editor_edit_title": "編集",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "保存",
        "editor_filter_show_flagged_only": "確認が必要なセグメントのみ表示",
        "editor_flag_summary": "セグメント: {total}  ·  要確認: {flagged} (長さ: {length}, 文字起こし: {whisper}, フォールバック: {fallback})",
        "editor_tooltip_length_unfit": "翻訳が長すぎ: 音声が速くなります - 短くしてください",
        "editor_tooltip_whisper_suspicious": "疑わしい文字起こし: 単独のトークンや繰り返し",
        "editor_tooltip_translation_fallback": "フォールバック翻訳: メインエンジンが失敗",
        "warn_editor": "エディタ",
        "label_url": "URL:",
        "btn_download": "⬇ ダウンロードと翻訳",
        "url_placeholder": "YouTube リンク (または他の yt-dlp サポート サイト) を貼り付けます...",
        "msg_no_url": "少なくとも 1 つの有効な URL を貼り付けます。",
        "msg_downloading": "⏳ ダウンロード中...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM(ローカル、推奨 - 吹き替え用の簡潔な翻訳)",
        "label_ollama_model": "モデル:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "デフォルト: qwen3:8b(推奨) - qwen3:4b 軽量(~3 GB)、qwen3:14b 高品質(~9 GB)、qwen2.5:7b-instruct レガシー。Ollama のインストールが必要",
        "opt_ollama_thinking":  "🧠 思考モード（低速、より高品質な翻訳）",
        "hint_ollama_thinking": "段階的に検討、約10倍遅いがイディオム・文法エラーを削減",
        "msg_ollama_unavailable": (
            "Ollama が利用できません。インストール方法:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "その後モデルを取得:\n"
            "  ollama pull {model}\n"
            "\n"
            "MarianMT/Google にフォールバックします。"
        ),
        "label_log_panel": "ログ:",
        "btn_log_show": "▼ ログを表示",
        "btn_log_hide": "▲ ログを非表示",
        "btn_log_copy": "コピー",
        "btn_log_save": "保存...",
        "btn_log_clear": "クリア",
        "btn_preflight": "診断",
        "msg_preflight_title": "診断",
        "msg_preflight_ok": "診断が完了しました。レポートはログに記録されています。",
        "msg_preflight_failed": "診断で対応が必要な問題が見つかりました。ログを確認してください。",
        "settings_title": "設定",
        "settings_appearance": "外観",
        "settings_theme": "テーマ",
        "settings_accent": "アクセントカラー",
        "settings_text_size": "文字サイズ",
        "settings_language": "UI言語",
        "theme_auto": "自動（システム）",
        "theme_light": "ライト",
        "accent_default": "デフォルト",
        "size_small": "小",
        "size_normal": "標準",
        "size_large": "大",
        "size_xlarge": "特大",
        "btn_close": "閉じる",
        "btn_reset": "デフォルトに戻す",
    },
    "ko": {
        "label_video": "동영상:",
        "label_output": "산출:",
        "label_output_dir": "출력 폴더:",
        "label_from": "에서:",
        "label_to": "에게:",
        "label_voice": "목소리:",
        "label_tts_rate": "TTS 속도:",
        "panel_input": "입력",
        "panel_translation": "번역",
        "panel_profile": "워크플로 프로필",
        "panel_start": "시작",
        "section_audio": "오디오",
        "section_voice_cloning": "음성 복제",
        "section_lip_sync": "립싱크",
        "section_diarization": "화자 분리",
        "section_model": "모델",
        "section_engine": "번역 엔진",
        "section_subtitles": "자막",
        "section_hotwords": "키워드",
        "label_model_hint": "← 빠르다 / 정확하다 → (turbo: large-v3 품질, GPU에서 ~6-8배 빠름)",
        "label_ui_lang": "UI 언어:",
        "btn_add": "+ 추가",
        "btn_remove": "- 제거하다",
        "btn_clear": "✗ 지우기",
        "btn_browse": "먹다…",
        "btn_start": "▶ 번역 시작",
        "btn_processing": "⏳ 처리 중...",
        "btn_transcribing": "⏳ 스크립트 작성 중...",
        "btn_dubbing": "⏳ 더빙 중...",
        "btn_installing": "⏳ 설치 중...",
        "opt_subs_only": "자막만 .srt(더빙 없음)",
        "opt_no_subs": "자막 없음",
        "opt_no_demucs": "음성/음악 분리 건너뛰기(Demucs)",
        "opt_edit_subs": "더빙하기 전에 자막 편집기 표시",
        "opt_xtts": "음성 복제(Coqui XTTS v2 - 첫 실행: 다운로드 ~1.8GB)",
        "opt_lipsync": "립싱크 (Wav2Lip - 첫 실행: 약 416MB 다운로드)",
        "label_engine": "번역 엔진:",
        "engine_google": "Google (기본)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (로컬)",
        "label_deepl_key": "DeepL API 키:",
        "opt_diarization": "화자 분리 (pyannote)",
        "label_hf_token": "HF 토큰:",
        "hint_hf_token": "무료 HF 토큰: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "쉼표로 구분된 기술 용어/브랜드명(예: Strix, pipx, Docker). 드문 단어에서 Whisper 오류를 약 43% 줄여줍니다",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "동영상을 하나 이상 추가하세요.",
        "msg_completed": "번역 완료!",
        "msg_error": "문제가 발생했습니다. 로그를 확인하세요.",
        "msg_translation_unavailable": "번역 실패: 번역 엔진 또는 대체 엔진으로 사용된 Google Translate가 요청을 차단했습니다(한도 도달). 나중에 다시 시도하거나 MarianMT, DeepL 또는 Ollama를 사용하고 올바르게 설정되어 있는지 확인하세요.",
        "msg_translation_partial": "선택한 엔진이 번역하지 못한 세그먼트: {n}. 원래 언어로 남아 있거나 대체 번역이 사용되었습니다. 로그를 확인하거나 자막 편집기에서 검토하세요.",
        "msg_confirm_stop": "처리가 진행 중입니다. 멈추다?",
        "msg_confirm": "확인하다",
        "msg_completed_t": "완전한",
        "msg_error_t": "오류",
        "msg_deps_missing": "종속성 누락",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg를 찾을 수 없습니다. 설치해 주세요.",
        "msg_deps_install": "자동으로 설치하시겠습니까?",
        "msg_installed": "패키지가 설치되었습니다.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "기록된 세그먼트가 없습니다.",
        "editor_title": "자막 편집자",
        "editor_hint": "더빙하기 전에 자막을 검토하고 수정하세요.",
        "editor_col_num": "#",
        "editor_col_start": "시작",
        "editor_col_end": "끝",
        "editor_col_orig": "원래의",
        "editor_col_trans": "번역",
        "editor_btn_confirm": "✓ 확인하고 더빙을 시작하세요",
        "editor_btn_cancel": "✗ 취소",
        "editor_edit_title": "편집하다",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "구하다",
        "editor_filter_show_flagged_only": "검토가 필요한 세그먼트만 표시",
        "editor_flag_summary": "세그먼트: {total}  ·  검토 대상: {flagged} (길이: {length}, 전사: {whisper}, 폴백: {fallback})",
        "editor_tooltip_length_unfit": "번역이 너무 김: 오디오가 빨라짐 - 줄이세요",
        "editor_tooltip_whisper_suspicious": "의심스러운 전사: 고립된 토큰 또는 반복",
        "editor_tooltip_translation_fallback": "폴백 번역: 기본 엔진 실패",
        "warn_editor": "편집자",
        "label_url": "URL:",
        "btn_download": "⬇ 다운로드 및 번역",
        "url_placeholder": "YouTube 링크(또는 다른 yt-dlp 지원 사이트)를 붙여넣으세요...",
        "msg_no_url": "유효한 URL을 하나 이상 붙여넣으세요.",
        "msg_downloading": "⏳ 다운로드 중...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM (로컬, 권장 - 더빙용 간결한 번역)",
        "label_ollama_model": "모델:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "기본값: qwen3:8b (권장) - qwen3:4b 경량 (~3 GB), qwen3:14b 고품질 (~9 GB), qwen2.5:7b-instruct 레거시. Ollama 설치 필요",
        "opt_ollama_thinking":  "🧠 사고 모드 (느림, 더 나은 번역)",
        "hint_ollama_thinking": "단계별로 숙고, 약 10배 느리지만 관용구/문법 오류 감소",
        "msg_ollama_unavailable": (
            "Ollama를 사용할 수 없습니다. 설치하려면:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "그런 다음 모델을 가져오세요:\n"
            "  ollama pull {model}\n"
            "\n"
            "MarianMT/Google로 폴백됩니다."
        ),
        "label_log_panel": "로그:",
        "btn_log_show": "▼ 로그 표시",
        "btn_log_hide": "▲ 로그 숨기기",
        "btn_log_copy": "복사",
        "btn_log_save": "저장...",
        "btn_log_clear": "지우기",
        "btn_preflight": "진단",
        "msg_preflight_title": "진단",
        "msg_preflight_ok": "진단이 완료되었습니다. 로그에 보고서가 있습니다.",
        "msg_preflight_failed": "진단에서 처리가 필요한 문제가 발견되었습니다. 로그를 확인하세요.",
        "settings_title": "설정",
        "settings_appearance": "모양",
        "settings_theme": "테마",
        "settings_accent": "강조 색상",
        "settings_text_size": "텍스트 크기",
        "settings_language": "UI 언어",
        "theme_auto": "자동 (시스템)",
        "theme_light": "라이트",
        "accent_default": "기본값",
        "size_small": "작게",
        "size_normal": "보통",
        "size_large": "크게",
        "size_xlarge": "매우 크게",
        "btn_close": "닫기",
        "btn_reset": "기본값으로 재설정",
    },
    "no": {
        "label_video": "Video:",
        "label_output": "Produksjon:",
        "label_output_dir": "Utdatamappe:",
        "label_from": "Fra:",
        "label_to": "Til:",
        "label_voice": "Stemme:",
        "label_tts_rate": "TTS hastighet:",
        "panel_input": "Inndata",
        "panel_translation": "Oversettelse",
        "panel_profile": "Arbeidsprofil",
        "panel_start": "Start",
        "section_audio": "Lyd",
        "section_voice_cloning": "Stemmekloning",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Taleridentifikasjon",
        "section_model": "Modell",
        "section_engine": "Oversettelsesmotor",
        "section_subtitles": "Undertekster",
        "section_hotwords": "Nøkkelord",
        "label_model_hint": "← rask / nøyaktig → (turbo: large-v3 kvalitet, ~6-8× raskere på GPU)",
        "label_ui_lang": "UI-språk:",
        "btn_add": "+ Legg til",
        "btn_remove": "- Fjern",
        "btn_clear": "✗ Tydelig",
        "btn_browse": "Bla gjennom...",
        "btn_start": "▶ Start oversettelse",
        "btn_processing": "⏳ Behandler...",
        "btn_transcribing": "⏳ Transkriberer...",
        "btn_dubbing": "⏳ Dubbing...",
        "btn_installing": "⏳ Installerer...",
        "opt_subs_only": "Kun undertekster .srt (ingen dubbing)",
        "opt_no_subs": "Ingen undertekster",
        "opt_no_demucs": "Hopp over stemme-/musikkseparasjon (demucs)",
        "opt_edit_subs": "Vis undertekstredigering før dubbing",
        "opt_xtts": "Stemmekloning (Coqui XTTS v2 - første kjøring: nedlastinger ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip - første kjøring: last ned ~416MB)",
        "label_engine": "Oversettelsesmotor:",
        "engine_google": "Google (standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-nøkkel:",
        "opt_diarization": "Taleridentifikasjon (pyannote)",
        "label_hf_token": "HF-token:",
        "hint_hf_token": "Gratis HF-token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Kommaseparerte tekniske termer/merkenavn (f.eks. Strix, pipx, Docker). Reduserer Whisper-feil på sjeldne ord med ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Legg til minst én video.",
        "msg_completed": "Oversettelsen fullført!",
        "msg_error": "Noe gikk galt. Sjekk loggen.",
        "msg_translation_unavailable": "Oversettelsen mislyktes: Google Translate, brukt som motor eller som reserve, blokkerte forespørslene (grensen er nådd). Prøv igjen senere, eller bruk MarianMT, DeepL eller Ollama, og kontroller at de er riktig konfigurert.",
        "msg_translation_partial": "Segmenter som ikke ble oversatt av den valgte motoren: {n}. De er fortsatt på originalspråket eller har en reserveoversettelse. Sjekk loggen, eller gå gjennom dem i undertekstredigereren.",
        "msg_confirm_stop": "Behandling pågår. Stoppe?",
        "msg_confirm": "Bekrefte",
        "msg_completed_t": "Fullført",
        "msg_error_t": "Feil",
        "msg_deps_missing": "Manglende avhengigheter",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg ble ikke funnet. Vennligst installer det.",
        "msg_deps_install": "Installere automatisk?",
        "msg_installed": "Pakker installert.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Ingen segmenter er transkribert.",
        "editor_title": "Tekstredigerer",
        "editor_hint": "Gjennomgå og korriger undertekster før dubbing",
        "editor_col_num": "#",
        "editor_col_start": "Start",
        "editor_col_end": "Slutt",
        "editor_col_orig": "Opprinnelig",
        "editor_col_trans": "Oversettelse",
        "editor_btn_confirm": "✓ Bekreft og start dubbingen",
        "editor_btn_cancel": "✗ Avbryt",
        "editor_edit_title": "Redigere",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Spare",
        "editor_filter_show_flagged_only": "Vis bare segmenter til gjennomgang",
        "editor_flag_summary": "Segmenter: {total}  ·  Til gjennomgang: {flagged} (lengde: {length}, transkripsjon: {whisper}, reserve: {fallback})",
        "editor_tooltip_length_unfit": "Oversettelsen er for lang: lyden blir raskere - forkort",
        "editor_tooltip_whisper_suspicious": "Mistenkelig transkripsjon: isolerte tokens eller gjentakelser",
        "editor_tooltip_translation_fallback": "Reserveoversettelse: hovedmotoren feilet",
        "warn_editor": "Redaktør",
        "label_url": "URL:",
        "btn_download": "⬇ Last ned og oversett",
        "url_placeholder": "Lim inn YouTube-kobling (eller et annet yt-dlp-støttet nettsted)...",
        "msg_no_url": "Lim inn minst én gyldig nettadresse.",
        "msg_downloading": "⏳ Laster ned...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, anbefalt - konsise oversettelser for dubbing)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Standard: qwen3:8b (anbefalt) - qwen3:4b lett (~3 GB), qwen3:14b høyere kvalitet (~9 GB), qwen2.5:7b-instruct eldre. Krever Ollama installert",
        "opt_ollama_thinking":  "🧠 Tenkemodus (tregere, bedre oversettelser)",
        "hint_ollama_thinking": "Vurderer trinn for trinn, ~10x tregere men reduserer idiom-/grammatikkfeil",
        "msg_ollama_unavailable": (
            "Ollama ikke tilgjengelig. For å installere:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Deretter hent modellen:\n"
            "  ollama pull {model}\n"
            "\n"
            "Faller tilbake til MarianMT/Google."
        ),
        "label_log_panel": "Logg:",
        "btn_log_show": "▼ Vis logg",
        "btn_log_hide": "▲ Skjul logg",
        "btn_log_copy": "Kopier",
        "btn_log_save": "Lagre...",
        "btn_log_clear": "Tøm",
        "btn_preflight": "Diagnostikk",
        "msg_preflight_title": "Diagnostikk",
        "msg_preflight_ok": "Diagnostikk fullført. Rapport i loggen.",
        "msg_preflight_failed": "Diagnostikken fant nødvendige problemer. Sjekk loggen.",
        "settings_title": "Innstillinger",
        "settings_appearance": "Utseende",
        "settings_theme": "Tema",
        "settings_accent": "Aksentfarge",
        "settings_text_size": "Tekststørrelse",
        "settings_language": "Grensesnittspråk",
        "theme_auto": "Automatisk (system)",
        "theme_light": "Lys",
        "accent_default": "Standard",
        "size_small": "Liten",
        "size_normal": "Normal",
        "size_large": "Stor",
        "size_xlarge": "Svært stor",
        "btn_close": "Lukk",
        "btn_reset": "Gjenopprett standardinnstillinger",
    },
    "pl": {
        "label_video": "Wideo:",
        "label_output": "Wyjście:",
        "label_output_dir": "Folder wyjściowy:",
        "label_from": "Z:",
        "label_to": "Do:",
        "label_voice": "Głos:",
        "label_tts_rate": "Prędkość TTS:",
        "panel_input": "Wejście",
        "panel_translation": "Tłumaczenie",
        "panel_profile": "Profil pracy",
        "panel_start": "Start",
        "section_audio": "Dźwięk",
        "section_voice_cloning": "Klonowanie głosu",
        "section_lip_sync": "Synchronizacja ust",
        "section_diarization": "Rozpoznawanie mówców",
        "section_model": "Model",
        "section_engine": "Silnik tłumaczenia",
        "section_subtitles": "Napisy",
        "section_hotwords": "Słowa kluczowe",
        "label_model_hint": "← szybki / dokładny → (turbo: jakość large-v3, ~6-8× szybsze na GPU)",
        "label_ui_lang": "Język interfejsu:",
        "btn_add": "+ Dodaj",
        "btn_remove": "- Usunąć",
        "btn_clear": "✗ Jasne",
        "btn_browse": "Przeglądać…",
        "btn_start": "▶ Rozpocznij tłumaczenie",
        "btn_processing": "⏳ Przetwarzanie...",
        "btn_transcribing": "⏳ Transkrypcja...",
        "btn_dubbing": "⏳ Dubbing...",
        "btn_installing": "⏳ Instalowanie...",
        "opt_subs_only": "Tylko napisy .srt (bez dubbingu)",
        "opt_no_subs": "Brak napisów",
        "opt_no_demucs": "Pomiń separację głosu/muzyki (Demucs)",
        "opt_edit_subs": "Pokaż edytor napisów przed kopiowaniem",
        "opt_xtts": "Klonowanie głosu (Coqui XTTS v2 - pierwsze uruchomienie: pliki do pobrania ~1,8 GB)",
        "opt_lipsync": "Synchronizacja ust (Wav2Lip - pierwsze uruchomienie: pobranie ~416MB)",
        "label_engine": "Silnik tłumaczenia:",
        "engine_google": "Google (domyślny)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokalny)",
        "label_deepl_key": "Klucz API DeepL:",
        "opt_diarization": "Rozpoznawanie mówców (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Darmowy token HF: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Terminy techniczne/nazwy marek rozdzielone przecinkami (np. Strix, pipx, Docker). Zmniejsza błędy Whisper dla rzadkich słów o ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Dodaj co najmniej jeden film.",
        "msg_completed": "Tłumaczenie zakończone!",
        "msg_error": "Coś poszło nie tak. Sprawdź dziennik.",
        "msg_translation_unavailable": "Tłumaczenie nie powiodło się: Google Translate, użyty jako silnik lub rozwiązanie zapasowe, zablokował żądania (osiągnięto limit). Spróbuj ponownie później lub użyj MarianMT, DeepL albo Ollama i sprawdź, czy są poprawnie skonfigurowane.",
        "msg_translation_partial": "Liczba segmentów nieprzetłumaczonych przez wybrany silnik: {n}. Pozostały w języku oryginalnym lub mają tłumaczenie zapasowe. Sprawdź dziennik lub przejrzyj je w edytorze napisów.",
        "msg_confirm_stop": "Przetwarzanie w toku. Zatrzymywać się?",
        "msg_confirm": "Potwierdzać",
        "msg_completed_t": "Zakończony",
        "msg_error_t": "Błąd",
        "msg_deps_missing": "Brakujące zależności",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nNie znaleziono ffmpeg. Zainstaluj go.",
        "msg_deps_install": "Zainstalować automatycznie?",
        "msg_installed": "Pakiety zainstalowane.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Brak transkrypcji segmentów.",
        "editor_title": "Edytor napisów",
        "editor_hint": "Przed kopiowaniem sprawdź i popraw napisy",
        "editor_col_num": "#",
        "editor_col_start": "Start",
        "editor_col_end": "Koniec",
        "editor_col_orig": "Oryginalny",
        "editor_col_trans": "Tłumaczenie",
        "editor_btn_confirm": "✓ Potwierdź i rozpocznij kopiowanie",
        "editor_btn_cancel": "✗ Anuluj",
        "editor_edit_title": "Redagować",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Ratować",
        "editor_filter_show_flagged_only": "Pokaż tylko segmenty do przejrzenia",
        "editor_flag_summary": "Segmenty: {total}  ·  Do przejrzenia: {flagged} (długość: {length}, transkrypcja: {whisper}, zapas: {fallback})",
        "editor_tooltip_length_unfit": "Tłumaczenie zbyt długie: dźwięk zostanie przyspieszony - skróć",
        "editor_tooltip_whisper_suspicious": "Podejrzana transkrypcja: pojedyncze tokeny lub powtórzenia",
        "editor_tooltip_translation_fallback": "Tłumaczenie zapasowe: główny silnik zawiódł",
        "warn_editor": "Redaktor",
        "label_url": "URL:",
        "btn_download": "⬇ Pobierz i przetłumacz",
        "url_placeholder": "Wklej link do YouTube (lub innej witryny obsługującej yt-dlp)...",
        "msg_no_url": "Wklej co najmniej jeden prawidłowy adres URL.",
        "msg_downloading": "⏳ Pobieram...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokalny, zalecany - zwięzłe tłumaczenia do dubbingu)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Domyślnie: qwen3:8b (zalecane) - qwen3:4b lekki (~3 GB), qwen3:14b wyższa jakość (~9 GB), qwen2.5:7b-instruct starszy. Wymaga zainstalowanego Ollama",
        "opt_ollama_thinking":  "🧠 Tryb myślenia (wolniejszy, lepsze tłumaczenia)",
        "hint_ollama_thinking": "Rozważa krok po kroku, ~10x wolniej, ale zmniejsza błędy w idiomach i gramatyce",
        "msg_ollama_unavailable": (
            "Ollama niedostępny. Aby zainstalować:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Następnie pobierz model:\n"
            "  ollama pull {model}\n"
            "\n"
            "Zostanie użyty MarianMT/Google jako rezerwa."
        ),
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Pokaż log",
        "btn_log_hide": "▲ Ukryj log",
        "btn_log_copy": "Kopiuj",
        "btn_log_save": "Zapisz...",
        "btn_log_clear": "Wyczyść",
        "btn_preflight": "Diagnostyka",
        "msg_preflight_title": "Diagnostyka",
        "msg_preflight_ok": "Diagnostyka zakończona. Raport w dzienniku.",
        "msg_preflight_failed": "Diagnostyka wykryła problemy wymagające uwagi. Sprawdź dziennik.",
        "settings_title": "Ustawienia",
        "settings_appearance": "Wygląd",
        "settings_theme": "Motyw",
        "settings_accent": "Kolor akcentu",
        "settings_text_size": "Rozmiar tekstu",
        "settings_language": "Język interfejsu",
        "theme_auto": "Automatyczny (system)",
        "theme_light": "Jasny",
        "accent_default": "Domyślny",
        "size_small": "Mały",
        "size_normal": "Normalny",
        "size_large": "Duży",
        "size_xlarge": "Bardzo duży",
        "btn_close": "Zamknij",
        "btn_reset": "Przywróć ustawienia domyślne",
    },
    "pt": {
        "label_video": "Vídeo:",
        "label_output": "Saída:",
        "label_output_dir": "Pasta de saída:",
        "label_from": "De:",
        "label_to": "Para:",
        "label_voice": "Voz:",
        "label_tts_rate": "Velocidade TTS:",
        "panel_input": "Entrada",
        "panel_translation": "Tradução",
        "panel_profile": "Perfil de trabalho",
        "panel_start": "Início",
        "section_audio": "Áudio",
        "section_voice_cloning": "Clonagem de voz",
        "section_lip_sync": "Sincronização labial",
        "section_diarization": "Diarização",
        "section_model": "Modelo",
        "section_engine": "Motor de tradução",
        "section_subtitles": "Legendas",
        "section_hotwords": "Palavras-chave",
        "label_model_hint": "← rápido / preciso → (turbo: qualidade large-v3, ~6-8× mais rápido na GPU)",
        "label_ui_lang": "Idioma da interface do usuário:",
        "btn_add": "+ Adicionar",
        "btn_remove": "- Remover",
        "btn_clear": "✗ Limpar",
        "btn_browse": "Navegar…",
        "btn_start": "▶ Iniciar tradução",
        "btn_processing": "⏳ Processando...",
        "btn_transcribing": "⏳ Transcrevendo...",
        "btn_dubbing": "⏳ Dublagem...",
        "btn_installing": "⏳ Instalando...",
        "opt_subs_only": "Somente legendas .srt (sem dublagem)",
        "opt_no_subs": "Sem legendas",
        "opt_no_demucs": "Pular separação voz/música (Demucs)",
        "opt_edit_subs": "Mostrar editor de legendas antes da dublagem",
        "opt_xtts": "Clonagem de voz (Coqui XTTS v2 - primeira execução: downloads de aproximadamente 1,8 GB)",
        "opt_lipsync": "Sincronização labial (Wav2Lip - primeira execução: download ~416MB)",
        "label_engine": "Motor de tradução:",
        "engine_google": "Google (padrão)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Chave API DeepL:",
        "opt_diarization": "Diarização de locutores (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratuito: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Termos técnicos/marcas separados por vírgula (ex. Strix, pipx, Docker). Reduz erros do Whisper em palavras raras em ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Adicione pelo menos um vídeo.",
        "msg_completed": "Tradução concluída!",
        "msg_error": "Algo deu errado. Verifique o registro.",
        "msg_translation_unavailable": "Falha na tradução: o Google Translate, usado como mecanismo ou como alternativa, bloqueou as solicitações (limite atingido). Tente novamente mais tarde ou use MarianMT, DeepL ou Ollama, verificando se estão configurados corretamente.",
        "msg_translation_partial": "Segmentos não traduzidos pelo mecanismo escolhido: {n}. Ficaram no idioma original ou têm uma tradução alternativa. Verifique o registro ou revise-os no editor de legendas.",
        "msg_confirm_stop": "Processamento em andamento. Parar?",
        "msg_confirm": "Confirmar",
        "msg_completed_t": "Concluído",
        "msg_error_t": "Erro",
        "msg_deps_missing": "Dependências ausentes",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg não encontrado. Por favor, instale.",
        "msg_deps_install": "Instalar automaticamente?",
        "msg_installed": "Pacotes instalados.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Nenhum segmento transcrito.",
        "editor_title": "Editor de legendas",
        "editor_hint": "Revise e corrija as legendas antes de dublar",
        "editor_col_num": "#",
        "editor_col_start": "Começar",
        "editor_col_end": "Fim",
        "editor_col_orig": "Original",
        "editor_col_trans": "Tradução",
        "editor_btn_confirm": "✓ Confirme e comece a dublagem",
        "editor_btn_cancel": "✗ Cancelar",
        "editor_edit_title": "Editar",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Salvar",
        "editor_filter_show_flagged_only": "Mostrar somente segmentos para revisão",
        "editor_flag_summary": "Segmentos: {total}  ·  Para revisar: {flagged} (comprimento: {length}, transcrição: {whisper}, reserva: {fallback})",
        "editor_tooltip_length_unfit": "Tradução longa: o áudio será acelerado - encurte",
        "editor_tooltip_whisper_suspicious": "Transcrição suspeita: tokens isolados ou repetições",
        "editor_tooltip_translation_fallback": "Tradução de reserva: o motor principal falhou",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Baixe e traduza",
        "url_placeholder": "Cole o link do YouTube (ou outro site compatível com yt-dlp)...",
        "msg_no_url": "Cole pelo menos um URL válido.",
        "msg_downloading": "⏳ Baixando...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recomendado - traduções concisas para dublagem)",
        "label_ollama_model": "Modelo:",
        "label_ollama_url": "URL do Ollama:",
        "hint_ollama": "Padrão: qwen3:8b (recomendado) - qwen3:4b leve (~3 GB), qwen3:14b qualidade superior (~9 GB), qwen2.5:7b-instruct legado. Requer Ollama instalado",
        "opt_ollama_thinking":  "🧠 Modo pensante (mais lento, traduções melhores)",
        "hint_ollama_thinking": "Delibera passo a passo, ~10x mais lento mas reduz erros de idiomas/gramática",
        "msg_ollama_unavailable": (
            "Ollama indisponível. Para instalar:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Depois baixe o modelo:\n"
            "  ollama pull {model}\n"
            "\n"
            "Será usado MarianMT/Google como alternativa."
        ),
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Mostrar log",
        "btn_log_hide": "▲ Ocultar log",
        "btn_log_copy": "Copiar",
        "btn_log_save": "Salvar...",
        "btn_log_clear": "Limpar",
        "btn_preflight": "Diagnóstico",
        "msg_preflight_title": "Diagnóstico",
        "msg_preflight_ok": "Diagnóstico concluído. Relatório no registro.",
        "msg_preflight_failed": "O diagnóstico encontrou problemas que exigem atenção. Verifique o registro.",
        "settings_title": "Configurações",
        "settings_appearance": "Aparência",
        "settings_theme": "Tema",
        "settings_accent": "Cor de destaque",
        "settings_text_size": "Tamanho do texto",
        "settings_language": "Idioma da interface",
        "theme_auto": "Automático (sistema)",
        "theme_light": "Claro",
        "accent_default": "Padrão",
        "size_small": "Pequeno",
        "size_normal": "Normal",
        "size_large": "Grande",
        "size_xlarge": "Muito grande",
        "btn_close": "Fechar",
        "btn_reset": "Restaurar padrões",
    },
    "ro": {
        "label_video": "Video:",
        "label_output": "Ieșire:",
        "label_output_dir": "Folder de ieșire:",
        "label_from": "Din:",
        "label_to": "La:",
        "label_voice": "Voce:",
        "label_tts_rate": "Viteza TTS:",
        "panel_input": "Intrare",
        "panel_translation": "Traducere",
        "panel_profile": "Profil de lucru",
        "panel_start": "Start",
        "section_audio": "Audio",
        "section_voice_cloning": "Clonarea vocii",
        "section_lip_sync": "Lip Sync",
        "section_diarization": "Identificare vorbitori",
        "section_model": "Model",
        "section_engine": "Motor de traducere",
        "section_subtitles": "Subtitrări",
        "section_hotwords": "Cuvinte cheie",
        "label_model_hint": "← rapid / precis → (turbo: calitate large-v3, ~6-8× mai rapid pe GPU)",
        "label_ui_lang": "Limba UI:",
        "btn_add": "+ Adăugați",
        "btn_remove": "- Îndepărtează",
        "btn_clear": "✗ Clar",
        "btn_browse": "Răsfoiți...",
        "btn_start": "▶ Începeți traducerea",
        "btn_processing": "⏳ Se procesează...",
        "btn_transcribing": "⏳ Se transcrie...",
        "btn_dubbing": "⏳ Dublare...",
        "btn_installing": "⏳ Se instalează...",
        "opt_subs_only": "Numai subtitrări .srt (fără dublare)",
        "opt_no_subs": "Fără subtitrări",
        "opt_no_demucs": "Omiteți separarea voce/muzică (Demucs)",
        "opt_edit_subs": "Afișați editorul de subtitrări înainte de dublare",
        "opt_xtts": "Clonarea vocii (Coqui XTTS v2 - prima rulare: descărcări ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip - prima rulare: descărcare ~416MB)",
        "label_engine": "Motor de traducere:",
        "engine_google": "Google (implicit)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Cheie API DeepL:",
        "opt_diarization": "Identificare vorbitori (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratuit: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Termeni tehnici/mărci separate prin virgulă (ex. Strix, pipx, Docker). Reduce erorile Whisper la cuvinte rare cu ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Adăugați cel puțin un videoclip.",
        "msg_completed": "Traducerea finalizată!",
        "msg_error": "Ceva a mers prost. Verificați jurnalul.",
        "msg_translation_unavailable": "Traducerea a eșuat: Google Translate, folosit ca motor sau ca rezervă, a blocat cererile (limită atinsă). Încercați din nou mai târziu sau folosiți MarianMT, DeepL sau Ollama, verificând că sunt configurate corect.",
        "msg_translation_partial": "Segmente netraduse de motorul ales: {n}. Au rămas în limba originală sau au o traducere de rezervă. Verificați jurnalul sau revizuiți-le în editorul de subtitrări.",
        "msg_confirm_stop": "Procesare în curs. Stop?",
        "msg_confirm": "Confirma",
        "msg_completed_t": "Terminat",
        "msg_error_t": "Eroare",
        "msg_deps_missing": "Lipsesc dependențe",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg nu a fost găsit. Vă rugăm să îl instalați.",
        "msg_deps_install": "Instalați automat?",
        "msg_installed": "Pachetele instalate.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Nu au fost transcrise segmente.",
        "editor_title": "Editor de subtitrări",
        "editor_hint": "Verificați și corectați subtitrările înainte de dublare",
        "editor_col_num": "#",
        "editor_col_start": "Început",
        "editor_col_end": "Sfârşit",
        "editor_col_orig": "Original",
        "editor_col_trans": "Traducere",
        "editor_btn_confirm": "✓ Confirmați și începeți dublarea",
        "editor_btn_cancel": "✗ Anulează",
        "editor_edit_title": "Edita",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Salva",
        "editor_filter_show_flagged_only": "Afișează doar segmentele de revizuit",
        "editor_flag_summary": "Segmente: {total}  ·  De revizuit: {flagged} (lungime: {length}, transcriere: {whisper}, rezervă: {fallback})",
        "editor_tooltip_length_unfit": "Traducere prea lungă: audio va fi accelerat - scurtează",
        "editor_tooltip_whisper_suspicious": "Transcriere suspectă: tokenuri izolate sau repetiții",
        "editor_tooltip_translation_fallback": "Traducere de rezervă: motorul principal a eșuat",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Descărcați și traduceți",
        "url_placeholder": "Inserați linkul YouTube (sau alt site acceptat de yt-dlp)...",
        "msg_no_url": "Lipiți cel puțin o adresă URL validă.",
        "msg_downloading": "⏳ Se descarcă...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recomandat - traduceri concise pentru dublaj)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Implicit: qwen3:8b (recomandat) - qwen3:4b ușor (~3 GB), qwen3:14b calitate superioară (~9 GB), qwen2.5:7b-instruct vechi. Necesită Ollama instalat",
        "opt_ollama_thinking":  "🧠 Mod gândire (mai lent, traduceri mai bune)",
        "hint_ollama_thinking": "Deliberează pas cu pas, ~10x mai lent, dar reduce erorile de idiomuri/gramatică",
        "msg_ollama_unavailable": (
            "Ollama indisponibil. Pentru instalare:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Apoi descărcați modelul:\n"
            "  ollama pull {model}\n"
            "\n"
            "Se va folosi MarianMT/Google ca rezervă."
        ),
        "label_log_panel": "Jurnal:",
        "btn_log_show": "▼ Afișează jurnalul",
        "btn_log_hide": "▲ Ascunde jurnalul",
        "btn_log_copy": "Copiază",
        "btn_log_save": "Salvează...",
        "btn_log_clear": "Șterge",
        "btn_preflight": "Diagnostic",
        "msg_preflight_title": "Diagnostic",
        "msg_preflight_ok": "Diagnostic finalizat. Raport în jurnal.",
        "msg_preflight_failed": "Diagnosticul a găsit probleme care necesită atenție. Verificați jurnalul.",
        "settings_title": "Setări",
        "settings_appearance": "Aspect",
        "settings_theme": "Temă",
        "settings_accent": "Culoare de accent",
        "settings_text_size": "Dimensiune text",
        "settings_language": "Limba interfeței",
        "theme_auto": "Automat (sistem)",
        "theme_light": "Luminos",
        "accent_default": "Implicit",
        "size_small": "Mic",
        "size_normal": "Normal",
        "size_large": "Mare",
        "size_xlarge": "Foarte mare",
        "btn_close": "Închide",
        "btn_reset": "Restabilește setările implicite",
    },
    "ru": {
        "label_video": "Видео:",
        "label_output": "Выход:",
        "label_output_dir": "Папка вывода:",
        "label_from": "От:",
        "label_to": "К:",
        "label_voice": "Голос:",
        "label_tts_rate": "Скорость ТТС:",
        "panel_input": "Вход",
        "panel_translation": "Перевод",
        "panel_profile": "Профиль работы",
        "panel_start": "Запуск",
        "section_audio": "Аудио",
        "section_voice_cloning": "Голосовое клонирование",
        "section_lip_sync": "Синхронизация губ",
        "section_diarization": "Разделение дикторов",
        "section_model": "Модель",
        "section_engine": "Движок перевода",
        "section_subtitles": "Субтитры",
        "section_hotwords": "Ключевые слова",
        "label_model_hint": "← быстро / точно → (turbo: качество large-v3, ~6-8× быстрее на GPU)",
        "label_ui_lang": "Язык пользовательского интерфейса:",
        "btn_add": "+ Добавить",
        "btn_remove": "- Удалять",
        "btn_clear": "✗ Очистить",
        "btn_browse": "Просматривать…",
        "btn_start": "▶ Начать перевод",
        "btn_processing": "⏳ Обработка...",
        "btn_transcribing": "⏳ Транскрипция...",
        "btn_dubbing": "⏳ Дубляж...",
        "btn_installing": "⏳ Установка...",
        "opt_subs_only": "Только субтитры .srt (без дубляжа)",
        "opt_no_subs": "Нет субтитров",
        "opt_no_demucs": "Пропустить разделение голоса и музыки (Demucs)",
        "opt_edit_subs": "Показывать редактор субтитров перед перезаписью",
        "opt_xtts": "Голосовое клонирование (Coqui XTTS v2 - первый запуск: загрузка ~ 1,8 ГБ)",
        "opt_lipsync": "Синхронизация губ (Wav2Lip - первый запуск: загрузка ~416МБ)",
        "label_engine": "Движок перевода:",
        "engine_google": "Google (по умолчанию)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (локально)",
        "label_deepl_key": "API ключ DeepL:",
        "opt_diarization": "Разделение дикторов (pyannote)",
        "label_hf_token": "Токен HF:",
        "hint_hf_token": "Бесплатный токен HF: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Технические термины/бренды через запятую (напр. Strix, pipx, Docker). Снижает ошибки Whisper на редких словах на ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Добавьте хотя бы одно видео.",
        "msg_completed": "Перевод завершен!",
        "msg_error": "Что-то пошло не так. Проверьте журнал.",
        "msg_translation_unavailable": "Перевод не выполнен: Google Translate, использованный как движок или как резервный вариант, заблокировал запросы (достигнут лимит). Повторите попытку позже или используйте MarianMT, DeepL или Ollama, убедившись, что они правильно настроены.",
        "msg_translation_partial": "Сегменты, не переведённые выбранным движком: {n}. Они остались на исходном языке или получили резервный перевод. Проверьте журнал или просмотрите их в редакторе субтитров.",
        "msg_confirm_stop": "Идет обработка. Останавливаться?",
        "msg_confirm": "Подтверждать",
        "msg_completed_t": "Завершенный",
        "msg_error_t": "Ошибка",
        "msg_deps_missing": "Отсутствующие зависимости",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg не найден. Пожалуйста, установите его.",
        "msg_deps_install": "Установить автоматически?",
        "msg_installed": "Пакеты установлены.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Никакие сегменты не транскрибируются.",
        "editor_title": "Редактор субтитров",
        "editor_hint": "Просмотрите и исправьте субтитры перед перезаписью.",
        "editor_col_num": "#",
        "editor_col_start": "Начинать",
        "editor_col_end": "Конец",
        "editor_col_orig": "Оригинал",
        "editor_col_trans": "Перевод",
        "editor_btn_confirm": "✓ Подтвердите и начните перезапись.",
        "editor_btn_cancel": "✗ Отмена",
        "editor_edit_title": "Редактировать",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Сохранять",
        "editor_filter_show_flagged_only": "Показывать только сегменты для проверки",
        "editor_flag_summary": "Сегменты: {total}  ·  К проверке: {flagged} (длина: {length}, транскрипция: {whisper}, резерв: {fallback})",
        "editor_tooltip_length_unfit": "Перевод слишком длинный: аудио ускорится - сократите",
        "editor_tooltip_whisper_suspicious": "Подозрительная транскрипция: отдельные токены или повторы",
        "editor_tooltip_translation_fallback": "Резервный перевод: основной движок не сработал",
        "warn_editor": "Редактор",
        "label_url": "URL:",
        "btn_download": "⬇ Скачать и перевести",
        "url_placeholder": "Вставьте ссылку на YouTube (или другой сайт, поддерживаемый yt-dlp)...",
        "msg_no_url": "Вставьте хотя бы один действительный URL-адрес.",
        "msg_downloading": "⏳ Загрузка...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (локально, рекомендуется - лаконичные переводы для дубляжа)",
        "label_ollama_model": "Модель:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "По умолчанию: qwen3:8b (рекомендуется) - qwen3:4b лёгкий (~3 ГБ), qwen3:14b более высокое качество (~9 ГБ), qwen2.5:7b-instruct устаревший. Требуется установленный Ollama",
        "opt_ollama_thinking":  "🧠 Режим рассуждения (медленнее, переводы лучше)",
        "hint_ollama_thinking": "Обдумывает шаг за шагом, ~10x медленнее, но уменьшает ошибки идиом/грамматики",
        "msg_ollama_unavailable": (
            "Ollama недоступен. Для установки:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Затем загрузите модель:\n"
            "  ollama pull {model}\n"
            "\n"
            "Будет использован MarianMT/Google как резервный."
        ),
        "label_log_panel": "Журнал:",
        "btn_log_show": "▼ Показать журнал",
        "btn_log_hide": "▲ Скрыть журнал",
        "btn_log_copy": "Копировать",
        "btn_log_save": "Сохранить...",
        "btn_log_clear": "Очистить",
        "btn_preflight": "Диагностика",
        "msg_preflight_title": "Диагностика",
        "msg_preflight_ok": "Диагностика завершена. Отчёт в журнале.",
        "msg_preflight_failed": "Диагностика обнаружила проблемы, требующие внимания. Проверьте журнал.",
        "settings_title": "Настройки",
        "settings_appearance": "Внешний вид",
        "settings_theme": "Тема",
        "settings_accent": "Цвет акцента",
        "settings_text_size": "Размер текста",
        "settings_language": "Язык интерфейса",
        "theme_auto": "Автоматически (система)",
        "theme_light": "Светлая",
        "accent_default": "По умолчанию",
        "size_small": "Маленький",
        "size_normal": "Обычный",
        "size_large": "Крупный",
        "size_xlarge": "Очень крупный",
        "btn_close": "Закрыть",
        "btn_reset": "Восстановить настройки по умолчанию",
    },
    "es": {
        "label_video": "Video:",
        "label_output": "Producción:",
        "label_output_dir": "Carpeta de salida:",
        "label_from": "De:",
        "label_to": "A:",
        "label_voice": "Voz:",
        "label_tts_rate": "Velocidad TTS:",
        "panel_input": "Entrada",
        "panel_translation": "Traducción",
        "panel_profile": "Perfil de trabajo",
        "panel_start": "Inicio",
        "section_audio": "Audio",
        "section_voice_cloning": "Clonación de voz",
        "section_lip_sync": "Sincronización labial",
        "section_diarization": "Diarización",
        "section_model": "Modelo",
        "section_engine": "Motor de traducción",
        "section_subtitles": "Subtítulos",
        "section_hotwords": "Palabras clave",
        "label_model_hint": "← rápido / preciso → (turbo: calidad large-v3, ~6-8× más rápido en GPU)",
        "label_ui_lang": "Idioma de la interfaz de usuario:",
        "btn_add": "+ Agregar",
        "btn_remove": "- Eliminar",
        "btn_clear": "✗ Borrar",
        "btn_browse": "Navegar…",
        "btn_start": "▶ Iniciar traducción",
        "btn_processing": "⏳ Procesamiento...",
        "btn_transcribing": "⏳ Transcribiendo...",
        "btn_dubbing": "⏳ Doblaje...",
        "btn_installing": "⏳ Instalando...",
        "opt_subs_only": "Sólo subtítulos .srt (sin doblaje)",
        "opt_no_subs": "Sin subtítulos",
        "opt_no_demucs": "Saltar separación de voz/música (Demucs)",
        "opt_edit_subs": "Mostrar editor de subtítulos antes del doblaje",
        "opt_xtts": "Clonación de voz (Coqui XTTS v2 - primera ejecución: descargas ~1,8 GB)",
        "opt_lipsync": "Sincronización labial (Wav2Lip - primera ejecución: descarga ~416MB)",
        "label_engine": "Motor de traducción:",
        "engine_google": "Google (predeterminado)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Clave API de DeepL:",
        "opt_diarization": "Diarización de hablantes (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratuito: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Términos técnicos/marcas separados por comas (p. ej. Strix, pipx, Docker). Reduce los errores de Whisper en palabras raras ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Añade al menos un vídeo.",
        "msg_completed": "¡Traducción completada!",
        "msg_error": "Algo salió mal. Consulta el registro.",
        "msg_translation_unavailable": "La traducción ha fallado: Google Translate, usado como motor o como alternativa, ha bloqueado las solicitudes (límite alcanzado). Vuelve a intentarlo más tarde o usa MarianMT, DeepL u Ollama, comprobando que estén bien configurados.",
        "msg_translation_partial": "Segmentos no traducidos por el motor elegido: {n}. Se han quedado en el idioma original o tienen una traducción alternativa. Consulta el registro o revísalos en el editor de subtítulos.",
        "msg_confirm_stop": "Procesamiento en curso. ¿Detener?",
        "msg_confirm": "Confirmar",
        "msg_completed_t": "Terminado",
        "msg_error_t": "Error",
        "msg_deps_missing": "Dependencias faltantes",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg no encontrado. Por favor, instálalo.",
        "msg_deps_install": "¿Instalar automáticamente?",
        "msg_installed": "Paquetes instalados.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "No se transcriben segmentos.",
        "editor_title": "Editor de subtítulos",
        "editor_hint": "Revisar y corregir subtítulos antes del doblaje.",
        "editor_col_num": "#",
        "editor_col_start": "Comenzar",
        "editor_col_end": "Fin",
        "editor_col_orig": "Original",
        "editor_col_trans": "Traducción",
        "editor_btn_confirm": "✓ Confirmar y comenzar a doblar",
        "editor_btn_cancel": "✗ Cancelar",
        "editor_edit_title": "Editar",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Ahorrar",
        "editor_filter_show_flagged_only": "Mostrar solo segmentos a revisar",
        "editor_flag_summary": "Segmentos: {total}  ·  A revisar: {flagged} (longitud: {length}, transcripción: {whisper}, respaldo: {fallback})",
        "editor_tooltip_length_unfit": "Traducción demasiado larga: el audio se acelerará - acorta",
        "editor_tooltip_whisper_suspicious": "Transcripción sospechosa: tokens aislados o repeticiones",
        "editor_tooltip_translation_fallback": "Traducción de respaldo: el motor principal falló",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Descargar y traducir",
        "url_placeholder": "Pegue el enlace de YouTube (u otro sitio compatible con yt-dlp)...",
        "msg_no_url": "Pegue al menos una URL válida.",
        "msg_downloading": "⏳ Descargando...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recomendado - traducciones concisas para doblaje)",
        "label_ollama_model": "Modelo:",
        "label_ollama_url": "URL de Ollama:",
        "hint_ollama": "Por defecto: qwen3:8b (recomendado) - qwen3:4b ligero (~3 GB), qwen3:14b mayor calidad (~9 GB), qwen2.5:7b-instruct heredado. Requiere Ollama instalado",
        "opt_ollama_thinking":  "🧠 Modo de pensamiento (más lento, mejores traducciones)",
        "hint_ollama_thinking": "Delibera paso a paso, ~10x más lento pero reduce errores de modismos/gramática",
        "msg_ollama_unavailable": (
            "Ollama no disponible. Para instalar:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Luego descargue el modelo:\n"
            "  ollama pull {model}\n"
            "\n"
            "Se usará MarianMT/Google como alternativa."
        ),
        "label_log_panel": "Registro:",
        "btn_log_show": "▼ Mostrar registro",
        "btn_log_hide": "▲ Ocultar registro",
        "btn_log_copy": "Copiar",
        "btn_log_save": "Guardar...",
        "btn_log_clear": "Borrar",
        "btn_preflight": "Diagnóstico",
        "msg_preflight_title": "Diagnóstico",
        "msg_preflight_ok": "Diagnóstico completado. Informe en el registro.",
        "msg_preflight_failed": "El diagnóstico encontró problemas que requieren atención. Consulta el registro.",
        "settings_title": "Configuración",
        "settings_appearance": "Apariencia",
        "settings_theme": "Tema",
        "settings_accent": "Color de acento",
        "settings_text_size": "Tamaño del texto",
        "settings_language": "Idioma de la interfaz",
        "theme_auto": "Automático (sistema)",
        "theme_light": "Claro",
        "accent_default": "Predeterminado",
        "size_small": "Pequeño",
        "size_normal": "Normal",
        "size_large": "Grande",
        "size_xlarge": "Muy grande",
        "btn_close": "Cerrar",
        "btn_reset": "Restablecer valores predeterminados",
    },
    "sv": {
        "label_video": "Video:",
        "label_output": "Produktion:",
        "label_output_dir": "Utdatamapp:",
        "label_from": "Från:",
        "label_to": "Till:",
        "label_voice": "Röst:",
        "label_tts_rate": "TTS hastighet:",
        "panel_input": "Indata",
        "panel_translation": "Översättning",
        "panel_profile": "Arbetsprofil",
        "panel_start": "Start",
        "section_audio": "Ljud",
        "section_voice_cloning": "Röstkloning",
        "section_lip_sync": "Läppsynk",
        "section_diarization": "Talaridentifiering",
        "section_model": "Modell",
        "section_engine": "Översättningsmotor",
        "section_subtitles": "Undertexter",
        "section_hotwords": "Nyckelord",
        "label_model_hint": "← snabb / exakt → (turbo: large-v3-kvalitet, ~6-8× snabbare på GPU)",
        "label_ui_lang": "UI-språk:",
        "btn_add": "+ Lägg till",
        "btn_remove": "- Ta bort",
        "btn_clear": "✗ Tydlig",
        "btn_browse": "Bläddra…",
        "btn_start": "▶ Starta översättning",
        "btn_processing": "⏳ Bearbetar...",
        "btn_transcribing": "⏳ Transkriberar...",
        "btn_dubbing": "⏳ Dubbning...",
        "btn_installing": "⏳ Installerar...",
        "opt_subs_only": "Endast undertexter .srt (ingen dubbning)",
        "opt_no_subs": "Inga undertexter",
        "opt_no_demucs": "Hoppa över röst-/musikseparation (Demucs)",
        "opt_edit_subs": "Visa undertextredigerare före dubbning",
        "opt_xtts": "Röstkloning (Coqui XTTS v2 - första körningen: nedladdningar ~1,8 GB)",
        "opt_lipsync": "Läppsynk (Wav2Lip - första körningen: laddar ner ~416MB)",
        "label_engine": "Översättningsmotor:",
        "engine_google": "Google (standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-nyckel:",
        "opt_diarization": "Talaridentifiering (pyannote)",
        "label_hf_token": "HF-token:",
        "hint_hf_token": "Gratis HF-token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Kommaseparerade tekniska termer/varumärken (t.ex. Strix, pipx, Docker). Minskar Whisper-fel på sällsynta ord med ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Lägg till minst en video.",
        "msg_completed": "Översättningen klar!",
        "msg_error": "Något gick fel. Kontrollera loggen.",
        "msg_translation_unavailable": "Översättningen misslyckades: Google Translate, som användes som motor eller som reserv, blockerade förfrågningarna (gränsen nådd). Försök igen senare eller använd MarianMT, DeepL eller Ollama och kontrollera att de är rätt konfigurerade.",
        "msg_translation_partial": "Segment som den valda motorn inte översatte: {n}. De är kvar på originalspråket eller har en reservöversättning. Kontrollera loggen eller granska dem i undertextredigeraren.",
        "msg_confirm_stop": "Bearbetning pågår. Stopp?",
        "msg_confirm": "Bekräfta",
        "msg_completed_t": "Avslutad",
        "msg_error_t": "Fel",
        "msg_deps_missing": "Saknade beroenden",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg hittades inte. Installera det.",
        "msg_deps_install": "Installera automatiskt?",
        "msg_installed": "Paket installerade.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Inga segment har transkriberats.",
        "editor_title": "Undertextredigerare",
        "editor_hint": "Granska och korrigera undertexter före dubbning",
        "editor_col_num": "#",
        "editor_col_start": "Start",
        "editor_col_end": "Avsluta",
        "editor_col_orig": "Original",
        "editor_col_trans": "Översättning",
        "editor_btn_confirm": "✓ Bekräfta och börja dubba",
        "editor_btn_cancel": "✗ Avbryt",
        "editor_edit_title": "Redigera",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Spara",
        "editor_filter_show_flagged_only": "Visa endast segment att granska",
        "editor_flag_summary": "Segment: {total}  ·  Att granska: {flagged} (längd: {length}, transkription: {whisper}, reserv: {fallback})",
        "editor_tooltip_length_unfit": "Översättningen är för lång: ljudet kommer att snabbas upp - förkorta",
        "editor_tooltip_whisper_suspicious": "Misstänkt transkription: isolerade token eller upprepningar",
        "editor_tooltip_translation_fallback": "Reservöversättning: huvudmotorn misslyckades",
        "warn_editor": "Redaktör",
        "label_url": "URL:",
        "btn_download": "⬇ Ladda ner och översätt",
        "url_placeholder": "Klistra in YouTube-länk (eller annan webbplats som stöds av yt-dlp)...",
        "msg_no_url": "Klistra in minst en giltig webbadress.",
        "msg_downloading": "⏳ Laddar ner...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, rekommenderas - koncisa översättningar för dubbning)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Standard: qwen3:8b (rekommenderas) - qwen3:4b lätt (~3 GB), qwen3:14b högre kvalitet (~9 GB), qwen2.5:7b-instruct äldre. Kräver installerat Ollama",
        "opt_ollama_thinking":  "🧠 Tänkeläge (långsammare, bättre översättningar)",
        "hint_ollama_thinking": "Överväger steg för steg, ~10x långsammare men minskar idiom-/grammatikfel",
        "msg_ollama_unavailable": (
            "Ollama inte tillgänglig. För att installera:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Hämta sedan modellen:\n"
            "  ollama pull {model}\n"
            "\n"
            "Faller tillbaka på MarianMT/Google."
        ),
        "label_log_panel": "Logg:",
        "btn_log_show": "▼ Visa logg",
        "btn_log_hide": "▲ Dölj logg",
        "btn_log_copy": "Kopiera",
        "btn_log_save": "Spara...",
        "btn_log_clear": "Rensa",
        "btn_preflight": "Diagnostik",
        "msg_preflight_title": "Diagnostik",
        "msg_preflight_ok": "Diagnostik klar. Rapport i loggen.",
        "msg_preflight_failed": "Diagnostiken hittade problem som måste åtgärdas. Kontrollera loggen.",
        "settings_title": "Inställningar",
        "settings_appearance": "Utseende",
        "settings_theme": "Tema",
        "settings_accent": "Accentfärg",
        "settings_text_size": "Textstorlek",
        "settings_language": "Gränssnittsspråk",
        "theme_auto": "Automatisk (system)",
        "theme_light": "Ljust",
        "accent_default": "Standard",
        "size_small": "Liten",
        "size_normal": "Normal",
        "size_large": "Stor",
        "size_xlarge": "Mycket stor",
        "btn_close": "Stäng",
        "btn_reset": "Återställ standardinställningar",
    },
    "tr": {
        "label_video": "Video:",
        "label_output": "Çıkış:",
        "label_output_dir": "Çıktı klasörü:",
        "label_from": "İtibaren:",
        "label_to": "İle:",
        "label_voice": "Ses:",
        "label_tts_rate": "TTS Hızı:",
        "panel_input": "Giriş",
        "panel_translation": "Çeviri",
        "panel_profile": "İş akışı profili",
        "panel_start": "Başlat",
        "section_audio": "Ses",
        "section_voice_cloning": "Ses Klonlama",
        "section_lip_sync": "Dudak Senkronu",
        "section_diarization": "Konuşmacı ayrıştırma",
        "section_model": "Model",
        "section_engine": "Çeviri motoru",
        "section_subtitles": "Altyazılar",
        "section_hotwords": "Anahtar kelimeler",
        "label_model_hint": "← hızlı / doğru → (turbo: large-v3 kalitesi, GPU'da ~6-8× daha hızlı)",
        "label_ui_lang": "Kullanıcı Arayüzü Dili:",
        "btn_add": "+ Ekle",
        "btn_remove": "- Kaldırmak",
        "btn_clear": "✗ Temizle",
        "btn_browse": "Göz at…",
        "btn_start": "▶ Çeviriyi Başlat",
        "btn_processing": "⏳ İşleniyor...",
        "btn_transcribing": "⏳ Yazıya aktarılıyor...",
        "btn_dubbing": "⏳ Dublaj...",
        "btn_installing": "⏳ Yükleniyor...",
        "opt_subs_only": "Yalnızca altyazılar .srt (dublaj yok)",
        "opt_no_subs": "Altyazı yok",
        "opt_no_demucs": "Ses/müzik ayrımını atla (Demucs)",
        "opt_edit_subs": "Dublajdan önce altyazı düzenleyiciyi göster",
        "opt_xtts": "Ses Klonlama (Coqui XTTS v2 - ilk çalıştırma: indirmeler ~1,8 GB)",
        "opt_lipsync": "Dudak Senkronu (Wav2Lip - ilk çalıştırma: ~416MB indirme)",
        "label_engine": "Çeviri motoru:",
        "engine_google": "Google (varsayılan)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (yerel)",
        "label_deepl_key": "DeepL API anahtarı:",
        "opt_diarization": "Konuşmacı ayrıştırma (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Ücretsiz HF token: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Virgülle ayrılmış teknik terimler/marka adları (örn. Strix, pipx, Docker). Nadir kelimelerde Whisper hatalarını ~%43 azaltır",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "En az bir video ekleyin.",
        "msg_completed": "Çeviri tamamlandı!",
        "msg_error": "Bir şeyler ters gitti. Günlüğü kontrol edin.",
        "msg_translation_unavailable": "Çeviri başarısız: motor veya yedek olarak kullanılan Google Translate istekleri engelledi (sınıra ulaşıldı). Daha sonra tekrar deneyin veya doğru yapılandırıldıklarından emin olarak MarianMT, DeepL ya da Ollama'yı kullanın.",
        "msg_translation_partial": "Seçilen motorun çeviremediği segmentler: {n}. Orijinal dilde kaldılar veya yedek bir çeviriye sahipler. Günlüğü kontrol edin veya altyazı düzenleyicisinde gözden geçirin.",
        "msg_confirm_stop": "İşleme devam ediyor. Durmak?",
        "msg_confirm": "Onaylamak",
        "msg_completed_t": "Tamamlanmış",
        "msg_error_t": "Hata",
        "msg_deps_missing": "Eksik bağımlılıklar",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg bulunamadı. Lütfen yükleyin.",
        "msg_deps_install": "Otomatik olarak yüklensin mi?",
        "msg_installed": "Paketler kuruldu.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Hiçbir bölüm yazıya geçirilmedi.",
        "editor_title": "Altyazı Düzenleyici",
        "editor_hint": "Dublajdan önce altyazıları inceleyin ve düzeltin",
        "editor_col_num": "#",
        "editor_col_start": "Başlangıç",
        "editor_col_end": "Son",
        "editor_col_orig": "Orijinal",
        "editor_col_trans": "Çeviri",
        "editor_btn_confirm": "✓ Onaylayın ve dublajı başlatın",
        "editor_btn_cancel": "✗ İptal",
        "editor_edit_title": "Düzenlemek",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Kaydetmek",
        "editor_filter_show_flagged_only": "Yalnızca incelenecek segmentleri göster",
        "editor_flag_summary": "Segmentler: {total}  ·  İncelenecek: {flagged} (uzunluk: {length}, transkripsiyon: {whisper}, yedek: {fallback})",
        "editor_tooltip_length_unfit": "Çeviri çok uzun: ses hızlandırılacak - kısaltın",
        "editor_tooltip_whisper_suspicious": "Şüpheli transkripsiyon: yalıtık jetonlar veya tekrarlar",
        "editor_tooltip_translation_fallback": "Yedek çeviri: ana motor başarısız oldu",
        "warn_editor": "Editör",
        "label_url": "URL:",
        "btn_download": "⬇ İndir ve Çevir",
        "url_placeholder": "YouTube bağlantısını (veya yt-dlp destekli başka bir siteyi) yapıştırın...",
        "msg_no_url": "En az bir geçerli URL yapıştırın.",
        "msg_downloading": "⏳ İndiriliyor...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (yerel, önerilen - dublaj için özlü çeviriler)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Varsayılan: qwen3:8b (önerilen) - qwen3:4b hafif (~3 GB), qwen3:14b daha yüksek kalite (~9 GB), qwen2.5:7b-instruct eski. Ollama kurulu olmasını gerektirir",
        "opt_ollama_thinking":  "🧠 Düşünme modu (daha yavaş, daha iyi çeviriler)",
        "hint_ollama_thinking": "Adım adım değerlendirir, ~10x daha yavaş ancak deyim/dilbilgisi hatalarını azaltır",
        "msg_ollama_unavailable": (
            "Ollama mevcut değil. Kurulum için:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Ardından modeli indirin:\n"
            "  ollama pull {model}\n"
            "\n"
            "MarianMT/Google'a geri dönülecek."
        ),
        "label_log_panel": "Günlük:",
        "btn_log_show": "▼ Günlüğü göster",
        "btn_log_hide": "▲ Günlüğü gizle",
        "btn_log_copy": "Kopyala",
        "btn_log_save": "Kaydet...",
        "btn_log_clear": "Temizle",
        "btn_preflight": "Tanılama",
        "msg_preflight_title": "Tanılama",
        "msg_preflight_ok": "Tanılama tamamlandı. Rapor günlükte.",
        "msg_preflight_failed": "Tanılama, giderilmesi gereken sorunlar buldu. Günlüğü kontrol edin.",
        "settings_title": "Ayarlar",
        "settings_appearance": "Görünüm",
        "settings_theme": "Tema",
        "settings_accent": "Vurgu rengi",
        "settings_text_size": "Metin boyutu",
        "settings_language": "Arayüz dili",
        "theme_auto": "Otomatik (sistem)",
        "theme_light": "Açık",
        "accent_default": "Varsayılan",
        "size_small": "Küçük",
        "size_normal": "Normal",
        "size_large": "Büyük",
        "size_xlarge": "Çok büyük",
        "btn_close": "Kapat",
        "btn_reset": "Varsayılanlara sıfırla",
    },
    "uk": {
        "label_video": "Відео:",
        "label_output": "Вихід:",
        "label_output_dir": "Тека виводу:",
        "label_from": "Від:",
        "label_to": "до:",
        "label_voice": "Голос:",
        "label_tts_rate": "Швидкість TTS:",
        "panel_input": "Вхід",
        "panel_translation": "Переклад",
        "panel_profile": "Профіль роботи",
        "panel_start": "Запуск",
        "section_audio": "Аудіо",
        "section_voice_cloning": "Клонування голосу",
        "section_lip_sync": "Синхронізація губ",
        "section_diarization": "Розділення дикторів",
        "section_model": "Модель",
        "section_engine": "Рушій перекладу",
        "section_subtitles": "Субтитри",
        "section_hotwords": "Ключові слова",
        "label_model_hint": "← швидко / точно → (turbo: якість large-v3, ~6-8× швидше на GPU)",
        "label_ui_lang": "Мова інтерфейсу користувача:",
        "btn_add": "+ Додати",
        "btn_remove": "- Зняти",
        "btn_clear": "✗ Ясно",
        "btn_browse": "Перегляд…",
        "btn_start": "▶ Розпочніть переклад",
        "btn_processing": "⏳ Обробка...",
        "btn_transcribing": "⏳ Транскрибування...",
        "btn_dubbing": "⏳ Дубляж...",
        "btn_installing": "⏳ Встановлення...",
        "opt_subs_only": "Лише субтитри .srt (без дубляжу)",
        "opt_no_subs": "Без субтитрів",
        "opt_no_demucs": "Пропустити розділення голосу та музики (Demucs)",
        "opt_edit_subs": "Показати редактор субтитрів перед дубляжем",
        "opt_xtts": "Клонування голосу (Coqui XTTS v2 - перший запуск: завантаження ~1,8 ГБ)",
        "opt_lipsync": "Синхронізація губ (Wav2Lip - перший запуск: завантаження ~416МБ)",
        "label_engine": "Рушій перекладу:",
        "engine_google": "Google (типовий)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (локально)",
        "label_deepl_key": "Ключ API DeepL:",
        "opt_diarization": "Розділення дикторів (pyannote)",
        "label_hf_token": "Токен HF:",
        "hint_hf_token": "Безкоштовний токен HF: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Технічні терміни/назви брендів через кому (напр. Strix, pipx, Docker). Зменшує помилки Whisper на рідкісних словах на ~43%",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Додайте хоча б одне відео.",
        "msg_completed": "Переклад завершено!",
        "msg_error": "Щось пішло не так. Перевірте журнал.",
        "msg_translation_unavailable": "Переклад не вдався: Google Translate, використаний як рушій або як резервний варіант, заблокував запити (досягнуто ліміту). Спробуйте пізніше або скористайтеся MarianMT, DeepL чи Ollama, перевіривши, що їх правильно налаштовано.",
        "msg_translation_partial": "Сегменти, не перекладені вибраним рушієм: {n}. Вони залишилися мовою оригіналу або мають резервний переклад. Перевірте журнал або перегляньте їх у редакторі субтитрів.",
        "msg_confirm_stop": "Триває обробка. СТІЙ?",
        "msg_confirm": "Підтвердити",
        "msg_completed_t": "Виконано",
        "msg_error_t": "Помилка",
        "msg_deps_missing": "Відсутні залежності",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nffmpeg не знайдено. Будь ласка, встановіть його.",
        "msg_deps_install": "Встановити автоматично?",
        "msg_installed": "Встановлені пакети.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Немає транскрибованих сегментів.",
        "editor_title": "Редактор субтитрів",
        "editor_hint": "Перегляньте та виправте субтитри перед дубляжем",
        "editor_col_num": "#",
        "editor_col_start": "старт",
        "editor_col_end": "Кінець",
        "editor_col_orig": "Оригінал",
        "editor_col_trans": "Переклад",
        "editor_btn_confirm": "✓ Підтвердьте та почніть дубляж",
        "editor_btn_cancel": "✗ Скасувати",
        "editor_edit_title": "Редагувати",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "зберегти",
        "editor_filter_show_flagged_only": "Показувати лише сегменти для перевірки",
        "editor_flag_summary": "Сегменти: {total}  ·  До перевірки: {flagged} (довжина: {length}, транскрипція: {whisper}, резерв: {fallback})",
        "editor_tooltip_length_unfit": "Переклад задовгий: аудіо буде прискорено - скоротіть",
        "editor_tooltip_whisper_suspicious": "Підозріла транскрипція: ізольовані токени або повтори",
        "editor_tooltip_translation_fallback": "Резервний переклад: основний рушій зазнав збою",
        "warn_editor": "редактор",
        "label_url": "URL:",
        "btn_download": "⬇ Завантажте та перекладіть",
        "url_placeholder": "Вставте посилання YouTube (або інший сайт, що підтримує yt-dlp)...",
        "msg_no_url": "Вставте принаймні одну дійсну URL-адресу.",
        "msg_downloading": "⏳ Завантаження...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (локально, рекомендовано - лаконічні переклади для дубляжу)",
        "label_ollama_model": "Модель:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "За замовчуванням: qwen3:8b (рекомендовано) - qwen3:4b легка (~3 ГБ), qwen3:14b вища якість (~9 ГБ), qwen2.5:7b-instruct застаріла. Потрібен встановлений Ollama",
        "opt_ollama_thinking":  "🧠 Режим міркування (повільніше, кращі переклади)",
        "hint_ollama_thinking": "Обмірковує крок за кроком, ~10x повільніше, але зменшує помилки ідіом/граматики",
        "msg_ollama_unavailable": (
            "Ollama недоступний. Для встановлення:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Потім завантажте модель:\n"
            "  ollama pull {model}\n"
            "\n"
            "Буде використано MarianMT/Google як резервний варіант."
        ),
        "label_log_panel": "Журнал:",
        "btn_log_show": "▼ Показати журнал",
        "btn_log_hide": "▲ Сховати журнал",
        "btn_log_copy": "Копіювати",
        "btn_log_save": "Зберегти...",
        "btn_log_clear": "Очистити",
        "btn_preflight": "Діагностика",
        "msg_preflight_title": "Діагностика",
        "msg_preflight_ok": "Діагностику завершено. Звіт у журналі.",
        "msg_preflight_failed": "Діагностика виявила проблеми, що потребують уваги. Перевірте журнал.",
        "settings_title": "Налаштування",
        "settings_appearance": "Зовнішній вигляд",
        "settings_theme": "Тема",
        "settings_accent": "Колір акценту",
        "settings_text_size": "Розмір тексту",
        "settings_language": "Мова інтерфейсу",
        "theme_auto": "Автоматично (система)",
        "theme_light": "Світла",
        "accent_default": "Типовий",
        "size_small": "Малий",
        "size_normal": "Звичайний",
        "size_large": "Великий",
        "size_xlarge": "Дуже великий",
        "btn_close": "Закрити",
        "btn_reset": "Відновити типові налаштування",
    },
    "vi": {
        "label_video": "Băng hình:",
        "label_output": "Đầu ra:",
        "label_output_dir": "Thư mục đầu ra:",
        "label_from": "Từ:",
        "label_to": "ĐẾN:",
        "label_voice": "Tiếng nói:",
        "label_tts_rate": "Tốc độ TTS:",
        "panel_input": "Đầu vào",
        "panel_translation": "Dịch thuật",
        "panel_profile": "Hồ sơ làm việc",
        "panel_start": "Bắt đầu",
        "section_audio": "Âm thanh",
        "section_voice_cloning": "Nhân bản giọng nói",
        "section_lip_sync": "Đồng bộ môi",
        "section_diarization": "Phân tách người nói",
        "section_model": "Mô hình",
        "section_engine": "Công cụ dịch",
        "section_subtitles": "Phụ đề",
        "section_hotwords": "Từ khóa",
        "label_model_hint": "← nhanh / chính xác → (turbo: chất lượng large-v3, ~6-8× nhanh hơn trên GPU)",
        "label_ui_lang": "Ngôn ngữ giao diện người dùng:",
        "btn_add": "+ Thêm",
        "btn_remove": "- Di dời",
        "btn_clear": "✗ Rõ ràng",
        "btn_browse": "Duyệt…",
        "btn_start": "▶ Bắt đầu dịch",
        "btn_processing": "⏳ Đang xử lý...",
        "btn_transcribing": "⏳ Phiên âm...",
        "btn_dubbing": "⏳ Lồng tiếng...",
        "btn_installing": "⏳ Đang cài đặt...",
        "opt_subs_only": "Chỉ có phụ đề .srt (không lồng tiếng)",
        "opt_no_subs": "Không có phụ đề",
        "opt_no_demucs": "Bỏ qua việc tách giọng/nhạc (Demucs)",
        "opt_edit_subs": "Hiển thị trình chỉnh sửa phụ đề trước khi lồng tiếng",
        "opt_xtts": "Nhân bản giọng nói (Coqui XTTS v2 - lần chạy đầu tiên: tải xuống ~1,8GB)",
        "opt_lipsync": "Đồng bộ môi (Wav2Lip - chạy lần đầu: tải ~416MB)",
        "label_engine": "Công cụ dịch:",
        "engine_google": "Google (mặc định)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (cục bộ)",
        "label_deepl_key": "Khóa API DeepL:",
        "opt_diarization": "Phân tách người nói (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF miễn phí: huggingface.co/settings/tokens",
        "label_hotwords": "Hotwords:",
        "hint_hotwords": "Các thuật ngữ kỹ thuật/thương hiệu phân tách bằng dấu phẩy (ví dụ: Strix, pipx, Docker). Giảm ~43% lỗi Whisper với các từ hiếm",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Thêm ít nhất một video.",
        "msg_completed": "Bản dịch đã hoàn tất!",
        "msg_error": "Đã xảy ra lỗi. Kiểm tra nhật ký.",
        "msg_translation_unavailable": "Dịch thất bại: Google Translate, được dùng làm công cụ chính hoặc dự phòng, đã chặn các yêu cầu (đạt giới hạn). Hãy thử lại sau hoặc dùng MarianMT, DeepL hoặc Ollama và kiểm tra rằng chúng được cấu hình đúng.",
        "msg_translation_partial": "Số đoạn không được công cụ đã chọn dịch: {n}. Các đoạn này vẫn ở ngôn ngữ gốc hoặc dùng bản dịch dự phòng. Hãy kiểm tra nhật ký hoặc xem lại chúng trong trình chỉnh sửa phụ đề.",
        "msg_confirm_stop": "Đang xử lý. Dừng lại?",
        "msg_confirm": "Xác nhận",
        "msg_completed_t": "Hoàn thành",
        "msg_error_t": "Lỗi",
        "msg_deps_missing": "Thiếu phần phụ thuộc",
        "msg_deps_python": "Missing Python packages:\n  • ",
        "msg_deps_bins": "Missing programs:\n  • ",
        "msg_deps_ffmpeg": "\n\nKhông tìm thấy ffmpeg. Vui lòng cài đặt.",
        "msg_deps_install": "Cài đặt tự động?",
        "msg_installed": "Các gói đã được cài đặt.",
        "msg_install_failed": "Installation failed:\n{}",
        "msg_no_segments": "Không có phân đoạn nào được phiên âm.",
        "editor_title": "Trình chỉnh sửa phụ đề",
        "editor_hint": "Xem lại và sửa phụ đề trước khi lồng tiếng",
        "editor_col_num": "#",
        "editor_col_start": "Bắt đầu",
        "editor_col_end": "Kết thúc",
        "editor_col_orig": "Nguyên bản",
        "editor_col_trans": "Dịch thuật",
        "editor_btn_confirm": "✓ Xác nhận và bắt đầu lồng tiếng",
        "editor_btn_cancel": "✗ Hủy",
        "editor_edit_title": "Biên tập",
        "editor_seg_label": "Segment {} -",
        "editor_btn_save": "Cứu",
        "editor_filter_show_flagged_only": "Chỉ hiển thị các đoạn cần xem lại",
        "editor_flag_summary": "Đoạn: {total}  ·  Cần xem lại: {flagged} (độ dài: {length}, phiên âm: {whisper}, dự phòng: {fallback})",
        "editor_tooltip_length_unfit": "Bản dịch quá dài: âm thanh sẽ bị tăng tốc - rút gọn",
        "editor_tooltip_whisper_suspicious": "Phiên âm đáng ngờ: token riêng lẻ hoặc lặp lại",
        "editor_tooltip_translation_fallback": "Bản dịch dự phòng: engine chính thất bại",
        "warn_editor": "Biên tập viên",
        "label_url": "URL:",
        "btn_download": "⬇ Tải xuống và dịch",
        "url_placeholder": "Dán liên kết YouTube (hoặc trang web hỗ trợ yt-dlp khác)...",
        "msg_no_url": "Dán ít nhất một URL hợp lệ.",
        "msg_downloading": "⏳ Đang tải xuống...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (cục bộ, khuyến nghị - bản dịch ngắn gọn cho lồng tiếng)",
        "label_ollama_model": "Mô hình:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Mặc định: qwen3:8b (khuyến nghị) - qwen3:4b nhẹ (~3 GB), qwen3:14b chất lượng cao hơn (~9 GB), qwen2.5:7b-instruct cũ. Yêu cầu đã cài Ollama",
        "opt_ollama_thinking":  "🧠 Chế độ tư duy (chậm hơn, dịch tốt hơn)",
        "hint_ollama_thinking": "Cân nhắc từng bước, chậm ~10x nhưng giảm lỗi thành ngữ/ngữ pháp",
        "msg_ollama_unavailable": (
            "Ollama không khả dụng. Để cài đặt:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh   (Linux/macOS)\n"
            "  https://ollama.com/download                      (Windows)\n"
            "\n"
            "Sau đó tải mô hình:\n"
            "  ollama pull {model}\n"
            "\n"
            "Sẽ chuyển sang MarianMT/Google."
        ),
        "label_log_panel": "Nhật ký:",
        "btn_log_show": "▼ Hiển thị nhật ký",
        "btn_log_hide": "▲ Ẩn nhật ký",
        "btn_log_copy": "Sao chép",
        "btn_log_save": "Lưu...",
        "btn_log_clear": "Xóa",
        "btn_preflight": "Chẩn đoán",
        "msg_preflight_title": "Chẩn đoán",
        "msg_preflight_ok": "Đã hoàn tất chẩn đoán. Báo cáo trong nhật ký.",
        "msg_preflight_failed": "Chẩn đoán phát hiện các vấn đề cần xử lý. Kiểm tra nhật ký.",
        "settings_title": "Cài đặt",
        "settings_appearance": "Giao diện",
        "settings_theme": "Chủ đề",
        "settings_accent": "Màu nhấn",
        "settings_text_size": "Kích thước văn bản",
        "settings_language": "Ngôn ngữ giao diện",
        "theme_auto": "Tự động (hệ thống)",
        "theme_light": "Sáng",
        "accent_default": "Mặc định",
        "size_small": "Nhỏ",
        "size_normal": "Bình thường",
        "size_large": "Lớn",
        "size_xlarge": "Rất lớn",
        "btn_close": "Đóng",
        "btn_reset": "Đặt lại về mặc định",
    },

# ── UI_LANG_OPTIONS ──
}

UI_LANG_OPTIONS = [
    ("it", "🇮🇹 Italiano"),
    ("en", "🇬🇧 English"),
    ("ar", "🇸🇦 العربية"),
    ("zh", "🇨🇳 中文"),
    ("cs", "🇨🇿 Čeština"),
    ("da", "🇩🇰 Dansk"),
    ("nl", "🇳🇱 Nederlands"),
    ("fi", "🇫🇮 Suomi"),
    ("fr", "🇫🇷 Français"),
    ("de", "🇩🇪 Deutsch"),
    ("el", "🇬🇷 Ελληνικά"),
    ("hi", "🇮🇳 हिन्दी"),
    ("hu", "🇭🇺 Magyar"),
    ("id", "🇮🇩 Indonesia"),
    ("ja", "🇯🇵 日本語"),
    ("ko", "🇰🇷 한국어"),
    ("no", "🇳🇴 Norsk"),
    ("pl", "🇵🇱 Polski"),
    ("pt", "🇧🇷 Português"),
    ("ro", "🇷🇴 Română"),
    ("ru", "🇷🇺 Русский"),
    ("es", "🇪🇸 Español"),
    ("sv", "🇸🇪 Svenska"),
    ("tr", "🇹🇷 Türkçe"),
    ("uk", "🇺🇦 Українська"),
    ("vi", "🇻🇳 Tiếng Việt"),
]
UI_LANG_CODES = {code for code, _ in UI_LANG_OPTIONS}

# Player and live-mode strings live in their own module (spec 2.6, Q5) and are
# merged here, so UI_STRINGS stays the single runtime dictionary. merge_into
# never raises: problems are logged at startup and caught by the i18n tests.
from videotranslator.ui_strings_player import merge_into as _merge_player_strings  # noqa: E402
_PLAYER_STRING_PROBLEMS = _merge_player_strings(UI_STRINGS)


# ═══════════════════════════════════════════════════════════
#  PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════

from videotranslator.media import run_ffmpeg as _run_ffmpeg  # noqa: E402


def download_youtube(url: str, out_dir: str) -> str:
    """Downloads a video from YouTube (or any yt-dlp supported site) to out_dir.
    Returns the path of the downloaded file."""
    from videotranslator.input_source import download_url

    return download_url(url, out_dir, log_cb=lambda msg: print(msg, flush=True))


def extract_audio(video_path: str, audio_path: str):
    from videotranslator.media import extract_audio as _extract_audio

    _extract_audio(
        video_path,
        audio_path,
        log_cb=lambda msg: print(msg, flush=True),
        runner=_run_ffmpeg,
    )


def separate_audio(audio_path: str, tmp_dir: str) -> tuple[str, str]:
    """Separates voice and music with Demucs htdemucs. Returns (vocals_path, background_path)."""
    from videotranslator.media import separate_audio as _separate_audio

    return _separate_audio(
        audio_path,
        tmp_dir,
        log_cb=lambda msg: print(msg, flush=True),
        ffmpeg_runner=_run_ffmpeg,
    )


def transcribe(
    audio_path: str,
    model_name: str,
    lang_source: str,
    hotwords: list[str] | None = None,
) -> tuple[list[dict], str]:
    from videotranslator.transcription import transcribe_audio

    return transcribe_audio(
        audio_path,
        model_name,
        lang_source,
        hotwords,
        log_cb=lambda msg: print(msg, flush=True),
    )


from videotranslator.platforms import (  # noqa: E402
    default_videos_dir as _default_videos_dir,
    windows_known_videos_dir as _windows_known_videos_dir,
)


# Strong sentence-ending punctuation - ASCII + CJK full-width + Arabic question mark.
# Used by _split_on_punctuation to re-align Whisper segments at natural
# syntactic boundaries, including Chinese/Japanese/Arabic.
_END_PUNCT_CHARS = r".?!;。？！；؟"
_END_PUNCT_SET = frozenset(_END_PUNCT_CHARS)


def _split_on_punctuation(
    segments: list[dict],
    min_duration: float = 1.0,
) -> list[dict]:
    """Re-splits each Whisper segment on strong punctuation (. ? ! ; 。 ？ ！ ； ؟),
    optionally followed by whitespace. Timestamps are re-proportioned by
    character count. Does not split on commas. Does not produce sub-segments
    shorter than min_duration. Preserves 'speaker' if present.

    The lookahead is `\\S` (non-space): this also handles scripts that do not
    separate sentences with a space (Chinese, Japanese). For Latin scripts the
    "uppercase/digit" filter on the next character preserves previous behaviour;
    for CJK/Arabic any non-punctuation character is treated as a valid boundary
    (those scripts have no case distinction).

    Reduces XTTS hallucinations by feeding complete sentences instead of
    mid-sentence cuts.
    """
    import re as _re
    pattern = _re.compile(
        rf"([{_re.escape(_END_PUNCT_CHARS)}]+)(\s*)(?=\S)"
    )

    out: list[dict] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        start = float(seg["start"])
        end = float(seg["end"])
        duration = max(end - start, 1e-6)
        if not text or duration < 2 * min_duration:
            out.append(seg)
            continue

        # Build list of candidate cut positions.
        cuts: list[int] = []
        for m in pattern.finditer(text):
            next_idx = m.end()
            if next_idx < len(text):
                next_ch = text[next_idx]
                ws_between = m.group(2)  # whitespace consumed between punct and next_ch
                # Latin scripts: require (mandatory whitespace) AND
                # (uppercase/digit) to avoid splitting on abbreviations
                # ("U.S.", "e.g.", "p.m."), where there is zero whitespace
                # between the dot and the next letter. This replicates the
                # old `\\s+` behaviour for the Latin script.
                # Non-latin (CJK, Arabic, …): any non-punct character is
                # acceptable even without whitespace, because those scripts
                # have no case distinction and often do not separate sentences
                # with a space (Japanese, Chinese).
                is_latin = next_ch.isascii() and next_ch.isalpha()
                # Non-latin gate on `not isascii()`: an ASCII digit/punct
                # after an ASCII dot always belongs to Latin text (decimals
                # "3.14", closing quotes "'yes.'") and must not be a
                # cut-point. Only truly non-ASCII characters (CJK, Arabic,
                # Devanagari, etc.) benefit from `\\s*` (optional whitespace)
                # because those scripts do not separate sentences with a space.
                if is_latin:
                    if ws_between and next_ch.isupper():
                        cuts.append(next_idx)
                elif not next_ch.isascii():
                    cuts.append(next_idx)
        if not cuts:
            out.append(seg)
            continue

        # Build sub-sentences and character-proportional timestamps.
        pieces: list[tuple[str, int]] = []  # (piece_text, char_end_abs)
        prev = 0
        for c in cuts:
            piece = text[prev:c].strip()
            if piece:
                pieces.append((piece, c))
            prev = c
        tail = text[prev:].strip()
        if tail:
            pieces.append((tail, len(text)))

        if len(pieces) <= 1:
            out.append(seg)
            continue

        total_chars = len(text)
        sub_segments: list[dict] = []
        prev_char = 0
        for piece_text, char_end in pieces:
            sub_start = start + duration * (prev_char / total_chars)
            sub_end = start + duration * (char_end / total_chars)
            if sub_end - sub_start < min_duration:
                # Instead of creating a useless micro-segment, merge with the
                # previous one (if it exists) or fall back to the original
                # segment if no split makes sense.
                if sub_segments:
                    sub_segments[-1]["end"] = sub_end
                    sub_segments[-1]["text"] = (sub_segments[-1]["text"] + " " + piece_text).strip()
                    prev_char = char_end
                    continue
                else:
                    sub_segments = []
                    break
            new_seg = {"start": sub_start, "end": sub_end, "text": piece_text}
            if "speaker" in seg:
                new_seg["speaker"] = seg["speaker"]
            sub_segments.append(new_seg)
            prev_char = char_end

        if sub_segments and len(sub_segments) > 1:
            out.extend(sub_segments)
        else:
            out.append(seg)

    return out


def _merge_short_segments(
    segments: list[dict],
    min_duration: float = 3.0,
    max_gap: float = 2.0,
    max_merged_duration: float = 20.0,
    aggressive: bool = False,
    verbose: bool = False,
) -> list[dict]:
    """Merge consecutive short segments (<min_duration) with the next one when:
    - gap between the end of the previous and the start of the next < max_gap
    - same speaker (if that information is present)
    - the resulting duration does not exceed max_merged_duration
    Reduces XTTS hallucinations and atempo compression (fewer small slots
    with a longer English TTS → fewer audible atempo > 1.5 ratios).
    Parameters tuned 2026-04-24 after diagnostic on an IT→EN video: 60% of
    segments had ratio > 1.30 with the old defaults (1.5/0.4/12.0).

    Default `max_gap=2.0` (bumped 2026-04-27): the wider tolerance absorbs
    normal human breath pauses (1-2 s) that Whisper incorrectly treats as
    semantic boundaries, preventing continuous sentences from being broken
    into fragments.

    Second "orphan" pass (2026-04-27): after the primary merge, detects very
    short segments (≤5 words) that end with strong punctuation (.?!) and are
    tail fragments of a Whisper sentence broken on a breath pause. Forces them
    into the previous segment with looser constraints (gap≤3 s, total≤25 s)
    but the same speaker and a tight ceiling to prevent mega-fragments.

    `aggressive=True` raises the bounds (min 4.0, gap 1.5, max 30.0) to give
    TTS more room when the target is much longer than the source (e.g. EN→IT):
    longer segments have more headroom to absorb language expansion. Trade-off:
    higher maximum peaks, offset by a more aggressive auto-tuned XTTS speed.
    Note: with the new default max_gap=2.0, aggressive=True no longer bumps the
    gap (max(1.5, 2.0)=2.0) - intentional, conservative for existing callers.

    `verbose=True` prints each merged orphan (useful for tuning debugging).
    """
    if aggressive:
        # Force-override the parameters: the caller may have passed the
        # defaults (not knowing it is an expanded case). Always bump here.
        min_duration = max(min_duration, 4.0)
        max_gap = max(max_gap, 1.5)
        max_merged_duration = max(max_merged_duration, 30.0)
    if not segments:
        return segments
    merged: list[dict] = []
    for seg in segments:
        if not merged:
            merged.append(dict(seg))
            continue
        prev = merged[-1]
        prev_dur = prev["end"] - prev["start"]
        gap = seg["start"] - prev["end"]
        same_speaker = prev.get("speaker") == seg.get("speaker")
        new_dur = seg["end"] - prev["start"]
        # Guard: if segments overlap significantly (diarization with overlap)
        # `gap` is very negative; in that case do not merge, to avoid absorbing
        # another speaker's turn or a spurious overlap.
        if (
            prev_dur < min_duration
            and gap <= max_gap
            and gap >= -0.5
            and same_speaker
            and new_dur <= max_merged_duration
        ):
            # guard: if segments overlap, preserve the max end
            prev["end"] = max(prev["end"], seg["end"])
            prev["text"] = (prev.get("text", "") + " " + seg.get("text", "")).strip()
            # preserva eventuali metadati per-word (Whisper word_timestamps)
            if "words" in prev or "words" in seg:
                prev["words"] = prev.get("words", []) + seg.get("words", [])
        else:
            merged.append(dict(seg))

    # Second pass: orphans (short terminal fragments that Whisper detached from
    # the preceding sentence due to a breath pause). Iterate over `merged` and
    # build `final`, deciding for each element whether it is an orphan to merge
    # into the previous or a standalone segment. Multiple consecutive orphans
    # are all fused into the first non-orphan (chained through `prev` in
    # `final[-1]`).
    final: list[dict] = []
    for idx, seg in enumerate(merged):
        if idx == 0 or not final:
            final.append(seg)
            continue
        prev = final[-1]
        text = (seg.get("text", "") or "").strip()
        n_words = len(text.split()) if text else 0
        ends_with_terminal = bool(text) and text[-1] in ".?!"
        same_speaker = prev.get("speaker") == seg.get("speaker")
        gap = seg["start"] - prev["end"]
        new_dur = seg["end"] - prev["start"]
        is_orphan = (
            n_words > 0
            and n_words <= 5
            and ends_with_terminal
            and same_speaker
            and gap <= 3.0
            and gap >= -0.5
            and new_dur <= 25.0
        )
        if is_orphan:
            if verbose:
                print(
                    f"[merge] orfano fuso con prev: '{text}' "
                    f"(gap={gap:.2f}s, words={n_words})",
                    flush=True,
                )
            prev["end"] = max(prev["end"], seg["end"])
            prev["text"] = (prev.get("text", "") + " " + seg.get("text", "")).strip()
            if "words" in prev or "words" in seg:
                prev["words"] = prev.get("words", []) + seg.get("words", [])
        else:
            final.append(seg)
    return final


# Migration bridge for extracted pure segment helpers. This second binding is
# intentional because the legacy definitions above still exist during the
# transition; runtime callers below this point use the tested module versions.
from videotranslator.segments import (  # noqa: E402,F811
    expand_tight_slots as _expand_tight_slots,
    merge_short_segments as _merge_short_segments,
    repair_split_sentences as _repair_split_sentences,
    split_on_punctuation as _split_on_punctuation,
)
from videotranslator.ollama_length_control import (  # noqa: E402
    build_rewrite_shorter_prompt as _build_rewrite_shorter_prompt,
    compute_target_chars as _compute_target_chars,
    should_reprompt_for_length as _should_reprompt_for_length,
)
from videotranslator.ollama_prompt import (  # noqa: E402
    CONTEXT_SNIPPET_MAX_CHARS as _CONTEXT_SNIPPET_MAX_CHARS,
    build_translation_prompt as _build_translation_prompt,
)
from videotranslator.ollama_cove import (  # noqa: E402
    CoVeMetrics as _CoVeMetrics,
    build_verification_prompt as _cove_build_verification_prompt,
    needs_verification as _cove_needs_verification,
    parse_verification_response as _cove_parse_verification_response,
)
from videotranslator.document_context import (  # noqa: E402
    build_summary_prompt as _build_summary_prompt,
    is_summary_useful as _is_summary_useful,
)
from videotranslator.tts_text_sanitizer import (  # noqa: E402
    sanitize_for_tts as _sanitize_for_tts,
)
from videotranslator.difficulty_detector import (  # noqa: E402
    classify_difficulty as _classify_difficulty,
    estimate_p90_ratio as _estimate_p90_ratio,
    format_difficulty_log as _format_difficulty_log,
    tts_speed_factor_for as _tts_speed_factor_for,
)
from videotranslator.difficulty_profile import (  # noqa: E402
    MEDIUM as _DIFFICULTY_PROFILE_MEDIUM,
    Profile as _DifficultyProfile,
    format_profile_log as _format_profile_log,
    resolve_profile as _resolve_difficulty_profile,
)
from videotranslator.face_detector import (  # noqa: E402
    has_enough_faces as _has_enough_faces,
)
from videotranslator.quality_flags import (  # noqa: E402
    FLAG_LENGTH_UNFIT as _FLAG_LENGTH_UNFIT,
    FLAG_TRANSLATION_FALLBACK as _FLAG_TRANSLATION_FALLBACK,
    FLAG_WHISPER_SUSPICIOUS as _FLAG_WHISPER_SUSPICIOUS,
    QUALITY_FLAG_COLOURS as _QUALITY_FLAG_COLOURS,
    add_quality_flag as _add_quality_flag,
    compute_segment_quality_flags as _compute_segment_quality_flags,
    has_any_flag as _has_any_flag,
    primary_flag as _primary_flag,
)


from videotranslator.ollama_runtime import (  # noqa: E402
    set_subprocess_hooks as _set_ollama_subprocess_hooks,
    _ollama_find_binary,
    _ollama_health_check,
    _ollama_install,
    _ollama_install_linux,
    _ollama_install_macos,
    _ollama_install_windows,
    _ollama_is_daemon_running,
    _ollama_lang_name,
    _ollama_num_predict_for_segment,
    _ollama_pull_model,
    _ollama_start_daemon,
    _ollama_strip_preamble,
    _ollama_wait_for_daemon,
)


def translate_with_ollama(
    segments: list[dict],
    source_lang: str,
    target_lang: str,
    model: str = "qwen3:8b",
    api_url: str = "http://localhost:11434",
    slot_aware: bool = True,
    batch_size: int = 1,
    fallback_fn=None,
    thinking: bool = False,
    use_document_context: bool = True,
    difficulty_profile: _DifficultyProfile | None = None,
    use_cove: bool = True,
) -> list[dict]:
    """Translate segments via a local Ollama daemon using a slot-aware prompt
    that enforces conciseness for dubbing.

    Args:
        segments: list of dicts with keys `start`, `end`, `text`, opt `speaker`.
        source_lang: ISO code of the source language (e.g. "en"). "auto" accepted.
        target_lang: ISO code of the target language (e.g. "it").
        model: Ollama model name (default "qwen3:8b"). For Qwen3, thinking mode
               is disabled automatically (think=False + /no_think suffix) to
               prevent <think>...</think> blocks that XTTS would speak as outliers.
        api_url: base URL of the Ollama daemon (default "http://localhost:11434").
        slot_aware: if True, includes reading time in the prompt (recommended).
        batch_size: number of segments to pack into a single prompt. 1 = safe
                    (trivial parsing), >1 = faster but brittle parsing. In v2.0
                    we keep the default at 1 and leave the parameter as a future
                    hook (the code supports >1 with automatic per-segment fallback
                    if output parsing fails).
        fallback_fn: optional callable `(seg) -> str` invoked for a single
                     segment when Ollama raises. If None, the source text is
                     used as-is (degrades to "no translation").
        difficulty_profile: TASK 2G v2 profile (easy/medium/hard) that configures
                     the budget, threshold, and iteration count for the length
                     re-prompt. If None, the MEDIUM quality profile is used.
        use_cove: if True (default), enables the second-pass Chain-of-Verification
                     (TASK 2U) on segments containing risky patterns (negations,
                     quantifiers). The model verifies with isolated yes/no
                     questions whether the first translation preserves negations
                     and quantifiers, and can correct it. Covered by the Profile
                     (EASY=False, MEDIUM/HARD=True) but the caller can override
                     the flag (CLI ``--no-cove`` to disable globally).

    Returns the list of segments with `text_src` and `text_tgt` populated,
    using the same schema produced by `translate_segments` for other engines.
    """
    import re as _re
    import requests
    base = api_url.rstrip("/")
    src_name = _ollama_lang_name(source_lang)
    tgt_name = _ollama_lang_name(target_lang)

    # TASK 2G v2: profile orchestrator. None = default MEDIUM quality policy.
    # The caller is expected
    # to pass a resolved Profile when --no-difficulty-profile is OFF;
    # we fall back to MEDIUM here so the public function stays usable
    # standalone (CLI, notebooks) without forcing every caller to know
    # about the orchestrator.
    _profile = difficulty_profile or _DIFFICULTY_PROFILE_MEDIUM

    # Health check upfront - if Ollama is down we raise immediately instead of
    # failing 300 times in the loop.
    # TASK 2J: if the requested model is missing
    # but the daemon has another usable model, the selector returns it via
    # `resolved_model` and we proceed with it instead of falling through to
    # Google. Surface the warning so the user sees what happened.
    ok, msg, resolved_model = _ollama_health_check(base, model)
    if not ok:
        raise RuntimeError(msg)
    if msg and resolved_model and resolved_model != model:
        print(f"     ! {msg}", flush=True)
        model = resolved_model

    print(f"     → Ollama ready ({model} @ {base}, slot_aware={slot_aware}, batch={batch_size})", flush=True)

    # Detect Qwen3 family - needs thinking mode disabled to avoid <think>
    # blocks in output that XTTS would pronounce as audible chain-of-thought.
    # Sampling parameters tuned per Qwen team's official recommendations:
    #   - Qwen3 non-thinking: T=0.7, TopP=0.8, TopK=20 (avoids endless loops)
    #   - Qwen2.x and others: stricter T=0.3, TopP=0.9 for translation
    # Double protection: payload `think:false` (Ollama API ≥2025) +
    # /no_think suffix in the prompt (also works on older versions).
    is_qwen3 = model.lower().startswith("qwen3")
    # `thinking` is only meaningful for Qwen3 (other models ignore the flag).
    # For non-Qwen3 models the log label stays "standard"; for Qwen3 it reflects
    # the user's choice - thinking=True enables step-by-step deliberation
    # (~10x slower, reduces idiom/grammar errors), False keeps fast behaviour
    # with the /no_think prompt.
    if is_qwen3:
        _mode_label = f"Qwen3 {'thinking' if thinking else 'non-thinking'} (think={thinking})"
    else:
        _mode_label = "standard"
    print(f"     → Mode: {_mode_label}", flush=True)

    # Debug opt-in: when set, logs source + final output for every segment.
    # Useful for investigating preamble/commentary residues without re-running the pipeline.
    _ollama_debug = os.environ.get("VIDEOTRANSLATORAI_OLLAMA_DEBUG") == "1"

    # Length safeguard: compute the expected expansion factor (target/source)
    # from the LANG_EXPANSION table once, before the segment loop. Used to
    # estimate the maximum plausible length for each segment. Cap 1.8× =
    # permissive margin for verbose LLMs but catches commentary outliers.
    _src_key = (source_lang or "").split("-")[0] if source_lang != "auto" else ""
    _tgt_key = target_lang.split("-")[0] if target_lang else ""
    _exp_tgt = LANG_EXPANSION.get(target_lang, LANG_EXPANSION.get(_tgt_key, 1.0))
    _exp_src = LANG_EXPANSION.get(source_lang, LANG_EXPANSION.get(_src_key, 1.0)) or 1.0
    _expansion_factor = _exp_tgt / _exp_src if _exp_src > 0 else 1.0

    # TASK 2G: pre-flight difficulty estimate. Pure-text heuristic that
    # predicts the P90 of pre_stretch_ratio BEFORE TTS+stretch. Lets the
    # user know upfront whether the dub will be fluent (easy), partially
    # accelerated (medium) or audibly accelerated on most segments (hard).
    # Informational only - pipeline runs to completion regardless.
    #
    # tts_speed_factor lookup is per-target-language (it=1.15, en/es/fr/de
    # ~=1.10, zh/ja/ko ~=1.05). Empirical means observed on production
    # CSVs; the XTTS cap is 1.35 but most segments land lower. Using the
    # cap as divisor would over-correct. See difficulty_detector module
    # for the full table and calibration notes.
    _est_p90 = _estimate_p90_ratio(
        segments, target_lang, _expansion_factor,
        tts_speed_factor=_tts_speed_factor_for(target_lang),
    )
    if _est_p90 > 0:
        _diff_class = _classify_difficulty(_est_p90)
        print(
            f"     {_format_difficulty_log(_est_p90, _diff_class, target_lang)}",
            flush=True,
        )

    translated: list[dict] = []
    total = len(segments)
    total_src_chars = 0
    total_tgt_chars = 0
    failed = 0
    truncated_count = 0
    # TASK 2C-1: iterative re-prompt for length control. `rewrite_attempts`
    # counts the segments whose first translation was over budget and for which
    # we requested a "rewrite shorter" retry. `rewrite_success` counts how many
    # of those retries actually produced a shorter version.
    rewrite_attempts = 0
    rewrite_success = 0
    # TASK 2U: Chain-of-Verification counters. Kept in a small shared object
    # so logs/tests can distinguish useful corrections from rejected empty
    # responses, HTTP failures and skipped non-risky segments.
    cove_metrics = _CoVeMetrics()

    def _build_prompt(
        text: str,
        slot_s: float,
        prev_text: str | None = None,
        next_text: str | None = None,
    ) -> str:
        # Thin wrapper around the pure module-level builder. Closure captures
        # src_name, tgt_name, slot_aware, is_qwen3, thinking from the
        # surrounding _translate_with_ollama scope so the call sites stay
        # short. The actual prompt construction (including the optional
        # CONTEXT block injecting prev_text/next_text for disambiguation
        # and the document-level GLOBAL CONTEXT from TASK 2K) lives in
        # videotranslator.ollama_prompt and is unit-tested there.
        return _build_translation_prompt(
            text,
            slot_s,
            src_name,
            tgt_name,
            slot_aware=slot_aware,
            is_qwen3=is_qwen3,
            thinking=thinking,
            prev_text=prev_text,
            next_text=next_text,
            global_context=_global_context,
        )

    def _call_ollama(prompt: str, num_predict: int) -> str:
        if is_qwen3:
            options = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "num_predict": num_predict,
            }
        else:
            options = {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": num_predict,
            }
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        # Toggle thinking mode on Qwen3 via the native API flag (Ollama
        # supports `think` from 2025+). If the API ignores the flag on older
        # versions, the `/no_think` suffix in the prompt (when thinking=False)
        # acts as a safety fallback. With thinking=True the model deliberates
        # step-by-step: ~10x slower but reduces idiom/grammar errors.
        if is_qwen3:
            payload["think"] = bool(thinking)
        # Generous timeout: qwen3:8b / qwen2.5:7b on an RTX 3090 produces
        # ~40-80 tok/s, but on CPU-only it can drop to 2-5 tok/s. With thinking
        # enabled the model produces 3-5x more tokens (internal chain-of-thought
        # + answer), so we raise the timeout to 360 s to avoid cut-off.
        _timeout = 360 if (is_qwen3 and thinking) else 120
        r = requests.post(f"{base}/api/generate", json=payload, timeout=_timeout)
        r.raise_for_status()
        data = r.json()
        return _ollama_strip_preamble(data.get("response", ""))

    # TASK 2K: document-level context. One Ollama call up front to get a
    # semantic summary of the whole transcript; injected into every per-
    # segment prompt as 'GLOBAL CONTEXT (do not translate)' to anchor
    # terminology, tone and global referents (a "he" 3 minutes later
    # referring to a person introduced at the start). Skipped for short
    # videos where the local prev/next window already covers everything,
    # and skipped entirely when the caller passes use_document_context=False
    # (CLI --no-document-context, ergonomic opt-out for fast runs).
    _global_context: str | None = None
    if use_document_context and _is_summary_useful(segments):
        try:
            _summary_prompt = _build_summary_prompt(
                segments, tgt_name, src_name,
                is_qwen3=is_qwen3, thinking=thinking,
            )
            if _summary_prompt:
                # Token budget for the summary: bias the input length
                # toward "long" so the output budget is generous. The
                # summary is a one-off call; spending an extra ~500
                # tokens of headroom is cheaper than truncating the
                # glossary.
                _summary_predict = _ollama_num_predict_for_segment(
                    "x" * 1500, is_qwen3, thinking,
                )
                _summary_raw = _call_ollama(_summary_prompt, _summary_predict)
                _summary_clean = (_summary_raw or "").strip()
                if _summary_clean:
                    _global_context = _summary_clean
                    print(
                        f"     → Document context: {len(_global_context)} chars summary "
                        f"generated for translation guide",
                        flush=True,
                    )
        except Exception as _ctx_err:
            print(
                f"     ! Document context generation failed: {_ctx_err}; "
                f"proceeding without global context",
                flush=True,
            )
            _global_context = None

    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        slot_s = max(0.0, float(seg.get("end", 0)) - float(seg.get("start", 0)))

        # TASK 2D: sliding context window. Pass the previous and next
        # segment text as CONTEXT (for understanding only) so qwen3 can
        # resolve sentence-spanning fragments like "...less likely to" /
        # "stick. When I gave up sugar..." that Whisper splits on
        # punctuation/pause. Each snippet is capped at
        # _CONTEXT_SNIPPET_MAX_CHARS by the builder to keep the prompt
        # compact and Ollama latency low.
        _prev_text: str | None = None
        if i > 0:
            _prev_raw = (segments[i - 1].get("text") or "").strip()
            if _prev_raw:
                _prev_text = _prev_raw
        _next_text: str | None = None
        if i + 1 < len(segments):
            _next_raw = (segments[i + 1].get("text") or "").strip()
            if _next_raw:
                _next_text = _next_raw

        # Per-segment metrics counters (used later when building entry dict
        # so the metrics CSV can correlate ratio outliers with retry decisions).
        _seg_target_chars = 0
        _seg_retry_attempted = False
        _seg_retry_succeeded = False

        if not text:
            tr = ""
        else:
            try:
                prompt = _build_prompt(
                    text,
                    slot_s,
                    prev_text=_prev_text,
                    next_text=_next_text,
                )
                num_predict = _ollama_num_predict_for_segment(text, is_qwen3, thinking)
                tr = _call_ollama(prompt, num_predict)
                if not tr:
                    if is_qwen3 and thinking:
                        retry_predict = _ollama_num_predict_for_segment(
                            text, is_qwen3, thinking, retry=1
                        )
                        print(
                            f"     ! Ollama thinking returned empty response for segment #{i} "
                            f"(num_predict={num_predict}); retrying with num_predict={retry_predict}",
                            flush=True,
                        )
                        tr = _call_ollama(prompt, retry_predict)
                        if not tr:
                            print(
                                f"     ! Ollama thinking retry exhausted for segment #{i} "
                                f"(initial num_predict={num_predict}, retry num_predict={retry_predict}); "
                                f"falling back",
                                flush=True,
                            )
                    if not tr:
                        # Empty response - treat as failure and fall back.
                        raise RuntimeError("empty response")
                # ── Length re-prompt (TASK 2C-1, 2G v2) ─────────────────
                # If the first translation is significantly over the budget
                # allowed for the audio slot, ask the model to rewrite it
                # shorter. This reduces the "strong/severe" zone of the atempo
                # diagnostic (>1.50x) without penalising segments already within
                # budget. Cost: +N Ollama calls only for outliers
                # (N = profile.length_retry_max_iter, 2 for MEDIUM, 3 for HARD).
                #
                # TASK 2G v2: budget, threshold, and iteration count come from
                # the Profile. Denser profiles demand shorter sentences before
                # letting atempo/rubberband compress the audio.
                target_chars = _compute_target_chars(
                    slot_s,
                    target_lang,
                    slack=_profile.target_chars_slack,
                    min_chars=_profile.target_chars_floor,
                )
                _seg_target_chars = target_chars
                _retry_threshold = _profile.length_retry_threshold
                _retry_max_iter = _profile.length_retry_max_iter
                _retry_iter = 0
                while (
                    _retry_iter < _retry_max_iter
                    and _should_reprompt_for_length(
                        len(tr), target_chars, threshold=_retry_threshold
                    )
                ):
                    _retry_iter += 1
                    rewrite_attempts += 1
                    _seg_retry_attempted = True
                    rewrite_prompt = _build_rewrite_shorter_prompt(
                        first_translation=tr,
                        slot_s=slot_s,
                        target_chars=target_chars,
                        target_lang_name=tgt_name,
                        is_qwen3=is_qwen3,
                        thinking=thinking,
                    )
                    rewrite_predict = _ollama_num_predict_for_segment(
                        text, is_qwen3, thinking
                    )
                    try:
                        tr_short = _call_ollama(rewrite_prompt, rewrite_predict)
                    except Exception as _re_err:
                        tr_short = ""
                        print(
                            f"     ! Length retry seg #{i} (iter {_retry_iter}) "
                            f"HTTP failed: {_re_err}; keeping previous translation",
                            flush=True,
                        )
                        # On HTTP error stop iterating: a flaky daemon would
                        # otherwise burn the full retry budget for nothing.
                        break
                    if tr_short and len(tr_short) < len(tr):
                        if not _seg_retry_succeeded:
                            # Count "first success" once even if further iter
                            # produce additional shrinkage; rewrite_success is
                            # the number of segments improved, not the total
                            # number of successful calls.
                            rewrite_success += 1
                            _seg_retry_succeeded = True
                        _iter_tag = (
                            f" iter {_retry_iter}/{_retry_max_iter}"
                            if _retry_max_iter > 1 else ""
                        )
                        print(
                            f"     ↺ Length retry seg #{i}{_iter_tag}: "
                            f"{len(tr)} → {len(tr_short)} chars "
                            f"(target {target_chars}, slot {slot_s:.1f}s)",
                            flush=True,
                        )
                        tr = tr_short
                    elif tr_short:
                        # Model responded but did not shorten. Log only when
                        # _ollama_debug to avoid cluttering the output, and
                        # stop the loop: a second iteration with the same
                        # translation would hit the same local minimum of the
                        # model, wasting budget.
                        if _ollama_debug:
                            print(
                                f"     [ollama-debug] length retry seg #{i} "
                                f"iter {_retry_iter} did not shorten "
                                f"({len(tr_short)} >= {len(tr)})",
                                flush=True,
                            )
                        break
                # TASK 5C: post-retry quality flag. If the (possibly
                # multi-iter) length retry loop exhausted its budget and
                # the translation is *still* above the comfort threshold,
                # mark the segment so the editor highlights it for review.
                # The pipeline still ships the over-budget translation -
                # this is purely a hint for the human reviewer.
                if (
                    _seg_target_chars > 0
                    and _should_reprompt_for_length(
                        len(tr), _seg_target_chars, threshold=_retry_threshold
                    )
                ):
                    _add_quality_flag(seg, _FLAG_LENGTH_UNFIT)
                # ── Length safeguard ────────────────────────────────────
                # If the residual output after strip_preamble is >> the source
                # relative to the expected expansion, the model almost certainly
                # included unstripped commentary. Truncate to the first complete
                # sentence (or to a char cap with word-boundary) to prevent
                # XTTS from synthesising 20+ seconds of disclaimer.
                # v2.2: tighter cap 1.5x (was 1.8x) to catch Ollama outliers
                # from unstripped commentary/disclaimers more aggressively.
                max_reasonable_chars = max(
                    50, int(len(text) * _expansion_factor * 1.5)
                )
                if len(tr) > max_reasonable_chars:
                    # v2.2: always log the truncated SRC and OUT so the user can
                    # diagnose which segments triggered the safety without having
                    # to set VIDEOTRANSLATORAI_OLLAMA_DEBUG.
                    src_preview = text[:120] + ("..." if len(text) > 120 else "")
                    cleaned_preview = tr[:200] + ("..." if len(tr) > 200 else "")
                    print(
                        f"     ! Ollama output sospetto (segment {i}): "
                        f"{len(tr)} chars vs max atteso {max_reasonable_chars}. "
                        f"Attivo safety truncation.",
                        flush=True,
                    )
                    print(f"       SRC: {src_preview!r}", flush=True)
                    print(f"       OUT: {cleaned_preview!r}", flush=True)
                    # Strategy: first complete sentence (.?!。？！ followed by
                    # space/end). Fallback: cap with word-boundary.
                    m = _re.search(r"^(.+?[.?!。？！])(?:\s|$)", tr)
                    if m and len(m.group(1)) <= max_reasonable_chars * 1.1:
                        tr = m.group(1)
                    else:
                        tr = tr[:max_reasonable_chars].rsplit(" ", 1)[0] + "..."
                    truncated_count += 1
                # ── Chain-of-Verification (TASK 2U) ────────────────────
                # Second-pass opt-in that targets semantic errors by qwen3
                # on risky segments (negations, quantifiers).
                # Reference: ACL 2024 paper 'Chain-of-Verification
                # Reduces Hallucination in Large Language Models'.
                # Triggered ONLY if: (a) flag use_cove True (controlled
                # by Profile + CLI --no-cove), (b) source contains a
                # risky pattern, (c) candidate translation is non-empty.
                # Failure is best-effort: the first translation remains
                # valid if the HTTP check fails or the output is unusable.
                if use_cove and tr:
                    _cove_needs, _cove_reasons = _cove_needs_verification(text)
                    if _cove_needs:
                        cove_metrics.record_attempt()
                        try:
                            _cove_prompt = _cove_build_verification_prompt(
                                source_text=text,
                                candidate_translation=tr,
                                src_lang_name=src_name,
                                tgt_lang_name=tgt_name,
                                reasons=_cove_reasons,
                                is_qwen3=is_qwen3,
                                thinking=thinking,
                            )
                            _cove_predict = _ollama_num_predict_for_segment(
                                text, is_qwen3, thinking
                            )
                            _cove_raw = _call_ollama(_cove_prompt, _cove_predict)
                            _cove_corrected, _cove_changed = (
                                _cove_parse_verification_response(
                                    _cove_raw, original_translation=tr
                                )
                            )
                            if _cove_changed and _cove_corrected:
                                cove_metrics.record_correction()
                                if _ollama_debug:
                                    print(
                                        f"     ↻ CoVe seg #{i} "
                                        f"(reasons={','.join(_cove_reasons)}): "
                                        f"{tr!r} → {_cove_corrected!r}",
                                        flush=True,
                                    )
                                tr = _cove_corrected
                            elif _cove_changed and not _cove_corrected:
                                cove_metrics.record_rejected()
                        except Exception as _cove_err:
                            cove_metrics.record_failure()
                            # CoVe is opt-in best-effort: an HTTP error or
                            # a parse failure must not block the segment.
                            # The first translation remains valid.
                            if _ollama_debug:
                                print(
                                    f"     ! CoVe seg #{i} failed: {_cove_err}",
                                    flush=True,
                                )
                    else:
                        cove_metrics.record_skipped()
                if _ollama_debug:
                    print(
                        f"     [ollama-debug] seg#{i} src={text!r} → tgt={tr!r}",
                        flush=True,
                    )
            except Exception as e:
                failed += 1
                fb_text = None
                if fallback_fn is not None:
                    try:
                        fb_text = fallback_fn(seg)
                    except Exception as fe:
                        print(f"     ! Ollama+fallback both failed for segment #{i}: {fe}", flush=True)
                if fb_text:
                    tr = fb_text
                    print(
                        f"     ! Ollama translation failed for segment #{i}, fallback used: {e}",
                        flush=True,
                    )
                else:
                    tr = text
                    print(
                        f"     ! Ollama translation failed for segment #{i}, keeping source: {e}",
                        flush=True,
                    )
                # TASK 5C: primary engine failed for this segment - flag so
                # the editor surfaces it. Both branches (fallback used OR
                # source kept) are lower-quality than a successful Ollama
                # translation, so they share the same flag.
                _add_quality_flag(seg, _FLAG_TRANSLATION_FALLBACK)

        total_src_chars += len(text)
        total_tgt_chars += len(tr)
        entry = {
            "start": seg["start"],
            "end":   seg["end"],
            "text_src": text,
            "text_tgt": tr or text,
            # STEP 1: per-segment metrics for CSV dump in build_dubbed_track.
            # Underscore prefix marks them as internal pipeline metadata so
            # downstream consumers (subtitle writers, editors) ignore them.
            "_target_chars": _seg_target_chars,
            "_length_retry_attempted": _seg_retry_attempted,
            "_length_retry_succeeded": _seg_retry_succeeded,
        }
        if "speaker" in seg:
            entry["speaker"] = seg["speaker"]
        # TASK 5C: propagate quality flags from the source segment (where the
        # Whisper sanity stage tagged whisper_suspicious) and from the in-loop
        # additions (length_unfit, translation_fallback) to the translated
        # entry so the subtitle editor can colourise the row.
        _flags_for_entry = _compute_segment_quality_flags(seg)
        if _flags_for_entry:
            entry["_quality_flags"] = _flags_for_entry
        translated.append(entry)
        if (i + 1) % 4 == 0 or i + 1 == total:
            print(f"     {i+1}/{total}...", end="\r", flush=True)

    # Shrinkage statistic: how much more concise the Ollama output is relative
    # to the source (character-count approximation). Useful for diagnosing
    # whether the "CONCISE" prompt is working (expected ratio ~0.9-1.1 vs the
    # naïve 1.25 for EN→IT with deep-translator).
    if total_src_chars > 0:
        ratio = total_tgt_chars / total_src_chars
        # Naïve expansion expected from the LANG_EXPANSION table (literal baseline)
        exp_tgt = LANG_EXPANSION.get(target_lang, LANG_EXPANSION.get(target_lang.split("-")[0], 1.0))
        exp_src = LANG_EXPANSION.get(source_lang, LANG_EXPANSION.get((source_lang or "").split("-")[0], 1.0))
        baseline = (exp_tgt / exp_src) if exp_src > 0 else 1.0
        shrinkage_pct = (ratio / baseline - 1.0) * 100.0 if baseline > 0 else 0.0
        fail_note = f", {failed} fallback" if failed else ""
        print(
            f"     → Ollama translation: {total}/{total} segments, "
            f"char ratio={ratio:.2f} vs literal baseline {baseline:.2f} "
            f"(shrinkage {shrinkage_pct:+.1f}%){fail_note}",
            flush=True,
        )
        if rewrite_attempts > 0:
            print(
                f"     → Length re-prompt: {rewrite_attempts} segments over budget, "
                f"{rewrite_success} shortened ({rewrite_attempts - rewrite_success} kept original)",
                flush=True,
            )
        if truncated_count > 0:
            print(
                f"     → Safety-truncated for length: {truncated_count} segments "
                f"(see log above for context)",
                flush=True,
            )
        if cove_metrics.attempted > 0:
            # TASK 2U: CoVe summary. The "verified" count is the number
            # of segments where the source had a risk pattern (negation
            # / quantifier) and we ran the second-pass; "corrected" is
            # the subset where the model produced a substantially
            # different translation that we accepted. A 0/N corrected
            # rate is normal on clean translations - it just means the
            # first pass already preserved every negation.
            print(
                f"     → CoVe verification: {cove_metrics.summary()}",
                flush=True,
            )
    else:
        print(f"     → Ollama translation: {total}/{total} segments (no text)", flush=True)

    return translated


from videotranslator.translation import (  # noqa: E402
    TranslationUnavailableError,
    _marian_normalize_lang,
    translate_segments as _translate_segments_impl,
)


def _count_fallback_segments(result) -> int:
    """Count segments of a ``translate_video`` result whose translation
    failed (source text kept or fallback engine used)."""
    if not isinstance(result, dict):
        return 0
    return sum(
        1 for seg in result.get("segments") or []
        if _FLAG_TRANSLATION_FALLBACK in _compute_segment_quality_flags(seg)
    )


def _error_key_for(exc: BaseException) -> str | None:
    """UI_STRINGS key of a specific error dialog for ``exc``, if any."""
    if isinstance(exc, TranslationUnavailableError):
        return "msg_translation_unavailable"
    return None


def _shared_error_key(error_keys: list[str | None]) -> str | None:
    """Error dialog key for a run of several files, given the
    ``_error_key_for`` result of each failed file: the specific key only
    when every failure had that same key, else None (generic message)."""
    distinct = set(error_keys)
    return distinct.pop() if len(distinct) == 1 else None


def translate_segments(
    segments: list[dict], source: str, target: str,
    engine: str = "google", deepl_key: str = "",
    ollama_model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    ollama_slot_aware: bool = True,
    ollama_thinking: bool = False,
    ollama_document_context: bool = True,
    difficulty_profile: _DifficultyProfile | None = None,
    ollama_use_cove: bool = True,
) -> list[dict]:
    return _translate_segments_impl(
        segments, source, target,
        engine=engine, deepl_key=deepl_key,
        ollama_model=ollama_model, ollama_url=ollama_url,
        ollama_slot_aware=ollama_slot_aware,
        ollama_thinking=ollama_thinking,
        ollama_document_context=ollama_document_context,
        difficulty_profile=difficulty_profile,
        ollama_use_cove=ollama_use_cove,
        ollama_translator=translate_with_ollama,
    )


from videotranslator.edge_tts_engine import (  # noqa: E402
    generate_tts,
    tts_all as _tts_all,
    tts_segment as _tts_segment,
)
from videotranslator.tts_reference import (  # noqa: E402
    build_vad_reference as _build_vad_reference,
    build_vad_reference_tiered as _build_vad_reference_tiered,
    extract_speaker_reference as _extract_speaker_reference,
)


from videotranslator.xtts_engine import generate_tts_xtts  # noqa: E402


# v2.5.2: seed list for multi-attempt XTTS retry.
# Using different empirical seeds pushes the XTTS GPT2 decoder down different
# paths, reducing the probability that the same text falls into the same
# deterministic loop of a fixed seed (was 42 in v2.2-2.5.1).
# The last seed (42) is kept for backwards-compatibility with v2.2-2.5.1 logs
# in case regression-test comparisons are needed.
RETRY_SEEDS = (7, 1337, 42)


from videotranslator.audio_assembly import (  # noqa: E402
    build_dubbed_track as _build_dubbed_track_impl,
)
from videotranslator.output_media import (  # noqa: E402
    get_duration,
    mux_video as _mux_video_impl,
    save_subtitles,
    segments_to_srt,
)


def build_dubbed_track(
    segments: list[dict],
    tts_files: list[str],
    bg_path: str | None,
    total_duration: float,
    tmp_dir: str,
    bg_volume: float = 0.15,
    label: str = "[6/6] Assembling dubbed track...",
    metrics_csv_path: str | None = None,
    overlap_fade_enabled: bool = True,
    difficulty_profile: _DifficultyProfile | None = None,
) -> str:
    """Compatibility wrapper for the modular dubbed-track assembler."""
    return _build_dubbed_track_impl(
        segments,
        tts_files,
        bg_path,
        total_duration,
        tmp_dir,
        bg_volume=bg_volume,
        label=label,
        metrics_csv_path=metrics_csv_path,
        overlap_fade_enabled=overlap_fade_enabled,
        difficulty_profile=difficulty_profile,
        run_ffmpeg=_run_ffmpeg,
        log=print,
    )

def mux_video(video_input: str, audio_track: str, output_path: str):
    """Compatibility wrapper around the modular mux helper."""
    return _mux_video_impl(
        video_input,
        audio_track,
        output_path,
        run_ffmpeg=_run_ffmpeg,
        log=print,
    )


# ═══════════════════════════════════════════════════════════
#  LIP SYNC (Wav2Lip)
# ═══════════════════════════════════════════════════════════

def _is_dir_user_writable(path: Path) -> bool:
    """Return True only if the current user can actually create files in *path*.

    ``os.access(..., os.W_OK)`` is unreliable on Windows: it only inspects the
    read-only attribute and does NOT consult NTFS ACLs, so a standard (non-
    elevated) user often sees ``W_OK=True`` on ``C:\\Program Files\\...`` even
    though a real write would be denied by UAC/MIC. Probing with an actual
    tempfile create+delete is the only portable way to get a truthful answer
    on both Windows and POSIX without introducing pywin32.
    """
    if not path.exists() or not path.is_dir():
        return False
    try:
        # delete=True removes the file as soon as the handle is closed.
        with tempfile.NamedTemporaryFile(dir=str(path), prefix=".vtai_wtest_",
                                         delete=True):
            pass
        return True
    except (OSError, PermissionError):
        return False


def _resolve_wav2lip_paths():
    """Resolve Wav2Lip asset and work directories using the pure resolver.

    Delegates to :func:`videotranslator.platforms.resolve_wav2lip_paths` so
    the platform-specific candidate logic lives in one place and is fully
    unit-tested. The asset dir is allowed to live under a system-wide,
    possibly read-only install path; the work dir is always per-user and
    writable.

    Backwards compatibility: callers that previously used a single
    ``WAV2LIP_DIR`` keep working - ``WAV2LIP_DIR`` is aliased to ``asset_dir``
    below, which is exactly what the legacy code did when assets were
    already populated under the system path or fell back to
    ``~/.local/share/wav2lip``.
    """
    from videotranslator.platforms import resolve_wav2lip_paths as _impl
    return _impl()


def _resolve_wav2lip_dir() -> Path:
    """Legacy single-dir helper kept for callers that only need asset_dir."""
    return _resolve_wav2lip_paths().asset_dir


_WAV2LIP_PATHS  = _resolve_wav2lip_paths()
WAV2LIP_DIR     = _WAV2LIP_PATHS.asset_dir
# Per-user scratch space for frames / intermediate sync output. NEVER under
# ProgramFiles on Windows: the pipeline must be able to write here without
# admin rights. See ``Wav2LipPaths`` in ``videotranslator/platforms.py``.
WAV2LIP_WORK_DIR = _WAV2LIP_PATHS.work_dir
WAV2LIP_REPO    = WAV2LIP_DIR / "Wav2Lip"
WAV2LIP_MODEL   = WAV2LIP_DIR / "wav2lip_gan.pth"
WAV2LIP_REPO_URL  = "https://github.com/Rudrabha/Wav2Lip.git"
WAV2LIP_MODEL_URL = "https://huggingface.co/numz/wav2lip_studio/resolve/main/Wav2lip/wav2lip_gan.pth"
WAV2LIP_TIMEOUT = 3600  # seconds before Wav2Lip subprocess is forcibly killed

# Base deps needed by Wav2Lip on all platforms; dlib + face-detection extras
# are handled separately below (different install strategy per OS).
from videotranslator.wav2lip_runtime import (  # noqa: E402
    WAV2LIP_BASE_REQUIREMENTS,
    missing_wav2lip_base_packages as _missing_wav2lip_base_packages,
    missing_wav2lip_face_packages as _missing_wav2lip_face_packages,
)

WAV2LIP_BASE_PKGS = [req.pip_name for req in WAV2LIP_BASE_REQUIREMENTS]
# Face-detection stack required by Wav2Lip's inference.py. On Windows the
# installer ships pre-built dlib wheels; on Linux dlib must compile from
# source (needs cmake + a C++ toolchain), so we attempt it best-effort and
# surface a clear message on failure instead of crashing mid-pipeline.
#
# We pull `new-basicsr` (maintained fork) instead of the original `basicsr`
# 1.4.2 (abandoned 2022). The original fails to build on Python 3.13 with
# `KeyError: '__version__'` because its setup.py uses the
# get_version() helper that relies on PEP 667-broken locals() semantics.
# `new-basicsr` ships a pre-built wheel (no setup.py invocation at install
# time) AND installs the SAME top-level `basicsr` package - every
# `import basicsr...` in Wav2Lip / facexlib keeps working unchanged.
WAV2LIP_FACE_PKGS = ["new-basicsr", "facexlib"]

from videotranslator.subprocess_utils import ActiveSubprocessRegistry  # noqa: E402

_active_subprocesses = ActiveSubprocessRegistry()


def _register_subprocess(proc: subprocess.Popen) -> None:
    """Add a running subprocess to the global registry under a lock."""
    _active_subprocesses.register(proc)


def _unregister_subprocess(proc: subprocess.Popen) -> None:
    """Remove a subprocess from the global registry under a lock."""
    _active_subprocesses.unregister(proc)


def _snapshot_active_subprocesses() -> list[subprocess.Popen]:
    """Return a list copy of the registry while holding the lock.

    Iteration / .terminate() happens outside the lock so we never block
    worker threads trying to register a new subprocess on a slow kill.
    """
    return _active_subprocesses.snapshot()


_set_ollama_subprocess_hooks(_register_subprocess, _unregister_subprocess)


def _install_wav2lip_base_stack() -> None:
    """Install missing base packages imported by Wav2Lip inference.py."""
    missing = _missing_wav2lip_base_packages()
    if not missing:
        return
    print(f"     Installing Wav2Lip base deps: {', '.join(missing)}", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet",
         "--break-system-packages"] + missing,
        check=False,
    )
    if result.returncode != 0:
        print("     ! Some Wav2Lip base deps failed to install - lipsync may not work.", flush=True)


def _install_wav2lip_face_stack_linux() -> None:
    """Install dlib + new-basicsr + facexlib on Linux with a cmake pre-check.

    dlib has no official PyPI wheels for Linux; pip must compile from source
    via cmake + libboost. We pre-check for cmake and emit an actionable error
    instead of letting pip dump a long traceback.

    `new-basicsr` is a maintained fork of the abandoned `basicsr` 1.4.2 - it
    ships a pre-built wheel and installs as the same `basicsr` module, which
    sidesteps the `KeyError: '__version__'` build failure of the original on
    Python 3.13 (PEP 667 broke its setup.py exec/locals pattern).
    `facexlib` is pure Python and installs cleanly regardless.
    """
    # new-basicsr + facexlib are cheap (wheel + pure python), install them
    # first so lipsync can at least attempt to run even if dlib is missing.
    missing_face = set(_missing_wav2lip_face_packages())
    light_pkgs = [pkg for pkg in WAV2LIP_FACE_PKGS if pkg in missing_face]
    if light_pkgs:
        print(f"     Installing Wav2Lip face deps: {', '.join(light_pkgs)}", flush=True)
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--break-system-packages"] + light_pkgs,
            check=False,
        )
        if res.returncode != 0:
            print("     ! new-basicsr/facexlib install failed - lipsync face detection may not work.", flush=True)

    # dlib: short-circuit if already importable (system package or prior install).
    try:
        import dlib  # noqa: F401
        print("     [+] dlib already available.", flush=True)
        return
    except ImportError:
        pass

    if not shutil.which("cmake"):
        print(
            "     ! dlib not installed: cmake is required to build dlib from source.\n"
            "       Install it with:  sudo apt install cmake build-essential libboost-all-dev\n"
            "       Then rerun this tool - Wav2Lip lipsync will be retried automatically.",
            flush=True,
        )
        return

    print("     Installing dlib (compiling from source, may take a few minutes)...", flush=True)
    res = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--break-system-packages", "dlib"],
        check=False,
    )
    if res.returncode != 0:
        print(
            "     ! dlib build failed. Ensure a C++ toolchain is present:\n"
            "       sudo apt install build-essential cmake libboost-all-dev\n"
            "       Lipsync will be unavailable until dlib installs cleanly.",
            flush=True,
        )


def _ensure_wav2lip_python_deps() -> None:
    """Ensure Python packages imported by Wav2Lip are present."""
    _install_wav2lip_base_stack()
    missing_face = _missing_wav2lip_face_packages()
    if not missing_face:
        return
    names = ", ".join(missing_face)
    if sys.platform.startswith("win"):
        print(
            f"     ! Wav2Lip face deps missing: {names}. "
            "Run setup_windows.bat to install the Windows face stack.",
            flush=True,
        )
        return
    _install_wav2lip_face_stack_linux()


def _ensure_wav2lip_assets():
    """Ensure Wav2Lip repo and GAN weights are available locally.

    The asset directory may be a system-wide install (e.g. under
    ``%ProgramFiles%`` on Windows) that is read-only for unprivileged users.
    The pure path resolver guarantees that if assets are NOT yet present we
    landed on a writable fallback, so a plain ``mkdir`` here is safe in
    "fresh install" mode. Even when repo+model are already present we still
    verify Python runtime deps: users can have a populated asset cache but a
    fresh Python environment.
    """
    repo_present = WAV2LIP_REPO.exists() and (WAV2LIP_REPO / "inference.py").exists()
    model_present = WAV2LIP_MODEL.exists()
    if repo_present and model_present:
        _ensure_wav2lip_python_deps()
        return

    WAV2LIP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        WAV2LIP_WORK_DIR.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        pass

    if not repo_present:
        if WAV2LIP_REPO.exists():
            raise RuntimeError(
                f"Incomplete Wav2Lip repo at {WAV2LIP_REPO}: missing inference.py"
            )
        print(f"     Cloning Wav2Lip repo → {WAV2LIP_REPO}", flush=True)
        if not shutil.which("git"):
            raise RuntimeError("git not found: required to clone Wav2Lip repo")
        subprocess.run(
            ["git", "clone", "--depth", "1", WAV2LIP_REPO_URL, str(WAV2LIP_REPO)],
            check=True, capture_output=True,
        )

        # Patch audio.py: librosa>=0.9 changed filters.mel() to keyword-only args
        audio_py = WAV2LIP_REPO / "audio.py"
        if audio_py.exists():
            txt = audio_py.read_text(encoding="utf-8")
            patched = txt.replace(
                "librosa.filters.mel(hp.sample_rate, hp.n_fft,",
                "librosa.filters.mel(sr=hp.sample_rate, n_fft=hp.n_fft,",
            )
            if patched != txt:
                audio_py.write_text(patched, encoding="utf-8")
                print("     Patched audio.py for librosa>=0.9 compatibility.", flush=True)

    _ensure_wav2lip_python_deps()

    if not WAV2LIP_MODEL.exists():
        print("     Downloading Wav2Lip GAN model (~416MB)...", flush=True)
        part = Path(str(WAV2LIP_MODEL) + ".part")
        try:
            from urllib.request import Request, urlopen
            req = Request(WAV2LIP_MODEL_URL, headers={"User-Agent": "VideoTranslatorAI/1.0"})
            with urlopen(req, timeout=120) as r, open(part, "wb") as f:
                shutil.copyfileobj(r, f)
            part.replace(WAV2LIP_MODEL)
        except Exception as e:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"Failed downloading Wav2Lip model: {e}") from e


from videotranslator.lipsync import apply_lipsync as _apply_lipsync_impl  # noqa: E402


def apply_lipsync(video_path: str, audio_path: str, tmp_dir: str) -> str:
    return _apply_lipsync_impl(
        video_path,
        audio_path,
        tmp_dir,
        wav2lip_repo=WAV2LIP_REPO,
        wav2lip_model=WAV2LIP_MODEL,
        wav2lip_work_dir=WAV2LIP_WORK_DIR,
        ensure_assets=_ensure_wav2lip_assets,
        timeout=WAV2LIP_TIMEOUT,
        register_subprocess=_register_subprocess,
        unregister_subprocess=_unregister_subprocess,
        popen=subprocess.Popen,
        timer_factory=threading.Timer,
        log=print,
    )


from videotranslator.config import (  # noqa: E402
    get_default_config_path as _get_default_config_path,
    get_legacy_config_path as _get_legacy_config_path,
    load_json_config as _load_json_config,
    merge_json_config as _merge_json_config,
    migrate_legacy_config_if_needed as _migrate_legacy_config_if_needed,
    write_json_config as _write_json_config,
)


def _resolve_config_path() -> Path:
    """Return the platform-aware user config path, migrating legacy on first run.

    Linux: $XDG_CONFIG_HOME/videotranslatorai/config.json (default
    ~/.config/videotranslatorai/config.json). Windows: %APPDATA%\\VideoTranslatorAI\\config.json.
    macOS: ~/Library/Application Support/VideoTranslatorAI/config.json.

    On first run after upgrading from <=v1.9, any existing
    ~/.videotranslatorai_config.json is copied (not moved) to the new path so
    older versions of the tool keep working during the transition window.
    """
    new_path = _get_default_config_path()
    try:
        migrated = _migrate_legacy_config_if_needed()
    except Exception:
        migrated = False
    if migrated:
        legacy = _get_legacy_config_path()
        print(f"[+] Config migrated from {legacy} to {new_path}", flush=True)
    return new_path


CONFIG_PATH = _resolve_config_path()
KEYRING_SERVICE = "VideoTranslatorAI"
KEYRING_USERNAME = "hf_token"
_KEYRING_MIGRATED = False

from videotranslator.secrets import (  # noqa: E402
    import_keyring_backend as _import_keyring_backend,
    load_secret_token as _load_secret_token,
    save_secret_token as _save_secret_token,
)


def load_config() -> dict:
    return _load_json_config(CONFIG_PATH)


def _write_config_raw(cfg: dict) -> None:
    """Write the cfg dict (whole, not merged) atomically with 0600 permissions.
    Use this when keys need to be deleted; save_config merges and would never
    remove existing keys.
    """
    _write_json_config(CONFIG_PATH, cfg)


def save_config(data: dict) -> None:
    try:
        _merge_json_config(CONFIG_PATH, data)
    except Exception as e:
        print(f"     ! Could not save config: {e}", flush=True)


def _keyring_available():
    """Return the keyring module if available, otherwise None."""
    return _import_keyring_backend()


def load_hf_token() -> str:
    """Read the HF token: first from the keyring, then (migration) from the legacy JSON."""
    return _load_secret_token(
        keyring_backend=_keyring_available(),
        config_path=CONFIG_PATH,
        service_name=KEYRING_SERVICE,
        username=KEYRING_USERNAME,
    )


def save_hf_token(token: str) -> None:
    """Save the HF token to the system keyring. Falls back to JSON if keyring is unavailable."""
    token = (token or "").strip()
    if not token:
        return
    stored_in_keyring = _save_secret_token(
        token,
        keyring_backend=_keyring_available(),
        config_path=CONFIG_PATH,
        service_name=KEYRING_SERVICE,
        username=KEYRING_USERNAME,
    )
    if not stored_in_keyring:
        print(f"     ! keyring backend unavailable, "
              f"storing HF token in plaintext at {CONFIG_PATH}", flush=True)


def diarize_audio(audio_path: str, hf_token: str) -> list[dict]:
    """Run pyannote speaker-diarization-3.1. Returns [{start,end,speaker}, ...]."""
    from pyannote.audio import Pipeline
    print("[3b] Running speaker diarization (pyannote)...", flush=True)
    # Initialise pipeline to None before the try so the finally block does not
    # crash with NameError if from_pretrained raises.
    pipeline = None
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )
        try:
            import torch
            if torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
        except Exception:
            pass
        diarization = pipeline(audio_path)
        segments: list[dict] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({"start": float(turn.start), "end": float(turn.end), "speaker": str(speaker)})
        speakers = sorted({s["speaker"] for s in segments})
        print(f"     → {len(segments)} diarization turns | {len(speakers)} speakers: {', '.join(speakers)}", flush=True)
        return segments
    finally:
        with contextlib.suppress(Exception):
            if pipeline is not None:
                del pipeline
            import torch
            torch.cuda.empty_cache()


def assign_speakers(whisper_segments: list[dict], diar_segments: list[dict]) -> list[dict]:
    """For each Whisper segment, assign the speaker with the largest temporal overlap."""
    if not diar_segments:
        return whisper_segments
    for seg in whisper_segments:
        s_start = seg["start"]
        s_end = seg["end"]
        best_speaker = None
        best_overlap = 0.0
        for d in diar_segments:
            overlap = max(0.0, min(s_end, d["end"]) - max(s_start, d["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d["speaker"]
        if best_speaker is not None:
            seg["speaker"] = best_speaker
    return whisper_segments


from videotranslator.pipeline_runner import (  # noqa: E402
    PipelineRuntime as _PipelineRuntime,
    translate_video as _translate_video_impl,
)


def _build_pipeline_runtime() -> _PipelineRuntime:
    return _PipelineRuntime(
        languages=LANGUAGES,
        lang_expansion=LANG_EXPANSION,
        suggest_xtts_speed=_suggest_xtts_speed,
        default_videos_dir=_default_videos_dir,
        extract_audio=extract_audio,
        separate_audio=separate_audio,
        run_ffmpeg=_run_ffmpeg,
        transcribe=transcribe,
        split_on_punctuation=_split_on_punctuation,
        diarize_audio=diarize_audio,
        assign_speakers=assign_speakers,
        merge_short_segments=_merge_short_segments,
        repair_split_sentences=_repair_split_sentences,
        expand_tight_slots=_expand_tight_slots,
        add_quality_flag=_add_quality_flag,
        flag_whisper_suspicious=_FLAG_WHISPER_SUSPICIOUS,
        estimate_p90_ratio=_estimate_p90_ratio,
        tts_speed_factor_for=_tts_speed_factor_for,
        classify_difficulty=_classify_difficulty,
        resolve_difficulty_profile=_resolve_difficulty_profile,
        format_profile_log=_format_profile_log,
        translate_segments=translate_segments,
        generate_tts_xtts=generate_tts_xtts,
        generate_tts=generate_tts,
        build_dubbed_track=build_dubbed_track,
        has_enough_faces=_has_enough_faces,
        apply_lipsync=apply_lipsync,
    )


def translate_video(
    video_in: str,
    output: str | None = None,
    model: str = "small",
    lang_source: str = "auto",
    lang_target: str = DEFAULT_LANG,
    voice: str | None = None,
    tts_rate: str = "+0%",
    no_subs: bool = False,
    subs_only: bool = False,
    no_demucs: bool = False,
    translation_engine: str = "google",
    deepl_key: str = "",
    segments_override: list[dict] | None = None,
    tts_engine: str = "edge",
    use_diarization: bool = False,
    hf_token: str = "",
    use_lipsync: bool = False,
    xtts_speed: float | None = None,
    ollama_model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    ollama_slot_aware: bool = True,
    ollama_thinking: bool = False,
    ollama_document_context: bool = True,
    slot_expansion: bool = True,
    sentence_repair: bool = True,
    overlap_fade_enabled: bool = True,
    whisper_sanity: bool = True,
    difficulty_profile_enabled: bool = True,
    difficulty_override: str | None = None,
    hotwords: list[str] | None = None,
    ollama_use_cove: bool = True,
    keep_original_audio: bool = True,
    output_dir: str | None = None,
) -> dict:
    """Compatibility wrapper for the modular pipeline runner."""
    return _translate_video_impl(
        video_in=video_in,
        output=output,
        model=model,
        lang_source=lang_source,
        lang_target=lang_target,
        voice=voice,
        tts_rate=tts_rate,
        no_subs=no_subs,
        subs_only=subs_only,
        no_demucs=no_demucs,
        translation_engine=translation_engine,
        deepl_key=deepl_key,
        segments_override=segments_override,
        tts_engine=tts_engine,
        use_diarization=use_diarization,
        hf_token=hf_token,
        use_lipsync=use_lipsync,
        xtts_speed=xtts_speed,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        ollama_slot_aware=ollama_slot_aware,
        ollama_thinking=ollama_thinking,
        ollama_document_context=ollama_document_context,
        slot_expansion=slot_expansion,
        sentence_repair=sentence_repair,
        overlap_fade_enabled=overlap_fade_enabled,
        whisper_sanity=whisper_sanity,
        difficulty_profile_enabled=difficulty_profile_enabled,
        difficulty_override=difficulty_override,
        hotwords=hotwords,
        ollama_use_cove=ollama_use_cove,
        keep_original_audio=keep_original_audio,
        output_dir=output_dir,
        runtime=_build_pipeline_runtime(),
    )


# ═══════════════════════════════════════════════════════════
#  GUI HELPERS
# ═══════════════════════════════════════════════════════════

def check_dependencies():
    return _find_missing_dependencies(REQUIRED_PACKAGES)


_thread_local = threading.local()


class _GlobalRedirect(io.TextIOBase):
    """Installed once at GUI startup. Routes print() to the per-thread _TkStreamRedirect
    if one is active for the calling thread, otherwise passes through to the original stream."""

    def __init__(self, original):
        super().__init__()
        self._original = original

    def writable(self): return True

    def write(self, s):
        redir = getattr(_thread_local, "redirect", None)
        if redir is not None:
            return redir.write(s)
        if self._original is None:
            # pythonw: sys.stdout/sys.stderr are None, so library output from
            # threads without a GUI redirect (tqdm, warnings) is dropped
            # instead of raising (spec R9).
            return len(s)
        return self._original.write(s)

    def flush(self):
        redir = getattr(_thread_local, "redirect", None)
        if redir is not None:
            redir.flush()
        elif self._original is not None:
            self._original.flush()

    def fileno(self):
        if self._original is None:
            raise io.UnsupportedOperation("fileno")
        return self._original.fileno()


class _TkStreamRedirect(io.TextIOBase):
    """Per-thread redirect to the GUI log widget with 100ms throttle to avoid flooding Tk."""

    def __init__(self, tk_root, on_write):
        super().__init__()
        self._root      = tk_root
        self._on_write  = on_write
        self._buf: list[str] = []
        self._flush_pending  = False

    def writable(self): return True

    def write(self, s):
        if not s:
            return 0
        self._buf.append(s)
        if not self._flush_pending:
            self._flush_pending = True
            try:
                self._root.after(100, self._flush_buf)
            except RuntimeError:
                pass
        return len(s)

    def _flush_buf(self):
        self._flush_pending = False
        buf, self._buf = self._buf, []  # atomic swap under GIL - safe against concurrent append()
        if buf:
            try:
                self._on_write("".join(buf))
            except Exception:
                pass

    def flush(self):
        buf, self._buf = self._buf, []  # atomic swap
        self._flush_pending = False
        if buf:
            try:
                self._root.after(0, self._on_write, "".join(buf))
            except RuntimeError:
                # main thread already in destroy(): Tk unavailable
                pass
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
#  SUBTITLE EDITOR
# ═══════════════════════════════════════════════════════════

class SubtitleEditor(tk.Toplevel):
    def __init__(self, parent, segments: list[dict], on_confirm, ui_s=None,
                 on_seek=None, on_change=None):
        super().__init__(parent)
        self._s = ui_s if callable(ui_s) else (lambda k: UI_STRINGS["it"].get(k, k))
        self.title(self._s("editor_title"))
        self.configure(bg=BG)
        self.geometry("900x600")
        self.segments   = [s.copy() for s in segments]
        self.on_confirm = on_confirm
        self._on_seek = on_seek
        self._on_change = on_change
        self._change_after_id = None

        # TASK 5C: filter state - when True, only segments with at least one
        # quality flag are shown. Useful on long videos (200+ segments) where
        # only a handful are flagged for review.
        self._filter_flagged_only = tk.BooleanVar(value=False)
        # Tooltip handle (for hover-over flag explanation). Created lazily.
        self._tooltip: tk.Toplevel | None = None
        self._tooltip_iid: str | None = None

        tk.Label(self, text=self._s("editor_hint"),
                 bg=BG, fg=FG2, font="VT.Base").pack(pady=(10, 4))

        # ── Filter / summary bar ──────────────────────────────────────
        # Counts how many segments carry each flag, plus a checkbox to
        # restrict the view to flagged rows. When no segment is flagged
        # we still show the bar (with all counts at 0) so the layout is
        # stable across runs.
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=12, pady=(2, 4))
        flag_count = self._count_flags()
        summary = self._s("editor_flag_summary").format(
            total=len(self.segments),
            flagged=flag_count["any"],
            length=flag_count[_FLAG_LENGTH_UNFIT],
            whisper=flag_count[_FLAG_WHISPER_SUSPICIOUS],
            fallback=flag_count[_FLAG_TRANSLATION_FALLBACK],
        )
        tk.Label(bar, text=summary, bg=BG, fg=FG2,
                 font="VT.Base").pack(side="left")
        # The Tk Checkbutton on a dark theme needs `selectcolor=BG` so the
        # tick box doesn't render as a bright white square. `activebackground`
        # keeps the hover state in-theme.
        chk = tk.Checkbutton(
            bar,
            text=self._s("editor_filter_show_flagged_only"),
            variable=self._filter_flagged_only,
            command=self._populate,
            bg=BG, fg=FG, activebackground=BG, activeforeground=FG,
            selectcolor=BG, relief="flat", borderwidth=0,
            highlightthickness=0, font="VT.Base",
        )
        # Disable the checkbox when there are zero flagged segments - toggling
        # it would blank the table, which is confusing.
        if flag_count["any"] == 0:
            chk.configure(state="disabled")
        chk.pack(side="right")

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=12, pady=4)

        cols = (self._s("editor_col_num"), self._s("editor_col_start"),
                self._s("editor_col_end"), self._s("editor_col_orig"),
                self._s("editor_col_trans"))
        self._tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for c, w in zip(cols, [40, 80, 80, 350, 350]):
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, minwidth=w)

        # TASK 5C: configure colour tags for each known quality flag. The
        # palette is defined in videotranslator.quality_flags so the GUI
        # and the pipeline stay in sync (and so the colours are unit-tested
        # for shape). Catppuccin Mocha companions to BG=#1e1e2e - high
        # saturation backgrounds with dark FG so flagged rows pop without
        # losing legibility. Tag priority is resolved by primary_flag()
        # which returns the most severe flag for the row.
        for _flag, _colours in _QUALITY_FLAG_COLOURS.items():
            self._tree.tag_configure(
                _flag,
                background=_colours["background"],
                foreground=_colours["foreground"],
            )

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._populate()
        self._tree.bind("<Double-1>", self._on_edit)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        # Hover bindings for the per-row tooltip explaining why a row is
        # flagged. Motion fires often (every pixel) but the handler is
        # cheap (identify_row + dict lookup) so the cost is negligible.
        self._tree.bind("<Motion>", self._on_tree_motion)
        self._tree.bind("<Leave>", self._on_tree_leave)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text=self._s("editor_btn_confirm"),
                  command=self._confirm,
                  bg=ACC, fg=ACC_FG, activebackground=ACC_HOVER,
                  activeforeground=ACC_FG, disabledforeground=ACC_FG,
                  font="VT.Large",
                  relief="flat", padx=16, pady=6).pack(side="left", padx=8)
        tk.Button(btn_frame, text=self._s("editor_btn_cancel"),
                  command=self.destroy,
                  bg=SEL, fg=FG, relief="flat", padx=12, pady=6).pack(side="left")

    def _count_flags(self) -> dict[str, int]:
        """Tally segments per quality flag for the summary bar."""
        out: dict[str, int] = {
            _FLAG_LENGTH_UNFIT: 0,
            _FLAG_WHISPER_SUSPICIOUS: 0,
            _FLAG_TRANSLATION_FALLBACK: 0,
            "any": 0,
        }
        for s in self.segments:
            flags = _compute_segment_quality_flags(s)
            if not flags:
                continue
            out["any"] += 1
            for f in flags:
                if f in out:
                    out[f] += 1
        return out

    def _populate(self):
        self._tree.delete(*self._tree.get_children())
        only_flagged = bool(self._filter_flagged_only.get())
        for i, s in enumerate(self.segments):
            flags = _compute_segment_quality_flags(s)
            if only_flagged and not flags:
                continue
            tags: tuple[str, ...] = ()
            primary = _primary_flag(flags)
            if primary:
                tags = (primary,)
            # iid keeps the original index so _on_edit / tooltip lookups
            # always reference the correct dict in self.segments even
            # when the filter hides intermediate rows.
            self._tree.insert("", "end", iid=str(i), values=(
                i + 1,
                f"{s['start']:.1f}s",
                f"{s['end']:.1f}s",
                s.get("text_src", s.get("text", "")),
                s["text_tgt"],
            ), tags=tags)

    def _on_select(self, _event=None):
        selected = self._tree.selection()
        if selected and self._on_seek is not None:
            try:
                self._on_seek(float(self.segments[int(selected[0])]["start"]))
            except (ValueError, KeyError, IndexError):
                pass

    def _schedule_preview_update(self):
        if self._on_change is None:
            return
        if self._change_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._change_after_id)
        self._change_after_id = self.after(500, self._flush_preview_update)

    def _flush_preview_update(self):
        self._change_after_id = None
        if self._on_change is not None:
            self._on_change(self.segments)

    def _on_edit(self, event):
        item = self._tree.identify_row(event.y)
        col  = self._tree.identify_column(event.x)
        if not item or col not in ("#4", "#5"):
            return
        idx      = int(item)
        field    = "text_src" if col == "#4" else "text_tgt"
        current  = self.segments[idx].get(field, self.segments[idx].get("text", ""))
        col_name = self._s("editor_col_orig") if col == "#4" else self._s("editor_col_trans")

        win = tk.Toplevel(self)
        win.title(self._s("editor_edit_title"))
        win.configure(bg=BG)
        win.geometry("500x120")
        tk.Label(win, text=f"{self._s('editor_seg_label').format(idx+1)} {col_name}:",
                 bg=BG, fg=FG).pack(pady=6)
        entry = tk.Entry(win, width=60, bg=FIELD, fg=FG, **_field_colors(),
                         font="VT.Base", relief="flat")
        entry.insert(0, current)
        entry.pack(padx=10)
        entry.focus()

        def save(_=None):
            self.segments[idx][field] = entry.get()
            self._populate()
            self._schedule_preview_update()
            win.destroy()

        entry.bind("<Return>", save)
        tk.Button(win, text=self._s("editor_btn_save"), command=save,
                  bg=ACC, fg=ACC_FG, activebackground=ACC_HOVER,
                  activeforeground=ACC_FG, disabledforeground=ACC_FG,
                  relief="flat", padx=10).pack(pady=6)

    def _flag_tooltip_text(self, flags: list[str]) -> str:
        """Compose the hover text for a row with one or more flags.

        When multiple flags coexist on a segment we list them in priority
        order so the most severe explanation shows first. Each line is
        the localised tooltip for one flag.
        """
        lines: list[str] = []
        # Walk the canonical priority order: severe → mild.
        for f in (
            _FLAG_TRANSLATION_FALLBACK,
            _FLAG_LENGTH_UNFIT,
            _FLAG_WHISPER_SUSPICIOUS,
        ):
            if f in flags:
                lines.append(self._s(f"editor_tooltip_{f}"))
        return "\n".join(lines)

    def _on_tree_motion(self, event) -> None:
        iid = self._tree.identify_row(event.y)
        if not iid:
            self._hide_tooltip()
            return
        if iid == self._tooltip_iid:
            return  # already showing the tooltip for this row
        try:
            idx = int(iid)
        except ValueError:
            self._hide_tooltip()
            return
        if not (0 <= idx < len(self.segments)):
            self._hide_tooltip()
            return
        flags = _compute_segment_quality_flags(self.segments[idx])
        if not flags:
            self._hide_tooltip()
            return
        text = self._flag_tooltip_text(flags)
        if not text:
            self._hide_tooltip()
            return
        self._show_tooltip(event.x_root + 16, event.y_root + 12, text, iid)

    def _on_tree_leave(self, _event) -> None:
        self._hide_tooltip()

    def _show_tooltip(self, x: int, y: int, text: str, iid: str) -> None:
        # Recreate the tooltip when the bound row changes; reposition only
        # otherwise. A persistent Toplevel would flicker on Motion.
        if self._tooltip is not None and self._tooltip_iid != iid:
            self._hide_tooltip()
        if self._tooltip is None:
            tip = tk.Toplevel(self)
            tip.wm_overrideredirect(True)  # no titlebar/decoration
            tip.configure(bg=SEL, padx=2, pady=2)
            lbl = tk.Label(
                tip, text=text, bg=SEL, fg=FG,
                font="VT.Base", justify="left",
                wraplength=320,
            )
            lbl.pack()
            self._tooltip = tip
        else:
            # Update text in case priority/flag list changed for same iid.
            for child in self._tooltip.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(text=text)
                    break
        try:
            self._tooltip.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            pass
        self._tooltip_iid = iid

    def _hide_tooltip(self) -> None:
        if self._tooltip is not None:
            try:
                self._tooltip.destroy()
            except tk.TclError:
                pass
            self._tooltip = None
        self._tooltip_iid = None

    def destroy(self):  # type: ignore[override]
        # Make sure the orphan tooltip Toplevel is cleaned up when the
        # editor closes - otherwise it would linger as a ghost label.
        self._hide_tooltip()
        if self._change_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._change_after_id)
            self._change_after_id = None
        super().destroy()

    def _confirm(self):
        self.on_confirm(self.segments)
        self.destroy()


# ═══════════════════════════════════════════════════════════
#  MAIN GUI APP
# ═══════════════════════════════════════════════════════════


def _parse_hotwords_gui(raw: str) -> list[str]:
    """Adapter from the Tk Entry text to a normalized hotwords list.

    Wraps ``videotranslator.hotwords.parse_hotwords_string`` so the Entry
    text (comma-separated by user) becomes the list expected by
    ``translate_video(..., hotwords=...)``. Returns ``[]`` on empty
    input; the caller flips that to ``None`` to keep the decoder default.
    """
    try:
        from videotranslator.hotwords import parse_hotwords_string
        return parse_hotwords_string(raw)
    except Exception:
        return []


def _is_noisy_x11_log(line: str) -> bool:
    """True for the repetitive, harmless mpv X11 BadWindow/BadDrawable blocks.

    While embedded on X11, mpv installs a process-global Xlib error handler
    (mpv 0.41 never calls XQueryTree, so these are not window-tree queries):
    expected X errors from Tk or the GL stack surface as three-line "[mpv] X11
    error" blocks. The video renders fine. Only BadWindow/BadDrawable blocks are
    collapsed into a periodic summary; other X errors (BadMatch, BadAlloc, ...)
    are kept as real signals. The consumer logs the first full block verbatim so
    the resourceid and request code stay available for diagnosis.
    """
    low = line.lower()
    if "x11 error: badwindow" in low or "x11 error: baddrawable" in low:
        return True
    if "resourceid:" in low and "serial:" in low:
        return True
    if low.startswith("error code:") and "request code:" in low:
        return True
    return False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        _ocfg = load_config()
        self._ui_settings = _normalize_ui_settings(_ocfg, lang_codes=UI_LANG_CODES)
        # Movable panels of the settings column: id -> (outer frame, pack
        # options), current order, and the state of a drag in progress.
        self._panels = {}
        self._panel_order = _normalize_panel_order(_ocfg.get("ui_panel_order"))
        self._drag = None
        self._drag_indicator = None
        # With the "auto" theme the OS probe runs in the background: the
        # first paint uses the value cached by the previous run.
        self._theme = _ThemeManager(
            self, module_globals=globals(),
            system_dark=_cached_system_dark(_ocfg),
            on_system_dark=self._remember_system_dark,
            on_reapplied=self._refresh_theme_dependents)
        self._theme.apply(self._ui_settings, recolor=False)
        self.title("Video Translator AI")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._set_window_icon()

        self._ui_lang   = tk.StringVar(value=self._ui_settings["ui_lang"])
        self._ui_theme_var  = tk.StringVar(value=self._ui_settings["ui_theme"])
        self._ui_accent_var = tk.StringVar(value=self._ui_settings["ui_accent"])
        self._ui_scale_var  = tk.StringVar(value=self._ui_settings["ui_scale"])
        self._settings_win  = None
        self._model     = tk.StringVar(value=DEFAULT_WHISPER_MODEL)
        self._lang_src  = tk.StringVar(value="auto")
        self._lang_tgt  = tk.StringVar(value="it")
        self._voice     = tk.StringVar(value=LANGUAGES["it"]["voices"][0])
        self._tts_rate  = tk.IntVar(value=0)
        self._subs_only = tk.BooleanVar(value=False)
        self._no_subs   = tk.BooleanVar(value=False)
        self._no_demucs = tk.BooleanVar(value=False)
        self._edit_subs = tk.BooleanVar(value=False)
        self._use_xtts  = tk.BooleanVar(value=False)
        self._use_lipsync = tk.BooleanVar(value=False)
        # Translation engine: "google" | "deepl" | "marian" | "llm_ollama"
        self._translation_engine = tk.StringVar(value="google")
        self._deepl_key_var      = tk.StringVar()
        # Ollama LLM config (v2.0) - preset da config JSON se presente
        self._ollama_model_var   = tk.StringVar(
            value=_ocfg.get("ollama_model", "qwen3:8b")
        )
        self._ollama_url_var     = tk.StringVar(
            value=_ocfg.get("ollama_url", "http://localhost:11434")
        )
        self._ollama_slot_aware  = tk.BooleanVar(
            value=_ocfg.get("ollama_slot_aware", True)
        )
        # Thinking mode on Qwen3: default OFF (fast). When True the model
        # deliberates step-by-step (~10x slower, reduces idiom/grammar errors).
        self._ollama_thinking    = tk.BooleanVar(
            value=_ocfg.get("ollama_thinking", False)
        )
        # Diarization: the HF token is persisted in the system keyring (with
        # automatic migration from the old legacy JSON).
        self._use_diarization = tk.BooleanVar(value=False)
        self._hf_token_var    = tk.StringVar(value=load_hf_token())
        # Hotwords: comma-separated list of brand/proper nouns/jargon to bias
        # Whisper decoding. Always visible (no gate). See videotranslator.hotwords.
        self._hotwords_var    = tk.StringVar(
            value=str(_ocfg.get("hotwords", ""))
        )
        # Active quality preset (Fast / Balanced / Studio / Cinematic) - maps
        # onto the existing Tk vars; no new pipeline state is introduced.
        self._active_profile = tk.StringVar(value="balanced")
        # Summary line shown in the START card (lang pair + engine + profile).
        self._summary_var = tk.StringVar(value="")
        self._running    = False
        self._destroying = False
        # Guard re-entrancy: during the async Ollama setup (detect / install
        # / start daemon / pull model) block duplicate triggers from Start /
        # Download. We do not use `_running` because that flag fires only when
        # the real pipeline starts, not during the pre-flight.
        self._ollama_setup_in_flight = False
        self._batch_files: list[str] = []
        self._url_placeholder_active = True
        self._pending_pkgs_after_ffmpeg: list[str] = []
        self._preflight_running = False
        # Integrated player (spec 9 P1): the last availability status, the
        # install request computed with it, and the flag shared by every
        # component install (startup ffmpeg/pip installs set it too).
        self._installing = False
        self._player_status = None
        self._player_install_request = None
        self._player_settings = _player_settings_module.normalize_player_settings(
            _ocfg, sys_platform=sys.platform)
        self._player_bridge = _player_engine.EventBridge()
        self._player_mixer = _player_engine.VolumeMixer(
            user_volume=self._player_settings.volume,
            muted=self._player_settings.muted)
        self._player_clock = _player_engine.PlaybackClock()
        self._player_backend = None
        self._voice_backend = None            # second mpv for live dubbed voice (P5)
        self._player_controller = _player_core.PlayerController(
            None, self._player_settings, on_change=self._on_player_state,
            save=save_config)
        self._player_results: list[_player_core.MediaItem] = []
        self._editor_open = False
        self._editor_preview_srt: str | None = None
        self._player_init_running = False
        self._player_init_thread = None
        self._player_poll_after = None
        self._player_guard = None
        self._player_vo_profile = self._player_settings.vo_profile
        self._player_vo_retries = 0
        self._player_loaded_at = None
        self._player_video_params_seen = False
        self._player_log_lines: list[str] = []
        self._mpv_x11_noise = 0        # count of suppressed harmless X11 errors
        self._mpv_x11_noise_at = 0.0   # last time a summary was logged
        self._player_fallback_notice_pending = False
        self._player_release_pending = False
        self._player_fullscreen = False
        # Live real-time translation (spec 4, 5.9): one session at a time, driven
        # by the LiveBar and rendered onto the player's overlay via video.rt.
        self._live_session = None
        self._live_poll_after = None
        self._live_stopping = False
        self._live_resolving = False
        self._pending_live_source = None
        self._close_started_at = None
        self._close_done = None

        self._build_ui()
        # Restore log panel visibility from config (default collapsed in the
        # modernized GUI - the log starts hidden unless config opts in).
        self._log_visible = bool(_ocfg.get("ui_log_visible", False))
        if not self._log_visible:
            self._log_container.grid_remove()
            self._btn_log_toggle.configure(text=self._s("btn_log_show"))
        else:
            self._btn_log_toggle.configure(text=self._s("btn_log_hide"))
        for problem in _PLAYER_STRING_PROBLEMS:
            self._log_write(f"[!] Player strings: {problem}\n")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Minimum window size + reasonable default geometry so the window
        # remains usable on small displays (1366×768, 1280×720) and at
        # Windows scaling 125%/150%. The card column is wrapped in its own
        # Canvas with a vertical Scrollbar (see `_build_ui`), so even when
        # the window is shorter than the cards the user can scroll to reach
        # every control. Header, player pane, log and progress bar stay
        # outside that canvas and remain visible at all times.
        self.minsize(900, 600)
        self.geometry("1100x780")
        self.after(100, self._fit_to_screen)
        self.after(200, self._check_deps_on_start)
        self.after(800, self._upgrade_ytdlp_in_background)
        self.after(1500, self._refresh_player_status)
        self._optional_checked = False

        # Install global redirect once - routes print() to per-thread GUI log
        sys.stdout = _GlobalRedirect(sys.stdout)
        sys.stderr = _GlobalRedirect(sys.stderr)

    def _set_window_icon(self) -> None:
        """Set the window icon from the bundled assets folder.

        Gracefully falls back to the default Tk icon if assets/ is missing or
        the image cannot be loaded - common e.g. when the GUI is launched
        from a source checkout without the assets committed yet.
        """
        here = Path(__file__).resolve().parent
        candidates_ico = [here / "assets" / "icon.ico", here / "icon.ico"]
        candidates_png = [here / "assets" / "icon.png",
                          here / "assets" / "icon_256.png",
                          here / "icon.png"]

        # Windows honours .ico best via iconbitmap
        if sys.platform.startswith("win"):
            for p in candidates_ico:
                if p.exists():
                    try:
                        self.iconbitmap(default=str(p))
                        return
                    except tk.TclError:
                        pass

        # Cross-platform fallback: iconphoto with a PNG (requires PhotoImage)
        for p in candidates_png:
            if p.exists():
                try:
                    img = tk.PhotoImage(file=str(p))
                    self.iconphoto(True, img)
                    # Keep a reference to prevent GC
                    self._icon_img = img
                    return
                except tk.TclError:
                    continue

    def _fit_to_screen(self):
        self.update_idletasks()
        # Center on the monitor the window opens on (the one under the pointer),
        # not the middle of the whole virtual desktop, which on a multi-monitor
        # setup straddles two screens or lands on the wrong one.
        full = (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())
        try:
            px, py = self.winfo_pointerxy()
        except tk.TclError:
            px, py = full[2] // 2, full[3] // 2
        mx, my, mw, mh = _platforms.monitor_bounds_at(px, py, fallback=full)
        # Prefer the explicit geometry hint (1100x780) over reqsize, because the
        # form lives inside a Canvas-wrapped frame and reqwidth from the Canvas
        # under-reports the form's actual width. Clamp to this monitor, floor at
        # a usable minimum (matches `self.minsize`) unless the monitor is smaller.
        win_w = min(max(1100, self.winfo_reqwidth()), mw - 40)
        win_w = max(win_w, min(900, mw - 40))
        win_h = min(max(780, self.winfo_reqheight()), mh - 80)
        win_h = max(win_h, min(600, mh - 80))
        x = mx + max(0, (mw - win_w) // 2)
        y = my + max(0, (mh - win_h) // 2 - 20)
        # Center first so the window sits on the right monitor, keeping this as
        # the restore size, then maximize to fill THAT screen.
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.update_idletasks()
        self._maximize_window((mx, my, mw, mh))

    def _maximize_window(self, bounds) -> None:
        """Expand to fill the current monitor, cross-platform.

        On Windows ``state("zoomed")`` maximizes and keeps the taskbar visible.
        On X11 the ``-zoomed`` hint is unreliable (xfwm4 accepts it silently
        without maximizing), so the window is sized to the monitor explicitly,
        which always works and stays on the screen it was centered on.
        """
        try:
            self.state("zoomed")
            return
        except tk.TclError:
            pass
        mx, my, mw, mh = bounds
        self.geometry(f"{mw}x{mh}+{mx}+{my}")

    def _s(self, key: str) -> str:
        # Fallback chain: current UI lang → it → en → key (literal)
        # Required when a key was added only to it/en (e.g. incrementally
        # introduced features) to prevent users of the other 24 languages from
        # seeing raw key names instead of a translated label.
        lang = self._ui_lang.get()
        for bucket in (UI_STRINGS.get(lang, {}), UI_STRINGS["it"], UI_STRINGS["en"]):
            if key in bucket:
                return bucket[key]
        return key

    # ── Dependency check ─────────────────────────────────────────────────────

    def _check_deps_on_start(self):
        missing_pkgs, missing_bins = check_dependencies()
        if not missing_pkgs and not missing_bins:
            # Nothing required to install - safe to check optional now
            self.after(300, self._check_optional_deps)
            return
        # Serialize: install ffmpeg first, then pip packages in _ffmpeg_done callback
        self._pending_pkgs_after_ffmpeg = missing_pkgs
        if missing_bins:
            self._install_ffmpeg()
        elif missing_pkgs:
            self._install_deps(missing_pkgs)

    def _install_ffmpeg(self):
        self._running = True
        self._installing = True
        self._btn.configure(state="disabled", text=self._s("btn_installing"))
        self._progress.start(12)
        self._log_write("[*] ffmpeg not found - installing automatically...\n")

        def do():
            ok = False
            if sys.platform == "win32":
                ok = self._install_ffmpeg_windows()
            else:
                ok = self._install_ffmpeg_linux()
            self.after(0, self._ffmpeg_done, ok)

        threading.Thread(target=do, daemon=True).start()

    def _install_ffmpeg_linux(self) -> bool:
        # Detect package manager
        for mgr, update_cmd, install_cmd in [
            ("apt-get", ["apt-get", "update"], ["apt-get", "install", "-y", "ffmpeg"]),
            ("dnf",     ["dnf",     "makecache"], ["dnf", "install", "-y", "ffmpeg"]),
            ("pacman",  ["pacman",  "-Sy"],     ["pacman", "-S", "--noconfirm", "ffmpeg"]),
        ]:
            if not shutil.which(mgr):
                continue
            # Try pkexec first (graphical sudo), fall back to sudo
            for prefix in (["pkexec"], ["sudo", "-n"], ["sudo"]):
                # Step 1: update package cache
                update = prefix + update_cmd
                self.after(0, self._log_write, f"    Running: {' '.join(update)}\n")
                with subprocess.Popen(
                    update, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, text=True,
                    encoding="utf-8", errors="replace",
                ) as proc:
                    try:
                        for line in proc.stdout:
                            line = line.rstrip()
                            if line:
                                self.after(0, self._log_write, f"    {line}\n")
                        proc.wait()
                    except Exception:
                        proc.kill(); proc.wait()
                    rc_update = proc.returncode
                if rc_update != 0:
                    continue  # try next prefix (stdout already closed by context manager)
                # Step 2: install ffmpeg
                full_cmd = prefix + install_cmd
                self.after(0, self._log_write, f"    Running: {' '.join(full_cmd)}\n")
                with subprocess.Popen(
                    full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, text=True,
                    encoding="utf-8", errors="replace",
                ) as proc:
                    try:
                        for line in proc.stdout:
                            line = line.rstrip()
                            if line:
                                self.after(0, self._log_write, f"    {line}\n")
                        proc.wait()
                    except Exception:
                        proc.kill(); proc.wait()
                    rc_install = proc.returncode
                if rc_install == 0:
                    return True
        return False

    def _install_ffmpeg_windows(self) -> bool:
        import urllib.request, zipfile, ctypes
        # Download ffmpeg essentials build from GitHub releases
        ffmpeg_url  = "https://github.com/BtbN/ffmpeg-builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        install_dir = Path.home() / ".local" / "bin" / "ffmpeg"
        install_dir.mkdir(parents=True, exist_ok=True)
        zip_path    = install_dir / "ffmpeg.zip"

        self.after(0, self._log_write, "    Downloading ffmpeg (~60 MB)...\n")
        try:
            # Stream download via urlopen + copyfileobj so we can enforce a
            # per-read timeout. urlretrieve has no timeout knob and will hang
            # indefinitely on a slow/stalled mirror. Pattern mirrors
            # _ensure_wav2lip_assets which downloads the Wav2Lip model.
            from urllib.request import Request, urlopen
            req = Request(ffmpeg_url, headers={"User-Agent": "VideoTranslatorAI/1.0"})
            downloaded = 0
            with urlopen(req, timeout=120) as r, open(zip_path, "wb") as out:
                total = int(r.headers.get("Content-Length") or 0)
                chunk = 64 * 1024
                while True:
                    buf = r.read(chunk)
                    if not buf:
                        break
                    out.write(buf)
                    downloaded += len(buf)
                    if total > 0:
                        pct = min(100, downloaded * 100 // total)
                        self.after(0, self._log_write, f"\r    Downloading... {pct}%")
            self.after(0, self._log_write, "\n    Extracting...\n")
            install_dir_resolved = install_dir.resolve()
            with zipfile.ZipFile(zip_path, "r") as z:
                for member in z.namelist():
                    if member.endswith(("ffmpeg.exe", "ffprobe.exe")):
                        # Guard against zip slip
                        # NOTE: Path.is_relative_to() requires Python 3.9+
                        member_resolved = (install_dir / member).resolve()
                        if not member_resolved.is_relative_to(install_dir_resolved):
                            continue
                        z.extract(member, install_dir)
                        src = install_dir / member
                        dst = install_dir / Path(member).name
                        if src != dst:
                            shutil.move(str(src), str(dst))
            zip_path.unlink(missing_ok=True)
            # Add to user PATH via registry
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
            try:
                old_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                old_path = ""
            if str(install_dir) not in old_path:
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ,
                                  old_path + ";" + str(install_dir))
            winreg.CloseKey(key)
            os.environ["PATH"] += os.pathsep + str(install_dir)
            return True
        except Exception as e:
            self.after(0, self._log_write, f"    ! ffmpeg download failed: {e}\n")
            return False

    def _ffmpeg_done(self, ok: bool):
        self._running = False
        self._installing = False
        self._progress.stop()
        if ok:
            self._log_write("[✓] ffmpeg installed successfully.\n")
        else:
            self._log_write(
                "[✗] Could not install ffmpeg automatically.\n"
                "    Linux:   sudo apt install ffmpeg\n"
                "    Windows: https://ffmpeg.org/download.html\n"
            )
        # Chain: install pending Python packages now that ffmpeg is done
        pending = self._pending_pkgs_after_ffmpeg
        self._pending_pkgs_after_ffmpeg = []
        if pending:
            self._install_deps(pending)
        else:
            self._btn.configure(state="normal", text=self._s("btn_start"))
            self.after(300, self._check_optional_deps)

    def _install_deps(self, packages):
        self._running = True
        self._installing = True
        self._btn.configure(state="disabled", text=self._s("btn_installing"))
        self._progress.start(12)
        self._log_write(f"[*] Installing: {', '.join(packages)}\n")

        def do():
            cmd = [sys.executable, "-m", "pip", "install",
                   "--break-system-packages", "--no-color"] + packages
            # encoding="utf-8" + errors="replace" is critical on Windows:
            # without it, text=True falls back to locale.getpreferredencoding()
            # (cp1252 on Italian/English installs) and pip's tqdm progress bars
            # or non-ASCII package URLs trigger UnicodeDecodeError mid-install.
            # stdin=DEVNULL avoids inheriting a None stdin from pythonw.exe
            # on Windows (the GUI launcher has no console).
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace",
            )
            _register_subprocess(proc)
            ok = True
            # 10-minute ceiling: covers large Torch wheels on slow mirrors
            # without letting the GUI freeze forever if pip stalls.
            # NB: proc.wait(timeout=…) does not fire if pip stalls without
            # closing stdout, because the for-loop on proc.stdout blocks there.
            # A Timer that kills the process guarantees the unblock (the
            # stdout iterator raises or returns EOF as soon as the process dies).
            PIP_TIMEOUT = 600
            timed_out = {"fired": False}

            def _on_timeout():
                timed_out["fired"] = True
                with contextlib.suppress(Exception):
                    proc.kill()
                # On Windows, TerminateProcess does not always unblock a
                # pending read on the child's stdout pipe immediately -
                # close our end so the for-loop wakes up even if the OS
                # is slow to tear down the pipe.
                with contextlib.suppress(Exception):
                    if proc.stdout is not None:
                        proc.stdout.close()

            watchdog = threading.Timer(PIP_TIMEOUT, _on_timeout)
            watchdog.daemon = True
            watchdog.start()
            try:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.after(0, self._log_write, f"    {line}\n")
                with contextlib.suppress(Exception):
                    proc.wait(timeout=30)
                if timed_out["fired"]:
                    self.after(0, self._log_write,
                               f"    ! pip install timed out after {PIP_TIMEOUT}s - aborting.\n")
                    ok = False
                else:
                    ok = proc.returncode == 0
            except Exception:
                # If the timeout watchdog closed stdout the iterator raises
                # here - still print the timeout message so the user sees the
                # cause instead of a generic "Installation failed".
                if timed_out["fired"]:
                    self.after(0, self._log_write,
                               f"    ! pip install timed out after {PIP_TIMEOUT}s - aborting.\n")
                with contextlib.suppress(Exception):
                    proc.kill()
                    proc.wait(timeout=30)
                ok = False
            finally:
                watchdog.cancel()
                _unregister_subprocess(proc)
            self.after(0, self._install_done, ok, packages)

        threading.Thread(target=do, daemon=True).start()

    def _install_done(self, ok, packages):
        self._running = False
        self._installing = False
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        if ok:
            self._log_write(f"[✓] Installed: {', '.join(packages)}\n")
        else:
            self._log_write("[✗] Installation failed. Check the log above for details.\n")
        # Required install chain finished - safe to check optional packages now
        self.after(300, self._check_optional_deps)

    def _upgrade_ytdlp_in_background(self):
        """Silently upgrade yt-dlp in a daemon thread; logs only if a new version is installed.

        Respects the `yt_dlp_auto_upgrade` flag in config (default True). If the user
        sets it to False (e.g. on PEP 668 systems where they do not want the env
        modified), the upgrade is skipped silently.
        """
        # Check user consent via config flag (default: enabled for backwards compat)
        try:
            _cfg = load_config()
        except Exception:
            _cfg = {}
        if not _cfg.get("yt_dlp_auto_upgrade", True):
            return  # user opted out

        import re as _re

        def do():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade",
                     "--break-system-packages", "--no-color", "yt-dlp"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    timeout=120,
                )
                for line in (result.stdout or "").splitlines():
                    if "Successfully installed" in line:
                        # m3: regex that avoids a trailing dot (e.g. "yt-dlp-2024.10.")
                        m = _re.search(r"yt[-_]dlp-([0-9]+(?:\.[0-9]+)+)", line)
                        if m and not self._destroying:
                            self.after(0, self._log_write,
                                       f"[✓] yt-dlp aggiornato a {m.group(1)}\n")
                        break
            except Exception:
                pass  # upgrade failure is non-fatal

        threading.Thread(target=do, daemon=True).start()

    def _check_optional_deps(self):
        """Show one-time popup if optional packages are missing; let user choose to install."""
        if self._optional_checked:
            return
        self._optional_checked = True

        # TASK 2C-2: non-blocking hint for Rubber Band CLI on Linux.
        # It is a system binary (apt/dnf/pacman), not installable via pip,
        # so it does not belong in the OPTIONAL_PACKAGES popup. Log only:
        # if missing, build_dubbed_track will still use atempo (no regression).
        if sys.platform.startswith("linux") and shutil.which("rubberband") is None:
            self._log_write(
                "[i] Optional: install Rubber Band CLI for higher-quality "
                "audio stretching in the 1.15-1.50 ratio band:\n"
                "    sudo apt install rubberband-cli  "
                "(or your distro equivalent)\n"
            )

        def _is_present(mod: str) -> bool:
            aliases = _OPTIONAL_ALIASES.get(mod, [mod])
            return any(importlib.util.find_spec(a) is not None for a in aliases)

        missing = [
            (mod, pip_pkgs, desc)
            for mod, (pip_pkgs, desc) in OPTIONAL_PACKAGES.items()
            if not _is_present(mod)
        ]
        if not missing:
            return

        # Deduplicate by primary pip package name; collect all requirements to install
        seen: set[str] = set()
        items: list[tuple[list[str], str]] = []
        for _mod, pip_pkgs, desc in missing:
            key = pip_pkgs[0]
            if key not in seen:
                seen.add(key)
                items.append((pip_pkgs, desc))

        names_str = "\n".join(f"  • {pkgs[0]} - {desc}" for pkgs, desc in items)
        answer = messagebox.askyesno(
            "Pacchetti opzionali mancanti",
            f"I seguenti pacchetti opzionali non sono installati:\n\n{names_str}\n\n"
            "Vuoi installarli adesso? (operazione in background)",
            parent=self,
        )
        if answer:
            all_pkgs = [pkg for pkgs, _ in items for pkg in pkgs]
            self._install_deps(all_pkgs)
        else:
            self._log_write("[i] Pacchetti opzionali saltati. Puoi installarli manualmente.\n")

    # ── UI builder ───────────────────────────────────────────────────────────

    # ── GUI style helpers ──────────────────────────────────────────────────

    def _status_badge(self, parent, text, color):
        """Discreet status indicator: coloured dot + label (header)."""
        f = tk.Frame(parent, bg=BG)
        tk.Label(f, text="●", bg=BG, fg=color, font="VT.Small").pack(side="left")
        tk.Label(f, text=text, bg=BG, fg=FG2, font="VT.Small").pack(side="left", padx=(3, 0))
        return f

    def _flat_btn(self, parent, primary=False, **kwargs):
        """Flat button with a 1 px border. Returns (wrap_frame, button).

        ``primary`` renders the accent-filled call-to-action variant. Hover
        colours are read from the module globals at event time, so they
        follow live theme changes.
        """
        kwargs.pop("bg", None)
        kwargs.pop("activebackground", None)
        kwargs.pop("activeforeground", None)
        # Compatibility shim: drop the legacy "glow" keyword of old call sites
        kwargs.pop("glow", None)
        fg = kwargs.pop("fg", ACC_FG if primary else FG)
        cursor = kwargs.pop("cursor", "hand2")
        wrap = tk.Frame(parent, bg=ACC if primary else BORDER, padx=1, pady=1)
        btn = tk.Button(
            wrap,
            bg=ACC if primary else BTN,
            fg=fg,
            activebackground=ACC_HOVER if primary else BORDER,
            activeforeground=ACC_FG if primary else FG,
            disabledforeground=ACC_FG if primary else FG2,
            relief="flat", bd=0, highlightthickness=0,
            cursor=cursor,
            font=kwargs.pop("font", "VT.Bold" if primary else "VT.Base"),
            padx=kwargs.pop("padx", 10), pady=kwargs.pop("pady", 4),
            **kwargs,
        )
        btn.pack(fill="both", expand=True)

        def _enter(_e, b=btn, p=primary):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=ACC_HOVER if p else BORDER)

        def _leave(_e, b=btn, p=primary):
            b.configure(bg=ACC if p else BTN)

        btn.bind("<Enter>", _enter)
        btn.bind("<Leave>", _leave)
        return wrap, btn

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
        """Surface card with a 1 px border; returns the inner padded frame."""
        outer = tk.Frame(parent, bg=SURFACE, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=BORDER)
        outer.pack(fill="x", **pack)
        inner = tk.Frame(outer, bg=SURFACE)
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
            decomposed = unicodedata.normalize("NFD", upper)
            stripped = "".join(ch for ch in decomposed if ch != "\u0301")
            upper = unicodedata.normalize("NFC", stripped)
        return upper

    def _section_title(self, parent, text):
        """Small upper-case section label in muted colour.

        Returns ``(frame, label)``: the caller keeps ``label`` to retext it
        on a UI language change (``_apply_lang``).
        """
        bg = parent.cget("bg") if "bg" in parent.keys() else SURFACE
        f = tk.Frame(parent, bg=bg)
        lbl = tk.Label(f, text=self._title_upper(text, self._ui_lang.get()), bg=bg, fg=FG2,
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
        hdr = tk.Frame(inner, bg=SURFACE, cursor="fleur")
        hdr.pack(fill="x", pady=(0, 8) if title else (0, 2))
        title_lbl = None
        if title:
            title_frame, title_lbl = self._section_title(hdr, title)
            title_frame.pack(side="left")
        grip = tk.Label(hdr, text="≡", bg=SURFACE, fg=FG2,
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
            ind = self._drag_indicator = tk.Frame(self._right_pane, height=3)
        if not self._pointer_over_column(event.x_root):
            # Leaving the column sideways cancels the drop (release does nothing).
            d["index"] = None
            ind.pack_forget()
            return
        idx = _drop_index(event.y_root, self._panel_spans(d["pid"]))
        d["index"] = idx
        ind.configure(bg=ACC)
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
        new_order = _move_panel(self._panel_order, d["pid"], d["index"])
        if new_order != self._panel_order:
            self._panel_order = new_order
            self._repack_panels()
            save_config({"ui_panel_order": new_order})

    def _repack_panels(self):
        """Re-pack the registered panels following ``self._panel_order``."""
        ordered = [pid for pid in self._panel_order if pid in self._panels]
        for pid in ordered:
            self._panels[pid][0].pack_forget()
        for pid in ordered:
            outer, opts = self._panels[pid]
            outer.pack(fill="x", **opts)

    def _make_accordion_section(self, parent, title_text):
        """Return (outer_frame, body_frame, arrow_label, title_label). Starts
        collapsed. The caller keeps ``title_label`` to retext it on a UI
        language change (``_apply_lang``).

        A separator is drawn above every section but the first one; the
        card's drag header does not count as a section."""
        first = not any(getattr(c, "_is_accordion_section", False)
                        for c in parent.winfo_children())
        outer = tk.Frame(parent, bg=SURFACE)
        outer._is_accordion_section = True
        outer.pack(fill="x", pady=1)
        if not first:
            tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")
        hdr = tk.Frame(outer, bg=SURFACE, cursor="hand2")
        hdr.pack(fill="x")
        arrow_lbl = tk.Label(hdr, text="▸", bg=SURFACE, fg=FG2, font="VT.Base", width=2)
        arrow_lbl.pack(side="left")
        title_lbl = tk.Label(hdr, text=title_text, bg=SURFACE, fg=FG, font="VT.Base")
        title_lbl.pack(side="left", padx=(2, 0), pady=6)
        body = tk.Frame(outer, bg=SURFACE, padx=24, pady=6)
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
            self._model.set(DEFAULT_WHISPER_MODEL)
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
            if name == active:
                btn.configure(bg=ACC_SOFT, fg=FG,
                              highlightthickness=1, highlightbackground=ACC)
            else:
                btn.configure(bg=BTN, fg=FG,
                              highlightthickness=1, highlightbackground=BORDER)
        if hasattr(self, "_lbl_profile_hint"):
            self._lbl_profile_hint.configure(
                text=_HINTS.get(active, ""))

    def _update_start_summary(self):
        """Rebuild the summary line shown in the START card."""
        if not hasattr(self, "_summary_var"):
            return
        try:
            src_key  = self._lang_src.get()
            tgt_key  = self._lang_tgt.get()
            src_name = SOURCE_LANGS.get(src_key, src_key)
            tgt_name = LANGUAGES.get(tgt_key, {}).get("name", tgt_key)
            eng = self._translation_engine.get()
            eng_label = {
                "google":     "Google Translate",
                "deepl":      "DeepL",
                "marian":     "MarianMT",
                "llm_ollama": "Ollama LLM",
            }.get(eng, eng)
            tts     = "XTTS v2" if self._use_xtts.get() else "Edge-TTS"
            profile = self._active_profile.get().capitalize()
            self._summary_var.set(
                f"{src_name} → {tgt_name}  ·  {eng_label}"
                f"  ·  {tts}  ·  {profile}"
            )
        except Exception:
            pass

    # ── _build_ui sub-methods ───────────────────────────────────────────────

    def _build_header(self, parent):
        """Top header bar: logo, subtitle, status badges, settings gear."""
        # Outer header frame: root row 0, fixed above the body (it never
        # scrolls). Kept as _header_frame so the player's fullscreen can
        # hide it (spec 3.1).
        header_wrap = tk.Frame(parent, bg=BG)
        header_wrap.grid(row=0, column=0, sticky="ew")
        header_wrap.columnconfigure(1, weight=1)
        self._header_frame = header_wrap

        header = tk.Frame(header_wrap, bg=BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew",
                    padx=20, pady=(16, 10))
        header.columnconfigure(1, weight=1)

        # ── Logo block (left) ─────────────────────────────────────────────
        logo_block = tk.Frame(header, bg=BG)
        logo_block.grid(row=0, column=0, sticky="w")
        tk.Label(logo_block, text="Video Translator AI",
                 font="VT.Title", bg=BG, fg=FG).pack(side="left")
        tk.Label(logo_block, text="Open source dubbing studio",
                 font="VT.Small", bg=BG, fg=FG2).pack(side="left", padx=(10, 0), pady=(6, 0))

        # ── Status + settings gear (right) ────────────────────────────────
        right = tk.Frame(header, bg=BG)
        right.grid(row=0, column=1, sticky="e")

        badges = tk.Frame(right, bg=BG)
        badges.pack(side="left", padx=(0, 16))
        gpu_ok = bool(shutil.which("nvidia-smi"))
        self._status_badge(badges, "GPU" if gpu_ok else "CPU",
                           OK if gpu_ok else FG2).pack(side="left", padx=(0, 12))
        self._status_badge(badges, "Ollama", FG2).pack(side="left", padx=(0, 12))
        has_wav2lip = importlib.util.find_spec("dlib") is not None
        self._status_badge(badges, "Wav2Lip",
                           OK if has_wav2lip else FG2).pack(side="left", padx=(0, 4))
        # Integrated player: grey until the background status check reports
        # (_on_player_status); the tooltip gives the reason (spec 2.3).
        self._player_badge = self._status_badge(badges, self._s("player_badge"), FG2)
        self._player_badge.pack(side="left", padx=(8, 4))
        self._player_badge_dot, self._player_badge_label = self._player_badge.winfo_children()
        self._player_badge_tip = _HoverTip(self._player_badge, self._player_status_text,
                                           colors_fn=lambda: (SEL, FG))

        # Keyboard focus ring: bd/pady 0 offset its 2 px, so the header keeps its height.
        self._btn_settings = tk.Label(right, text="⚙", bg=BG, fg=FG2, font="VT.Title",
                                      cursor="hand2", padx=4, pady=0, bd=0,
                                      highlightthickness=2,
                                      highlightbackground=BG, highlightcolor=ACC)
        self._btn_settings.pack(side="left")
        self._btn_settings.bind("<Button-1>", lambda e: self._open_settings())
        self._keyboard_operable(self._btn_settings, self._open_settings)
        self._btn_settings.bind("<Enter>", lambda e: self._btn_settings.configure(fg=FG))
        self._btn_settings.bind("<Leave>", lambda e: self._btn_settings.configure(fg=FG2))

        # Thin border line under header
        tk.Frame(header_wrap, bg=BORDER, height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew")

    def _build_input_section(self, parent):
        """Right-column INPUT card: batch list, output path, URL download."""
        inner, self._lbl_panel_input = self._panel(
            parent, "input", self._s("panel_input"), pady=(0, 10))

        # Hidden label refs required by _apply_lang (configure(text=...))
        self._lbl_video  = tk.Label(inner, text="", bg=CARD)
        self._lbl_output = tk.Label(inner, text="", bg=CARD)
        self._lbl_url    = tk.Label(inner, text="", bg=CARD)

        # ── Batch file list ────────────────────────────────────────────────
        batch_outer = tk.Frame(inner, bg=CARD)
        batch_outer.pack(fill="x", pady=(0, 4))
        batch_frame = tk.Frame(batch_outer, bg=CARD)
        batch_frame.pack(side="left", fill="both", expand=True)
        self._batch_listbox = tk.Listbox(
            batch_frame, height=4,
            bg=FIELD, fg=FG, selectbackground=ACC,
            selectforeground=ACC_FG,
            font="VT.Mono", relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACC,
            activestyle="none", exportselection=False)
        self._batch_listbox.pack(side="left", fill="both", expand=True)
        self._batch_listbox.bind("<<ListboxSelect>>", self._on_input_select)
        _sb = ttk.Scrollbar(batch_frame, command=self._batch_listbox.yview)
        self._batch_listbox.configure(yscrollcommand=_sb.set)
        _sb.pack(side="left", fill="y")
        btn_col = tk.Frame(batch_outer, bg=CARD)
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
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(4, 6))
        out_row = tk.Frame(inner, bg=CARD)
        out_row.pack(fill="x", pady=(0, 6))
        tk.Label(out_row, text=self._s("label_output"),
                 bg=CARD, fg=FG2, font="VT.Small").pack(side="left", padx=(0, 6))
        self._output_var = tk.StringVar()
        tk.Entry(out_row, textvariable=self._output_var,
                 bg=FIELD, fg=FG, **_field_colors(), relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
                 font="VT.Base").pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        _w, self._btn_browse = self._flat_btn(
            out_row, text=self._s("btn_browse"), command=self._browse_output,
            padx=8, pady=2)
        _w.pack(side="left")

        # ── Output folder (one place for every translated file) ──────────────
        dir_row = tk.Frame(inner, bg=CARD)
        dir_row.pack(fill="x", pady=(0, 6))
        self._lbl_output_dir = tk.Label(dir_row, text=self._s("label_output_dir"),
                                        bg=CARD, fg=FG2, font="VT.Small")
        self._lbl_output_dir.pack(side="left", padx=(0, 6))
        self._output_dir_var = tk.StringVar(value=load_config().get("output_dir", ""))
        _dir_entry = tk.Entry(dir_row, textvariable=self._output_dir_var,
                              bg=FIELD, fg=FG, **_field_colors(), relief="flat",
                              highlightthickness=1, highlightbackground=BORDER,
                              highlightcolor=ACC, font="VT.Base")
        _dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        # Persist manual edits when the field loses focus.
        _dir_entry.bind("<FocusOut>", lambda _e: self._persist_output_dir())
        _wdir, self._btn_output_dir = self._flat_btn(
            dir_row, text=self._s("btn_browse"), command=self._browse_output_dir,
            padx=8, pady=2)
        _wdir.pack(side="left")

        # ── URL download ───────────────────────────────────────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(0, 6))
        tk.Label(inner, text=self._s("label_url"),
                 bg=CARD, fg=FG2, font="VT.Small").pack(anchor="w", pady=(0, 2))
        url_row = tk.Frame(inner, bg=CARD)
        url_row.pack(fill="x", pady=(0, 2))
        # width=30: a small request, so the Text stretches with fill="x"
        # instead of forcing the column to its 80-column default.
        self._url_text = tk.Text(
            url_row, height=2, width=20,
            bg=FIELD, fg=FG, **_field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
            font="VT.Mono", wrap="none")
        self._url_text.insert("1.0", self._s("url_placeholder"))
        self._url_text.configure(fg=FG2)
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

    def _build_advanced_panel(self, parent):
        """Right-pane card, below Start: collapsible accordion sections for
        all advanced options."""
        adv, _ = self._panel(parent, "settings", None, pady=(4, 0))
        self._advanced_card = adv

        def cb(par, text_key, var, cmd=None):
            w = tk.Checkbutton(
                par, text=self._s(text_key), variable=var, command=cmd,
                wraplength=_HINT_WRAP, justify="left",
                bg=SURFACE, fg=FG, selectcolor=SEL,
                activebackground=SURFACE, activeforeground=FG,
                highlightbackground=SURFACE, highlightcolor=ACC, font="VT.Base")
            w._text_key = text_key
            return w

        # ── 1. WHISPER MODEL ──────────────────────────────────────────────
        sect, body, _, self._lbl_section_model = self._make_accordion_section(
            adv, self._s("section_model"))
        sect.pack(fill="x")
        mf = tk.Frame(body, bg=SURFACE)
        mf.pack(anchor="w", pady=4)
        # Four radios per row: the settings column is 460 px wide.
        for i, m in enumerate(WHISPER_MODELS):
            tk.Radiobutton(
                mf, text=m, variable=self._model, value=m,
                bg=SURFACE, fg=RED if "large" in m else FG,
                selectcolor=SEL, activebackground=SURFACE,
                activeforeground=RED if "large" in m else FG,
                highlightbackground=SURFACE, highlightcolor=ACC,
                font="VT.Base").grid(row=i // 4, column=i % 4, sticky="w", padx=3)
        self._lbl_model_hint = tk.Label(
            body, text=self._s("label_model_hint"),
            bg=SURFACE, fg=FG2, font="VT.Small",
            wraplength=_HINT_WRAP, justify="left")
        self._lbl_model_hint.pack(anchor="w", padx=4, pady=(0, 4))

        # ── 2. TRANSLATION ENGINE ─────────────────────────────────────────
        # body2 uses grid layout so _ollama_row/_deepl_row work with
        # grid_remove()/grid() as called by _on_engine_change().
        sect2, body2, _, self._lbl_section_engine = self._make_accordion_section(
            adv, self._s("section_engine"))
        sect2.pack(fill="x")
        body2.columnconfigure(0, weight=1)

        # Engines on two rows (two per row) so the section fits the column.
        self._lbl_engine = tk.Label(
            body2, text=self._s("label_engine"),
            bg=SURFACE, fg=FG, font="VT.Bold")
        self._lbl_engine.grid(row=0, column=0, sticky="w", pady=(4, 0))
        engine_row = tk.Frame(body2, bg=SURFACE)
        engine_row.grid(row=1, column=0, sticky="w")
        self._rb_eng_google = tk.Radiobutton(
            engine_row, text=self._s("engine_google"),
            variable=self._translation_engine, value="google",
            command=self._on_engine_change,
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Base")
        self._rb_eng_google.pack(side="left")
        self._rb_eng_deepl = tk.Radiobutton(
            engine_row, text=self._s("engine_deepl"),
            variable=self._translation_engine, value="deepl",
            command=self._on_engine_change,
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Base")
        self._rb_eng_deepl.pack(side="left", padx=(6, 0))
        # Two engines per row keep the column at its 460 px minimum in
        # every UI language and text size.
        engine_row_b = tk.Frame(body2, bg=SURFACE)
        engine_row_b.grid(row=2, column=0, sticky="w")
        self._rb_eng_marian = tk.Radiobutton(
            engine_row_b, text=self._s("engine_marian"),
            variable=self._translation_engine, value="marian",
            command=self._on_engine_change,
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Base")
        self._rb_eng_marian.pack(side="left")
        # The Ollama label is long: own row, wrapped.
        engine_row2 = tk.Frame(body2, bg=SURFACE)
        engine_row2.grid(row=3, column=0, sticky="w")
        self._rb_eng_ollama = tk.Radiobutton(
            engine_row2, text=self._s("engine_ollama"),
            variable=self._translation_engine, value="llm_ollama",
            command=self._on_engine_change,
            wraplength=_HINT_WRAP, justify="left",
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Base")
        self._rb_eng_ollama.pack(anchor="w")

        # Ollama config row (toggled by _on_engine_change). Two lines inside
        # one container so grid()/grid_remove() keep working on the container.
        self._ollama_row = tk.Frame(body2, bg=SURFACE)
        self._ollama_row.grid(row=4, column=0, sticky="w", pady=(2, 0))
        _ol_line1 = tk.Frame(self._ollama_row, bg=SURFACE)
        _ol_line1.pack(anchor="w")
        _ol_line2 = tk.Frame(self._ollama_row, bg=SURFACE)
        _ol_line2.pack(anchor="w", pady=(2, 0))
        self._lbl_ollama_model = tk.Label(
            _ol_line1, text=self._s("label_ollama_model"),
            bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_ollama_model.pack(side="left")
        self._ollama_model_combo = ttk.Combobox(
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
        self._lbl_ollama_url = tk.Label(
            _ol_line2, text=self._s("label_ollama_url"),
            bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_ollama_url.pack(side="left")
        self._ollama_url_entry = tk.Entry(
            _ol_line2, textvariable=self._ollama_url_var, width=22,
            bg=FIELD, fg=FG, **_field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
            font="VT.Mono")
        self._ollama_url_entry.pack(side="left", padx=(4, 8))
        self._chk_ollama_slot = tk.Checkbutton(
            _ol_line2, text="slot-aware",
            variable=self._ollama_slot_aware,
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Small")
        self._chk_ollama_slot.pack(side="left", padx=(4, 0))
        self._ollama_row.grid_remove()

        # Ollama thinking row (toggled by _on_engine_change)
        self._ollama_row2 = tk.Frame(body2, bg=SURFACE)
        self._ollama_row2.grid(row=5, column=0, sticky="w", pady=(2, 0))
        self._chk_ollama_thinking = tk.Checkbutton(
            self._ollama_row2, text=self._s("opt_ollama_thinking"),
            variable=self._ollama_thinking,
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Small")
        self._chk_ollama_thinking.pack(anchor="w")
        self._lbl_ollama_thinking_hint = tk.Label(
            self._ollama_row2,
            text=self._s("hint_ollama_thinking"),
            bg=SURFACE, fg=FG2, font="VT.Italic",
            wraplength=_HINT_WRAP, justify="left")
        self._lbl_ollama_thinking_hint.pack(anchor="w", padx=(24, 0))
        self._ollama_row2.grid_remove()

        # DeepL key row (toggled by _on_engine_change)
        self._deepl_row = tk.Frame(body2, bg=SURFACE)
        self._deepl_row.grid(row=6, column=0, sticky="w", pady=(2, 4))
        self._lbl_deepl_key = tk.Label(
            self._deepl_row, text=self._s("label_deepl_key"),
            bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_deepl_key.pack(side="left")
        self._deepl_key_entry = tk.Entry(
            self._deepl_row, textvariable=self._deepl_key_var, width=28,
            bg=FIELD, fg=FG, **_field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
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
        self._chk_xtts = cb(body4, "opt_xtts", self._use_xtts)
        self._chk_xtts.pack(anchor="w", pady=4)

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

        diar_f = tk.Frame(body6, bg=SURFACE)
        diar_f.grid(row=0, column=0, sticky="w", pady=(4, 0))
        self._chk_diar = tk.Checkbutton(
            diar_f, text=self._s("opt_diarization"),
            variable=self._use_diarization,
            command=self._on_diarization_toggle,
            bg=SURFACE, fg=FG, selectcolor=SEL, activebackground=SURFACE, activeforeground=FG,
            highlightbackground=SURFACE, highlightcolor=ACC,
            font="VT.Base")
        self._chk_diar.pack(side="left")

        # Token line plus a wrapped hint line, inside one container so
        # grid()/grid_remove() keep working on the container.
        self._hf_row = tk.Frame(body6, bg=SURFACE)
        self._hf_row.grid(row=1, column=0, sticky="w", pady=(2, 4))
        _hf_line = tk.Frame(self._hf_row, bg=SURFACE)
        _hf_line.pack(anchor="w")
        self._lbl_hf_token = tk.Label(
            _hf_line, text=self._s("label_hf_token"),
            bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_hf_token.pack(side="left")
        self._hf_token_entry = tk.Entry(
            _hf_line, textvariable=self._hf_token_var, width=28,
            bg=FIELD, fg=FG, **_field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
            font="VT.Mono", show="*")
        self._hf_token_entry.pack(side="left", padx=(4, 0))
        self._lbl_hf_hint = tk.Label(
            self._hf_row, text=self._s("hint_hf_token"),
            bg=SURFACE, fg=FG2, font="VT.Italic",
            wraplength=_HINT_WRAP, justify="left")
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
        self._hotwords_row = tk.Frame(body8, bg=SURFACE)
        self._hotwords_row.pack(anchor="w", fill="x", pady=4)
        self._lbl_hotwords = tk.Label(
            self._hotwords_row, text=self._s("label_hotwords"),
            bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_hotwords.pack(side="left")
        self._hotwords_entry = tk.Entry(
            self._hotwords_row, textvariable=self._hotwords_var, width=28,
            bg=FIELD, fg=FG, **_field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
            font="VT.Mono")
        self._hotwords_entry.pack(side="left", padx=(4, 0), fill="x", expand=True)
        self._lbl_hotwords_hint = tk.Label(
            body8, text=self._s("hint_hotwords"),
            bg=SURFACE, fg=FG2, font="VT.Italic",
            wraplength=_HINT_WRAP, justify="left")
        self._lbl_hotwords_hint.pack(anchor="w", pady=(0, 4))

    def _build_lang_voice_section(self, parent):
        """Right-pane card: language pair + voice chips + TTS rate slider."""
        inner, self._lbl_panel_translation = self._panel(
            parent, "translation", self._s("panel_translation"), padx=4, pady=(0, 10))

        # Source language
        from_row = tk.Frame(inner, bg=CARD)
        from_row.pack(fill="x", pady=2)
        self._lbl_from = tk.Label(
            from_row, text=self._s("label_from"),
            bg=CARD, fg=FG2, font="VT.Small", width=6, anchor="e")
        self._lbl_from.pack(side="left")
        self._src_combo = ttk.Combobox(
            from_row, values=list(SOURCE_LANGS.values()),
            state="readonly", width=22)
        self._src_combo.current(0)
        self._src_combo.pack(side="left", padx=(4, 0))
        src_keys = list(SOURCE_LANGS.keys())
        self._src_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, k=src_keys: self._lang_src.set(
                k[self._src_combo.current()]))

        # Target language
        to_row = tk.Frame(inner, bg=CARD)
        to_row.pack(fill="x", pady=2)
        self._lbl_to = tk.Label(
            to_row, text=self._s("label_to"),
            bg=CARD, fg=FG2, font="VT.Small", width=6, anchor="e")
        self._lbl_to.pack(side="left")
        self._tgt_combo = ttk.Combobox(
            to_row, values=[v["name"] for v in LANGUAGES.values()],
            state="readonly", width=22)
        self._tgt_combo.current(list(LANGUAGES.keys()).index("it"))
        self._tgt_combo.pack(side="left", padx=(4, 0))
        self._tgt_combo.bind("<<ComboboxSelected>>", self._on_lang_tgt_change)

        # Voice label + chips
        voice_lbl_row = tk.Frame(inner, bg=CARD)
        voice_lbl_row.pack(fill="x", pady=(8, 2))
        self._lbl_voice = tk.Label(
            voice_lbl_row, text=self._s("label_voice"),
            bg=CARD, fg=FG2, font="VT.Small")
        self._lbl_voice.pack(side="left")

        self._voice_frame = tk.Frame(inner, bg=CARD)
        self._voice_frame.pack(fill="x", pady=(0, 6))
        self._build_voice_buttons()

        # TTS rate slider
        rate_title_row = tk.Frame(inner, bg=CARD)
        rate_title_row.pack(fill="x", pady=(4, 2))
        self._lbl_tts_rate = tk.Label(
            rate_title_row, text=self._s("label_tts_rate"),
            bg=CARD, fg=FG2, font="VT.Small")
        self._lbl_tts_rate.pack(side="left")

        rate_frame = tk.Frame(inner, bg=CARD)
        rate_frame.pack(fill="x", pady=(0, 4))
        tk.Label(rate_frame, text="-50%", bg=CARD, fg=FG2,
                 font="VT.Small").pack(side="left")
        ttk.Scale(rate_frame, from_=-50, to=50, variable=self._tts_rate,
                  orient="horizontal", length=180).pack(side="left", padx=6)
        tk.Label(rate_frame, text="+50%", bg=CARD, fg=FG2,
                 font="VT.Small").pack(side="left")
        self._rate_lbl = tk.Label(
            rate_frame, text="+0%", bg=CARD, fg=FG,
            font="VT.Bold", width=6)
        self._rate_lbl.pack(side="left", padx=4)
        self._tts_rate.trace_add("write", self._update_rate_label)

    def _build_profile_section(self, parent):
        """Right-pane card: Fast / Balanced / Studio / Cinematic presets."""
        inner, self._lbl_panel_profile = self._panel(
            parent, "profile", self._s("panel_profile"), padx=4, pady=(0, 10))

        btn_row = tk.Frame(inner, bg=CARD)
        btn_row.pack(fill="x")

        _PROFILE_LABELS = {
            "fast":      "Fast",
            "balanced":  "Balanced",
            "studio":    "Studio",
            "cinematic": "Cinema",
        }
        self._profile_btns = {}
        for name, label in _PROFILE_LABELS.items():
            btn = tk.Button(
                btn_row, text=label,
                bg=BTN, fg=FG,
                font="VT.Base",
                relief="flat", padx=6, pady=6,
                cursor="hand2",
                highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
                activebackground=ACC_SOFT, activeforeground=FG,
                command=lambda n=name: self._apply_profile(n),
            )
            btn.pack(side="left", padx=(0, 4), fill="x", expand=True)
            self._profile_btns[name] = btn

        # Hint text (updates when profile changes)
        self._lbl_profile_hint = tk.Label(
            inner, text="", bg=CARD, fg=FG2,
            font="VT.Small", wraplength=_HINT_WRAP,
            anchor="w", justify="left")
        self._lbl_profile_hint.pack(fill="x", pady=(6, 0))

        self._update_profile_buttons()

    def _build_start_section(self, parent):
        """Right-pane card: summary line + big Start button + status row."""
        inner, self._lbl_panel_start = self._panel(
            parent, "start", self._s("panel_start"), padx=4, pady=(0, 10))

        # Summary line (auto-updated on lang/voice/profile changes)
        self._lbl_summary = tk.Label(
            inner, textvariable=self._summary_var,
            bg=CARD, fg=FG2, font="VT.Small",
            wraplength=_HINT_WRAP, justify="left")
        self._lbl_summary.pack(anchor="w", pady=(0, 10))

        # Start button - full-width, accent-filled primary
        _ws, self._btn = self._flat_btn(
            inner, primary=True, text=self._s("btn_start"),
            command=self._start, font="VT.Large", padx=24, pady=8)
        _ws.pack(fill="x")

        # Status row below button
        status_row = tk.Frame(inner, bg=CARD)
        status_row.pack(fill="x", pady=(8, 0))
        tk.Label(status_row, text="⚡", bg=CARD, fg=ACC,
                 font="VT.Small").pack(side="left")
        self._lbl_status = tk.Label(
            status_row, text="Ready",
            bg=CARD, fg=FG2, font="VT.Small")
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
        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(8, 8))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        self._body = body

        # Left pane: the integrated player (P1 shows its status and Install).
        # It sits outside every canvas, so it follows the window height and a
        # wheel over it scrolls nothing.
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._left_pane = left
        self._player_area = tk.Frame(left, bg=FIELD, highlightthickness=1,
                                     highlightbackground=BORDER,
                                     highlightcolor=BORDER)
        self._player_area.pack(fill="both", expand=True)
        self._player_panel = _PlayerPanel(
            self._player_area, ui_s=self._s, make_button=self._flat_btn,
            on_command=self._on_player_command,
            logo_path=Path(__file__).resolve().parent / "assets" / "icon_256.png",
            theme=self._theme, keyboard_operable=self._keyboard_operable,
            log=self._player_log)
        # Live-translation strip under the player transport (spec 5.9). It sits
        # inside the player area, below the panel; mpv renders into a deeper child
        # (video_host), so the strip never overlaps the video, and the left pane
        # still holds exactly the player area (P0 layout invariant preserved).
        self._live_bar = _LiveBar(
            self._player_area, ui_s=self._s, make_button=self._flat_btn,
            on_command=self._on_live_command, theme=self._theme,
            keyboard_operable=self._keyboard_operable, log=self._player_log)
        self._live_bar.pack(side="bottom", fill="x")
        self._player_panel.pack(side="top", fill="both", expand=True)
        self._refresh_live_bar_enabled()

        # Right column: input, translation, profile, start, then the settings
        # accordion, in a canvas that scrolls only this column. The canvas
        # takes the width of the cards' widest state, never below 460 px
        # (_sync_right_column); its height follows the window.
        column = tk.Frame(body, bg=BG)
        column.grid(row=0, column=1, sticky="ns")
        column.rowconfigure(0, weight=1)
        self._right_column = column
        self._right_canvas = tk.Canvas(column, bg=BG, highlightthickness=0,
                                       width=_RIGHT_COLUMN_MIN_WIDTH)
        self._right_canvas.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        self._right_vsb = ttk.Scrollbar(column, orient="vertical",
                                        command=self._right_canvas.yview)
        self._right_vsb.grid(row=0, column=1, sticky="ns")
        self._right_canvas.configure(yscrollcommand=self._right_vsb.set)

        right = tk.Frame(self._right_canvas, bg=BG)
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
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="nsew")
        self._log_frame = log_frame
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        log_header = tk.Frame(log_frame, bg=BG)
        log_header.grid(row=0, column=0, sticky="ew")
        self._lbl_log_panel = tk.Label(
            log_header, text=self._s("label_log_panel"),
            bg=BG, fg=FG, font="VT.Bold")
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

        self._log_container = tk.Frame(log_frame, bg=BG)
        self._log_container.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self._log_container.rowconfigure(0, weight=1)
        self._log_container.columnconfigure(0, weight=1)
        self._log = tk.Text(
            self._log_container, height=12, width=76,
            bg=FIELD, fg=FG, font="VT.Mono", **_field_colors(), relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
            state="disabled", wrap="word")
        vsb = ttk.Scrollbar(self._log_container, command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # ── Progress bar (root row 3) ─────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
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
            width = _right_column_width(self._cards_widest_width())
            if int(canvas.cget("width")) != width:
                canvas.configure(width=width)
            canvas.configure(scrollregion=canvas.bbox("all"))
            if self._canvas_content_fits(canvas):
                canvas.yview_moveto(0)
        except tk.TclError:
            pass  # the window is being destroyed

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
        canvas = getattr(self, "_right_canvas", None)
        if canvas is None:
            return
        wheel = getattr(self, "_wheel", None)
        if wheel is None:
            wheel = self._wheel = _WheelAccumulator()
        try:
            if self._canvas_content_fits(canvas):
                return
            units = wheel.feed(getattr(event, "num", None),
                               getattr(event, "delta", 0))
            if units:
                canvas.yview_scroll(units, "units")
        except tk.TclError:
            pass  # the window is being destroyed

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
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    # ── Language switcher ────────────────────────────────────────────────────

    def _on_ui_lang_change(self, _=None):
        idx = self._ui_lang_combo.current()
        if idx < 0:
            return
        self._ui_lang.set(UI_LANG_OPTIONS[idx][0])
        save_config({"ui_lang": self._ui_lang.get()})
        self._apply_lang()

    # ── Settings window ─────────────────────────────────────────────────────

    def _segmented(self, parent, options, variable, command):
        """Row of flat toggle buttons bound to ``variable``.

        ``options`` is a list of ``(value, label)``. The returned row exposes
        ``_refresh()`` to re-read the selection colours after a theme change.
        """
        row = tk.Frame(parent, bg=parent.cget("bg"))
        buttons = {}

        def refresh(*_):
            cur = variable.get()
            for value, b in buttons.items():
                if value == cur:
                    b.configure(bg=ACC_SOFT, fg=FG, highlightbackground=ACC)
                else:
                    b.configure(bg=BTN, fg=FG, highlightbackground=BORDER)

        def choose(value):
            variable.set(value)
            refresh()
            command()

        for value, label in options:
            b = tk.Button(row, text=label, bg=BTN, fg=FG, font="VT.Base",
                          relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                          activebackground=ACC_SOFT, activeforeground=FG,
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=ACC,
                          command=lambda v=value: choose(v))
            b.pack(side="left", padx=(0, 4))
            buttons[value] = b
        refresh()
        row._refresh = refresh
        return row

    def _theme_options(self):
        """(value, label) pairs for the theme row; Graphite/Slate/Neon are proper nouns."""
        labels = {"auto": self._s("theme_auto"), "light": self._s("theme_light")}
        return [(k, labels.get(k, k.capitalize())) for k in _THEME_CHOICES]

    def _scale_options(self):
        return [(k, self._s(f"size_{k}")) for k in _SCALES]

    def _accent_dot_colour(self, value):
        """Swatch colour: the theme's own accent for "default", the fixed accent otherwise."""
        if value == "default":
            return _resolve_palette(self._theme.palette.name, "default").ACC
        return _ACCENTS[value]

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
                        bg=SURFACE,
                        highlightbackground=FG if value == cur else SURFACE,
                        highlightcolor=ACC)

    def _open_settings(self):
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return
        win = tk.Toplevel(self, bg=BG)
        self._settings_win = win
        win.title(self._s("settings_title"))
        win.resizable(False, False)
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", self._close_settings)
        body = tk.Frame(win, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Appearance
        self._lbl_settings_appearance = tk.Label(
            body, text=self._s("settings_appearance").upper(), bg=BG, fg=FG2, font="VT.SmallBold")
        self._lbl_settings_appearance.pack(anchor="w")
        card = self._card(body, pady=(6, 14))

        self._lbl_settings_theme = tk.Label(card, text=self._s("settings_theme"),
                                            bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_settings_theme.pack(anchor="w")
        self._seg_theme = self._segmented(card, self._theme_options(),
                                          self._ui_theme_var, self._apply_ui_settings)
        self._seg_theme.pack(anchor="w", pady=(4, 12))

        self._lbl_settings_accent = tk.Label(card, text=self._s("settings_accent"),
                                             bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_settings_accent.pack(anchor="w")
        dots = tk.Frame(card, bg=SURFACE)
        dots.pack(anchor="w", pady=(4, 12))
        self._accent_dots = {}

        def choose_accent(value):
            self._ui_accent_var.set(value)
            self._apply_ui_settings()

        for value in _ACCENT_CHOICES:
            d = tk.Label(dots, text="●", bg=SURFACE, fg=self._accent_dot_colour(value),
                         font="VT.Title", cursor="hand2",
                         padx=4, highlightthickness=2, highlightbackground=SURFACE,
                         highlightcolor=ACC)
            d.pack(side="left", padx=(0, 2))
            d.bind("<Button-1>", lambda e, v=value: choose_accent(v))
            self._keyboard_operable(d, lambda v=value: choose_accent(v))
            self._accent_dots[value] = d
            if value == "default":
                # Caption sits next to its own dot, before the fixed accents
                self._lbl_accent_default = tk.Label(dots, text=self._s("accent_default"),
                                                    bg=SURFACE, fg=FG2, font="VT.Small")
                self._lbl_accent_default.pack(side="left", padx=(2, 14))
        self._refresh_accent_dots()

        self._lbl_settings_size = tk.Label(card, text=self._s("settings_text_size"),
                                           bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_settings_size.pack(anchor="w")
        self._seg_scale = self._segmented(card, self._scale_options(),
                                          self._ui_scale_var, self._apply_ui_settings)
        self._seg_scale.pack(anchor="w", pady=(4, 0))

        # Language
        self._lbl_settings_language = tk.Label(
            body, text=self._s("settings_language").upper(), bg=BG, fg=FG2, font="VT.SmallBold")
        self._lbl_settings_language.pack(anchor="w")
        lang_card = self._card(body, pady=(6, 14))
        self._lbl_ui_lang = tk.Label(lang_card, text=self._s("label_ui_lang"),
                                     bg=SURFACE, fg=FG2, font="VT.Small")
        self._lbl_ui_lang.pack(anchor="w")
        self._ui_lang_combo = ttk.Combobox(
            lang_card, values=[lbl for _, lbl in UI_LANG_OPTIONS], state="readonly", width=24)
        _codes = [code for code, _ in UI_LANG_OPTIONS]
        self._ui_lang_combo.current(_codes.index(self._ui_lang.get()) if self._ui_lang.get() in _codes else 0)
        self._ui_lang_combo.pack(anchor="w", pady=(4, 0))
        self._ui_lang_combo.bind("<<ComboboxSelected>>", self._on_ui_lang_change)

        # Player options: keep these separate from appearance preferences so
        # they remain available even when the integrated player is offline.
        self._lbl_settings_player = tk.Label(
            body, text=self._s("settings_player").upper(), bg=BG, fg=FG2,
            font="VT.SmallBold")
        self._lbl_settings_player.pack(anchor="w")
        player_card = self._card(body, pady=(6, 14))
        self._player_autoload_var = tk.BooleanVar(value=self._player_settings.autoload_result)
        self._keep_original_audio_var = tk.BooleanVar(
            value=self._player_settings.keep_original_audio)
        self._chk_player_autoload = tk.Checkbutton(
            player_card, text=self._s("opt_player_autoload"),
            variable=self._player_autoload_var,
            command=self._save_player_options,
            bg=SURFACE, fg=FG, activebackground=SURFACE, activeforeground=FG,
            selectcolor=BG, relief="flat", borderwidth=0, font="VT.Base",
        )
        self._chk_player_autoload.pack(anchor="w")
        self._chk_keep_original_audio = tk.Checkbutton(
            player_card, text=self._s("opt_keep_original_audio"),
            variable=self._keep_original_audio_var,
            command=self._save_player_options,
            bg=SURFACE, fg=FG, activebackground=SURFACE, activeforeground=FG,
            selectcolor=BG, relief="flat", borderwidth=0, font="VT.Base",
        )
        self._chk_keep_original_audio.pack(anchor="w")
        self._player_credits_label = tk.Label(
            player_card, text=self._player_panel.status_text(), bg=SURFACE,
            fg=FG2, font="VT.Small", justify="left", wraplength=420,
        )
        self._player_credits_label.pack(anchor="w", pady=(4, 0))

        # Buttons
        btns = tk.Frame(body, bg=BG)
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
        self._player_settings = dataclasses.replace(
            self._player_settings,
            autoload_result=bool(self._player_autoload_var.get()),
            keep_original_audio=bool(self._keep_original_audio_var.get()),
        )
        save_config({
            _player_settings_module.PLAYER_AUTOLOAD_KEY:
                self._player_settings.autoload_result,
            _player_settings_module.KEEP_ORIGINAL_AUDIO_KEY:
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
        save_config({k: self._ui_settings[k] for k in ("ui_theme", "ui_accent", "ui_scale")})
        self._refresh_theme_dependents()

    def _refresh_theme_dependents(self):
        """Repaint what the colour mapping of a theme change cannot handle.

        Selection states re-read the (new) globals: the colour mapping alone
        cannot tell a selected dot from one that merely shares the old accent.
        """
        if self._settings_win is not None and self._settings_win.winfo_exists():
            for row in (self._seg_theme, self._seg_scale):
                row._refresh()
            self._refresh_accent_dots()
        self._update_profile_buttons()
        player_panel = getattr(self, "_player_panel", None)
        if player_panel is not None:
            player_panel.apply_theme()
        live_bar = getattr(self, "_live_bar", None)
        if live_bar is not None:
            live_bar.apply_theme()
        # Another text size changes the cards' width, and a large shrink can
        # leave the view below the content without any <Configure>.
        self.after_idle(self._sync_right_column)

    def _remember_system_dark(self, value):
        """Cache the OS dark-mode answer so the next start paints with it."""
        save_config({_SYSTEM_DARK_KEY: value})

    def _reset_ui_settings(self):
        if self._panel_order != list(_PANEL_IDS):
            self._panel_order = list(_PANEL_IDS)
            self._repack_panels()
            save_config({"ui_panel_order": self._panel_order})
        self._ui_theme_var.set(_DEFAULT_THEME)
        self._ui_accent_var.set(_DEFAULT_ACCENT)
        self._ui_scale_var.set(_DEFAULT_SCALE)
        self._apply_ui_settings()
        # Spec 2.5: Reset also forgets the cached libmpv probe, so the next
        # status check probes the library again. save_config merges and cannot
        # delete a key, hence the raw write of the whole file.
        cfg = load_config()
        player_keys = ("player_probe", "player_vo_profile")
        if any(key in cfg for key in player_keys):
            for key in player_keys:
                cfg.pop(key, None)
            try:
                _write_config_raw(cfg)
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
        lang = self._ui_lang.get()
        self._lbl_panel_input.configure(text=self._title_upper(self._s("panel_input"), lang))
        self._lbl_panel_translation.configure(text=self._title_upper(self._s("panel_translation"), lang))
        self._lbl_panel_profile.configure(text=self._title_upper(self._s("panel_profile"), lang))
        self._lbl_panel_start.configure(text=self._title_upper(self._s("panel_start"), lang))
        self._lbl_video.configure(text=self._s("label_video"))
        self._lbl_output.configure(text=self._s("label_output"))
        self._lbl_output_dir.configure(text=self._s("label_output_dir"))
        self._lbl_section_model.configure(text=self._s("section_model"))
        self._lbl_model_hint.configure(text=self._s("label_model_hint"))
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
            self._url_text.configure(fg=FG2)
        self._btn_add.configure(text=self._s("btn_add"))
        self._btn_remove.configure(text=self._s("btn_remove"))
        self._btn_clear.configure(text=self._s("btn_clear"))
        self._btn_browse.configure(text=self._s("btn_browse"))
        self._btn_output_dir.configure(text=self._s("btn_browse"))
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
        # Log panel labels
        self._lbl_log_panel.configure(text=self._s("label_log_panel"))
        self._btn_log_toggle.configure(
            text=self._s("btn_log_hide" if getattr(self, "_log_visible", True) else "btn_log_show"))
        self._btn_log_copy.configure(text=self._s("btn_log_copy"))
        self._btn_log_save.configure(text=self._s("btn_log_save"))
        self._btn_log_clear.configure(text=self._s("btn_log_clear"))
        self._btn_preflight.configure(text=self._s("btn_preflight"))
        # Update source language combo labels
        lang = self._ui_lang.get()
        src_map  = SOURCE_LANGS_EN if lang == "en" else SOURCE_LANGS
        src_keys = list(src_map.keys())
        cur_key  = self._lang_src.get()
        self._src_combo["values"] = list(src_map.values())
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
        self.after_idle(self._sync_right_column)

    # ── Voice buttons ────────────────────────────────────────────────────────

    def _build_voice_buttons(self):
        """Rebuild voice pill-buttons for the selected target language."""
        for w in self._voice_frame.winfo_children():
            w.destroy()
        lang_key = list(LANGUAGES.keys())[self._tgt_combo.current()]
        voices   = LANGUAGES[lang_key]["voices"]
        self._voice.set(voices[0])

        def _refresh_pills(*_):
            """Re-color all pill buttons to reflect selection."""
            cur = self._voice.get()
            for btn_v, btn_w in _pill_map.items():
                if btn_v == cur:
                    btn_w.configure(bg=ACC_SOFT, fg=FG, highlightbackground=ACC)
                else:
                    btn_w.configure(bg=BTN, fg=FG, highlightbackground=BORDER)

        _pill_map = {}
        for v in voices:
            label = v.split("-")[2].replace("Neural", "").replace("Multilingual", "ML")
            btn = tk.Radiobutton(
                self._voice_frame, text=label,
                variable=self._voice, value=v,
                indicatoron=False,
                bg=BTN, fg=FG,
                selectcolor=ACC_SOFT,
                activebackground=ACC_SOFT, activeforeground=FG,
                font="VT.Base",
                relief="flat", padx=10, pady=4,
                highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACC,
                cursor="hand2",
                command=_refresh_pills,
            )
            btn.pack(side="left", padx=(0, 4))
            _pill_map[v] = btn

        # Apply initial coloring
        _refresh_pills()
        self._update_start_summary()

    def _on_lang_tgt_change(self, _=None):
        self._lang_tgt.set(list(LANGUAGES.keys())[self._tgt_combo.current()])
        self._build_voice_buttons()
        # Re-bind mousewheel to newly created voice pill buttons
        try:
            self._bind_mousewheel(self._voice_frame)
        except Exception:
            pass
        self._update_start_summary()
        # New voice chips can change the cards' width.
        self.after_idle(self._sync_right_column)

    def _update_rate_label(self, *_):
        try:
            v = int(round(self._tts_rate.get()))
        except (ValueError, tk.TclError):
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

    # ── TTS engine mutual exclusion (v2.3) ────────────────────────────────
    # ── Ollama auto-setup (v2.0.1) ────────────────────────────────────────
    #
    # Flow (all off-thread, UI always responsive):
    #   1. Binary → if missing: popup [Yes/No] → _ollama_install
    #   2. Daemon → if down: start in background, wait up to 15 s
    #   3. Model → if missing: popup [Yes/No/Change model] → ollama pull
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
        model = self._ollama_model_var.get().strip() or "qwen3:8b"
        url = self._ollama_url_var.get().strip() or "http://localhost:11434"
        cfg = load_config()
        auto_install = cfg.get("ollama_auto_install", True)

        def _setup():
            ok = self._ollama_setup_worker(model, url, auto_install)
            if on_ready is not None and not self._destroying:
                self.after(0, on_ready, ok)

        threading.Thread(target=_setup, daemon=True).start()

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
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            try:
                target()
            finally:
                _thread_local.redirect = None

        return threading.Thread(target=run, name=name, daemon=daemon)


    # -- Integrated player: availability and install (spec 9 P1) ------------

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
            with contextlib.suppress(RuntimeError):
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
        cached = load_config().get("player_probe")

        def work():
            try:
                status = _libmpv_runtime.resolve_status(cached=cached, force_probe=force_probe)
                request = _system_packages.player_install_request(
                    status, sys_platform=sys.platform,
                    mpv_importable=importlib.util.find_spec("mpv") is not None)
            except Exception as exc:  # the badge must never stay grey without a reason
                status = _libmpv_runtime.LibmpvStatus(
                    ok=False, reason="probe-crashed", detail=f"status check failed: {exc}")
                request = _system_packages.PlayerInstallRequest()
            self._post_if_alive(lambda: self._on_player_status(status, request))

        self._redirecting_thread_factory(work, name="player-status").start()

    def _on_player_status(self, status, request) -> None:
        self._player_status = status
        self._player_install_request = request
        entry = _libmpv_runtime.cache_entry(status)
        if entry is not None and load_config().get("player_probe") != entry:
            save_config({"player_probe": entry})  # config writes stay on the Tk thread
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

    def _update_player_badge(self) -> None:
        level = _libmpv_runtime.badge_level(self._player_status) if self._player_status else None
        self._player_badge_dot.configure(fg={"ok": OK, "warn": WARN, "error": ERR}.get(level, FG2))

    def _on_player_command(self, name: str, args: dict) -> None:
        """Route PlayerPanel intents on Tk; the controller owns player state."""
        if name == "install":
            self._install_player()
            return
        controller = self._player_controller
        if name == "play_pause":
            controller.play_pause()
        elif name == "stop":
            controller.stop()
        elif name == "previous":
            controller.previous()
        elif name == "next":
            controller.next()
        elif name == "back_10":
            self._player_clock.expect_restart()
            controller.seek_relative(-10.0)
        elif name == "forward_10":
            self._player_clock.expect_restart()
            controller.seek_relative(10.0)
        elif name == "seek":
            self._player_clock.expect_restart()
            controller.seek(float(args.get("seconds", 0.0)),
                            dragging=bool(args.get("dragging", False)))
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
                controller.snapshot(_platforms.default_videos_dir(), datetime.datetime.now())
            except (OSError, RuntimeError) as exc:
                self._player_panel.notify(
                    "player_snapshot_failed", {"detail": str(exc), "path": ""})
        elif name == "open_folder":
            item = controller.state.item
            if item is not None and item.kind != "live":
                _platforms.reveal_in_file_manager(Path(item.path))
        elif name == "playlist":
            self._player_panel.show_playlist(
                self._source_media_items(), self._player_results,
                job_running=self._running)
        elif name == "load_item":
            item = args.get("item")
            if isinstance(item, _player_core.MediaItem):
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
            messagebox.showwarning(self._s("msg_error_t"), self._s("live_err_busy_job"))
            return True
        return False

    def _on_live_command(self, intent: str, params: dict) -> None:
        """Route LiveBar intents on the Tk thread (mirrors _on_player_command)."""
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
            if session is not None:
                session.set_engine("marian")
            return
        if session is None:
            return  # settings changed while idle are read at start()
        if intent == "mode":
            session.set_sync_mode(params.get("mode", "delayed"))
        elif intent == "delay":
            session.set_delay(float(params.get("seconds", 0.0)))
        elif intent == "engine":
            session.set_engine(params.get("engine", "marian"))
        elif intent == "dub":
            session.set_dub_enabled(bool(params.get("enabled", True)))
        elif intent == "subs":
            session.set_subs_enabled(bool(params.get("enabled", True)))

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
            self._launch_live_session(source, "file", title=None)
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
        # Play the resolved stream in the player while the same URL is translated.
        # The mpv backend is created lazily on first load, so start the session
        # only once it exists (below), not synchronously here.
        item = _player_core.MediaItem(path=stream_url, kind="source", title=title)
        self._player_controller.set_playlist([item], index=0)
        self._player_controller.load(item, paused=False)
        self._ensure_or_show_player_status()
        self._pending_live_source = (stream_url, "url", title)
        self._await_backend_and_launch(time.monotonic() + 20.0)

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
        if unavailable or time.monotonic() >= deadline:
            self._pending_live_source = None
            self._live_resolving = False
            self._live_bar.show_banner("player_unavailable_title", is_error=True)
            self._refresh_live_bar_enabled()
            return
        if not self._player_init_running:
            self._ensure_or_show_player_status()   # (re)trigger backend creation
        self.after(150, lambda: self._await_backend_and_launch(deadline))

    def _launch_live_session(self, source: str, source_kind: str, *,
                             title: str | None) -> None:
        # The launch is the terminal step of a start: clear the resolving flag so
        # the bar reflects the session (or, on failure below, re-enables Start).
        self._live_resolving = False
        raw = self._live_bar.current_settings()
        tgt = self._lang_tgt.get()
        values = {
            "source": source, "source_kind": source_kind,
            "lang_source": self._lang_src.get(),
            "lang_target": tgt,
            "voice": self._live_voice_for(tgt),
            "engine": raw["engine"],
            "deepl_key": self._deepl_key_var.get().strip(),
            "ollama_url": self._ollama_url_var.get().strip(),
            "ollama_model": self._ollama_model_var.get().strip(),
        }
        settings = _player_settings_module.normalize_live_settings({
            "live_sync_mode": raw["mode"], "live_delay_s": raw["delay"],
            "live_engine": raw["engine"], "live_dub_enabled": raw["dub"],
            "live_subs_enabled": raw["subs"],
        })
        cache_dir = Path(tempfile.gettempdir()) / "VideoTranslatorAI" / "live"
        try:
            cfg = _live_session_module.build_live_config(
                values, settings=settings, cache_dir=cache_dir, now=time.time())
            factories = _live_session_module.build_live_factories(
                cfg, log=self._player_log)
            voice_backend = self._ensure_voice_backend() if raw["dub"] else None
            self._live_session = _live_session_module.LiveSession(
                cfg, video=self._player_backend, clock_view=self._player_clock,
                factories=factories, voice=voice_backend, log=self._player_log,
                thread_factory=self._redirecting_thread_factory)
            self._live_session.start()
        except Exception as exc:                     # noqa: BLE001
            self._player_log(f"[live] start failed: {exc}")
            self._live_session = None
            self._live_bar.show_banner("live_err_internal",
                                       {"detail": str(exc)}, is_error=True)
            self._refresh_live_bar_enabled()
            return
        self._live_bar.clear_banner()
        self._live_bar.set_active(True)
        self._live_bar.set_start_enabled(False)
        self._schedule_live_poll()

    def _schedule_live_poll(self) -> None:
        if self._destroying or self._live_session is None:
            return
        self._live_poll_after = self.after(250, self._poll_live_status)

    def _poll_live_status(self) -> None:
        self._live_poll_after = None
        session = self._live_session
        if session is None or self._destroying:
            return
        status = session.status()
        self._live_bar.render(status)
        if status.state in ("stopped", "failed", "ended"):
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
        self._live_session = None
        self._live_stopping = False
        if self._live_poll_after is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._live_poll_after)
            self._live_poll_after = None
        if session is not None:
            def work():
                session.join(5.0)
            self._redirecting_thread_factory(work, name="live-stop").start()
        self._live_bar.set_active(False)
        self._refresh_live_bar_enabled()

    def _source_media_items(self) -> list[_player_core.MediaItem]:
        return [
            _player_core.MediaItem(path, "source", Path(path).name)
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
            item = _player_core.MediaItem(
                path=str(video), kind="dubbed",
                title=getattr(output, "title", None) or Path(video).name,
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
        if self._player_status is not None and not self._player_status.ok:
            request = self._player_install_request or _system_packages.PlayerInstallRequest()
            self._player_panel.show_unavailable(
                self._player_status, install_cmd=request.manual_command)
            return
        self._ensure_player()

    @staticmethod
    def _load_libx11():
        name = ctypes.util.find_library("X11") or "libX11.so.6"
        return ctypes.CDLL(name)

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
        if (sys.platform.startswith("linux")
                and self.tk.call("tk", "windowingsystem") == "x11"):
            if self._player_guard is None:
                self._player_guard = _player_engine.X11ErrorGuard(
                    load_libx11=self._load_libx11)
            self._player_guard.capture()
        self._player_init_running = True

        def work():
            try:
                module = _libmpv_runtime.load_mpv()
                backend = _player_engine.create_video_backend(
                    wid=wid, bridge=self._player_bridge, mixer=self._player_mixer,
                    vo_profile=profile, mpv_module=module,
                    sys_platform="win32" if sys.platform == "win32" else "linux",
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
        status = _libmpv_runtime.LibmpvStatus(
            ok=False, reason="libmpv-load-failed",
            detail=f"player initialization failed: {exc}")
        self._on_player_status(status, _system_packages.PlayerInstallRequest())
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
        self._start_player_poll()

    def _live_voice_for(self, tgt: str) -> str:
        """Pick the edge-tts voice for the live dub: the user's if it fits the
        target language, otherwise the language's first catalog voice."""
        voices = LANGUAGES.get(tgt, {}).get("voices", [])
        current = self._voice.get()
        if current in voices:
            return current
        return voices[0] if voices else current

    def _ensure_voice_backend(self):
        """Create the second, video-less mpv for the live dub, once per app run.

        Shares the player bridge (it writes only namespaced values and voice-*
        events, never the player state). Returns None if libmpv cannot build it;
        the session then degrades to subtitles only.
        """
        if self._voice_backend is not None or self._player_backend is None:
            return self._voice_backend
        try:
            module = _libmpv_runtime.load_mpv()
            self._voice_backend = _player_engine.create_voice_backend(
                bridge=self._player_bridge, mpv_module=module,
                sys_platform="win32" if sys.platform == "win32" else "linux",
                log=None)
        except Exception as exc:                     # noqa: BLE001
            self._player_log(f"[live] dubbed voice unavailable: {exc}")
            self._voice_backend = None
        return self._voice_backend

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
        now = time.monotonic()
        snapshot = self._player_bridge.drain()
        for event in snapshot.events:
            if event.kind == "playback-restart":
                self._player_clock.on_playback_restart(now)
            elif event.kind == "file-loaded":
                self._player_loaded_at = now
                self._player_video_params_seen = False
            elif event.kind == "mouse" and isinstance(event.payload, tuple):
                action = _player_core.mouse_action(*event.payload)
                if action is not None:
                    self._on_player_mouse_action(action)
            elif event.kind == "snapshot-saved":
                self._player_panel.notify("player_snapshot_saved", dict(event.payload or {}))
            elif event.kind == "snapshot-failed":
                self._player_panel.notify("player_snapshot_failed", dict(event.payload or {}))
            elif event.kind == "adapter-error":
                self._player_log(f"[!] mpv adapter: {event.payload}")
            elif event.kind == "log":
                line = str(event.payload)
                if _is_noisy_x11_log(line):
                    # mpv floods the log with harmless X11 BadWindow errors while
                    # embedded on X11 (its process-global Xlib handler reports
                    # expected X errors from Tk or the GL stack); the video
                    # renders fine. Log the first full block verbatim (resourceid
                    # + request code for diagnosis), then collapse the rest into a
                    # periodic summary instead of a line each.
                    self._mpv_x11_noise += 1
                    stamp = time.monotonic()
                    if self._mpv_x11_noise <= 3:
                        self._log_write(f"[mpv] {line}\n")
                    elif (self._mpv_x11_noise == 4
                            or stamp - self._mpv_x11_noise_at >= 5.0):
                        self._mpv_x11_noise_at = stamp
                        self._log_write(
                            f"[mpv] harmless X11 window errors during playback "
                            f"({self._mpv_x11_noise} so far, repeats suppressed)\n")
                else:
                    self._player_log_lines.append(line)
                    del self._player_log_lines[:-100]
                    self._log_write(f"[mpv] {line}\n")
        video_params = snapshot.changed.get("video-params")
        if video_params is not None and video_params[0]:
            self._player_video_params_seen = True
            if self._player_fallback_notice_pending:
                self._player_fallback_notice_pending = False
                save_config({"player_vo_profile": self._player_vo_profile})
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
            seeking=seeking)
        clock_now = self._player_clock.now(now)
        self._player_controller.apply_events(snapshot, clock_now)
        self._player_panel.render(self._player_controller.state, position=clock_now)
        if self._player_vo_failed(now):
            self._begin_player_vo_fallback()
            return
        if self._player_controller.state.item is not None:
            self._start_player_poll()

    def _player_vo_failed(self, now: float) -> bool:
        if self._player_init_running:
            return False
        tracks = self._bridge_value(self._player_bridge, "track-list", [])
        has_video = any(
            isinstance(track, dict) and track.get("type") == "video"
            for track in (tracks or []))
        return _player_engine.detect_vo_failure(
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
        platform_key = "win32" if sys.platform == "win32" else "linux"
        next_profile = _player_engine.next_vo_profile(
            platform_key, self._player_vo_profile or "", accepted)
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
                backend, lambda: self._finish_player_vo_failure("video-output-error"))
            return
        if (platform_key == "linux"
                and (self._player_guard is None or not self._player_guard.captured)):
            save_config({"player_vo_profile": next_profile})
            self._terminate_failed_player(
                backend, lambda: self._finish_player_vo_restart_required(next_profile))
            return
        self._player_vo_retries += 1
        wid = self._player_panel.host_wid()

        def work():
            try:
                backend.terminate(3.0)
                self._player_bridge.close()
                if self._player_guard is not None:
                    self._player_guard.restore()
                module = _libmpv_runtime.load_mpv()
                replacement_bridge = _player_engine.EventBridge()
                replacement = _player_engine.create_video_backend(
                    wid=wid, bridge=replacement_bridge, mixer=self._player_mixer,
                    vo_profile=next_profile, mpv_module=module,
                    sys_platform=platform_key, log=None)
            except Exception as exc:
                self._post_if_alive(
                    lambda error=exc: self._on_player_init_failed(error))
                return
            if self._destroying:
                replacement.terminate(3.0)
                if self._player_guard is not None:
                    self._player_guard.restore()
                return
            self._post_if_alive(
                lambda: self._on_player_fallback_ready(
                    replacement, replacement_bridge, next_profile))

        self._player_init_thread = self._redirecting_thread_factory(
            work, name="player-init")
        self._player_init_thread.start()

    def _terminate_failed_player(self, backend, on_done) -> None:
        def work():
            try:
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
        self._player_clock = _player_engine.PlaybackClock()
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
        status = dataclasses.replace(
            self._player_status, ok=False, reason="restart-required",
            detail="video output fallback will be used after restart")
        self._on_player_status(status, _system_packages.PlayerInstallRequest())

    def _on_player_mouse_action(self, action: str) -> None:
        with contextlib.suppress(tk.TclError):
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
        with contextlib.suppress(tk.TclError, AttributeError):
            widget_class = event.widget.winfo_class()
        if not _player_core.handles_player_key(
                widget_class, event.keysym, focus_in_player=focus_in_player):
            return None
        action = _player_core.PLAYER_KEYS[event.keysym]
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
        with contextlib.suppress(tk.TclError):
            self.attributes("-fullscreen", on)
        self._player_panel.set_fullscreen_layout(on)

    def _install_player(self) -> None:
        if self._installing:
            messagebox.showerror(self._s("msg_error_t"), self._s("live_err_busy_install"),
                                 parent=self)
            return
        request = self._player_install_request
        if request is None or request.empty:
            self._refresh_player_status(force_probe=True)
            return
        windows_install = None
        if request.windows_dest is not None:
            question = self._s("player_install_confirm").format(size=request.download_mb)
            if not messagebox.askyesno(self._s("msg_confirm"), question, parent=self):
                return
            dest = request.windows_dest

            def windows_install():
                return _libmpv_runtime.install_windows(dest, log=self._player_log)

        self._installing = True
        self._player_panel.show_install_progress("installing")
        self._player_log("[*] Installing the integrated video player...")
        self._player_installer().install(
            pip_packages=request.pip_packages, system_plans=request.system_plans,
            windows_install=windows_install, expect_modules=("mpv",),
            on_done=self._on_player_install_done)

    def _player_installer(self):
        return _system_packages.ComponentInstaller(
            runner=lambda cmd: _system_packages.run_streaming(cmd, log=self._player_log),
            thread_factory=self._redirecting_thread_factory,
            find_spec=importlib.util.find_spec,
            refresh=_system_packages.refresh_import_paths,
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
            status = dataclasses.replace(
                self._player_status, ok=False, reason="restart-required",
                detail="installed, but not importable until the application restarts")
            self._on_player_status(status, _system_packages.PlayerInstallRequest())
            return
        self._refresh_player_status(force_probe=True)
    def _ollama_setup_worker(self, model: str, url: str, auto_install: bool) -> bool:
        """Worker thread: runs steps 1-4. Returns True if Ollama is ready.

        This is the heart of the flow - each step has a precise early-exit
        so that no state accumulates, and every popup is forwarded to the main
        thread via `_ask_yes_no_sync` (blocks the worker until the user
        responds, but the GUI stays fluid).
        """
        # Step 1: binary detection
        binary = _ollama_find_binary()
        if not binary:
            self._log_async("[*] Ollama non trovato sul sistema.\n")
            if not auto_install:
                self._log_async(
                    "[i] ollama_auto_install=false → fallback Google se userai llm_ollama.\n"
                )
                return False
            if not self._ask_yes_no_sync(
                "Ollama",
                "Ollama non è installato. Installare automaticamente?\n\n"
                "Download ~1 GB. Su Linux servirà la password sudo.",
            ):
                self._log_async("[i] Install rifiutato. Fallback Google attivo.\n")
                return False
            self._log_async("[*] Installazione Ollama in corso...\n")
            ok, msg = _ollama_install(log_cb=self._log_async)
            if not ok:
                self._log_async(f"[x] Installazione fallita: {msg}\n")
                return False
            binary = _ollama_find_binary()
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
        if _ollama_is_daemon_running(url, timeout=2.0):
            self._log_async(f"[+] Ollama daemon gia' attivo su {url}\n")
        else:
            # If we just installed Ollama, the desktop app on Windows starts its
            # embedded daemon with a 5-10s delay. Wait for it before falling back
            # to `ollama serve` (which would EADDRINUSE-fail against the desktop daemon).
            self._log_async(
                "[*] Daemon non ancora attivo, attesa fino a 12s "
                "(Ollama Desktop puo' avviare il proprio daemon in background)...\n"
            )
            if _ollama_wait_for_daemon(url, wait_seconds=12.0):
                self._log_async(f"[+] Ollama daemon attivo su {url} (avviato dall'app desktop)\n")
            else:
                self._log_async("[*] Avvio daemon Ollama (ollama serve)...\n")
                ok, msg = _ollama_start_daemon(
                    binary, api_url=url, wait_seconds=15.0, log_cb=self._log_async
                )
                if not ok:
                    # Port-conflict fallback: if `ollama serve` failed because
                    # something else (Ollama Desktop, prior daemon) bound 11434,
                    # the existing daemon is fine - verify and use it.
                    msg_lower = (msg or "").lower()
                    port_conflict = any(s in msg_lower for s in (
                        "address already in use",
                        "bind:",
                        "in use",
                        "consentito un solo utilizzo",   # Italian Windows
                        "una sola utilizzazione",
                        "only one usage of each socket",  # English Windows
                    ))
                    if port_conflict and _ollama_is_daemon_running(url, timeout=3.0):
                        self._log_async(
                            f"[+] Port 11434 occupata da un altro daemon Ollama gia' attivo - "
                            f"riutilizzo quello.\n"
                        )
                    else:
                        self._log_async(f"[x] Daemon non avviato: {msg}\n")
                        return False

        # Step 3: model available?
        # TASK 2J: health check now returns (ok, msg, resolved_model). When
        # the requested tag is missing but the daemon has compatible models
        # the selector picks a fallback and returns ok=True with a warning.
        # We surface the warning to the user but DO NOT prompt for pull -
        # the pipeline will run on `resolved_model` automatically.
        health_ok, health_msg, resolved_model = _ollama_health_check(url, model, timeout=5.0)
        if health_ok and health_msg and resolved_model and resolved_model != model:
            self._log_async(f"[!] {health_msg}\n")
        elif not health_ok:
            # Heuristic: is this a "missing model", "daemon down",
            # or "no model installed" problem?
            msg_lower = (health_msg or "").lower()
            if "not reachable" in msg_lower or "invalid json" in msg_lower:
                self._log_async(f"[x] Ollama non raggiungibile: {health_msg}\n")
                return False
            # Modello mancante (zero modelli installati nel daemon) → chiedi pull
            if not auto_install:
                self._log_async(
                    f"[i] Modello '{model}' mancante e ollama_auto_install=false.\n"
                )
                return False
            if not self._ask_yes_no_sync(
                "Ollama",
                f"Il modello '{model}' non e' stato scaricato.\n\n"
                f"Dimensione tipica: 4-5 GB. Scaricarlo ora?\n\n"
                f"(Scegli No per usare il fallback Google)",
            ):
                self._log_async(f"[i] Pull rifiutato per {model}. Fallback Google.\n")
                return False
            ok, msg = _ollama_pull_model(model, binary=binary, log_cb=self._log_async)
            if not ok:
                self._log_async(f"[x] ollama pull fallito: {msg}\n")
                return False
            # Verifica finale
            health_ok, health_msg, resolved_model = _ollama_health_check(url, model, timeout=5.0)
            if not health_ok:
                self._log_async(f"[x] Verifica post-pull fallita: {health_msg}\n")
                return False

        self._log_async(f"[+] Ollama pronto: {resolved_model or model} @ {url}\n")
        return True

    def _ask_yes_no_sync(self, title: str, message: str) -> bool:
        """Call messagebox.askyesno on the main thread and block the worker
        until the user responds. Uses an Event for the rendezvous.
        """
        if self._destroying:
            return False
        result: dict[str, bool] = {"v": False}
        done = threading.Event()

        def _prompt():
            try:
                result["v"] = bool(messagebox.askyesno(title, message, parent=self))
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
            if importlib.util.find_spec(pkg) is None
        ]
        if not missing:
            return
        pkg_list = "\n  • ".join(missing)
        msg = (
            f"MarianMT richiede pacchetti aggiuntivi:\n  • {pkg_list}\n\n"
            f"Verranno installati con pip (--break-system-packages)."
            f"{self._s('msg_deps_install')}"
        )
        if messagebox.askyesno(self._s("msg_deps_missing"), msg):
            self._install_deps(missing)
        else:
            self._translation_engine.set("google")
            self._deepl_row.grid_remove()

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
            self._url_text.configure(fg=FG)
            self._url_placeholder_active = False

    def _url_focus_out(self, _=None):
        if not self._url_text.get("1.0", "end").strip():
            self._url_text.insert("1.0", self._s("url_placeholder"))
            self._url_text.configure(fg=FG2)
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
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_url"))
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
            except tk.TclError:
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
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
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
                        with tempfile.TemporaryDirectory(prefix="ytdl_") as tmp_dl:
                            video_path = download_youtube(url, tmp_dl)
                            self.after(0, self._log_write,
                                       self._s("log_dl_done").format(Path(video_path).name) + "\n")
                            # Move to a stable path outside the TemporaryDirectory
                            # shutil.move overwrites the placeholder atomically via os.rename
                            fd, stable = tempfile.mkstemp(suffix=".mp4", prefix="yt_")
                            os.close(fd)
                            shutil.move(video_path, stable)
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
                        cfg = dataclasses.replace(
                            p,
                            video_in=stable,
                            output=p.output if len(urls) == 1 else None,
                        )
                        result = translate_video(**cfg.to_translate_video_kwargs())
                        fallback_count += _count_fallback_segments(result)
                        output = JobOutput.from_result(result)
                        if output.video_path:
                            outputs.append(output)
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
                        all_ok = False
                        error_keys.append(_error_key_for(e))
                    finally:
                        if stable and os.path.exists(stable):
                            try:
                                os.remove(stable)
                            except OSError:
                                pass
            finally:
                _thread_local.redirect = None
            if not handed_off_to_editor:
                if outputs:
                    self.after(0, self._on_job_outputs, outputs)
                self.after(0, self._on_done, all_ok,
                           _shared_error_key(error_keys), fallback_count)

        threading.Thread(target=run, daemon=True).start()

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title=self._s("label_video"),
            filetypes=[("Video", "*.mp4 *.mkv *.webm *.avi *.mov"), ("All", "*.*")]
        )
        for p in paths:
            if p not in self._batch_files:
                self._batch_files.append(p)
                self._batch_listbox.insert("end", Path(p).name)
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
        p = filedialog.asksaveasfilename(
            title=self._s("label_output"),
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("All", "*.*")]
        )
        if p:
            self._output_var.set(p)

    def _browse_output_dir(self):
        """Pick the single folder where translated files are written."""
        initial = self._output_dir_var.get().strip() or str(
            _platforms.default_output_dir())
        chosen = filedialog.askdirectory(title=self._s("label_output_dir"),
                                         initialdir=initial, mustexist=False)
        if chosen:
            self._output_dir_var.set(chosen)
            self._persist_output_dir()

    def _persist_output_dir(self):
        """Save the configured output folder (empty string means the default)."""
        save_config({"output_dir": self._output_dir_var.get().strip()})

    # ── Translation start ─────────────────────────────────────────────────────

    def _start(self):
        if self._running or self._ollama_setup_in_flight or self._player_release_pending:
            return
        if self._block_if_live_active():
            return
        if not self._batch_files:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_video"))
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
            except tk.TclError:
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
        deadline = time.monotonic() + 2.0

        def poll():
            if self._destroying:
                return
            if (self._player_controller.is_released({
                    "idle-active": self._player_bridge.latest("idle-active")})
                    or time.monotonic() >= deadline):
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
        except (ValueError, tk.TclError):
            rate = 0
        cfg = load_config()
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
        if hf_token and use_diarization:
            save_hf_token(hf_token)
        # Persist Ollama prefs (model/url/slot_aware/thinking) when the user
        # has selected this engine - so the fields are pre-filled on next launch.
        if translation_engine == "llm_ollama":
            try:
                save_config({
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
            tts_engine="xtts" if self._use_xtts.get() else "edge",
            translation_engine=translation_engine,
            deepl_key=self._deepl_key_var.get().strip(),
            use_diarization=use_diarization,
            hf_token=hf_token,
            use_lipsync=self._use_lipsync.get(),
            xtts_speed=xtts_speed,
            # Hotwords parsed to normalized list (None if empty), so
            # translate_video keeps the unbiased decoder default.
            hotwords=_parse_hotwords_gui(self._hotwords_var.get()) or None,
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
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            try:
                # voice passed even though phase 1 is subs_only (no TTS):
                # avoids the misleading log "[i] yt_xxx | auto->it |
                # it-IT-ElsaNeural" that defaulted to LANGUAGES[lang]["voices"][0]
                # when voice was None. Now phase 1 log reflects user's actual
                # voice selection (used for real in phase 2 _run_with_segments).
                cfg = dataclasses.replace(p, video_in=video_path, subs_only=True)
                result = translate_video(**cfg.to_translate_video_kwargs())
                self.after(0, self._open_editor, video_path,
                           result["segments"], cleanup_path,
                           _count_fallback_segments(result))
            except Exception as e:
                self.after(0, self._log_write, f"[x] Error: {e}\n{traceback.format_exc()}\n")
                # Clean up the downloaded temp file even on phase-1 error
                self._cleanup_editor_tempfile(cleanup_path)
                self.after(0, self._on_done, False, _error_key_for(e))
            finally:
                _thread_local.redirect = None

        threading.Thread(target=phase1, daemon=True).start()

    def _cleanup_editor_tempfile(self, cleanup_path: str | None) -> None:
        """Remove the temporary file associated with the editor flow (URL download).
        Safe no-op if ``cleanup_path`` is None or does not exist."""
        if not cleanup_path:
            return
        try:
            if os.path.exists(cleanup_path):
                os.remove(cleanup_path)
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
            messagebox.showwarning(self._s("warn_editor"), self._s("msg_no_segments"))
            self._cleanup_editor_tempfile(cleanup_path)
            return
        if fallback_count:
            messagebox.showwarning(
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
        fd, self._editor_preview_srt = tempfile.mkstemp(
            suffix=".srt", prefix="vtai_editor_preview_")
        os.close(fd)
        preview_path = Path(self._editor_preview_srt)
        preview_path.write_text(
            segments_to_srt(segments), encoding="utf-8")
        preview_item = _player_core.MediaItem(
            video_path, "source", Path(video_path).name,
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

        editor = SubtitleEditor(self, segments, on_confirm, ui_s=self._s,
                                on_seek=on_seek, on_change=on_change)
        editor.transient(self)
        self._right_pane.update_idletasks()
        editor_x, editor_y, editor_w, editor_h = _player_core.editor_geometry(
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
                with contextlib.suppress(OSError):
                    os.remove(self._editor_preview_srt)
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
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            try:
                cfg = dataclasses.replace(
                    p,
                    video_in=video_path,
                    segments_override=segments,
                )
                result = translate_video(**cfg.to_translate_video_kwargs())
                from videotranslator.jobs import JobOutput
                output = JobOutput.from_result(
                    result, source_path=video_path if cleanup_path is None else None)
                if output.video_path:
                    self.after(0, self._on_job_outputs, [output])
                self.after(0, self._on_done, True)
            except Exception as e:
                self.after(0, self._log_write, f"[x] {e}\n{traceback.format_exc()}\n")
                self.after(0, self._on_done, False)
            finally:
                _thread_local.redirect = None
                self._cleanup_editor_tempfile(cleanup_path)

        threading.Thread(target=do, daemon=True).start()

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
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            total  = len(files)
            all_ok = True
            error_keys = []
            fallback_count = 0
            from videotranslator.jobs import JobOutput
            outputs = []
            try:
                for i, f in enumerate(files):
                    self.after(0, self._log_write,
                               f"\n{'-'*50}\n[{i+1}/{total}] {Path(f).name}\n{'-'*50}\n")
                    try:
                        cfg = dataclasses.replace(
                            p,
                            video_in=f,
                            output=p.output if len(files) == 1 else None,
                        )
                        result = translate_video(**cfg.to_translate_video_kwargs())
                        fallback_count += _count_fallback_segments(result)
                        output = JobOutput.from_result(result, source_path=f)
                        if output.video_path:
                            outputs.append(output)
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {e}\n{traceback.format_exc()}\n")
                        all_ok = False
                        error_keys.append(_error_key_for(e))
            finally:
                _thread_local.redirect = None
            if outputs:
                self.after(0, self._on_job_outputs, outputs)
            self.after(0, self._on_done, all_ok,
                       _shared_error_key(error_keys), fallback_count)

        threading.Thread(target=run_all, daemon=True).start()

    # ── Log ──────────────────────────────────────────────────────────────────

    _LOG_MAX_LINES = 5000

    def _log_write(self, text: str):
        if self._destroying:
            return
        # Smart auto-scroll: only follow tail if user hasn't scrolled up
        try:
            yview_bottom = self._log.yview()[1]
        except Exception:
            yview_bottom = 1.0
        at_bottom = yview_bottom >= 0.95
        self._log.configure(state="normal")
        self._log.insert("end", text)
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

    def _run_gui_preflight(self):
        if self._preflight_running:
            return
        self._preflight_running = True
        with contextlib.suppress(Exception):
            self._btn_preflight.configure(state="disabled")
        if not getattr(self, "_log_visible", True):
            self._log_visible = True
            self._log_container.grid()
            self._btn_log_toggle.configure(text=self._s("btn_log_hide"))
            with contextlib.suppress(Exception):
                save_config({"ui_log_visible": True})
        self._log_write("\n[*] Running diagnostics...\n")

        def worker():
            try:
                report = _run_preflight(required_packages=REQUIRED_PACKAGES,
                                        native_checks=(_libmpv_native_check,))
                text = "\n" + _format_preflight_report(report) + "\n"
                ok = report.ok
                failed = report.required_failures
                error_message = ""
            except Exception as exc:
                text = f"\n[!] Diagnostics failed: {exc}\n{traceback.format_exc()}\n"
                ok = False
                failed = ()
                error_message = str(exc)

            def done():
                if self._destroying:
                    return
                self._preflight_running = False
                with contextlib.suppress(Exception):
                    self._btn_preflight.configure(
                        state="normal", text=self._s("btn_preflight")
                    )
                self._log_write(text)
                try:
                    if error_message:
                        messagebox.showerror(
                            self._s("msg_preflight_title"), error_message, parent=self
                        )
                    elif ok:
                        messagebox.showinfo(
                            self._s("msg_preflight_title"),
                            self._s("msg_preflight_ok"),
                            parent=self,
                        )
                    elif failed:
                        messagebox.showwarning(
                            self._s("msg_preflight_title"),
                            self._s("msg_preflight_failed"),
                            parent=self,
                        )
                except Exception:
                    pass

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

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
                messagebox.showerror(self._s("msg_error_t"), str(e))
            except Exception:
                pass

    def _log_clear(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _toggle_log(self):
        self._log_visible = not getattr(self, "_log_visible", True)
        if self._log_visible:
            self._log_container.grid()
            self._btn_log_toggle.configure(text=self._s("btn_log_hide"))
        else:
            self._log_container.grid_remove()
            self._btn_log_toggle.configure(text=self._s("btn_log_show"))
        try:
            save_config({"ui_log_visible": self._log_visible})
        except Exception:
            pass

    # ── Done / Close ─────────────────────────────────────────────────────────

    def _on_done(self, success: bool, error_key: str | None = None,
                 fallback_count: int = 0):
        if self._destroying:
            return
        self._running = False
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        self._btn_download.configure(state="normal", text=self._s("btn_download"))
        if success:
            self._log_write("\n✓ Done!\n")
            if fallback_count:
                messagebox.showwarning(
                    self._s("msg_completed_t"),
                    self._s("msg_translation_partial").format(n=fallback_count),
                )
            else:
                messagebox.showinfo(self._s("msg_completed_t"), self._s("msg_completed"))
        else:
            messagebox.showerror(self._s("msg_error_t"), self._s(error_key or "msg_error"))

    def _on_close(self):
        if self._destroying:
            return
        if self._running:
            if not messagebox.askyesno(self._s("msg_confirm"), self._s("msg_confirm_stop")):
                return
        self._begin_close()

    def _begin_close(self) -> None:
        """Stop native player resources before destroying their Tk host window."""
        self._destroying = True
        self._theme.close()
        # Stop a live session first: its sched thread writes to backend.rt, so it
        # must be gone before the backend is terminated below.
        live = self._live_session
        if live is not None:
            self._live_session = None
            live.request_stop()
            with contextlib.suppress(Exception):
                live.join(4.0)
        if self._live_poll_after is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._live_poll_after)
            self._live_poll_after = None
        if self._player_poll_after is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._player_poll_after)
            self._player_poll_after = None
        self._close_started_at = time.monotonic()
        self._close_done = threading.Event()
        backend = self._player_backend
        voice_backend = self._voice_backend
        self._voice_backend = None
        guard = self._player_guard
        init_thread = self._player_init_thread
        if (backend is None and voice_backend is None
                and (init_thread is None or not init_thread.is_alive())):
            self._player_bridge.close()
            if guard is not None:
                guard.restore()
            self._close_done.set()
            self._finish_close()
            return

        def work():
            try:
                self._player_bridge.close()
                if voice_backend is not None:
                    with contextlib.suppress(Exception):
                        voice_backend.terminate(3.0)
                if backend is not None:
                    backend.terminate(3.0)
                if init_thread is not None and init_thread.is_alive():
                    init_thread.join(6.0)
            finally:
                if guard is not None:
                    guard.restore()
                self._close_done.set()

        self._redirecting_thread_factory(work, name="app-close").start()
        self.after(0, self._finish_close)

    def _finish_close(self) -> None:
        if self._close_done is None:
            return
        if (not self._close_done.is_set()
                and time.monotonic() - self._close_started_at < 10.0):
            self.after(50, self._finish_close)
            return
        # Snapshot under lock, then terminate outside the lock so worker
        # threads calling _register_subprocess/_unregister_subprocess on
        # another subprocess are not blocked while a slow kill is in flight.
        for p in _snapshot_active_subprocesses():
            with contextlib.suppress(Exception):
                p.terminate()
        self.destroy()


# ═══════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════

def _cli():
    from videotranslator.cli import _cli as _real_cli
    _real_cli()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _cli()
    else:
        App().mainloop()
