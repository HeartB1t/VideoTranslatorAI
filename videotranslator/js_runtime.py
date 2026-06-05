"""JavaScript runtime provisioning for yt-dlp.

Recent yt-dlp needs an external JS runtime (deno by default; node/bun/quickjs
are also supported) to solve YouTube's signature challenge. Without one, yt-dlp
falls back to weak player clients that YouTube bot-blocks, surfacing as
"Sign in to confirm you're not a bot".

Policy implemented here (two tiers):

* **Tier 1 — no install:** if a runtime is already reachable (on PATH or in the
  app-local bin dir), tell yt-dlp to use it. Zero download.
* **Tier 2 — auto-install:** if none is present, fetch the standalone ``deno``
  binary (single self-contained file, no admin) into the app-local bin dir and
  point yt-dlp at it.

The pure helpers (asset name, URLs, path resolution) are split from the
side-effecting ones (download/extract) so the policy is unit-testable without
touching the network.
"""

from __future__ import annotations

import io
import os
import platform
import shutil
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


# Order of preference: deno is yt-dlp's first-class runtime; node/bun are
# common on dev machines and fully supported.
JS_RUNTIME_PREFERENCE: tuple[str, ...] = ("deno", "node", "bun")

# deno publishes per-target zips on every GitHub release; "latest" always
# resolves to the newest stable.
DENO_RELEASE_BASE = "https://github.com/denoland/deno/releases/latest/download"

# Network read timeout for the binary download (seconds).
DENO_DOWNLOAD_TIMEOUT = 180


# ── pure helpers ────────────────────────────────────────────────────────────

