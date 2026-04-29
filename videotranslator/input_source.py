"""Input-source helpers for local files and yt-dlp downloads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def build_ytdlp_options(out_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Return the project's standard yt-dlp options for one URL."""
    out_template = os.path.join(str(out_dir), "%(title).80s.%(ext)s")
    return {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "restrictfilenames": True,
        "socket_timeout": 30,
        "retries": 5,
        "extractor_args": {"youtube": {"player_client": ["ios", "android"]}},
    }


def resolve_downloaded_filename(prepared_filename: str | os.PathLike[str]) -> str:
    """Return the final file path after yt-dlp merge/output extension changes."""
    filename = str(prepared_filename)
    if os.path.exists(filename):
        return filename

    stem = os.path.splitext(filename)[0]
    for ext in (".mp4", ".mkv", ".webm"):
        candidate = stem + ext
        if os.path.exists(candidate):
            return candidate

    raise RuntimeError(f"Download completed but file not found: {filename}")


def is_probable_url(value: str) -> bool:
    """Small URL classifier used by future CLI/GUI input handling."""
    text = (value or "").strip().lower()
    return text.startswith(("http://", "https://"))


def normalize_input_path(value: str | os.PathLike[str]) -> str:
    """Expand a local input path without requiring it to exist."""
    return str(Path(value).expanduser())
