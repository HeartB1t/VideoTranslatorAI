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
import importlib.util
import io
import json
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

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
DEFAULT_LANG = "it"

REQUIRED_PACKAGES = {
    "faster_whisper": "faster-whisper",
    "edge_tts":       "edge-tts",
    "deep_translator": "deep-translator",
    "pydub":          "pydub",
    "demucs":         "demucs",
    "yt_dlp":         "yt-dlp",
}
if sys.version_info >= (3, 13):
    REQUIRED_PACKAGES["audioop"] = "audioop-lts"

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
        "label_engine":       "Motore traduzione:",
        "engine_google":      "Google (default)",
        "engine_deepl":       "DeepL Free",
        "engine_marian":      "MarianMT (locale)",
        "label_deepl_key":    "API key DeepL:",
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
        "label_url":          "URL:",
        "btn_download":       "⬇  Scarica e Traduci",
        "url_placeholder":    "Incolla link YouTube (o altro sito supportato da yt-dlp)...",
        "msg_no_url":         "Incolla almeno un URL valido.",
        "msg_downloading":    "⏳ Download in corso...",
        "log_downloading":    "Download: {}",
        "log_dl_done":        "Download completato → {}",
        "log_dl_error":       "Errore download: {}",
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
        "label_engine":       "Translation engine:",
        "engine_google":      "Google (default)",
        "engine_deepl":       "DeepL Free",
        "engine_marian":      "MarianMT (local)",
        "label_deepl_key":    "DeepL API key:",
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
        "label_url":          "URL:",
        "btn_download":       "⬇  Download & Translate",
        "url_placeholder":    "Paste YouTube link (or other yt-dlp supported site)...",
        "msg_no_url":         "Paste at least one valid URL.",
        "msg_downloading":    "⏳ Downloading...",
        "log_downloading":    "Downloading: {}",
        "log_dl_done":        "Download complete → {}",
        "log_dl_error":       "Download error: {}",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
        "msg_deps_ffmpeg": "\n\nInstall ffmpeg:\n  sudo apt install ffmpeg",
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
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
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

    try:
        with torch.no_grad():
            sources = apply_model(model, waveform.unsqueeze(0), device=device)[0]
        # htdemucs order: [drums, bass, other, vocals]
        vocals = sources[3].mean(0, keepdim=True).cpu()
        background = sources[:3].sum(0).mean(0, keepdim=True).cpu()
    finally:
        del model, waveform, sources
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


def transcribe(audio_path: str, model_name: str, lang_source: str) -> list[dict]:
    import torch
    from faster_whisper import WhisperModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    print(f"[3/6] Transcribing with faster-Whisper (model={model_name}, device={device})...", flush=True)

    model = WhisperModel(model_name, device=device, compute_type=compute)
    lang = None if lang_source == "auto" else lang_source
    try:
        segments, info = model.transcribe(
            audio_path,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"threshold": 0.3, "min_silence_duration_ms": 300},
            condition_on_previous_text=False,  # prevents hallucination/repetition loops
            repetition_penalty=1.3,            # penalizes repeated tokens
            no_repeat_ngram_size=3,            # blocks n-gram repetition
            compression_ratio_threshold=2.4,   # discards hallucinated segments
            log_prob_threshold=-1.0,
            temperature=0,
        )
        # Remove consecutive duplicate segments (extra safety net)
        result = []
        prev_text = None
        for s in segments:
            text = s.text.strip()
            if text and text != prev_text:
                result.append({"start": s.start, "end": s.end, "text": text})
                prev_text = text
    finally:
        del model
        try:
            import torch as _t
            if device == "cuda":
                _t.cuda.empty_cache()
        except Exception:
            pass
    print(f"     → {len(result)} segments | detected language: {info.language}", flush=True)
    return result


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
) -> list[dict]:
    src = "auto" if source == "auto" else source
    print(f"[4/6] Translating {src.upper()}→{target.upper()} ({len(segments)} segments, engine={engine})...", flush=True)

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

    if engine == "deepl" and deepl_key.strip():
        from deep_translator import DeeplTranslator
        translator = DeeplTranslator(
            api_key=deepl_key.strip(), source=src, target=target, use_free_api=True
        )
    else:
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
    files = []
    total = len(segments)
    failed = 0
    for i, seg in enumerate(segments):
        out = os.path.join(tmp_dir, f"seg_{i:04d}.mp3")
        text = (seg.get("text_tgt") or "").strip()
        if text:
            await _tts_segment(text, voice, out, rate=rate)
            if not os.path.exists(out):
                failed += 1
        files.append(out)
        if i % 10 == 0:
            print(f"     {i+1}/{total}...", end="\r", flush=True)
    if failed:
        print(f"     ! Warning: {failed}/{total} TTS segments failed and will be silent.", flush=True)
    return files


