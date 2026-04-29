#!/usr/bin/env python3
"""
Video Translator AI — single-file edition
Pipeline: faster-Whisper (GPU) + Demucs + Google Translate + Edge-TTS
Run with arguments for CLI mode, without for GUI mode.
"""

# ═══════════════════════════════════════════════════════════
#  IMPORTS
# ═══════════════════════════════════════════════════════════

import argparse
import asyncio
import contextlib
import importlib.util
import io
import json
import locale
import traceback
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
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

# Languages supported NATIVAMENTE da CosyVoice (zero-shot / SFT). Per qualsiasi
# altra lingua usiamo la modalità cross-lingual (passa il prompt scritto + reference
# audio nella lingua sorgente — il modello lo doppia mantenendo timbro). IT NON è
# nativa nei pesi 1.x; in 2.x è migliorata ma rimane prudente passare per cross-lingual.
# Riferimento: https://github.com/FunAudioLLM/CosyVoice (Supported languages section).
COSYVOICE_NATIVE_LANGS = {"zh-CN", "en", "ja", "ko"}

# Mapping lingua target → token CosyVoice per modalità cross-lingual. La forma
# attesa dall'API è "<|lang|>" (es. "<|it|>"), embedded come prefix nel prompt.
# Le lingue NON in questa mappa fallback a "<|en|>" (più rappresentate nel training).
COSYVOICE_LANG_TAGS = {
    "it": "<|it|>", "en": "<|en|>", "es": "<|es|>", "fr": "<|fr|>",
    "de": "<|de|>", "ja": "<|ja|>", "ko": "<|ko|>", "zh-CN": "<|zh|>",
    "pt": "<|pt|>", "ru": "<|ru|>", "ar": "<|ar|>", "nl": "<|nl|>",
    "pl": "<|pl|>", "tr": "<|tr|>", "hi": "<|hi|>", "vi": "<|vi|>",
    "id": "<|id|>", "th": "<|th|>",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
DEFAULT_LANG = "it"

# Expansion ratio rispetto all'inglese (≈1.0). Valori >1 = la lingua usa più
# caratteri/sillabe/secondi di EN per esprimere lo stesso contenuto; <1 il
# contrario. Fonti: corpora multilingual (UN Parallel, TED, Europarl, OPUS),
# approssimazioni usate per autotune XTTS speed su coppie asimmetriche.
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
    """Autotune dello speed XTTS v2 in funzione dell'asimmetria fra lingue.

    Ritorna (speed, ratio, auto) dove:
    - speed: valore da passare a `generate_tts_xtts`, nel range [1.10, 1.40];
    - ratio: expansion del target rispetto alla source (target/source);
    - auto: True se il valore è stato calcolato, False se è un override utente.

    Se `user_override` è fornito (da CLI --xtts-speed o config JSON con chiave
    esplicita), viene rispettato senza modifiche — ci fidiamo che l'utente sappia
    cosa sta facendo. Con `user_override=None` l'euristica sceglie uno speed più
    alto quando il target è significativamente più lungo del source (caso EN→IT,
    EN→FR…) per dare a XTTS più margine e ridurre l'atempo post-processing.
    Source "auto" o sconosciuta viene trattata come EN (ratio base 1.0).
    """
    def _norm(code: str) -> str:
        c = (code or "").strip()
        if not c or c.lower() == "auto":
            return "en"
        # cinese: mappa tutte le varianti su "zh" della tabella
        if c.lower().startswith("zh"):
            # Accetta sia "zh" sia "zh-CN" (entrambi in tabella)
            return c if c in LANG_EXPANSION else "zh"
        return c

    src = _norm(lang_source)
    tgt = _norm(lang_target)
    src_exp = LANG_EXPANSION.get(src, 1.0)
    tgt_exp = LANG_EXPANSION.get(tgt, 1.0)
    # Guard: se una delle due è 0 (non dovrebbe succedere) evita div/0
    ratio = (tgt_exp / src_exp) if src_exp > 0 else 1.0

    if user_override is not None:
        # Rispetta sempre la scelta esplicita, ma restituisci comunque il ratio
        # per log/debug del chiamante.
        return float(user_override), ratio, False

    if ratio >= 1.20:
        speed = 1.35   # target molto più lungo (es. EN→IT, EN→FR)
    elif ratio >= 1.10:
        speed = 1.30   # target moderatamente più lungo
    elif ratio <= 0.75:
        # target decisamente più corto (es. EN→ZH 0.70). Soglia 0.75 (non 0.90
        # come prima stesura) per NON toccare IT→EN (ratio 0.80) che il tuning
        # empirico v1.4 ha già fissato a 1.25. Con 0.90 avremmo retrocesso IT→EN
        # a 1.15, violando il vincolo "non rompere nulla che funziona".
        speed = 1.15
    else:
        speed = 1.25   # caso simmetrico / quasi (es. IT→EN 0.80, IT→ES, EN→JA 0.85)

    # Cap di sicurezza nel range utile (sotto 1.10 XTTS suona lento, sopra 1.40
    # inizia a perdere prosodia anche nativamente).
    speed = max(1.10, min(speed, 1.40))
    return speed, ratio, True


# Chars/sec baseline per XTTS v2 a speed=1.0 (stima empirica aggregata su
# segmenti reali v1.4-v1.6). Serve per calcolare il tempo che XTTS impiegherebbe
# a pronunciare un testo senza time-stretch e decidere quanto speed nativo serve
# per farlo stare in uno slot temporale. Lingue sillabiche/logografiche (ja/zh)
# hanno chars/sec molto più bassi perché 1 carattere = 1 sillaba o concetto.
_XTTS_CHARS_PER_SEC = {
    "en": 16.0, "it": 15.0, "es": 15.5, "fr": 15.0, "de": 14.5,
    "pt": 15.0, "nl": 15.0, "ja": 10.0, "zh-CN": 8.0, "zh": 8.0, "ko": 10.5,
    "ru": 13.5, "ar": 13.0, "hi": 13.0, "tr": 14.0, "pl": 13.5,
    "uk": 13.5, "cs": 14.0, "el": 13.0, "hu": 13.0, "fi": 13.5,
    "sv": 14.5, "da": 14.5, "no": 14.5, "ro": 14.5, "vi": 13.0,
    "id": 14.0,
}


def _estimate_tts_duration_s(text: str, lang: str) -> float:
    """Stima durata (secondi) che XTTS impiegherebbe a pronunciare `text` in
    `lang` a speed=1.0. Usa la tabella `_XTTS_CHARS_PER_SEC`; fallback a 14.0
    chars/sec (media europea) per lingue fuori tabella. Minimo 0.5s per evitare
    divisioni degeneri su testi molto corti.

    Il lookup è **case-insensitive** perché la chiamante passa il codice nella
    forma attesa da XTTS (`zh-cn` lowercase) mentre la tabella usa `zh-CN` con
    variante breve `zh`. Senza normalizzazione il cinese cadrebbe al default
    14.0 (media europea) sottostimando la durata di ~1.75x e annullando
    l'adaptive speed proprio sulla lingua con gap chars/sec più estremo.
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
    """Calcola lo speed XTTS v2 adattivo per un singolo segmento.

    Idea: se il testo ci sta già comodo nello slot a speed=1.0 lascia lo speed
    basso (meno artefatti), se invece richiederebbe >40% di compressione alza
    fino al `ceiling` per ridurre l'atempo post-processing che è l'origine
    principale del suono "metallico".

    Parametri:
      text        : testo target da sintetizzare (può essere vuoto)
      slot_s      : durata dello slot sorgente in secondi
      lang_target : codice lingua per lookup in `_XTTS_CHARS_PER_SEC`
      ceiling     : tetto superiore (tipicamente lo speed globale autotune)

    Ritorno: speed nel range [1.05, min(1.40, ceiling)]. Guard su slot_s<=0.
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
from videotranslator.audio_stretch import (  # noqa: E402
    build_rubberband_command as _build_rubberband_command,
    select_stretch_engine as _select_stretch_engine,
)


REQUIRED_PACKAGES = {
    "faster_whisper": "faster-whisper",
    "edge_tts":       "edge-tts",
    "deep_translator": "deep-translator",
    "pydub":          "pydub",
    "demucs":         "demucs",
    "yt_dlp":         "yt-dlp",
    "torchcodec":     "torchcodec",
    # `requests` è usato da DeepL e dal nuovo engine Ollama (v2.0). È già
    # dipendenza transitiva di deep-translator, ma lo dichiariamo esplicito
    # così check_dependencies lo segnala immediatamente in caso di install
    # rotto.
    "requests":       "requests",
}
if sys.version_info >= (3, 13):
    REQUIRED_PACKAGES["audioop"] = "audioop-lts"

# Pacchetti opzionali: migliorano la qualità ma non bloccano l'avvio.
# chiave = modulo Python, valore = (lista pip requirements, descrizione UI)
# Fork mantenuto (Idiap): pure-Python wheel universale per Py ≥3.10, evita il
# setup.py rotto del pacchetto originale `TTS` su Windows. Pin transformers<5.1
# (5.x rimuove isin_mps_friendly; 5.1 rompe coqui-tts — issue #558).
_TTS_PKGS = ["coqui-tts", "transformers<5.1"]
OPTIONAL_PACKAGES: dict[str, tuple[list[str], str]] = {
    "sacremoses":    (["sacremoses"],    "MarianMT tokenizer (traduzione offline)"),
    "sentencepiece": (["sentencepiece"], "MarianMT tokenizer (traduzione offline)"),
    "TTS":           (_TTS_PKGS,         "XTTS v2 (sintesi vocale alta qualità, ~2 GB)"),
    # chiave "pyannote" (namespace parent) invece di "pyannote.audio": find_spec
    # su un dotted-name solleva ModuleNotFoundError se il parent non è installato
    # invece di ritornare None, rompendo _check_optional_deps. Il namespace parent
    # esiste solo se pyannote.audio è installato.
    # Upper bound <4.0 allineato a install_windows.bat: pyannote 4.x richiede
    # torch>=2.8 (CUDA 13), incompatibile con il pin torch 2.6 del progetto
    # (testato: senza upper bound, pip installa 4.x e rompe l'ambiente CUDA).
    "pyannote":      (["pyannote.audio>=3.1,<4.0"], "Diarization multi-speaker (pyannote, richiede HF token gratuito)"),
    "silero_vad":    (["silero-vad"],    "VAD per reference XTTS (selezione speech continuo)"),
    "keyring":       (["keyring"],       "Storage sicuro HF token (Credential Manager / Keychain / Secret Service)"),
    # CosyVoice (v2.3): NON nel set obbligatorio. Auto-detect on-demand quando
    # l'utente sceglie il radio "Voice Cloning Pro". Il pacchetto PyPI `cosyvoice`
    # è il wrapper community (Lucas Jin) attualmente disponibile; il modello
    # vero (CosyVoice-300M-Instruct, ~1.7 GB) viene scaricato al primo uso via
    # ModelScope. CosyVoice 2.0 ufficiale (FunAudioLLM) non ha ancora una
    # release PyPI: quando arriverà, basta cambiare il pin qui sotto.
    # Nota: NON includiamo questo nel popup "install all optional" perché
    # la dipendenza è grossa (modelscope, onnxruntime-gpu, hyperpyyaml…) e
    # vogliamo che l'utente la richieda esplicitamente.
}
# Alias per moduli che possono avere nomi diversi a seconda della versione installata
_OPTIONAL_ALIASES: dict[str, list[str]] = {
    "TTS": ["TTS", "coqui_tts"],
}

# ── GUI colours ──────────────────────────────────────────────
BG  = "#1e1e2e"
FG  = "#cdd6f4"
FG2 = "#6c7086"
ACC = "#89b4fa"
SEL = "#313244"
RED = "#f38ba8"
GRN = "#a6e3a1"

# ── UI translation strings ───────────────────────────────────
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
        "opt_xtts":           "🎙 Voice Cloning (Coqui XTTS v2 — prima esecuzione: download ~1.8GB)",
        "opt_cosyvoice":      "🎤 Voice Cloning Pro (CosyVoice 2.0 — sperimentale, setup manuale)",
        "opt_lipsync":        "💋 Lip Sync (Wav2Lip — prima esecuzione: download ~416MB)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 non installato.\n\n"
            "Installare automaticamente?\n"
            "  - Pacchetto Python: ~500 MB\n"
            "  - Modello (al primo Avvia): ~1.7 GB\n\n"
            "CosyVoice ha tasso di hallucination <2% (vs XTTS 5-15%) "
            "su long-form, quindi outlier audio molto rari."
        ),
        "msg_cosyvoice_installing": "[*] Installazione CosyVoice 2.0 in corso (~500 MB pip + 1.7 GB modello al primo Avvia)...",
        "hint_cosyvoice":     "Modello: CosyVoice2-0.5B (Instruct) — IT via cross-lingual con prefix <|it|>",
        "label_engine":       "Motore traduzione:",
        "engine_google":      "Google (default)",
        "engine_deepl":       "DeepL Free",
        "engine_marian":      "MarianMT (locale)",
        "engine_ollama":      "LLM Ollama (locale, consigliato — traduzioni concise per doppiaggio)",
        "label_deepl_key":    "API key DeepL:",
        "label_ollama_model": "Modello:",
        "label_ollama_url":   "URL Ollama:",
        "hint_ollama":        (
            "Default: qwen3:8b (raccomandato) — qwen3:4b leggero (~3 GB), "
            "qwen3:14b qualità superiore (~9 GB), qwen2.5:7b-instruct retrocompat. "
            "Richiede Ollama installato"
        ),
        "opt_ollama_thinking":  "🧠 Modalità thinking (più lento, traduzioni migliori)",
        "hint_ollama_thinking": "Delibera passo-passo, ~5x più lento ma riduce errori idiomi e grammatica",
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
        "msg_xtts_no_lang":   "XTTS v2 non supporta '{lang}'. Verrà usato Edge-TTS.",
        "msg_no_video":       "Aggiungi almeno un video.",
        "msg_completed":      "Traduzione completata!",
        "msg_error":          "Qualcosa è andato storto. Controlla il log.",
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
        "editor_seg_label":   "Segmento {} —",
        "editor_btn_save":    "Salva",
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
        "opt_xtts":           "🎙 Voice Cloning (Coqui XTTS v2 — first run: downloads ~1.8GB)",
        "opt_cosyvoice":      "🎤 Voice Cloning Pro (CosyVoice 2.0 — experimental, manual setup)",
        "opt_lipsync":        "💋 Lip Sync (Wav2Lip — first run: downloads ~416MB)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 not installed.\n\n"
            "Install automatically?\n"
            "  - Python package: ~500 MB\n"
            "  - Model (at first Start): ~1.7 GB\n\n"
            "CosyVoice has <2% hallucination rate (vs XTTS 5-15%) on "
            "long-form, so outlier audio is very rare."
        ),
        "msg_cosyvoice_installing": "[*] Installing CosyVoice 2.0 (~500 MB pip + 1.7 GB model at first Start)...",
        "hint_cosyvoice":     "Model: CosyVoice2-0.5B (Instruct) — IT via cross-lingual with <|it|> prefix",
        "label_engine":       "Translation engine:",
        "engine_google":      "Google (default)",
        "engine_deepl":       "DeepL Free",
        "engine_marian":      "MarianMT (local)",
        "engine_ollama":      "LLM Ollama (local, recommended — concise translations for dubbing)",
        "label_deepl_key":    "DeepL API key:",
        "label_ollama_model": "Model:",
        "label_ollama_url":   "Ollama URL:",
        "hint_ollama":        (
            "Default: qwen3:8b (recommended) — qwen3:4b lightweight (~3 GB), "
            "qwen3:14b higher quality (~9 GB), qwen2.5:7b-instruct legacy. "
            "Requires Ollama installed"
        ),
        "opt_ollama_thinking":  "🧠 Thinking mode (slower, better translations)",
        "hint_ollama_thinking": "Deliberates step-by-step, ~5x slower but reduces idiom/grammar errors",
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
        "msg_xtts_no_lang":   "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video":       "Add at least one video.",
        "msg_completed":      "Translation completed!",
        "msg_error":          "Something went wrong. Check the log.",
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
        "editor_seg_label":   "Segment {} —",
        "editor_btn_save":    "Save",
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
    },
    "ar": {
        "label_video": "فيديو:",
        "label_output": "الإخراج:",
        "label_model": "نموذج:",
        "label_from": "من:",
        "label_to": "ل:",
        "label_voice": "صوت:",
        "label_tts_rate": "سرعة تحويل النص إلى كلام:",
        "label_options": "خيارات:",
        "label_model_hint": "← سريع / دقيق →",
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
        "opt_xtts": "استنساخ الصوت (Coqui XTTS v2 — التشغيل الأول: التنزيلات ~1.8 جيجابايت)",
        "opt_lipsync": "مزامنة الشفاه (Wav2Lip — التشغيل الأول: التنزيل ~416MB)",
        "label_engine": "محرك الترجمة:",
        "engine_google": "Google (افتراضي)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (محلي)",
        "label_deepl_key": "مفتاح API لـ DeepL:",
        "opt_diarization": "تمييز المتحدثين (pyannote)",
        "label_hf_token": "رمز HF:",
        "hint_hf_token": "رمز HF مجاني: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "أضف مقطع فيديو واحدًا على الأقل.",
        "msg_completed": "اكتملت الترجمة!",
        "msg_error": "حدث خطأ ما. تحقق من السجل.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "يحفظ",
        "warn_editor": "محرر",
        "label_url": "URL:",
        "btn_download": "⬇ تنزيل وترجمة",
        "url_placeholder": "الصق رابط YouTube (أو أي موقع آخر يدعم yt-dlp)...",
        "msg_no_url": "الصق عنوان URL صالحًا واحدًا على الأقل.",
        "msg_downloading": "⏳ جاري التحميل...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (محلي، موصى به — ترجمات موجزة للدبلجة)",
        "label_ollama_model": "النموذج:",
        "label_ollama_url": "عنوان Ollama:",
        "hint_ollama": "افتراضي: qwen3:8b (موصى به) — qwen3:4b خفيف (~3 جيجابايت)، qwen3:14b جودة أعلى (~9 جيجابايت)، qwen2.5:7b-instruct قديم. يتطلب تثبيت Ollama",
        "opt_ollama_thinking":  "🧠 وضع التفكير (أبطأ، ترجمات أفضل)",
        "hint_ollama_thinking": "يتداول خطوة بخطوة، ~5x أبطأ ولكن يقلل من أخطاء التعابير والقواعد",
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
        "opt_cosyvoice": "🎤 استنساخ صوت احترافي (CosyVoice 2.0 — تجريبي، إعداد يدوي)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 غير مثبت.\n"
            "\n"
            "هل تريد التثبيت تلقائيًا؟\n"
            "  - حزمة Python: ~500 ميجابايت\n"
            "  - النموذج (عند أول بدء): ~1.7 جيجابايت\n"
            "\n"
            "معدل هلوسة CosyVoice أقل من 2% (مقابل 5-15% لـ XTTS) في المحتوى الطويل، لذا فإن المخرجات الصوتية الشاذة نادرة جدًا."
        ),
        "msg_cosyvoice_installing": "[*] جاري تثبيت CosyVoice 2.0 (~500 ميجابايت pip + 1.7 جيجابايت نموذج عند أول بدء)...",
        "hint_cosyvoice": "النموذج: CosyVoice2-0.5B (Instruct) — IT عبر متعدد اللغات مع البادئة <|it|>",
        "label_log_panel": "السجل:",
        "btn_log_show": "▼ إظهار السجل",
        "btn_log_hide": "▲ إخفاء السجل",
        "btn_log_copy": "نسخ",
        "btn_log_save": "حفظ...",
        "btn_log_clear": "مسح",
    },
    "zh": {
        "label_video": "视频：",
        "label_output": "输出：",
        "label_model": "模型：",
        "label_from": "从：",
        "label_to": "到：",
        "label_voice": "嗓音：",
        "label_tts_rate": "TTS 速度：",
        "label_options": "选项：",
        "label_model_hint": "← 快速/准确 →",
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
        "opt_xtts": "语音克隆（Coqui XTTS v2 — 首次运行：下载量约 1.8GB）",
        "opt_lipsync": "唇形同步 (Wav2Lip — 首次运行：下载约 416MB)",
        "label_engine": "翻译引擎：",
        "engine_google": "Google（默认）",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT（本地）",
        "label_deepl_key": "DeepL API 密钥：",
        "opt_diarization": "多说话人分离 (pyannote)",
        "label_hf_token": "HF 令牌：",
        "hint_hf_token": "免费 HF 令牌：huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "添加至少一个视频。",
        "msg_completed": "翻译完成！",
        "msg_error": "出了点问题。检查日志。",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "节省",
        "warn_editor": "编辑",
        "label_url": "URL:",
        "btn_download": "⬇ 下载和翻译",
        "url_placeholder": "粘贴 YouTube 链接（或其他 yt-dlp 支持的网站）...",
        "msg_no_url": "粘贴至少一个有效的 URL。",
        "msg_downloading": "⏳ 正在下载...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM(本地,推荐 — 简洁的配音翻译)",
        "label_ollama_model": "模型:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "默认: qwen3:8b(推荐) — qwen3:4b 轻量级(~3 GB), qwen3:14b 更高质量(~9 GB), qwen2.5:7b-instruct 旧版本。需要安装 Ollama",
        "opt_ollama_thinking":  "🧠 思考模式 (更慢，翻译更好)",
        "hint_ollama_thinking": "逐步推敲，慢约5倍，但能减少习语和语法错误",
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
        "opt_cosyvoice": "🎤 专业语音克隆(CosyVoice 2.0 — 实验性,手动设置)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 未安装。\n"
            "\n"
            "是否自动安装?\n"
            "  - Python 包: ~500 MB\n"
            "  - 模型(首次启动时): ~1.7 GB\n"
            "\n"
            "CosyVoice 在长篇内容中的幻觉率低于 2%(对比 XTTS 的 5-15%),因此异常音频极为罕见。"
        ),
        "msg_cosyvoice_installing": "[*] 正在安装 CosyVoice 2.0(~500 MB pip + 首次启动时 1.7 GB 模型)...",
        "hint_cosyvoice": "模型: CosyVoice2-0.5B (Instruct) — IT 通过跨语言带 <|it|> 前缀",
        "label_log_panel": "日志:",
        "btn_log_show": "▼ 显示日志",
        "btn_log_hide": "▲ 隐藏日志",
        "btn_log_copy": "复制",
        "btn_log_save": "保存...",
        "btn_log_clear": "清除",
    },
    "cs": {
        "label_video": "Video:",
        "label_output": "výstup:",
        "label_model": "Model:",
        "label_from": "Z:",
        "label_to": "Na:",
        "label_voice": "Hlas:",
        "label_tts_rate": "Rychlost TTS:",
        "label_options": "Možnosti:",
        "label_model_hint": "← rychlé / přesné →",
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
        "opt_xtts": "Hlasové klonování (Coqui XTTS v2 – první spuštění: stažení ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip — první spuštění: stažení ~416MB)",
        "label_engine": "Překladač:",
        "engine_google": "Google (výchozí)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokální)",
        "label_deepl_key": "API klíč DeepL:",
        "opt_diarization": "Rozpoznávání mluvčích (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Bezplatný HF token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Přidejte alespoň jedno video.",
        "msg_completed": "Překlad dokončen!",
        "msg_error": "Něco se pokazilo. Zkontrolujte protokol.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Uložit",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Stáhnout a přeložit",
        "url_placeholder": "Vložte odkaz na YouTube (nebo jiný web podporovaný yt-dlp)...",
        "msg_no_url": "Vložte alespoň jednu platnou adresu URL.",
        "msg_downloading": "⏳ Stahování...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokální, doporučeno — stručné překlady pro dabing)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Výchozí: qwen3:8b (doporučeno) — qwen3:4b odlehčený (~3 GB), qwen3:14b vyšší kvalita (~9 GB), qwen2.5:7b-instruct starší. Vyžaduje nainstalovaný Ollama",
        "opt_ollama_thinking":  "🧠 Režim přemýšlení (pomalejší, lepší překlady)",
        "hint_ollama_thinking": "Zvažuje krok za krokem, ~5x pomalejší, ale snižuje chyby v idiomech a gramatice",
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
        "opt_cosyvoice": "🎤 Pro klonování hlasu (CosyVoice 2.0 — experimentální, ruční instalace)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 není nainstalován.\n"
            "\n"
            "Nainstalovat automaticky?\n"
            "  - Python balíček: ~500 MB\n"
            "  - Model (při prvním Start): ~1,7 GB\n"
            "\n"
            "CosyVoice má míru halucinací <2 % (oproti XTTS 5-15 %) u dlouhých nahrávek, takže odlehlé výstupy jsou velmi vzácné."
        ),
        "msg_cosyvoice_installing": "[*] Instalace CosyVoice 2.0 probíhá (~500 MB pip + 1,7 GB model při prvním Start)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT přes cross-lingual s prefixem <|it|>",
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Zobrazit log",
        "btn_log_hide": "▲ Skrýt log",
        "btn_log_copy": "Kopírovat",
        "btn_log_save": "Uložit...",
        "btn_log_clear": "Vymazat",
    },
    "da": {
        "label_video": "Video:",
        "label_output": "Produktion:",
        "label_model": "Model:",
        "label_from": "Fra:",
        "label_to": "Til:",
        "label_voice": "Stemme:",
        "label_tts_rate": "TTS hastighed:",
        "label_options": "Valgmuligheder:",
        "label_model_hint": "← hurtig / præcis →",
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
        "opt_xtts": "Stemmekloning (Coqui XTTS v2 — første kørsel: downloads ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip — første kørsel: download ~416MB)",
        "label_engine": "Oversættelsesmotor:",
        "engine_google": "Google (standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-nøgle:",
        "opt_diarization": "Højttalerseparation (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Gratis HF token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Tilføj mindst én video.",
        "msg_completed": "Oversættelse afsluttet!",
        "msg_error": "Noget gik galt. Tjek loggen.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Spare",
        "warn_editor": "Redaktør",
        "label_url": "URL:",
        "btn_download": "⬇ Download og oversæt",
        "url_placeholder": "Indsæt YouTube-link (eller et andet yt-dlp-understøttet websted)...",
        "msg_no_url": "Indsæt mindst én gyldig webadresse.",
        "msg_downloading": "⏳ Downloader...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, anbefalet — koncise oversættelser til dubbing)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Standard: qwen3:8b (anbefalet) — qwen3:4b let (~3 GB), qwen3:14b højere kvalitet (~9 GB), qwen2.5:7b-instruct ældre. Kræver Ollama installeret",
        "opt_ollama_thinking":  "🧠 Tænketilstand (langsommere, bedre oversættelser)",
        "hint_ollama_thinking": "Overvejer trin for trin, ~5x langsommere, men reducerer idiom-/grammatikfejl",
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
        "opt_cosyvoice": "🎤 Pro stemmekloning (CosyVoice 2.0 — eksperimentel, manuel opsætning)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 ikke installeret.\n"
            "\n"
            "Installer automatisk?\n"
            "  - Python-pakke: ~500 MB\n"
            "  - Model (ved første Start): ~1,7 GB\n"
            "\n"
            "CosyVoice har en hallucinationsrate på <2 % (mod XTTS 5-15 %) ved lange optagelser, så afvigende lyd er meget sjældent."
        ),
        "msg_cosyvoice_installing": "[*] Installerer CosyVoice 2.0 (~500 MB pip + 1,7 GB model ved første Start)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT via cross-lingual med <|it|>-præfiks",
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Vis log",
        "btn_log_hide": "▲ Skjul log",
        "btn_log_copy": "Kopier",
        "btn_log_save": "Gem...",
        "btn_log_clear": "Ryd",
    },
    "nl": {
        "label_video": "Video:",
        "label_output": "Uitgang:",
        "label_model": "Model:",
        "label_from": "Van:",
        "label_to": "Naar:",
        "label_voice": "Stem:",
        "label_tts_rate": "TTS-snelheid:",
        "label_options": "Opties:",
        "label_model_hint": "← snel / nauwkeurig →",
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
        "opt_xtts": "Spraakklonen (Coqui XTTS v2 – eerste keer: downloads ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip — eerste keer: download ~416MB)",
        "label_engine": "Vertaalengine:",
        "engine_google": "Google (standaard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokaal)",
        "label_deepl_key": "DeepL API-sleutel:",
        "opt_diarization": "Sprekerdiarisatie (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Gratis HF token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Voeg ten minste één video toe.",
        "msg_completed": "Vertaling voltooid!",
        "msg_error": "Er is iets misgegaan. Controleer het logboek.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Redden",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Downloaden en vertalen",
        "url_placeholder": "Plak de YouTube-link (of een andere door yt-dlp ondersteunde site)...",
        "msg_no_url": "Plak minimaal één geldige URL.",
        "msg_downloading": "⏳ Downloaden...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokaal, aanbevolen — beknopte vertalingen voor nasynchronisatie)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "Ollama-URL:",
        "hint_ollama": "Standaard: qwen3:8b (aanbevolen) — qwen3:4b licht (~3 GB), qwen3:14b hogere kwaliteit (~9 GB), qwen2.5:7b-instruct legacy. Vereist Ollama geïnstalleerd",
        "opt_ollama_thinking":  "🧠 Denkmodus (langzamer, betere vertalingen)",
        "hint_ollama_thinking": "Overweegt stap voor stap, ~5x langzamer maar minder idioom- en grammaticafouten",
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
        "opt_cosyvoice": "🎤 Pro voice cloning (CosyVoice 2.0 — experimenteel, handmatige setup)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 niet geïnstalleerd.\n"
            "\n"
            "Automatisch installeren?\n"
            "  - Python-pakket: ~500 MB\n"
            "  - Model (bij eerste Start): ~1,7 GB\n"
            "\n"
            "CosyVoice heeft <2% hallucinatiepercentage (vs XTTS 5-15%) bij lange opnames, dus uitschieters zijn zeer zeldzaam."
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 wordt geïnstalleerd (~500 MB pip + 1,7 GB model bij eerste Start)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT via cross-lingual met prefix <|it|>",
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Log tonen",
        "btn_log_hide": "▲ Log verbergen",
        "btn_log_copy": "Kopiëren",
        "btn_log_save": "Opslaan...",
        "btn_log_clear": "Wissen",
    },
    "fi": {
        "label_video": "Video:",
        "label_output": "Lähtö:",
        "label_model": "Malli:",
        "label_from": "Lähettäjä:",
        "label_to": "Vastaanottaja:",
        "label_voice": "Ääni:",
        "label_tts_rate": "TTS nopeus:",
        "label_options": "Vaihtoehdot:",
        "label_model_hint": "← nopea / tarkka →",
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
        "opt_xtts": "Äänen kloonaus (Coqui XTTS v2 – ensimmäinen käyttökerta: lataukset ~1,8 Gt)",
        "opt_lipsync": "Huulisynkka (Wav2Lip — ensimmäinen ajo: lataa ~416MB)",
        "label_engine": "Käännöskone:",
        "engine_google": "Google (oletus)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (paikallinen)",
        "label_deepl_key": "DeepL API-avain:",
        "opt_diarization": "Puhujan tunnistus (pyannote)",
        "label_hf_token": "HF-tunnus:",
        "hint_hf_token": "Ilmainen HF-tunnus: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Lisää vähintään yksi video.",
        "msg_completed": "Käännös valmis!",
        "msg_error": "Jotain meni pieleen. Tarkista loki.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Tallentaa",
        "warn_editor": "Toimittaja",
        "label_url": "URL:",
        "btn_download": "⬇ Lataa ja käännä",
        "url_placeholder": "Liitä YouTube-linkki (tai muu yt-dlp-tuettu sivusto)...",
        "msg_no_url": "Liitä vähintään yksi kelvollinen URL-osoite.",
        "msg_downloading": "⏳ Ladataan...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (paikallinen, suositeltu — tiiviit käännökset dubbaukseen)",
        "label_ollama_model": "Malli:",
        "label_ollama_url": "Ollaman URL:",
        "hint_ollama": "Oletus: qwen3:8b (suositeltu) — qwen3:4b kevyt (~3 GB), qwen3:14b parempi laatu (~9 GB), qwen2.5:7b-instruct vanha. Vaatii Ollaman asennuksen",
        "opt_ollama_thinking":  "🧠 Ajattelutila (hitaampi, parempia käännöksiä)",
        "hint_ollama_thinking": "Harkitsee vaiheittain, ~5x hitaampi mutta vähentää idiomi- ja kielioppivirheitä",
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
        "opt_cosyvoice": "🎤 Pro-äänikloonaus (CosyVoice 2.0 — kokeellinen, manuaalinen asennus)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 ei ole asennettu.\n"
            "\n"
            "Asennetaanko automaattisesti?\n"
            "  - Python-paketti: ~500 MB\n"
            "  - Malli (ensimmäisellä käynnistyksellä): ~1,7 GB\n"
            "\n"
            "CosyVoicen hallusinaatiosuhde on alle 2 % (vrt. XTTS 5-15 %) pitkissä äänitteissä, joten poikkeavat ääniraidat ovat hyvin harvinaisia."
        ),
        "msg_cosyvoice_installing": "[*] Asennetaan CosyVoice 2.0 (~500 MB pip + 1,7 GB malli ensimmäisellä käynnistyksellä)...",
        "hint_cosyvoice": "Malli: CosyVoice2-0.5B (Instruct) — IT cross-lingual <|it|>-etuliitteellä",
        "label_log_panel": "Loki:",
        "btn_log_show": "▼ Näytä loki",
        "btn_log_hide": "▲ Piilota loki",
        "btn_log_copy": "Kopioi",
        "btn_log_save": "Tallenna...",
        "btn_log_clear": "Tyhjennä",
    },
    "fr": {
        "label_video": "Vidéo:",
        "label_output": "Sortir:",
        "label_model": "Modèle:",
        "label_from": "Depuis:",
        "label_to": "À:",
        "label_voice": "Voix:",
        "label_tts_rate": "Vitesse TTS :",
        "label_options": "Possibilités :",
        "label_model_hint": "← rapide / précis →",
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
        "opt_xtts": "Clonage vocal (Coqui XTTS v2 — première exécution : téléchargements ~ 1,8 Go)",
        "opt_lipsync": "Synchronisation labiale (Wav2Lip — première exécution : téléchargement ~416 Mo)",
        "label_engine": "Moteur de traduction :",
        "engine_google": "Google (par défaut)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Clé API DeepL :",
        "opt_diarization": "Diarisation multi-locuteurs (pyannote)",
        "label_hf_token": "Jeton HF :",
        "hint_hf_token": "Jeton HF gratuit : huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Ajoutez au moins une vidéo.",
        "msg_completed": "Traduction terminée !",
        "msg_error": "Quelque chose s'est mal passé. Vérifiez le journal.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Sauvegarder",
        "warn_editor": "Éditeur",
        "label_url": "URL:",
        "btn_download": "⬇ Télécharger et traduire",
        "url_placeholder": "Collez le lien YouTube (ou tout autre site pris en charge par yt-dlp)...",
        "msg_no_url": "Collez au moins une URL valide.",
        "msg_downloading": "⏳ Téléchargement...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recommandé — traductions concises pour le doublage)",
        "label_ollama_model": "Modèle :",
        "label_ollama_url": "URL Ollama :",
        "hint_ollama": "Par défaut : qwen3:8b (recommandé) — qwen3:4b léger (~3 Go), qwen3:14b qualité supérieure (~9 Go), qwen2.5:7b-instruct hérité. Nécessite Ollama installé",
        "opt_ollama_thinking":  "🧠 Mode réflexif (plus lent, meilleures traductions)",
        "hint_ollama_thinking": "Délibère étape par étape, ~5x plus lent mais réduit les erreurs d'idiomes et de grammaire",
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
        "opt_cosyvoice": "🎤 Voice Cloning Pro (CosyVoice 2.0 — expérimental, installation manuelle)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 non installé.\n"
            "\n"
            "Installer automatiquement ?\n"
            "  - Paquet Python : ~500 Mo\n"
            "  - Modèle (au premier Démarrage) : ~1,7 Go\n"
            "\n"
            "CosyVoice a un taux d'hallucination <2 % (vs XTTS 5-15 %) sur les contenus longs, donc les sorties audio aberrantes sont très rares."
        ),
        "msg_cosyvoice_installing": "[*] Installation de CosyVoice 2.0 en cours (~500 Mo pip + 1,7 Go modèle au premier Démarrage)...",
        "hint_cosyvoice": "Modèle : CosyVoice2-0.5B (Instruct) — IT via cross-lingual avec préfixe <|it|>",
        "label_log_panel": "Journal :",
        "btn_log_show": "▼ Afficher le journal",
        "btn_log_hide": "▲ Masquer le journal",
        "btn_log_copy": "Copier",
        "btn_log_save": "Enregistrer...",
        "btn_log_clear": "Effacer",
    },
    "de": {
        "label_video": "Video:",
        "label_output": "Ausgabe:",
        "label_model": "Modell:",
        "label_from": "Aus:",
        "label_to": "Zu:",
        "label_voice": "Stimme:",
        "label_tts_rate": "TTS-Geschwindigkeit:",
        "label_options": "Optionen:",
        "label_model_hint": "← schnell / genau →",
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
        "opt_xtts": "Voice Cloning (Coqui XTTS v2 – erster Durchlauf: Downloads ~1,8 GB)",
        "opt_lipsync": "Lippensynchronisation (Wav2Lip — Erststart: Download ~416MB)",
        "label_engine": "Übersetzungs-Engine:",
        "engine_google": "Google (Standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-Schlüssel:",
        "opt_diarization": "Sprechertrennung (pyannote)",
        "label_hf_token": "HF-Token:",
        "hint_hf_token": "Kostenloser HF-Token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Fügen Sie mindestens ein Video hinzu.",
        "msg_completed": "Übersetzung abgeschlossen!",
        "msg_error": "Etwas ist schief gelaufen. Überprüfen Sie das Protokoll.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Speichern",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Herunterladen und übersetzen",
        "url_placeholder": "Fügen Sie den YouTube-Link (oder eine andere von YT-DLP unterstützte Website) ein ...",
        "msg_no_url": "Fügen Sie mindestens eine gültige URL ein.",
        "msg_downloading": "⏳ Herunterladen...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, empfohlen — präzise Übersetzungen für Synchronisation)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama-URL:",
        "hint_ollama": "Standard: qwen3:8b (empfohlen) — qwen3:4b leichtgewichtig (~3 GB), qwen3:14b höhere Qualität (~9 GB), qwen2.5:7b-instruct älter. Erfordert installiertes Ollama",
        "opt_ollama_thinking":  "🧠 Denkmodus (langsamer, bessere Übersetzungen)",
        "hint_ollama_thinking": "Überlegt Schritt für Schritt, ~5x langsamer, reduziert aber Idiom- und Grammatikfehler",
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
        "opt_cosyvoice": "🎤 Voice Cloning Pro (CosyVoice 2.0 — experimentell, manuelle Einrichtung)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 nicht installiert.\n"
            "\n"
            "Automatisch installieren?\n"
            "  - Python-Paket: ~500 MB\n"
            "  - Modell (beim ersten Start): ~1,7 GB\n"
            "\n"
            "CosyVoice hat eine Halluzinationsrate <2 % (gegenüber XTTS 5-15 %) bei langen Aufnahmen, sodass Ausreißer im Audio sehr selten sind."
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 wird installiert (~500 MB pip + 1,7 GB Modell beim ersten Start)...",
        "hint_cosyvoice": "Modell: CosyVoice2-0.5B (Instruct) — IT via cross-lingual mit Präfix <|it|>",
        "label_log_panel": "Protokoll:",
        "btn_log_show": "▼ Protokoll anzeigen",
        "btn_log_hide": "▲ Protokoll ausblenden",
        "btn_log_copy": "Kopieren",
        "btn_log_save": "Speichern...",
        "btn_log_clear": "Löschen",
    },
    "el": {
        "label_video": "Βίντεο:",
        "label_output": "Παραγωγή:",
        "label_model": "Μοντέλο:",
        "label_from": "Από:",
        "label_to": "Να:",
        "label_voice": "Φωνή:",
        "label_tts_rate": "Ταχύτητα TTS:",
        "label_options": "Επιλογές:",
        "label_model_hint": "← γρήγορο / ακριβές →",
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
        "opt_xtts": "Κλωνοποίηση φωνής (Coqui XTTS v2 — πρώτη εκτέλεση: λήψεις ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip — πρώτη εκτέλεση: λήψη ~416MB)",
        "label_engine": "Μηχανή μετάφρασης:",
        "engine_google": "Google (προεπιλογή)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (τοπικό)",
        "label_deepl_key": "Κλειδί API DeepL:",
        "opt_diarization": "Διαχωρισμός ομιλητών (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Δωρεάν HF token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Προσθέστε τουλάχιστον ένα βίντεο.",
        "msg_completed": "Η μετάφραση ολοκληρώθηκε!",
        "msg_error": "Κάτι πήγε στραβά. Ελέγξτε το ημερολόγιο.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Εκτός",
        "warn_editor": "Συντάκτης",
        "label_url": "URL:",
        "btn_download": "⬇ Λήψη & Μετάφραση",
        "url_placeholder": "Επικόλληση συνδέσμου YouTube (ή άλλου ιστότοπου που υποστηρίζεται από yt-dlp)...",
        "msg_no_url": "Επικολλήστε τουλάχιστον ένα έγκυρο URL.",
        "msg_downloading": "⏳ Λήψη...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (τοπικό, συνιστώμενο — συνοπτικές μεταφράσεις για μεταγλώττιση)",
        "label_ollama_model": "Μοντέλο:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Προεπιλογή: qwen3:8b (συνιστάται) — qwen3:4b ελαφρύ (~3 GB), qwen3:14b υψηλότερη ποιότητα (~9 GB), qwen2.5:7b-instruct παλιό. Απαιτείται εγκατεστημένο Ollama",
        "opt_ollama_thinking":  "🧠 Λειτουργία σκέψης (πιο αργή, καλύτερες μεταφράσεις)",
        "hint_ollama_thinking": "Συλλογίζεται βήμα-βήμα, ~5x πιο αργή αλλά μειώνει λάθη ιδιωμάτων/γραμματικής",
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
        "opt_cosyvoice": "🎤 Pro κλωνοποίηση φωνής (CosyVoice 2.0 — πειραματικό, χειροκίνητη εγκατάσταση)",
        "msg_cosyvoice_unavailable": (
            "Το CosyVoice 2.0 δεν είναι εγκατεστημένο.\n"
            "\n"
            "Αυτόματη εγκατάσταση;\n"
            "  - Πακέτο Python: ~500 MB\n"
            "  - Μοντέλο (στην πρώτη Εκκίνηση): ~1,7 GB\n"
            "\n"
            "Το CosyVoice έχει ποσοστό παραισθήσεων <2 % (έναντι XTTS 5-15 %) σε μεγάλο περιεχόμενο, οπότε ακραίες ηχητικές εξόδους είναι πολύ σπάνιες."
        ),
        "msg_cosyvoice_installing": "[*] Εγκατάσταση CosyVoice 2.0 σε εξέλιξη (~500 MB pip + 1,7 GB μοντέλο στην πρώτη Εκκίνηση)...",
        "hint_cosyvoice": "Μοντέλο: CosyVoice2-0.5B (Instruct) — IT μέσω cross-lingual με πρόθεμα <|it|>",
        "label_log_panel": "Καταγραφή:",
        "btn_log_show": "▼ Εμφάνιση καταγραφής",
        "btn_log_hide": "▲ Απόκρυψη καταγραφής",
        "btn_log_copy": "Αντιγραφή",
        "btn_log_save": "Αποθήκευση...",
        "btn_log_clear": "Εκκαθάριση",
    },
    "hi": {
        "label_video": "वीडियो:",
        "label_output": "आउटपुट:",
        "label_model": "नमूना:",
        "label_from": "से:",
        "label_to": "को:",
        "label_voice": "आवाज़:",
        "label_tts_rate": "टीटीएस स्पीड:",
        "label_options": "विकल्प:",
        "label_model_hint": "← तेज़/सटीक →",
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
        "opt_lipsync": "लिप सिंक (Wav2Lip — पहली बार: ~416MB डाउनलोड)",
        "label_engine": "अनुवाद इंजन:",
        "engine_google": "Google (डिफ़ॉल्ट)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (लोकल)",
        "label_deepl_key": "DeepL API कुंजी:",
        "opt_diarization": "वक्ता पहचान (pyannote)",
        "label_hf_token": "HF टोकन:",
        "hint_hf_token": "मुफ़्त HF टोकन: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "कम से कम एक वीडियो जोड़ें.",
        "msg_completed": "अनुवाद पूरा हुआ!",
        "msg_error": "कुछ गलत हो गया। लॉग की जाँच करें.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "बचाना",
        "warn_editor": "संपादक",
        "label_url": "URL:",
        "btn_download": "⬇ डाउनलोड करें और अनुवाद करें",
        "url_placeholder": "YouTube लिंक चिपकाएँ (या अन्य yt-dlp समर्थित साइट)...",
        "msg_no_url": "कम से कम एक वैध यूआरएल चिपकाएँ.",
        "msg_downloading": "⏳ डाउनलोड हो रहा है...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (स्थानीय, अनुशंसित — डबिंग के लिए संक्षिप्त अनुवाद)",
        "label_ollama_model": "मॉडल:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "डिफ़ॉल्ट: qwen3:8b (अनुशंसित) — qwen3:4b हल्का (~3 GB), qwen3:14b उच्च गुणवत्ता (~9 GB), qwen2.5:7b-instruct पुराना। Ollama स्थापित होना आवश्यक",
        "opt_ollama_thinking":  "🧠 थिंकिंग मोड (धीमा, बेहतर अनुवाद)",
        "hint_ollama_thinking": "चरण-दर-चरण विचार करता है, ~5x धीमा लेकिन मुहावरे/व्याकरण की गलतियाँ कम करता है",
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
        "opt_cosyvoice": "🎤 प्रो वॉइस क्लोनिंग (CosyVoice 2.0 — प्रायोगिक, मैन्युअल सेटअप)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 स्थापित नहीं है।\n"
            "\n"
            "स्वचालित रूप से स्थापित करें?\n"
            "  - Python पैकेज: ~500 MB\n"
            "  - मॉडल (पहली बार Start पर): ~1.7 GB\n"
            "\n"
            "CosyVoice की हलूसिनेशन दर <2% है (बनाम XTTS 5-15%) लंबी सामग्री पर, इसलिए ऑडियो आउटलेयर बहुत दुर्लभ हैं।"
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 स्थापित किया जा रहा है (~500 MB pip + पहली बार Start पर 1.7 GB मॉडल)...",
        "hint_cosyvoice": "मॉडल: CosyVoice2-0.5B (Instruct) — IT क्रॉस-लिंगुअल के माध्यम से <|it|> उपसर्ग के साथ",
        "label_log_panel": "लॉग:",
        "btn_log_show": "▼ लॉग दिखाएं",
        "btn_log_hide": "▲ लॉग छिपाएं",
        "btn_log_copy": "कॉपी",
        "btn_log_save": "सहेजें...",
        "btn_log_clear": "साफ़ करें",
    },
    "hu": {
        "label_video": "Videó:",
        "label_output": "Kimenet:",
        "label_model": "Modell:",
        "label_from": "Tól:",
        "label_to": "Címzett:",
        "label_voice": "Hang:",
        "label_tts_rate": "TTS sebesség:",
        "label_options": "Opciók:",
        "label_model_hint": "← gyors / pontos →",
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
        "opt_xtts": "Hangklónozás (Coqui XTTS v2 – első futtatás: letöltések ~1,8 GB)",
        "opt_lipsync": "Ajakszinkron (Wav2Lip — első futás: letöltés ~416MB)",
        "label_engine": "Fordítómotor:",
        "engine_google": "Google (alapértelmezett)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (helyi)",
        "label_deepl_key": "DeepL API kulcs:",
        "opt_diarization": "Beszélőelkülönítés (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Ingyenes HF token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Adjon hozzá legalább egy videót.",
        "msg_completed": "A fordítás elkészült!",
        "msg_error": "Valami elromlott. Ellenőrizze a naplót.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Megtakarítás",
        "warn_editor": "Szerkesztő",
        "label_url": "URL:",
        "btn_download": "⬇ Letöltés és fordítás",
        "url_placeholder": "YouTube link (vagy más yt-dlp által támogatott webhely) beillesztése...",
        "msg_no_url": "Illesszen be legalább egy érvényes URL-t.",
        "msg_downloading": "⏳ Letöltés...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM (helyi, ajánlott — tömör fordítások szinkronizáláshoz)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Alapértelmezett: qwen3:8b (ajánlott) — qwen3:4b könnyű (~3 GB), qwen3:14b jobb minőség (~9 GB), qwen2.5:7b-instruct régi. Telepített Ollama szükséges",
        "opt_ollama_thinking":  "🧠 Gondolkodó mód (lassabb, jobb fordítások)",
        "hint_ollama_thinking": "Lépésről lépésre mérlegel, ~5x lassabb, de csökkenti az idióma- és nyelvtani hibákat",
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
        "opt_cosyvoice": "🎤 Pro hangklónozás (CosyVoice 2.0 — kísérleti, kézi beállítás)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 nincs telepítve.\n"
            "\n"
            "Telepítse automatikusan?\n"
            "  - Python csomag: ~500 MB\n"
            "  - Modell (első indításkor): ~1,7 GB\n"
            "\n"
            "A CosyVoice hallucinációs aránya <2 % (XTTS 5-15 %) hosszú tartalmaknál, így a kiugró audiok nagyon ritkák."
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 telepítése folyamatban (~500 MB pip + 1,7 GB modell az első indításkor)...",
        "hint_cosyvoice": "Modell: CosyVoice2-0.5B (Instruct) — IT cross-lingual módban <|it|> előtaggal",
        "label_log_panel": "Napló:",
        "btn_log_show": "▼ Napló megjelenítése",
        "btn_log_hide": "▲ Napló elrejtése",
        "btn_log_copy": "Másolás",
        "btn_log_save": "Mentés...",
        "btn_log_clear": "Törlés",
    },
    "id": {
        "label_video": "Video:",
        "label_output": "Keluaran:",
        "label_model": "Model:",
        "label_from": "Dari:",
        "label_to": "Ke:",
        "label_voice": "Suara:",
        "label_tts_rate": "Kecepatan TTS:",
        "label_options": "Pilihan:",
        "label_model_hint": "← cepat / akurat →",
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
        "opt_xtts": "Kloning Suara (Coqui XTTS v2 — dijalankan pertama kali: unduh ~1,8GB)",
        "opt_lipsync": "Sinkronisasi Bibir (Wav2Lip — menjalankan pertama: unduh ~416MB)",
        "label_engine": "Mesin terjemahan:",
        "engine_google": "Google (default)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "Kunci API DeepL:",
        "opt_diarization": "Pemisahan pembicara (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratis: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Tambahkan setidaknya satu video.",
        "msg_completed": "Terjemahan selesai!",
        "msg_error": "Ada yang tidak beres. Periksa lognya.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Menyimpan",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Unduh & Terjemahkan",
        "url_placeholder": "Tempel tautan YouTube (atau situs lain yang mendukung yt-dlp)...",
        "msg_no_url": "Tempelkan setidaknya satu URL yang valid.",
        "msg_downloading": "⏳ Mengunduh...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, direkomendasikan — terjemahan ringkas untuk dubbing)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Default: qwen3:8b (direkomendasikan) — qwen3:4b ringan (~3 GB), qwen3:14b kualitas lebih tinggi (~9 GB), qwen2.5:7b-instruct lawas. Memerlukan Ollama terinstal",
        "opt_ollama_thinking":  "🧠 Mode berpikir (lebih lambat, terjemahan lebih baik)",
        "hint_ollama_thinking": "Mempertimbangkan langkah demi langkah, ~5x lebih lambat tetapi mengurangi kesalahan idiom/tata bahasa",
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
        "opt_cosyvoice": "🎤 Pro voice cloning (CosyVoice 2.0 — eksperimental, setup manual)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 tidak terinstal.\n"
            "\n"
            "Instal otomatis?\n"
            "  - Paket Python: ~500 MB\n"
            "  - Model (saat Start pertama): ~1,7 GB\n"
            "\n"
            "CosyVoice memiliki tingkat halusinasi <2% (vs XTTS 5-15%) pada konten panjang, sehingga audio outlier sangat jarang."
        ),
        "msg_cosyvoice_installing": "[*] Menginstal CosyVoice 2.0 (~500 MB pip + 1,7 GB model saat Start pertama)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT via cross-lingual dengan prefiks <|it|>",
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Tampilkan log",
        "btn_log_hide": "▲ Sembunyikan log",
        "btn_log_copy": "Salin",
        "btn_log_save": "Simpan...",
        "btn_log_clear": "Bersihkan",
    },
    "ja": {
        "label_video": "ビデオ：",
        "label_output": "出力：",
        "label_model": "モデル：",
        "label_from": "から：",
        "label_to": "に：",
        "label_voice": "声：",
        "label_tts_rate": "TTS速度:",
        "label_options": "オプション:",
        "label_model_hint": "← 速い / 正確 →",
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
        "opt_xtts": "音声クローン作成 (Coqui XTTS v2 — 初回実行: ダウンロード ~1.8GB)",
        "opt_lipsync": "リップシンク (Wav2Lip — 初回実行: 約416MBダウンロード)",
        "label_engine": "翻訳エンジン:",
        "engine_google": "Google (デフォルト)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (ローカル)",
        "label_deepl_key": "DeepL APIキー:",
        "opt_diarization": "話者ダイアライゼーション (pyannote)",
        "label_hf_token": "HFトークン:",
        "hint_hf_token": "無料HFトークン: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "少なくとも 1 つのビデオを追加します。",
        "msg_completed": "翻訳が完了しました！",
        "msg_error": "何か問題が発生しました。ログを確認してください。",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "保存",
        "warn_editor": "エディタ",
        "label_url": "URL:",
        "btn_download": "⬇ ダウンロードと翻訳",
        "url_placeholder": "YouTube リンク (または他の yt-dlp サポート サイト) を貼り付けます...",
        "msg_no_url": "少なくとも 1 つの有効な URL を貼り付けます。",
        "msg_downloading": "⏳ ダウンロード中...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM(ローカル、推奨 — 吹き替え用の簡潔な翻訳)",
        "label_ollama_model": "モデル:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "デフォルト: qwen3:8b(推奨) — qwen3:4b 軽量(~3 GB)、qwen3:14b 高品質(~9 GB)、qwen2.5:7b-instruct レガシー。Ollama のインストールが必要",
        "opt_ollama_thinking":  "🧠 思考モード（低速、より高品質な翻訳）",
        "hint_ollama_thinking": "段階的に検討、約5倍遅いがイディオム・文法エラーを削減",
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
        "opt_cosyvoice": "🎤 プロボイスクローニング(CosyVoice 2.0 — 実験的、手動セットアップ)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 がインストールされていません。\n"
            "\n"
            "自動インストールしますか?\n"
            "  - Python パッケージ: 約 500 MB\n"
            "  - モデル(初回 Start 時): 約 1.7 GB\n"
            "\n"
            "CosyVoice の幻覚率は 2% 未満(XTTS の 5-15% に対して)で、長尺コンテンツでも異常な音声出力は非常にまれです。"
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 をインストール中(~500 MB pip + 初回 Start 時 1.7 GB モデル)...",
        "hint_cosyvoice": "モデル: CosyVoice2-0.5B (Instruct) — IT はクロスリンガル経由で <|it|> プレフィックス付き",
        "label_log_panel": "ログ:",
        "btn_log_show": "▼ ログを表示",
        "btn_log_hide": "▲ ログを非表示",
        "btn_log_copy": "コピー",
        "btn_log_save": "保存...",
        "btn_log_clear": "クリア",
    },
    "ko": {
        "label_video": "동영상:",
        "label_output": "산출:",
        "label_model": "모델:",
        "label_from": "에서:",
        "label_to": "에게:",
        "label_voice": "목소리:",
        "label_tts_rate": "TTS 속도:",
        "label_options": "옵션:",
        "label_model_hint": "← 빠르다 / 정확하다 →",
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
        "opt_xtts": "음성 복제(Coqui XTTS v2 — 첫 실행: 다운로드 ~1.8GB)",
        "opt_lipsync": "립싱크 (Wav2Lip — 첫 실행: 약 416MB 다운로드)",
        "label_engine": "번역 엔진:",
        "engine_google": "Google (기본)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (로컬)",
        "label_deepl_key": "DeepL API 키:",
        "opt_diarization": "화자 분리 (pyannote)",
        "label_hf_token": "HF 토큰:",
        "hint_hf_token": "무료 HF 토큰: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "동영상을 하나 이상 추가하세요.",
        "msg_completed": "번역 완료!",
        "msg_error": "문제가 발생했습니다. 로그를 확인하세요.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "구하다",
        "warn_editor": "편집자",
        "label_url": "URL:",
        "btn_download": "⬇ 다운로드 및 번역",
        "url_placeholder": "YouTube 링크(또는 다른 yt-dlp 지원 사이트)를 붙여넣으세요...",
        "msg_no_url": "유효한 URL을 하나 이상 붙여넣으세요.",
        "msg_downloading": "⏳ 다운로드 중...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "Ollama LLM (로컬, 권장 — 더빙용 간결한 번역)",
        "label_ollama_model": "모델:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "기본값: qwen3:8b (권장) — qwen3:4b 경량 (~3 GB), qwen3:14b 고품질 (~9 GB), qwen2.5:7b-instruct 레거시. Ollama 설치 필요",
        "opt_ollama_thinking":  "🧠 사고 모드 (느림, 더 나은 번역)",
        "hint_ollama_thinking": "단계별로 숙고, 약 5배 느리지만 관용구/문법 오류 감소",
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
        "opt_cosyvoice": "🎤 프로 보이스 클로닝 (CosyVoice 2.0 — 실험적, 수동 설정)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0이 설치되지 않았습니다.\n"
            "\n"
            "자동으로 설치하시겠습니까?\n"
            "  - Python 패키지: ~500 MB\n"
            "  - 모델 (첫 시작 시): ~1.7 GB\n"
            "\n"
            "CosyVoice는 장문 콘텐츠에서 환각률이 2% 미만(XTTS의 5-15% 대비)이므로 이상한 오디오 출력은 매우 드뭅니다."
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 설치 중 (~500 MB pip + 첫 시작 시 1.7 GB 모델)...",
        "hint_cosyvoice": "모델: CosyVoice2-0.5B (Instruct) — IT는 <|it|> 접두사가 있는 크로스링구얼 경유",
        "label_log_panel": "로그:",
        "btn_log_show": "▼ 로그 표시",
        "btn_log_hide": "▲ 로그 숨기기",
        "btn_log_copy": "복사",
        "btn_log_save": "저장...",
        "btn_log_clear": "지우기",
    },
    "no": {
        "label_video": "Video:",
        "label_output": "Produksjon:",
        "label_model": "Modell:",
        "label_from": "Fra:",
        "label_to": "Til:",
        "label_voice": "Stemme:",
        "label_tts_rate": "TTS hastighet:",
        "label_options": "Alternativer:",
        "label_model_hint": "← rask / nøyaktig →",
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
        "opt_xtts": "Stemmekloning (Coqui XTTS v2 — første kjøring: nedlastinger ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip — første kjøring: last ned ~416MB)",
        "label_engine": "Oversettelsesmotor:",
        "engine_google": "Google (standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-nøkkel:",
        "opt_diarization": "Taleridentifikasjon (pyannote)",
        "label_hf_token": "HF-token:",
        "hint_hf_token": "Gratis HF-token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Legg til minst én video.",
        "msg_completed": "Oversettelsen fullført!",
        "msg_error": "Noe gikk galt. Sjekk loggen.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Spare",
        "warn_editor": "Redaktør",
        "label_url": "URL:",
        "btn_download": "⬇ Last ned og oversett",
        "url_placeholder": "Lim inn YouTube-kobling (eller et annet yt-dlp-støttet nettsted)...",
        "msg_no_url": "Lim inn minst én gyldig nettadresse.",
        "msg_downloading": "⏳ Laster ned...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, anbefalt — konsise oversettelser for dubbing)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Standard: qwen3:8b (anbefalt) — qwen3:4b lett (~3 GB), qwen3:14b høyere kvalitet (~9 GB), qwen2.5:7b-instruct eldre. Krever Ollama installert",
        "opt_ollama_thinking":  "🧠 Tenkemodus (tregere, bedre oversettelser)",
        "hint_ollama_thinking": "Vurderer trinn for trinn, ~5x tregere men reduserer idiom-/grammatikkfeil",
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
        "opt_cosyvoice": "🎤 Pro stemmekloning (CosyVoice 2.0 — eksperimentell, manuelt oppsett)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 ikke installert.\n"
            "\n"
            "Installere automatisk?\n"
            "  - Python-pakke: ~500 MB\n"
            "  - Modell (ved første Start): ~1,7 GB\n"
            "\n"
            "CosyVoice har en hallusinasjonsrate på <2 % (mot XTTS 5-15 %) på lange opptak, så avvikende lyd er svært sjeldent."
        ),
        "msg_cosyvoice_installing": "[*] Installerer CosyVoice 2.0 (~500 MB pip + 1,7 GB modell ved første Start)...",
        "hint_cosyvoice": "Modell: CosyVoice2-0.5B (Instruct) — IT via cross-lingual med prefiks <|it|>",
        "label_log_panel": "Logg:",
        "btn_log_show": "▼ Vis logg",
        "btn_log_hide": "▲ Skjul logg",
        "btn_log_copy": "Kopier",
        "btn_log_save": "Lagre...",
        "btn_log_clear": "Tøm",
    },
    "pl": {
        "label_video": "Wideo:",
        "label_output": "Wyjście:",
        "label_model": "Model:",
        "label_from": "Z:",
        "label_to": "Do:",
        "label_voice": "Głos:",
        "label_tts_rate": "Prędkość TTS:",
        "label_options": "Opcje:",
        "label_model_hint": "← szybki / dokładny →",
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
        "opt_xtts": "Klonowanie głosu (Coqui XTTS v2 — pierwsze uruchomienie: pliki do pobrania ~1,8 GB)",
        "opt_lipsync": "Synchronizacja ust (Wav2Lip — pierwsze uruchomienie: pobranie ~416MB)",
        "label_engine": "Silnik tłumaczenia:",
        "engine_google": "Google (domyślny)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokalny)",
        "label_deepl_key": "Klucz API DeepL:",
        "opt_diarization": "Rozpoznawanie mówców (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Darmowy token HF: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Dodaj co najmniej jeden film.",
        "msg_completed": "Tłumaczenie zakończone!",
        "msg_error": "Coś poszło nie tak. Sprawdź dziennik.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Ratować",
        "warn_editor": "Redaktor",
        "label_url": "URL:",
        "btn_download": "⬇ Pobierz i przetłumacz",
        "url_placeholder": "Wklej link do YouTube (lub innej witryny obsługującej yt-dlp)...",
        "msg_no_url": "Wklej co najmniej jeden prawidłowy adres URL.",
        "msg_downloading": "⏳ Pobieram...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokalny, zalecany — zwięzłe tłumaczenia do dubbingu)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Domyślnie: qwen3:8b (zalecane) — qwen3:4b lekki (~3 GB), qwen3:14b wyższa jakość (~9 GB), qwen2.5:7b-instruct starszy. Wymaga zainstalowanego Ollama",
        "opt_ollama_thinking":  "🧠 Tryb myślenia (wolniejszy, lepsze tłumaczenia)",
        "hint_ollama_thinking": "Rozważa krok po kroku, ~5x wolniej, ale zmniejsza błędy w idiomach i gramatyce",
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
        "opt_cosyvoice": "🎤 Pro klonowanie głosu (CosyVoice 2.0 — eksperymentalne, ręczna konfiguracja)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 nie jest zainstalowany.\n"
            "\n"
            "Zainstalować automatycznie?\n"
            "  - Pakiet Python: ~500 MB\n"
            "  - Model (przy pierwszym Start): ~1,7 GB\n"
            "\n"
            "CosyVoice ma wskaźnik halucynacji <2% (vs XTTS 5-15%) w długich nagraniach, więc nietypowe wyjścia audio są bardzo rzadkie."
        ),
        "msg_cosyvoice_installing": "[*] Instalowanie CosyVoice 2.0 (~500 MB pip + 1,7 GB model przy pierwszym Start)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT przez cross-lingual z prefiksem <|it|>",
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Pokaż log",
        "btn_log_hide": "▲ Ukryj log",
        "btn_log_copy": "Kopiuj",
        "btn_log_save": "Zapisz...",
        "btn_log_clear": "Wyczyść",
    },
    "pt": {
        "label_video": "Vídeo:",
        "label_output": "Saída:",
        "label_model": "Modelo:",
        "label_from": "De:",
        "label_to": "Para:",
        "label_voice": "Voz:",
        "label_tts_rate": "Velocidade TTS:",
        "label_options": "Opções:",
        "label_model_hint": "← rápido / preciso →",
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
        "opt_xtts": "Clonagem de voz (Coqui XTTS v2 – primeira execução: downloads de aproximadamente 1,8 GB)",
        "opt_lipsync": "Sincronização labial (Wav2Lip — primeira execução: download ~416MB)",
        "label_engine": "Motor de tradução:",
        "engine_google": "Google (padrão)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Chave API DeepL:",
        "opt_diarization": "Diarização de locutores (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratuito: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Adicione pelo menos um vídeo.",
        "msg_completed": "Tradução concluída!",
        "msg_error": "Algo deu errado. Verifique o registro.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Salvar",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Baixe e traduza",
        "url_placeholder": "Cole o link do YouTube (ou outro site compatível com yt-dlp)...",
        "msg_no_url": "Cole pelo menos um URL válido.",
        "msg_downloading": "⏳ Baixando...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recomendado — traduções concisas para dublagem)",
        "label_ollama_model": "Modelo:",
        "label_ollama_url": "URL do Ollama:",
        "hint_ollama": "Padrão: qwen3:8b (recomendado) — qwen3:4b leve (~3 GB), qwen3:14b qualidade superior (~9 GB), qwen2.5:7b-instruct legado. Requer Ollama instalado",
        "opt_ollama_thinking":  "🧠 Modo pensante (mais lento, traduções melhores)",
        "hint_ollama_thinking": "Delibera passo a passo, ~5x mais lento mas reduz erros de idiomas/gramática",
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
        "opt_cosyvoice": "🎤 Voice Cloning Pro (CosyVoice 2.0 — experimental, configuração manual)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 não instalado.\n"
            "\n"
            "Instalar automaticamente?\n"
            "  - Pacote Python: ~500 MB\n"
            "  - Modelo (no primeiro Iniciar): ~1,7 GB\n"
            "\n"
            "CosyVoice tem taxa de alucinação <2% (vs XTTS 5-15%) em conteúdo longo, então saídas de áudio anômalas são muito raras."
        ),
        "msg_cosyvoice_installing": "[*] Instalando CosyVoice 2.0 (~500 MB pip + modelo de 1,7 GB no primeiro Iniciar)...",
        "hint_cosyvoice": "Modelo: CosyVoice2-0.5B (Instruct) — IT via cross-lingual com prefixo <|it|>",
        "label_log_panel": "Log:",
        "btn_log_show": "▼ Mostrar log",
        "btn_log_hide": "▲ Ocultar log",
        "btn_log_copy": "Copiar",
        "btn_log_save": "Salvar...",
        "btn_log_clear": "Limpar",
    },
    "ro": {
        "label_video": "Video:",
        "label_output": "Ieșire:",
        "label_model": "Model:",
        "label_from": "Din:",
        "label_to": "La:",
        "label_voice": "Voce:",
        "label_tts_rate": "Viteza TTS:",
        "label_options": "Opțiuni:",
        "label_model_hint": "← rapid / precis →",
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
        "opt_xtts": "Clonarea vocii (Coqui XTTS v2 — prima rulare: descărcări ~1,8 GB)",
        "opt_lipsync": "Lip Sync (Wav2Lip — prima rulare: descărcare ~416MB)",
        "label_engine": "Motor de traducere:",
        "engine_google": "Google (implicit)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Cheie API DeepL:",
        "opt_diarization": "Identificare vorbitori (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratuit: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Adăugați cel puțin un videoclip.",
        "msg_completed": "Traducerea finalizată!",
        "msg_error": "Ceva a mers prost. Verificați jurnalul.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Salva",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Descărcați și traduceți",
        "url_placeholder": "Inserați linkul YouTube (sau alt site acceptat de yt-dlp)...",
        "msg_no_url": "Lipiți cel puțin o adresă URL validă.",
        "msg_downloading": "⏳ Se descarcă...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recomandat — traduceri concise pentru dublaj)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Implicit: qwen3:8b (recomandat) — qwen3:4b ușor (~3 GB), qwen3:14b calitate superioară (~9 GB), qwen2.5:7b-instruct vechi. Necesită Ollama instalat",
        "opt_ollama_thinking":  "🧠 Mod gândire (mai lent, traduceri mai bune)",
        "hint_ollama_thinking": "Deliberează pas cu pas, ~5x mai lent, dar reduce erorile de idiomuri/gramatică",
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
        "opt_cosyvoice": "🎤 Pro voice cloning (CosyVoice 2.0 — experimental, configurare manuală)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 nu este instalat.\n"
            "\n"
            "Instalați automat?\n"
            "  - Pachet Python: ~500 MB\n"
            "  - Model (la prima pornire): ~1,7 GB\n"
            "\n"
            "CosyVoice are rata de halucinații <2 % (față de XTTS 5-15 %) pe conținut lung, deci ieșirile audio aberante sunt foarte rare."
        ),
        "msg_cosyvoice_installing": "[*] Se instalează CosyVoice 2.0 (~500 MB pip + 1,7 GB model la prima pornire)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT via cross-lingual cu prefix <|it|>",
        "label_log_panel": "Jurnal:",
        "btn_log_show": "▼ Afișează jurnalul",
        "btn_log_hide": "▲ Ascunde jurnalul",
        "btn_log_copy": "Copiază",
        "btn_log_save": "Salvează...",
        "btn_log_clear": "Șterge",
    },
    "ru": {
        "label_video": "Видео:",
        "label_output": "Выход:",
        "label_model": "Модель:",
        "label_from": "От:",
        "label_to": "К:",
        "label_voice": "Голос:",
        "label_tts_rate": "Скорость ТТС:",
        "label_options": "Параметры:",
        "label_model_hint": "← быстро / точно →",
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
        "opt_xtts": "Голосовое клонирование (Coqui XTTS v2 — первый запуск: загрузка ~ 1,8 ГБ)",
        "opt_lipsync": "Синхронизация губ (Wav2Lip — первый запуск: загрузка ~416МБ)",
        "label_engine": "Движок перевода:",
        "engine_google": "Google (по умолчанию)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (локально)",
        "label_deepl_key": "API ключ DeepL:",
        "opt_diarization": "Разделение дикторов (pyannote)",
        "label_hf_token": "Токен HF:",
        "hint_hf_token": "Бесплатный токен HF: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Добавьте хотя бы одно видео.",
        "msg_completed": "Перевод завершен!",
        "msg_error": "Что-то пошло не так. Проверьте журнал.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Сохранять",
        "warn_editor": "Редактор",
        "label_url": "URL:",
        "btn_download": "⬇ Скачать и перевести",
        "url_placeholder": "Вставьте ссылку на YouTube (или другой сайт, поддерживаемый yt-dlp)...",
        "msg_no_url": "Вставьте хотя бы один действительный URL-адрес.",
        "msg_downloading": "⏳ Загрузка...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (локально, рекомендуется — лаконичные переводы для дубляжа)",
        "label_ollama_model": "Модель:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "По умолчанию: qwen3:8b (рекомендуется) — qwen3:4b лёгкий (~3 ГБ), qwen3:14b более высокое качество (~9 ГБ), qwen2.5:7b-instruct устаревший. Требуется установленный Ollama",
        "opt_ollama_thinking":  "🧠 Режим рассуждения (медленнее, переводы лучше)",
        "hint_ollama_thinking": "Обдумывает шаг за шагом, ~5x медленнее, но уменьшает ошибки идиом/грамматики",
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
        "opt_cosyvoice": "🎤 Pro клонирование голоса (CosyVoice 2.0 — экспериментально, ручная настройка)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 не установлен.\n"
            "\n"
            "Установить автоматически?\n"
            "  - Пакет Python: ~500 МБ\n"
            "  - Модель (при первом Старте): ~1,7 ГБ\n"
            "\n"
            "Уровень галлюцинаций CosyVoice <2 % (против XTTS 5-15 %) на длинном контенте, поэтому аномальные аудиовыходы очень редки."
        ),
        "msg_cosyvoice_installing": "[*] Установка CosyVoice 2.0 (~500 МБ pip + 1,7 ГБ модель при первом Старте)...",
        "hint_cosyvoice": "Модель: CosyVoice2-0.5B (Instruct) — IT через cross-lingual с префиксом <|it|>",
        "label_log_panel": "Журнал:",
        "btn_log_show": "▼ Показать журнал",
        "btn_log_hide": "▲ Скрыть журнал",
        "btn_log_copy": "Копировать",
        "btn_log_save": "Сохранить...",
        "btn_log_clear": "Очистить",
    },
    "es": {
        "label_video": "Video:",
        "label_output": "Producción:",
        "label_model": "Modelo:",
        "label_from": "De:",
        "label_to": "A:",
        "label_voice": "Voz:",
        "label_tts_rate": "Velocidad TTS:",
        "label_options": "Opciones:",
        "label_model_hint": "← rápido / preciso →",
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
        "opt_xtts": "Clonación de voz (Coqui XTTS v2 – primera ejecución: descargas ~1,8 GB)",
        "opt_lipsync": "Sincronización labial (Wav2Lip — primera ejecución: descarga ~416MB)",
        "label_engine": "Motor de traducción:",
        "engine_google": "Google (predeterminado)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (local)",
        "label_deepl_key": "Clave API de DeepL:",
        "opt_diarization": "Diarización de hablantes (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF gratuito: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Añade al menos un vídeo.",
        "msg_completed": "¡Traducción completada!",
        "msg_error": "Algo salió mal. Consulta el registro.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Ahorrar",
        "warn_editor": "Editor",
        "label_url": "URL:",
        "btn_download": "⬇ Descargar y traducir",
        "url_placeholder": "Pegue el enlace de YouTube (u otro sitio compatible con yt-dlp)...",
        "msg_no_url": "Pegue al menos una URL válida.",
        "msg_downloading": "⏳ Descargando...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (local, recomendado — traducciones concisas para doblaje)",
        "label_ollama_model": "Modelo:",
        "label_ollama_url": "URL de Ollama:",
        "hint_ollama": "Por defecto: qwen3:8b (recomendado) — qwen3:4b ligero (~3 GB), qwen3:14b mayor calidad (~9 GB), qwen2.5:7b-instruct heredado. Requiere Ollama instalado",
        "opt_ollama_thinking":  "🧠 Modo de pensamiento (más lento, mejores traducciones)",
        "hint_ollama_thinking": "Delibera paso a paso, ~5x más lento pero reduce errores de modismos/gramática",
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
        "opt_cosyvoice": "🎤 Voice Cloning Pro (CosyVoice 2.0 — experimental, configuración manual)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 no instalado.\n"
            "\n"
            "¿Instalar automáticamente?\n"
            "  - Paquete Python: ~500 MB\n"
            "  - Modelo (al primer Iniciar): ~1,7 GB\n"
            "\n"
            "CosyVoice tiene una tasa de alucinación <2% (vs XTTS 5-15%) en contenido largo, por lo que las salidas de audio anómalas son muy raras."
        ),
        "msg_cosyvoice_installing": "[*] Instalando CosyVoice 2.0 (~500 MB pip + modelo de 1,7 GB al primer Iniciar)...",
        "hint_cosyvoice": "Modelo: CosyVoice2-0.5B (Instruct) — IT vía cross-lingual con prefijo <|it|>",
        "label_log_panel": "Registro:",
        "btn_log_show": "▼ Mostrar registro",
        "btn_log_hide": "▲ Ocultar registro",
        "btn_log_copy": "Copiar",
        "btn_log_save": "Guardar...",
        "btn_log_clear": "Borrar",
    },
    "sv": {
        "label_video": "Video:",
        "label_output": "Produktion:",
        "label_model": "Modell:",
        "label_from": "Från:",
        "label_to": "Till:",
        "label_voice": "Röst:",
        "label_tts_rate": "TTS hastighet:",
        "label_options": "Alternativ:",
        "label_model_hint": "← snabb / exakt →",
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
        "opt_xtts": "Röstkloning (Coqui XTTS v2 — första körningen: nedladdningar ~1,8 GB)",
        "opt_lipsync": "Läppsynk (Wav2Lip — första körningen: laddar ner ~416MB)",
        "label_engine": "Översättningsmotor:",
        "engine_google": "Google (standard)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (lokal)",
        "label_deepl_key": "DeepL API-nyckel:",
        "opt_diarization": "Talaridentifiering (pyannote)",
        "label_hf_token": "HF-token:",
        "hint_hf_token": "Gratis HF-token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Lägg till minst en video.",
        "msg_completed": "Översättningen klar!",
        "msg_error": "Något gick fel. Kontrollera loggen.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Spara",
        "warn_editor": "Redaktör",
        "label_url": "URL:",
        "btn_download": "⬇ Ladda ner och översätt",
        "url_placeholder": "Klistra in YouTube-länk (eller annan webbplats som stöds av yt-dlp)...",
        "msg_no_url": "Klistra in minst en giltig webbadress.",
        "msg_downloading": "⏳ Laddar ner...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (lokal, rekommenderas — koncisa översättningar för dubbning)",
        "label_ollama_model": "Modell:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Standard: qwen3:8b (rekommenderas) — qwen3:4b lätt (~3 GB), qwen3:14b högre kvalitet (~9 GB), qwen2.5:7b-instruct äldre. Kräver installerat Ollama",
        "opt_ollama_thinking":  "🧠 Tänkeläge (långsammare, bättre översättningar)",
        "hint_ollama_thinking": "Överväger steg för steg, ~5x långsammare men minskar idiom-/grammatikfel",
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
        "opt_cosyvoice": "🎤 Pro röstkloning (CosyVoice 2.0 — experimentell, manuell installation)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 inte installerad.\n"
            "\n"
            "Installera automatiskt?\n"
            "  - Python-paket: ~500 MB\n"
            "  - Modell (vid första Start): ~1,7 GB\n"
            "\n"
            "CosyVoice har en hallucinationsfrekvens <2 % (mot XTTS 5-15 %) på långt innehåll, så avvikande ljudutdata är mycket sällsynt."
        ),
        "msg_cosyvoice_installing": "[*] Installerar CosyVoice 2.0 (~500 MB pip + 1,7 GB modell vid första Start)...",
        "hint_cosyvoice": "Modell: CosyVoice2-0.5B (Instruct) — IT via cross-lingual med prefix <|it|>",
        "label_log_panel": "Logg:",
        "btn_log_show": "▼ Visa logg",
        "btn_log_hide": "▲ Dölj logg",
        "btn_log_copy": "Kopiera",
        "btn_log_save": "Spara...",
        "btn_log_clear": "Rensa",
    },
    "tr": {
        "label_video": "Video:",
        "label_output": "Çıkış:",
        "label_model": "Modeli:",
        "label_from": "İtibaren:",
        "label_to": "İle:",
        "label_voice": "Ses:",
        "label_tts_rate": "TTS Hızı:",
        "label_options": "Seçenekler:",
        "label_model_hint": "← hızlı / doğru →",
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
        "opt_xtts": "Ses Klonlama (Coqui XTTS v2 — ilk çalıştırma: indirmeler ~1,8 GB)",
        "opt_lipsync": "Dudak Senkronu (Wav2Lip — ilk çalıştırma: ~416MB indirme)",
        "label_engine": "Çeviri motoru:",
        "engine_google": "Google (varsayılan)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (yerel)",
        "label_deepl_key": "DeepL API anahtarı:",
        "opt_diarization": "Konuşmacı ayrıştırma (pyannote)",
        "label_hf_token": "HF token:",
        "hint_hf_token": "Ücretsiz HF token: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "En az bir video ekleyin.",
        "msg_completed": "Çeviri tamamlandı!",
        "msg_error": "Bir şeyler ters gitti. Günlüğü kontrol edin.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Kaydetmek",
        "warn_editor": "Editör",
        "label_url": "URL:",
        "btn_download": "⬇ İndir ve Çevir",
        "url_placeholder": "YouTube bağlantısını (veya yt-dlp destekli başka bir siteyi) yapıştırın...",
        "msg_no_url": "En az bir geçerli URL yapıştırın.",
        "msg_downloading": "⏳ İndiriliyor...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (yerel, önerilen — dublaj için özlü çeviriler)",
        "label_ollama_model": "Model:",
        "label_ollama_url": "Ollama URL:",
        "hint_ollama": "Varsayılan: qwen3:8b (önerilen) — qwen3:4b hafif (~3 GB), qwen3:14b daha yüksek kalite (~9 GB), qwen2.5:7b-instruct eski. Ollama kurulu olmasını gerektirir",
        "opt_ollama_thinking":  "🧠 Düşünme modu (daha yavaş, daha iyi çeviriler)",
        "hint_ollama_thinking": "Adım adım değerlendirir, ~5x daha yavaş ancak deyim/dilbilgisi hatalarını azaltır",
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
        "opt_cosyvoice": "🎤 Pro ses klonlama (CosyVoice 2.0 — deneysel, manuel kurulum)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 kurulu değil.\n"
            "\n"
            "Otomatik olarak kur?\n"
            "  - Python paketi: ~500 MB\n"
            "  - Model (ilk Başlat'ta): ~1,7 GB\n"
            "\n"
            "CosyVoice'un halüsinasyon oranı <%2'dir (XTTS %5-15'e karşı) uzun içerikte, bu nedenle aykırı ses çıktıları çok nadirdir."
        ),
        "msg_cosyvoice_installing": "[*] CosyVoice 2.0 kuruluyor (~500 MB pip + ilk Başlat'ta 1,7 GB model)...",
        "hint_cosyvoice": "Model: CosyVoice2-0.5B (Instruct) — IT, <|it|> önekiyle cross-lingual üzerinden",
        "label_log_panel": "Günlük:",
        "btn_log_show": "▼ Günlüğü göster",
        "btn_log_hide": "▲ Günlüğü gizle",
        "btn_log_copy": "Kopyala",
        "btn_log_save": "Kaydet...",
        "btn_log_clear": "Temizle",
    },
    "uk": {
        "label_video": "Відео:",
        "label_output": "Вихід:",
        "label_model": "модель:",
        "label_from": "Від:",
        "label_to": "до:",
        "label_voice": "Голос:",
        "label_tts_rate": "Швидкість TTS:",
        "label_options": "Опції:",
        "label_model_hint": "← швидко / точно →",
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
        "opt_xtts": "Клонування голосу (Coqui XTTS v2 — перший запуск: завантаження ~1,8 ГБ)",
        "opt_lipsync": "Синхронізація губ (Wav2Lip — перший запуск: завантаження ~416МБ)",
        "label_engine": "Рушій перекладу:",
        "engine_google": "Google (типовий)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (локально)",
        "label_deepl_key": "Ключ API DeepL:",
        "opt_diarization": "Розділення дикторів (pyannote)",
        "label_hf_token": "Токен HF:",
        "hint_hf_token": "Безкоштовний токен HF: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Додайте хоча б одне відео.",
        "msg_completed": "Переклад завершено!",
        "msg_error": "Щось пішло не так. Перевірте журнал.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "зберегти",
        "warn_editor": "редактор",
        "label_url": "URL:",
        "btn_download": "⬇ Завантажте та перекладіть",
        "url_placeholder": "Вставте посилання YouTube (або інший сайт, що підтримує yt-dlp)...",
        "msg_no_url": "Вставте принаймні одну дійсну URL-адресу.",
        "msg_downloading": "⏳ Завантаження...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (локально, рекомендовано — лаконічні переклади для дубляжу)",
        "label_ollama_model": "Модель:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "За замовчуванням: qwen3:8b (рекомендовано) — qwen3:4b легка (~3 ГБ), qwen3:14b вища якість (~9 ГБ), qwen2.5:7b-instruct застаріла. Потрібен встановлений Ollama",
        "opt_ollama_thinking":  "🧠 Режим міркування (повільніше, кращі переклади)",
        "hint_ollama_thinking": "Обмірковує крок за кроком, ~5x повільніше, але зменшує помилки ідіом/граматики",
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
        "opt_cosyvoice": "🎤 Pro клонування голосу (CosyVoice 2.0 — експериментально, ручне налаштування)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 не встановлено.\n"
            "\n"
            "Встановити автоматично?\n"
            "  - Пакет Python: ~500 МБ\n"
            "  - Модель (при першому Старті): ~1,7 ГБ\n"
            "\n"
            "Рівень галюцинацій CosyVoice <2 % (проти XTTS 5-15 %) на довгому контенті, тому аномальні аудіовиходи дуже рідкі."
        ),
        "msg_cosyvoice_installing": "[*] Встановлення CosyVoice 2.0 (~500 МБ pip + 1,7 ГБ модель при першому Старті)...",
        "hint_cosyvoice": "Модель: CosyVoice2-0.5B (Instruct) — IT через cross-lingual з префіксом <|it|>",
        "label_log_panel": "Журнал:",
        "btn_log_show": "▼ Показати журнал",
        "btn_log_hide": "▲ Сховати журнал",
        "btn_log_copy": "Копіювати",
        "btn_log_save": "Зберегти...",
        "btn_log_clear": "Очистити",
    },
    "vi": {
        "label_video": "Băng hình:",
        "label_output": "Đầu ra:",
        "label_model": "Người mẫu:",
        "label_from": "Từ:",
        "label_to": "ĐẾN:",
        "label_voice": "Tiếng nói:",
        "label_tts_rate": "Tốc độ TTS:",
        "label_options": "Tùy chọn:",
        "label_model_hint": "← nhanh / chính xác →",
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
        "opt_xtts": "Nhân bản giọng nói (Coqui XTTS v2 — lần chạy đầu tiên: tải xuống ~1,8GB)",
        "opt_lipsync": "Đồng bộ môi (Wav2Lip — chạy lần đầu: tải ~416MB)",
        "label_engine": "Công cụ dịch:",
        "engine_google": "Google (mặc định)",
        "engine_deepl": "DeepL Free",
        "engine_marian": "MarianMT (cục bộ)",
        "label_deepl_key": "Khóa API DeepL:",
        "opt_diarization": "Phân tách người nói (pyannote)",
        "label_hf_token": "Token HF:",
        "hint_hf_token": "Token HF miễn phí: huggingface.co/settings/tokens",
        "msg_xtts_no_lang": "XTTS v2 does not support '{lang}'. Falling back to Edge-TTS.",
        "msg_no_video": "Thêm ít nhất một video.",
        "msg_completed": "Bản dịch đã hoàn tất!",
        "msg_error": "Đã xảy ra lỗi. Kiểm tra nhật ký.",
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
        "editor_seg_label": "Segment {} —",
        "editor_btn_save": "Cứu",
        "warn_editor": "Biên tập viên",
        "label_url": "URL:",
        "btn_download": "⬇ Tải xuống và dịch",
        "url_placeholder": "Dán liên kết YouTube (hoặc trang web hỗ trợ yt-dlp khác)...",
        "msg_no_url": "Dán ít nhất một URL hợp lệ.",
        "msg_downloading": "⏳ Đang tải xuống...",
        "log_downloading": "Downloading: {}",
        "log_dl_done": "Download complete → {}",
        "log_dl_error": "Download error: {}",
        "engine_ollama": "LLM Ollama (cục bộ, khuyến nghị — bản dịch ngắn gọn cho lồng tiếng)",
        "label_ollama_model": "Mô hình:",
        "label_ollama_url": "URL Ollama:",
        "hint_ollama": "Mặc định: qwen3:8b (khuyến nghị) — qwen3:4b nhẹ (~3 GB), qwen3:14b chất lượng cao hơn (~9 GB), qwen2.5:7b-instruct cũ. Yêu cầu đã cài Ollama",
        "opt_ollama_thinking":  "🧠 Chế độ tư duy (chậm hơn, dịch tốt hơn)",
        "hint_ollama_thinking": "Cân nhắc từng bước, chậm ~5x nhưng giảm lỗi thành ngữ/ngữ pháp",
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
        "opt_cosyvoice": "🎤 Nhân bản giọng Pro (CosyVoice 2.0 — thử nghiệm, cài thủ công)",
        "msg_cosyvoice_unavailable": (
            "CosyVoice 2.0 chưa được cài đặt.\n"
            "\n"
            "Cài đặt tự động?\n"
            "  - Gói Python: ~500 MB\n"
            "  - Mô hình (lần đầu Start): ~1,7 GB\n"
            "\n"
            "CosyVoice có tỷ lệ ảo giác <2% (so với XTTS 5-15%) trên nội dung dài, vì vậy đầu ra âm thanh bất thường rất hiếm."
        ),
        "msg_cosyvoice_installing": "[*] Đang cài CosyVoice 2.0 (~500 MB pip + 1,7 GB mô hình ở lần đầu Start)...",
        "hint_cosyvoice": "Mô hình: CosyVoice2-0.5B (Instruct) — IT qua cross-lingual với tiền tố <|it|>",
        "label_log_panel": "Nhật ký:",
        "btn_log_show": "▼ Hiển thị nhật ký",
        "btn_log_hide": "▲ Ẩn nhật ký",
        "btn_log_copy": "Sao chép",
        "btn_log_save": "Lưu...",
        "btn_log_clear": "Xóa",
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


# ═══════════════════════════════════════════════════════════
#  PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════

def _run_ffmpeg(cmd: list[str], step: str = "ffmpeg"):
    # ffmpeg moderno emette UTF-8 su tutte le piattaforme (incluso Windows).
    # Usiamo errors="replace" per degradare gracefully su eventuali byte non-UTF8
    # (es. path locali con encoding legacy) invece di crashare con UnicodeDecodeError.
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-10:]
        raise RuntimeError(f"{step} failed (exit {proc.returncode}):\n" + "\n".join(err))
    return proc


