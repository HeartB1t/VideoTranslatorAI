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
import logging
import platform
import re
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

# Language names are shown in their own language (endonyms), the usual
# convention of language pickers: the same list reads right in every UI
# language, and each user finds their language by its own name.
LANGUAGE_NATIVE_NAMES = {
    "ar": "العربية", "zh-CN": "中文", "cs": "Čeština", "da": "Dansk",
    "de": "Deutsch", "el": "Ελληνικά", "en": "English", "es": "Español",
    "fi": "Suomi", "fr": "Français", "hi": "हिन्दी", "hu": "Magyar",
    "id": "Bahasa Indonesia", "it": "Italiano", "ja": "日本語", "ko": "한국어",
    "nl": "Nederlands", "no": "Norsk", "pl": "Polski", "pt": "Português",
    "ro": "Română", "ru": "Русский", "sv": "Svenska", "tr": "Türkçe",
    "uk": "Українська", "vi": "Tiếng Việt",
}
for _code, _entry in LANGUAGES.items():
    _flag = _entry["name"].split(" ", 1)[0]
    _entry["name"] = f"{_flag} {LANGUAGE_NATIVE_NAMES[_code]}"

# Source languages offered for transcription; "auto" is labelled with the
# UI string "lang_auto_detect".
SOURCE_LANG_CODES = ("auto", "en", "it", "es", "fr", "de", "pt", "ru", "zh-CN",
                     "ja", "ko", "ar")
SOURCE_LANGS = {code: ("🔍 Auto" if code == "auto" else LANGUAGES[code]["name"])
                for code in SOURCE_LANG_CODES}