def generate_tts(segments: list[dict], voice: str, tmp_dir: str, rate: str = "+0%") -> list[str]:
    print(f"[5/6] Generating TTS (voice={voice}, rate={rate})...", flush=True)
    files = asyncio.run(_tts_all(segments, voice, tmp_dir, rate))
    print("     → TTS done                   ", flush=True)
    return files


def generate_tts_xtts(
    segments: list[dict],
    reference_audio: str,
    lang_target: str,
    tmp_dir: str,
    diar_segments: list[dict] | None = None,
) -> list[str]:
    """Voice cloning TTS via Coqui XTTS v2. Uses reference_audio to clone speaker voice.
    If diar_segments is provided, extracts per-speaker reference clips and uses the
    correct one for each segment (based on seg['speaker']).
    """
    import torch
    from TTS.api import TTS as CoquiTTS

    xtts_lang = XTTS_LANGS.get(lang_target)
    if not xtts_lang:
        print(f"[!] XTTS v2 does not support '{lang_target}', falling back to Edge-TTS.", flush=True)
        return None  # caller will fall back to edge-tts

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[5/6] Generating TTS with Coqui XTTS v2 (voice cloning, device={device})...", flush=True)
    print(f"     Reference audio: {Path(reference_audio).name}", flush=True)

    # Global (fallback) 30s reference clip
    ref_clip = os.path.join(tmp_dir, "xtts_ref.wav")
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
                speaker_refs[spk] = ref
            else:
                print(f"     ! No reference for {spk}, will use global reference.", flush=True)

    tts_model = None
    try:
        tts_model = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        files = []
        total = len(segments)
        for i, seg in enumerate(segments):
            out = os.path.join(tmp_dir, f"seg_{i:04d}.wav")
            text = (seg.get("text_tgt") or "").strip()
            if text:
                spk = seg.get("speaker")
                spk_ref = speaker_refs.get(spk, ref_clip) if spk else ref_clip
                try:
                    tts_model.tts_to_file(
                        text=text,
                        speaker_wav=spk_ref,
                        language=xtts_lang,
                        file_path=out,
                    )
                except Exception as e:
                    print(f"     ! XTTS seg {i}: {e}", flush=True)
            files.append(out)
            if i % 10 == 0:
                print(f"     {i+1}/{total}...", end="\r", flush=True)
    finally:
        del tts_model
        if device == "cuda":
            try:
                import torch as _t
                _t.cuda.empty_cache()
            except Exception:
                pass

    print("     → XTTS done                   ", flush=True)
    return files


def build_dubbed_track(
    segments: list[dict],
    tts_files: list[str],
    bg_path: str | None,
    total_duration: float,
    tmp_dir: str,
    bg_volume: float = 0.15,
) -> str:
    from pydub import AudioSegment

    print("[6/6] Assembling dubbed track...", flush=True)
    total_ms = int(total_duration * 1000)
    dubbed = AudioSegment.silent(duration=total_ms)

    for i, (seg, tts_file) in enumerate(zip(segments, tts_files)):
        if not os.path.exists(tts_file) or os.path.getsize(tts_file) == 0:
            continue
        try:
            tts_audio = AudioSegment.from_file(tts_file)
        except Exception as e:
            print(f"     ! Cannot read {tts_file}: {e}", flush=True)
            continue
        if len(tts_audio) == 0:
            continue
        start_ms = int(seg["start"] * 1000)
        end_ms   = int(seg["end"] * 1000)
        slot_ms  = max(end_ms - start_ms, 1)
        if len(tts_audio) > slot_ms:
            ratio = min(len(tts_audio) / slot_ms, 1.5)
            sped  = os.path.join(tmp_dir, f"seg_{i:04d}_sped.mp3")
            try:
                _run_ffmpeg([
                    "ffmpeg", "-y", "-i", tts_file,
                    "-filter:a", f"atempo={ratio:.3f}", sped
                ], step=f"atempo seg {i}")
                tts_audio = AudioSegment.from_file(sped)
            except Exception as e:
                print(f"     ! atempo failed seg {i}: {e}", flush=True)
        dubbed = dubbed.overlay(tts_audio, position=start_ms)

    if bg_path and os.path.exists(bg_path):
        bg = AudioSegment.from_file(bg_path)
        if len(bg) < total_ms:
            bg = bg + AudioSegment.silent(duration=total_ms - len(bg))
        bg = bg[:total_ms]
        if bg_volume <= 0:
            bg = AudioSegment.silent(duration=total_ms)
        elif bg_volume < 1.0:
            bg = bg + (20 * math.log10(bg_volume))
        dubbed = bg.overlay(dubbed)

    out = os.path.join(tmp_dir, "track_dubbed.wav")
    dubbed.export(out, format="wav")

    # Normalize to -23 LUFS (EBU R128 broadcast standard)
    try:
        import numpy as np
        import soundfile as sf
        import pyloudnorm as pyln
        data, rate = sf.read(out)
        meter = pyln.Meter(rate)
        loudness = meter.integrated_loudness(data)
        if loudness > -70:  # skip if signal too quiet (silence)
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