def download_youtube(url: str, out_dir: str) -> str:
    """Downloads a video from YouTube (or any yt-dlp supported site) to out_dir.
    Returns the path of the downloaded file."""
    import yt_dlp

    out_template = os.path.join(out_dir, "%(title).80s.%(ext)s")
    ydl_opts = {
        # Rimosso filtro ext=mp4: forzava h264 e YouTube cappa 1080p a VP9/AV1.
        # ffmpeg fa il merge in mp4 grazie a merge_output_format.
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "restrictfilenames": True,
        "socket_timeout": 30,
        "retries": 5,
        # Use iOS client to avoid YouTube 403/SABR streaming issues
        "extractor_args": {"youtube": {"player_client": ["ios", "android"]}},
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp may change extension after merge
        if not os.path.exists(filename):
            stem = os.path.splitext(filename)[0]
            for ext in (".mp4", ".mkv", ".webm"):
                candidate = stem + ext
                if os.path.exists(candidate):
                    filename = candidate
                    break

    if not os.path.exists(filename):
        raise RuntimeError(f"Download completed but file not found: {filename}")

    print(f"[+] Downloaded: {filename}", flush=True)
    return filename


def extract_audio(video_path: str, audio_path: str):
    print(f"[1/6] Extracting audio from: {Path(video_path).name}", flush=True)
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", audio_path
    ], step="extract_audio")
    print(f"     → {audio_path}", flush=True)


