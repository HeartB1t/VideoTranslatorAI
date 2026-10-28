"""Input-source helpers for local files and yt-dlp downloads."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

COOKIES_FILE_KEY = "yt_dlp_cookies_file"


class _YoutubeDLLike(Protocol):
    def __enter__(self) -> "_YoutubeDLLike": ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...
    def extract_info(self, url: str, download: bool) -> dict[str, Any]: ...
    def prepare_filename(self, info: dict[str, Any]) -> str: ...


# Browsers yt-dlp can read cookies from, in order of preference: Firefox
# first (its cookies read reliably on every OS), Edge and Chrome last (on
# Windows their cookie store is often locked or app-bound encrypted).
_CHROMIUM_ORDER = ("brave", "vivaldi", "opera", "whale", "chromium", "edge", "chrome")


def _browser_profile_roots(
    sys_platform: str, env: Mapping[str, str], home: Path
) -> list[tuple[str, list[Path], str]]:
    """(browser, profile roots, cookie database name), mirroring where yt-dlp looks."""
    if sys_platform in ("win32", "cygwin"):
        local = Path(env.get("LOCALAPPDATA", home / "AppData" / "Local"))
        roaming = Path(env.get("APPDATA", home / "AppData" / "Roaming"))
        firefox = [roaming / "Mozilla" / "Firefox" / "Profiles",
                   local / "Packages" / "Mozilla.Firefox_n80bbvh6b1yt2" / "LocalCache"
                   / "Roaming" / "Mozilla" / "Firefox" / "Profiles"]
        chromium = {
            "brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
            "chrome": local / "Google" / "Chrome" / "User Data",
            "chromium": local / "Chromium" / "User Data",
            "edge": local / "Microsoft" / "Edge" / "User Data",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "vivaldi": local / "Vivaldi" / "User Data",
            "whale": local / "Naver" / "Naver Whale" / "User Data",
        }
    elif sys_platform == "darwin":
        support = home / "Library" / "Application Support"
        firefox = [support / "Firefox" / "Profiles"]
        chromium = {
            "brave": support / "BraveSoftware" / "Brave-Browser",
            "chrome": support / "Google" / "Chrome",
            "chromium": support / "Chromium",
            "edge": support / "Microsoft Edge",
            "opera": support / "com.operasoftware.Opera",
            "vivaldi": support / "Vivaldi",
            "whale": support / "Naver" / "Whale",
        }
    else:
        config = Path(env.get("XDG_CONFIG_HOME") or home / ".config")
        firefox = [config / "mozilla" / "firefox",
                   home / ".mozilla" / "firefox",
                   home / ".var" / "app" / "org.mozilla.firefox" / "config" / "mozilla" / "firefox",
                   home / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox",
                   home / "snap" / "firefox" / "common" / ".mozilla" / "firefox"]
        chromium = {
            "brave": config / "BraveSoftware" / "Brave-Browser",
            "chrome": config / "google-chrome",
            "chromium": config / "chromium",
            "edge": config / "microsoft-edge",
            "opera": config / "opera",
            "vivaldi": config / "vivaldi",
            "whale": config / "naver-whale",
        }
    return [("firefox", firefox, "cookies.sqlite")] + [
        (name, [chromium[name]], "Cookies") for name in _CHROMIUM_ORDER
    ]


def _has_file_named(root: Path, filename: str, max_depth: int = 3) -> bool:
    """True when ``filename`` exists in ``root`` or up to ``max_depth`` levels below."""
    stack = [(root, 0)]
    while stack:
        folder, depth = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.name == filename and entry.is_file():
                        return True
                    if depth < max_depth and entry.is_dir(follow_symlinks=False):
                        stack.append((Path(entry.path), depth + 1))
        except OSError:
            continue
    return False


def _detect_browser(
    sys_platform: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> tuple[str, ...] | None:
    """Return (browser_name,) for yt-dlp cookiesfrombrowser, or None if not found.

    A browser counts only when its cookie database exists: an installed but
    never used browser (or an unsupported one) would make yt-dlp abort the
    download with "failed to load cookies".
    """
    sys_platform = sys.platform if sys_platform is None else sys_platform
    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    for browser, roots, filename in _browser_profile_roots(sys_platform, env, home):
        if any(_has_file_named(root, filename) for root in roots):
            return (browser,)
    return None


COOKIES_FILE_ENV = "VTAI_COOKIES_FILE"


def _configured_cookies_file() -> str | None:
    """The cookies.txt path to use: the ``VTAI_COOKIES_FILE`` env var (set by the
    CLI ``--cookies-file``) wins over the ``yt_dlp_cookies_file`` user config."""
    env_value = os.environ.get(COOKIES_FILE_ENV, "").strip()
    if env_value:
        return env_value

    from videotranslator.config import load_user_config

    try:
        value = load_user_config().get(COOKIES_FILE_KEY)
    except Exception:
        return None
    if not value:
        return None
    return str(value).strip() or None


def _is_cookie_load_error(exc: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ == "CookieLoadError":
            return True
        current = current.__cause__ or current.__context__
    return "failed to load cookies" in str(exc).lower()


def _run_ytdlp(
    ytdlp_cls: Callable[[dict[str, Any]], _YoutubeDLLike],
    opts: dict[str, Any],
    action: Callable[[_YoutubeDLLike], Any],
    log_cb: Callable[[str], None] | None,
) -> Any:
    """Run ``action`` on a yt-dlp instance; retry once without browser cookies
    when they cannot be read (locked or encrypted store), instead of failing."""
    try:
        with ytdlp_cls(opts) as ydl:
            return action(ydl)
    except Exception as exc:
        browser = opts.get("cookiesfrombrowser")
        if not (browser and _is_cookie_load_error(exc)):
            emit_download_advice(exc, log_cb)
            raise
        if log_cb is not None:
            log_cb(f"[!] Could not read the {browser[0]} cookies (close the browser, or set "
                   f"{COOKIES_FILE_KEY} to an exported cookies.txt): retrying without them.")
    retry = {key: value for key, value in opts.items() if key != "cookiesfrombrowser"}
    try:
        with ytdlp_cls(retry) as ydl:
            return action(ydl)
    except Exception as exc:
        emit_download_advice(exc, log_cb)
        raise


def emit_download_warnings(log_cb: Callable[[str], None] | None) -> None:
    """Emit advisory warnings before a URL download (anti-bot / VPN advice)."""
    if log_cb is None:
        return

    log_cb(
        "[!] YouTube may require anti-bot authentication ('Sign in to "
        "confirm you're not a bot'). The block is usually tied to IP "
        "reputation: switching IP with a VPN often clears it. Being logged "
        "into YouTube in your browser also helps (cookies are read automatically), "
        f"or set {COOKIES_FILE_KEY} in config.json to a cookies.txt exported from it."
    )


# yt-dlp error texts that mean an IP / anti-bot block (the VPN advice helps)
# or a video only paying members can watch (the VPN advice would mislead).
# "http error 403" on YouTube video data (after the manifest extracted fine)
# is an IP / token throttle too: the data URLs are refused without a valid
# session, so the same VPN / logged-in-cookies advice applies.
_BOT_BLOCK_MARKERS = ("not a bot", "sign in to confirm", "http error 429",
                      "too many requests", "http error 403")
_MEMBERS_ONLY_MARKERS = ("members-only", "members only", "join this channel",
                         "available to this channel's members")


def emit_download_advice(error: BaseException, log_cb: Callable[[str], None] | None) -> None:
    """After a failed yt-dlp call, explain the cause when it is a known one.

    The anti-bot / VPN advice is shown only when the error is an IP or bot
    block, not before every download (it misled on unrelated errors).
    """
    if log_cb is None:
        return
    text = str(error).lower()
    if any(marker in text for marker in _MEMBERS_ONLY_MARKERS):
        log_cb("[!] This video is for the channel's paying members only: it cannot be "
               "downloaded without a member account (a VPN does not help).")
    elif any(marker in text for marker in _BOT_BLOCK_MARKERS):
        emit_download_warnings(log_cb)


def build_ytdlp_options(
    out_dir: str | os.PathLike[str],
    *,
    js_runtimes: dict[str, Any] | None = None,
    cookies_file: str | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Return the project's standard yt-dlp options for one URL.

    ``js_runtimes`` overrides runtime selection; when None we auto-detect an
    already-available runtime (PATH or app-local bin) so yt-dlp can solve the
    YouTube signature challenge instead of falling back to bot-blocked clients.
    ``cookies_file`` (default: ``yt_dlp_cookies_file`` from the user config) is
    an exported cookies.txt; when it exists it replaces the browser cookies.
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
        # "default" keeps yt-dlp's own client choice, which it updates with each
        # release as YouTube changes and adapts to cookies / JS runtime; a fixed
        # list froze it (and android/ios are skipped once cookies are loaded).
        # tv and android_vr are added because they still serve progressive
        # itag 18 for VODs (live mode); android_vr may need a GVS PO token.
        "extractor_args": {
            "youtube": {"player_client": ["default", "tv", "android_vr"]}
        },
    }
    cookies_file = _configured_cookies_file() if cookies_file is None else cookies_file
    if cookies_file and os.path.isfile(os.path.expanduser(cookies_file)):
        opts["cookiefile"] = os.path.expanduser(cookies_file)
    else:
        if cookies_file and log_cb is not None:
            log_cb(f"[!] {COOKIES_FILE_KEY} not found: {cookies_file} (using browser cookies)")
        browser = _detect_browser()
        if browser:
            opts["cookiesfrombrowser"] = browser

    runtimes = js_runtimes if js_runtimes is not None else resolve_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = runtimes
    return opts


def build_ytdlp_audio_options(
    out_dir: str | os.PathLike[str],
    *,
    js_runtimes: dict[str, Any] | None = None,
    cookies_file: str | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Return yt-dlp options for an audio-only download.

    Same policy as ``build_ytdlp_options`` (cookies, outtmpl, restrictfilenames,
    js_runtimes, extractor args) but it asks for ``bestaudio/best`` and drops the
    ``merge_output_format`` remux so yt-dlp keeps bestaudio's native container
    (.m4a/.webm/.opus) instead of wrapping it in mp4.
    """
    opts = build_ytdlp_options(out_dir, js_runtimes=js_runtimes,
                               cookies_file=cookies_file, log_cb=log_cb)
    opts["format"] = "bestaudio/best"
    opts.pop("merge_output_format", None)
    return opts


