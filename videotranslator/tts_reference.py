"""Reference-audio helpers for voice-cloning TTS engines."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from typing import Any


def safe_speaker_name(speaker: str) -> str:
    """Return a filesystem-safe speaker label."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", speaker)


def select_speaker_turns(
    diar_segments: list[dict],
    speaker: str,
    *,
    max_duration: float = 30.0,
    min_turn_duration: float = 1.0,
) -> list[tuple[float, float]]:
    """Select the longest useful turns for one speaker up to max_duration."""
    turns = [d for d in diar_segments if d["speaker"] == speaker]
    turns.sort(key=lambda d: d["end"] - d["start"], reverse=True)

    selected: list[tuple[float, float]] = []
    total = 0.0
    for turn in turns:
        dur = float(turn["end"]) - float(turn["start"])
        if dur < min_turn_duration:
            continue
        take = min(dur, max_duration - total)
        if take <= 0:
            break
        start = float(turn["start"])
        selected.append((start, start + take))
        total += take
        if total >= max_duration:
            break
    return selected


def build_speaker_reference_filter(selected: list[tuple[float, float]]) -> str:
    """Build the ffmpeg filter_complex used to concatenate speaker turns."""
    filter_parts = []
    for i, (start, end) in enumerate(selected):
        filter_parts.append(
            f"[0:a]atrim=start={start:.3f}:end={end:.3f},"
            f"asetpts=PTS-STARTPTS[a{i}]"
        )
    concat_inputs = "".join(f"[a{i}]" for i in range(len(selected)))
    return (
        ";".join(filter_parts)
        + f";{concat_inputs}concat=n={len(selected)}:v=0:a=1[out]"
    )


def merge_vad_timestamps(
    timestamps: list[dict],
    *,
    max_gap_ms: int = 300,
) -> list[tuple[float, float]]:
    """Merge adjacent VAD speech chunks separated by a short pause."""
    max_gap_s = max_gap_ms / 1000.0
    merged: list[tuple[float, float]] = []
    for item in timestamps:
        start = float(item["start"])
        end = float(item["end"])
        if merged and start - merged[-1][1] <= max_gap_s:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def select_vad_reference_ranges(
    merged: list[tuple[float, float]],
    *,
    target_seconds: float = 18.0,
    min_seconds: float = 3.0,
) -> list[tuple[float, float]] | None:
    """Select VAD ranges that provide enough clean speech for voice cloning."""
    if not merged:
        return None

    by_duration = sorted(merged, key=lambda se: se[1] - se[0], reverse=True)
    longest = by_duration[0]
    if longest[1] - longest[0] >= target_seconds:
        return [longest]

    picked: list[tuple[float, float]] = []
    total = 0.0
    for start, end in by_duration:
        picked.append((start, end))
        total += end - start
        if total >= target_seconds:
            break
    if total < min_seconds:
        return None
    picked.sort(key=lambda se: se[0])
    return picked


def build_vad_reference(
    src_audio: str,
    out_wav: str,
    *,
    target_seconds: float = 18.0,
    min_seconds: float = 3.0,
    max_gap_ms: int = 300,
    sample_rate: int = 22050,
    log: Callable[..., None] = print,
) -> str | None:
    """Build a clean VAD-based reference clip for voice cloning."""
    try:
        import numpy as np  # type: ignore
        import soundfile as sf  # type: ignore
        from silero_vad import get_speech_timestamps, load_silero_vad, read_audio  # type: ignore
    except ImportError as exc:
        log(f"     ! silero-vad not available ({exc}), using raw reference.", flush=True)
        return None

    try:
        model = load_silero_vad()
        wav_16k = read_audio(src_audio, sampling_rate=16000)
        timestamps = get_speech_timestamps(
            wav_16k,
            model,
            sampling_rate=16000,
            return_seconds=True,
        )
        if not timestamps:
            log("     ! VAD: no speech detected, using raw reference.", flush=True)
            return None

        merged = merge_vad_timestamps(timestamps, max_gap_ms=max_gap_ms)
        selected = select_vad_reference_ranges(
            merged,
            target_seconds=target_seconds,
            min_seconds=min_seconds,
        )
        if selected is None:
            total = sum(end - start for start, end in merged)
            log(
                f"     ! VAD: only {total:.1f}s speech (<{min_seconds}s), "
                f"using raw reference.",
                flush=True,
            )
            return None

        audio_hq, sr_hq = sf.read(src_audio, always_2d=False)
        if audio_hq.ndim > 1:
            audio_hq = audio_hq.mean(axis=1)
        if sr_hq != sample_rate:
            import math as _math

            n_out = int(_math.ceil(len(audio_hq) * sample_rate / sr_hq))
            x_old = np.linspace(0, 1, num=len(audio_hq), endpoint=False)
            x_new = np.linspace(0, 1, num=n_out, endpoint=False)
            audio_hq = np.interp(x_new, x_old, audio_hq).astype(np.float32)
            sr_hq = sample_rate

        pieces = []
        for start, end in selected:
            i0 = max(0, int(start * sr_hq))
            i1 = min(len(audio_hq), int(end * sr_hq))
            if i1 > i0:
                pieces.append(audio_hq[i0:i1])
        if not pieces:
            return None

        out = np.concatenate(pieces)
        sf.write(out_wav, out, sr_hq, subtype="PCM_16")
        log(
            f"     → VAD reference: {len(out) / sr_hq:.1f}s speech "
            f"(from {len(merged)} chunks)",
            flush=True,
        )
        return out_wav
    except Exception as exc:
        log(
            f"     ! VAD reference failed ({exc.__class__.__name__}: {exc}), "
            f"using raw reference.",
            flush=True,
        )
        return None


def build_vad_reference_tiered(
    src_audio: str,
    out_wav: str,
    *,
    targets: tuple[float, ...] = (18.0, 15.0, 12.0, 10.0),
    builder: Callable[..., str | None] = build_vad_reference,
    log: Callable[..., None] = print,
) -> str | None:
    """Try VAD reference extraction with descending duration targets."""
    for i, target in enumerate(targets):
        result = builder(src_audio, out_wav, target_seconds=target)
        if result:
            if i > 0:
                log(
                    f"     → VAD reference built at fallback target {target:.0f}s "
                    f"(primary {targets[0]:.0f}s not reachable)",
                    flush=True,
                )
            return result
    return None


def extract_speaker_reference(
    vocals_path: str,
    diar_segments: list[dict],
    speaker: str,
    tmp_dir: str,
    *,
    max_duration: float = 30.0,
    run: Callable[..., Any] = subprocess.run,
    log: Callable[..., None] = print,
) -> str | None:
    """Concat up to max_duration seconds of clean vocals from one speaker."""
    selected = select_speaker_turns(
        diar_segments,
        speaker,
        max_duration=max_duration,
    )
    if not selected:
        return None

    out = os.path.join(tmp_dir, f"ref_{safe_speaker_name(speaker)}.wav")
    filter_complex = build_speaker_reference_filter(selected)
    try:
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                vocals_path,
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                "-ar",
                "22050",
                "-ac",
                "1",
                out,
            ],
            capture_output=True,
            check=True,
        )
        return out
    except subprocess.CalledProcessError as exc:
        log(f"     ! Could not extract reference for {speaker}: {exc}", flush=True)
        return None