def separate_audio(audio_path: str, tmp_dir: str) -> tuple[str, str]:
    """Separates voice and music with Demucs htdemucs. Returns (vocals_path, background_path)."""
    print("[2/6] Separating voice/music with Demucs...", flush=True)
    import torch
    import torchaudio
    from demucs import pretrained
    from demucs.apply import apply_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = pretrained.get_model("htdemucs")
    model.to(device)

    waveform, sr = torchaudio.load(audio_path)
    if waveform.shape[0] == 1:
        waveform = waveform.repeat(2, 1)
    waveform = waveform.to(device)

    sources = None
    # Chunking: segment=7s è lo standard della CLI demucs, overlap=0.25 copre il
    # taglio delle maschere. Evita OOM VRAM su video lunghi (>30 min / 8 GB GPU).
    apply_kwargs = {"device": device}
    try:
        import inspect
        sig = inspect.signature(apply_model)
        if "segment" in sig.parameters:
            apply_kwargs["segment"] = 7.0
        if "overlap" in sig.parameters:
            apply_kwargs["overlap"] = 0.25
    except (TypeError, ValueError):
        pass
    try:
        with torch.no_grad():
            sources = apply_model(model, waveform.unsqueeze(0), **apply_kwargs)[0]
        # htdemucs order: [drums, bass, other, vocals]
        vocals = sources[3].mean(0, keepdim=True).cpu()
        background = sources[:3].sum(0).mean(0, keepdim=True).cpu()
    finally:
        del model, waveform
        if sources is not None:
            del sources
        if device == "cuda":
            torch.cuda.empty_cache()

    vocals_16k = os.path.join(tmp_dir, "vocals_16k.wav")
    bg_path = os.path.join(tmp_dir, "background.wav")

    torchaudio.save(os.path.join(tmp_dir, "vocals_raw.wav"), vocals, sr)
    torchaudio.save(bg_path, background, sr)

    _run_ffmpeg([
        "ffmpeg", "-y", "-i", os.path.join(tmp_dir, "vocals_raw.wav"),
        "-ar", "16000", "-ac", "1", vocals_16k
    ], step="resample vocals")

    print(f"     → Vocals (16kHz): {vocals_16k}", flush=True)
    print(f"     → Background: {bg_path}", flush=True)
    return vocals_16k, bg_path


def transcribe(audio_path: str, model_name: str, lang_source: str) -> tuple[list[dict], str]:
    import torch
    from faster_whisper import WhisperModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    print(f"[3/6] Transcribing with faster-Whisper (model={model_name}, device={device})...", flush=True)

    try:
        model = WhisperModel(model_name, device=device, compute_type=compute)
    except Exception as e:
        if device == "cuda":
            print(f"     ! CUDA unavailable ({e}), falling back to CPU...", flush=True)
            device, compute = "cpu", "int8"
            model = WhisperModel(model_name, device=device, compute_type=compute)
        else:
            raise
    lang = None if lang_source == "auto" else lang_source

    def _run_transcribe(dev, cmp):
        nonlocal model
        if dev != device:
            del model
            model = WhisperModel(model_name, device=dev, compute_type=cmp)
        segments, info = model.transcribe(
            audio_path,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"threshold": 0.3, "min_silence_duration_ms": 300},
            condition_on_previous_text=False,
            repetition_penalty=1.3,
            no_repeat_ngram_size=3,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            temperature=0,
        )
        out = []
        prev_text = None
        for s in segments:
            text = s.text.strip()
            if text and text != prev_text:
                out.append({"start": s.start, "end": s.end, "text": text})
                prev_text = text
        return out, info

    try:
        try:
            result, info = _run_transcribe(device, compute)
        except RuntimeError as e:
            if device == "cuda" and ("libcublas" in str(e) or "CUDA" in str(e) or "cuda" in str(e).lower()):
                print(f"     ! CUDA error during inference ({e}), retrying on CPU...", flush=True)
                result, info = _run_transcribe("cpu", "int8")
                device = "cpu"
            else:
                raise
    finally:
        del model
        try:
            import torch as _t
            if device == "cuda":
                _t.cuda.empty_cache()
        except Exception:
            pass
    detected = info.language or lang_source
    print(f"     → {len(result)} segments | detected language: {detected}", flush=True)
    return result, detected


def _windows_known_videos_dir() -> Path | None:
    """Resolve the real 'Videos' Known Folder on Windows via Shell32.

    Returns the actual filesystem path even when the user has redirected
    the Videos library to another drive (Properties → Location → Move).
    ``Path.home() / "Videos"`` is wrong in that case because it always
    points at ``%USERPROFILE%\\Videos`` regardless of the redirection.

    Uses ctypes (stdlib) against ``SHGetKnownFolderPath`` with
    ``FOLDERID_Videos = {18989B1D-99B5-455B-841C-AB7C74E4DDFC}`` — the
    Shell32 API recommended since Windows Vista (SHGetFolderPath is
    deprecated). No pywin32 dependency is added: pulling pywin32 just for
    one Known Folder lookup would bloat the Windows installer by ~9 MB and
    complicate multi-user system-wide installs, which is not justified
    for an edge case (user-relocated Videos folder).

    Returns None on any failure so the caller can fall back safely.
    """
    if not sys.platform.startswith("win"):
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # FOLDERID_Videos = {18989B1D-99B5-455B-841C-AB7C74E4DDFC}
        folderid_videos = _GUID(
            0x18989B1D, 0x99B5, 0x455B,
            (ctypes.c_ubyte * 8)(0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC),
        )
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        SHGetKnownFolderPath.restype = ctypes.c_long  # HRESULT
        out = ctypes.c_wchar_p()
        hr = SHGetKnownFolderPath(ctypes.byref(folderid_videos), 0, None,
                                  ctypes.byref(out))
        if hr == 0 and out.value:
            path_str = out.value
            # CoTaskMemFree the buffer returned by SHGetKnownFolderPath
            ctypes.windll.ole32.CoTaskMemFree(out)
            return Path(path_str)
    except Exception:
        # ctypes failure, ancient Windows, sandboxed Python — all fall back.
        return None
    return None


def _default_videos_dir() -> Path:
    """User's preferred 'Videos' folder, honouring XDG / Known Folders.

    - Linux: query ``xdg-user-dir VIDEOS`` so a localised system (``~/Video``
      on Italian, ``~/视频`` on zh_CN, ``~/Filme`` on German, …) saves there
      instead of a parallel English-named ``~/Videos`` directory.
    - macOS: the canonical folder is ``~/Movies``; use it when present.
    - Windows: use Shell32 ``SHGetKnownFolderPath(FOLDERID_Videos)`` so we
      follow the real location even when the user has redirected the Videos
      library to another drive (e.g. ``D:\\Media``). Fall back to
      ``%USERPROFILE%\\Videos`` if the Shell32 call fails.
    """
    if sys.platform.startswith("linux"):
        with contextlib.suppress(FileNotFoundError,
                                 subprocess.CalledProcessError,
                                 subprocess.TimeoutExpired):
            out = subprocess.run(
                ["xdg-user-dir", "VIDEOS"],
                capture_output=True, text=True, check=True, timeout=2,
            ).stdout.strip()
            if out:
                return Path(out)
    if sys.platform == "darwin":
        movies = Path.home() / "Movies"
        if movies.exists():
            return movies
    if sys.platform.startswith("win"):
        kf = _windows_known_videos_dir()
        if kf is not None:
            return kf
    return Path.home() / "Videos"


# Punteggiatura forte di fine-frase — ASCII + CJK full-width + interrogativo arabo.
# Usata da _split_on_punctuation per riallineare i segmenti Whisper a confini
# sintattici naturali, anche in cinese/giapponese/arabo.
_END_PUNCT_CHARS = r".?!;。？！；؟"
_END_PUNCT_SET = frozenset(_END_PUNCT_CHARS)


def _split_on_punctuation(
    segments: list[dict],
    min_duration: float = 1.0,
) -> list[dict]:
    """Re-splits each Whisper segment su punteggiatura forte (. ? ! ; 。 ？ ！ ； ؟),
    opzionalmente seguita da whitespace. Timestamps riproporzionati sul numero
    di caratteri. Non splitta sulle virgole. Non produce sotto-segmenti di
    durata <min_duration. Preserva 'speaker' se presente.

    Il lookahead è `\\S` (non spazio): così funziona anche per script che non
    separano le frasi con uno spazio (cinese, giapponese). Per le lingue
    latine il filtro "uppercase/digit" sul char successivo conserva il
    comportamento precedente; per CJK/arabo qualunque char non-punct è
    considerato un boundary valido (non hanno case distinction).

    Riduce hallucinations XTTS dando frasi complete invece di tagli mid-sentence.
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

        # Costruisce lista di candidate cut positions.
        cuts: list[int] = []
        for m in pattern.finditer(text):
            next_idx = m.end()
            if next_idx < len(text):
                next_ch = text[next_idx]
                ws_between = m.group(2)  # whitespace consumed between punct and next_ch
                # Latin scripts: richiede (whitespace obbligatorio) AND
                # (maiuscola/cifra) per non splittare su abbreviazioni
                # ("U.S.", "e.g.", "p.m."), dove dopo il punto c'è zero
                # whitespace prima della lettera successiva. Questo replica
                # il vecchio comportamento `\\s+` per lo script latino.
                # Non-latin (CJK, arabo, …): qualunque char non-punct va
                # bene anche senza whitespace, perché queste lingue non
                # hanno case distinction e spesso non separano frasi con
                # spazio (giapponese, cinese).
                is_latin = next_ch.isascii() and next_ch.isalpha()
                # Gate non-latin su `not isascii()`: un digit/punct ASCII
                # dopo un punto ASCII appartiene sempre a testo latino
                # (decimali "3.14", quote chiuse "'yes.'") e non dev'essere
                # un cut-point. Solo i veri caratteri non-ASCII (CJK, arabo,
                # devanagari, ecc.) beneficiano del `\\s*` (whitespace
                # opzionale), perché queste lingue non separano le frasi
                # con spazio.
                if is_latin:
                    if ws_between and next_ch.isupper():
                        cuts.append(next_idx)
                elif not next_ch.isascii():
                    cuts.append(next_idx)
        if not cuts:
            out.append(seg)
            continue

        # Costruisce sotto-frasi e timestamp proporzionali ai caratteri.
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
                # Invece di creare un micro-segment inutile, merge col precedente
                # (se esiste) o ritorna al segmento originale se nessuno split ha senso.
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
    """Unisce segmenti consecutivi brevi (<min_duration) con il successivo se:
    - gap tra fine precedente e inizio successivo < max_gap
    - lo stesso speaker (se presente l'informazione)
    - la durata risultante non supera max_merged_duration
    Riduce hallucinations di XTTS e compressione atempo (meno slot piccoli con
    TTS inglese più lungo → meno atempo > 1.5 udibili).
    Parametri tarati 2026-04-24 dopo diagnostic su video IT→EN: 60% segmenti
    avevano ratio > 1.30 con i vecchi default (1.5/0.4/12.0).

    Default `max_gap=2.0` (bumpato 2026-04-27): tara permette di assorbire pause
    respiro umane normali (1-2s) che Whisper interpreta erroneamente come
    boundaries semantiche, evitando di spezzare frasi continue in frammenti.

    Secondo passaggio "orfani" (2026-04-27): dopo il merge primario, rileva
    segmenti molto corti (≤5 parole) che terminano con punteggiatura forte
    (.?!) e che sono frammenti di coda di una frase Whisper-spezzata su pausa
    respiro. Li forza nel precedente con vincoli più larghi (gap≤3s, dur
    totale≤25s) ma stesso speaker e tetto stretto per evitare megaframmenti.

    `aggressive=True` alza i bound (min 4.0, gap 1.5, max 30.0) per dare più
    spazio al TTS quando il target è molto più lungo del source (es. EN→IT):
    segmenti più lunghi hanno margine maggiore per assorbire l'espansione della
    lingua. Trade-off: picchi massimi più alti, compensati dallo speed XTTS
    auto-tuned più aggressivo. Nota: con il nuovo default max_gap=2.0,
    aggressive=True non bumpa più il gap (max(1.5, 2.0)=2.0) — comportamento
    voluto, conservativo per i caller esistenti.

    `verbose=True` stampa ogni orfano fuso (debugging della tara).
    """
    if aggressive:
        # Override forzato dei parametri: il chiamante può anche essere passato
        # i default (quando non sa che è un caso espanso). Qui bumpa sempre.
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
        # Guard: se i segmenti sono significativamente sovrapposti (diarization con
        # overlap) `gap` è molto negativo; in tal caso non fondere per evitare di
        # inglobare un turno di altro speaker o un overlap spurio.
        if (
            prev_dur < min_duration
            and gap <= max_gap
            and gap >= -0.5
            and same_speaker
            and new_dur <= max_merged_duration
        ):
            # guard: se segmenti overlapping preserva il max end
            prev["end"] = max(prev["end"], seg["end"])
            prev["text"] = (prev.get("text", "") + " " + seg.get("text", "")).strip()
            # preserva eventuali metadati per-word (Whisper word_timestamps)
            if "words" in prev or "words" in seg:
                prev["words"] = prev.get("words", []) + seg.get("words", [])
        else:
            merged.append(dict(seg))

    # Secondo passaggio: orfani (frammenti corti terminali che Whisper ha
    # staccato dalla frase precedente per via di una pausa respiro). Iteriamo
    # su `merged` e costruiamo `final` decidendo per ogni elemento se è un
    # orfano da fondere col precedente o un segmento autonomo. Più orfani
    # consecutivi vengono fusi tutti nel primo non-orfano (a catena su `prev`
    # in `final[-1]`).
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
from videotranslator.tts_text_sanitizer import (  # noqa: E402
    sanitize_for_tts as _sanitize_for_tts,
)
from videotranslator.metrics_csv import (  # noqa: E402
    dump_segment_metrics as _dump_segment_metrics,
)
from videotranslator.difficulty_detector import (  # noqa: E402
    classify_difficulty as _classify_difficulty,
    estimate_p90_ratio as _estimate_p90_ratio,
    format_difficulty_log as _format_difficulty_log,
)
from videotranslator.face_detector import (  # noqa: E402
    has_enough_faces as _has_enough_faces,
)


# ── Ollama LLM translation (v2.0) ──────────────────────────────────────────
# Mapping da codici ISO a nomi umani: il prompt LLM è molto più robusto se
# riceve "English"/"Italian" invece di "en"/"it". Segue lo stesso set di
# LANGUAGES + codici sorgente whisper comuni; mancanze cadono sul code raw
# (gli LLM moderni lo capiscono comunque, con meno accuracy).
_OLLAMA_LANG_NAMES: dict[str, str] = {
    "auto": "auto-detected",
    "ar": "Arabic", "cs": "Czech", "da": "Danish", "de": "German",
    "el": "Greek", "en": "English", "es": "Spanish", "fi": "Finnish",
    "fr": "French", "hi": "Hindi", "hu": "Hungarian", "id": "Indonesian",
    "it": "Italian", "ja": "Japanese", "ko": "Korean", "nl": "Dutch",
    "no": "Norwegian", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian",
    "ru": "Russian", "sv": "Swedish", "tr": "Turkish", "uk": "Ukrainian",
    "vi": "Vietnamese", "zh": "Chinese", "zh-cn": "Chinese", "zh-CN": "Chinese",
}


def _ollama_lang_name(code: str) -> str:
    if not code:
        return "English"
    return _OLLAMA_LANG_NAMES.get(code, _OLLAMA_LANG_NAMES.get(code.lower(), code))


def _ollama_num_predict_for_segment(
    text: str,
    is_qwen3: bool,
    thinking: bool,
    retry: int = 0,
) -> int:
    """Token budget for one Ollama segment.

    Qwen3 thinking can spend thousands of tokens in chain-of-thought before it
    emits the final answer. If ``num_predict`` is exhausted inside ``<think>``,
    `_ollama_strip_preamble()` correctly strips the orphan reasoning block and
    returns an empty string. Keep thinking enabled, but give it a larger budget
    and one retry with doubled budget before falling back.
    """
    num_predict = max(64, len(text) * 2 // 4 * 2)
    if is_qwen3 and thinking:
        num_predict = max(4096, num_predict * 20)
    if retry > 0:
        # Qwen3 thinking on dense segments (e.g. qwen3:14b on long sentences)
        # can blow past 8192 tokens of chain-of-thought; observed in production
        # 2026-04-28 with seg #24. Quadruple the retry budget instead of just
        # doubling so the second attempt has a real chance to finish.
        if is_qwen3 and thinking:
            num_predict *= 4 ** retry
        else:
            num_predict *= 2 ** retry
    return num_predict


def _ollama_health_check(api_url: str, model: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Verifica che Ollama sia raggiungibile e che il modello richiesto sia
    presente. Ritorna (ok, message). `message` è "" se ok, altrimenti è
    human-readable (es. "Ollama non raggiungibile: ConnectionError", o
    "Model qwen3:8b not installed").

    Non solleva eccezioni — il chiamante gestisce il fallback.
    """
    import requests
    base = api_url.rstrip("/")
    try:
        r = requests.get(f"{base}/api/tags", timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        return False, f"Ollama not reachable at {base} ({e.__class__.__name__}: {e})"
    except Exception as e:
        return False, f"Ollama returned invalid JSON at {base} ({e.__class__.__name__}: {e})"

    models = [m.get("name", "") for m in data.get("models", [])]
    # Ollama tag naming: `qwen2.5:7b-instruct` vs `qwen2.5:7b-instruct-q4_K_M`.
    # Accettiamo match esatto o prefix+":".
    target = model.strip()
    if target in models:
        return True, ""
    # Match per prefix (es. "qwen2.5:7b-instruct" matcha "qwen2.5:7b-instruct-q4_K_M")
    for m in models:
        if m.startswith(target + "-") or m.split(":")[0] == target.split(":")[0]:
            # Non è match esatto, ma stesso base model → accept con warning
            return True, ""
    available = ", ".join(models[:5]) if models else "none"
    return False, (
        f"Model '{target}' not installed in Ollama. Available: {available}. "
        f"Install with: ollama pull {target}"
    )


def _ollama_strip_preamble(text: str) -> str:
    """Rimuove artefatti tipici della risposta LLM per evitare che XTTS
    sintetizzi preamboli/disclaimer/note come audio (causa outlier atempo).

    Pipeline di pulizia (ordine critico):
      0. Qwen3 chain-of-thought: blocchi <think>/<thinking>/<reasoning> chiusi
         o orfani (output troncato). Devono morire PRIMA di tutto: contengono
         sintassi LLM-specifica che potrebbe matchare i pattern dei passi
         successivi e generare residui sporchi.
      1. Blocchi markdown code ```...``` (alcuni modelli wrappano l'output).
      2. Marcatori grassetto/corsivo **x** *x* ***x***.
      3. Preamble multi-lingua ("Ecco la traduzione:", "Here's the translation:",
         "Sure!", 好的/这是/翻译, ecc.) — case-insensitive, multiline.
      4. Commentary note tra parentesi tonde con parole chiave tipiche di
         self-commentary del modello (kept natural, fits within, ho mantenuto…).
         Parentesi legittime del testo originale NON sono toccate.
      5. Note tra parentesi quadre [note: ...], [spoken, ...].
      6. Righe "Note: ...", "Nota: ...", "N.B. ..." su riga isolata.
      7. Virgolette esterne "..." '...' «...» „…” “…”.
      8. Collasso whitespace/newline multipli → singolo spazio (evita pause
         lunghe durante la sintesi XTTS).
    """
    if not text:
        return ""
    import re as _re
    t = text.strip()

    # 0. Qwen3 chain-of-thought: rimuovi blocchi <think>...</think> che
    #    possono arrivare se /no_think è stato ignorato (es. fine-tuning
    #    Qwen3 che bypassa il toggle, o versione vecchia di Ollama che
    #    ignora `think:false`). Cattura sia tag standard che varianti
    #    comuni (<thinking>, <reasoning>) usate da derivati Qwen3.
    THINK_BLOCK_RE = _re.compile(
        r"<\s*(think|thinking|reasoning)\s*>[\s\S]*?<\s*/\s*\1\s*>",
        flags=_re.IGNORECASE,
    )
    t = THINK_BLOCK_RE.sub("", t)
    # 0b. Tag aperti senza chiusura (output troncato per num_predict raggiunto):
    #     se trovi <think> senza </think>, taglia tutto fino al doppio newline
    #     o a fine stringa. Evita di consegnare a XTTS un blocco di reasoning
    #     a metà.
    ORPHAN_THINK_RE = _re.compile(
        r"<\s*(think|thinking|reasoning)\s*>[\s\S]*?(?=\n\n|$)",
        flags=_re.IGNORECASE,
    )
    t = ORPHAN_THINK_RE.sub("", t)
    t = t.strip()

    # 1. Unwrap blocchi markdown code ```...``` conservando il contenuto.
    #    Alcuni modelli wrappano il testo tradotto in un code fence.
    t = _re.sub(r"```[a-zA-Z0-9]*\n?([\s\S]*?)```", r"\1", t)
    # 2. Rimuovi marcatori markdown grassetto/corsivo (conserva il contenuto)
    t = _re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", t)
    # 3. Preamble multi-lingua (IT, EN, FR, ES, DE, ZH). Applichiamo i pattern
    #    in loop fixed-point (max 6 passate) così prefissi concatenati come
    #    "Sure! Here's the translation:" o "好的这是翻译：" vengono mangiati in
    #    sequenza. Ogni pattern termina con `\s*` / `:?\s*` per attaccarsi al
    #    successivo senza spazi residui.
    PREAMBLE_PATTERNS = [
        # EN/IT "Here's the translation:" — con varianti "concisa", "tradotta"
        r"^(?:here'?s?|this is|the|la|le|il)\s+(?:the\s+)?(?:concise\s+)?translation(?:\s+(?:concisa|per\s+\S+|tradotta))?\s*[:.\-]?\s*",
        # IT "Ecco la/il traduzione [concisa/per doppiaggio/tradotta]:"
        r"^ecco(?:\s+(?:la|il))?(?:\s+traduzione)?(?:\s+(?:concisa|per\s+\S+|tradotta))?\s*[:.\-]?\s*",
        # Singolo token "Traduzione:" / "Translation:" / "Übersetzung:" / "Traducción:"
        r"^(?:traduzione|translated|translation|übersetzung|traducción|traduction)\s*[:.\-]?\s*",
        # Acknowledgment: "Ok,", "Sure!", "Certainly.", "Certo!", "Bien sûr,"
        r"^(?:ok|sure|certainly|of course|certo|bien sûr)\s*[,.!]?\s*",
        # Cinese: "好的" (OK), "这是" (this is), "翻译：" (translation:)
        r"^好的\s*[，,:：]?\s*",
        r"^这是\s*[，,:：]?\s*",
        r"^翻译\s*[：:]\s*",
        # "Per favore" (acknowledgment) — NOTA: "N.B.", "Note:", "Nota bene:",
        # "Please note:" sono gestiti al step 6 come riga intera (mangiano
        # tutta la frase di disclaimer, non solo il prefisso).
        r"^per favore\s*[,:.\-]?\s*",
    ]
    for _ in range(6):
        prev = t
        for pat in PREAMBLE_PATTERNS:
            t = _re.sub(pat, "", t, count=1, flags=_re.IGNORECASE | _re.MULTILINE)
        if t == prev:
            break
    # 4. Note/disclaimer tra parentesi tonde con keyword di commentary.
    #    Volutamente conservativo: evitiamo false positive su parentesi di
    #    contenuto (es. "(2020)", "(diretto da Nolan)"). Match non-greedy.
    COMMENTARY_RE = _re.compile(
        r"\(\s*(?:note|n\.?\s*b\.?|nota|hint|tip|keeping|"
        r"kept|fits?\s+(?:well\s+)?within|target\s+reading|"
        r"natural|spoken|concise|shortened|translated|nota\s+bene|"
        r"ho\s+mantenuto|mantenendo|per\s+rimanere)"
        r"[^)]*?\)",
        flags=_re.IGNORECASE,
    )
    t = COMMENTARY_RE.sub("", t)
    # 5. Note tra parentesi quadre [note:...], [spoken, natural], ecc.
    BRACKET_NOTE_RE = _re.compile(
        r"\[\s*(?:note|nota|comment|spoken|dubbing)[^\]]*?\]",
        flags=_re.IGNORECASE,
    )
    t = BRACKET_NOTE_RE.sub("", t)
    # 6. Riga isolata "Note: ..." / "Nota: ..." / "Disclaimer: ..." / "N.B. ..."
    #    Mangia anche il newline precedente per non lasciare doppi spazi dopo
    #    il whitespace collapse (step 8).
    FINAL_NOTE_LINE_RE = _re.compile(
        r"(?:^|\n)[ \t]*"
        r"(?:note|nota|nota\s+bene|n\.?\s*b\.?|please\s+note|disclaimer|observation)"
        r"\s*[:\-]\s*[^\n]*",
        flags=_re.IGNORECASE,
    )
    t = FINAL_NOTE_LINE_RE.sub("", t)
    # 7. Virgolette esterne a coppie (open/close). Prima applicazione: un loop
    #    perché potremmo avere layer multipli tipo "\"«testo»\"".
    QUOTE_PAIRS = [
        ("\"", "\""), ("'", "'"),
        ("«", "»"), ("“", "”"), ("„", "”"), ("„", "“"),
    ]
    for _ in range(3):
        t = t.strip()
        peeled = False
        for open_q, close_q in QUOTE_PAIRS:
            if len(t) > len(open_q) + len(close_q) and t.startswith(open_q) and t.endswith(close_q):
                t = t[len(open_q):-len(close_q)]
                peeled = True
                break
        if not peeled:
            break
    # 8. Collassa whitespace multipli e newline → spazio singolo (evita pause
    #    lunghe durante la sintesi XTTS)
    t = _re.sub(r"\s+", " ", t)

    # 9. Punteggiatura "isolata" / orfana che XTTS pronuncerebbe letteralmente
    #    come "punto", "virgola", o emetterebbe colpi acustici secchi udibili
    #    ("dice il punto alla fine"). Casi reali osservati su output Qwen3:
    #      ".  Buongiorno a tutti."   (preamble strippato che lascia il "." iniziale)
    #      "Buongiorno a tutti . . ."  (Qwen ripete punteggiatura di chiusura)
    #      ".\nBuongiorno"             (riga vuota con sola punteggiatura)
    #      "Buongiorno , a tutti"      (spazio prima della virgola)
    #
    # Sequence: leading isolated punct → multiple consecutive marks → space
    # before punct → final tidy. Eseguito DOPO il collasso whitespace così
    # opera su una stringa già normalizzata ai singoli spazi.
    LEADING_PUNCT_RE   = _re.compile(r"^[\s.,;:!?\-–—…]+")
    REPEATED_PUNCT_RE  = _re.compile(r"([.,;:!?])(?:\s*\1)+")
    SPACE_BEFORE_RE    = _re.compile(r"\s+([.,;:!?])")
    DANGLING_PUNCT_RE  = _re.compile(r"\s+[.,;:!?\-–—…]+\s*$")  # tail isolato
    t = LEADING_PUNCT_RE.sub("", t)
    t = REPEATED_PUNCT_RE.sub(r"\1", t)
    t = SPACE_BEFORE_RE.sub(r"\1", t)
    t = DANGLING_PUNCT_RE.sub(".", t)  # se la fine ha punct orfano, lascia un solo "."

    return t.strip()


# ── Ollama auto-setup (v2.0.1) ─────────────────────────────────────────────
# Obiettivo: zero manual setup per l'utente finale. Stessa strategia già usata
# per ffmpeg (download on-demand) e Git for Windows (installer auto). Le
# funzioni qui sotto sono puri helper — nessun Tk, nessuno stato globale:
# accettano un log_cb opzionale per streamare output alla GUI, e registrano
# i subprocess nel registry globale così `_on_close` li può terminare.

def _ollama_find_binary() -> str | None:
    """Ritorna il path all'eseguibile `ollama` se trovato, altrimenti None.

    Linux/macOS: `shutil.which`. Windows: `shutil.which` + fallback sui path
    di default dell'installer ufficiale (`%LOCALAPPDATA%\\Programs\\Ollama` e
    `%ProgramFiles%\\Ollama`). Necessario perché su Windows subito dopo
    un'install silent il PATH del processo corrente non è ancora aggiornato.
    """
    p = shutil.which("ollama")
    if p:
        return p
    if sys.platform.startswith("win"):
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            # Installer ufficiale Ollama (per-user install)
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe",
            # Installer ufficiale system-wide (raro, richiede admin)
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Ollama" / "ollama.exe",
            # winget install Ollama.Ollama → symlink in WinGet/Links (Win11
            # default in PATH, Win10 spesso no — quindi serve fallback esplicito)
            Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ollama.exe",
        ]
        for c in candidates:
            try:
                if c.is_file():
                    return str(c)
            except OSError:
                continue
    return None


def _ollama_is_daemon_running(api_url: str, timeout: float = 2.0) -> bool:
    """Probe `/api/tags` con timeout corto. True se il daemon risponde 2xx."""
    import requests
    base = api_url.rstrip("/")
    try:
        r = requests.get(f"{base}/api/tags", timeout=timeout)
        return r.status_code < 400
    except Exception:
        return False


def _ollama_wait_for_daemon(api_url: str, wait_seconds: float = 12.0,
                            poll_interval: float = 1.0) -> bool:
    """Polla `_ollama_is_daemon_running` per `wait_seconds`. True se risponde.

    Usato dopo l'install di Ollama Desktop su Windows: l'installer avvia il
    proprio daemon embedded ma con 5-10s di delay rispetto al completamento
    dell'install stesso. Senza questa attesa il nostro fallback `ollama serve`
    parte e fallisce con port-already-in-use.
    """
    import time
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if _ollama_is_daemon_running(api_url, timeout=1.5):
            return True
        time.sleep(poll_interval)
    return False


def _ollama_start_daemon(
    binary: str,
    api_url: str = "http://localhost:11434",
    wait_seconds: float = 15.0,
    log_cb=None,
) -> tuple[bool, str]:
    """Avvia `ollama serve` detached e aspetta che `/api/tags` risponda.

    Ritorna (ok, message). `message` è il path al log tempfile su fallimento,
    stringa vuota su successo. Il subprocess è registrato in
    `_active_subprocesses` per permettere a `_on_close` di terminarlo.
    """
    log = log_cb or (lambda s: None)

    # Log file per debug: su Windows senza console, altrimenti perdiamo lo
    # stderr del daemon se parte e poi crasha.
    log_file = tempfile.NamedTemporaryFile(
        prefix="ollama-serve-", suffix=".log", delete=False, mode="w",
        encoding="utf-8",
    )
    log_path = log_file.name
    log_file.close()
    fh = open(log_path, "w", encoding="utf-8")

    # start_new_session/CREATE_NEW_PROCESS_GROUP: detach dal main process
    # così la chiusura della GUI non killa il daemon (a meno che _on_close
    # lo faccia esplicitamente via registry).
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": fh,
        "stderr": subprocess.STDOUT,
    }
    if sys.platform.startswith("win"):
        # CREATE_NEW_PROCESS_GROUP = 0x00000200. Su Windows non esiste
        # start_new_session; usiamo il flag creationflags.
        kwargs["creationflags"] = 0x00000200
    else:
        kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen([binary, "serve"], **kwargs)
    except Exception as e:
        fh.close()
        return False, f"Failed to spawn `ollama serve`: {e} (log: {log_path})"

    _register_subprocess(proc)

    # Polling: aspetta wait_seconds al massimo. Exit-code check: se il daemon
    # muore subito (porta già occupata, config rotta), smettiamo di attendere.
    import time
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            # Daemon morto prima di rispondere
            fh.close()
            _unregister_subprocess(proc)
            try:
                tail = Path(log_path).read_text(encoding="utf-8", errors="replace")[-500:]
            except Exception:
                tail = "(log unreadable)"
            log(f"     ! ollama serve exited early (rc={proc.returncode}): {tail}\n")
            return False, f"ollama serve exited (rc={proc.returncode}). Log: {log_path}"
        if _ollama_is_daemon_running(api_url, timeout=1.5):
            log(f"     [+] Ollama daemon attivo su {api_url}\n")
            # NB: il fh resta aperto intenzionalmente — il daemon scrive
            # lì per tutta la sessione. Sarà chiuso quando proc termina.
            return True, ""
        time.sleep(0.5)

    # Timeout
    log(f"     ! Ollama daemon non ha risposto entro {wait_seconds:.0f}s (log: {log_path})\n")
    return False, f"Daemon did not become ready within {wait_seconds:.0f}s. Log: {log_path}"


