"""Subtitle and final video output helpers."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable

from videotranslator.media import run_ffmpeg


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp."""
    h, rem = divmod(seconds, 3600)
    m, sec = divmod(rem, 60)
    ms = int((sec % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{ms:03d}"


def save_subtitles(
    segments: list[dict],
    output_base: str,
    *,
    log: Callable[..., None] = print,
) -> str:
    """Write translated segments to an SRT file and return its path."""
    path = output_base + ".srt"
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            text = (seg.get("text_tgt") or "").strip()
            f.write(
                f"{i}\n"
                f"{format_srt_timestamp(seg['start'])} --> "
                f"{format_srt_timestamp(seg['end'])}\n"
                f"{text}\n\n"
            )
    log(f"[+] Subtitles: {path}", flush=True)
    return path


def get_duration(
    video_path: str,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> float:
    """Return media duration in seconds using ffprobe."""
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read duration of {video_path}: {exc}") from exc


def mux_video(
    video_input: str,
    audio_track: str,
    output_path: str,
    *,
    run_ffmpeg: Callable[..., None] = run_ffmpeg,
    log: Callable[..., None] = print,
) -> None:
    """Mux the original video stream with the dubbed audio track."""
    log(f"[+] Muxing -> {output_path}", flush=True)
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_input,
            "-i",
            audio_track,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            output_path,
        ],
        step="mux_video",
    )