CONFIG_PATH = Path.home() / ".videotranslatorai_config.json"


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def save_config(data: dict) -> None:
    try:
        existing = load_config()
        existing.update(data)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"     ! Could not save config: {e}", flush=True)


def diarize_audio(audio_path: str, hf_token: str) -> list[dict]:
    """Run pyannote speaker-diarization-3.1. Returns [{start,end,speaker}, ...]."""
    from pyannote.audio import Pipeline
    print("[3b] Running speaker diarization (pyannote)...", flush=True)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    # Use GPU if available
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
    safe_spk = speaker.replace(" ", "_")
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
    tts_engine: str = "edge",   # "edge" or "xtts"
    use_diarization: bool = False,
    hf_token: str = "",
) -> dict:
    """
    Main pipeline. Returns dict with output paths and segments.
    segments_override: skip transcription+translation and use these segments (GUI editor).
    """
    if lang_target not in LANGUAGES:
        raise ValueError(f"Unsupported target language: {lang_target}")
    if not os.path.exists(video_in):
        raise FileNotFoundError(f"Video not found: {video_in}")

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
            videos_dir = Path.home() / "Videos"
            videos_dir.mkdir(exist_ok=True)
            output = str(videos_dir / f"{stem}_{lang_target}.mp4")
        else:
            output = str(input_dir / f"{stem}_{lang_target}.mp4")
    output_base = str(Path(output).with_suffix(""))

    print(f"[i] {Path(video_in).name} | {lang_source}→{lang_target} | {voice}", flush=True)

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
            raw_segs = transcribe(vocals_path, model, lang_source)
            # Speaker diarization (before translation so speaker info propagates)
            if use_diarization and hf_token.strip():
                try:
                    diar_segments = diarize_audio(vocals_path, hf_token.strip())
                    raw_segs = assign_speakers(raw_segs, diar_segments)
                except Exception as e:
                    print(f"     ! Diarization failed ({e.__class__.__name__}: {e}), continuing without speaker info.", flush=True)
                    diar_segments = []
            segments = translate_segments(raw_segs, lang_source, lang_target, engine=translation_engine, deepl_key=deepl_key)

        if not no_subs:
            save_subtitles(segments, output_base)

        if subs_only:
            print("\n[+] --subs-only mode complete.")
            return {"srt": output_base + ".srt", "segments": segments}

        # TTS generation — Edge-TTS or Coqui XTTS v2
        tts_files = None
        if tts_engine == "xtts":
            try:
                tts_files = generate_tts_xtts(
                    segments, vocals_path, lang_target, tmp_dir,
                    diar_segments=diar_segments,
                )
            except Exception as e:
                print(f"     ! XTTS failed ({e}), falling back to Edge-TTS.", flush=True)
                tts_files = None
        if tts_files is None:
            tts_files = generate_tts(segments, voice, tmp_dir, rate=tts_rate)
        duration  = get_duration(video_in)
        track     = build_dubbed_track(segments, tts_files, bg_path, duration, tmp_dir)
        mux_video(video_in, track, output)

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