# Containers yt-dlp commonly writes for an audio-only download.
_AUDIO_DOWNLOAD_EXTENSIONS = (
    ".m4a", ".webm", ".opus", ".mp3", ".ogg", ".oga", ".wav", ".aac",
)


def resolve_downloaded_filename(
    prepared_filename: str | os.PathLike[str],
    *,
    extensions: tuple[str, ...] = (".mp4", ".mkv", ".webm"),
) -> str:
    """Return the final file path after yt-dlp merge/output extension changes.

    ``extensions`` lists the containers to probe when the prepared name does not
    exist (the merge/remux changed it); audio-only downloads pass audio ones.
    """
    filename = str(prepared_filename)
    if os.path.exists(filename):
        return filename

    stem = os.path.splitext(filename)[0]
    for ext in extensions:
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

    # Lazy: make sure yt-dlp has a JS runtime (auto-install deno if none).
    js_runtimes = ensure_js_runtime(log_cb=log_cb)
    opts = build_ytdlp_options(out_dir, js_runtimes=js_runtimes, log_cb=log_cb)

    def action(ydl: _YoutubeDLLike) -> str:
        info = ydl.extract_info(url, download=True)
        return resolve_downloaded_filename(ydl.prepare_filename(info))

    filename = _run_ytdlp(ytdlp_cls, opts, action, log_cb)
    if log_cb is not None:
        log_cb(f"[+] Downloaded: {filename}")
    return filename