def _ollama_install_linux(log_cb=None, timeout_s: int = 300) -> tuple[bool, str]:
    """Installa Ollama via lo script ufficiale `curl -fsSL … | sh`.

    Richiede sudo per scrivere in /usr/local/bin. Se sudo non è presente,
    ritorna messaggio actionable invece di appendere a silenzio.
    """
    log = log_cb or (lambda s: None)

    if not shutil.which("curl"):
        return False, (
            "curl non trovato. Installa curl (es. `sudo apt install curl`) "
            "e riprova, oppure installa Ollama manualmente da https://ollama.com/download"
        )

    # Lo script ufficiale richiede privilegi root. Usiamo pkexec o sudo.
    prefixes: list[list[str]] = []
    if shutil.which("pkexec"):
        prefixes.append(["pkexec", "sh", "-c"])
    if shutil.which("sudo"):
        prefixes.append(["sudo", "sh", "-c"])
    prefixes.append(["sh", "-c"])  # root-less fallback (funzionerà solo se root)

    install_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
    last_err = ""
    for prefix in prefixes:
        cmd = prefix + [install_cmd]
        log(f"     Running: {' '.join(prefix)} <install.sh>\n")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError as e:
            last_err = f"{e.__class__.__name__}: {e}"
            continue

        _register_subprocess(proc)
        watchdog = threading.Timer(timeout_s, proc.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log(f"     {line}\n")
            proc.wait(timeout=30)
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill(); proc.wait(timeout=10)
        finally:
            watchdog.cancel()
            _unregister_subprocess(proc)

        if proc.returncode == 0:
            return True, ""
        last_err = f"exit {proc.returncode} (prefix={prefix[0]})"

    return False, (
        f"Ollama install script failed ({last_err}). "
        f"Installa manualmente: curl -fsSL https://ollama.com/install.sh | sh"
    )


def _ollama_install_windows(log_cb=None, timeout_s: int = 600) -> tuple[bool, str]:
    """Scarica OllamaSetup.exe e lo lancia in modalità completamente silent.

    L'installer di Ollama è basato su Inno Setup. Usiamo il set di flag
    `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL`:
      - `/VERYSILENT`: niente wizard, niente progress UI (`/SILENT` da solo
        mostrerebbe ancora una progress bar che può richiedere input);
      - `/SUPPRESSMSGBOXES`: sopprime le message box di default;
      - `/NORESTART`: non riavviare la macchina a fine install;
      - `/NOCANCEL`: l'utente non può abortire via tasto.
    Senza questo set completo il subprocess può bloccarsi sull'attesa di
    input utente fino allo scadere del timeout.

    Post-install, aggiorniamo il PATH del processo corrente aggiungendo il
    path di default dell'installer, così `_ollama_find_binary` funziona
    senza dover riavviare la GUI.
    """
    log = log_cb or (lambda s: None)
    url = "https://ollama.com/download/OllamaSetup.exe"
    setup_path = Path(tempfile.gettempdir()) / "OllamaSetup.exe"

    log(f"     Scaricando Ollama (~1 GB) da {url}...\n")
    try:
        from urllib.request import Request, urlopen
        req = Request(url, headers={"User-Agent": "VideoTranslatorAI/2.0"})
        downloaded = 0
        last_pct = -1
        with urlopen(req, timeout=120) as r, open(setup_path, "wb") as out:
            total = int(r.headers.get("Content-Length") or 0)
            chunk = 256 * 1024
            while True:
                buf = r.read(chunk)
                if not buf:
                    break
                out.write(buf)
                downloaded += len(buf)
                if total > 0:
                    pct = min(100, downloaded * 100 // total)
                    # Log ogni 5% per non inondare la GUI
                    if pct // 5 != last_pct // 5:
                        log(f"     Download... {pct}%\n")
                        last_pct = pct
    except Exception as e:
        with contextlib.suppress(Exception):
            setup_path.unlink(missing_ok=True)
        return False, f"Download fallito: {e}"

    log("     Avvio installer silent (richiede UAC)...\n")
    # Inno Setup silent install
    try:
        proc = subprocess.Popen(
            [str(setup_path),
             "/VERYSILENT", "/SUPPRESSMSGBOXES",
             "/NORESTART", "/NOCANCEL"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
    except Exception as e:
        return False, f"Impossibile lanciare installer: {e}"

    _register_subprocess(proc)
    watchdog = threading.Timer(timeout_s, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"     {line}\n")
        proc.wait(timeout=30)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill(); proc.wait(timeout=10)
    finally:
        watchdog.cancel()
        _unregister_subprocess(proc)
        with contextlib.suppress(Exception):
            setup_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        # rc=1223 = ERROR_CANCELLED su Windows (utente ha cliccato "No" sul
        # prompt UAC dell'installer Ollama). Il messaggio criptico "rc=1223"
        # è inutile per l'utente finale → tradurre in linguaggio umano.
        # rc=1602 = ERROR_INSTALL_USEREXIT (cancel volontario senza UAC).
        if proc.returncode in (1223, 1602):
            return False, (
                "Installazione annullata dall'utente (UAC negato o annullato). "
                "Riavvia la traduzione e accetta il prompt UAC, oppure scarica "
                "manualmente da https://ollama.com/download"
            )
        return False, (
            f"Installer exit rc={proc.returncode}. "
            f"Scarica e installa manualmente da https://ollama.com/download"
        )

    # Post-install: aggiorniamo PATH del processo corrente col path di default
    # dell'installer Ollama. Questo evita di dover riavviare la GUI.
    default_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
    if default_dir.is_dir():
        cur_path = os.environ.get("PATH", "")
        if str(default_dir) not in cur_path:
            os.environ["PATH"] = cur_path + os.pathsep + str(default_dir)
    return True, ""


def _ollama_install_macos(log_cb=None, timeout_s: int = 600) -> tuple[bool, str]:
    """Prova `brew install ollama` se Homebrew è presente, altrimenti messaggio
    manuale con link al .dmg. Non scarichiamo automaticamente il .dmg perché
    richiede interazione utente per il drag-and-drop.
    """
    log = log_cb or (lambda s: None)
    if shutil.which("brew"):
        log("     Installazione via Homebrew: brew install ollama\n")
        try:
            proc = subprocess.Popen(
                ["brew", "install", "ollama"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
        except Exception as e:
            return False, f"brew install fallito: {e}"
        _register_subprocess(proc)
        watchdog = threading.Timer(timeout_s, proc.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log(f"     {line}\n")
            proc.wait(timeout=30)
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill(); proc.wait(timeout=10)
        finally:
            watchdog.cancel()
            _unregister_subprocess(proc)
        if proc.returncode == 0:
            return True, ""
        return False, f"brew exit rc={proc.returncode}"

    return False, (
        "Homebrew non trovato. Installa Ollama manualmente scaricando il .dmg "
        "da https://ollama.com/download, poi riprova."
    )


def _ollama_install(log_cb=None) -> tuple[bool, str]:
    """Dispatch cross-platform dell'installazione di Ollama."""
    if sys.platform.startswith("win"):
        return _ollama_install_windows(log_cb=log_cb)
    if sys.platform == "darwin":
        return _ollama_install_macos(log_cb=log_cb)
    # Linux + altri Unix
    return _ollama_install_linux(log_cb=log_cb)


def _ollama_pull_model(
    model: str,
    binary: str | None = None,
    log_cb=None,
    timeout_s: int = 1200,
) -> tuple[bool, str]:
    """Esegue `ollama pull <model>` streamando l'output alla GUI.

    `timeout_s` è generoso (20 min default) perché i modelli sono grossi
    (~4 GB) e le connessioni possono essere lente. Il subprocess è registrato
    nel registry globale per la pulizia su _on_close.
    """
    log = log_cb or (lambda s: None)
    ollama_bin = binary or _ollama_find_binary()
    if not ollama_bin:
        return False, "ollama binary non trovato"

    log(f"     Scaricando modello {model} (può richiedere diversi minuti)...\n")
    # CREATE_NO_WINDOW (0x08000000) prevents Windows from popping a visible
    # console window for the ollama.exe child process (Go binary, console
    # subsystem). Without this the user sees a black cmd window pop up over
    # the GUI for the entire 5+ GB download. Linux/macOS ignore the flag.
    popen_kwargs = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    if sys.platform.startswith("win"):
        popen_kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen([ollama_bin, "pull", model], **popen_kwargs)
    except Exception as e:
        return False, f"Failed to spawn `ollama pull`: {e}"

    _register_subprocess(proc)
    watchdog = threading.Timer(timeout_s, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    # `ollama pull` uses \r to redraw progress 10x/sec, mixes spinner chars
    # (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) for unbounded ops like sha256 verify, AND emits ANSI
    # cursor-control escape sequences. Naive line capture produced thousands
    # of duplicate log entries. We need a STABLE key per logical state
    # (e.g. "pulling a3de86cd1c13:") that ignores the changing %/bytes,
    # otherwise consecutive progress ticks always look "different".
    import re
    import time as _time
    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    _ANSI_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    _PCT_RE = re.compile(r"(\d{1,3})%")
    # Stable-key extractors: collapse all variable parts (digits, units,
    # progress bar fill, etc.) so "pulling X: 5% ... 250 MB" and
    # "pulling X: 6% ... 300 MB" map to the same key.
    _STABLE_PREFIX = re.compile(
        r'^(pulling\s+[\w.\-]+:|verifying\s+[\w.\-]+\s+[\w.\-]+|'
        r'writing\s+manifest|pulling\s+manifest|success|removing\s+\w+)',
        re.IGNORECASE,
    )

    def _stable_key(s: str) -> str:
        m = _STABLE_PREFIX.match(s)
        return m.group(1).lower() if m else s

    last_key = ""
    last_pct_seen = -1
    last_log_t = 0.0
    try:
        for line in proc.stdout:
            # Strip ANSI escape codes that Ollama emits for cursor control.
            line = _ANSI_RE.sub('', line)
            # Ollama mixes \r and \n. Split on both to recover individual frames.
            for fragment in line.replace("\r", "\n").split("\n"):
                # Strip spinner chars + whitespace
                fragment = "".join(c for c in fragment if c not in _SPINNER).strip()
                if not fragment:
                    continue
                key = _stable_key(fragment)
                now = _time.monotonic()
                if key == last_key:
                    # Same logical state — throttle progress ticks to one
                    # log entry every 5% delta OR every 2 seconds OR at 100%.
                    m = _PCT_RE.search(fragment)
                    if m:
                        pct = int(m.group(1))
                        is_complete = pct == 100 and last_pct_seen != 100
                        if pct - last_pct_seen >= 5 or now - last_log_t >= 2.0 or is_complete:
                            log(f"     {fragment}\n")
                            last_pct_seen = pct
                            last_log_t = now
                    # else: pure spinner or post-100 duplicate, drop silently.
                    continue
                # New logical state → always log.
                log(f"     {fragment}\n")
                last_key = key
                last_log_t = now
                m = _PCT_RE.search(fragment)
                last_pct_seen = int(m.group(1)) if m else -1
        proc.wait(timeout=30)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill(); proc.wait(timeout=10)
    finally:
        watchdog.cancel()
        _unregister_subprocess(proc)

    if proc.returncode != 0:
        return False, f"ollama pull {model} failed (rc={proc.returncode})"
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# CosyVoice 2.0 helpers (v2.3) — additive engine alongside Coqui XTTS v2.
#
# Scelta di design: il PyPI ufficiale `cosyvoice` (Lucas Jin, community wrapper)
# è l'unico path pip-installabile oggi. Wrappa CosyVoice-300M-Instruct (1.x)
# e scarica i pesi via ModelScope al primo uso. CosyVoice 2.0 ufficiale
# (FunAudioLLM) richiede tuttora git clone + conda + WeTextProcessing — non
# fattibile per un installer mainstream. Quando uscirà la 2.x su PyPI, basta
# aggiornare _COSYVOICE_PIP_PKG e _cosyvoice_load_model più sotto.
#
# Per rilevare hallucination (problema strutturale di XTTS che ha motivato il
# v2.3) riusiamo lo stesso schema retry di v2.2: misura durata effettiva,
# confronto col predicted, retry una volta. CosyVoice ha tasso di drift molto
# più basso (~2% vs 5-15% di XTTS su long-form), ma il safety net resta.
# ─────────────────────────────────────────────────────────────────────────────

# Pacchetto pip da installare per la modalità auto-install. La singola riga di
# codice da aggiornare quando CosyVoice 2.0 ufficiale sarà su PyPI.
_COSYVOICE_PIP_PKG = "cosyvoice"

# Cache directory: il wrapper di Lucas usa "checkpoints/cosyvoice" relativo
# alla cwd, comportamento scomodo per una GUI che può avere cwd variabile.
# Lo forziamo sempre sotto la cache utente standard, cross-platform.
def _cosyvoice_cache_dir() -> Path:
    """Ritorna la directory dove tenere i pesi CosyVoice. Idempotente.

    - Linux/macOS: $XDG_CACHE_HOME/videotranslatorai/cosyvoice (default ~/.cache).
    - Windows:     %LOCALAPPDATA%\\VideoTranslatorAI\\cosyvoice.
    Creata on-demand. Se la creazione fallisce (es. permessi), fallback a
    tempfile.gettempdir() per non bloccare la pipeline.
    """
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "VideoTranslatorAI"
    else:
        base = Path(
            os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
        ) / "videotranslatorai"
    cache = base / "cosyvoice"
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache = Path(tempfile.gettempdir()) / "videotranslatorai_cosyvoice"
        cache.mkdir(parents=True, exist_ok=True)
    return cache


def _cosyvoice_is_installed() -> bool:
    """True se il pacchetto Python `cosyvoice` è importabile.

    Usa importlib.util.find_spec per evitare di importare effettivamente il
    modulo (che è pesante e farebbe partire il loading dei pesi).
    """
    try:
        return importlib.util.find_spec("cosyvoice") is not None
    except (ValueError, ModuleNotFoundError, ImportError):
        return False


def _cosyvoice_model_present(cache_dir: Path | None = None) -> bool:
    """True se il modello CosyVoice-300M-Instruct è già stato scaricato.

    Heuristic: cerca il file `llm.pt` (~600 MB) dentro la directory del modello.
    Se manca, il primo `tts_to_file` triggherà un download di ~1.7 GB via
    ModelScope. Vogliamo segnalarlo all'utente prima di lanciare la pipeline.
    """
    cache = cache_dir or _cosyvoice_cache_dir()
    # Il wrapper salva i modelli in CosyVoice-300M-Instruct/, dentro cache_dir.
    return (cache / "CosyVoice-300M-Instruct" / "llm.pt").exists()


def _cosyvoice_install(log_cb=None, timeout_s: int = 1800) -> tuple[bool, str]:
    """Installa il pacchetto CosyVoice via pip nel runtime corrente.

    Cross-platform via `--break-system-packages` (PEP 668 su Kali/Debian) +
    `--no-color` per output pulito nel log. Il timeout è generoso (30 min)
    perché trascina giù modelscope, onnxruntime-gpu e altre wheel pesanti.

    Ritorna (ok, message). `message` è "" su successo, descrizione errore su
    fallimento. Nota: questa è SOLO l'install del wrapper Python; il modello
    (~1.7 GB) viene scaricato al primo `tts_to_file`.
    """
    log = log_cb or (lambda s: None)
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--break-system-packages", "--no-color", _COSYVOICE_PIP_PKG,
    ]
    log(f"[*] pip install {_COSYVOICE_PIP_PKG} (può richiedere alcuni minuti)...\n")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True,
            encoding="utf-8", errors="replace",
        )
    except Exception as e:
        return False, f"Failed to spawn pip install: {e}"

    _register_subprocess(proc)
    # Watchdog timer: pip può stallare su mirror slow senza chiudere stdout.
    # Stessa pattern di _install_deps in GUI ma replicato qui per uso headless
    # (CLI / chiamate fuori dal Tk loop).
    timed_out = {"fired": False}

    def _on_timeout():
        timed_out["fired"] = True
        with contextlib.suppress(Exception):
            proc.kill()
            if proc.stdout is not None:
                proc.stdout.close()

    watchdog = threading.Timer(timeout_s, _on_timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"    {line}\n")
        with contextlib.suppress(Exception):
            proc.wait(timeout=30)
    except Exception as e:
        log(f"    ! pip install error: {e}\n")
    finally:
        watchdog.cancel()
        _unregister_subprocess(proc)

    if timed_out["fired"]:
        return False, f"pip install timed out after {timeout_s}s"
    if proc.returncode != 0:
        return False, f"pip install {_COSYVOICE_PIP_PKG} failed (rc={proc.returncode})"
    return True, ""


def _cosyvoice_download_model(cache_dir: Path | None = None, log_cb=None) -> tuple[bool, str]:
    """Scarica i pesi CosyVoice-300M-Instruct via ModelScope.

    Idempotente: se i file esistono già, ritorna subito True. La modalità
    "scarica tutti i checkpoint" è scelta intenzionale — il wrapper
    `CosyVoiceTTS(model_type='instruct')` carica il bundle Instruct ma le
    altre dipendenze condividono asset (es. CosyVoice-ttsfrd contiene il
    text-frontend per i numeri/abbreviazioni IT/EN).

    Se ModelScope non è raggiungibile (es. firewall sino), fallback su
    HuggingFace Hub usando lo stesso repo `iic/CosyVoice-300M-Instruct`.
    """
    log = log_cb or (lambda s: None)
    cache = cache_dir or _cosyvoice_cache_dir()
    target_dir = cache / "CosyVoice-300M-Instruct"
    # Idempotente: file marker presente = nulla da fare.
    if (target_dir / "llm.pt").exists():
        log(f"[+] CosyVoice model già presente in {target_dir}\n")
        return True, ""

    log(f"[*] Download CosyVoice-300M-Instruct (~1.7 GB) → {target_dir}...\n")
    # Tentativo 1: ModelScope (canale ufficiale dei modelli iic/*)
    try:
        from modelscope import snapshot_download  # type: ignore
        snapshot_download("iic/CosyVoice-300M-Instruct", local_dir=str(target_dir))
        log("[+] Download da ModelScope OK\n")
        return True, ""
    except Exception as e:
        log(f"    ! ModelScope download fallito ({e}), provo HuggingFace...\n")

    # Tentativo 2: HuggingFace Hub mirror
    try:
        from huggingface_hub import snapshot_download as hf_snapshot_download  # type: ignore
        hf_snapshot_download(repo_id="model-scope/CosyVoice-300M-Instruct", local_dir=str(target_dir))
        log("[+] Download da HuggingFace OK\n")
        return True, ""
    except Exception as e:
        return False, f"Sia ModelScope che HuggingFace hanno fallito: {e}"


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
) -> list[dict]:
    """Traduce i segmenti tramite Ollama locale usando un prompt slot-aware che
    impone concisione per il doppiaggio.

    Args:
        segments: lista di dict con chiavi `start`, `end`, `text`, opz `speaker`.
        source_lang: codice ISO della lingua sorgente (es. "en"). "auto" accettato.
        target_lang: codice ISO della lingua target (es. "it").
        model: nome del modello Ollama (default "qwen3:8b"). Per Qwen3 il
               thinking mode viene disabilitato automaticamente (think=False
               + suffisso /no_think) per evitare blocchi <think>...</think>
               che XTTS pronuncerebbe come outlier.
        api_url: base URL del daemon Ollama (default "http://localhost:11434").
        slot_aware: se True, include il reading time nel prompt (consigliato).
        batch_size: numero di segmenti da accorpare in un singolo prompt. 1 = safe
                    (parsing banale), >1 = più veloce ma parsing brittle. Per
                    v2.0 teniamo 1 di default e lasciamo il parametro come hook
                    futuro (il codice supporta >1 con fallback automatico su
                    per-segment se il parsing dell'output fallisce).
        fallback_fn: callable opzionale `(seg) -> str` invocata per il singolo
                     segmento quando Ollama solleva. Se None, il testo sorgente
                     è usato as-is (degrada a "no translation").

    Ritorna la lista di segmenti con `text_src` e `text_tgt` popolati, identica
    nello schema a quella prodotta da `translate_segments` per gli altri engine.
    """
    import re as _re
    import requests
    base = api_url.rstrip("/")
    src_name = _ollama_lang_name(source_lang)
    tgt_name = _ollama_lang_name(target_lang)

    # Health check upfront — così se Ollama è down solleviamo subito invece di
    # fallire 300 volte nel loop.
    ok, msg = _ollama_health_check(base, model)
    if not ok:
        raise RuntimeError(msg)

    print(f"     → Ollama ready ({model} @ {base}, slot_aware={slot_aware}, batch={batch_size})", flush=True)

    # Detect Qwen3 family — needs thinking mode disabled to avoid <think>
    # blocks in output that XTTS would pronounce as audible chain-of-thought.
    # Sampling parameters tuned per Qwen team's official recommendations:
    #   - Qwen3 non-thinking: T=0.7, TopP=0.8, TopK=20 (avoids endless loops)
    #   - Qwen2.x and others: stricter T=0.3, TopP=0.9 for translation
    # Doppia protezione: payload `think:false` (Ollama API ≥2025) +
    # suffix `/no_think` nel prompt (vince anche su versioni vecchie).
    is_qwen3 = model.lower().startswith("qwen3")
    # `thinking` è significativo solo per Qwen3 (gli altri modelli ignorano il
    # flag). Per modelli non-Qwen3 il log resta "standard"; per Qwen3 riflette
    # la scelta utente — thinking=True abilita la deliberazione step-by-step
    # (~5x più lento, riduce errori idiomi/grammatica), False mantiene il
    # comportamento veloce con prompt /no_think.
    if is_qwen3:
        _mode_label = f"Qwen3 {'thinking' if thinking else 'non-thinking'} (think={thinking})"
    else:
        _mode_label = "standard"
    print(f"     → Mode: {_mode_label}", flush=True)

    # Debug opt-in: se settato, logga sorgente + output finale per ogni segmento.
    # Utile per indagare residui di preamble/commentary senza re-runnare pipeline.
    _ollama_debug = os.environ.get("VIDEOTRANSLATORAI_OLLAMA_DEBUG") == "1"

    # Length safeguard: calcoliamo una volta sola il fattore expansion atteso
    # (target/source) dalla tabella LANG_EXPANSION. Usato per stimare la
    # lunghezza massima plausibile per ogni segmento. Cap 1.8× = margine
    # permissivo per LLM verbose ma catturante per outlier da commentary.
    _src_key = (source_lang or "").split("-")[0] if source_lang != "auto" else ""
    _tgt_key = target_lang.split("-")[0] if target_lang else ""
    _exp_tgt = LANG_EXPANSION.get(target_lang, LANG_EXPANSION.get(_tgt_key, 1.0))
    _exp_src = LANG_EXPANSION.get(source_lang, LANG_EXPANSION.get(_src_key, 1.0)) or 1.0
    _expansion_factor = _exp_tgt / _exp_src if _exp_src > 0 else 1.0

    # TASK 2G: pre-flight difficulty estimate. Pure-text heuristic that
    # predicts the P90 of pre_stretch_ratio BEFORE TTS+stretch. Lets the
    # user know upfront whether the dub will be fluent (easy), partially
    # accelerated (medium) or audibly accelerated on most segments (hard).
    # Informational only — pipeline runs to completion regardless.
    _est_p90 = _estimate_p90_ratio(segments, target_lang, _expansion_factor)
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
    # TASK 2C-1: re-prompt iterativo per length control. `rewrite_attempts`
    # conta i segmenti per cui la prima traduzione era oltre budget e abbiamo
    # chiesto un retry "rewrite shorter". `rewrite_success` conta quanti di
    # quei retry hanno effettivamente prodotto una versione più corta.
    rewrite_attempts = 0
    rewrite_success = 0

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
        # CONTEXT block injecting prev_text/next_text for disambiguation)
        # lives in videotranslator.ollama_prompt and is unit-tested there.
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
        # Toggle thinking mode su Qwen3 via flag API nativa (Ollama supporta
        # `think` dal 2025+). Se l'API ignora il flag su versioni vecchie, il
        # suffisso `/no_think` nel prompt (quando thinking=False) fa da safety.
        # Con thinking=True il modello delibera step-by-step: ~5x più lento
        # ma riduce errori idiomi/grammatica.
        if is_qwen3:
            payload["think"] = bool(thinking)
        # Timeout generoso: qwen3:8b / qwen2.5:7b su RTX 3090 produce
        # ~40-80 tok/s, ma su CPU-only può arrivare a 2-5 tok/s. Con thinking
        # attivo il modello produce 3-5x più tokens (chain-of-thought interno
        # + risposta) quindi alziamo il timeout a 360s per evitare cut-off.
        _timeout = 360 if (is_qwen3 and thinking) else 120
        r = requests.post(f"{base}/api/generate", json=payload, timeout=_timeout)
        r.raise_for_status()
        data = r.json()
        return _ollama_strip_preamble(data.get("response", ""))

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
                        # Risposta vuota = considera fallita, fallback
                        raise RuntimeError("empty response")
                # ── Length re-prompt (TASK 2C-1) ────────────────────────
                # Se la prima traduzione è significativamente sopra il budget
                # ammesso per lo slot audio, chiediamo al modello di
                # riscriverla più corta. Questo abbatte la zona "strong/severe"
                # dell'atempo diagnostic (>1.50x) senza penalizzare i segmenti
                # già a misura. Costo: +1 chiamata Ollama solo sugli outlier.
                target_chars = _compute_target_chars(
                    slot_s, target_lang, slack=1.10
                )
                _seg_target_chars = target_chars
                if _should_reprompt_for_length(len(tr), target_chars, threshold=1.10):
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
                            f"     ! Length retry seg #{i} HTTP failed: {_re_err}; "
                            f"keeping first translation",
                            flush=True,
                        )
                    if tr_short and len(tr_short) < len(tr):
                        rewrite_success += 1
                        _seg_retry_succeeded = True
                        print(
                            f"     ↺ Length retry seg #{i}: {len(tr)} → "
                            f"{len(tr_short)} chars (target {target_chars}, "
                            f"slot {slot_s:.1f}s)",
                            flush=True,
                        )
                        tr = tr_short
                    elif tr_short:
                        # Modello ha risposto ma non ha accorciato. Tracciamo
                        # solo se _ollama_debug, per non rumorizzare i log.
                        if _ollama_debug:
                            print(
                                f"     [ollama-debug] length retry seg #{i} "
                                f"did not shorten ({len(tr_short)} >= {len(tr)})",
                                flush=True,
                            )
                # ── Length safeguard ────────────────────────────────────
                # Se l'output residuo dopo strip_preamble è >> del sorgente
                # rispetto all'expansion atteso, il modello ha quasi
                # certamente incluso commentary non-catturato. Tronchiamo
                # alla prima frase completa (o a char cap con word-boundary)
                # per evitare che XTTS sintetizzi 20+ secondi di disclaimer.
                # v2.2: cap stretto 1.5x (era 1.8x) per catturare più aggressivamente
                # gli outlier Ollama da commentary/disclaimer non-strippato.
                max_reasonable_chars = max(
                    50, int(len(text) * _expansion_factor * 1.5)
                )
                if len(tr) > max_reasonable_chars:
                    # v2.2: log sempre il SRC e l'OUT troncati, così l'utente può
                    # diagnosticare quali segmenti hanno triggato il safety senza
                    # dover impostare VIDEOTRANSLATORAI_OLLAMA_DEBUG.
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
                    # Strategia: prima frase completa (.?!。？！ seguito da
                    # spazio/fine). Fallback: cap con word-boundary.
                    m = _re.search(r"^(.+?[.?!。？！])(?:\s|$)", tr)
                    if m and len(m.group(1)) <= max_reasonable_chars * 1.1:
                        tr = m.group(1)
                    else:
                        tr = tr[:max_reasonable_chars].rsplit(" ", 1)[0] + "..."
                    truncated_count += 1
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
        translated.append(entry)
        if (i + 1) % 4 == 0 or i + 1 == total:
            print(f"     {i+1}/{total}...", end="\r", flush=True)

    # Statistica shrinkage: quanto più conciso è l'output Ollama rispetto
    # al sorgente (approssimazione per caratteri). Utile a diagnosticare se
    # il prompt "CONCISE" sta funzionando (atteso ratio ~0.9-1.1 vs naïf
    # 1.25 per EN→IT con deep-translator).
    if total_src_chars > 0:
        ratio = total_tgt_chars / total_src_chars
        # expansion naïf atteso dalla tabella LANG_EXPANSION (baseline letterale)
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
    else:
        print(f"     → Ollama translation: {total}/{total} segments (no text)", flush=True)

    return translated


def _marian_normalize_lang(code: str) -> str:
    """Normalize language codes to the short form Helsinki-NLP models expect."""
    if not code:
        return code
    c = code.lower()
    # Helsinki-NLP uses 'zh' not 'zh-cn'
    if c.startswith("zh"):
        return "zh"
    # Norwegian: 'no' -> 'nb' on HF (Bokmal)
    if c == "no":
        return "nb"
    return c.split("-")[0]


def translate_segments(
    segments: list[dict], source: str, target: str,
    engine: str = "google", deepl_key: str = "",
    ollama_model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    ollama_slot_aware: bool = True,
    ollama_thinking: bool = False,
) -> list[dict]:
    src = "auto" if source == "auto" else source
    print(f"[4/6] Translating {src.upper()}→{target.upper()} ({len(segments)} segments, engine={engine})...", flush=True)

    # ── Ollama LLM translation (v2.0) ──────────────────────────────────────
    # Leva strutturale contro gli atempo artifacts: l'LLM capisce il vincolo
    # temporale e comprime la traduzione alla sorgente, invece di lasciare che
    # MarianMT/Google producano output letterali +25% più lunghi.
    if engine == "llm_ollama":
        try:
            return translate_with_ollama(
                segments, src, target,
                model=ollama_model, api_url=ollama_url,
                slot_aware=ollama_slot_aware, batch_size=1,
                thinking=ollama_thinking,
            )
        except Exception as e:
            print(f"     ! Ollama unavailable ({e}), falling back to Google Translate.", flush=True)
            engine = "google"

    # ── MarianMT local translation ──────────────────────────────────────────
    if engine == "marian":
        # Auto-detect is not supported: we need an explicit source language.
        if src == "auto":
            print("     ! MarianMT requires explicit source language (auto not supported), falling back to Google.", flush=True)
        else:
            m_src = _marian_normalize_lang(src)
            m_tgt = _marian_normalize_lang(target)
            model_name = f"Helsinki-NLP/opus-mt-{m_src}-{m_tgt}"
            tokenizer = None
            model = None
            try:
                # lazy import to keep startup fast
                from transformers import MarianMTModel, MarianTokenizer
                import torch
                tokenizer = MarianTokenizer.from_pretrained(model_name)
                model = MarianMTModel.from_pretrained(model_name)
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model = model.to(device)
                print(f"     → MarianMT loaded ({model_name}, device={device})", flush=True)

                texts = [(seg.get("text") or "").strip() for seg in segments]
                results: list[str] = []
                batch_size = 8
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    # Preserve empty strings to keep indices aligned
                    non_empty_idx = [j for j, t in enumerate(batch) if t]
                    batch_out = [""] * len(batch)
                    if non_empty_idx:
                        inputs = tokenizer(
                            [batch[j] for j in non_empty_idx],
                            return_tensors="pt", padding=True,
                            truncation=True, max_length=512,
                        ).to(device)
                        with torch.no_grad():
                            translated = model.generate(**inputs)
                        decoded = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]
                        for j, out in zip(non_empty_idx, decoded):
                            batch_out[j] = out
                    results.extend(batch_out)
                    print(f"     {min(i + batch_size, len(texts))}/{len(texts)}...", end="\r", flush=True)

                translated_segs = []
                for seg, tr in zip(segments, results):
                    text = (seg.get("text") or "").strip()
                    translated_segs.append({
                        "start": seg["start"],
                        "end":   seg["end"],
                        "text_src": text,
                        "text_tgt": tr or text,
                        **({"speaker": seg["speaker"]} if "speaker" in seg else {}),
                    })
                print("     → Translation done (MarianMT)          ", flush=True)
                return translated_segs
            except Exception as e:
                print(f"     ! MarianMT model {model_name} not available ({e.__class__.__name__}), falling back to Google.", flush=True)
            finally:
                # free VRAM
                try:
                    del model
                    del tokenizer
                    import torch as _t
                    if _t.cuda.is_available():
                        _t.cuda.empty_cache()
                except Exception:
                    pass
        # fall through to Google if MarianMT failed
        engine = "google"

    # ── DeepL: batch API con retry/backoff ──────────────────────────────────
    if engine == "deepl" and deepl_key.strip():
        key = deepl_key.strip()
        endpoint = "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"
        import requests, time as _time
        texts = [(seg.get("text") or "").strip() for seg in segments]
        results: list[str] = [""] * len(texts)
        idx_nonempty = [i for i, t in enumerate(texts) if t]
        BATCH = 50
        MAX_RETRIES = 5
        headers = {"Authorization": f"DeepL-Auth-Key {key}"}
        deepl_target = target.upper()
        if deepl_target == "EN":
            deepl_target = "EN-US"
        deepl_source = None if src == "auto" else src.upper()
        try:
            for i in range(0, len(idx_nonempty), BATCH):
                chunk_idx = idx_nonempty[i:i + BATCH]
                payload = [("target_lang", deepl_target)]
                if deepl_source:
                    payload.append(("source_lang", deepl_source))
                # `context` (DeepL v2) nudges the model toward concise spoken-register
                # output, reducing overrun vs. source duration for dubbing.
                payload.append((
                    "context",
                    "Keep the translation concise and natural for dubbing. "
                    "Prefer spoken register over formal register.",
                ))
                for j in chunk_idx:
                    payload.append(("text", texts[j]))
                for attempt in range(MAX_RETRIES):
                    try:
                        r = requests.post(endpoint, headers=headers, data=payload, timeout=60)
                        if r.status_code == 429 or r.status_code >= 500:
                            wait = float(r.headers.get("Retry-After", 2 ** attempt))
                            print(f"     ! DeepL {r.status_code}, retry in {wait:.1f}s...", flush=True)
                            _time.sleep(wait)
                            continue
                        if r.status_code == 403:
                            raise RuntimeError(f"DeepL 403 Forbidden — verifica la API key ({r.text[:200]})")
                        r.raise_for_status()
                        data = r.json()
                        for j, item in zip(chunk_idx, data.get("translations", [])):
                            results[j] = item.get("text", "") or texts[j]
                        break
                    except requests.RequestException as e:
                        if attempt == MAX_RETRIES - 1:
                            print(f"     ! DeepL batch {i}-{i+len(chunk_idx)} failed: {e}", flush=True)
                            for j in chunk_idx:
                                results[j] = texts[j]
                        else:
                            _time.sleep(2 ** attempt)
                print(f"     {min(i + BATCH, len(idx_nonempty))}/{len(idx_nonempty)}...", end="\r", flush=True)
            translated = []
            for seg, tr in zip(segments, results):
                text = (seg.get("text") or "").strip()
                entry = {
                    "start": seg["start"], "end": seg["end"],
                    "text_src": text, "text_tgt": tr or text,
                }
                if "speaker" in seg:
                    entry["speaker"] = seg["speaker"]
                translated.append(entry)
            print("     → Translation done (DeepL)          ", flush=True)
            return translated
        except Exception as e:
            print(f"     ! DeepL failed ({e}), falling back to Google Translate.", flush=True)
            engine = "google"

    # ── Google Translate fallback ──────────────────────────────────────────
    from deep_translator import GoogleTranslator
    if engine == "deepl":
        print("     ! DeepL key missing, falling back to Google Translate.", flush=True)
    translator = GoogleTranslator(source=src, target=target)
    translated = []
    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        if not text:
            text_tgt = ""
        else:
            try:
                text_tgt = translator.translate(text) or text
            except Exception as e:
                print(f"     ! Error segment {i}: {e}", flush=True)
                text_tgt = text
        entry = {
            "start": seg["start"],
            "end": seg["end"],
            "text_src": text,
            "text_tgt": text_tgt,
        }
        if "speaker" in seg:
            entry["speaker"] = seg["speaker"]
        translated.append(entry)
        if i % 10 == 0:
            print(f"     {i+1}/{len(segments)}...", end="\r", flush=True)
    print("     → Translation done          ", flush=True)
    return translated


async def _tts_segment(text: str, voice: str, out_path: str, rate: str = "+0%", retries: int = 5):
    import edge_tts
    for attempt in range(retries):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate)
            await comm.save(out_path)
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"     ! TTS retry {attempt+1} ({e.__class__.__name__}) in {wait}s...", flush=True)
                await asyncio.sleep(wait)
            else:
                print(f"     ! TTS failed: {text[:40]!r} ({e.__class__.__name__}: {e})", flush=True)


async def _tts_all(segments: list[dict], voice: str, tmp_dir: str, rate: str) -> list[str]:
    # Edge-TTS è HTTP puro → parallelizzazione safe con un semaphore per non
    # saturare il servizio. Rate-limit Azure si assesta sui 3-5 req/s: 4 concorrenti
    # è più conservativo di 8 e riduce i 429/timeout senza penalizzare il throughput.
    total = len(segments)
    files = [os.path.join(tmp_dir, f"seg_{i:04d}.mp3") for i in range(total)]
    sem = asyncio.Semaphore(4)
    done_counter = {"n": 0, "failed": 0}

    async def _run(i: int):
        text = (segments[i].get("text_tgt") or "").strip()
        if not text:
            return
        async with sem:
            await _tts_segment(text, voice, files[i], rate=rate)
        if not os.path.exists(files[i]):
            done_counter["failed"] += 1
        done_counter["n"] += 1
        if done_counter["n"] % 10 == 0 or done_counter["n"] == total:
            print(f"     {done_counter['n']}/{total}...", end="\r", flush=True)

    await asyncio.gather(*(_run(i) for i in range(total)))
    if done_counter["failed"]:
        print(f"     ! Warning: {done_counter['failed']}/{total} TTS segments failed and will be silent.", flush=True)
    return files


def generate_tts(segments: list[dict], voice: str, tmp_dir: str, rate: str = "+0%") -> list[str]:
    print(f"[5/6] Generating TTS (voice={voice}, rate={rate})...", flush=True)
    files = asyncio.run(_tts_all(segments, voice, tmp_dir, rate))
    print("     → TTS done                   ", flush=True)
    return files


def _build_vad_reference(
    src_audio: str,
    out_wav: str,
    target_seconds: float = 18.0,
    min_seconds: float = 3.0,
    max_gap_ms: int = 300,
    sample_rate: int = 22050,
) -> str | None:
    """Estrae una reference vocale pulita da src_audio usando silero-vad.
    Strategia: sceglie il segmento di parlato continuo più lungo (gap fra sub-chunk
    VAD ≤ max_gap_ms); se è <target_seconds, concatena i segmenti più lunghi fino
    a raggiungere target_seconds. Scrive un WAV mono 22050 Hz in out_wav.
    Ritorna out_wav o None in caso di errore/parlato insufficiente.

    `target_seconds` default 18.0 (prima 12.0): XTTS clona meglio con ~15-20s di
    materiale pulito. Su audio lunghi (>1 min) il VAD trova tipicamente 80+
    secondi di parlato, quindi il target 18 è raggiungibile. Se non lo è, il
    chiamante può ritentare con target minori (fallback 18→15→12→10).
    """
    try:
        import numpy as np
        import soundfile as sf
        from silero_vad import load_silero_vad, get_speech_timestamps, read_audio
    except ImportError as e:
        print(f"     ! silero-vad not available ({e}), using raw reference.", flush=True)
        return None

    try:
        model = load_silero_vad()
        # silero-vad opera a 16 kHz
        wav_16k = read_audio(src_audio, sampling_rate=16000)
        timestamps = get_speech_timestamps(
            wav_16k, model, sampling_rate=16000, return_seconds=True,
        )
        if not timestamps:
            print("     ! VAD: no speech detected, using raw reference.", flush=True)
            return None

        # Fonde sub-segmenti separati da pause brevi nel "continuous speech block".
        max_gap_s = max_gap_ms / 1000.0
        merged: list[tuple[float, float]] = []
        for t in timestamps:
            s, e = float(t["start"]), float(t["end"])
            if merged and s - merged[-1][1] <= max_gap_s:
                merged[-1] = (merged[-1][0], e)
            else:
                merged.append((s, e))

        merged.sort(key=lambda se: se[1] - se[0], reverse=True)
        longest = merged[0]
        longest_dur = longest[1] - longest[0]

        if longest_dur >= target_seconds:
            selected = [longest]
        else:
            # Top-N segmenti fino a target_seconds (ordine cronologico per naturalezza).
            picked: list[tuple[float, float]] = []
            total = 0.0
            for s, e in merged:
                picked.append((s, e))
                total += e - s
                if total >= target_seconds:
                    break
            if total < min_seconds:
                print(f"     ! VAD: only {total:.1f}s speech (<{min_seconds}s), using raw reference.", flush=True)
                return None
            picked.sort(key=lambda se: se[0])
            selected = picked

        # Carica a sample_rate target, slicing diretto in array numpy.
        audio_hq, sr_hq = sf.read(src_audio, always_2d=False)
        if audio_hq.ndim > 1:
            audio_hq = audio_hq.mean(axis=1)
        # Resample a sample_rate se necessario (lineare è sufficiente per reference).
        if sr_hq != sample_rate:
            import math as _m
            n_out = int(_m.ceil(len(audio_hq) * sample_rate / sr_hq))
            x_old = np.linspace(0, 1, num=len(audio_hq), endpoint=False)
            x_new = np.linspace(0, 1, num=n_out, endpoint=False)
            audio_hq = np.interp(x_new, x_old, audio_hq).astype(np.float32)
            sr_hq = sample_rate

        pieces = []
        for s, e in selected:
            i0 = max(0, int(s * sr_hq))
            i1 = min(len(audio_hq), int(e * sr_hq))
            if i1 > i0:
                pieces.append(audio_hq[i0:i1])
        if not pieces:
            return None
        out = np.concatenate(pieces)
        sf.write(out_wav, out, sr_hq, subtype="PCM_16")
        print(f"     → VAD reference: {len(out)/sr_hq:.1f}s speech (from {len(merged)} chunks)", flush=True)
        return out_wav
    except Exception as e:
        print(f"     ! VAD reference failed ({e.__class__.__name__}: {e}), using raw reference.", flush=True)
        return None


def _build_vad_reference_tiered(
    src_audio: str,
    out_wav: str,
    targets: tuple[float, ...] = (18.0, 15.0, 12.0, 10.0),
) -> str | None:
    """Wrapper che tenta `_build_vad_reference` con target decrescenti.

    XTTS v2 clona meglio la voce con ~15-20s di parlato pulito, quindi partiamo
    da 18s. Se il VAD non trova abbastanza materiale (o la funzione ritorna None
    per qualsiasi motivo), riduciamo progressivamente: 18 → 15 → 12 → 10.
    Se tutti i tentativi falliscono, ritorna None e il chiamante farà fallback
    sul comportamento legacy (ffmpeg -t 30 / copia raw).
    """
    for i, target in enumerate(targets):
        result = _build_vad_reference(src_audio, out_wav, target_seconds=target)
        if result:
            if i > 0:
                # Log esplicito: l'utente deve capire che abbiamo ripiegato a
                # un target più basso (meno materiale = clone potenzialmente
                # meno fedele, ma comunque migliore di una reference raw).
                print(f"     → VAD reference built at fallback target {target:.0f}s (primary {targets[0]:.0f}s not reachable)", flush=True)
            return result
    return None


def generate_tts_xtts(
    segments: list[dict],
    reference_audio: str,
    lang_target: str,
    tmp_dir: str,
    diar_segments: list[dict] | None = None,
    speed: float = 1.1,
) -> list[str]:
    """Voice cloning TTS via Coqui XTTS v2. Uses reference_audio to clone speaker voice.
    If diar_segments is provided, extracts per-speaker reference clips and uses the
    correct one for each segment (based on seg['speaker']).
    `speed` is clamped to XTTS v2 accepted range (0.5–2.0) and applied natively by
    the model: genera audio target più vicino alla durata source, riducendo il
    post-atempo in build_dubbed_track (meno artefatti).
    """
    import torch
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    from TTS.api import TTS as CoquiTTS

    xtts_lang = XTTS_LANGS.get(lang_target)
    if not xtts_lang:
        print(f"[!] XTTS v2 does not support '{lang_target}', falling back to Edge-TTS.", flush=True)
        return None  # caller will fall back to edge-tts

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # XTTS v2 range officially supported: 0.5–2.0. `speed` qui è il CEILING per
    # lo speed adattivo per-segmento (vedi _compute_segment_speed sotto): nessun
    # segmento lo supera. Retrocompat: utenti con `xtts_speed` pinnato in config
    # vedono il loro valore usato come tetto → comportamento ≤ vecchio fisso.
    speed = max(0.5, min(float(speed), 2.0))
    print(f"[5/6] Generating TTS with Coqui XTTS v2 (voice cloning, device={device}, speed<={speed:.2f} adaptive)...", flush=True)
    print(f"     Reference audio: {Path(reference_audio).name}", flush=True)

    # Global (fallback) reference clip — preferisco VAD per evitare silenzi/rumore.
    ref_clip = os.path.join(tmp_dir, "xtts_ref.wav")
    vad_ref = _build_vad_reference_tiered(reference_audio, ref_clip)
    if not vad_ref:
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", reference_audio,
                "-t", "30", "-ar", "22050", "-ac", "1", ref_clip
            ], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            shutil.copy(reference_audio, ref_clip)

    # Per-speaker references when diarization is available
    speaker_refs: dict[str, str] = {}
    if diar_segments:
        unique_speakers = sorted({d["speaker"] for d in diar_segments})
        print(f"     Building per-speaker references for: {', '.join(unique_speakers)}", flush=True)
        for spk in unique_speakers:
            ref = _extract_speaker_reference(reference_audio, diar_segments, spk, tmp_dir)
            if ref:
                # Refina la reference per-speaker con VAD per eliminare pause/rumore
                # residui nei turni selezionati.
                refined = os.path.join(tmp_dir, f"{Path(ref).stem}_vad.wav")
                if _build_vad_reference_tiered(ref, refined):
                    ref = refined
                speaker_refs[spk] = ref
            else:
                print(f"     ! No reference for {spk}, will use global reference.", flush=True)

    tts_model = None
    # Lock around the model call: XTTS non è thread-safe (single GPU context).
    # Il ThreadPool permette di sovrapporre tokenization (CPU) e save WAV (disco)
    # mentre un altro worker tiene occupata la GPU.
    from concurrent.futures import ThreadPoolExecutor
    tts_lock = threading.Lock()
    # Tolleranza float per il conteggio "at cap": segmenti il cui speed è
    # clampato al ceiling (l'utente vede il parametro che in UI→tetto globale).
    _CAP_EPS = 1e-3
    # Statistiche speed adattivo (per log a fine loop). Protette dallo stesso
    # counter_lock del progress counter per non aggiungere un terzo lock.
    speed_stats = {"min": None, "max": None, "sum": 0.0, "n": 0, "at_cap": 0}
    # v2.2: contatori hallucination retry. `attempts` = quante volte abbiamo
    # detectato output anomalo (durata > 2.5x predicted) e tentato un retry;
    # `successful` = quanti di quei retry hanno effettivamente prodotto un
    # output più corto del 60% rispetto all'originale (soglia "miglioramento").
    retry_stats = {"attempts": 0, "successful": 0}
    try:
        tts_model = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        total = len(segments)
        files: list[str] = [os.path.join(tmp_dir, f"seg_{i:04d}.wav") for i in range(total)]
        done_counter = {"n": 0}
        counter_lock = threading.Lock()

        def _gen_one(i: int):
            seg = segments[i]
            out = files[i]
            text = (seg.get("text_tgt") or seg.get("text") or "").strip()
            if not text:
                return None
            # TASK 2F: rimuovi punteggiatura interna che XTTS verbalizza
            # (es. ":" pronunciato "due punti" in italiano). Va PRIMA dello
            # strip terminale così la pulizia è completa.
            text = _sanitize_for_tts(text)
            # v2.5.2: rimuovi punteggiatura finale prima di passarla a XTTS.
            # XTTS in voice cloning su lingue latine pronuncia letteralmente
            # ".", "!", "?" finali ("punto", "esclamativo") nonostante
            # enable_text_splitting=True. Lo strip non altera la prosodia
            # (XTTS aggiunge naturalmente una pausa a fine generazione).
            # NB: usiamo `text` strippato per stima durata e generazione, MA
            # _compute_segment_speed lo riceve dopo lo strip → la stima
            # chars/sec è marginalmente più bassa (1-2 char in meno) → speed
            # leggermente più basso → trade-off accettabile.
            text = _strip_xtts_terminal_punct(text)
            if not text:
                return None
            spk = seg.get("speaker")
            spk_ref = speaker_refs.get(spk, ref_clip) if spk else ref_clip
            # Speed adattivo: `speed` (arg funzione) agisce da ceiling.
            # slot_s calcolato dallo start/end Whisper; se mancano, fallback a
            # 0 → _compute_segment_speed ritorna min(ceiling, 1.25).
            try:
                slot_s = float(seg.get("end", 0)) - float(seg.get("start", 0))
            except Exception:
                slot_s = 0.0
            seg_speed = _compute_segment_speed(text, slot_s, xtts_lang, ceiling=speed)
            # v2.2: parametri tuned for Italian long-form, anti-loop. Più
            # restrittivi rispetto a v2.1 dopo aver osservato outlier severi
            # (ratio >4x slot) su segmenti EN→IT che NON triggavano il safety
            # Qwen ma producevano 20+ secondi di audio per ~80 chars di testo.
            # Valori derivati da empirical testing forum coqui-tts su long-form:
            #   - temperature 0.55 (era 0.65): meno randomness → meno deriva
            #   - repetition_penalty 10.0 (era 5.0): più aggressivo contro loop
            #   - top_k 30 (era 50): vocabolario più focused
            #   - top_p 0.75 (era 0.85): più deterministico
            # Trade-off accettato: prosodia leggermente più piatta sui segmenti
            # normali in cambio di assenza di hallucination al 4x slot.
            xtts_kwargs = dict(
                temperature=0.55,
                repetition_penalty=10.0,
                length_penalty=1.0,
                top_k=30,
                top_p=0.75,
                enable_text_splitting=True,
            )
            try:
                with tts_lock:
                    tts_model.tts_to_file(
                        text=text,
                        speaker_wav=spk_ref,
                        language=xtts_lang,
                        file_path=out,
                        speed=seg_speed,
                        **xtts_kwargs,
                    )
                # v2.5.2: post-TTS validation con strategia di recovery
                # multi-stage. Se l'output supera 2.5x predicted (XTTS sta
                # hallucinando), prova in sequenza:
                #   1. Retry con seed alternativi (RETRY_SEEDS, max 2)
                #   2. Split del testo a metà se >30 char e nessun retry OK
                # Tiene sempre il "miglior" output finora — se nulla funziona
                # build_dubbed_track applicherà atempo (cap 4.0). Conta tutti
                # i tentativi falliti+riusciti in retry_stats per visibilità
                # nel log finale.
                actual_s = _measure_wav_duration_s(out)
                est_at_unit_speed = _estimate_tts_duration_s(text, xtts_lang)
                predicted_s = est_at_unit_speed / seg_speed if seg_speed > 0 else 0.0
                if predicted_s > 0 and actual_s > predicted_s * 2.5:
                    print(
                        f"     ! XTTS output sospetto (segment {i}): "
                        f"{actual_s:.1f}s vs predicted {predicted_s:.1f}s "
                        f"(ratio {actual_s/predicted_s:.1f}x). Multi-seed retry.",
                        flush=True,
                    )
                    best_s = actual_s
                    rescued = False
                    # Step 1: due retry con seed differenti.
                    for retry_n, seed in enumerate(RETRY_SEEDS[:2], start=1):
                        with counter_lock:
                            retry_stats["attempts"] += 1
                        retry_path = out + f".retry{retry_n}"
                        try:
                            with tts_lock:
                                torch.manual_seed(seed)
                                if torch.cuda.is_available():
                                    torch.cuda.manual_seed_all(seed)
                                tts_model.tts_to_file(
                                    text=text,
                                    speaker_wav=spk_ref,
                                    language=xtts_lang,
                                    file_path=retry_path,
                                    speed=seg_speed,
                                    **xtts_kwargs,
                                )
                            retry_s = _measure_wav_duration_s(retry_path)
                            if retry_s > 0 and retry_s < actual_s * 0.6:
                                # Successo netto: questo retry rompe il loop.
                                shutil.move(retry_path, out)
                                best_s = retry_s
                                rescued = True
                                with counter_lock:
                                    retry_stats["successful"] += 1
                                print(
                                    f"       Retry seed={seed} OK: "
                                    f"{retry_s:.1f}s "
                                    f"({retry_s/predicted_s:.1f}x predicted)",
                                    flush=True,
                                )
                                break
                            elif retry_s > 0 and retry_s < best_s:
                                # Miglioramento parziale: tieni come "miglior tentativo".
                                shutil.move(retry_path, out)
                                best_s = retry_s
                            else:
                                try: os.remove(retry_path)
                                except OSError: pass
                        except Exception as re:
                            print(
                                f"       Retry seed={seed} failed for seg {i}: {re}",
                                flush=True,
                            )
                            try: os.remove(retry_path)
                            except OSError: pass
                    # Step 2: split del testo se i seed non sono bastati.
                    if not rescued and len(text) > 30:
                        with counter_lock:
                            retry_stats["attempts"] += 1
                        print(
                            f"       Retry seeds non risolti. Provo SPLIT testo.",
                            flush=True,
                        )
                        split_pos = _find_split_point(text)
                        if 10 < split_pos < len(text) - 10:
                            part1 = text[:split_pos].strip()
                            part2 = text[split_pos:].strip()
                            chunk1_path = out + ".part1"
                            chunk2_path = out + ".part2"
                            try:
                                with tts_lock:
                                    tts_model.tts_to_file(
                                        text=part1,
                                        speaker_wav=spk_ref,
                                        language=xtts_lang,
                                        file_path=chunk1_path,
                                        speed=seg_speed,
                                        **xtts_kwargs,
                                    )
                                    tts_model.tts_to_file(
                                        text=part2,
                                        speaker_wav=spk_ref,
                                        language=xtts_lang,
                                        file_path=chunk2_path,
                                        speed=seg_speed,
                                        **xtts_kwargs,
                                    )
                                _concat_wavs([chunk1_path, chunk2_path], out)
                                split_s = _measure_wav_duration_s(out)
                                if split_s > 0 and split_s < best_s:
                                    print(
                                        f"       Split OK: {split_s:.1f}s "
                                        f"({split_s/predicted_s:.1f}x predicted)",
                                        flush=True,
                                    )
                                    with counter_lock:
                                        retry_stats["successful"] += 1
                                    best_s = split_s
                                    rescued = True
                                else:
                                    print(
                                        f"       Split no improvement "
                                        f"({split_s:.1f}s).",
                                        flush=True,
                                    )
                            except Exception as se:
                                print(
                                    f"       Split failed for seg {i}: {se}",
                                    flush=True,
                                )
                            finally:
                                for tmpf in (chunk1_path, chunk2_path):
                                    try: os.remove(tmpf)
                                    except OSError: pass
                    if not rescued:
                        print(
                            f"       Nessun retry ha rotto il loop. "
                            f"Mantengo miglior tentativo: {best_s:.1f}s.",
                            flush=True,
                        )
            except Exception as e:
                print(f"     ! XTTS seg {i}: {e}", flush=True)
            with counter_lock:
                # Aggiorna stats speed adattivo
                if speed_stats["min"] is None or seg_speed < speed_stats["min"]:
                    speed_stats["min"] = seg_speed
                if speed_stats["max"] is None or seg_speed > speed_stats["max"]:
                    speed_stats["max"] = seg_speed
                speed_stats["sum"] += seg_speed
                speed_stats["n"] += 1
                if seg_speed >= speed - _CAP_EPS:
                    speed_stats["at_cap"] += 1
                done_counter["n"] += 1
                n = done_counter["n"]
                # Print sotto lock per evitare output frammentato fra thread.
                if n % 10 == 0 or n == total:
                    print(f"     {n}/{total}...", end="\r", flush=True)
            return None

        # max_workers=4: GPU resta serializzata dal lock, ma I/O e pre/post si
        # sovrappongono. Valore più alto produce contention inutile sul lock.
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(_gen_one, range(total)))
    finally:
        del tts_model
        if device == "cuda":
            try:
                import torch as _t
                _t.cuda.empty_cache()
            except Exception:
                pass

    print("     → XTTS done                   ", flush=True)
    # Log distribuzione speed adattivo. Skippa se nessun segmento ha testo.
    n_stats = speed_stats["n"]
    if n_stats > 0:
        s_min = speed_stats["min"] or 0.0
        s_max = speed_stats["max"] or 0.0
        s_mean = speed_stats["sum"] / n_stats
        at_cap = speed_stats["at_cap"]
        pct = (at_cap / n_stats) * 100.0
        print(
            f"     → XTTS adaptive speed: min={s_min:.2f}, mean={s_mean:.2f}, "
            f"max={s_max:.2f} over {n_stats} segments",
            flush=True,
        )
        print(
            f"     → Segments at speed cap ({speed:.2f}): {at_cap}/{n_stats} ({pct:.1f}%)",
            flush=True,
        )
        # v2.2: visibilità su quanti segmenti hanno triggato il retry anti-
        # hallucination e quanti sono stati effettivamente rescued. Se il
        # numero attempts è significativo (>5%), valutare di stringere ancora
        # repetition_penalty o ridurre top_k.
        if retry_stats["attempts"] > 0:
            print(
                f"     → XTTS hallucination retries: {retry_stats['attempts']} "
                f"({retry_stats['successful']} successful)",
                flush=True,
            )
    return files


