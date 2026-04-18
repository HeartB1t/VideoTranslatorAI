#!/usr/bin/env python3
"""
video_translator.py v2 — Pipeline AI per traduzione/doppiaggio video
Stack: faster-whisper (GPU) + Demucs (separazione voce) + Google Translate + Edge-TTS
"""

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

LANGUAGES = {
    "ar":    {"name": "Arabo",       "voices": ["ar-SA-ZariyahNeural", "ar-SA-HamedNeural", "ar-EG-SalmaNeural"]},
    "zh-CN": {"name": "Cinese",      "voices": ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural"]},
    "cs":    {"name": "Ceco",        "voices": ["cs-CZ-VlastaNeural", "cs-CZ-AntoninNeural"]},
    "da":    {"name": "Danese",      "voices": ["da-DK-ChristelNeural", "da-DK-JeppeNeural"]},
    "de":    {"name": "Tedesco",     "voices": ["de-DE-KatjaNeural", "de-DE-ConradNeural", "de-DE-AmalaNeural"]},
    "el":    {"name": "Greco",       "voices": ["el-GR-AthinaNeural", "el-GR-NestorasNeural"]},
    "en":    {"name": "Inglese",     "voices": ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural"]},
    "es":    {"name": "Spagnolo",    "voices": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-MX-DaliaNeural"]},
    "fi":    {"name": "Finlandese",  "voices": ["fi-FI-NooraNeural", "fi-FI-HarriNeural"]},
    "fr":    {"name": "Francese",    "voices": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural", "fr-FR-EloiseNeural"]},
    "hi":    {"name": "Hindi",       "voices": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"]},
    "hu":    {"name": "Ungherese",   "voices": ["hu-HU-NoemiNeural", "hu-HU-TamasNeural"]},
    "id":    {"name": "Indonesiano", "voices": ["id-ID-GadisNeural", "id-ID-ArdiNeural"]},
    "it":    {"name": "Italiano",    "voices": ["it-IT-ElsaNeural", "it-IT-IsabellaNeural", "it-IT-DiegoNeural", "it-IT-GiuseppeMultilingualNeural"]},
    "ja":    {"name": "Giapponese",  "voices": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"]},
    "ko":    {"name": "Coreano",     "voices": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"]},
    "nl":    {"name": "Olandese",    "voices": ["nl-NL-ColetteNeural", "nl-NL-MaartenNeural"]},
    "no":    {"name": "Norvegese",   "voices": ["nb-NO-PernilleNeural", "nb-NO-FinnNeural"]},
    "pl":    {"name": "Polacco",     "voices": ["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"]},
    "pt":    {"name": "Portoghese",  "voices": ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-PT-RaquelNeural"]},
    "ro":    {"name": "Rumeno",      "voices": ["ro-RO-AlinaNeural", "ro-RO-EmilNeural"]},
    "ru":    {"name": "Russo",       "voices": ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]},
    "sv":    {"name": "Svedese",     "voices": ["sv-SE-SofieNeural", "sv-SE-MattiasNeural"]},
    "tr":    {"name": "Turco",       "voices": ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]},
    "uk":    {"name": "Ucraino",     "voices": ["uk-UA-PolinaNeural", "uk-UA-OstapNeural"]},
    "vi":    {"name": "Vietnamita",  "voices": ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]},
}

DEFAULT_LANG = "it"
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]


def install_deps():
    deps = ["faster-whisper", "edge-tts", "deep-translator", "pydub", "demucs"]
    if sys.version_info >= (3, 13):
        deps.append("audioop-lts")
    print("[*] Installazione dipendenze...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages"
    ] + deps)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages",
        "torchaudio==2.6.0", "--index-url", "https://download.pytorch.org/whl/cu124"
    ])
    print("[+] Dipendenze installate.\n")


def check_deps() -> list[str]:
    missing = []
    for pkg in ["faster_whisper", "edge_tts", "deep_translator", "pydub", "demucs"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def _run_ffmpeg(cmd: list[str], step: str = "ffmpeg"):
    """Esegue ffmpeg/ffprobe catturando stderr e rialzando un errore leggibile."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-10:]
        raise RuntimeError(f"{step} fallito (exit {proc.returncode}):\n" + "\n".join(err))
    return proc


def extract_audio(video_path: str, audio_path: str):
    print(f"[1/6] Estrazione audio da: {Path(video_path).name}", flush=True)
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        audio_path
    ], step="extract_audio")
    print(f"     → {audio_path}", flush=True)


def separate_audio(audio_path: str, tmp_dir: str) -> tuple[str, str]:
    """Separa voce e musica con Demucs htdemucs. Ritorna (vocals_path, background_path)."""
    print("[2/6] Separazione voce/musica con Demucs...", flush=True)
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

        # htdemucs: [drums, bass, other, vocals]
        vocals = sources[3].mean(0, keepdim=True).cpu()
        background = sources[:3].sum(0).mean(0, keepdim=True).cpu()
    finally:
        # Libera memoria GPU per i passi successivi (faster-whisper ne ha bisogno).
        del model
        if device == "cuda":
            torch.cuda.empty_cache()

    vocals_16k = os.path.join(tmp_dir, "vocals_16k.wav")
    bg_path = os.path.join(tmp_dir, "background.wav")

    torchaudio.save(os.path.join(tmp_dir, "vocals_raw.wav"), vocals, sr)
    torchaudio.save(bg_path, background, sr)

    # Converti voce a 16kHz mono per Whisper
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", os.path.join(tmp_dir, "vocals_raw.wav"),
        "-ar", "16000", "-ac", "1", vocals_16k
    ], step="resample vocals")

    print(f"     → Voce (16kHz): {vocals_16k}", flush=True)
    print(f"     → Musica: {bg_path}", flush=True)
    return vocals_16k, bg_path


def transcribe(audio_path: str, model_name: str, lang_source: str) -> list[dict]:
    import torch
    from faster_whisper import WhisperModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    print(f"[3/6] Trascrizione faster-whisper (model={model_name}, device={device})...", flush=True)

    model = WhisperModel(model_name, device=device, compute_type=compute)
    lang = None if lang_source == "auto" else lang_source
    try:
        segments, info = model.transcribe(audio_path, language=lang, beam_size=5, vad_filter=True)
        result = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    finally:
        del model
        try:
            import torch as _torch
            if device == "cuda":
                _torch.cuda.empty_cache()
        except Exception:
            pass
    print(f"     → {len(result)} segmenti | lingua rilevata: {info.language}", flush=True)
    return result


def translate_segments(segments: list[dict], source: str, target: str) -> list[dict]:
    from deep_translator import GoogleTranslator
    src = "auto" if source == "auto" else source
    print(f"[4/6] Traduzione {src.upper()}→{target.upper()} ({len(segments)} segmenti)...", flush=True)
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
                print(f"     ! Errore segmento {i}: {e}", flush=True)
                text_tgt = text
        translated.append({
            "start": seg["start"],
            "end": seg["end"],
            "text_src": text,
            "text_tgt": text_tgt,
        })
        if i % 10 == 0:
            print(f"     {i+1}/{len(segments)}...", end="\r", flush=True)
    print("     → Traduzione completata          ", flush=True)
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
                print(f"     ! TTS retry {attempt+1} ({e.__class__.__name__}) tra {wait}s...", flush=True)
                await asyncio.sleep(wait)
            else:
                print(f"     ! TTS fallito: {text[:40]!r} ({e.__class__.__name__}: {e})", flush=True)


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
    print(f"[5/6] Generazione TTS (voce={voice}, velocità={rate})...", flush=True)
    # Un solo event loop per tutti i segmenti (evita overhead di asyncio.run in loop).
    files = asyncio.run(_tts_all(segments, voice, tmp_dir, rate))
    print("     → TTS generato                   ", flush=True)
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

    print("[6/6] Assemblaggio traccia doppiata...", flush=True)
    total_ms = int(total_duration * 1000)
    dubbed = AudioSegment.silent(duration=total_ms)

    for i, (seg, tts_file) in enumerate(zip(segments, tts_files)):
        if not os.path.exists(tts_file) or os.path.getsize(tts_file) == 0:
            continue
        try:
            tts_audio = AudioSegment.from_file(tts_file)
        except Exception as e:
            print(f"     ! Impossibile leggere {tts_file}: {e}", flush=True)
            continue
        if len(tts_audio) == 0:
            continue
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)
        slot_ms = max(end_ms - start_ms, 1)
        if len(tts_audio) > slot_ms:
            # atempo accetta 0.5-2.0; limitiamo a 1.5 per qualità udibile.
            ratio = min(len(tts_audio) / slot_ms, 1.5)
            sped = os.path.join(tmp_dir, f"seg_{i:04d}_sped.mp3")
            try:
                _run_ffmpeg([
                    "ffmpeg", "-y", "-i", tts_file,
                    "-filter:a", f"atempo={ratio:.3f}", sped
                ], step=f"atempo seg {i}")
                tts_audio = AudioSegment.from_file(sped)
            except Exception as e:
                print(f"     ! atempo fallito seg {i}: {e}", flush=True)
        dubbed = dubbed.overlay(tts_audio, position=start_ms)

    if bg_path and os.path.exists(bg_path):
        bg = AudioSegment.from_file(bg_path)
        if len(bg) < total_ms:
            bg = bg + AudioSegment.silent(duration=total_ms - len(bg))
        bg = bg[:total_ms]
        # Attenuazione in dB: gain = 20*log10(bg_volume). pydub somma dB con '+'.
        # bg_volume in (0,1] → gain negativo. Evita log(0).
        if bg_volume <= 0:
            bg = AudioSegment.silent(duration=total_ms)
        elif bg_volume < 1.0:
            gain_db = 20 * math.log10(bg_volume)
            bg = bg + gain_db
        dubbed = bg.overlay(dubbed)

    out = os.path.join(tmp_dir, "track_dubbed.wav")
    dubbed.export(out, format="wav")
    print(f"     → Traccia: {out}", flush=True)
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
    print(f"[+] Sottotitoli: {path}", flush=True)


def get_duration(video_path: str) -> float:
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", video_path
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe fallito: {r.stderr.strip()}")
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Impossibile leggere la durata di {video_path}: {e}")


def mux_video(video_input: str, audio_track: str, output_path: str):
    print(f"[+] Mux finale → {output_path}", flush=True)
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
    Pipeline principale. Ritorna dict con percorsi output e segmenti.
    segments_override: salta trascrizione+traduzione e usa questi segmenti (editor GUI).
    """
    if lang_target not in LANGUAGES:
        raise ValueError(f"Lingua target non supportata: {lang_target}")
    if not os.path.exists(video_in):
        raise FileNotFoundError(f"Video non trovato: {video_in}")

    voice = voice or LANGUAGES[lang_target]["voices"][0]
    stem = Path(video_in).stem
    output = output or str(Path(video_in).parent / f"{stem}_{lang_target}.mp4")
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
                print(f"     ! Demucs fallito ({e}), procedo senza separazione", flush=True)
                bg_path = None
                vocals_16k = os.path.join(tmp_dir, "audio_16k.wav")
                _run_ffmpeg([
                    "ffmpeg", "-y", "-i", audio_raw,
                    "-ar", "16000", "-ac", "1", vocals_16k
                ], step="resample audio")
                vocals_path = vocals_16k
        else:
            vocals_16k = os.path.join(tmp_dir, "audio_16k.wav")
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", audio_raw,
                "-ar", "16000", "-ac", "1", vocals_16k
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
            print("\n[+] Modalità --subs-only completata.")
            return {"srt": output_base + ".srt", "segments": segments}

        tts_files = generate_tts(segments, voice, tmp_dir, rate=tts_rate)
        duration = get_duration(video_in)
        track = build_dubbed_track(segments, tts_files, bg_path, duration, tmp_dir)
        mux_video(video_in, track, output)

    print(f"\n[✓] Video tradotto: {output}")
    return {"video": output, "srt": output_base + ".srt", "segments": segments}


def main():
    parser = argparse.ArgumentParser(description="Video Translator AI v2")
    parser.add_argument("input", nargs="?", help="Video di input")
    parser.add_argument("-o", "--output", help="File output")
    parser.add_argument("--model", default="small", choices=WHISPER_MODELS)
    parser.add_argument("--lang-source", default="auto", help="Lingua sorgente (default: auto)")
    parser.add_argument("--lang-target", default=DEFAULT_LANG, choices=list(LANGUAGES.keys()))
    parser.add_argument("--voice", default=None)
    parser.add_argument("--tts-rate", default="+0%", help="Velocità TTS es. +10%% -20%%")
    parser.add_argument("--no-subs", action="store_true")
    parser.add_argument("--subs-only", action="store_true")
    parser.add_argument("--no-demucs", action="store_true", help="Salta separazione voce/musica")
    parser.add_argument("--batch", nargs="+", metavar="FILE", help="Traduce più file in sequenza")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()

    if args.install:
        install_deps()
        if not args.input and not args.batch:
            return

    missing = check_deps()
    if missing:
        print(f"[!] Dipendenze mancanti: {missing}\n    Esegui: python3 video_translator.py --install")
        sys.exit(1)

    files = args.batch if args.batch else ([args.input] if args.input else [])
    if not files:
        parser.print_help()
        sys.exit(0)

    for f in files:
        if not os.path.exists(f):
            print(f"[!] File non trovato: {f}")
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
    main()