# Languages supported by XTTS v2 (maps our codes → XTTS codes)
XTTS_LANGS = {
    "ar": "ar", "zh-CN": "zh-cn", "cs": "cs", "de": "de",
    "en": "en", "es": "es", "fr": "fr", "hi": "hi",
    "hu": "hu", "it": "it", "ja": "ja", "ko": "ko",
    "nl": "nl", "pl": "pl", "pt": "pt", "ru": "ru", "tr": "tr",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"]
# Config keys of the 'Models for this PC' window: the choices applied last
# (restored at startup) and the ones they replaced (Restore previous).
_MODELS_CHOICE_KEY = "models_choice"
_MODELS_PREVIOUS_KEY = "models_previous"


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
from videotranslator import app_log as _app_log  # noqa: E402
from videotranslator import bevel_tk as _bevel_tk  # noqa: E402
from videotranslator import gear_icon as _gear_icon  # noqa: E402
from videotranslator import libmpv_runtime as _libmpv_runtime  # noqa: E402
from videotranslator import platforms as _platforms  # noqa: E402
from videotranslator.resource_paths import assets_dir as _assets_dir  # noqa: E402
from videotranslator import live_session as _live_session_module  # noqa: E402
from videotranslator.live_translate import is_model_heavy_for_live as _is_model_heavy_for_live  # noqa: E402
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
    BASE_THEMES as _BASE_THEMES,
    SKIN_CHOICES as _SKIN_CHOICES,
    contrast_ratio as _contrast_ratio,
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
BORDER_PX = _DEFAULT_PALETTE.border_px     # card frame thickness, set per theme


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
        "section_extract_audio": "Estrai audio",
        "label_audio_format": "Formato:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Solo strumentale (rimuovi voce)",
        "btn_extract_audio": "Estrai",
        "msg_no_input_extract": "Nessun file o URL da cui estrarre l'audio.",
        "msg_extract_done": "Estrazione audio completata.",
        "log_extracting": "Estrazione audio da: {}",
        "label_from":         "Da:",
        "label_to":           "A:",
        "label_voice":        "Voce:",
        "label_tts_rate":     "Velocità TTS:",
        "panel_input": "Input",
        "panel_translation": "Traduzione",
        "panel_profile": "Profilo di lavoro",
        "panel_start": "Avvio",
        "section_audio": "Audio",
        "section_voice_cloning": "Clonazione vocale",
        "section_lip_sync": "Sincronizzazione labiale",
        "section_diarization": "Riconoscimento dei parlanti",
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
        "msg_secret_session_only": "Keyring non disponibile: la chiave vale solo per questa sessione (non salvata su disco).",
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
        "btn_download":       "↓  Scarica e Traduci",
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
        "section_extract_audio": "Extract audio",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Instrumental only (remove voice)",
        "btn_extract_audio": "Extract",
        "msg_no_input_extract": "No file or URL to extract audio from.",
        "msg_extract_done": "Audio extraction complete.",
        "log_extracting": "Extracting audio from: {}",
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
        "msg_secret_session_only": "Keyring unavailable: the key is kept only for this session (not saved to disk).",
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
        "btn_download":       "↓  Download & Translate",
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
        "section_extract_audio": "استخراج الصوت",
        "label_audio_format": "الصيغة:",
        "label_audio_bitrate": "معدل البت:",
        "opt_instrumental": "الموسيقى فقط (إزالة الصوت)",
        "btn_extract_audio": "استخراج",
        "msg_no_input_extract": "لا يوجد ملف أو رابط لاستخراج الصوت منه.",
        "msg_extract_done": "اكتمل استخراج الصوت.",
        "log_extracting": "استخراج الصوت من: {}",
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
        "msg_secret_session_only": "خزنة المفاتيح غير متاحة: يُحتفظ بالمفتاح لهذه الجلسة فقط (لا يُحفظ على القرص).",
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
        "btn_download": "↓ تنزيل وترجمة",
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
        "section_extract_audio": "提取音频",
        "label_audio_format": "格式：",
        "label_audio_bitrate": "比特率：",
        "opt_instrumental": "仅伴奏（移除人声）",
        "btn_extract_audio": "提取",
        "msg_no_input_extract": "没有可提取音频的文件或网址。",
        "msg_extract_done": "音频提取完成。",
        "log_extracting": "正在提取音频：{}",
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
        "msg_secret_session_only": "密钥环不可用：密钥仅在本次会话中保留（不会保存到磁盘）。",
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
        "btn_download": "↓ 下载和翻译",
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
        "section_extract_audio": "Extrahovat zvuk",
        "label_audio_format": "Formát:",
        "label_audio_bitrate": "Datový tok:",
        "opt_instrumental": "Pouze instrumentální (odebrat hlas)",
        "btn_extract_audio": "Extrahovat",
        "msg_no_input_extract": "Žádný soubor ani URL k extrakci zvuku.",
        "msg_extract_done": "Extrakce zvuku dokončena.",
        "log_extracting": "Extrahuji zvuk z: {}",
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
        "section_lip_sync": "Synchronizace rtů",
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
        "msg_secret_session_only": "Klíčenka není dostupná: klíč je uchován pouze pro tuto relaci (neukládá se na disk).",
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
        "btn_download": "↓ Stáhnout a přeložit",
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
        "section_extract_audio": "Udtræk lyd",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Kun instrumental (fjern stemme)",
        "btn_extract_audio": "Udtræk",
        "msg_no_input_extract": "Ingen fil eller URL at udtrække lyd fra.",
        "msg_extract_done": "Lydudtrækning fuldført.",
        "log_extracting": "Udtrækker lyd fra: {}",
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
        "section_lip_sync": "Læbesynkronisering",
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
        "msg_secret_session_only": "Nøglering ikke tilgængelig: nøglen bevares kun i denne session (gemmes ikke på disken).",
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
        "btn_download": "↓ Download og oversæt",
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
        "section_extract_audio": "Audio extraheren",
        "label_audio_format": "Formaat:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Alleen instrumentaal (stem verwijderen)",
        "btn_extract_audio": "Extraheren",
        "msg_no_input_extract": "Geen bestand of URL om audio uit te extraheren.",
        "msg_extract_done": "Audio-extractie voltooid.",
        "log_extracting": "Audio extraheren uit: {}",
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
        "section_lip_sync": "Lipsynchronisatie",
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
        "msg_secret_session_only": "Sleutelring niet beschikbaar: de sleutel wordt alleen voor deze sessie bewaard (niet op schijf opgeslagen).",
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
        "btn_download": "↓ Downloaden en vertalen",
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
        "section_extract_audio": "Pura ääni",
        "label_audio_format": "Muoto:",
        "label_audio_bitrate": "Bittinopeus:",
        "opt_instrumental": "Vain instrumentaali (poista ääni)",
        "btn_extract_audio": "Pura",
        "msg_no_input_extract": "Ei tiedostoa tai URL-osoitetta, josta purkaa ääni.",
        "msg_extract_done": "Äänen purku valmis.",
        "log_extracting": "Puretaan ääntä kohteesta: {}",
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
        "msg_secret_session_only": "Avainnippu ei käytettävissä: avain säilytetään vain tätä istuntoa varten (ei tallenneta levylle).",
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
        "btn_download": "↓ Lataa ja käännä",
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
        "section_extract_audio": "Extraire l'audio",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Débit:",
        "opt_instrumental": "Instrumental seulement (supprimer la voix)",
        "btn_extract_audio": "Extraire",
        "msg_no_input_extract": "Aucun fichier ou URL pour extraire l'audio.",
        "msg_extract_done": "Extraction audio terminée.",
        "log_extracting": "Extraction de l'audio depuis: {}",
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
        "msg_secret_session_only": "Trousseau indisponible : la clé est conservée uniquement pour cette session (non enregistrée sur le disque).",
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
        "btn_download": "↓ Télécharger et traduire",
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
        "section_extract_audio": "Audio extrahieren",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Nur instrumental (Stimme entfernen)",
        "btn_extract_audio": "Extrahieren",
        "msg_no_input_extract": "Keine Datei oder URL zum Extrahieren von Audio.",
        "msg_extract_done": "Audio-Extraktion abgeschlossen.",
        "log_extracting": "Audio wird extrahiert aus: {}",
        "label_from": "Aus:",
        "label_to": "Zu:",
        "label_voice": "Stimme:",
        "label_tts_rate": "TTS-Geschwindigkeit:",
        "panel_input": "Eingabe",
        "panel_translation": "Übersetzung",
        "panel_profile": "Workflow-Profil",
        "panel_start": "Start",
        "section_audio": "Audio",
        "section_voice_cloning": "Stimmklonen",
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
        "msg_secret_session_only": "Schlüsselbund nicht verfügbar: Der Schlüssel wird nur für diese Sitzung behalten (nicht auf der Festplatte gespeichert).",
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
        "btn_download": "↓ Herunterladen und übersetzen",
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
        "section_extract_audio": "Εξαγωγή ήχου",
        "label_audio_format": "Μορφή:",
        "label_audio_bitrate": "Ρυθμός bit:",
        "opt_instrumental": "Μόνο ορχηστρικό (αφαίρεση φωνής)",
        "btn_extract_audio": "Εξαγωγή",
        "msg_no_input_extract": "Δεν υπάρχει αρχείο ή URL για εξαγωγή ήχου.",
        "msg_extract_done": "Η εξαγωγή ήχου ολοκληρώθηκε.",
        "log_extracting": "Εξαγωγή ήχου από: {}",
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
        "section_lip_sync": "Συγχρονισμός χειλιών",
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
        "msg_secret_session_only": "Η θήκη κλειδιών δεν είναι διαθέσιμη: το κλειδί διατηρείται μόνο για αυτήν τη συνεδρία (δεν αποθηκεύεται στον δίσκο).",
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
        "btn_download": "↓ Λήψη & Μετάφραση",
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
        "section_extract_audio": "ऑडियो निकालें",
        "label_audio_format": "प्रारूप:",
        "label_audio_bitrate": "बिटरेट:",
        "opt_instrumental": "केवल वाद्य (आवाज़ हटाएँ)",
        "btn_extract_audio": "निकालें",
        "msg_no_input_extract": "ऑडियो निकालने के लिए कोई फ़ाइल या URL नहीं।",
        "msg_extract_done": "ऑडियो निष्कर्षण पूर्ण।",
        "log_extracting": "ऑडियो निकाला जा रहा है: {}",
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
        "msg_secret_session_only": "कीरिंग उपलब्ध नहीं: कुंजी केवल इस सत्र के लिए रखी जाती है (डिस्क पर सहेजी नहीं जाती)।",
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
        "btn_download": "↓ डाउनलोड करें और अनुवाद करें",
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
        "section_extract_audio": "Hang kinyerése",
        "label_audio_format": "Formátum:",
        "label_audio_bitrate": "Bitráta:",
        "opt_instrumental": "Csak hangszeres (ének eltávolítása)",
        "btn_extract_audio": "Kinyerés",
        "msg_no_input_extract": "Nincs fájl vagy URL a hang kinyeréséhez.",
        "msg_extract_done": "A hang kinyerése kész.",
        "log_extracting": "Hang kinyerése innen: {}",
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
        "msg_secret_session_only": "A kulcstartó nem érhető el: a kulcs csak erre a munkamenetre marad meg (nem kerül lemezre mentésre).",
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
        "btn_download": "↓ Letöltés és fordítás",
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
        "section_extract_audio": "Ekstrak audio",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Hanya instrumental (hapus vokal)",
        "btn_extract_audio": "Ekstrak",
        "msg_no_input_extract": "Tidak ada file atau URL untuk mengekstrak audio.",
        "msg_extract_done": "Ekstraksi audio selesai.",
        "log_extracting": "Mengekstrak audio dari: {}",
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
        "msg_secret_session_only": "Keyring tidak tersedia: kunci hanya disimpan untuk sesi ini (tidak disimpan ke disk).",
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
        "btn_download": "↓ Unduh & Terjemahkan",
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
        "section_extract_audio": "音声を抽出",
        "label_audio_format": "形式：",
        "label_audio_bitrate": "ビットレート：",
        "opt_instrumental": "伴奏のみ（音声を除去）",
        "btn_extract_audio": "抽出",
        "msg_no_input_extract": "音声を抽出するファイルまたはURLがありません。",
        "msg_extract_done": "音声の抽出が完了しました。",
        "log_extracting": "音声を抽出中: {}",
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
        "msg_secret_session_only": "キーリングを利用できません。キーはこのセッションのみ保持されます（ディスクには保存されません）。",
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
        "btn_download": "↓ ダウンロードと翻訳",
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
        "section_extract_audio": "오디오 추출",
        "label_audio_format": "형식:",
        "label_audio_bitrate": "비트레이트:",
        "opt_instrumental": "반주만 (음성 제거)",
        "btn_extract_audio": "추출",
        "msg_no_input_extract": "오디오를 추출할 파일 또는 URL이 없습니다.",
        "msg_extract_done": "오디오 추출 완료.",
        "log_extracting": "오디오 추출 중: {}",
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
        "msg_secret_session_only": "키링을 사용할 수 없습니다. 키는 이 세션에만 유지됩니다(디스크에 저장되지 않음).",
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
        "btn_download": "↓ 다운로드 및 번역",
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
        "section_extract_audio": "Trekk ut lyd",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Kun instrumental (fjern stemme)",
        "btn_extract_audio": "Trekk ut",
        "msg_no_input_extract": "Ingen fil eller URL å trekke ut lyd fra.",
        "msg_extract_done": "Lyduttrekk fullført.",
        "log_extracting": "Trekker ut lyd fra: {}",
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
        "section_lip_sync": "Leppesynkronisering",
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
        "msg_secret_session_only": "Nøkkelring utilgjengelig: nøkkelen beholdes kun for denne økten (lagres ikke på disk).",
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
        "btn_download": "↓ Last ned og oversett",
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
        "section_extract_audio": "Wyodrębnij dźwięk",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Przepływność:",
        "opt_instrumental": "Tylko instrumental (usuń głos)",
        "btn_extract_audio": "Wyodrębnij",
        "msg_no_input_extract": "Brak pliku lub adresu URL do wyodrębnienia dźwięku.",
        "msg_extract_done": "Wyodrębnianie dźwięku zakończone.",
        "log_extracting": "Wyodrębnianie dźwięku z: {}",
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
        "msg_secret_session_only": "Pęk kluczy niedostępny: klucz jest przechowywany tylko dla tej sesji (nie zapisywany na dysku).",
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
        "btn_download": "↓ Pobierz i przetłumacz",
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
        "section_extract_audio": "Extrair áudio",
        "label_audio_format": "Formato:",
        "label_audio_bitrate": "Taxa de bits:",
        "opt_instrumental": "Somente instrumental (remover voz)",
        "btn_extract_audio": "Extrair",
        "msg_no_input_extract": "Nenhum arquivo ou URL para extrair o áudio.",
        "msg_extract_done": "Extração de áudio concluída.",
        "log_extracting": "Extraindo áudio de: {}",
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
        "msg_secret_session_only": "Keyring indisponível: a chave é mantida apenas para esta sessão (não salva no disco).",
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
        "btn_download": "↓ Baixe e traduza",
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
        "section_extract_audio": "Extrage audio",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Rată de biți:",
        "opt_instrumental": "Doar instrumental (elimină vocea)",
        "btn_extract_audio": "Extrage",
        "msg_no_input_extract": "Niciun fișier sau URL din care să extragi audio.",
        "msg_extract_done": "Extragerea audio s-a finalizat.",
        "log_extracting": "Se extrage audio din: {}",
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
        "section_lip_sync": "Sincronizare labială",
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
        "msg_secret_session_only": "Breloc de chei indisponibil: cheia este păstrată doar pentru această sesiune (nu este salvată pe disc).",
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
        "btn_download": "↓ Descărcați și traduceți",
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
        "section_extract_audio": "Извлечь звук",
        "label_audio_format": "Формат:",
        "label_audio_bitrate": "Битрейт:",
        "opt_instrumental": "Только инструментал (убрать голос)",
        "btn_extract_audio": "Извлечь",
        "msg_no_input_extract": "Нет файла или URL для извлечения звука.",
        "msg_extract_done": "Извлечение звука завершено.",
        "log_extracting": "Извлечение звука из: {}",
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
        "msg_secret_session_only": "Хранилище ключей недоступно: ключ сохраняется только для этого сеанса (не записывается на диск).",
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
        "btn_download": "↓ Скачать и перевести",
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
        "section_extract_audio": "Extraer audio",
        "label_audio_format": "Formato:",
        "label_audio_bitrate": "Tasa de bits:",
        "opt_instrumental": "Solo instrumental (quitar voz)",
        "btn_extract_audio": "Extraer",
        "msg_no_input_extract": "No hay archivo ni URL para extraer el audio.",
        "msg_extract_done": "Extracción de audio completada.",
        "log_extracting": "Extrayendo audio de: {}",
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
        "msg_secret_session_only": "Llavero no disponible: la clave se conserva solo para esta sesión (no se guarda en el disco).",
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
        "btn_download": "↓ Descargar y traducir",
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
        "section_extract_audio": "Extrahera ljud",
        "label_audio_format": "Format:",
        "label_audio_bitrate": "Bithastighet:",
        "opt_instrumental": "Endast instrumental (ta bort röst)",
        "btn_extract_audio": "Extrahera",
        "msg_no_input_extract": "Ingen fil eller URL att extrahera ljud från.",
        "msg_extract_done": "Ljudextrahering klar.",
        "log_extracting": "Extraherar ljud från: {}",
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
        "msg_secret_session_only": "Nyckelring ej tillgänglig: nyckeln behålls endast för denna session (sparas inte på disken).",
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
        "btn_download": "↓ Ladda ner och översätt",
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
        "section_extract_audio": "Sesi çıkar",
        "label_audio_format": "Biçim:",
        "label_audio_bitrate": "Bit hızı:",
        "opt_instrumental": "Yalnızca enstrümantal (sesi kaldır)",
        "btn_extract_audio": "Çıkar",
        "msg_no_input_extract": "Ses çıkarılacak dosya veya URL yok.",
        "msg_extract_done": "Ses çıkarma tamamlandı.",
        "log_extracting": "Ses çıkarılıyor: {}",
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
        "msg_secret_session_only": "Anahtarlık kullanılamıyor: anahtar yalnızca bu oturum için tutulur (diske kaydedilmez).",
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
        "btn_download": "↓ İndir ve Çevir",
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
        "section_extract_audio": "Витягти звук",
        "label_audio_format": "Формат:",
        "label_audio_bitrate": "Бітрейт:",
        "opt_instrumental": "Лише інструментал (прибрати голос)",
        "btn_extract_audio": "Витягти",
        "msg_no_input_extract": "Немає файлу або URL для витягання звуку.",
        "msg_extract_done": "Витягання звуку завершено.",
        "log_extracting": "Витягання звуку з: {}",
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
        "msg_secret_session_only": "Сховище ключів недоступне: ключ зберігається лише для цього сеансу (не записується на диск).",
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
        "btn_download": "↓ Завантажте та перекладіть",
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
        "section_extract_audio": "Trích xuất âm thanh",
        "label_audio_format": "Định dạng:",
        "label_audio_bitrate": "Bitrate:",
        "opt_instrumental": "Chỉ nhạc nền (loại bỏ giọng)",
        "btn_extract_audio": "Trích xuất",
        "msg_no_input_extract": "Không có tệp hoặc URL để trích xuất âm thanh.",
        "msg_extract_done": "Đã trích xuất âm thanh xong.",
        "log_extracting": "Đang trích xuất âm thanh từ: {}",
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
        "msg_secret_session_only": "Không có keyring: khóa chỉ được giữ cho phiên này (không lưu vào đĩa).",
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
        "btn_download": "↓ Tải xuống và dịch",
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
from videotranslator.ui_strings_models import merge_into as _merge_models_strings  # noqa: E402
from videotranslator.voice_preview import preview_sentence as _preview_sentence  # noqa: E402
from videotranslator.voice_preview import synthesize_edge as _synthesize_edge_preview  # noqa: E402
from videotranslator.voice_preview_tk import PreviewHub as _PreviewHub  # noqa: E402
from videotranslator.voice_preview_tk import SpeakerButton as _SpeakerButton  # noqa: E402
from videotranslator.voice_preview_tk import error_key as _preview_error_key  # noqa: E402
from videotranslator.video_effects import shader_for_theme as _shader_for_theme  # noqa: E402
_PLAYER_STRING_PROBLEMS += _merge_models_strings(UI_STRINGS)
from videotranslator.ui_strings_log import merge_into as _merge_log_strings  # noqa: E402
_PLAYER_STRING_PROBLEMS += _merge_log_strings(UI_STRINGS)
from videotranslator.ui_strings_python import merge_into as _merge_python_strings  # noqa: E402
_PLAYER_STRING_PROBLEMS += _merge_python_strings(UI_STRINGS)


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


from videotranslator.segments import (  # noqa: E402
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
    check_ollama as _check_ollama_status,
    ollama_model_size_gb as _ollama_model_size_gb,
    ollama_models_dir as _ollama_models_dir,
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


def _ollama_else_text(texts: dict, fallback: str) -> str:
    return (texts["ollama_pull_else_model"].format(other=fallback) if fallback
            else texts["ollama_pull_else_google"])


def _ollama_pull_question(texts: dict, model: str, fallback: str, fit=None) -> str:
    """The question before pulling ``model``: its size when known, a warning
    when it does not fit the memory (``fit``, a model_catalog.PullFit), and
    what a translation uses otherwise (the installed ``fallback``, or
    Google). ``texts`` holds the UI strings, read on the Tk thread."""
    parts = [texts["ollama_pull_ask"].format(model=model)]
    size = _ollama_model_size_gb(model)
    if size:
        parts.append(texts["ollama_pull_size"].format(gb=f"{size:g}"))
    if fit is not None and fit.verdict in ("too_big", "tight"):
        key = "ollama_pull_heavy" if fit.verdict == "too_big" else "ollama_pull_tight"
        have = "?" if fit.have_gb is None else f"{fit.have_gb:.1f}"
        parts.append(texts[key].format(model=model, need=f"{fit.need_gb:g}", have=have))
    parts.append(_ollama_else_text(texts, fallback))
    return "\n\n".join(parts)


def _ollama_no_disk_text(texts: dict, model: str, fallback: str, fit) -> str:
    """Why ``model`` is not offered: it does not fit the disk."""
    free = "?" if fit.disk_free_gb is None else f"{fit.disk_free_gb:.1f}"
    return "\n\n".join((texts["ollama_pull_no_disk"].format(
        model=model, need=f"{fit.download_gb:.1f}", free=free),
        _ollama_else_text(texts, fallback)))


from videotranslator.ollama_translate import translate_with_ollama  # noqa: E402


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
WAV2LIP_TIMEOUT = 3600  # seconds before Wav2Lip subprocess is forcibly killed

# Base deps needed by Wav2Lip on all platforms; dlib + face-detection extras
# are handled separately below (different install strategy per OS).
from videotranslator.wav2lip_runtime import (  # noqa: E402
    WAV2LIP_BASE_REQUIREMENTS,
    download_wav2lip_model as _download_wav2lip_model,
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
         "--break-system-packages", *_system_packages.pip_constraint_args()] + missing,
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
             "--break-system-packages", *_system_packages.pip_constraint_args()] + light_pkgs,
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
        [sys.executable, "-m", "pip", "install", "--break-system-packages",
         *_system_packages.pip_constraint_args(), "dlib"],
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
        try:
            _download_wav2lip_model(WAV2LIP_MODEL)
        except Exception as e:
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


def load_elevenlabs_key() -> str:
    """The ElevenLabs API key: system keyring first, JSON config as fallback."""
    from videotranslator import elevenlabs_tts as _el
    return _load_secret_token(
        keyring_backend=_keyring_available(), config_path=CONFIG_PATH,
        service_name=KEYRING_SERVICE, username=_el.KEYRING_USERNAME,
        config_key=_el.CONFIG_KEY)


# A cleartext secret in the JSON config is acceptable on Linux/macOS (home is
# 0700 and the file is 0600), but not on Windows, where %APPDATA% is not locked
# down the same way. There, without a keyring the secret stays in memory for
# the session only.
_ALLOW_PLAINTEXT_SECRETS = not sys.platform.startswith("win")


def save_elevenlabs_key(key: str) -> str:
    """Persist the ElevenLabs key. Returns 'keyring', 'plaintext' or 'session'."""
    from videotranslator import elevenlabs_tts as _el
    stored = _save_secret_token(
        key, keyring_backend=_keyring_available(), config_path=CONFIG_PATH,
        service_name=KEYRING_SERVICE, username=_el.KEYRING_USERNAME,
        config_key=_el.CONFIG_KEY, allow_plaintext=_ALLOW_PLAINTEXT_SECRETS)
    if stored:
        return "keyring"
    return "plaintext" if _ALLOW_PLAINTEXT_SECRETS else "session"


def save_hf_token(token: str) -> str:
    """Persist the HF token. Returns 'keyring', 'plaintext' or 'session'.

    On Windows without a keyring the token is NOT written in cleartext: it is
    kept in memory for the session only (status 'session').
    """
    token = (token or "").strip()
    if not token:
        return "keyring"
    stored_in_keyring = _save_secret_token(
        token,
        keyring_backend=_keyring_available(),
        config_path=CONFIG_PATH,
        service_name=KEYRING_SERVICE,
        username=KEYRING_USERNAME,
        allow_plaintext=_ALLOW_PLAINTEXT_SECRETS,
    )
    if stored_in_keyring:
        return "keyring"
    if _ALLOW_PLAINTEXT_SECRETS:
        print(f"     ! keyring backend unavailable, "
              f"storing HF token in plaintext at {CONFIG_PATH}", flush=True)
        return "plaintext"
    return "session"


from videotranslator.diarization import assign_speakers, diarize_audio  # noqa: E402,F401
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
    voicebox_url: str = "http://127.0.0.1:17493",
    voicebox_engine: str = "chatterbox",
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
        voicebox_url=voicebox_url,
        voicebox_engine=voicebox_engine,
        runtime=_build_pipeline_runtime(),
    )


