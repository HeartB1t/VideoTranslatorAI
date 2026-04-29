"""Media helpers shared by the GUI, CLI and future pipeline modules."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


SubprocessRun = Callable[..., Any]
LogCallback = Callable[[str], None]


def run_ffmpeg(
    cmd: list[str],
    step: str = "ffmpeg",
    *,
    run: SubprocessRun = subprocess.run,
):
    """Run ffmpeg and raise a concise RuntimeError on failure."""
    proc = run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-10:]
        raise RuntimeError(f"{step} failed (exit {proc.returncode}):\n" + "\n".join(err))
    return proc


def build_extract_audio_cmd(video_path: str, audio_path: str) -> list[str]:
    """Return the ffmpeg command used for the first pipeline audio extraction."""
    return [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        "-ac",
        "2",
        audio_path,
    ]


def extract_audio(
    video_path: str,
    audio_path: str,
    *,
    log_cb: LogCallback | None = None,
    runner: Callable[[list[str], str], Any] = run_ffmpeg,
) -> None:
    """Extract stereo 44.1 kHz PCM audio from a video file."""
    if log_cb is not None:
        log_cb(f"[1/6] Extracting audio from: {Path(video_path).name}")
    runner(build_extract_audio_cmd(video_path, audio_path), "extract_audio")
    if log_cb is not None:
        log_cb(f"     -> {audio_path}")
