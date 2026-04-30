"""CosyVoice voice-cloning engine."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from videotranslator.cosyvoice_runtime import (
    cosyvoice_cache_dir,
    cosyvoice_download_model,
    cosyvoice_is_installed,
    cosyvoice_model_present,
)
from videotranslator.timing import compute_segment_speed, estimate_tts_duration_s
from videotranslator.tts_audio import measure_wav_duration_s, strip_xtts_terminal_punct
from videotranslator.tts_reference import build_vad_reference_tiered, extract_speaker_reference


COSYVOICE_NATIVE_LANGS = {"zh-CN", "en", "ja", "ko"}

COSYVOICE_LANG_TAGS = {
    "it": "<|it|>", "en": "<|en|>", "es": "<|es|>", "fr": "<|fr|>",
    "de": "<|de|>", "ja": "<|ja|>", "ko": "<|ko|>", "zh-CN": "<|zh|>",
    "pt": "<|pt|>", "ru": "<|ru|>", "ar": "<|ar|>", "nl": "<|nl|>",
    "pl": "<|pl|>", "tr": "<|tr|>", "hi": "<|hi|>", "vi": "<|vi|>",
    "id": "<|id|>", "th": "<|th|>",
}


def generate_tts_cosyvoice(
    segments: list[dict],
    reference_audio: str,
    lang_target: str,
    tmp_dir: str,
    diar_segments: list[dict] | None = None,
    speed: float = 1.25,
    *,
    torch_module: Any | None = None,
    torchaudio_module: Any | None = None,
    librosa_module: Any | None = None,
    cosy_cls: Callable[..., Any] | None = None,
    installed_check: Callable[[], bool] = cosyvoice_is_installed,
    cache_dir_func: Callable[[], Path] = cosyvoice_cache_dir,
    model_present: Callable[[Path], bool] = cosyvoice_model_present,
    download_model: Callable[..., tuple[bool, str]] = cosyvoice_download_model,
    log: Callable[..., None] = print,
) -> list[str] | None:
    """Generate voice-cloned TTS with CosyVoice."""
    if torch_module is None:
        import torch as torch_module  # type: ignore

    if not installed_check():
        log("[!] CosyVoice non installato, fallback al TTS successivo.", flush=True)
        return None

    cache_dir = cache_dir_func()
    if not model_present(cache_dir):
        ok, msg = download_model(cache_dir, log_cb=lambda s: log(s, end="", flush=True))
        if not ok:
            log(f"[!] CosyVoice model download fallito: {msg}. Fallback.", flush=True)
            return None

    device = "cuda" if torch_module.cuda.is_available() else "cpu"
    speed = max(0.5, min(float(speed), 2.0))

    is_native = lang_target in COSYVOICE_NATIVE_LANGS
    lang_tag = COSYVOICE_LANG_TAGS.get(lang_target, "<|en|>")
    mode_label = "native" if is_native else f"cross-lingual ({lang_tag})"
    log(
        f"[5/6] Generating TTS with CosyVoice 2.0 (voice cloning, "
        f"device={device}, speed<={speed:.2f} adaptive)...",
        flush=True,
    )
    log(f"     → CosyVoice2-0.5B loaded ({mode_label} mode for {lang_target})", flush=True)
    log(f"     Reference audio: {Path(reference_audio).name}", flush=True)

    ref_clip = os.path.join(tmp_dir, "cosyvoice_ref.wav")
    vad_ref = build_vad_reference_tiered(reference_audio, ref_clip)
    if not vad_ref:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", reference_audio,
                    "-t", "30", "-ar", "16000", "-ac", "1", ref_clip,
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

    cosy = None
    try:
        if cosy_cls is None:
            from cosyvoice.cli.cosyvoice import CosyVoice as cosy_cls  # type: ignore
        model_path = str(cache_dir / "CosyVoice-300M-Instruct")
        cosy = cosy_cls(
            model_path,
            load_jit=torch_module.cuda.is_available(),
            fp16=torch_module.cuda.is_available(),
        )
    except Exception as exc:
        log(f"[!] CosyVoice model load failed ({exc.__class__.__name__}: {exc}). Fallback.", flush=True)
        return None

    try:
        if torchaudio_module is None:
            import torchaudio as torchaudio_module  # type: ignore
    except Exception:
        log("[!] torchaudio non disponibile per CosyVoice. Fallback.", flush=True)
        return None
    if librosa_module is None:
        import librosa as librosa_module  # type: ignore

    cosy_lock = threading.Lock()
    cap_eps = 1e-3
    speed_stats = {"min": None, "max": None, "sum": 0.0, "n": 0, "at_cap": 0}
    retry_stats = {"attempts": 0, "successful": 0}
    total = len(segments)
    files: list[str] = [os.path.join(tmp_dir, f"seg_{i:04d}.wav") for i in range(total)]
    done_counter = {"n": 0}
    counter_lock = threading.Lock()

    def save_speech(out_path: str, speech_tensor: Any) -> None:
        torchaudio_module.save(out_path, speech_tensor, 22050)

    def gen_one(i: int) -> None:
        seg = segments[i]
        out = files[i]
        text = (seg.get("text_tgt") or seg.get("text") or "").strip()
        if not text:
            return
        text = strip_xtts_terminal_punct(text)
        if not text:
            return
        spk = seg.get("speaker")
        spk_ref = speaker_refs.get(spk, ref_clip) if spk else ref_clip
        cosy_text = text if is_native else f"{lang_tag}{text}"
        try:
            slot_s = float(seg.get("end", 0)) - float(seg.get("start", 0))
        except Exception:
            slot_s = 0.0
        seg_speed = compute_segment_speed(text, slot_s, lang_target, ceiling=speed)

        try:
            with cosy_lock:
                prompt_speech_16k, _ = librosa_module.load(spk_ref, sr=16000, mono=True)
                prompt_speech_16k = torch_module.from_numpy(prompt_speech_16k).unsqueeze(0)
                if hasattr(cosy, "inference_cross_lingual"):
                    gen = cosy.inference_cross_lingual(
                        cosy_text, prompt_speech_16k, stream=False, speed=seg_speed,
                    )
                else:
                    gen = cosy.inference_zero_shot(
                        cosy_text, "", prompt_speech_16k, stream=False, speed=seg_speed,
                    )
                first = next(gen)
                save_speech(out, first["tts_speech"])

            actual_s = measure_wav_duration_s(out)
            est_at_unit_speed = estimate_tts_duration_s(text, lang_target)
            predicted_s = est_at_unit_speed / seg_speed if seg_speed > 0 else 0.0
            if predicted_s > 0 and actual_s > predicted_s * 2.5:
                log(
                    f"     ! CosyVoice output sospetto (segment {i}): "
                    f"{actual_s:.1f}s vs predicted {predicted_s:.1f}s "
                    f"(ratio {actual_s / predicted_s:.1f}x). Retry.",
                    flush=True,
                )
                with counter_lock:
                    retry_stats["attempts"] += 1
                try:
                    with cosy_lock:
                        torch_module.manual_seed(42)
                        if torch_module.cuda.is_available():
                            torch_module.cuda.manual_seed_all(42)
                        if hasattr(cosy, "inference_cross_lingual"):
                            gen = cosy.inference_cross_lingual(
                                cosy_text, prompt_speech_16k, stream=False, speed=seg_speed,
                            )
                        else:
                            gen = cosy.inference_zero_shot(
                                cosy_text, "", prompt_speech_16k, stream=False, speed=seg_speed,
                            )
                        first = next(gen)
                        save_speech(out, first["tts_speech"])
                    actual_s_retry = measure_wav_duration_s(out)
                    if actual_s_retry > 0 and actual_s_retry < actual_s * 0.6:
                        log(
                            f"       Retry OK: {actual_s_retry:.1f}s "
                            f"({actual_s_retry / predicted_s:.1f}x predicted)",
                            flush=True,
                        )
                        with counter_lock:
                            retry_stats["successful"] += 1
                    else:
                        log(f"       Retry no improvement ({actual_s_retry:.1f}s); keeping original.", flush=True)
                except Exception as exc:
                    log(f"       Retry failed for seg {i}: {exc}", flush=True)
        except Exception as exc:
            log(f"     ! CosyVoice seg {i}: {exc}", flush=True)

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

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(gen_one, range(total)))
    finally:
        del cosy
        if device == "cuda":
            try:
                torch_module.cuda.empty_cache()
            except Exception:
                pass

    log("     → CosyVoice done                   ", flush=True)
    n_stats = speed_stats["n"]
    if n_stats > 0:
        s_min = speed_stats["min"] or 0.0
        s_max = speed_stats["max"] or 0.0
        s_mean = speed_stats["sum"] / n_stats
        at_cap = speed_stats["at_cap"]
        pct = (at_cap / n_stats) * 100.0
        log(
            f"     → CosyVoice adaptive speed: min={s_min:.2f}, mean={s_mean:.2f}, "
            f"max={s_max:.2f} over {n_stats} segments",
            flush=True,
        )
        log(
            f"     → Segments at speed cap ({speed:.2f}): {at_cap}/{n_stats} ({pct:.1f}%)",
            flush=True,
        )
        if retry_stats["attempts"] > 0:
            log(
                f"     → CosyVoice hallucination retries: {retry_stats['attempts']} "
                f"({retry_stats['successful']} successful) [<2.5x threshold]",
                flush=True,
            )
        else:
            log("     → Hallucination check: 0 outliers (<2.5x threshold)", flush=True)
    return files