def _normalize_machine(machine: str) -> str:
    """Collapse arch aliases to deno's naming (x86_64 / aarch64)."""
    m = (machine or "").lower()
    if m in ("x86_64", "amd64", "x64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "aarch64"
    return m


def _is_windows(system: str) -> bool:
    return system.lower().startswith("win")


def deno_asset_name(system: str, machine: str) -> str:
    """Return the deno release asset filename for ``system``/``machine``.

    Raises ``RuntimeError`` when deno ships no build for the platform.
    """
    arch = _normalize_machine(machine)
    sysl = system.lower()
    if sysl.startswith("linux"):
        if arch in ("x86_64", "aarch64"):
            return f"deno-{arch}-unknown-linux-gnu.zip"
    elif _is_windows(sysl):
        if arch == "x86_64":
            return "deno-x86_64-pc-windows-msvc.zip"
    elif sysl == "darwin":
        if arch in ("x86_64", "aarch64"):
            return f"deno-{arch}-apple-darwin.zip"
    raise RuntimeError(f"No prebuilt deno binary for {system}/{machine}")


def deno_download_url(system: str, machine: str) -> str:
    """Full URL of the deno zip for the given platform."""
    return f"{DENO_RELEASE_BASE}/{deno_asset_name(system, machine)}"


def app_data_dir(
    *,
    system: str | None = None,
    env: dict[str, str] | None = None,
    home: str | None = None,
) -> Path:
    """Return the per-user app data directory (platform-correct)."""
    system = system if system is not None else sys.platform
    env = env if env is not None else dict(os.environ)
    home = home if home is not None else os.path.expanduser("~")

    if _is_windows(system):
        base = env.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        return Path(base) / "VideoTranslatorAI"
    if system.lower() == "darwin":
        return Path(home) / "Library" / "Application Support" / "VideoTranslatorAI"
    base = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return Path(base) / "VideoTranslatorAI"


def app_bin_dir(**kwargs: Any) -> Path:
    """App-local bin dir where auto-installed runtimes live."""
    return app_data_dir(**kwargs) / "bin"


def runtime_binary_name(name: str, system: str) -> str:
    """Executable filename for a runtime on ``system`` (adds .exe on Windows)."""
    return f"{name}.exe" if _is_windows(system) else name


def find_runtime(
    *,
    which: Callable[[str], str | None] = shutil.which,
    bin_dir: str | os.PathLike[str] | None = None,
    system: str | None = None,
    preference: tuple[str, ...] = JS_RUNTIME_PREFERENCE,
) -> tuple[str, str] | None:
    """Return (runtime_name, path) of the first available runtime, or None.

    Looks on PATH first, then in the app-local bin dir (where Tier-2 installs
    land — that dir is intentionally NOT added to the user's PATH).
    """
    system = system if system is not None else sys.platform
    resolved_bin = Path(bin_dir) if bin_dir is not None else app_bin_dir(system=system)
    for name in preference:
        on_path = which(name)
        if on_path:
            return (name, on_path)
        candidate = resolved_bin / runtime_binary_name(name, system)
        if candidate.exists():
            return (name, str(candidate))
    return None


def resolve_js_runtimes(**kwargs: Any) -> dict[str, dict[str, str]] | None:
    """Return a yt-dlp ``js_runtimes`` dict for the first available runtime.

    None when nothing is found (yt-dlp then falls back to its default).
    """
    found = find_runtime(**kwargs)
    if not found:
        return None
    name, path = found
    return {name: {"path": path}}


# ── side-effecting helpers ──────────────────────────────────────────────────

def _default_download(url: str) -> bytes:
    from urllib.request import urlopen

    with urlopen(url, timeout=DENO_DOWNLOAD_TIMEOUT) as resp:  # noqa: S310 (https only)
        return resp.read()


def _deno_member(zf: zipfile.ZipFile, exe: str) -> str:
    """Find the deno binary entry inside the release zip."""
    for entry in zf.namelist():
        if Path(entry).name == exe:
            return entry
    raise RuntimeError(f"deno binary '{exe}' not found in archive")


def install_deno(
    *,
    system: str | None = None,
    machine: str | None = None,
    bin_dir: str | os.PathLike[str] | None = None,
    downloader: Callable[[str], bytes] | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> str:
    """Download and extract the standalone deno binary; return its path.

    ``downloader`` is injectable so tests exercise extraction without network.
    """
    system = system if system is not None else sys.platform
    machine = machine if machine is not None else platform.machine()
    resolved_bin = Path(bin_dir) if bin_dir is not None else app_bin_dir(system=system)
    exe = runtime_binary_name("deno", system)
    target = resolved_bin / exe

    url = deno_download_url(system, machine)
    resolved_bin.mkdir(parents=True, exist_ok=True)
    if log_cb:
        log_cb(f"     Downloading deno JS runtime (yt-dlp dependency) → {target}")

    data = (downloader or _default_download)(url)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        member = _deno_member(zf, exe)
        with zf.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)

    if not _is_windows(system):
        os.chmod(target, 0o755)
    if log_cb:
        log_cb(f"     deno installed: {target}")
    return str(target)


def ensure_js_runtime(
    *,
    install: bool = True,
    log_cb: Callable[[str], None] | None = None,
    finder: Callable[..., dict[str, dict[str, str]] | None] = resolve_js_runtimes,
    installer: Callable[..., str] = install_deno,
) -> dict[str, dict[str, str]] | None:
    """Resolve a JS runtime for yt-dlp, auto-installing deno if needed.

    Returns a yt-dlp ``js_runtimes`` dict, or None if no runtime is available
    and installation was skipped or failed.
    """
    existing = finder()
    if existing:
        if log_cb:
            name = next(iter(existing))
            log_cb(f"     JS runtime for yt-dlp: {name} ({existing[name].get('path')})")
        return existing

    if not install:
        return None

    if log_cb:
        log_cb(
            "[!] Nessun JS runtime trovato — yt-dlp lo richiede per YouTube. "
            "Installo deno automaticamente (binario singolo, nessun admin)..."
        )
    try:
        path = installer(log_cb=log_cb)
    except Exception as exc:  # network, unsupported arch, extraction, fs
        if log_cb:
            log_cb(
                f"[!] Auto-install di deno fallito: {exc}. "
                "Installa manualmente un runtime (es. 'curl -fsSL "
                "https://deno.land/install.sh | sh') e riprova."
            )
        return None
    return {"deno": {"path": path}}