def generate_tts_cosyvoice(
    segments: list[dict],
    reference_audio: str,
    lang_target: str,
    tmp_dir: str,
    diar_segments: list[dict] | None = None,
    speed: float = 1.25,
) -> list[str] | None:
    """Voice cloning TTS via CosyVoice (v2.3 add-on, alternativa a XTTS v2).

    Mirror funzionale di `generate_tts_xtts`: stessa firma, stessa convenzione
    di ritorno (lista path WAV nello stesso ordine dei `segments`, oppure None
    per segnalare al caller di fare fallback su Edge-TTS / XTTS).

    Differenze chiave rispetto a XTTS:
      - Modello con tasso di hallucination ~2% vs 5-15% di XTTS (benchmark
        community FunAudioLLM su long-form). Il safety net retry resta ma
        scatterà raramente.
      - API zero-shot/cross-lingual: passiamo prompt_text + prompt_speech_16k
        (la nostra reference VAD) e CosyVoice clona il timbro mantenendo la
        prosodia della lingua target. Per IT (non nativa nei pesi 1.x)
        usiamo prefix `<|it|>` nel testo per il language conditioning.
      - Speed: il modello ha controllo nativo via `speed` parameter (range
        0.5-2.0 come XTTS); il loop adattivo per-segmento è identico.

    Fallback graceful: qualunque eccezione (model load, OOM, lang non
    supportata, file mancanti) → ritorna None, il caller usa XTTS o Edge-TTS.
    """
    import torch

    # Quick sanity: pacchetto Python presente? Se no, ritorniamo None subito,
    # il caller mostrerà il messaggio "fallback" senza crash.
    if not _cosyvoice_is_installed():
        print("[!] CosyVoice non installato, fallback al TTS successivo.", flush=True)
        return None

    # Modello presente in cache? Tentiamo download on-demand. Se fallisce,
    # ritorno None per fallback (non vogliamo bloccare la pipeline aspettando
    # 1.7 GB se l'utente non ha confermato esplicitamente).
    cache_dir = _cosyvoice_cache_dir()
    if not _cosyvoice_model_present(cache_dir):
        ok, msg = _cosyvoice_download_model(cache_dir, log_cb=lambda s: print(s, end="", flush=True))
        if not ok:
            print(f"[!] CosyVoice model download fallito: {msg}. Fallback.", flush=True)
            return None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Cap speed nel range supportato dal modello (stesso di XTTS).
    speed = max(0.5, min(float(speed), 2.0))

    # Risolvi il tag lingua: nativa = nessun prefix nel testo, cross-lingual
    # = prefix `<|xx|>` per language conditioning del LLM interno.
    is_native = lang_target in COSYVOICE_NATIVE_LANGS
    lang_tag = COSYVOICE_LANG_TAGS.get(lang_target, "<|en|>")
    mode_label = "native" if is_native else f"cross-lingual ({lang_tag})"
    print(
        f"[5/6] Generating TTS with CosyVoice 2.0 (voice cloning, "
        f"device={device}, speed<={speed:.2f} adaptive)...", flush=True,
    )
    print(f"     → CosyVoice2-0.5B loaded ({mode_label} mode for {lang_target})", flush=True)
    print(f"     Reference audio: {Path(reference_audio).name}", flush=True)

    # Reference globale via VAD (stessa logica di XTTS — riusiamo gli stessi
    # helper così il comportamento "trova 18s di speech continuo" è identico).
    ref_clip = os.path.join(tmp_dir, "cosyvoice_ref.wav")
    vad_ref = _build_vad_reference_tiered(reference_audio, ref_clip)
    if not vad_ref:
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", reference_audio,
                "-t", "30", "-ar", "16000", "-ac", "1", ref_clip
            ], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            shutil.copy(reference_audio, ref_clip)

    # Per-speaker references (diarization). Stessa pipeline XTTS.
    speaker_refs: dict[str, str] = {}
    if diar_segments:
        unique_speakers = sorted({d["speaker"] for d in diar_segments})
        print(f"     Building per-speaker references for: {', '.join(unique_speakers)}", flush=True)
        for spk in unique_speakers:
            ref = _extract_speaker_reference(reference_audio, diar_segments, spk, tmp_dir)
            if ref:
                refined = os.path.join(tmp_dir, f"{Path(ref).stem}_vad.wav")
                if _build_vad_reference_tiered(ref, refined):
                    ref = refined
                speaker_refs[spk] = ref
            else:
                print(f"     ! No reference for {spk}, will use global reference.", flush=True)

    # Carica il modello tramite il wrapper community (Lucas Jin). Try/except
    # blanket: il package può rompersi per N motivi (deps mancanti,
    # onnxruntime-gpu vs CPU, modello corrotto). In tutti i casi: fallback.
    cosy = None
    try:
        # Import locale (non top-level) per non pagare il costo di import
        # quando l'utente non usa CosyVoice. Lo stesso pattern usato per CoquiTTS.
        from cosyvoice.cli.cosyvoice import CosyVoice  # type: ignore
        # Forziamo il working dir alla cache così il wrapper trova i pesi
        # senza dover patchare il suo costruttore (che usa path relativi).
        model_path = str(cache_dir / "CosyVoice-300M-Instruct")
        cosy = CosyVoice(
            model_path,
            load_jit=torch.cuda.is_available(),
            fp16=torch.cuda.is_available(),
        )
    except Exception as e:
        print(f"[!] CosyVoice model load failed ({e.__class__.__name__}: {e}). Fallback.", flush=True)
        return None

    # Loro API ritorna un generator di dict con `tts_speech` (Tensor float).
    # Per salvarlo a file usiamo torchaudio.save (sample rate del modello: 22050).
    try:
        import torchaudio  # type: ignore
    except Exception:
        print("[!] torchaudio non disponibile per CosyVoice. Fallback.", flush=True)
        return None

    from concurrent.futures import ThreadPoolExecutor
    cosy_lock = threading.Lock()
    _CAP_EPS = 1e-3
    speed_stats = {"min": None, "max": None, "sum": 0.0, "n": 0, "at_cap": 0}
    retry_stats = {"attempts": 0, "successful": 0}
    total = len(segments)
    files: list[str] = [os.path.join(tmp_dir, f"seg_{i:04d}.wav") for i in range(total)]
    done_counter = {"n": 0}
    counter_lock = threading.Lock()

    def _save_speech(out_path: str, speech_tensor) -> None:
        """Salva il tensore audio nel WAV. Sample rate 22050 = default CosyVoice."""
        torchaudio.save(out_path, speech_tensor, 22050)

    def _gen_one(i: int):
        seg = segments[i]
        out = files[i]
        text = (seg.get("text_tgt") or seg.get("text") or "").strip()
        if not text:
            return None
        # v2.5.2: stesso strip terminale di XTTS — CosyVoice ha lo stesso
        # bug noto in voice cloning su lingue latine (pronuncia letterale
        # del simbolo finale). Per coerenza fra engine.
        text = _strip_xtts_terminal_punct(text)
        if not text:
            return None
        spk = seg.get("speaker")
        spk_ref = speaker_refs.get(spk, ref_clip) if spk else ref_clip
        # Prefix lingua per cross-lingual mode. La forma `<|it|>` è
        # interpretata da CosyVoice come language conditioning per il LLM
        # interno (non viene pronunciata).
        cosy_text = text if is_native else f"{lang_tag}{text}"
        # Speed adattivo identico a XTTS — riuso _compute_segment_speed che
        # è language-agnostic (lavora su chars/sec target vs slot Whisper).
        try:
            slot_s = float(seg.get("end", 0)) - float(seg.get("start", 0))
        except Exception:
            slot_s = 0.0
        # Per il lookup chars/sec passiamo il codice "interno" (es. "it")
        # piuttosto che il tag XTTS — la tabella _XTTS_CHARS_PER_SEC è
        # comunque il riferimento empirico migliore disponibile.
        seg_speed = _compute_segment_speed(text, slot_s, lang_target, ceiling=speed)

        try:
            with cosy_lock:
                # API zero-shot: testo target + reference text (può essere vuoto
                # se il wrapper la accetta) + reference audio. Il wrapper
                # community espone `inference_zero_shot` con questa firma.
                # Per CosyVoice 2.x ufficiale l'analogo è `inference_cross_lingual`.
                # Caricamento reference: librosa per resample a 16kHz mono.
                import librosa  # type: ignore
                prompt_speech_16k, _ = librosa.load(spk_ref, sr=16000, mono=True)
                prompt_speech_16k = torch.from_numpy(prompt_speech_16k).unsqueeze(0)
                # `inference_cross_lingual` se disponibile (CosyVoice 2.x style),
                # altrimenti `inference_zero_shot` (1.x). Detect via getattr.
                if hasattr(cosy, "inference_cross_lingual"):
                    gen = cosy.inference_cross_lingual(
                        cosy_text, prompt_speech_16k, stream=False, speed=seg_speed,
                    )
                else:
                    gen = cosy.inference_zero_shot(
                        cosy_text, "", prompt_speech_16k, stream=False, speed=seg_speed,
                    )
                # `gen` è un generator di dict {"tts_speech": Tensor}
                first = next(gen)
                _save_speech(out, first["tts_speech"])

            # Post-TTS validation (riuso schema XTTS v2.2).
            actual_s = _measure_wav_duration_s(out)
            est_at_unit_speed = _estimate_tts_duration_s(text, lang_target)
            predicted_s = est_at_unit_speed / seg_speed if seg_speed > 0 else 0.0
            if predicted_s > 0 and actual_s > predicted_s * 2.5:
                print(
                    f"     ! CosyVoice output sospetto (segment {i}): "
                    f"{actual_s:.1f}s vs predicted {predicted_s:.1f}s "
                    f"(ratio {actual_s/predicted_s:.1f}x). Retry.",
                    flush=True,
                )
                with counter_lock:
                    retry_stats["attempts"] += 1
                try:
                    with cosy_lock:
                        torch.manual_seed(42)
                        if torch.cuda.is_available():
                            torch.cuda.manual_seed_all(42)
                        if hasattr(cosy, "inference_cross_lingual"):
                            gen = cosy.inference_cross_lingual(
                                cosy_text, prompt_speech_16k, stream=False, speed=seg_speed,
                            )
                        else:
                            gen = cosy.inference_zero_shot(
                                cosy_text, "", prompt_speech_16k, stream=False, speed=seg_speed,
                            )
                        first = next(gen)
                        _save_speech(out, first["tts_speech"])
                    actual_s_retry = _measure_wav_duration_s(out)
                    if actual_s_retry > 0 and actual_s_retry < actual_s * 0.6:
                        print(
                            f"       Retry OK: {actual_s_retry:.1f}s "
                            f"({actual_s_retry/predicted_s:.1f}x predicted)",
                            flush=True,
                        )
                        with counter_lock:
                            retry_stats["successful"] += 1
                    else:
                        print(
                            f"       Retry no improvement "
                            f"({actual_s_retry:.1f}s); keeping original.",
                            flush=True,
                        )
                except Exception as re:
                    print(f"       Retry failed for seg {i}: {re}", flush=True)
        except Exception as e:
            print(f"     ! CosyVoice seg {i}: {e}", flush=True)

        with counter_lock:
            if speed_stats["min"] is None or seg_speed < speed_stats["min"]:
                speed_stats["min"] = seg_speed
            if speed_stats["max"] is None or seg_speed > speed_stats["max"]:
                speed_stats["max"] = seg_speed
            speed_stats["sum"] += seg_speed
            speed_stats["n"] += 1
            if seg_speed >= speed - _CAP_EPS:
                speed_stats["at_cap"] += 1
            done_counter["n"] += 1
            n = done_counter["n"]
            if n % 10 == 0 or n == total:
                print(f"     {n}/{total}...", end="\r", flush=True)
        return None

    try:
        # ThreadPool con max_workers=4 come XTTS: il lock serializza la GPU
        # ma permette di sovrapporre il lavoro CPU (resample librosa, save).
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(_gen_one, range(total)))
    finally:
        del cosy
        if device == "cuda":
            try:
                import torch as _t
                _t.cuda.empty_cache()
            except Exception:
                pass

    print("     → CosyVoice done                   ", flush=True)
    n_stats = speed_stats["n"]
    if n_stats > 0:
        s_min = speed_stats["min"] or 0.0
        s_max = speed_stats["max"] or 0.0
        s_mean = speed_stats["sum"] / n_stats
        at_cap = speed_stats["at_cap"]
        pct = (at_cap / n_stats) * 100.0
        print(
            f"     → CosyVoice adaptive speed: min={s_min:.2f}, mean={s_mean:.2f}, "
            f"max={s_max:.2f} over {n_stats} segments",
            flush=True,
        )
        print(
            f"     → Segments at speed cap ({speed:.2f}): {at_cap}/{n_stats} ({pct:.1f}%)",
            flush=True,
        )
        if retry_stats["attempts"] > 0:
            print(
                f"     → CosyVoice hallucination retries: {retry_stats['attempts']} "
                f"({retry_stats['successful']} successful) "
                f"[<2.5x threshold]",
                flush=True,
            )
        else:
            print("     → Hallucination check: 0 outliers (<2.5x threshold)", flush=True)
    return files


