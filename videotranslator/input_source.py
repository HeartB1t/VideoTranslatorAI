"""Input-source helpers for local files and yt-dlp downloads."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol


class _YoutubeDLLike(Protocol):
    def __enter__(self) -> "_YoutubeDLLike": ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...
    def extract_info(self, url: str, download: bool) -> dict[str, Any]: ...
    def prepare_filename(self, info: dict[str, Any]) -> str: ...


def _detect_browser() -> tuple[str, ...] | None:
    """Return (browser_name,) for yt-dlp cookiesfrombrowser, or None if not found."""
    for browser in ("firefox", "chromium", "chrome", "brave", "librewolf", "vivaldi"):
        if shutil.which(browser):
            return (browser,)
    return None


def emit_download_warnings(log_cb: Callable[[str], None] | None) -> None:
    """Emit advisory warnings before a URL download (anti-bot / VPN advice)."""
    if log_cb is None:
        return

    log_cb(
        "[!] YouTube may require anti-bot authentication ('Sign in to "
        "confirm you're not a bot'). The block is usually tied to IP "
        "reputation: switching IP with a VPN often clears it. Being logged "
        "into YouTube in your browser also helps (cookies are read automatically)."
    )


def build_ytdlp_options(
    out_dir: str | os.PathLike[str],
    *,
    js_runtimes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the project's standard yt-dlp options for one URL.

    ``js_runtimes`` overrides runtime selection; when None we auto-detect an
    already-available runtime (PATH or app-local bin) so yt-dlp can solve the
    YouTube signature challenge instead of falling back to bot-blocked clients.
    """
    from videotranslator.js_runtime import resolve_js_runtimes

    out_template = os.path.join(str(out_dir), "%(title).80s.%(ext)s")
    opts: dict[str, Any] = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "restrictfilenames": True,
        "socket_timeout": 30,
        "retries": 5,
        "extractor_args": {"youtube": {"player_client": ["web", "ios", "android"]}},
    }
    browser = _detect_browser()
    if browser:
        opts["cookiesfrombrowser"] = browser

    runtimes = js_runtimes if js_runtimes is not None else resolve_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = runtimes
    return opts


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

    from videotranslator.js_runtime import ensure_js_runtime

    emit_download_warnings(log_cb)
    # Lazy: make sure yt-dlp has a JS runtime (auto-install deno if none).
    js_runtimes = ensure_js_runtime(log_cb=log_cb)
    opts = build_ytdlp_options(out_dir, js_runtimes=js_runtimes)
    with ytdlp_cls(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = resolve_downloaded_filename(ydl.prepare_filename(info))

    if log_cb is not None:
        log_cb(f"[+] Downloaded: {filename}")
    return filename


def _pick_stream_url(info: dict[str, Any], max_height: int) -> str | None:
    """Best progressive (audio+video) stream URL in ``info``, or None.

    Prefers the format yt-dlp already selected; otherwise scans every format for
    the tallest muxed one at or below ``max_height`` so both mpv (video+audio)
    and PyAV (audio) read a single stream.
    """
    if (info.get("url") and info.get("acodec", "none") != "none"
            and info.get("vcodec", "none") != "none"):
        return info["url"]
    best = None
    for fmt in info.get("formats", []):
        if (fmt.get("url") and fmt.get("acodec", "none") != "none"
                and fmt.get("vcodec", "none") != "none"):
            height = fmt.get("height") or 0
            if height <= max_height and (best is None
                                         or height > (best.get("height") or 0)):
                best = fmt
    if best is not None:
        return best["url"]
    return info.get("url")


def resolve_stream_url(
    url: str,
    *,
    ytdlp_cls: Callable[[dict[str, Any]], _YoutubeDLLike] | None = None,
    log_cb: Callable[[str], None] | None = None,
    max_height: int = 720,
) -> tuple[str, str]:
    """Resolve a video URL to a direct progressive stream URL (design 4.7, P6 VOD).

    Returns ``(stream_url, title)``. Picks a single muxed format so the player
    and the live decoder can both open one URL and stream progressively; a true
    live broadcast (a growing stream) is out of scope here. ``ytdlp_cls`` is
    injectable so tests exercise the contract without yt-dlp or the network.
    """
    if ytdlp_cls is None:
        import yt_dlp

        ytdlp_cls = yt_dlp.YoutubeDL

    from videotranslator.js_runtime import ensure_js_runtime

    emit_download_warnings(log_cb)
    js_runtimes = ensure_js_runtime(log_cb=log_cb)
    opts = build_ytdlp_options(".", js_runtimes=js_runtimes)
    opts["format"] = (
        f"best[acodec!=none][vcodec!=none][height<={max_height}]"
        "/best[acodec!=none][vcodec!=none]/best"
    )
    with ytdlp_cls(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise RuntimeError("the URL resolved to an empty playlist")
        info = entries[0]
    stream_url = _pick_stream_url(info, max_height)
    if not stream_url:
        raise RuntimeError("no playable progressive stream found for this URL")
    title = info.get("title") or url
    if log_cb is not None:
        log_cb(f"[+] Live source resolved: {title}")
    return stream_url, title


def is_probable_url(value: str) -> bool:
    """Small URL classifier used by future CLI/GUI input handling."""
    text = (value or "").strip().lower()
    return text.startswith(("http://", "https://"))


def normalize_input_path(value: str | os.PathLike[str]) -> str:
    """Expand a local input path without requiring it to exist."""
    return str(Path(value).expanduser())