class _TkStreamRedirect(io.TextIOBase):
    """Redirects print() output to the GUI log widget (thread-safe via after())."""

    def __init__(self, tk_root, on_write):
        super().__init__()
        self._root    = tk_root
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
        # Translation engine: "google" | "deepl" | "marian"
        self._translation_engine = tk.StringVar(value="google")
        self._deepl_key_var      = tk.StringVar()
        # Diarization
        _cfg = load_config()
        self._use_diarization = tk.BooleanVar(value=False)
        self._hf_token_var    = tk.StringVar(value=_cfg.get("hf_token", ""))
        self._running   = False
        self._batch_files: list[str] = []
        self._url_placeholder_active = True

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._fit_to_screen)
        self.after(200, self._check_deps_on_start)

    def _fit_to_screen(self):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w    = min(self.winfo_reqwidth(),  screen_w - 40)
        win_h    = min(self.winfo_reqheight(), screen_h - 80)
        x = (screen_w - win_w) // 2
        y = max(0, (screen_h - win_h) // 2 - 20)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _s(self, key: str) -> str:
        return UI_STRINGS.get(self._ui_lang.get(), UI_STRINGS["it"]).get(key, key)

    # ── Dependency check ─────────────────────────────────────────────────────

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
            messagebox.showerror(self._s("msg_deps_missing"), msg + self._s("msg_deps_ffmpeg"))
        elif messagebox.askyesno(self._s("msg_deps_missing"), msg + self._s("msg_deps_install")):
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

    # ── UI builder ───────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 5}

        # Header: title + UI language selector
        header = tk.Frame(self, bg=BG)
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

        tk.Label(self, text="faster-whisper  •  Demucs  •  Google Translate  •  Edge-TTS / XTTS v2",
                 font=("Helvetica", 9), bg=BG, fg=FG2).grid(row=1, column=0, columnspan=3)

        ttk.Separator(self, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=6)

        # Batch file list
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
        tk.Entry(self, textvariable=self._output_var, width=42,
                 bg=SEL, fg=FG, insertbackground=FG,
                 relief="flat", font=("Helvetica", 9)).grid(
            row=4, column=1, sticky="ew", padx=(0, 6), pady=5)
        self._btn_browse = tk.Button(self, text=self._s("btn_browse"),
                                     command=self._browse_output, bg="#45475a", fg=FG, relief="flat")
        self._btn_browse.grid(row=4, column=2, padx=(0, 16))

        # URL download field
        self._lbl_url = self._row_label(5, self._s("label_url"))
        url_frame = tk.Frame(self, bg=BG)
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

        ttk.Separator(self, orient="horizontal").grid(
            row=6, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # Whisper model
        self._lbl_model = self._row_label(7, self._s("label_model"))
        mf = tk.Frame(self, bg=BG)
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
        src_frame = tk.Frame(self, bg=BG)
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
        tgt_frame = tk.Frame(self, bg=BG)
        tgt_frame.grid(row=9, column=1, columnspan=2, sticky="w", **pad)
        self._tgt_combo = ttk.Combobox(tgt_frame, values=[v["name"] for v in LANGUAGES.values()],
                                        state="readonly", width=22, font=("Helvetica", 9))
        self._tgt_combo.current(list(LANGUAGES.keys()).index("it"))
        self._tgt_combo.pack(side="left")
        self._tgt_combo.bind("<<ComboboxSelected>>", self._on_lang_tgt_change)

        # Voice
        self._lbl_voice = self._row_label(10, self._s("label_voice"))
        self._voice_frame = tk.Frame(self, bg=BG)
        self._voice_frame.grid(row=10, column=1, columnspan=2, sticky="w", **pad)
        self._build_voice_buttons()

        # TTS rate
        self._lbl_tts_rate = self._row_label(11, self._s("label_tts_rate"))
        rate_frame = tk.Frame(self, bg=BG)
        rate_frame.grid(row=11, column=1, columnspan=2, sticky="w", **pad)
        tk.Label(rate_frame, text="-50%", bg=BG, fg=FG2, font=("Helvetica", 8)).pack(side="left")
        ttk.Scale(rate_frame, from_=-50, to=50, variable=self._tts_rate,
                  orient="horizontal", length=200).pack(side="left", padx=6)
        tk.Label(rate_frame, text="+50%", bg=BG, fg=FG2, font=("Helvetica", 8)).pack(side="left")
        self._rate_lbl = tk.Label(rate_frame, text="+0%", bg=BG, fg=ACC,
                                   font=("Helvetica", 9, "bold"), width=6)
        self._rate_lbl.pack(side="left", padx=4)
        self._tts_rate.trace_add("write", self._update_rate_label)

        ttk.Separator(self, orient="horizontal").grid(
            row=12, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # Options
        self._lbl_options = self._row_label(13, self._s("label_options"))
        opts = tk.Frame(self, bg=BG)
        opts.grid(row=13, column=1, columnspan=2, sticky="w", **pad)

        def cb(parent, text_key, var, cmd=None):
            w = tk.Checkbutton(parent, text=self._s(text_key), variable=var, command=cmd,
                               bg=BG, fg=FG, selectcolor=SEL,
                               activebackground=BG, font=("Helvetica", 9))
            w._text_key = text_key
            return w

        self._chk_subs_only = cb(opts, "opt_subs_only", self._subs_only, self._on_subs_only)
        self._chk_subs_only.grid(row=0, column=0, sticky="w")
        self._chk_no_subs   = cb(opts, "opt_no_subs",   self._no_subs,   self._on_no_subs)
        self._chk_no_subs.grid(row=1, column=0, sticky="w")
        self._chk_no_demucs = cb(opts, "opt_no_demucs", self._no_demucs)
        self._chk_no_demucs.grid(row=0, column=1, sticky="w", padx=16)
        self._chk_edit_subs = cb(opts, "opt_edit_subs", self._edit_subs)
        self._chk_edit_subs.grid(row=1, column=1, sticky="w", padx=16)
        self._chk_xtts = cb(opts, "opt_xtts", self._use_xtts)
        self._chk_xtts.grid(row=2, column=0, columnspan=2, sticky="w")

        # Translation engine radio group
        engine_row = tk.Frame(opts, bg=BG)
        engine_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
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

        # DeepL API key row (visible only when DeepL selected)
        self._deepl_row = tk.Frame(opts, bg=BG)
        self._deepl_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))
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
        diar_row.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._chk_diar = tk.Checkbutton(
            diar_row, text=self._s("opt_diarization"),
            variable=self._use_diarization,
            command=self._on_diarization_toggle,
            bg=BG, fg=FG, selectcolor=SEL, activebackground=BG, font=("Helvetica", 9))
        self._chk_diar.pack(side="left")

        self._hf_row = tk.Frame(opts, bg=BG)
        self._hf_row.grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))
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

        ttk.Separator(self, orient="horizontal").grid(
            row=14, column=0, columnspan=3, sticky="ew", padx=16, pady=4)

        # Start button
        self._btn = tk.Button(self, text=self._s("btn_start"), command=self._start,
                              bg=ACC, fg=BG, font=("Helvetica", 12, "bold"),
                              relief="flat", padx=20, pady=8, cursor="hand2",
                              activebackground="#74c7ec")
        self._btn.grid(row=15, column=0, columnspan=3, pady=8)

        # Log
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=16, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self._log = tk.Text(log_frame, height=8, width=76,
                            bg="#11111b", fg=GRN, font=("Monospace", 8),
                            relief="flat", state="disabled", wrap="word")
        vsb = tk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=17, column=0, columnspan=3, padx=16, pady=(0, 12))

        self.columnconfigure(1, weight=1)
        self.rowconfigure(16, weight=1)  # log row expands, progress bar stays at bottom

    def _row_label(self, row, text):
        lbl = tk.Label(self, text=text, bg=BG, fg="#bac2de",
                       font=("Helvetica", 9, "bold"), anchor="e")
        lbl.grid(row=row, column=0, sticky="e", padx=(16, 8), pady=5)
        return lbl

    # ── Language switcher ────────────────────────────────────────────────────

    def _on_ui_lang_change(self, _=None):
        self._ui_lang.set(UI_LANG_OPTIONS[self._ui_lang_combo.current()][0])
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
        self._lbl_engine.configure(text=self._s("label_engine"))
        self._rb_eng_google.configure(text=self._s("engine_google"))
        self._rb_eng_deepl.configure(text=self._s("engine_deepl"))
        self._rb_eng_marian.configure(text=self._s("engine_marian"))
        self._lbl_deepl_key.configure(text=self._s("label_deepl_key"))
        self._chk_diar.configure(text=self._s("opt_diarization"))
        self._lbl_hf_token.configure(text=self._s("label_hf_token"))
        self._lbl_hf_hint.configure(text="  " + self._s("hint_hf_token"))
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
        if self._translation_engine.get() == "deepl":
            self._deepl_row.grid()
        else:
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
        if self._running:
            return
        urls = self._get_urls()
        if not urls:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_url"))
            return
        self._running = True
        self._btn.configure(state="disabled")
        self._btn_download.configure(state="disabled", text=self._s("msg_downloading"))
        self._progress.start(12)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        p = self._snapshot_params()

        def run():
            redirect = _TkStreamRedirect(self, self._log_write)
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = redirect
            all_ok = True
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
                            fd, stable = tempfile.mkstemp(suffix=".mp4", prefix="yt_")
                            os.close(fd)
                            if os.path.exists(stable):
                                os.remove(stable)
                            shutil.move(video_path, stable)
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
                sys.stdout, sys.stderr = old_out, old_err
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
        if self._running:
            return
        if not self._batch_files:
            messagebox.showerror(self._s("msg_error_t"), self._s("msg_no_video"))
            return
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
            "tts_engine":  "xtts" if self._use_xtts.get() else "edge",
            "translation_engine": self._translation_engine.get(),
            "deepl_key":          self._deepl_key_var.get().strip(),
            "use_diarization":    self._use_diarization.get(),
            "hf_token":           self._hf_token_var.get().strip(),
        }
        # Persist HF token for next launch
        if snap["hf_token"] and snap["use_diarization"]:
            save_config({"hf_token": snap["hf_token"]})
        return snap

    def _start_with_editor(self, video_path: str):
        """Phase 1: transcribe + translate, then open subtitle editor."""
        self._log_write("Phase 1: Transcription + translation (no dubbing)...\n")
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_transcribing"))
        self._progress.start(12)
        p = self._snapshot_params()

        def phase1():
            redirect = _TkStreamRedirect(self, self._log_write)
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = redirect
            try:
                result = translate_video(
                    video_in=video_path,
                    model=p["model"],
                    lang_source=p["lang_src"],
                    lang_target=p["lang_tgt"],
                    subs_only=True,
                    no_demucs=p["no_demucs"],
                    tts_engine=p["tts_engine"],
                    translation_engine=p["translation_engine"],
                    deepl_key=p["deepl_key"],
                    use_diarization=p["use_diarization"],
                    hf_token=p["hf_token"],
                )
                self.after(0, self._open_editor, video_path, result["segments"])
            except Exception as e:
                self.after(0, self._log_write, f"[x] Error: {e}\n{traceback.format_exc()}\n")
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

        def on_confirm(edited):
            self._log_write("[i] Subtitles confirmed. Starting dubbing...\n")
            self._run_with_segments(video_path, edited)

        SubtitleEditor(self, segments, on_confirm, ui_s=self._s)

    def _run_with_segments(self, video_path: str, segments: list[dict]):
        """Phase 2: dubbing with editor segments."""
        self._running = True
        self._btn.configure(state="disabled", text=self._s("btn_dubbing"))
        self._progress.start(12)
        p = self._snapshot_params()

        def do():
            redirect = _TkStreamRedirect(self, self._log_write)
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = redirect
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
                )
                self.after(0, self._on_done, True)
            except Exception as e:
                self.after(0, self._log_write, f"[x] {e}\n{traceback.format_exc()}\n")
                self.after(0, self._on_done, False)
            finally:
                sys.stdout, sys.stderr = old_out, old_err

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
            redirect = _TkStreamRedirect(self, self._log_write)
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = redirect
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
                        )
                    except Exception as e:
                        self.after(0, self._log_write,
                                   f"[x] {e}\n{traceback.format_exc()}\n")
                        all_ok = False
            finally:
                sys.stdout, sys.stderr = old_out, old_err
            self.after(0, self._on_done, all_ok)

        threading.Thread(target=run_all, daemon=True).start()

    # ── Log ──────────────────────────────────────────────────────────────────

    def _log_write(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Done / Close ─────────────────────────────────────────────────────────

    def _on_done(self, success: bool):
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
                        choices=["google", "deepl", "marian"])
    parser.add_argument("--deepl-key", default="")
    parser.add_argument("--diarize", action="store_true",
                        help="Enable pyannote speaker diarization")
    parser.add_argument("--hf-token", default="",
                        help="HuggingFace token (falls back to ~/.videotranslatorai_config.json)")
    parser.add_argument("--batch", nargs="+", metavar="FILE")
    args = parser.parse_args()

    files = args.batch if args.batch else ([args.input] if args.input else [])
    if not files:
        parser.print_help()
        sys.exit(0)

    hf_token_cli = args.hf_token or load_config().get("hf_token", "")
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
            use_diarization=args.diarize,
            hf_token=hf_token_cli,
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _cli()
    else:
        App().mainloop()
