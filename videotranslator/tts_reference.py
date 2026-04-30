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
