"""Coqui XTTS voice-cloning engine."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from videotranslator.timing import compute_segment_speed, estimate_tts_duration_s
from videotranslator.tts_audio import (
    concat_wavs,
    find_split_point,
    measure_wav_duration_s,
    strip_xtts_terminal_punct,
)
from videotranslator.tts_reference import build_vad_reference_tiered, extract_speaker_reference
from videotranslator.tts_text_sanitizer import sanitize_for_tts


XTTS_LANGS = {
    "ar": "ar", "zh-CN": "zh-cn", "cs": "cs", "de": "de",
    "en": "en", "es": "es", "fr": "fr", "hi": "hi",
    "hu": "hu", "it": "it", "ja": "ja", "ko": "ko",
    "nl": "nl", "pl": "pl", "pt": "pt", "ru": "ru", "tr": "tr",
}

RETRY_SEEDS = (7, 1337, 42)


def generate_tts_xtts(
    segments: list[dict],
    reference_audio: str,
    lang_target: str,
    tmp_dir: str,
    diar_segments: list[dict] | None = None,
    speed: float = 1.1,
    *,
    tts_factory: Callable[[str], Any] | None = None,
    torch_module: Any | None = None,
    log: Callable[..., None] = print,
) -> list[str] | None:
    """Generate voice-cloned TTS with Coqui XTTS v2."""
    xtts_lang = XTTS_LANGS.get(lang_target)
    if not xtts_lang:
        log(f"[!] XTTS v2 does not support '{lang_target}', falling back to Edge-TTS.", flush=True)
        return None

    if torch_module is None:
        import torch as torch_module  # type: ignore
    if tts_factory is None:
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        from TTS.api import TTS as tts_factory  # type: ignore

    device = "cuda" if torch_module.cuda.is_available() else "cpu"
    speed = max(0.5, min(float(speed), 2.0))
    log(
        f"[5/6] Generating TTS with Coqui XTTS v2 "
        f"(voice cloning, device={device}, speed<={speed:.2f} adaptive)...",
        flush=True,
    )
    log(f"     Reference audio: {Path(reference_audio).name}", flush=True)

    ref_clip = os.path.join(tmp_dir, "xtts_ref.wav")
    vad_ref = build_vad_reference_tiered(reference_audio, ref_clip)
    if not vad_ref:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", reference_audio,
                    "-t", "30", "-ar", "22050", "-ac", "1", ref_clip,
                ],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            shutil.copy(reference_audio, ref_clip)

    speaker_refs: dict[str, str] = {}
    if diar_segments:
        unique_speakers = sorted({d["speaker"] for d in diar_segments})
        log(f"     Building per-speaker references for: {', '.join(unique_speakers)}", flush=True)
        for spk in unique_speakers:
            ref = extract_speaker_reference(reference_audio, diar_segments, spk, tmp_dir)
            if ref:
                refined = os.path.join(tmp_dir, f"{Path(ref).stem}_vad.wav")
                if build_vad_reference_tiered(ref, refined):
                    ref = refined
                speaker_refs[spk] = ref
            else:
                log(f"     ! No reference for {spk}, will use global reference.", flush=True)

    tts_model = None
    tts_lock = threading.Lock()
    cap_eps = 1e-3
    speed_stats = {"min": None, "max": None, "sum": 0.0, "n": 0, "at_cap": 0}
    retry_stats = {"attempts": 0, "successful": 0}
    try:
        tts_model = tts_factory("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        total = len(segments)
        files: list[str] = [os.path.join(tmp_dir, f"seg_{i:04d}.wav") for i in range(total)]
        done_counter = {"n": 0}
        counter_lock = threading.Lock()

        def gen_one(i: int) -> None:
            seg = segments[i]
            out = files[i]
            text = (seg.get("text_tgt") or seg.get("text") or "").strip()
            if not text:
                return
            text = sanitize_for_tts(text)
            text = strip_xtts_terminal_punct(text)
            if not text:
                return
            spk = seg.get("speaker")
            spk_ref = speaker_refs.get(spk, ref_clip) if spk else ref_clip
            try:
                slot_s = float(seg.get("end", 0)) - float(seg.get("start", 0))
            except Exception:
                slot_s = 0.0
            seg_speed = compute_segment_speed(text, slot_s, xtts_lang, ceiling=speed)
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
                actual_s = measure_wav_duration_s(out)
                est_at_unit_speed = estimate_tts_duration_s(text, xtts_lang)
                predicted_s = est_at_unit_speed / seg_speed if seg_speed > 0 else 0.0
                if predicted_s > 0 and actual_s > predicted_s * 2.5:
                    log(
                        f"     ! XTTS output sospetto (segment {i}): "
                        f"{actual_s:.1f}s vs predicted {predicted_s:.1f}s "
                        f"(ratio {actual_s / predicted_s:.1f}x). Multi-seed retry.",
                        flush=True,
                    )
                    best_s = actual_s
                    rescued = False
                    for retry_n, seed in enumerate(RETRY_SEEDS[:2], start=1):
                        with counter_lock:
                            retry_stats["attempts"] += 1
                        retry_path = out + f".retry{retry_n}"
                        try:
                            with tts_lock:
                                torch_module.manual_seed(seed)
                                if torch_module.cuda.is_available():
                                    torch_module.cuda.manual_seed_all(seed)
                                tts_model.tts_to_file(
                                    text=text,
                                    speaker_wav=spk_ref,
                                    language=xtts_lang,
                                    file_path=retry_path,
                                    speed=seg_speed,
                                    **xtts_kwargs,
                                )
                            retry_s = measure_wav_duration_s(retry_path)
                            if retry_s > 0 and retry_s < actual_s * 0.6:
                                shutil.move(retry_path, out)
                                best_s = retry_s
                                rescued = True
                                with counter_lock:
                                    retry_stats["successful"] += 1
                                log(
                                    f"       Retry seed={seed} OK: "
                                    f"{retry_s:.1f}s "
                                    f"({retry_s / predicted_s:.1f}x predicted)",
                                    flush=True,
                                )
                                break
                            if retry_s > 0 and retry_s < best_s:
                                shutil.move(retry_path, out)
                                best_s = retry_s
                            else:
                                try:
                                    os.remove(retry_path)
                                except OSError:
                                    pass
                        except Exception as exc:
                            log(f"       Retry seed={seed} failed for seg {i}: {exc}", flush=True)
                            try:
                                os.remove(retry_path)
                            except OSError:
                                pass
                    if not rescued and len(text) > 30:
                        with counter_lock:
                            retry_stats["attempts"] += 1
                        log("       Retry seeds non risolti. Provo SPLIT testo.", flush=True)
                        split_pos = find_split_point(text)
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
                                concat_wavs([chunk1_path, chunk2_path], out)
                                split_s = measure_wav_duration_s(out)
                                if split_s > 0 and split_s < best_s:
                                    log(
                                        f"       Split OK: {split_s:.1f}s "
                                        f"({split_s / predicted_s:.1f}x predicted)",
                                        flush=True,
                                    )
                                    with counter_lock:
                                        retry_stats["successful"] += 1
                                    best_s = split_s
                                    rescued = True
                                else:
                                    log(f"       Split no improvement ({split_s:.1f}s).", flush=True)
                            except Exception as exc:
                                log(f"       Split failed for seg {i}: {exc}", flush=True)
                            finally:
                                for tmpf in (chunk1_path, chunk2_path):
                                    try:
                                        os.remove(tmpf)
                                    except OSError:
                                        pass
                    if not rescued:
                        log(
                            f"       Nessun retry ha rotto il loop. "
                            f"Mantengo miglior tentativo: {best_s:.1f}s.",
                            flush=True,
                        )
            except Exception as exc:
                log(f"     ! XTTS seg {i}: {exc}", flush=True)
            with counter_lock:
                if speed_stats["min"] is None or seg_speed < speed_stats["min"]:
                    speed_stats["min"] = seg_speed
                if speed_stats["max"] is None or seg_speed > speed_stats["max"]:
                    speed_stats["max"] = seg_speed
                speed_stats["sum"] += seg_speed
                speed_stats["n"] += 1
                if seg_speed >= speed - cap_eps:
                    speed_stats["at_cap"] += 1
                done_counter["n"] += 1
                n = done_counter["n"]
                if n % 10 == 0 or n == total:
                    log(f"     {n}/{total}...", end="\r", flush=True)

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(gen_one, range(total)))
    finally:
        del tts_model
        if device == "cuda":
            try:
                torch_module.cuda.empty_cache()
            except Exception:
                pass

    log("     → XTTS done                   ", flush=True)
    n_stats = speed_stats["n"]
    if n_stats > 0:
        s_min = speed_stats["min"] or 0.0
        s_max = speed_stats["max"] or 0.0
        s_mean = speed_stats["sum"] / n_stats
        at_cap = speed_stats["at_cap"]
        pct = (at_cap / n_stats) * 100.0
        log(
            f"     → XTTS adaptive speed: min={s_min:.2f}, mean={s_mean:.2f}, "
            f"max={s_max:.2f} over {n_stats} segments",
            flush=True,
        )
        log(
            f"     → Segments at speed cap ({speed:.2f}): {at_cap}/{n_stats} ({pct:.1f}%)",
            flush=True,
        )
        if retry_stats["attempts"] > 0:
            log(
                f"     → XTTS hallucination retries: {retry_stats['attempts']} "
                f"({retry_stats['successful']} successful)",
                flush=True,
            )
    return files
