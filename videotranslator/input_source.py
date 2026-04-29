"""Input-source helpers for local files and yt-dlp downloads."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol


class _YoutubeDLLike(Protocol):
    def __enter__(self) -> "_YoutubeDLLike": ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...
    def extract_info(self, url: str, download: bool) -> dict[str, Any]: ...
    def prepare_filename(self, info: dict[str, Any]) -> str: ...


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


def download_url(
    url: str,
    out_dir: str | os.PathLike[str],
    *,
    ytdlp_cls: Callable[[dict[str, Any]], _YoutubeDLLike] | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> str:
    """Download one URL with yt-dlp and return the final media path.

    ``ytdlp_cls`` is injectable so tests can exercise the contract without
    importing yt-dlp or touching the network.
    """
    if ytdlp_cls is None:
        import yt_dlp

        ytdlp_cls = yt_dlp.YoutubeDL

    opts = build_ytdlp_options(out_dir)
    with ytdlp_cls(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = resolve_downloaded_filename(ydl.prepare_filename(info))

    if log_cb is not None:
        log_cb(f"[+] Downloaded: {filename}")
    return filename


def is_probable_url(value: str) -> bool:
    """Small URL classifier used by future CLI/GUI input handling."""
    text = (value or "").strip().lower()
    return text.startswith(("http://", "https://"))


def normalize_input_path(value: str | os.PathLike[str]) -> str:
    """Expand a local input path without requiring it to exist."""
    return str(Path(value).expanduser())
