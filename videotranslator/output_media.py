"""Subtitle and final video output helpers."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable

from videotranslator.media import run_ffmpeg


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp."""
    total_ms = max(0, int(round(seconds * 1000)))
    total_seconds, ms = divmod(total_ms, 1000)
    h, rem = divmod(total_seconds, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def segments_to_srt(segments: list[dict] | tuple[dict, ...]) -> str:
    """Render translated segments as SRT without touching the filesystem."""
    blocks = []
    for index, segment in enumerate(segments, 1):
        text = (segment.get("text_tgt") or "").strip()
        blocks.append(
            f"{index}\n"
            f"{format_srt_timestamp(segment['start'])} --> "
            f"{format_srt_timestamp(segment['end'])}\n"
            f"{text}\n\n"
        )
    return "".join(blocks)


def save_subtitles(
    segments: list[dict],
    output_base: str,
    *,
    log: Callable[..., None] = print,
) -> str:
    """Write translated segments to an SRT file and return its path."""
    path = output_base + ".srt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(segments_to_srt(segments))
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
    original_audio_input: str | None = None,
    run_ffmpeg: Callable[..., None] = run_ffmpeg,
    log: Callable[..., None] = print,
) -> None:
    """Mux the original video stream with the dubbed audio track."""
    log(f"[+] Muxing -> {output_path}", flush=True)
    if original_audio_input is None:
        # Keep the legacy command stable for callers that opt out.
        command = [
            "ffmpeg", "-y", "-i", video_input, "-i", audio_track,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0", output_path,
        ]
    else:
        same_input = original_audio_input == video_input
        command = ["ffmpeg", "-y", "-i", video_input, "-i", audio_track]
        if not same_input:
            command += ["-i", original_audio_input]
        original_index = 0 if same_input else 2
        command += [
            "-c:v", "copy",
            "-c:a:0", "aac", "-b:a:0", "192k",
            "-c:a:1", "aac", "-b:a:1", "160k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-metadata:s:a:0", "title=Dubbed",
            "-metadata:s:a:0", "handler_name=Dubbed",
            "-disposition:a:0", "default",
            "-map", f"{original_index}:a:0?",
            "-metadata:s:a:1", "title=Original",
            "-metadata:s:a:1", "handler_name=Original",
            "-disposition:a:1", "0", output_path,
        ]
    run_ffmpeg(
        command,
        step="mux_video",
    )