def download_audio_url(
    url: str,
    out_dir: str | os.PathLike[str],
    *,
    ytdlp_cls: Callable[[dict[str, Any]], _YoutubeDLLike] | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> str:
    """Download one URL audio-only with yt-dlp and return the final media path.

    Mirrors ``download_url`` (same JS-runtime setup and error advice) but uses
    the bestaudio options and probes audio containers to find the saved file.
    ``ytdlp_cls`` is injectable so tests exercise the contract without yt-dlp or
    the network.
    """
    if ytdlp_cls is None:
        import yt_dlp

        ytdlp_cls = yt_dlp.YoutubeDL

    from videotranslator.js_runtime import ensure_js_runtime

    js_runtimes = ensure_js_runtime(log_cb=log_cb)
    opts = build_ytdlp_audio_options(out_dir, js_runtimes=js_runtimes, log_cb=log_cb)

    def action(ydl: _YoutubeDLLike) -> str:
        info = ydl.extract_info(url, download=True)
        return resolve_downloaded_filename(
            ydl.prepare_filename(info),
            extensions=_AUDIO_DOWNLOAD_EXTENSIONS,
        )

    filename = _run_ytdlp(ytdlp_cls, opts, action, log_cb)
    if log_cb is not None:
        log_cb(f"[+] Downloaded audio: {filename}")
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
    # No muxed format. Fall back to the top-level URL only when it is not known
    # to be video-only: a direct media link often carries no codec metadata and
    # must still pass, but a known video-only stream would play muted and make
    # the live audio decoder fail with a cryptic IndexError, so reject it and let
    # resolve_stream_url raise a clear "no playable stream" message.
    top = info.get("url")
    if (top and info.get("vcodec", "none") != "none"
            and info.get("acodec", "none") == "none"):
        return None
    return top


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

    js_runtimes = ensure_js_runtime(log_cb=log_cb)
    opts = build_ytdlp_options(".", js_runtimes=js_runtimes, log_cb=log_cb)
    opts["format"] = (
        f"best[acodec!=none][vcodec!=none][height<={max_height}]"
        "/best[acodec!=none][vcodec!=none]/best"
    )
    info = _run_ytdlp(ytdlp_cls, opts, lambda ydl: ydl.extract_info(url, download=False), log_cb)
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
