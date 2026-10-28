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
from videotranslator.ui_strings import (  # noqa: E402,F401
    UI_STRINGS,
    UI_LANG_OPTIONS,
    UI_LANG_CODES,
)

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
        from videotranslator import libmpv_runtime as _libmpv_runtime  # noqa: F811
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