# ═══════════════════════════════════════════════════════════
#  GUI HELPERS
# ═══════════════════════════════════════════════════════════

def check_dependencies():
    return _find_missing_dependencies(REQUIRED_PACKAGES)


_thread_local = threading.local()
# Where print() of a thread without its own redirect goes while the GUI runs:
# the Log panel (and so the log file), set by App, cleared when it closes.
_DEFAULT_REDIRECT = None
# Control segments of App._log_insert (never Text tags): a \r that empties the
# panel's current line, and the removal of the previous line before a
# progress bar is rewritten.
_LOG_CUT_LINE = "ctl_cut_line"
_LOG_DROP_PREVIOUS_LINE = "ctl_drop_previous_line"


class _GlobalRedirect(io.TextIOBase):
    """Installed once at GUI startup. Routes print() to the per-thread _TkStreamRedirect
    if one is active for the calling thread, else to the app-wide default one (the
    Log panel), otherwise passes through to the original stream."""

    def __init__(self, original):
        super().__init__()
        self._original = original

    def writable(self): return True

    def write(self, s):
        redir = getattr(_thread_local, "redirect", None) or _DEFAULT_REDIRECT
        if redir is not None:
            return redir.write(s)
        if self._original is None:
            # pythonw: sys.stdout/sys.stderr are None, so library output from
            # threads without a GUI redirect (tqdm, warnings) is dropped
            # instead of raising (spec R9).
            return len(s)
        return self._original.write(s)

    def flush(self):
        redir = getattr(_thread_local, "redirect", None) or _DEFAULT_REDIRECT
        if redir is not None:
            redir.flush()
        elif self._original is not None:
            self._original.flush()

    def fileno(self):
        if self._original is None:
            raise io.UnsupportedOperation("fileno")
        return self._original.fileno()