def _build_atempo_chain(ratio: float, max_ratio: float = 4.0) -> str:
    """Costruisce una catena di filtri atempo per ffmpeg.
    atempo accetta 0.5–2.0 in un singolo filtro; per ratio fuori range si concatenano istanze.
    Esempio: ratio=3.0 → 'atempo=2.0,atempo=1.5'

    Parametri:
      ratio     : rapporto di time-stretch desiderato.
      max_ratio : cap massimo applicato al ratio per evitare artefatti audio.
                  Default 4.0 (coerente col chiamante build_dubbed_track).
                  Il chiamante può passare un valore diverso se lo desidera.
    """
    if not math.isfinite(ratio) or ratio <= 0:
        return "atempo=1.0"
    # Clamp simmetrico: il reciproco del max per slow-down estremi.
    lo = 1.0 / max_ratio if max_ratio > 0 else 0.25
    ratio = max(lo, min(ratio, max_ratio))
    parts = []
    r = ratio
    while r > 2.0:
        parts.append("atempo=2.0")
        r /= 2.0
    while r < 0.5:
        parts.append("atempo=0.5")
        r /= 0.5
    parts.append(f"atempo={r:.3f}")
    return ",".join(parts)


# v2.5.2: seed list for multi-attempt XTTS/CosyVoice retry.
# Seeds empirici diversi spingono il decoder GPT2 di XTTS/CosyVoice a path
# differenti, riducendo la probabilità che lo stesso testo cada nello stesso
# loop deterministico di un seed fisso (era 42 in v2.2-2.5.1).
# L'ultimo seed (42) è mantenuto per retrocompat con i log della v2.2-2.5.1
# in caso di confronti di regression test.
RETRY_SEEDS = (7, 1337, 42)


def _strip_xtts_terminal_punct(text: str) -> str:
    """Rimuove la punteggiatura finale di chiusura per evitare che XTTS la
    pronunci letteralmente in voice cloning (bug noto coqui-tts 2024+ su
    lingue latine: il modello tokenizza "." come "punto" anche con
    enable_text_splitting=True).

    Mantiene la punteggiatura INTERNA (virgole, punti di abbreviazioni come
    "Mr." in mezzo alla frase) perché serve alla prosodia.

    Esempi:
        "Buongiorno a tutti."     → "Buongiorno a tutti"
        "Buongiorno!"             → "Buongiorno"
        "Mr. Smith ha detto qcs." → "Mr. Smith ha detto qcs"  (mantiene "Mr.")
        "Frase, virgole, sì?"     → "Frase, virgole, sì"      (mantiene virgole)
        "Domanda?!"               → "Domanda"
    """
    if not text:
        return text
    # rstrip ricorsivo: gestisce combinazioni "?!", "...", ":..", " . ", ecc.
    # I caratteri inclusi coprono la punteggiatura di chiusura ASCII + alcuni
    # tipografici (… — – -) che XTTS gestisce male a fine frase. Le virgole
    # NON sono incluse perché in italiano/spagnolo possono terminare clausole
    # legittime (rare ma non hallucination-trigger).
    return text.rstrip().rstrip(".!?;:…—–-").rstrip()


def _find_split_point(text: str) -> int:
    """Trova posizione di split ottimale per dividere `text` in due chunk
    di durata simile, preferendo confini sintattici naturali.

    Strategia (in ordine):
      1. Virgola/punto-virgola/due punti più vicini al centro (range ±25%)
         → split DOPO il segno (spazio successivo incluso quando presente).
      2. Spazio più vicino al centro (stesso range).
      3. Fallback: split forzato a metà (può rompere parola, ultima risorsa).

    Ritorna l'indice di split (carattere a `text[idx]` apparterrà al secondo
    chunk). Su testi <2 chars ritorna 0 (chiamante deve guardare la lunghezza
    prima di chiamare).
    """
    n = len(text or "")
    if n < 2:
        return 0
    mid = n // 2
    search_range = max(10, n // 4)
    # Step 1: virgola / punto-virgola / due punti vicino al centro.
    for offset in range(search_range):
        for pos in (mid + offset, mid - offset):
            if 0 < pos < n and text[pos] in ",;:":
                # Split DOPO il segno; salta lo spazio se c'è.
                cut = pos + 1
                if cut < n and text[cut] == " ":
                    cut += 1
                return cut
    # Step 2: spazio centrale.
    for offset in range(search_range):
        for pos in (mid + offset, mid - offset):
            if 0 < pos < n and text[pos] == " ":
                return pos + 1  # secondo chunk parte dal char successivo
    # Step 3: fallback duro a metà.
    return mid


def _concat_wavs(paths: list[str], output: str) -> None:
    """Concatena WAV listati in `paths` scrivendoli in `output` con un piccolo
    crossfade (50ms) ai punti di giunzione, per evitare click udibili dovuti
    al brusco cambio di ampiezza tra chunk.

    Usato in v2.5.2 dalla strategia di retry XTTS/CosyVoice "split del testo a
    metà" quando i retry multi-seed non hanno rotto l'hallucination loop.

    Vincoli:
      - Tutti i WAV devono avere lo stesso sample rate (assumiamo sì: stessi
        modelli TTS). Se differiscono usiamo il sample rate del primo file.
      - Mono o stereo: gestito dalla forma (numpy 1D vs 2D) restituita da
        soundfile.read.
      - Se un file è troppo corto per il crossfade (<50ms) viene concatenato
        secco senza fade: meglio un piccolo click che zero output.
    """
    import soundfile as sf  # type: ignore
    import numpy as np  # type: ignore

    if not paths:
        raise ValueError("_concat_wavs: empty paths list")

    chunks: list = []
    sr: int | None = None
    for p in paths:
        data, this_sr = sf.read(p)
        if sr is None:
            sr = this_sr
        chunks.append(data)
    if sr is None or sr <= 0:
        raise ValueError("_concat_wavs: unable to read sample rate")

    crossfade_samples = int(sr * 0.05)  # 50ms
    out = chunks[0]
    for chunk in chunks[1:]:
        if len(out) >= crossfade_samples and len(chunk) >= crossfade_samples and crossfade_samples > 0:
            fade_out = np.linspace(1.0, 0.0, crossfade_samples)
            fade_in = np.linspace(0.0, 1.0, crossfade_samples)
            # Gestione mono/stereo: se 2D, broadcasta sulla dim canali.
            if out.ndim == 2:
                fade_out = fade_out[:, None]
                fade_in = fade_in[:, None]
            tail = out[-crossfade_samples:] * fade_out + chunk[:crossfade_samples] * fade_in
            out = np.concatenate([out[:-crossfade_samples], tail, chunk[crossfade_samples:]])
        else:
            out = np.concatenate([out, chunk])
    sf.write(output, out, sr)


def _measure_wav_duration_s(path: str) -> float:
    """Ritorna la durata in secondi di un wav (o altro formato leggibile da
    soundfile/ffprobe). Wrapper su `_probe_duration_ms` che converte il valore
    in float-seconds. 0.0 se la probe fallisce — il chiamante deve guardare.

    Usato da v2.2 in `generate_tts_xtts` per detectare hallucination XTTS:
    confronto fra durata effettiva e predicted (`_estimate_tts_duration_s`).
    """
    ms = _probe_duration_ms(path)
    return ms / 1000.0 if ms > 0 else 0.0


def _probe_duration_ms(path: str) -> int:
    """Ritorna la durata in millisecondi di un file audio.
    Prova prima soundfile.info (veloce, no subprocess). Su libsndfile datati
    (< 1.1) sf.info può fallire su MP3 generati da Edge-TTS → fallback ffprobe.
    Se entrambi falliscono, logga un warning e ritorna 0.
    """
    try:
        import soundfile as sf
        info = sf.info(path)
        if info.samplerate:
            return int(info.frames * 1000 / info.samplerate)
    except Exception:
        pass
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0", path,
            ],
            capture_output=True, text=True, check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return int(float(r.stdout.strip()) * 1000)
    except Exception as e:
        print(f"     ! ffprobe duration fallback failed for {path}: {e}", flush=True)
    print(f"     ! Could not probe duration for {path} (sf.info + ffprobe failed)", flush=True)
    return 0


def build_dubbed_track(
    segments: list[dict],
    tts_files: list[str],
    bg_path: str | None,
    total_duration: float,
    tmp_dir: str,
    bg_volume: float = 0.15,
    label: str = "[6/6] Assembling dubbed track...",
    metrics_csv_path: str | None = None,
) -> str:
    """Assembla la traccia doppiata in streaming via numpy memmap.
    Evita di accumulare AudioSegment in RAM (~600 MB per video 1h+): il mix avviene
    in-place su un file PCM 16-bit 44.1 kHz stereo che coincide 1:1 con il formato
    di output storico.
    """
    import numpy as np
    import soundfile as sf

    print(label, flush=True)
    SR = 44100
    CH = 2
    total_frames = int(total_duration * SR)
    out = os.path.join(tmp_dir, "track_dubbed.wav")

    # DIAGNOSTIC: traccia per-segment metrics — alimenta sia il diagnostic
    # aggregato (distribuzione bucket + top 10 worst) sia il dump CSV
    # opzionale per analisi P90/P95 cross-video. Lista di dict invece di
    # tuple anonime per evolverla senza rompere consumer esistenti.
    _atempo_stats: list[dict] = []

    # Tier strategy per stretch audio (TASK 2C-2):
    # - ratio <= 1.15 → atempo (default, ok per stretch leggeri)
    # - 1.15 < ratio <= 1.50 → rubberband CLI se disponibile (no chipmunk)
    # - ratio > 1.50 → atempo (rubberband stesso degrada oltre 1.5x)
    # Probe del binario UNA volta sola: select_stretch_engine() falla cleanly
    # ad atempo se il binary manca, quindi nessuna regressione.
    _rubberband_available = shutil.which("rubberband") is not None
    if _rubberband_available:
        print("     [info] Rubber Band CLI available — using for ratio 1.15-1.50 band", flush=True)
    rubberband_used = 0
    atempo_used = 0

    # Raw PCM int32 in memmap: serve headroom per sommare senza saturare durante
    # gli overlay, si clampa a int16 alla fine.
    raw_path = os.path.join(tmp_dir, "_track_mix.raw")
    mix = np.memmap(raw_path, dtype=np.int32, mode="w+", shape=(total_frames, CH))
    # Azzera esplicitamente (memmap 'w+' lo fa, ma su alcuni FS conviene forzare).
    mix[:] = 0

    def _overlay(pcm: np.ndarray, start_frame: int):
        end_frame = min(start_frame + pcm.shape[0], total_frames)
        length = end_frame - start_frame
        if length <= 0:
            return
        # Somma int32: i sample TTS sono int16 (±32k), gli int32 hanno ±2G.
        mix[start_frame:end_frame] += pcm[:length].astype(np.int32)

    def _read_segment_to_pcm(path: str) -> np.ndarray | None:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        try:
            data, sr = sf.read(path, dtype="int16", always_2d=True)
        except Exception as e:
            print(f"     ! Cannot read {path}: {e}", flush=True)
            return None
        if data.size == 0:
            return None
        # Resample/reformat a 44.1 kHz stereo via ffmpeg se necessario (fast path
        # quando matcha già il target).
        if sr == SR and data.shape[1] == CH:
            return data
        conv = os.path.join(tmp_dir, Path(path).stem + "_pcm.wav")
        try:
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", path,
                "-ar", str(SR), "-ac", str(CH), "-sample_fmt", "s16", conv,
            ], step=f"pcm conv {Path(path).name}")
            return sf.read(conv, dtype="int16", always_2d=True)[0]
        except Exception as e:
            print(f"     ! PCM conv failed {path}: {e}", flush=True)
            return None

    for i, (seg, tts_file) in enumerate(zip(segments, tts_files)):
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)
        slot_ms = max(end_ms - start_ms, 1)

        # Per-segment engine record. 'none' means TTS fit the slot already.
        # Distinguishes 'atempo' (chosen by policy) from 'atempo_fallback'
        # (rubberband attempted and failed) for the metrics CSV.
        _seg_engine_used = "none"

        # Se il TTS eccede lo slot (più 50 ms di margine), applica atempo via ffmpeg.
        src_path = tts_file
        tts_ms_probed = 0
        ratio_raw = 1.0
        if os.path.exists(tts_file) and os.path.getsize(tts_file) > 0:
            tts_ms_probed = _probe_duration_ms(tts_file)
            if slot_ms > 0:
                ratio_raw = tts_ms_probed / slot_ms
            if tts_ms_probed > slot_ms + 50:
                ratio = max(1.0, min(ratio_raw, 4.0))
                sped = os.path.join(tmp_dir, f"seg_{i:04d}_sped.wav")
                # Dispatch: la policy pura sceglie engine in base al ratio
                # (ed alla disponibilità del binary rubberband). Outside del
                # range 1.15–1.50, oppure quando rubberband manca, ricade su atempo.
                engine = _select_stretch_engine(ratio, _rubberband_available)
                _initial_engine = engine
                stretch_ok = False
                if engine == "rubberband":
                    cmd = _build_rubberband_command(tts_file, sped, ratio)
                    try:
                        proc = subprocess.run(
                            cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                        )
                        if proc.returncode != 0:
                            err_tail = (proc.stderr or "").strip().splitlines()[-10:]
                            raise RuntimeError(
                                f"rubberband seg {i} failed (exit {proc.returncode}):\n"
                                + "\n".join(err_tail)
                            )
                        # Rubber Band conserva il sample rate dell'input;
                        # _read_segment_to_pcm gestisce la conversione a SR/CH
                        # quando differisce, quindi non serve un ffmpeg extra qui.
                        rubberband_used += 1
                        src_path = sped
                        stretch_ok = True
                        _seg_engine_used = "rubberband"
                    except Exception as e:
                        # FALLBACK: nessuna regressione vs comportamento legacy.
                        # Se rubberband fallisce per qualsiasi motivo, riproviamo
                        # con atempo come se il binary non esistesse.
                        print(f"     ! rubberband failed seg {i}: {e}; retrying with atempo", flush=True)
                        engine = "atempo"

                if engine == "atempo":
                    chain = _build_atempo_chain(ratio)
                    try:
                        _run_ffmpeg([
                            "ffmpeg", "-y", "-i", tts_file,
                            "-filter:a", chain,
                            "-ar", str(SR), "-ac", str(CH), "-sample_fmt", "s16", sped,
                        ], step=f"atempo seg {i}")
                        src_path = sped
                        atempo_used += 1
                        stretch_ok = True
                        # Mark as fallback if rubberband had been the initial choice.
                        _seg_engine_used = (
                            "atempo_fallback" if _initial_engine == "rubberband" else "atempo"
                        )
                    except Exception as e:
                        print(f"     ! atempo failed seg {i}: {e}", flush=True)
                # Se entrambi gli engine sono falliti, src_path resta tts_file
                # (audio non compresso); il successivo hard-truncate con fade-out
                # gestirà l'overshoot. Comportamento storico.
                _ = stretch_ok  # lint: variabile usata solo per leggibilità del flow

        pcm = _read_segment_to_pcm(src_path)
        if pcm is None:
            continue

        # Hard-truncate con fade-out se ancora troppo lungo dopo atempo.
        slot_frames = int(slot_ms * SR / 1000)
        truncated = pcm.shape[0] > slot_frames
        if truncated:
            pcm = pcm[:slot_frames].copy()
            fade_len = max(1, min(int(0.08 * SR), pcm.shape[0] // 4))
            # Fade lineare su int16 → calcolato in float32 poi riconvertito.
            ramp = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
            tail = pcm[-fade_len:].astype(np.float32) * ramp[:, None]
            pcm[-fade_len:] = tail.astype(np.int16)

        # Diagnostic: registra sempre (anche i segmenti "fit", ratio <=1.0).
        _atempo_stats.append({
            "segment_index": i,
            "start_s": seg["start"],
            "end_s": seg["end"],
            "slot_s": slot_ms / 1000.0,
            "src_chars": len((seg.get("text_src") or "")),
            "tgt_chars": len((seg.get("text_tgt") or "")),
            "target_chars": seg.get("_target_chars", 0),
            "length_retry_attempted": bool(seg.get("_length_retry_attempted", False)),
            "length_retry_succeeded": bool(seg.get("_length_retry_succeeded", False)),
            "tts_duration_ms": tts_ms_probed,
            "pre_stretch_ratio": round(ratio_raw, 4),
            "stretch_engine": _seg_engine_used,
            "stretch_truncated": truncated,
            "text_src": seg.get("text_src", ""),
            "text_tgt": seg.get("text_tgt", ""),
        })

        start_frame = int(start_ms * SR / 1000)
        _overlay(pcm, start_frame)

    # DIAGNOSTIC: stampa distribuzione atempo (attivo sempre, output sintetico).
    if _atempo_stats:
        _buckets = [
            ("ratio <= 1.00  (no atempo needed):  ", lambda r: r <= 1.00),
            ("1.00 < ratio <= 1.10 (imperceptible):", lambda r: 1.00 < r <= 1.10),
            ("1.10 < ratio <= 1.30 (mild):         ", lambda r: 1.10 < r <= 1.30),
            ("1.30 < ratio <= 1.50 (noticeable):   ", lambda r: 1.30 < r <= 1.50),
            ("1.50 < ratio <= 2.00 (strong):       ", lambda r: 1.50 < r <= 2.00),
            ("ratio > 2.00   (severe):             ", lambda r: r > 2.00),
        ]
        total = len(_atempo_stats)
        trunc_count = sum(1 for s in _atempo_stats if s["stretch_truncated"])
        print(f"     --- ATEMPO DIAGNOSTIC: {total} segments ---", flush=True)
        for label_b, pred in _buckets:
            n = sum(1 for s in _atempo_stats if pred(s["pre_stretch_ratio"]))
            pct = 100.0 * n / total if total else 0.0
            print(f"       {label_b} {n:>4d}  ({pct:5.1f}%)", flush=True)
        print(f"       truncated after atempo:              {trunc_count:>4d}  ({100.0*trunc_count/total:.1f}%)", flush=True)
        # Top 10 worst per ratio
        worst = sorted(_atempo_stats, key=lambda s: -s["pre_stretch_ratio"])[:10]
        print(f"     --- Top 10 worst segments (highest ratio) ---", flush=True)
        for s in worst:
            mm, ss = divmod(int(s["start_s"]), 60)
            t_mark = "TRUNC" if s["stretch_truncated"] else "     "
            slot_ms_v = int(s["slot_s"] * 1000)
            print(
                f"       #{s['segment_index']:04d} @ {mm:02d}:{ss:02d}  "
                f"slot={slot_ms_v:>5d}ms  tts={s['tts_duration_ms']:>5d}ms  "
                f"ratio={s['pre_stretch_ratio']:5.2f}  {t_mark}",
                flush=True,
            )
        print(f"     --- end diagnostic ---", flush=True)
        # TASK 2C-2: stampa la ripartizione engine usati per stretch.
        # Utile in produzione per verificare che la tier strategy funzioni
        # come atteso (rubberband concentrato nel band 1.15–1.50).
        if rubberband_used + atempo_used > 0:
            print(
                f"     -> Stretch engines: {rubberband_used} rubberband, "
                f"{atempo_used} atempo",
                flush=True,
            )

        # STEP 1: dump per-segment metrics CSV for cross-video P90/P95 analysis.
        # Best effort: never fail the dubbing pipeline if the file is unwritable.
        if metrics_csv_path:
            try:
                n = _dump_segment_metrics(_atempo_stats, metrics_csv_path)
                print(
                    f"     -> Metrics CSV: {n} rows -> {metrics_csv_path}",
                    flush=True,
                )
            except Exception as _csv_err:
                print(
                    f"     ! Metrics CSV dump failed ({_csv_err}); pipeline continues",
                    flush=True,
                )

    # Mix background se disponibile (stessa semantica storica: bg_volume in ampiezza).
    if bg_path and os.path.exists(bg_path) and bg_volume > 0:
        bg_conv = os.path.join(tmp_dir, "_bg_pcm.wav")
        try:
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", bg_path,
                "-ar", str(SR), "-ac", str(CH), "-sample_fmt", "s16", bg_conv,
            ], step="bg pcm conv")
            # Streaming read/write per tenere il background fuori dalla RAM.
            CHUNK = SR * 10  # 10s
            with sf.SoundFile(bg_conv, "r") as bgf:
                # Scala su int32 in-place. Ampiezza lineare: 1.0 = unity,
                # >1.0 amplifica (coerente con semantica storica pydub+dB).
                scale = float(bg_volume)
                pos = 0
                while pos < total_frames:
                    want = min(CHUNK, total_frames - pos)
                    block = bgf.read(want, dtype="int16", always_2d=True)
                    if block.shape[0] == 0:
                        break
                    if scale != 1.0:
                        scaled = (block.astype(np.float32) * scale).astype(np.int32)
                    else:
                        scaled = block.astype(np.int32)
                    end_pos = pos + scaled.shape[0]
                    mix[pos:end_pos] += scaled
                    pos = end_pos
        except Exception as e:
            print(f"     ! Background mix failed: {e}", flush=True)

    # Clamp int32 → int16 e serializza in WAV.
    with sf.SoundFile(out, "w", samplerate=SR, channels=CH, subtype="PCM_16") as outf:
        CHUNK = SR * 10
        pos = 0
        while pos < total_frames:
            end = min(pos + CHUNK, total_frames)
            block = mix[pos:end]
            clipped = np.clip(block, -32768, 32767).astype(np.int16)
            outf.write(clipped)
            pos = end

    # Libera la memmap prima di unlink per evitare warning su Windows.
    del mix
    try:
        os.remove(raw_path)
    except OSError:
        pass

    # Normalize to -23 LUFS (EBU R128 broadcast standard).
    # Leggiamo in float32 (dimezza la RAM rispetto al default float64).
    # Per video molto lunghi (>30 min o >1.5 GB) logghiamo un warning: l'intero
    # buffer resta comunque in memoria perché pyln.normalize.loudness richiede
    # l'array completo, ma almeno con float32 siamo gestibili (~1.2 GB per 1h).
    try:
        import pyloudnorm as pyln
        try:
            track_bytes = os.path.getsize(out)
        except OSError:
            track_bytes = 0
        long_track = (total_duration > 1800.0) or (track_bytes > 1_500_000_000)
        if long_track:
            print(
                f"     ! Long track detected (duration={total_duration:.0f}s, "
                f"size={track_bytes/1e6:.0f} MB): LUFS normalization will use "
                f"float32 in-memory buffer.",
                flush=True,
            )
        data, rate = sf.read(out, dtype="float32")
        meter = pyln.Meter(rate)
        loudness = meter.integrated_loudness(data)
        if loudness > -70:
            normalized = pyln.normalize.loudness(data, loudness, -23.0)
            sf.write(out, normalized, rate)
            print(f"     → Normalized: {loudness:.1f} LUFS → -23.0 LUFS", flush=True)
    except Exception as e:
        print(f"     ! Loudness normalization skipped: {e}", flush=True)

    print(f"     → Track: {out}", flush=True)
    return out


def save_subtitles(segments: list[dict], output_base: str):
    def fmt(s: float) -> str:
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        ms = int((sec % 1) * 1000)
        return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{ms:03d}"

    path = output_base + ".srt"
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            text = (seg.get("text_tgt") or "").strip()
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{text}\n\n")
    print(f"[+] Subtitles: {path}", flush=True)


def get_duration(video_path: str) -> float:
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", video_path
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {r.stderr.strip()}")
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Cannot read duration of {video_path}: {e}")


def mux_video(video_input: str, audio_track: str, output_path: str):
    print(f"[+] Muxing → {output_path}", flush=True)
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", video_input, "-i", audio_track,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0", output_path
    ], step="mux_video")


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


def _resolve_wav2lip_dir() -> Path:
    """Return the directory that should host Wav2Lip repo + model.

    Priority (cross-platform unified path):
      1. system-wide install dir populated by the Windows/Linux installer
         (%ProgramFiles%\\VideoTranslatorAI\\wav2lip on Windows,
          /opt/VideoTranslatorAI/wav2lip on Linux), adopted only when it is
         **fully populated** (repo clone AND model weights) **and actually
         writable** by the current user — otherwise a later mkdir/git clone
         under ProgramFiles or /opt would raise PermissionError without
         falling back to the user-level path.

         Writability is checked with a real tempfile probe
         (``_is_dir_user_writable``) instead of ``os.access(..., os.W_OK)``
         because on Windows the latter ignores NTFS ACLs / UAC virtualisation
         and routinely reports ``True`` for Program Files directories that
         would in fact reject writes from a non-elevated process.
      2. per-user fallback: ~/.local/share/wav2lip (legacy path, always
         writable, used when the installer has not pre-seeded a complete
         system-wide copy).

    The system-wide branch prevents a double 416 MB download on Windows when
    ``install_windows.bat`` has already placed the assets under ProgramFiles.
    """
    candidates: list[Path] = []
    if sys.platform.startswith("win"):
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidates.append(Path(program_files) / "VideoTranslatorAI" / "wav2lip")
    else:
        candidates.append(Path("/opt/VideoTranslatorAI/wav2lip"))
    for cand in candidates:
        # AND (not OR): both repo and weights must be present, otherwise the
        # caller will try to mkdir/clone under a read-only system path.
        repo_ok   = (cand / "Wav2Lip" / "inference.py").exists()
        model_ok  = (cand / "wav2lip_gan.pth").exists()
        if repo_ok and model_ok and _is_dir_user_writable(cand):
            return cand
    return Path.home() / ".local" / "share" / "wav2lip"


WAV2LIP_DIR     = _resolve_wav2lip_dir()
WAV2LIP_REPO    = WAV2LIP_DIR / "Wav2Lip"
WAV2LIP_MODEL   = WAV2LIP_DIR / "wav2lip_gan.pth"
WAV2LIP_REPO_URL  = "https://github.com/Rudrabha/Wav2Lip.git"
WAV2LIP_MODEL_URL = "https://huggingface.co/numz/wav2lip_studio/resolve/main/Wav2lip/wav2lip_gan.pth"
WAV2LIP_TIMEOUT = 3600  # seconds before Wav2Lip subprocess is forcibly killed

# Base deps needed by Wav2Lip on all platforms; dlib + face-detection extras
# are handled separately below (different install strategy per OS).
WAV2LIP_BASE_PKGS = ["opencv-python", "librosa", "tqdm"]
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
# time) AND installs the SAME top-level `basicsr` package — every
# `import basicsr...` in Wav2Lip / facexlib keeps working unchanged.
WAV2LIP_FACE_PKGS = ["new-basicsr", "facexlib"]

_active_subprocesses: set[subprocess.Popen] = set()
_active_subprocesses_lock = threading.Lock()


def _register_subprocess(proc: subprocess.Popen) -> None:
    """Add a running subprocess to the global registry under a lock."""
    with _active_subprocesses_lock:
        _active_subprocesses.add(proc)


def _unregister_subprocess(proc: subprocess.Popen) -> None:
    """Remove a subprocess from the global registry under a lock."""
    with _active_subprocesses_lock:
        _active_subprocesses.discard(proc)


def _snapshot_active_subprocesses() -> list[subprocess.Popen]:
    """Return a list copy of the registry while holding the lock.

    Iteration / .terminate() happens outside the lock so we never block
    worker threads trying to register a new subprocess on a slow kill.
    """
    with _active_subprocesses_lock:
        return list(_active_subprocesses)


def _install_wav2lip_face_stack_linux() -> None:
    """Install dlib + new-basicsr + facexlib on Linux with a cmake pre-check.

    dlib has no official PyPI wheels for Linux; pip must compile from source
    via cmake + libboost. We pre-check for cmake and emit an actionable error
    instead of letting pip dump a long traceback.

    `new-basicsr` is a maintained fork of the abandoned `basicsr` 1.4.2 — it
    ships a pre-built wheel and installs as the same `basicsr` module, which
    sidesteps the `KeyError: '__version__'` build failure of the original on
    Python 3.13 (PEP 667 broke its setup.py exec/locals pattern).
    `facexlib` is pure Python and installs cleanly regardless.
    """
    # new-basicsr + facexlib are cheap (wheel + pure python), install them
    # first so lipsync can at least attempt to run even if dlib is missing.
    res = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet",
         "--break-system-packages"] + WAV2LIP_FACE_PKGS,
        check=False,
    )
    if res.returncode != 0:
        print("     ! new-basicsr/facexlib install failed — lipsync face detection may not work.", flush=True)

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
            "       Then rerun this tool — Wav2Lip lipsync will be retried automatically.",
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


def _ensure_wav2lip_assets():
    """Ensure Wav2Lip repo and GAN weights are available locally."""
    WAV2LIP_DIR.mkdir(parents=True, exist_ok=True)

    if not WAV2LIP_REPO.exists():
        print(f"     Cloning Wav2Lip repo → {WAV2LIP_REPO}", flush=True)
        if not shutil.which("git"):
            raise RuntimeError("git not found: required to clone Wav2Lip repo")
        subprocess.run(
            ["git", "clone", "--depth", "1", WAV2LIP_REPO_URL, str(WAV2LIP_REPO)],
            check=True, capture_output=True,
        )
        # Install only the packages Wav2Lip needs that aren't already present
        # (skip the repo's requirements.txt — it pins ancient versions incompatible with Python 3.13+)
        print(f"     Installing Wav2Lip base deps: {', '.join(WAV2LIP_BASE_PKGS)}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--break-system-packages"] + WAV2LIP_BASE_PKGS,
            check=False,
        )
        if result.returncode != 0:
            print("     ! Some Wav2Lip base deps failed to install — lipsync may not work.", flush=True)

        # Face-detection stack (dlib + basicsr + facexlib). On Windows we rely
        # on install_windows.bat to ship pre-built dlib wheels; here on Linux
        # we install them at first use.
        if not sys.platform.startswith("win"):
            _install_wav2lip_face_stack_linux()

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


