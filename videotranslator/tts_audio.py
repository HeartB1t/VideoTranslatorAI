"""TTS audio utility helpers.

These helpers are shared by XTTS generation and final track assembly.
Keeping them outside the GUI makes the audio policy testable without
loading Tk, Whisper or the TTS engines.
"""

from __future__ import annotations

import math
import subprocess
from collections.abc import Callable
from typing import Any


def build_atempo_chain(ratio: float, max_ratio: float = 4.0) -> str:
    """Build an ffmpeg atempo filter chain for a requested speed ratio."""
    if not math.isfinite(ratio) or ratio <= 0:
        return "atempo=1.0"
    lo = 1.0 / max_ratio if max_ratio > 0 else 0.25
    ratio = max(lo, min(ratio, max_ratio))
    parts: list[str] = []
    r = ratio
    while r > 2.0:
        parts.append("atempo=2.0")
        r /= 2.0
    while r < 0.5:
        parts.append("atempo=0.5")
        r /= 0.5
    parts.append(f"atempo={r:.3f}")
    return ",".join(parts)


def strip_xtts_terminal_punct(text: str) -> str:
    """Remove trailing punctuation that voice-cloning TTS may pronounce."""
    if not text:
        return text
    cleaned = text.rstrip()
    for _ in range(5):
        before = cleaned
        cleaned = cleaned.rstrip(".!?;:…—–-,)\u00a0\u200b。！？").rstrip()
        if cleaned == before:
            break
    return cleaned


def find_split_point(text: str) -> int:
    """Return a natural split index near the middle of ``text``."""
    n = len(text or "")
    if n < 2:
        return 0
    mid = n // 2
    search_range = max(10, n // 4)
    for offset in range(search_range):
        for pos in (mid + offset, mid - offset):
            if 0 < pos < n and text[pos] in ",;:":
                cut = pos + 1
                if cut < n and text[cut] == " ":
                    cut += 1
                return cut
    for offset in range(search_range):
        for pos in (mid + offset, mid - offset):
            if 0 < pos < n and text[pos] == " ":
                return pos + 1
    return mid


def concat_wavs(paths: list[str], output: str) -> None:
    """Concatenate WAV files with a short crossfade at joins."""
    import numpy as np  # type: ignore
    import soundfile as sf  # type: ignore

    if not paths:
        raise ValueError("concat_wavs: empty paths list")

    chunks: list[Any] = []
    sr: int | None = None
    for path in paths:
        data, this_sr = sf.read(path)
        if sr is None:
            sr = this_sr
        chunks.append(data)
    if sr is None or sr <= 0:
        raise ValueError("concat_wavs: unable to read sample rate")

    crossfade_samples = int(sr * 0.05)
    out = chunks[0]
    for chunk in chunks[1:]:
        if (
            len(out) >= crossfade_samples
            and len(chunk) >= crossfade_samples
            and crossfade_samples > 0
        ):
            fade_out = np.linspace(1.0, 0.0, crossfade_samples)
            fade_in = np.linspace(0.0, 1.0, crossfade_samples)
            if out.ndim == 2:
                fade_out = fade_out[:, None]
                fade_in = fade_in[:, None]
            tail = out[-crossfade_samples:] * fade_out + chunk[:crossfade_samples] * fade_in
            out = np.concatenate([out[:-crossfade_samples], tail, chunk[crossfade_samples:]])
        else:
            out = np.concatenate([out, chunk])
    sf.write(output, out, sr)


def probe_duration_ms(
    path: str,
    *,
    sf_info: Callable[[str], Any] | None = None,
    run: Callable[..., Any] = subprocess.run,
    log_cb: Callable[[str], None] | None = None,
) -> int:
    """Return audio duration in milliseconds, falling back from soundfile to ffprobe."""
    if sf_info is None:
        try:
            import soundfile as sf  # type: ignore

            sf_info = sf.info
        except Exception:
            sf_info = None

    if sf_info is not None:
        try:
            info = sf_info(path)
            if info.samplerate:
                return int(info.frames * 1000 / info.samplerate)
        except Exception:
            pass

    try:
        result = run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()) * 1000)
    except Exception as exc:
        if log_cb is not None:
            log_cb(f"     ! ffprobe duration fallback failed for {path}: {exc}")

    if log_cb is not None:
        log_cb(f"     ! Could not probe duration for {path} (sf.info + ffprobe failed)")
    return 0


def measure_wav_duration_s(path: str) -> float:
    """Return audio duration in seconds, or 0.0 if probing fails."""
    ms = probe_duration_ms(path)
    return ms / 1000.0 if ms > 0 else 0.0