class _LogPanelHandler(logging.Handler):
    """Warnings and errors of the libraries (python ``logging``) to the Log panel."""

    def __init__(self, app):
        super().__init__(level=logging.WARNING)
        self._app = app

    def emit(self, record):
        try:
            level = "error" if record.levelno >= logging.ERROR else "warn"
            area = (record.name or "lib").split(".")[0][:15]
            self._app._log_emit(" ".join(record.getMessage().split()), area, level)
        except Exception:                        # noqa: BLE001
            pass


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
            except (RuntimeError, tk.TclError):
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
                         font="VT.Base", relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACC)
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


# Repetitive mpv/ffmpeg notices that do not affect playback, keyed by kind: each is
# shown once, then hidden, so the log stays readable (the X11 block is separate).
_HARMLESS_MPV_NOTICES = (
    # ffmpeg's h264 decoder does not handle "late SEI" metadata in some streams
    # and repeats this pair for every occurrence; the picture decodes fine.
    ("h264_late_sei", ("late sei is not implemented",
                       "if you want to help, upload a sample of this file")),
    # The voice clips are constant-bitrate mp3, where this estimate is exact.
    ("mp3_duration", ("estimating duration from bitrate",)),
)


def _harmless_mpv_log_kind(line: str) -> str | None:
    """The kind of a known harmless, repetitive mpv notice, or None."""
    low = line.lower()
    for kind, markers in _HARMLESS_MPV_NOTICES:
        if any(marker in low for marker in markers):
            return kind
    return None