def apply_lipsync(video_path: str, audio_path: str, tmp_dir: str) -> str:
    """Sync lips of video_path with audio_path via Wav2Lip. Returns path to synced video."""
    print("[+] Applying Lip Sync (Wav2Lip)...", flush=True)
    _ensure_wav2lip_assets()

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # Free VRAM before starting subprocess so Wav2Lip finds GPU available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        device = "cpu"
    print(f"     Wav2Lip device: {device}", flush=True)

    inference_py = WAV2LIP_REPO / "inference.py"
    if not inference_py.exists():
        raise RuntimeError(f"Wav2Lip inference script not found: {inference_py}")

    out_path = os.path.join(tmp_dir, "video_lipsync.mp4")

    cmd = [
        sys.executable, str(inference_py),
        "--checkpoint_path", str(WAV2LIP_MODEL),
        "--face", video_path,
        "--audio", audio_path,
        "--outfile", out_path,
        "--nosmooth",
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(WAV2LIP_REPO) + os.pathsep + env.get("PYTHONPATH", "")

    # Stream output line-by-line so the GUI log shows progress in real time
    output_lines: list[str] = []
    proc = subprocess.Popen(
        cmd, cwd=str(WAV2LIP_REPO), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    _register_subprocess(proc)
    # Watchdog: kill Wav2Lip if it hangs beyond timeout
    _watchdog = threading.Timer(WAV2LIP_TIMEOUT, proc.kill)
    _watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            print(f"     [wav2lip] {line}", flush=True)
        proc.wait()
    except Exception:
        proc.kill()
        proc.wait()
        raise
    finally:
        _watchdog.cancel()
        _unregister_subprocess(proc)
        # Clean up Wav2Lip temp/ to avoid disk accumulation
        wav2lip_tmp = WAV2LIP_REPO / "temp"
        if wav2lip_tmp.exists():
            shutil.rmtree(wav2lip_tmp, ignore_errors=True)

    if proc.returncode != 0 or not os.path.exists(out_path):
        tail = "\n".join(output_lines[-20:])
        raise RuntimeError(f"Wav2Lip failed (exit {proc.returncode}):\n{tail}")

    print(f"     → Lip sync done: {out_path}", flush=True)
    return out_path


CONFIG_PATH = Path.home() / ".videotranslatorai_config.json"
KEYRING_SERVICE = "VideoTranslatorAI"
KEYRING_USERNAME = "hf_token"
_KEYRING_MIGRATED = False

from videotranslator.config import (  # noqa: E402
    load_json_config as _load_json_config,
    merge_json_config as _merge_json_config,
    write_json_config as _write_json_config,
)
from videotranslator.secrets import (  # noqa: E402
    import_keyring_backend as _import_keyring_backend,
    load_secret_token as _load_secret_token,
    save_secret_token as _save_secret_token,
)


def load_config() -> dict:
    return _load_json_config(CONFIG_PATH)


def _write_config_raw(cfg: dict) -> None:
    """Scrive il dict cfg (intero, non in merge) con permessi 0600 atomicamente.
    Usare questa quando serve rimuovere chiavi; save_config fa merge e non
    cancellerebbe nulla.
    """
    _write_json_config(CONFIG_PATH, cfg)


def save_config(data: dict) -> None:
    try:
        _merge_json_config(CONFIG_PATH, data)
    except Exception as e:
        print(f"     ! Could not save config: {e}", flush=True)


def _keyring_available():
    """Ritorna il modulo keyring se disponibile, altrimenti None."""
    return _import_keyring_backend()


def load_hf_token() -> str:
    """Legge il token HF: prima dal keyring, poi (migrazione) dal JSON legacy."""
    return _load_secret_token(
        keyring_backend=_keyring_available(),
        config_path=CONFIG_PATH,
        service_name=KEYRING_SERVICE,
        username=KEYRING_USERNAME,
    )


def save_hf_token(token: str) -> None:
    """Salva il token HF nel system keyring. Fallback JSON se keyring manca."""
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
    # Inizializza pipeline a None prima del try così il finally non crasha
    # con NameError se from_pretrained solleva.
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


def _extract_speaker_reference(
    vocals_path: str, diar_segments: list[dict], speaker: str,
    tmp_dir: str, max_duration: float = 30.0,
) -> str | None:
    """Concat up to max_duration seconds of clean vocals from one speaker."""
    turns = [d for d in diar_segments if d["speaker"] == speaker]
    if not turns:
        return None
    # Prefer longer turns first (cleaner reference)
    turns.sort(key=lambda d: d["end"] - d["start"], reverse=True)
    selected: list[tuple[float, float]] = []
    total = 0.0
    for d in turns:
        dur = d["end"] - d["start"]
        if dur < 1.0:
            continue
        take = min(dur, max_duration - total)
        if take <= 0:
            break
        selected.append((d["start"], d["start"] + take))
        total += take
        if total >= max_duration:
            break
    if not selected:
        return None

    # Build ffmpeg concat via filter_complex trim
    import re as _re
    safe_spk = _re.sub(r'[^A-Za-z0-9_-]', '_', speaker)
    out = os.path.join(tmp_dir, f"ref_{safe_spk}.wav")
    filter_parts = []
    for i, (s, e) in enumerate(selected):
        filter_parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}]")
    concat_inputs = "".join(f"[a{i}]" for i in range(len(selected)))
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(selected)}:v=0:a=1[out]"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", vocals_path,
            "-filter_complex", filter_complex,
            "-map", "[out]", "-ar", "22050", "-ac", "1", out,
        ], capture_output=True, check=True)
        return out
    except subprocess.CalledProcessError as e:
        print(f"     ! Could not extract reference for {speaker}: {e}", flush=True)
        return None


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
    tts_engine: str = "edge",   # "edge" | "xtts" | "cosyvoice" (v2.3)
    use_diarization: bool = False,
    hf_token: str = "",
    use_lipsync: bool = False,
    xtts_speed: float | None = None,
    ollama_model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    ollama_slot_aware: bool = True,
    ollama_thinking: bool = False,
    slot_expansion: bool = True,
) -> dict:
    """
    Main pipeline. Returns dict with output paths and segments.
    segments_override: skip transcription+translation and use these segments (GUI editor).

    `xtts_speed`: se None (default) viene calcolato via `_suggest_xtts_speed`
    in base alla coppia (lang_source, lang_target). Se fornito esplicitamente
    (config JSON con chiave presente / CLI --xtts-speed / parametro GUI futuro)
    viene rispettato senza modifiche. Questa è la leva principale per ridurre
    l'atempo post-processing su coppie asimmetriche tipo EN→IT.
    """
    if lang_target not in LANGUAGES:
        raise ValueError(f"Unsupported target language: {lang_target}")
    if not os.path.exists(video_in):
        raise FileNotFoundError(f"Video not found: {video_in}")

    # Autotune dello speed XTTS in base alla coppia di lingue. Rispetta sempre
    # un override esplicito (xtts_speed non-None). Calcolato qui, una sola volta
    # per chiamata, così sia il log iniziale sia l'invocazione di generate_tts_xtts
    # usano lo stesso valore.
    effective_xtts_speed, lang_ratio, speed_auto = _suggest_xtts_speed(
        lang_source, lang_target, xtts_speed,
    )
    # Caso "target molto più lungo del source" (ratio >= 1.20): oltre allo speed
    # auto-tuned, rendiamo anche il merge dei segmenti più aggressivo, così
    # l'italiano/francese tradotto ha slot più capienti da riempire. Il
    # gate `speed_auto` assicura che un utente v1.4 con `xtts_speed` pinnato
    # in config non veda cambiare silenziosamente anche il merge (i due dial
    # si muovono insieme: o entrambi auto, o entrambi a default).
    merge_aggressive = speed_auto and lang_ratio >= 1.20

    voice = voice or LANGUAGES[lang_target]["voices"][0]
    stem  = Path(video_in).stem
    if not output:
        input_dir = Path(video_in).parent
        tmp_root  = Path(tempfile.gettempdir())
        try:
            input_dir.relative_to(tmp_root)
            is_tmp = True
        except ValueError:
            is_tmp = False
        if is_tmp:
            videos_dir = _default_videos_dir()
            videos_dir.mkdir(parents=True, exist_ok=True)
            output = str(videos_dir / f"{stem}_{lang_target}.mp4")
        else:
            output = str(input_dir / f"{stem}_{lang_target}.mp4")
    output_base = str(Path(output).with_suffix(""))

    print(f"[i] {Path(video_in).name} | {lang_source}→{lang_target} | {voice}", flush=True)
    if tts_engine in ("xtts", "cosyvoice"):
        # Log esplicito di cosa ha deciso l'autotune. Utile in bug report / debug
        # di atempo artifacts. CosyVoice riusa lo stesso autotune (lo speed
        # range è equivalente; il ceiling è speso allo stesso modo nel loop
        # adattivo per-segmento).
        if speed_auto:
            _ratio_note = f"auto-tuned for {lang_source}→{lang_target}, ratio={lang_ratio:.2f}"
        else:
            _ratio_note = f"user override (ratio={lang_ratio:.2f})"
        _engine_label = "XTTS" if tts_engine == "xtts" else "CosyVoice"
        print(f"[i] {_engine_label} speed={effective_xtts_speed:.2f} ({_ratio_note}){' [aggressive merge]' if merge_aggressive else ''}", flush=True)

    with tempfile.TemporaryDirectory(prefix="vidtrans_") as tmp_dir:
        audio_raw = os.path.join(tmp_dir, "audio_raw.wav")
        extract_audio(video_in, audio_raw)

        bg_path = None
        vocals_path = audio_raw

        if not no_demucs:
            try:
                vocals_path, bg_path = separate_audio(audio_raw, tmp_dir)
            except Exception as e:
                print(f"     ! Demucs failed ({e}), proceeding without separation", flush=True)
                vocals_16k = os.path.join(tmp_dir, "audio_16k.wav")
                _run_ffmpeg([
                    "ffmpeg", "-y", "-i", audio_raw, "-ar", "16000", "-ac", "1", vocals_16k
                ], step="resample audio")
                vocals_path = vocals_16k
        else:
            vocals_16k = os.path.join(tmp_dir, "audio_16k.wav")
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", audio_raw, "-ar", "16000", "-ac", "1", vocals_16k
            ], step="resample audio")
            vocals_path = vocals_16k

        diar_segments: list[dict] = []
        if segments_override is not None:
            segments = segments_override
        else:
            raw_segs, detected_lang = transcribe(vocals_path, model, lang_source)
            effective_src = detected_lang if lang_source == "auto" else lang_source
            # Re-split su punteggiatura forte: dà a XTTS frasi complete invece di
            # cut mid-sentence di Whisper. Riduce hallucinations.
            pre_split = len(raw_segs)
            raw_segs = _split_on_punctuation(raw_segs)
            if len(raw_segs) > pre_split:
                print(f"     → Split on punctuation: {pre_split} → {len(raw_segs)}", flush=True)
            # Speaker diarization (before translation so speaker info propagates)
            if use_diarization and hf_token.strip():
                try:
                    diar_segments = diarize_audio(vocals_path, hf_token.strip())
                    raw_segs = assign_speakers(raw_segs, diar_segments)
                except Exception as e:
                    print(f"     ! Diarization failed ({e.__class__.__name__}: {e}), continuing without speaker info.", flush=True)
                    diar_segments = []
            # Merge dei segmenti troppo brevi per ridurre hallucinations XTTS
            # e produrre frasi più naturali per la traduzione. Su coppie con
            # target molto più lungo della source (ratio >= 1.20, es. EN→IT)
            # usiamo bound più generosi per dare al TTS slot più capienti.
            pre_merge = len(raw_segs)
            raw_segs = _merge_short_segments(raw_segs, aggressive=merge_aggressive)
            if len(raw_segs) < pre_merge:
                _note = " (aggressive)" if merge_aggressive else ""
                print(f"     → Merged short segments{_note}: {pre_merge} → {len(raw_segs)}", flush=True)
            # TASK 2E: smart slot expansion / time borrowing. Tight segments
            # (expected pre_stretch_ratio > 1.50) "rubano" tempo dai gap
            # silenziosi successivi e — se il vicino è sotto-utilizzato —
            # anche dall'inizio del suo slot. Riduce l'atempo udibile senza
            # toccare il testo o la traduzione. Disabilitabile con
            # --no-slot-expansion per A/B test in caso di regressioni.
            if slot_expansion:
                _exp_tgt = LANG_EXPANSION.get(
                    lang_target,
                    LANG_EXPANSION.get(lang_target.split("-")[0], 1.0),
                )
                _exp_src = LANG_EXPANSION.get(
                    effective_src,
                    LANG_EXPANSION.get((effective_src or "").split("-")[0], 1.0),
                ) or 1.0
                _expansion_factor = _exp_tgt / _exp_src if _exp_src > 0 else 1.0
                _orig_segs = [dict(s) for s in raw_segs]
                raw_segs = _expand_tight_slots(
                    raw_segs, lang_target, expansion_factor=_expansion_factor,
                )
                _n_expanded = sum(
                    1 for a, b in zip(_orig_segs, raw_segs)
                    if (b["end"] - b["start"]) > (a["end"] - a["start"]) + 1e-6
                )
                if _n_expanded > 0:
                    print(
                        f"     → Expanded {_n_expanded}/{len(raw_segs)} tight segments "
                        f"by borrowing silence",
                        flush=True,
                    )
            segments = translate_segments(
                raw_segs, effective_src, lang_target,
                engine=translation_engine, deepl_key=deepl_key,
                ollama_model=ollama_model, ollama_url=ollama_url,
                ollama_slot_aware=ollama_slot_aware,
                ollama_thinking=ollama_thinking,
            )

        if not no_subs:
            save_subtitles(segments, output_base)

        if subs_only:
            print("\n[+] --subs-only mode complete.")
            return {"srt": output_base + ".srt", "segments": segments}

        # TTS generation — Edge-TTS, Coqui XTTS v2 o CosyVoice (v2.3).
        # Cascata di fallback: cosyvoice → xtts → edge. Se l'utente ha scelto
        # cosyvoice e fallisce, proviamo XTTS prima di degradare a Edge-TTS,
        # così l'utente che sceglie un voice-cloning engine non si ritrova
        # automaticamente con voci sintetiche piatte.
        tts_files = None
        if tts_engine == "cosyvoice":
            try:
                tts_files = generate_tts_cosyvoice(
                    segments, vocals_path, lang_target, tmp_dir,
                    diar_segments=diar_segments,
                    speed=effective_xtts_speed,  # ceiling condiviso con XTTS
                )
            except Exception as e:
                print(f"     ! CosyVoice failed ({e}), falling back to XTTS.", flush=True)
                tts_files = None
            # Fallback intra-clone: prima di scendere a Edge-TTS, tentiamo XTTS
            # (l'utente ha esplicitamente chiesto voice cloning).
            if tts_files is None:
                try:
                    tts_files = generate_tts_xtts(
                        segments, vocals_path, lang_target, tmp_dir,
                        diar_segments=diar_segments,
                        speed=effective_xtts_speed,
                    )
                except Exception as e:
                    print(f"     ! XTTS fallback failed ({e}), falling back to Edge-TTS.", flush=True)
                    tts_files = None
        elif tts_engine == "xtts":
            try:
                tts_files = generate_tts_xtts(
                    segments, vocals_path, lang_target, tmp_dir,
                    diar_segments=diar_segments,
                    speed=effective_xtts_speed,
                )
            except Exception as e:
                print(f"     ! XTTS failed ({e}), falling back to Edge-TTS.", flush=True)
                tts_files = None
        if tts_files is None:
            tts_files = generate_tts(segments, voice, tmp_dir, rate=tts_rate)
        duration  = get_duration(video_in)
        track     = build_dubbed_track(
            segments, tts_files, bg_path, duration, tmp_dir,
            metrics_csv_path=output_base + "_metrics.csv",
        )
        mux_video(video_in, track, output)

        if use_lipsync:
            # TASK 2H: pre-check faces with cv2 Haar Cascade. Wav2Lip would
            # otherwise spend 30-60s reading every frame just to fail with
            # "Face not detected" on voice-only content (podcasts, screen
            # recordings, voice-over animations). The pre-check samples 15
            # frames in ~1s and skips Wav2Lip cleanly when no face is present.
            _face_dir = os.path.join(tmp_dir, "_face_check")
            _has_face, _face_ratio, _face_n, _face_total = _has_enough_faces(
                video_in, _face_dir
            )
            if not _has_face:
                print(
                    f"     [face-check] {_face_n}/{_face_total} sampled frames "
                    f"contain a face (ratio {_face_ratio:.2f}); skipping Wav2Lip "
                    f"— voice-only or no-face video",
                    flush=True,
                )
            else:
                print(
                    f"     [face-check] {_face_n}/{_face_total} sampled frames "
                    f"contain a face (ratio {_face_ratio:.2f}); proceeding with Wav2Lip",
                    flush=True,
                )
                try:
                    # Build a vocals-only track (no background music) for accurate lip sync
                    track_vocals = build_dubbed_track(segments, tts_files, None, duration, tmp_dir,
                                                       label="[6/6] Assembling vocals track for lip-sync...")
                    synced = apply_lipsync(output, track_vocals, tmp_dir)
                    shutil.move(synced, output)
                except Exception as e:
                    print(f"     ! Lip sync failed ({e.__class__.__name__}: {e}), keeping video without lip sync.", flush=True)

    print(f"\n[✓] Done: {output}")
    return {"video": output, "srt": output_base + ".srt", "segments": segments}


# ═══════════════════════════════════════════════════════════
#  GUI HELPERS
# ═══════════════════════════════════════════════════════════

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
        return self._original.write(s)

    def flush(self):
        redir = getattr(_thread_local, "redirect", None)
        if redir is not None:
            redir.flush()
        else:
            self._original.flush()

    def fileno(self):
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
        buf, self._buf = self._buf, []  # atomic swap under GIL — safe against concurrent append()
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
    def __init__(self, parent, segments: list[dict], on_confirm, ui_s=None):
        super().__init__(parent)
        self._s = ui_s if callable(ui_s) else (lambda k: UI_STRINGS["it"].get(k, k))
        self.title(self._s("editor_title"))
        self.configure(bg=BG)
        self.geometry("900x600")
        self.segments   = [s.copy() for s in segments]
        self.on_confirm = on_confirm

        tk.Label(self, text=self._s("editor_hint"),
                 bg=BG, fg=FG2, font=("Helvetica", 9)).pack(pady=(10, 4))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=12, pady=4)

        cols = (self._s("editor_col_num"), self._s("editor_col_start"),
                self._s("editor_col_end"), self._s("editor_col_orig"),
                self._s("editor_col_trans"))
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


