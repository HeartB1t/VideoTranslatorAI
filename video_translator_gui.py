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
}

UI_LANG_OPTIONS = [("it", "🇮🇹 Italiano"), ("en", "🇬🇧 English")]


# ═══════════════════════════════════════════════════════════
#  PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════

def _run_ffmpeg(cmd: list[str], step: str = "ffmpeg"):
    proc = subprocess.run(cmd, capture_output=True, text=True)
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
        del model
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
        segments, info = model.transcribe(audio_path, language=lang, beam_size=5, vad_filter=True)
        result = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
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


def translate_segments(segments: list[dict], source: str, target: str) -> list[dict]:
    from deep_translator import GoogleTranslator
    src = "auto" if source == "auto" else source
    print(f"[4/6] Translating {src.upper()}→{target.upper()} ({len(segments)} segments)...", flush=True)
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
        translated.append({
            "start": seg["start"],
            "end": seg["end"],
            "text_src": text,
            "text_tgt": text_tgt,
        })
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
    for i, seg in enumerate(segments):
        out = os.path.join(tmp_dir, f"seg_{i:04d}.mp3")
        text = (seg.get("text_tgt") or "").strip()
        if text:
            await _tts_segment(text, voice, out, rate=rate)
        files.append(out)
        if i % 10 == 0:
            print(f"     {i+1}/{total}...", end="\r", flush=True)
    return files


def generate_tts(segments: list[dict], voice: str, tmp_dir: str, rate: str = "+0%") -> list[str]:
    print(f"[5/6] Generating TTS (voice={voice}, rate={rate})...", flush=True)
    files = asyncio.run(_tts_all(segments, voice, tmp_dir, rate))
    print("     → TTS done                   ", flush=True)
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
    segments_override: list[dict] | None = None,
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
    if output is None:
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

        if segments_override is not None:
            segments = segments_override
        else:
            raw_segs = transcribe(vocals_path, model, lang_source)
            segments = translate_segments(raw_segs, lang_source, lang_target)

        if not no_subs:
            save_subtitles(segments, output_base)

        if subs_only:
            print("\n[+] --subs-only mode complete.")
            return {"srt": output_base + ".srt", "segments": segments}

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
        self.resizable(False, False)
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
        self._running   = False
        self._batch_files: list[str] = []
        self._url_placeholder_active = True

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._check_deps_on_start)

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
                                            state="readonly", width=12, font=("Helvetica", 8))
        self._ui_lang_combo.current(0)
        self._ui_lang_combo.pack(side="left")
        self._ui_lang_combo.bind("<<ComboboxSelected>>", self._on_ui_lang_change)

        tk.Label(self, text="faster-whisper  •  Demucs  •  Google Translate  •  Edge-TTS",
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
        log_frame.grid(row=16, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="ew")
        self._log = tk.Text(log_frame, height=12, width=76,
                            bg="#11111b", fg=GRN, font=("Monospace", 8),
                            relief="flat", state="disabled", wrap="word")
        vsb = tk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=17, column=0, columnspan=3, padx=16, pady=(0, 12))

        self.columnconfigure(1, weight=1)

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
        return {
            "model":      self._model.get(),
            "lang_src":   self._lang_src.get(),
            "lang_tgt":   self._lang_tgt.get(),
            "voice":      self._voice.get(),
            "tts_rate":   f"{rate:+d}%",
            "subs_only":  self._subs_only.get(),
            "no_subs":    self._no_subs.get(),
            "no_demucs":  self._no_demucs.get(),
            "output":     self._output_var.get().strip(),
        }

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
    parser.add_argument("--batch", nargs="+", metavar="FILE")
    args = parser.parse_args()

    files = args.batch if args.batch else ([args.input] if args.input else [])
    if not files:
        parser.print_help()
        sys.exit(0)

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
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _cli()
    else:
        App().mainloop()