from videotranslator.app_host import host as _app_host  # noqa: E402

# Before the mixins: they read this module's globals through app_host.
_app_host.bind(sys.modules[__name__])
from videotranslator.app_setup_tk import SetupMixin as _SetupMixin  # noqa: E402
from videotranslator.app_widgets_tk import WidgetsMixin as _WidgetsMixin  # noqa: E402
from videotranslator.app_build_tk import BuildMixin as _BuildMixin  # noqa: E402
from videotranslator.app_settings_tk import SettingsMixin as _SettingsMixin  # noqa: E402
from videotranslator.app_engines_tk import EnginesMixin as _EnginesMixin  # noqa: E402
from videotranslator.app_player_tk import PlayerMixin as _PlayerMixin  # noqa: E402
from videotranslator.app_live_tk import LiveMixin as _LiveMixin  # noqa: E402
from videotranslator.app_jobs_tk import JobsMixin as _JobsMixin  # noqa: E402
from videotranslator.app_log_tk import LogMixin as _LogMixin  # noqa: E402


class App(_SetupMixin, _WidgetsMixin, _BuildMixin, _SettingsMixin, _EnginesMixin, _PlayerMixin, _LiveMixin, _JobsMixin, _LogMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        # Everything the Log panel shows also goes to a daily log file (7 days).
        self._log_file = _app_log.FileSink(_app_log.log_dir_for(CONFIG_PATH))
        self._log_hooks_installed = False
        self._log_bol = True                   # the next log text starts a line
        self._log_level_now = "info"           # level of the line being written
        self._log_progress_key = None          # progress activity on the panel's last line
        self._log_pending_cr = False           # a trailing \r, judged with the next text
        self._last_click_at = 0.0              # to drop the echo of a clicked command
        _ocfg = load_config()
        self._ui_settings = _normalize_ui_settings(_ocfg, lang_codes=UI_LANG_CODES)
        # Movable panels of the settings column: id -> (outer frame, pack
        # options), current order, and the state of a drag in progress.
        self._panels = {}
        self._card_frames = []                 # outer frames, for BORDER_PX
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
        # One voice preview at a time for the whole app (speaker icons).
        self._voice_preview_hub = _PreviewHub(self._post_if_alive)
        self._voice_preview_key = None
        self._voice_speaker = None
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
        # Voicebox: voice cloning by a separate local server (off by default).
        self._use_voicebox = tk.BooleanVar(value=False)
        self._voicebox_url_var = tk.StringVar(
            value=_ocfg.get("voicebox_url", "http://127.0.0.1:17493"))
        self._voicebox_engine_var = tk.StringVar(
            value=_ocfg.get("voicebox_engine", "chatterbox"))
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
        self._ollama_setup_running = False     # _ensure_ollama_ready_async, one at a time
        self._ollama_setup_pending = []        # its callers that arrived meanwhile
        self._ollama_pull_declined = set()     # models refused this session: not asked again
        self._ollama_memory_checked = set()    # models checked against the memory this session
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
        # Auto-install del player: parte una sola volta per sessione quando il
        # player manca ed e' installabile (stesso spirito di ollama_auto_install).
        # Il flag evita loop se l'install fallisce e lo stato viene riletto; il
        # click manuale sul bottone resta sempre attivo (non guardato dal flag).
        self._player_auto_tried = False
        self._player_settings = _player_settings_module.normalize_player_settings(
            _ocfg, sys_platform=sys.platform)
        self._player_bridge = _player_engine.EventBridge()
        self._player_mixer = _player_engine.VolumeMixer(
            user_volume=self._player_settings.volume,
            muted=self._player_settings.muted)
        self._player_clock = _player_engine.PlaybackClock(log=self._player_log)
        self._player_backend = None
        self._voice_backend = None            # second mpv for live dubbed voice (P5)
        # The voice mpv is built on a worker; the result is handed to Tk through
        # _voice_built under _voice_lock, so close and VO fallback can always take
        # (and terminate) a result that is in flight. The token marks the one
        # current build: close/fallback clear it to invalidate a build under way.
        self._voice_lock = threading.Lock()
        self._voice_build_token = None
        self._voice_built = None
        self._voice_init_thread = None
        # A VO fallback hands its replacement player to Tk through this slot, for
        # the same reason: a close that starts meanwhile must be able to take and
        # terminate it (a dropped Tk callback would orphan a live mpv).
        self._fallback_lock = threading.Lock()
        self._fallback_ready = None
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
        self._mpv_quiet_seen: set[str] = set()  # harmless notice kinds already shown
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
        # A persisted heavy Ollama model gets its proactive hint at startup too.
        # Only after _build_ui: the hint's banner writes to the log panel, which
        # does not exist yet in the middle of _build_ui.
        self._refresh_live_heavy_model_hint()
        # Models applied in the 'Models for this PC' window survive a restart.
        self._models_dialog = None
        self._models_choice_restored = False
        self.after(1000, self._restore_model_choices)
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
        self._install_log_hooks()

        # Windows: a failed load of an optional native DLL (libmpv and its
        # dependencies) must raise an exception, never a modal hard-error box.
        # Mask it once for the whole GUI process; no-op off Windows.
        from videotranslator import libmpv_runtime as _libmpv_runtime
        _libmpv_runtime.mask_hard_error_dialogs()

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

    def _install_log_hooks(self) -> None:
        """Route every print, click, choice and error to the Log panel and file."""
        global _DEFAULT_REDIRECT
        if self._log_hooks_installed:
            return
        self._log_hooks_installed = True
        self._own_default_redirect = _TkStreamRedirect(self, self._log_write)
        _DEFAULT_REDIRECT = self._own_default_redirect
        self._saved_thread_excepthook = threading.excepthook
        threading.excepthook = self._log_thread_exception
        self._lib_log_handler = _LogPanelHandler(self)
        logging.getLogger().addHandler(self._lib_log_handler)
        # The log line goes BEFORE Tk's own class binding, which runs the
        # command: the click then precedes its result in the log.
        for cls in ("Button", "Checkbutton", "Radiobutton"):
            for sequence, handler in (("<ButtonRelease-1>", self._log_widget_click),
                                      ("<Key-space>", self._log_widget_key)):
                original = self.bind_class(cls, sequence)
                self.bind_class(cls, sequence, handler)
                if original:
                    self.tk.call("bind", cls, sequence, "+" + original)
        self.bind_class("TCombobox", "<<ComboboxSelected>>", self._log_combo_choice, add="+")
        self.bind_class("TScale", "<ButtonRelease-1>", self._log_scale_choice, add="+")
        self._log_session_header()

    def _remove_log_hooks(self) -> None:
        global _DEFAULT_REDIRECT
        if not self._log_hooks_installed:
            return
        self._log_hooks_installed = False
        # Clear the process-wide global only if it still points at THIS app's
        # redirect. The global is shared across every App in the process, so a
        # newer app may have installed its own since: tearing down an older app
        # (or one closing late from a worker) must not silence a live one, which
        # would drop its print() output. Same identity guard as the excepthook.
        if _DEFAULT_REDIRECT is getattr(self, "_own_default_redirect", None):
            _DEFAULT_REDIRECT = None
        if threading.excepthook == self._log_thread_exception:
            threading.excepthook = self._saved_thread_excepthook
        with contextlib.suppress(Exception):
            logging.getLogger().removeHandler(self._lib_log_handler)

    def destroy(self):
        self._remove_log_hooks()
        with contextlib.suppress(Exception):
            self._log_file.close()
        super().destroy()

    def report_callback_exception(self, exc, val, tb):
        """An error inside a Tk callback: log it with its traceback instead of stderr."""
        with contextlib.suppress(Exception):
            where = "Tk"
            frame = tb
            while frame is not None:                 # the innermost frame names the callback
                where = frame.tb_frame.f_code.co_name
                frame = frame.tb_next
            self._log_event("log_error", where=where, error=f"{exc.__name__}: {val}")
            self._log_write("".join(traceback.format_exception(exc, val, tb)))

    def _run_gui_preflight(self):
        if self._preflight_running:
            return
        self._preflight_running = True
        if self._log_file.ok:
            self._log_event("log_file", days=_app_log.KEEP_DAYS, path=self._log_file.path)
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
        # Never wait here: the preview worker may be in a network read. It stops
        # its player as soon as it sees the close request.
        with contextlib.suppress(Exception):
            self._voice_preview_hub.close(0.0)
        # A live bar change made just before closing is still waiting for its
        # debounced save: write it now instead of losing it.
        if getattr(self, "_live_save_after", None) is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._live_save_after)
            self._save_live_choices()
        # Signal a live session to stop now (fast, non-blocking); the actual join
        # happens on the close worker below, before the backend is terminated, so
        # the Tk thread never blocks (up to 4 s) on a network read in PyAV.
        live = self._live_session
        if live is not None:
            self._live_session = None
            with contextlib.suppress(Exception):
                live.request_stop()
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
        # The adopted voice backend, plus one built but not adopted yet; clearing
        # the build token also makes a build still running terminate its result.
        voice_backends = [v for v in (self._voice_backend, self._take_voice_build())
                          if v is not None]
        self._voice_backend = None
        voice_init = self._voice_init_thread
        # A VO fallback replacement built but not adopted yet (its Tk callback is
        # dropped once closing): take it so it is terminated before the guard.
        fallback = self._take_fallback_ready()
        guard = self._player_guard
        init_thread = self._player_init_thread
        if (backend is None and not voice_backends and live is None
                and fallback is None
                and (init_thread is None or not init_thread.is_alive())
                and (voice_init is None or not voice_init.is_alive())):
            self._player_bridge.close()
            if guard is not None:
                guard.restore()
            self._close_done.set()
            self._finish_close()
            return

        def work():
            try:
                # Join the live session first: its sched thread writes to
                # backend.rt (and clears the overlay), so it must be gone before
                # the backend is terminated.
                if live is not None:
                    with contextlib.suppress(Exception):
                        live.join(4.0)
                if voice_init is not None and voice_init.is_alive():
                    voice_init.join(6.0)         # it terminates its own late result
                self._player_bridge.close()
                for voice_backend in voice_backends:
                    with contextlib.suppress(Exception):
                        voice_backend.terminate(3.0)
                if backend is not None:
                    backend.terminate(3.0)
                if fallback is not None:
                    with contextlib.suppress(Exception):
                        fallback[1].close()
                        fallback[0].terminate(3.0)
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
    # Before any window: a Python the pinned torch cannot run on hands over to
    # the supported interpreter found on this PC (one start, not two).
    _system_packages.relaunch_on_unsupported_python(
        [str(Path(__file__).resolve()), *sys.argv[1:]])
    if len(sys.argv) > 1:
        _cli()
    else:
        # Before the Tk root: Tk only sees fonts registered before it starts.
        from videotranslator.ui_fonts import register_bundled_fonts
        register_bundled_fonts()
        App().mainloop()