# ═══════════════════════════════════════════════════════════
#  MAIN GUI APP
# ═══════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Translator AI")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._set_window_icon()

        self._ui_lang   = tk.StringVar(value="it")
        self._model     = tk.StringVar(value="small")
        self._lang_src  = tk.StringVar(value="auto")
        self._lang_tgt  = tk.StringVar(value="it")
        self._voice     = tk.StringVar(value=LANGUAGES["it"]["voices"][0])
        self._tts_rate  = tk.IntVar(value=0)
        self._subs_only = tk.BooleanVar(value=False)
        self._no_subs   = tk.BooleanVar(value=False)
        self._no_demucs = tk.BooleanVar(value=False)
        self._edit_subs = tk.BooleanVar(value=False)
        self._use_xtts  = tk.BooleanVar(value=False)
        # v2.3: CosyVoice 2.0 come terzo TTS engine. Mutuamente esclusivo con
        # XTTS — gestito via callback `_on_voice_clone_toggle` sotto.
        self._use_cosyvoice = tk.BooleanVar(value=False)
        self._use_lipsync = tk.BooleanVar(value=False)
        # Translation engine: "google" | "deepl" | "marian" | "llm_ollama"
        self._translation_engine = tk.StringVar(value="google")
        self._deepl_key_var      = tk.StringVar()
        # Ollama LLM config (v2.0) — preset da config JSON se presente
        _ocfg = load_config()
        self._ollama_model_var   = tk.StringVar(
            value=_ocfg.get("ollama_model", "qwen3:8b")
        )
        self._ollama_url_var     = tk.StringVar(
            value=_ocfg.get("ollama_url", "http://localhost:11434")
        )
        self._ollama_slot_aware  = tk.BooleanVar(
            value=_ocfg.get("ollama_slot_aware", True)
        )
        # Thinking mode su Qwen3: default OFF (veloce). Se True il modello
        # delibera step-by-step (~5x più lento, riduce errori idiomi/grammatica).
        self._ollama_thinking    = tk.BooleanVar(
            value=_ocfg.get("ollama_thinking", False)
        )
        # Diarization: il token HF è persistito nel system keyring (con migrazione
        # automatica dal vecchio JSON legacy).
        self._use_diarization = tk.BooleanVar(value=False)
        self._hf_token_var    = tk.StringVar(value=load_hf_token())
        self._running    = False
        self._destroying = False
        # Guard re-entrancy: durante il setup async di Ollama (detect / install
        # / start daemon / pull model) blocchiamo doppi trigger da Start /
        # Download. Non usiamo `_running` perché quello scatta solo quando
        # parte la pipeline vera, non durante il pre-flight.
        self._ollama_setup_in_flight = False
        self._batch_files: list[str] = []
        self._url_placeholder_active = True
        self._pending_pkgs_after_ffmpeg: list[str] = []

        self._build_ui()
        # Restore log panel visibility from config (default True)
        self._log_visible = bool(_ocfg.get("ui_log_visible", True))
        if not self._log_visible:
            self._log_container.grid_remove()
            self._btn_log_toggle.configure(text=self._s("btn_log_show"))
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Minimum window size + reasonable default geometry so the window
        # remains usable on small displays (1366×768, 1280×720) and at
        # Windows scaling 125%/150%. The form area is wrapped in a Canvas
        # with a vertical Scrollbar (see `_build_ui`), so even when the
        # window is resized below the form's natural height the user can
        # scroll to reach every control. Log + progress bar stay outside
        # the canvas and remain visible at all times.
        self.minsize(900, 600)
        self.geometry("1100x780")
        self.after(100, self._fit_to_screen)
        self.after(200, self._check_deps_on_start)
        self.after(800, self._upgrade_ytdlp_in_background)
        self._optional_checked = False

        # Install global redirect once — routes print() to per-thread GUI log
        sys.stdout = _GlobalRedirect(sys.stdout)
        sys.stderr = _GlobalRedirect(sys.stderr)

    def _set_window_icon(self) -> None:
        """Set the window icon from the bundled assets folder.

        Gracefully falls back to the default Tk icon if assets/ is missing or
        the image cannot be loaded — common e.g. when the GUI is launched
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
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        # Clamp to screen but enforce a usable minimum (matches `self.minsize`
        # set in __init__). When the form is taller than the screen, the
        # Canvas + Scrollbar in `_build_ui` lets the user reach every row.
        # Prefer the explicit geometry hint (1100x780) over reqsize, because the
        # form lives inside a Canvas-wrapped frame and reqwidth from the Canvas
        # under-reports the form's actual width.
        win_w = max(1100, min(self.winfo_reqwidth(),  screen_w - 40))
        win_h = max(780,  min(self.winfo_reqheight(), screen_h - 80))
        # But never exceed a strict minimum that defeats the purpose on small screens.
        win_w = max(win_w, 900)
        win_h = max(win_h, 600)
        x = (screen_w - win_w) // 2
        y = max(0, (screen_h - win_h) // 2 - 20)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _s(self, key: str) -> str:
        # Fallback chain: current UI lang → it → en → key (literal)
        # Necessario quando una chiave è stata aggiunta solo a it/en (es. nuove
        # feature introdotte incrementalmente) per evitare che gli utenti delle
        # altre 24 lingue vedano nomi di chiavi raw al posto della label tradotta.
        lang = self._ui_lang.get()
        for bucket in (UI_STRINGS.get(lang, {}), UI_STRINGS["it"], UI_STRINGS["en"]):
            if key in bucket:
                return bucket[key]
        return key

    # ── Dependency check ─────────────────────────────────────────────────────

    def _check_deps_on_start(self):
        missing_pkgs, missing_bins = check_dependencies()
        if not missing_pkgs and not missing_bins:
            # Nothing required to install — safe to check optional now
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
        self._btn.configure(state="disabled", text=self._s("btn_installing"))
        self._progress.start(12)
        self._log_write("[*] ffmpeg not found — installing automatically...\n")

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
            # NB: proc.wait(timeout=…) non scatta se pip si blocca senza
            # chiudere stdout, perché il for-loop su proc.stdout si ferma lì.
            # Un Timer che killa il processo garantisce lo sblocco (l'iteratore
            # su stdout solleva o ritorna EOF appena il processo muore).
            PIP_TIMEOUT = 600
            timed_out = {"fired": False}

            def _on_timeout():
                timed_out["fired"] = True
                with contextlib.suppress(Exception):
                    proc.kill()
                # On Windows, TerminateProcess does not always unblock a
                # pending read on the child's stdout pipe immediately —
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
                               f"    ! pip install timed out after {PIP_TIMEOUT}s — aborting.\n")
                    ok = False
                else:
                    ok = proc.returncode == 0
            except Exception:
                # Se il timeout watchdog ha chiuso stdout, l'iteratore qui
                # solleva — stampiamo comunque il messaggio di timeout così
                # l'utente vede la causa invece di un generico "Installation failed".
                if timed_out["fired"]:
                    self.after(0, self._log_write,
                               f"    ! pip install timed out after {PIP_TIMEOUT}s — aborting.\n")
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
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        if ok:
            self._log_write(f"[✓] Installed: {', '.join(packages)}\n")
        else:
            self._log_write("[✗] Installation failed. Check the log above for details.\n")
        # Required install chain finished — safe to check optional packages now
        self.after(300, self._check_optional_deps)

    def _upgrade_ytdlp_in_background(self):
        """Silently upgrade yt-dlp in a daemon thread; logs only if a new version is installed.

        Rispetta il flag `yt_dlp_auto_upgrade` in config (default True). Se l'utente
        lo imposta a False (es. su sistemi PEP 668 dove non vuole che l'env venga
        modificato), l'upgrade è skippato silenziosamente.
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
                        # m3: regex che evita trailing dot (es. "yt-dlp-2024.10.")
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

        # TASK 2C-2: suggerimento non-bloccante per Rubber Band CLI su Linux.
        # È un binario di sistema (apt/dnf/pacman), non installabile via pip,
        # quindi non rientra nel popup di OPTIONAL_PACKAGES. Loggiamo solo:
        # se manca, build_dubbed_track userà comunque atempo (no regressione).
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

        names_str = "\n".join(f"  • {pkgs[0]} — {desc}" for pkgs, desc in items)
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

    def _build_ui(self):
        pad = {"padx": 16, "pady": 5}

        # ── Outer layout (3 rows on the root window) ─────────────────────
        # row 0: scrollable canvas hosting the entire form
        # row 1: log panel (always visible, outside the canvas so the user
        #        can keep watching pipeline output while scrolling the form)
        # row 2: progress bar
        # The canvas approach lets the GUI stay usable on small displays
        # (1366×768, 1280×720) and on Windows 125%/150% scaling without
        # truncating the Start button or the option rows.
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._main_canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self._main_canvas.grid(row=0, column=0, sticky="nsew")
        main_vsb = tk.Scrollbar(self, orient="vertical",
                                command=self._main_canvas.yview)
        main_vsb.grid(row=0, column=1, sticky="ns")
        self._main_canvas.configure(yscrollcommand=main_vsb.set)

        self._main_frame = tk.Frame(self._main_canvas, bg=BG)
        self._main_canvas_window = self._main_canvas.create_window(
            (0, 0), window=self._main_frame, anchor="nw")

        # Keep scrollregion in sync with the inner frame's natural size.
        self._main_frame.bind(
            "<Configure>",
            lambda e: self._main_canvas.configure(
                scrollregion=self._main_canvas.bbox("all")))
        # Stretch the inner frame to the canvas width so the existing
        # column-weighted grid still expands horizontally as expected.
        self._main_canvas.bind(
            "<Configure>",
            lambda e: self._main_canvas.itemconfig(
                self._main_canvas_window, width=e.width))

        # Header: title + UI language selector
        header = tk.Frame(self._main_frame, bg=BG)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(16, 2))
        header.columnconfigure(0, weight=1)

        tk.Label(header, text="🎬 Video Translator AI",
                 font=("Helvetica", 16, "bold"), bg=BG, fg=FG).grid(row=0, column=0, sticky="w")

        lang_sel = tk.Frame(header, bg=BG)
        lang_sel.grid(row=0, column=1, sticky="e")
        self._lbl_ui_lang = tk.Label(lang_sel, text=self._s("label_ui_lang"),
                                     bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_ui_lang.pack(side="left", padx=(0, 4))
        self._ui_lang_combo = ttk.Combobox(lang_sel,
                                            values=[lbl for _, lbl in UI_LANG_OPTIONS],
                                            state="readonly", width=22, font=("Helvetica", 8))
        self._ui_lang_combo.current(0)
        self._ui_lang_combo.pack(side="left")
        self._ui_lang_combo.bind("<<ComboboxSelected>>", self._on_ui_lang_change)

        tk.Label(self._main_frame, text="faster-whisper  •  Demucs  •  Google Translate  •  Edge-TTS / XTTS v2",
                 font=("Helvetica", 9), bg=BG, fg=FG2).grid(row=1, column=0, columnspan=3)

        ttk.Separator(self._main_frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=6)

        # Batch file list
        self._lbl_video = self._row_label(3, self._s("label_video"))
        batch_frame = tk.Frame(self._main_frame, bg=BG)
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
        self._btn_add    = tk.Button(btn_col, text=self._s("btn_add"),
                                     command=self._add_files, bg=SEL, fg=FG, relief="flat", width=10)
        self._btn_add.pack(pady=2)
        self._btn_remove = tk.Button(btn_col, text=self._s("btn_remove"),
                                     command=self._remove_file, bg=SEL, fg=FG, relief="flat", width=10)
        self._btn_remove.pack(pady=2)
        self._btn_clear  = tk.Button(btn_col, text=self._s("btn_clear"),
                                     command=self._clear_files, bg=SEL, fg=FG, relief="flat", width=10)
        self._btn_clear.pack(pady=2)

        # Output
        self._lbl_output = self._row_label(4, self._s("label_output"))
        self._output_var = tk.StringVar()
        tk.Entry(self._main_frame, textvariable=self._output_var, width=42,
                 bg=SEL, fg=FG, insertbackground=FG,
                 relief="flat", font=("Helvetica", 9)).grid(
            row=4, column=1, sticky="ew", padx=(0, 6), pady=5)
        self._btn_browse = tk.Button(self._main_frame, text=self._s("btn_browse"),
                                     command=self._browse_output, bg="#45475a", fg=FG, relief="flat")
        self._btn_browse.grid(row=4, column=2, padx=(0, 16))

        # URL download field
        self._lbl_url = self._row_label(5, self._s("label_url"))
        url_frame = tk.Frame(self._main_frame, bg=BG)
        url_frame.grid(row=5, column=1, columnspan=2, sticky="ew", **pad)
        self._url_text = tk.Text(url_frame, height=2, width=52,
                                  bg=SEL, fg=FG, insertbackground=FG,
                                  font=("Monospace", 8), relief="flat", wrap="none")
        self._url_text.insert("1.0", self._s("url_placeholder"))
        self._url_text.configure(fg=FG2)
        self._url_text.bind("<FocusIn>",  self._url_focus_in)
        self._url_text.bind("<FocusOut>", self._url_focus_out)
        self._url_text.pack(side="left", fill="both", expand=True)
        self._btn_download = tk.Button(url_frame, text=self._s("btn_download"),
                                        command=self._start_download,
                                        bg=GRN, fg=BG, font=("Helvetica", 9, "bold"),
                                        relief="flat", padx=8, cursor="hand2")
        self._btn_download.pack(side="left", padx=(6, 0))

        ttk.Separator(self._main_frame, orient="horizontal").grid(
            row=6, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # Whisper model
        self._lbl_model = self._row_label(7, self._s("label_model"))
        mf = tk.Frame(self._main_frame, bg=BG)
        mf.grid(row=7, column=1, columnspan=2, sticky="w", **pad)
        for m in WHISPER_MODELS:
            tk.Radiobutton(mf, text=m, variable=self._model, value=m,
                           bg=BG, fg=RED if "large" in m else FG,
                           selectcolor=SEL, activebackground=BG,
                           font=("Helvetica", 9)).pack(side="left", padx=3)
        self._lbl_model_hint = tk.Label(mf, text=self._s("label_model_hint"),
                                         bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_model_hint.pack(side="left", padx=6)

        # Source language
        self._lbl_from = self._row_label(8, self._s("label_from"))
        src_frame = tk.Frame(self._main_frame, bg=BG)
        src_frame.grid(row=8, column=1, columnspan=2, sticky="w", **pad)
        self._src_combo = ttk.Combobox(src_frame, values=list(SOURCE_LANGS.values()),
                                        state="readonly", width=22, font=("Helvetica", 9))
        self._src_combo.current(0)
        self._src_combo.pack(side="left")
        src_keys = list(SOURCE_LANGS.keys())
        self._src_combo.bind("<<ComboboxSelected>>",
                              lambda e, k=src_keys: self._lang_src.set(k[self._src_combo.current()]))

        # Target language
        self._lbl_to = self._row_label(9, self._s("label_to"))
        tgt_frame = tk.Frame(self._main_frame, bg=BG)
        tgt_frame.grid(row=9, column=1, columnspan=2, sticky="w", **pad)
        self._tgt_combo = ttk.Combobox(tgt_frame, values=[v["name"] for v in LANGUAGES.values()],
                                        state="readonly", width=22, font=("Helvetica", 9))
        self._tgt_combo.current(list(LANGUAGES.keys()).index("it"))
        self._tgt_combo.pack(side="left")
        self._tgt_combo.bind("<<ComboboxSelected>>", self._on_lang_tgt_change)

        # Voice
        self._lbl_voice = self._row_label(10, self._s("label_voice"))
        self._voice_frame = tk.Frame(self._main_frame, bg=BG)
        self._voice_frame.grid(row=10, column=1, columnspan=2, sticky="w", **pad)
        self._build_voice_buttons()

        # TTS rate
        self._lbl_tts_rate = self._row_label(11, self._s("label_tts_rate"))
        rate_frame = tk.Frame(self._main_frame, bg=BG)
        rate_frame.grid(row=11, column=1, columnspan=2, sticky="w", **pad)
        tk.Label(rate_frame, text="-50%", bg=BG, fg=FG2, font=("Helvetica", 8)).pack(side="left")
        ttk.Scale(rate_frame, from_=-50, to=50, variable=self._tts_rate,
                  orient="horizontal", length=200).pack(side="left", padx=6)
        tk.Label(rate_frame, text="+50%", bg=BG, fg=FG2, font=("Helvetica", 8)).pack(side="left")
        self._rate_lbl = tk.Label(rate_frame, text="+0%", bg=BG, fg=ACC,
                                   font=("Helvetica", 9, "bold"), width=6)
        self._rate_lbl.pack(side="left", padx=4)
        self._tts_rate.trace_add("write", self._update_rate_label)

        ttk.Separator(self._main_frame, orient="horizontal").grid(
            row=12, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # Options
        self._lbl_options = self._row_label(13, self._s("label_options"))
        opts = tk.Frame(self._main_frame, bg=BG)
        opts.grid(row=13, column=1, columnspan=2, sticky="w", **pad)

        def cb(parent, text_key, var, cmd=None):
            w = tk.Checkbutton(parent, text=self._s(text_key), variable=var, command=cmd,
                               bg=BG, fg=FG, selectcolor=SEL,
                               activebackground=BG, font=("Helvetica", 9))
            w._text_key = text_key
            return w

        _opy = {"pady": (4, 0)}
        self._chk_subs_only = cb(opts, "opt_subs_only", self._subs_only, self._on_subs_only)
        self._chk_subs_only.grid(row=0, column=0, sticky="w", **_opy)
        self._chk_no_subs   = cb(opts, "opt_no_subs",   self._no_subs,   self._on_no_subs)
        self._chk_no_subs.grid(row=1, column=0, sticky="w", **_opy)
        self._chk_no_demucs = cb(opts, "opt_no_demucs", self._no_demucs)
        self._chk_no_demucs.grid(row=0, column=1, sticky="w", padx=16, **_opy)
        self._chk_edit_subs = cb(opts, "opt_edit_subs", self._edit_subs)
        self._chk_edit_subs.grid(row=1, column=1, sticky="w", padx=16, **_opy)
        # XTTS + Lipsync su row 2 in layout 2-colonne coerente con i checkbox
        # sopra (col 0 / col 1). La versione precedente metteva lipsync in col=2
        # con XTTS che occupava col 0+1: questo rendeva lipsync invisibile
        # quando il riquadro Ollama (row=6, col 0+1 columnspan=2) si dilatava
        # con il toggle thinking, perché col=2 finiva fuori dall'area visibile.
        # La selezione del checkbox XTTS resetta CosyVoice (mutuamente esclusivi).
        self._chk_xtts = cb(opts, "opt_xtts", self._use_xtts, self._on_xtts_toggle)
        self._chk_xtts.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._chk_lipsync = cb(opts, "opt_lipsync", self._use_lipsync)
        self._chk_lipsync.grid(row=2, column=1, sticky="w", padx=16, pady=(8, 0))
        # v2.3: nuovo checkbox CosyVoice in row dedicata sotto XTTS+Lipsync.
        # Mutual exclusion con XTTS gestita via _on_cosyvoice_toggle. Le row
        # successive del frame `opts` (translation engine, deepl, hf token,
        # diarization) sono indicizzate da row=3 in giù: usiamo row=2 con un
        # pady incrementato che lo stacking visualmente subito sotto _chk_xtts.
        # Tk gestisce row duplicate concatenandole nello stesso slot logico
        # ma manteniamo lo sticky="w" per non collidere con le colonne 1-2.
        self._chk_cosyvoice = cb(opts, "opt_cosyvoice", self._use_cosyvoice, self._on_cosyvoice_toggle)
        # Riga dedicata fra XTTS (row=2) e translation engine (row=3): scegliamo
        # un indice intermedio. Tk consente float-equivalenti via gestione
        # sequenziale solo con interi, quindi shift sotto: spostiamo la
        # translation engine row a row=4 e successive.
        self._chk_cosyvoice.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 4))
        # MODIFICA LOCALE (non committata) -- 2026-04-26
        # Checkbox CosyVoice 2.0 nascosta in attesa che l'integrazione upstream
        # diventi production-ready (PyPI `cosyvoice` rotto + WeTextProcessing
        # C++ build hell su Windows). Tutto il codice/i18n/scaffolding resta in
        # place: per riabilitare basta commentare la riga `grid_remove()` qui
        # sotto. Tentativo Cowork del 2026-04-26 fallito, in attesa di:
        #   - fix upstream PyPI `cosyvoice` (community wrapper Lucas Jin)
        #   - oppure CosyVoice 2.0 ufficiale (FunAudioLLM) pubblicato su PyPI
        #   - oppure scelta di TTS alternativo (F5-TTS, OpenVoice, Qwen3-TTS)
        # Riferimenti: helper a riga ~4222-4373, i18n keys `opt_cosyvoice` &
        # `msg_cosyvoice_*` & `hint_cosyvoice` su 26 lingue (riga 311+).
        self._chk_cosyvoice.grid_remove()

        # Translation engine radio group (row=4 dopo l'inserimento di
        # _chk_cosyvoice in row=3, v2.3).
        engine_row = tk.Frame(opts, bg=BG)
        engine_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._lbl_engine = tk.Label(engine_row, text=self._s("label_engine"),
                                    bg=BG, fg=FG, font=("Helvetica", 9, "bold"))
        self._lbl_engine.pack(side="left")
        self._rb_eng_google = tk.Radiobutton(
            engine_row, text=self._s("engine_google"),
            variable=self._translation_engine, value="google",
            command=self._on_engine_change,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 9))
        self._rb_eng_google.pack(side="left", padx=(6, 0))
        self._rb_eng_deepl = tk.Radiobutton(
            engine_row, text=self._s("engine_deepl"),
            variable=self._translation_engine, value="deepl",
            command=self._on_engine_change,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 9))
        self._rb_eng_deepl.pack(side="left", padx=(6, 0))
        self._rb_eng_marian = tk.Radiobutton(
            engine_row, text=self._s("engine_marian"),
            variable=self._translation_engine, value="marian",
            command=self._on_engine_change,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 9))
        self._rb_eng_marian.pack(side="left", padx=(6, 0))

        # Ollama LLM radio (v2.0). Nota: la label è lunga (descrive la feature)
        # perciò occupa una riga a sé sotto il row dei tre radio "classici".
        engine_row2 = tk.Frame(opts, bg=BG)
        engine_row2.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._rb_eng_ollama = tk.Radiobutton(
            engine_row2, text=self._s("engine_ollama"),
            variable=self._translation_engine, value="llm_ollama",
            command=self._on_engine_change,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 9))
        self._rb_eng_ollama.pack(side="left")

        # Ollama config row (visible only when llm_ollama selected)
        self._ollama_row = tk.Frame(opts, bg=BG)
        self._ollama_row.grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._lbl_ollama_model = tk.Label(self._ollama_row, text=self._s("label_ollama_model"),
                                          bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_ollama_model.pack(side="left")
        # Combobox invece di Entry: default + alternative suggerite nel task
        self._ollama_model_combo = ttk.Combobox(
            self._ollama_row, textvariable=self._ollama_model_var, width=28,
            values=[
                "qwen3:8b",                  # Default raccomandato (Qwen3, 5.2 GB)
                "qwen3:4b",                  # Leggero (Qwen3, ~3 GB)
                "qwen3:14b",                 # Qualità superiore (~9 GB)
                "qwen2.5:7b-instruct",       # Fallback compat (Qwen2.5)
                "llama3.2:3b-instruct",      # Esistente
                "mistral-nemo:12b-instruct", # Esistente
            ],
            font=("Monospace", 8),
        )
        self._ollama_model_combo.pack(side="left", padx=(4, 8))
        self._lbl_ollama_url = tk.Label(self._ollama_row, text=self._s("label_ollama_url"),
                                        bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_ollama_url.pack(side="left")
        self._ollama_url_entry = tk.Entry(
            self._ollama_row, textvariable=self._ollama_url_var, width=24,
            bg=SEL, fg=FG, insertbackground=FG, relief="flat",
            font=("Monospace", 8))
        self._ollama_url_entry.pack(side="left", padx=(4, 8))
        self._chk_ollama_slot = tk.Checkbutton(
            self._ollama_row, text="slot-aware",
            variable=self._ollama_slot_aware,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 8))
        self._chk_ollama_slot.pack(side="left", padx=(4, 0))
        self._ollama_row.grid_remove()  # hidden until llm_ollama selected

        # Ollama thinking row (riga dedicata): tenere il toggle thinking sulla
        # stessa riga di model+url+slot-aware ingrossava troppo `_ollama_row`,
        # spingendo lipsync (col=2 di `opts`) fuori dall'area visibile e
        # rendendo poco leggibile l'hint. Riga separata = label larga ok,
        # nessun impatto sulla larghezza delle altre colonne. Il toggle
        # disabilita il suffix `/no_think` nel prompt e invia `think:True` al
        # daemon. Solo Qwen3 risponde al flag (altri modelli lo ignorano).
        self._ollama_row2 = tk.Frame(opts, bg=BG)
        self._ollama_row2.grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._chk_ollama_thinking = tk.Checkbutton(
            self._ollama_row2, text=self._s("opt_ollama_thinking"),
            variable=self._ollama_thinking,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 8))
        self._chk_ollama_thinking.pack(side="left")
        self._lbl_ollama_thinking_hint = tk.Label(
            self._ollama_row2, text="  " + self._s("hint_ollama_thinking"),
            bg=BG, fg=FG2, font=("Helvetica", 8, "italic"))
        self._lbl_ollama_thinking_hint.pack(side="left")
        self._ollama_row2.grid_remove()  # hidden until llm_ollama selected

        # DeepL API key row (visible only when DeepL selected)
        self._deepl_row = tk.Frame(opts, bg=BG)
        self._deepl_row.grid(row=8, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._lbl_deepl_key = tk.Label(self._deepl_row, text=self._s("label_deepl_key"),
                                       bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_deepl_key.pack(side="left")
        self._deepl_key_entry = tk.Entry(
            self._deepl_row, textvariable=self._deepl_key_var, width=32,
            bg=SEL, fg=FG, insertbackground=FG, relief="flat",
            font=("Monospace", 8), show="*")
        self._deepl_key_entry.pack(side="left", padx=(4, 0))
        self._deepl_row.grid_remove()  # hidden until DeepL selected

        # Diarization row
        diar_row = tk.Frame(opts, bg=BG)
        diar_row.grid(row=9, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._chk_diar = tk.Checkbutton(
            diar_row, text=self._s("opt_diarization"),
            variable=self._use_diarization,
            command=self._on_diarization_toggle,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 9))
        self._chk_diar.pack(side="left")

        self._hf_row = tk.Frame(opts, bg=BG)
        self._hf_row.grid(row=10, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._lbl_hf_token = tk.Label(self._hf_row, text=self._s("label_hf_token"),
                                      bg=BG, fg=FG2, font=("Helvetica", 8))
        self._lbl_hf_token.pack(side="left")
        self._hf_token_entry = tk.Entry(
            self._hf_row, textvariable=self._hf_token_var, width=40,
            bg=SEL, fg=FG, insertbackground=FG, relief="flat",
            font=("Monospace", 8), show="*")
        self._hf_token_entry.pack(side="left", padx=(4, 0))
        self._lbl_hf_hint = tk.Label(self._hf_row, text="  " + self._s("hint_hf_token"),
                                     bg=BG, fg=FG2, font=("Helvetica", 8, "italic"))
        self._lbl_hf_hint.pack(side="left")
        self._hf_row.grid_remove()  # hidden until diarization enabled

        ttk.Separator(self._main_frame, orient="horizontal").grid(
            row=14, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # Start button
        self._btn = tk.Button(self._main_frame, text=self._s("btn_start"), command=self._start,
                              bg=ACC, fg=BG, font=("Helvetica", 12, "bold"),
                              relief="flat", padx=20, pady=8, cursor="hand2",
                              activebackground="#74c7ec")
        self._btn.grid(row=15, column=0, columnspan=3, pady=8)

        # Log panel — toolbar + collapsible Text widget.
        # Stays a direct child of the root window (NOT inside the scrollable
        # canvas) so pipeline output remains visible while the user scrolls
        # the form above. Sits in row=1 of the root grid (canvas is row=0).
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="nsew")
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        log_header = tk.Frame(log_frame, bg=BG)
        log_header.grid(row=0, column=0, sticky="ew")
        self._lbl_log_panel = tk.Label(log_header, text=self._s("label_log_panel"),
                                       bg=BG, fg=FG, font=("Helvetica", 9, "bold"))
        self._lbl_log_panel.pack(side="left")
        self._btn_log_toggle = tk.Button(
            log_header, text=self._s("btn_log_hide"),
            command=self._toggle_log,
            bg=SEL, fg=FG, font=("Helvetica", 8),
            relief="flat", padx=8, pady=2, cursor="hand2",
            activebackground=ACC, activeforeground=BG)
        self._btn_log_toggle.pack(side="left", padx=(8, 0))
        self._btn_log_clear = tk.Button(
            log_header, text=self._s("btn_log_clear"),
            command=self._log_clear,
            bg=SEL, fg=FG, font=("Helvetica", 8),
            relief="flat", padx=8, pady=2, cursor="hand2",
            activebackground=ACC, activeforeground=BG)
        self._btn_log_clear.pack(side="right")
        self._btn_log_save = tk.Button(
            log_header, text=self._s("btn_log_save"),
            command=self._log_save,
            bg=SEL, fg=FG, font=("Helvetica", 8),
            relief="flat", padx=8, pady=2, cursor="hand2",
            activebackground=ACC, activeforeground=BG)
        self._btn_log_save.pack(side="right", padx=(0, 4))
        self._btn_log_copy = tk.Button(
            log_header, text=self._s("btn_log_copy"),
            command=self._log_copy,
            bg=SEL, fg=FG, font=("Helvetica", 8),
            relief="flat", padx=8, pady=2, cursor="hand2",
            activebackground=ACC, activeforeground=BG)
        self._btn_log_copy.pack(side="right", padx=(0, 4))

        self._log_container = tk.Frame(log_frame, bg=BG)
        self._log_container.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self._log_container.rowconfigure(0, weight=1)
        self._log_container.columnconfigure(0, weight=1)
        self._log = tk.Text(self._log_container, height=12, width=76,
                            bg="#11111b", fg=GRN, font=("Monospace", 8),
                            relief="flat", state="disabled", wrap="word")
        vsb = tk.Scrollbar(self._log_container, command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Progress bar — root child, row=2 (under the log panel).
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 12))

        # Inner-frame column weight so form widgets stretch horizontally
        # (column 1 hosts entries / combos / wrap frames).
        self._main_frame.columnconfigure(1, weight=1)

        # Cross-platform mouse wheel scrolling. Tk does not propagate the
        # MouseWheel event to children automatically, so we walk the tree
        # and bind on every descendant of the canvas + main frame.
        self._bind_mousewheel(self._main_canvas)
        self._bind_mousewheel(self._main_frame)

    def _row_label(self, row, text):
        # All form rows live inside `self._main_frame` (a child of the
        # scrollable canvas built in `_build_ui`). Anchoring labels to the
        # root would break the scrolling layout, so we route them through
        # the inner frame just like every other form widget.
        lbl = tk.Label(self._main_frame, text=text, bg=BG, fg="#bac2de",
                       font=("Helvetica", 9, "bold"), anchor="e")
        lbl.grid(row=row, column=0, sticky="e", padx=(16, 8), pady=7)
        return lbl

    # ── Mouse wheel scrolling for the form canvas ──────────────────────────

    def _on_mousewheel(self, event):
        """Scroll the form canvas in response to a wheel event.

        Cross-platform delta normalisation:
          * Linux delivers Button-4 (up) / Button-5 (down) without `delta`.
          * Windows / macOS deliver MouseWheel with `delta` in multiples
            of 120 (positive = up).
        """
        # Defensive: the canvas may have been destroyed mid-shutdown.
        if not hasattr(self, "_main_canvas"):
            return
        if sys.platform.startswith("linux"):
            delta = -1 if getattr(event, "num", 0) == 5 else 1
        else:
            delta = int(-1 * (event.delta / 120))
        try:
            self._main_canvas.yview_scroll(delta, "units")
        except tk.TclError:
            # Window being destroyed
            pass

    def _bind_mousewheel(self, widget):
        """Recursively bind wheel events on `widget` and all its descendants.

        Tk does not auto-propagate MouseWheel events to child widgets, so
        the canvas would otherwise stop scrolling as soon as the cursor
        hovers over any inner control (entry, combobox, button, ...).
        """
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")  # Win/Mac
            widget.bind("<Button-4>",   self._on_mousewheel, add="+")  # Linux up
            widget.bind("<Button-5>",   self._on_mousewheel, add="+")  # Linux down
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
        self._apply_lang()

    def _apply_lang(self):
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
        if not self._running:
            self._btn.configure(text=self._s("btn_start"))
        self._chk_subs_only.configure(text=self._s("opt_subs_only"))
        self._chk_no_subs.configure(text=self._s("opt_no_subs"))
        self._chk_no_demucs.configure(text=self._s("opt_no_demucs"))
        self._chk_edit_subs.configure(text=self._s("opt_edit_subs"))
        self._chk_xtts.configure(text=self._s("opt_xtts"))
        self._chk_cosyvoice.configure(text=self._s("opt_cosyvoice"))
        self._chk_lipsync.configure(text=self._s("opt_lipsync"))
        self._lbl_engine.configure(text=self._s("label_engine"))
        self._rb_eng_google.configure(text=self._s("engine_google"))
        self._rb_eng_deepl.configure(text=self._s("engine_deepl"))
        self._rb_eng_marian.configure(text=self._s("engine_marian"))
        self._rb_eng_ollama.configure(text=self._s("engine_ollama"))
        self._lbl_ollama_model.configure(text=self._s("label_ollama_model"))
        self._lbl_ollama_url.configure(text=self._s("label_ollama_url"))
        self._chk_ollama_thinking.configure(text=self._s("opt_ollama_thinking"))
        self._lbl_ollama_thinking_hint.configure(text="  " + self._s("hint_ollama_thinking"))
        self._lbl_deepl_key.configure(text=self._s("label_deepl_key"))
        self._chk_diar.configure(text=self._s("opt_diarization"))
        self._lbl_hf_token.configure(text=self._s("label_hf_token"))
        self._lbl_hf_hint.configure(text="  " + self._s("hint_hf_token"))
        # Log panel labels
        self._lbl_log_panel.configure(text=self._s("label_log_panel"))
        self._btn_log_toggle.configure(
            text=self._s("btn_log_hide" if getattr(self, "_log_visible", True) else "btn_log_show"))
        self._btn_log_copy.configure(text=self._s("btn_log_copy"))
        self._btn_log_save.configure(text=self._s("btn_log_save"))
        self._btn_log_clear.configure(text=self._s("btn_log_clear"))
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
        self._src_combo.bind("<<ComboboxSelected>>",
                              lambda e, k=src_keys: self._lang_src.set(k[self._src_combo.current()]))

    # ── Voice buttons ────────────────────────────────────────────────────────

    def _build_voice_buttons(self):
        for w in self._voice_frame.winfo_children():
            w.destroy()
        lang_key = list(LANGUAGES.keys())[self._tgt_combo.current()]
        voices   = LANGUAGES[lang_key]["voices"]
        self._voice.set(voices[0])
        for v in voices:
            label = v.split("-")[2].replace("Neural", "").replace("Multilingual", "ML")
            tk.Radiobutton(self._voice_frame, text=label, variable=self._voice, value=v,
                           bg=BG, fg=FG, selectcolor=SEL,
                           activebackground=BG, font=("Helvetica", 9)).pack(side="left", padx=3)

    def _on_lang_tgt_change(self, _=None):
        self._lang_tgt.set(list(LANGUAGES.keys())[self._tgt_combo.current()])
        self._build_voice_buttons()
        # Re-bind mousewheel to newly created voice radio buttons
        try:
            self._bind_mousewheel(self._voice_frame)
        except Exception:
            pass

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
            # Tutto in thread daemon, popup via self.after per thread safety.
            # Respect `ollama_auto_install` config flag (default True).
            self._ensure_ollama_ready_async(on_ready=None)
        else:
            self._ollama_row.grid_remove()
            self._ollama_row2.grid_remove()
        if eng == "marian":
            self._check_marian_deps()

    # ── TTS engine mutual exclusion (v2.3) ────────────────────────────────
    #
    # XTTS e CosyVoice sono due engine di voice cloning alternativi: non ha
    # senso averli entrambi attivi (vincerebbe comunque la dispatch in
    # `translate_video` che controlla `tts_engine` calcolato in
    # `_snapshot_params`). Per evitare confusione UI, on toggle di uno
    # deselezioniamo l'altro. Stessa logica che `_on_subs_only` applica a
    # subs_only/no_subs.

    def _on_xtts_toggle(self):
        if self._use_xtts.get() and self._use_cosyvoice.get():
            self._use_cosyvoice.set(False)

    def _on_cosyvoice_toggle(self):
        """User ha cliccato su CosyVoice: deseleziona XTTS e gestisce il caso
        "non installato" in modo onesto.

        Stato attuale (2026-04): il pacchetto PyPI `cosyvoice` 0.0.8 (community
        wrapper Lucas Jin) ha setup.py rotto su Python 3.13+ e CosyVoice 2.0
        ufficiale di Alibaba (FunAudioLLM/CosyVoice) richiede git clone +
        venv Python 3.10 isolato + torch==2.3.1 (incompatibile col nostro pin
        torch>=2.6). Quindi NON tentiamo l'auto-install via pip: fallirebbe
        sempre e l'utente vedrebbe il checkbox "auto-deselezionarsi" senza
        capire perché. Mostriamo invece un popup informativo che spiega lo
        stato sperimentale e linka le istruzioni manuali.

        Quando un giorno il pacchetto pip sarà fixato a monte, basterà
        rimuovere il branch "experimental info" e ripristinare l'auto-install.
        """
        if not self._use_cosyvoice.get():
            return  # toggle off → niente da fare
        # Mutual exclusion con XTTS
        if self._use_xtts.get():
            self._use_xtts.set(False)
        # Già installato? Mostra solo info modello (download on-demand al run)
        if _cosyvoice_is_installed():
            cache = _cosyvoice_cache_dir()
            if _cosyvoice_model_present(cache):
                self._log_write(f"[+] CosyVoice ready ({cache})\n")
            else:
                self._log_write(
                    f"[i] CosyVoice installato; modello (~1.7 GB) verrà "
                    f"scaricato al primo Avvia.\n"
                )
            return
        # NON installato — non tentiamo l'auto-install (rotto upstream).
        # Mostriamo info + auto-deselezione con messaggio chiaro nel log.
        messagebox.showinfo(
            "CosyVoice 2.0 — Sperimentale",
            "CosyVoice 2.0 è disponibile come feature sperimentale ma\n"
            "richiede setup manuale (il pacchetto pip ufficiale è\n"
            "temporaneamente rotto su Python 3.10+).\n\n"
            "Per abilitarlo:\n"
            "  1) git clone --recursive\n"
            "     https://github.com/FunAudioLLM/CosyVoice.git\n"
            "  2) Setup venv Python 3.10 con torch==2.3.1\n"
            "  3) Aggiungi la dir clonata a PYTHONPATH\n\n"
            "Per ora la pipeline userà XTTS v2 (raccomandato).\n"
            "Verifica il CHANGELOG per aggiornamenti."
        )
        self._log_write(
            "[i] CosyVoice 2.0 sperimentale: setup manuale richiesto. "
            "Userò XTTS per questa sessione.\n"
        )
        self._use_cosyvoice.set(False)
        # Riattiva XTTS (default raccomandato) se l'utente l'aveva attivo
        # prima di cliccare CosyVoice
        # NOTA: lasciato a discrezione utente, non forzo l'attivazione XTTS.

    # ── Ollama auto-setup (v2.0.1) ────────────────────────────────────────
    #
    # Flusso (tutto off-thread, UI sempre responsive):
    #   1. Binary → se manca: popup [Sì/No] → _ollama_install
    #   2. Daemon → se down: start in background, wait fino a 15s
    #   3. Modello → se manca: popup [Sì/No/Cambia modello] → ollama pull
    #   4. Ready
    # Edge: se config `ollama_auto_install=false`, salta install/pull e
    # cade sul fallback Google senza popup.
    #
    # `on_ready` è un callback opzionale invocato su main thread quando
    # Ollama è pronto (utile per chainare la pipeline di traduzione).
    # Se Ollama non è pronto al termine, `on_ready(False)` viene chiamato.

    def _ensure_ollama_ready_async(self, on_ready=None):
        """Entry point: spawn il worker di setup in thread daemon.

        `on_ready`: callback(bool) invocato su main thread; True se Ollama è
        pronto (daemon up + modello disponibile), False altrimenti. Se None,
        la funzione serve solo a "warm up" Ollama (caso radio select).
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

    def _ollama_setup_worker(self, model: str, url: str, auto_install: bool) -> bool:
        """Worker thread: esegue gli step 1-4. Ritorna True se Ollama è pronto.

        Questo è il cuore del flusso — ogni step ha un early-exit puntuale
        così da non accumulare state, e ogni popup è inoltrato al main
        thread tramite `_ask_yes_no_sync` (blocca il worker finché l'utente
        risponde, ma la GUI resta fluida).
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
        # Quick check first (cheap when daemon is already up — common on second runs).
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
                    # the existing daemon is fine — verify and use it.
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
                            f"[+] Port 11434 occupata da un altro daemon Ollama gia' attivo — "
                            f"riutilizzo quello.\n"
                        )
                    else:
                        self._log_async(f"[x] Daemon non avviato: {msg}\n")
                        return False

        # Step 3: model available?
        health_ok, health_msg = _ollama_health_check(url, model, timeout=5.0)
        if not health_ok:
            # Heuristic: è un problema di "modello mancante" o di "daemon giù"?
            # _ollama_health_check ritorna "not reachable" se è il secondo caso.
            if "not reachable" in (health_msg or "").lower():
                self._log_async(f"[x] Ollama non raggiungibile: {health_msg}\n")
                return False
            # Modello mancante → chiedi pull
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
            health_ok, health_msg = _ollama_health_check(url, model, timeout=5.0)
            if not health_ok:
                self._log_async(f"[x] Verifica post-pull fallita: {health_msg}\n")
                return False

        self._log_async(f"[+] Ollama pronto: {model} @ {url}\n")
        return True

    def _ask_yes_no_sync(self, title: str, message: str) -> bool:
        """Chiama messagebox.askyesno sul main thread e blocca il worker
        finché l'utente risponde. Usa un Event per il rendezvous.
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
        # Attendi max 5 minuti — oltre significa che il dialogo è stato perso.
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
        if self._running or self._ollama_setup_in_flight:
            return
        urls = self._get_urls()
        if not urls:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_url"))
            return
        # Ollama auto-setup prima del download (stessa logica di _start)
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
        self._dispatch_download(urls)

    def _start_download_after_ollama(self, ok: bool, urls: list[str]) -> None:
        # Rilasciamo il guard pre-flight sia se procediamo (dispatch lo
        # riabiliterà a fine pipeline) sia se torniamo in idle.
        self._ollama_setup_in_flight = False
        if self._destroying or self._running:
            # GUI chiusa o pipeline già avviata altrove → ripristina stato UI.
            try:
                self._btn.configure(state="normal", text=self._s("btn_start"))
                self._btn_download.configure(state="normal",
                                             text=self._s("btn_download"))
            except tk.TclError:
                pass
            return
        if not ok:
            self._log_write("[i] Ollama non pronto: la pipeline usera' il fallback Google.\n")
        self._dispatch_download(urls)

    def _dispatch_download(self, urls: list[str]) -> None:
        self._running = True
        self._btn.configure(state="disabled")
        self._btn_download.configure(state="disabled", text=self._s("msg_downloading"))
        self._progress.start(12)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        p = self._snapshot_params()

        # Editor sottotitoli supportato solo su URL singolo (pipeline a 2 fasi
        # con UI bloccante: in batch su più URL non avrebbe senso).
        editor_requested = bool(self._edit_subs.get())
        use_editor_for_single_url = editor_requested and len(urls) == 1
        if editor_requested and len(urls) > 1:
            self._log_write(
                "[i] Editor sottotitoli supportato solo su singolo URL "
                "— skipping editor for batch URLs.\n"
            )

        def run():
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            all_ok = True
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
                        # Branch editor: schedula la fase 1 (transcribe+translate)
                        # sul main thread, lascia che _start_with_editor /
                        # _run_with_segments / _open_editor (cancel) si occupino
                        # del cleanup di `stable`. Salta _on_done qui — sarà
                        # invocato dal flusso editor quando completato/abortito.
                        if use_editor_for_single_url:
                            self.after(0, self._log_write,
                                       "[i] Opening subtitle editor — "
                                       "pipeline paused, waiting for user...\n")
                            self.after(0, self._start_with_editor,
                                       stable, stable)
                            handed_off_to_editor = True
                            # Don't delete `stable` in finally: editor owns it.
                            stable = None
                            return
                        translate_video(
                            video_in=stable,
                            output=p["output"] if len(urls) == 1 else None,
                            model=p["model"],
                            lang_source=p["lang_src"],
                            lang_target=p["lang_tgt"],
                            voice=p["voice"],
                            tts_rate=p["tts_rate"],
                            no_subs=p["no_subs"],
                            subs_only=p["subs_only"],
                            no_demucs=p["no_demucs"],
                            tts_engine=p["tts_engine"],
                            translation_engine=p["translation_engine"],
                            deepl_key=p["deepl_key"],
                            use_diarization=p["use_diarization"],
                            hf_token=p["hf_token"],
                            use_lipsync=p["use_lipsync"],
                            xtts_speed=p["xtts_speed"],
                            ollama_model=p["ollama_model"],
                            ollama_url=p["ollama_url"],
                            ollama_slot_aware=p["ollama_slot_aware"],
                            ollama_thinking=p["ollama_thinking"],
                        )
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
                        all_ok = False
                    finally:
                        if stable and os.path.exists(stable):
                            try:
                                os.remove(stable)
                            except OSError:
                                pass
            finally:
                _thread_local.redirect = None
            if not handed_off_to_editor:
                self.after(0, self._on_done, all_ok)

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

    def _remove_file(self):
        for i in reversed(self._batch_listbox.curselection()):
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

    # ── Translation start ─────────────────────────────────────────────────────

    def _start(self):
        if self._running or self._ollama_setup_in_flight:
            return
        if not self._batch_files:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_video"))
            return
        # Se engine = llm_ollama, esegui il setup prima di partire con la
        # pipeline vera. In caso di fallimento (utente rifiuta install,
        # download abortito, daemon non avviabile) translate_segments cade
        # automaticamente su Google — quindi procediamo comunque.
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
        """Callback dopo il setup Ollama: procedi comunque (fallback Google
        gestito nella pipeline). Se l'utente ha chiuso nel frattempo, skip.
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
        """Instrada verso editor o batch — parte comune a _start e
        _start_after_ollama."""
        if self._edit_subs.get() and len(self._batch_files) == 1:
            self._start_with_editor(self._batch_files[0])
        else:
            self._run_batch(self._batch_files)

    def _snapshot_params(self) -> dict:
        """Reads all Tk vars on the main thread (thread-safe snapshot)."""
        try:
            rate = int(round(self._tts_rate.get()))
        except (ValueError, tk.TclError):
            rate = 0
        cfg = load_config()
        # xtts_speed: se la chiave esiste nel config JSON è un override utente
        # esplicito; se è assente passiamo None per lasciare che l'autotune
        # scelga in base alla coppia di lingue.
        if "xtts_speed" in cfg:
            try:
                xtts_speed = float(cfg["xtts_speed"])
            except (TypeError, ValueError):
                xtts_speed = None
        else:
            xtts_speed = None
        snap = {
            "model":      self._model.get(),
            "lang_src":   self._lang_src.get(),
            "lang_tgt":   self._lang_tgt.get(),
            "voice":      self._voice.get(),
            "tts_rate":   f"{rate:+d}%",
            "subs_only":  self._subs_only.get(),
            "no_subs":    self._no_subs.get(),
            "no_demucs":  self._no_demucs.get(),
            "output":     self._output_var.get().strip(),
            # v2.3: precedenza cosyvoice > xtts > edge (i due voice-cloning
            # sono mutually exclusive a livello UI, ma se per qualche motivo
            # entrambi sono True qui scegliamo cosyvoice — engine "migliore"
            # per voice cloning secondo il rationale di v2.3).
            "tts_engine":  ("cosyvoice" if self._use_cosyvoice.get()
                            else ("xtts" if self._use_xtts.get() else "edge")),
            "translation_engine": self._translation_engine.get(),
            "deepl_key":          self._deepl_key_var.get().strip(),
            "use_diarization":    self._use_diarization.get(),
            "hf_token":           self._hf_token_var.get().strip(),
            "use_lipsync":        self._use_lipsync.get(),
            "xtts_speed":         xtts_speed,
            "ollama_model":       self._ollama_model_var.get().strip() or "qwen3:8b",
            "ollama_url":         self._ollama_url_var.get().strip() or "http://localhost:11434",
            "ollama_slot_aware":  bool(self._ollama_slot_aware.get()),
            "ollama_thinking":    bool(self._ollama_thinking.get()),
        }
        # Persist HF token for next launch
        if snap["hf_token"] and snap["use_diarization"]:
            save_hf_token(snap["hf_token"])
        # Persist Ollama prefs (model/url/slot_aware/thinking) quando l'utente ha
        # selezionato l'engine — così al prossimo avvio i campi sono precompilati.
        if snap["translation_engine"] == "llm_ollama":
            try:
                save_config({
                    "ollama_model": snap["ollama_model"],
                    "ollama_url": snap["ollama_url"],
                    "ollama_slot_aware": snap["ollama_slot_aware"],
                    "ollama_thinking": snap["ollama_thinking"],
                })
            except Exception as e:
                print(f"[i] Warning: could not persist Ollama prefs: {e}", flush=True)
        return snap

    def _start_with_editor(self, video_path: str,
                           cleanup_path: str | None = None):
        """Phase 1: transcribe + translate, then open subtitle editor.

        ``cleanup_path``: percorso di un file temporaneo (tipicamente il
        download YouTube spostato su path stabile) che il flusso editor deve
        rimuovere a fine pipeline (sia su confirm che su cancel/errore).
        Per file locali aperti dall'utente è ``None`` — il file resta intatto.
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
                result = translate_video(
                    video_in=video_path,
                    model=p["model"],
                    lang_source=p["lang_src"],
                    lang_target=p["lang_tgt"],
                    # voice passed even though phase 1 is subs_only (no TTS):
                    # avoids the misleading log "[i] yt_xxx | auto->it |
                    # it-IT-ElsaNeural" that defaulted to LANGUAGES[lang]["voices"][0]
                    # when voice was None. Now phase 1 log reflects user's actual
                    # voice selection (used for real in phase 2 _run_with_segments).
                    voice=p["voice"],
                    subs_only=True,
                    no_demucs=p["no_demucs"],
                    tts_engine=p["tts_engine"],
                    translation_engine=p["translation_engine"],
                    deepl_key=p["deepl_key"],
                    use_diarization=p["use_diarization"],
                    hf_token=p["hf_token"],
                    xtts_speed=p["xtts_speed"],
                    ollama_model=p["ollama_model"],
                    ollama_url=p["ollama_url"],
                    ollama_slot_aware=p["ollama_slot_aware"],
                    ollama_thinking=p["ollama_thinking"],
                )
                self.after(0, self._open_editor, video_path,
                           result["segments"], cleanup_path)
            except Exception as e:
                self.after(0, self._log_write, f"[x] Error: {e}\n{traceback.format_exc()}\n")
                # Pulisci il temp scaricato anche su errore in fase 1
                self._cleanup_editor_tempfile(cleanup_path)
                self.after(0, self._on_done, False)
            finally:
                _thread_local.redirect = None

        threading.Thread(target=phase1, daemon=True).start()

    def _cleanup_editor_tempfile(self, cleanup_path: str | None) -> None:
        """Rimuove il file temporaneo associato al flusso editor (download URL).
        Safe-no-op se ``cleanup_path`` è None o non esiste."""
        if not cleanup_path:
            return
        try:
            if os.path.exists(cleanup_path):
                os.remove(cleanup_path)
        except OSError:
            pass

    def _open_editor(self, video_path: str, segments: list[dict],
                     cleanup_path: str | None = None):
        self._progress.stop()
        self._running = False
        self._btn.configure(state="normal", text=self._s("btn_start"))
        self._btn_download.configure(state="normal", text=self._s("btn_download"))
        self._log_write(f"[i] {len(segments)} segments ready. Opening editor...\n")
        if not segments:
            messagebox.showwarning(self._s("warn_editor"), self._s("msg_no_segments"))
            self._cleanup_editor_tempfile(cleanup_path)
            return

        # Stato condiviso fra il callback _confirm e l'handler di chiusura
        # finestra: serve a non duplicare il cleanup quando l'utente conferma
        # (in quel caso il cleanup spetta a _run_with_segments) e a non
        # rimuovere il file mentre la fase 2 lo sta ancora usando.
        confirmed = {"flag": False}

        def on_confirm(edited):
            confirmed["flag"] = True
            self._log_write("[i] Subtitles confirmed. Starting dubbing...\n")
            self._run_with_segments(video_path, edited, cleanup_path)

        editor = SubtitleEditor(self, segments, on_confirm, ui_s=self._s)

        # Tkinter propaga <Destroy> a tutti i widget figli; filtriamo per
        # reagire solo alla distruzione del Toplevel stesso (idempotenza
        # garantita anche dal flag `confirmed`).
        def on_editor_destroyed(evt):
            if evt.widget is not editor:
                return
            if not confirmed["flag"]:
                self._log_write("[i] Editor closed without confirmation — "
                                "discarding download.\n")
                self._cleanup_editor_tempfile(cleanup_path)

        editor.bind("<Destroy>", on_editor_destroyed)

    def _run_with_segments(self, video_path: str, segments: list[dict],
                           cleanup_path: str | None = None):
        """Phase 2: dubbing with editor segments.

        ``cleanup_path`` viene rimosso nel ``finally`` del worker: il file
        scaricato non serve più dopo il mux finale.
        """
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_dubbing"))
        self._btn_download.configure(state="disabled")
        self._progress.start(12)
        p = self._snapshot_params()

        def do():
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            try:
                translate_video(
                    video_in=video_path,
                    output=p["output"] or None,
                    model=p["model"],
                    lang_source=p["lang_src"],
                    lang_target=p["lang_tgt"],
                    voice=p["voice"],
                    tts_rate=p["tts_rate"],
                    no_subs=p["no_subs"],
                    no_demucs=p["no_demucs"],
                    segments_override=segments,
                    tts_engine=p["tts_engine"],
                    translation_engine=p["translation_engine"],
                    deepl_key=p["deepl_key"],
                    use_diarization=p["use_diarization"],
                    hf_token=p["hf_token"],
                    use_lipsync=p["use_lipsync"],
                    xtts_speed=p["xtts_speed"],
                    ollama_model=p["ollama_model"],
                    ollama_url=p["ollama_url"],
                    ollama_slot_aware=p["ollama_slot_aware"],
                    ollama_thinking=p["ollama_thinking"],
                )
                self.after(0, self._on_done, True)
            except Exception as e:
                self.after(0, self._log_write, f"[x] {e}\n{traceback.format_exc()}\n")
                self.after(0, self._on_done, False)
            finally:
                _thread_local.redirect = None
                self._cleanup_editor_tempfile(cleanup_path)

        threading.Thread(target=do, daemon=True).start()

    def _run_batch(self, files: list[str]):
        """Batch translation — calls translate_video() directly in a worker thread."""
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
            try:
                for i, f in enumerate(files):
                    self.after(0, self._log_write,
                               f"\n{'-'*50}\n[{i+1}/{total}] {Path(f).name}\n{'-'*50}\n")
                    out = p["output"] if len(files) == 1 else None
                    try:
                        translate_video(
                            video_in=f,
                            output=out,
                            model=p["model"],
                            lang_source=p["lang_src"],
                            lang_target=p["lang_tgt"],
                            voice=p["voice"],
                            tts_rate=p["tts_rate"],
                            no_subs=p["no_subs"],
                            subs_only=p["subs_only"],
                            no_demucs=p["no_demucs"],
                            tts_engine=p["tts_engine"],
                            translation_engine=p["translation_engine"],
                            deepl_key=p["deepl_key"],
                            use_diarization=p["use_diarization"],
                            hf_token=p["hf_token"],
                            use_lipsync=p["use_lipsync"],
                            xtts_speed=p["xtts_speed"],
                            ollama_model=p["ollama_model"],
                            ollama_url=p["ollama_url"],
                            ollama_slot_aware=p["ollama_slot_aware"],
                            ollama_thinking=p["ollama_thinking"],
                        )
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {e}\n{traceback.format_exc()}\n")
                        all_ok = False
            finally:
                _thread_local.redirect = None
            self.after(0, self._on_done, all_ok)

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

    def _on_done(self, success: bool):
        if self._destroying:
            return
        self._running = False
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        self._btn_download.configure(state="normal", text=self._s("btn_download"))
        if success:
            self._log_write("\n✓ Done!\n")
            messagebox.showinfo(self._s("msg_completed_t"), self._s("msg_completed"))
        else:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_error"))

    def _on_close(self):
        if self._running:
            if not messagebox.askyesno(self._s("msg_confirm"), self._s("msg_confirm_stop")):
                return
        self._destroying = True
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
    missing_pkgs, missing_bins = check_dependencies()
    if missing_pkgs or missing_bins:
        all_missing = missing_pkgs + missing_bins
        print(f"[!] Missing dependencies: {', '.join(all_missing)}", file=sys.stderr)
        print("    Install with: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Video Translator AI")
    parser.add_argument("input", nargs="?", help="Input video")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("--model", default="small", choices=WHISPER_MODELS)
    parser.add_argument("--lang-source", default="auto")
    parser.add_argument("--lang-target", default=DEFAULT_LANG, choices=list(LANGUAGES.keys()))
    parser.add_argument("--voice", default=None)
    parser.add_argument("--tts-rate", default="+0%")
    parser.add_argument("--no-subs", action="store_true")
    parser.add_argument("--subs-only", action="store_true")
    parser.add_argument("--no-demucs", action="store_true")
    parser.add_argument("--translation-engine", default="google",
                        choices=["google", "deepl", "marian", "llm_ollama"])
    parser.add_argument("--deepl-key", default="")
    parser.add_argument("--ollama-model", default="qwen3:8b",
                        help="Ollama model tag (default: qwen3:8b — Qwen3 with thinking mode "
                             "auto-disabled to avoid <think> blocks. Use qwen2.5:7b-instruct "
                             "for legacy behaviour)")
    parser.add_argument("--ollama-url", default="http://localhost:11434",
                        help="Ollama daemon URL (default: http://localhost:11434)")
    parser.add_argument("--ollama-no-slot-aware", action="store_true",
                        help="Disable slot-aware prompting (faster, less constrained)")
    parser.add_argument("--ollama-thinking", action="store_true",
                        help="Enable Qwen3 thinking mode: deliberates step-by-step "
                             "(~5x slower, fewer idiom/grammar errors). Default off.")
    parser.add_argument("--diarize", action="store_true",
                        help="Enable pyannote speaker diarization")
    parser.add_argument("--hf-token", default="",
                        help="HuggingFace token (falls back to ~/.videotranslatorai_config.json)")
    parser.add_argument("--lipsync", action="store_true",
                        help="Apply Wav2Lip lip sync after dubbing (first run: downloads ~416MB)")
    parser.add_argument("--xtts-speed", type=float, default=None,
                        help="XTTS v2 native speed factor (0.5–2.0). "
                             "If omitted, auto-tuned per language pair "
                             "(e.g. EN→IT=1.35, IT→EN=1.25).")
    parser.add_argument("--no-slot-expansion", action="store_true",
                        help="Disable smart slot expansion / time borrowing for "
                             "tight segments (TASK 2E). Default ON: tight segments "
                             "borrow time from neighbouring silence/easy slots so "
                             "ffmpeg atempo can stay below audible thresholds.")
    # v2.3: TTS engine choice via CLI. Mutuamente esclusivi a livello GUI
    # (radio button), qui sono flag indipendenti — l'ultimo specificato vince.
    parser.add_argument("--xtts", action="store_true",
                        help="Use Coqui XTTS v2 voice cloning (~1.8GB first run)")
    parser.add_argument("--cosyvoice", action="store_true",
                        help="Use CosyVoice 2.0 voice cloning — qualità "
                             "superiore, hallucination rate <2%% vs XTTS 5-15%% "
                             "(~500MB pkg + ~1.7GB model first run)")
    parser.add_argument("--batch", nargs="+", metavar="FILE")
    args = parser.parse_args()

    files = args.batch if args.batch else ([args.input] if args.input else [])
    if not files:
        parser.print_help()
        sys.exit(0)

    cfg_cli = load_config()
    hf_token_cli = args.hf_token or load_hf_token() or cfg_cli.get("hf_token", "")
    # CLI ha la priorità, poi config JSON (se la chiave esiste), altrimenti None
    # → autotune kicks-in dentro translate_video().
    if args.xtts_speed is not None:
        xtts_speed_cli: float | None = args.xtts_speed
    elif "xtts_speed" in cfg_cli:
        try:
            xtts_speed_cli = float(cfg_cli["xtts_speed"])
        except (TypeError, ValueError):
            xtts_speed_cli = None
    else:
        xtts_speed_cli = None
    # v2.3: scelta TTS engine. Precedenza: --cosyvoice > --xtts > edge default.
    # Equivale alla logica del radio in GUI (mutuamente esclusivi).
    if args.cosyvoice:
        tts_engine_cli = "cosyvoice"
    elif args.xtts:
        tts_engine_cli = "xtts"
    else:
        tts_engine_cli = "edge"
    for f in files:
        if not os.path.exists(f):
            print(f"[!] File not found: {f}")
            continue
        translate_video(
            video_in=f,
            output=args.output if len(files) == 1 else None,
            model=args.model,
            lang_source=args.lang_source,
            lang_target=args.lang_target,
            voice=args.voice,
            tts_rate=args.tts_rate,
            no_subs=args.no_subs,
            subs_only=args.subs_only,
            no_demucs=args.no_demucs,
            translation_engine=args.translation_engine,
            deepl_key=args.deepl_key,
            tts_engine=tts_engine_cli,
            use_diarization=args.diarize,
            hf_token=hf_token_cli,
            use_lipsync=args.lipsync,
            xtts_speed=xtts_speed_cli,
            ollama_model=args.ollama_model or cfg_cli.get("ollama_model", "qwen3:8b"),
            ollama_url=args.ollama_url or cfg_cli.get("ollama_url", "http://localhost:11434"),
            ollama_slot_aware=not args.ollama_no_slot_aware,
            ollama_thinking=args.ollama_thinking or bool(cfg_cli.get("ollama_thinking", False)),
            slot_expansion=not args.no_slot_expansion,
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _cli()
    else:
        App().mainloop()
