"""Update the installed application from the project's GitHub releases.

``setup_windows.bat`` ([2] Repair / Update, ``update``) runs ``download``: when
the latest release is newer than the files next to the running installer, the
release zip is downloaded, verified and unpacked into ``%INSTALL_DIR%\\_update``
and the batch file hands over to that release's own installer. ``check`` only
reports (for a future notice in the GUI).

Standard library only: it must still work when the AI packages are broken.

Trust model (docs/superpowers/specs/2026-09-27-windows-updater-design.md):
HTTPS from one hard-coded repository. The SHA256 comes from the same release,
so it guards against transport errors and truncated files, not against a
compromised repository. Every check fails closed.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import shutil
import stat
import sys
import time
import zipfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from .libmpv_runtime import DownloadError, HttpClient

REPO = "HeartB1t/VideoTranslatorAI"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
LATEST_PAGE = f"https://github.com/{REPO}/releases/latest"
DOWNLOAD_BASE = f"https://github.com/{REPO}/releases/download"
ASSET_TEMPLATE = "VideoTranslatorAI-v{version}.zip"
SUMS_ASSET = "sha256.txt"
HANDOFF_FILE = "handoff.txt"
# The release must carry the installer, the application and the updater itself.
REQUIRED_FILES = ("setup_windows.bat", "video_translator_gui.py",
                  "videotranslator/__init__.py", "videotranslator/updater.py")
MAX_ZIP_BYTES = 64 << 20
MAX_UNPACKED_BYTES = 256 << 20
MAX_ENTRIES = 5000

EXIT_OK = 0            # up to date (check), nothing to hand over (download)
EXIT_UNAVAILABLE = 2   # no network, no API, no release: repair with the local files
EXIT_REJECTED = 3      # checksum or archive refused: repair with the local files
EXIT_NEWER = 10        # check: newer release; download: verified release ready

Version = tuple[int, int, int]

_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_INIT_VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)
_SUMS_LINE_RE = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(\S+)\s*$")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
# Windows opens these as devices whatever the extension ("nul.txt" is NUL).
_RESERVED_NAMES = frozenset({"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
                             *(f"COM{i}" for i in range(1, 10)),
                             *(f"LPT{i}" for i in range(1, 10))})


class UpdateError(Exception):
    """The release cannot be trusted or installed; nothing is handed over."""


@dataclass(frozen=True)
class Release:
    version: Version
    tag: str
    asset: str
    url: str
    sha256: str


def parse_version(text: Any) -> Version | None:
    """``"v2.1.0"`` or ``"2.1.0"`` as a tuple; anything else (rc, 4 parts) is None."""
    match = _VERSION_RE.fullmatch(str(text or "").strip())
    if not match:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return (major, minor, patch)


def format_version(version: Version | None) -> str:
    return ".".join(str(part) for part in version) if version else "unknown"


def is_newer(latest: Version, local: Version | None) -> bool:
    """An unreadable local version counts as older: the release replaces it."""
    return local is None or latest > local


def _version_in(text: str) -> Version | None:
    match = _INIT_VERSION_RE.search(text)
    return parse_version(match.group(1)) if match else None


def read_local_version(root: Path) -> Version | None:
    """``__version__`` of ``root/videotranslator``, read as text, never imported."""
    try:
        text = (Path(root) / "videotranslator" / "__init__.py").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _version_in(text)


def _valid_sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if _SHA256_RE.fullmatch(text) else None


def _release_sums(http: Any, tag: str) -> dict[str, str]:
    text = http.get_text(f"{DOWNLOAD_BASE}/{tag}/{SUMS_ASSET}")
    sums: dict[str, str] = {}
    for line in text.splitlines():
        match = _SUMS_LINE_RE.match(line.strip())
        if match:
            sums[match.group(2)] = match.group(1).lower()
    return sums


def _sums_checksum(http: Any, tag: str, name: str) -> str | None:
    try:
        return _valid_sha256(_release_sums(http, tag).get(name))
    except (OSError, ValueError):
        return None


def _from_api_answer(data: Any, http: Any, log: Callable[[str], None]) -> Release | None:
    if not isinstance(data, dict):
        log("GitHub API answer not understood")
        return None
    if data.get("draft") or data.get("prerelease"):
        log("the latest release is a draft or a pre-release: ignored")
        return None
    tag = str(data.get("tag_name") or "")
    version = parse_version(tag)
    if version is None:
        log(f"release tag {tag!r} is not vX.Y.Z: ignored")
        return None
    name = ASSET_TEMPLATE.format(version=format_version(version))
    assets = data.get("assets")
    asset = next((item for item in assets if isinstance(item, dict) and item.get("name") == name),
                 None) if isinstance(assets, list) else None
    if asset is None:
        log(f"release {tag} has no {name}")
        return None
    digest = str(asset.get("digest") or "")
    sha = _valid_sha256(digest.split(":", 1)[1]) if digest.startswith("sha256:") else None
    if sha is None:
        sha = _sums_checksum(http, tag, name)
    if sha is None:
        log(f"{name}: no published checksum, refused")
        return None
    url = str(asset.get("browser_download_url") or f"{DOWNLOAD_BASE}/{tag}/{name}")
    if not url.startswith("https://"):
        log(f"{name}: the download address is not HTTPS, refused")
        return None
    return Release(version, tag, name, url, sha)


def _from_latest_page(http: Any, log: Callable[[str], None]) -> Release | None:
    """API fallback (60 requests per hour per IP): the /releases/latest redirect."""
    try:
        tag = http.resolve(LATEST_PAGE).rstrip("/").rsplit("/", 1)[-1]
    except (OSError, ValueError) as exc:
        log(f"cannot reach the GitHub releases: {exc}")
        return None
    version = parse_version(tag)
    if version is None:
        log("no published release found")
        return None
    name = ASSET_TEMPLATE.format(version=format_version(version))
    sha = _sums_checksum(http, tag, name)
    if sha is None:
        log(f"{name}: no published checksum, refused")
        return None
    return Release(version, tag, name, f"{DOWNLOAD_BASE}/{tag}/{name}", sha)


def latest_release(http: Any, log: Callable[[str], None]) -> Release | None:
    """The newest published release with a verifiable zip, or None."""
    try:
        data = http.get_json(API_LATEST)
    except (OSError, ValueError) as exc:
        log(f"GitHub API unavailable ({exc}): using the latest release page")
        return _from_latest_page(http, log)
    return _from_api_answer(data, http, log)


def _safe_member(name: str) -> str:
    """The archive entry as a clean relative path, or UpdateError."""
    clean = name.replace("\\", "/")
    if not clean or clean.startswith("/") or ":" in clean:   # absolute, drive, stream
        raise UpdateError(f"unsafe path in the archive: {name!r}")
    parts = [part for part in clean.split("/") if part]
    for part in parts:
        # "..", "." and any name ending in a dot or a space (Windows drops them)
        if part != part.rstrip(". "):
            raise UpdateError(f"unsafe path in the archive: {name!r}")
        if part.split(".", 1)[0].upper() in _RESERVED_NAMES:
            raise UpdateError(f"reserved Windows name in the archive: {name!r}")
    return "/".join(parts)


def _plan(zf: zipfile.ZipFile) -> tuple[str, list[tuple[zipfile.ZipInfo, str]]]:
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise UpdateError(f"the archive has more than {MAX_ENTRIES} entries")
    plan: list[tuple[zipfile.ZipInfo, str]] = []
    seen: set[str] = set()
    tops: set[str] = set()
    for info in infos:
        if stat.S_ISLNK(info.external_attr >> 16):
            raise UpdateError(f"symbolic link in the archive: {info.filename!r}")
        rel = _safe_member(info.filename)
        if not rel:
            continue
        folded = rel.casefold()
        if folded in seen:
            raise UpdateError(f"two entries with the same name: {info.filename!r}")
        seen.add(folded)
        tops.add(rel.split("/", 1)[0])
        plan.append((info, rel))
    if len(tops) != 1:
        raise UpdateError("the archive must hold exactly one top folder")
    top = tops.pop()
    files = {rel for info, rel in plan if not info.is_dir()}
    for required in REQUIRED_FILES:
        if f"{top}/{required}" not in files:
            raise UpdateError(f"the archive has no {required}")
    return top, plan


def safe_extract(archive: Path, dest: Path, expected: Version) -> Path:
    """Check every entry, then unpack into ``dest``; the release folder is returned.

    Nothing is written before all checks pass. The size cap counts the bytes
    really decompressed: the sizes in the zip headers are not trusted.
    """
    dest = Path(dest)
    try:
        zf = zipfile.ZipFile(archive)
    except (zipfile.BadZipFile, OSError) as exc:
        raise UpdateError(f"not a valid zip: {exc}") from exc
    with zf:
        top, plan = _plan(zf)
        with zf.open(f"{top}/videotranslator/__init__.py") as handle:
            found = _version_in(handle.read(1 << 16).decode("utf-8", "replace"))
        if found != expected:
            raise UpdateError(f"the archive holds version {format_version(found)}, "
                              f"the release tag says {format_version(expected)}")
        created = not dest.exists()
        staging = dest / f".{top}.partial"
        try:
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir(parents=True)
            base = staging.resolve()
            total = 0
            for info, rel in plan:
                sub = rel.split("/", 1)[1] if "/" in rel else ""
                target = staging.joinpath(*sub.split("/")) if sub else staging
                if not target.resolve().is_relative_to(base):
                    raise UpdateError(f"unsafe path in the archive: {info.filename!r}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    for block in iter(lambda: src.read(1 << 16), b""):
                        total += len(block)
                        if total > MAX_UNPACKED_BYTES:
                            raise UpdateError(f"the archive unpacks to more than {MAX_UNPACKED_BYTES} bytes")
                        out.write(block)
            final = dest / top
            if final.exists():
                shutil.rmtree(final)
            os.replace(staging, final)
        except (zipfile.BadZipFile, zlib.error) as exc:
            shutil.rmtree(staging, ignore_errors=True)
            raise UpdateError(f"damaged archive: {exc}") from exc
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            if created:
                shutil.rmtree(dest, ignore_errors=True)
            raise
    return final


def download(release: Release, dest: Path, http: Any, log: Callable[[str], None]) -> Path:
    """Fetch, verify and unpack ``release`` into a fresh ``dest``; its installer is returned.

    On any failure ``dest`` is removed, so the batch file never finds half an
    update. On success ``dest/handoff.txt`` holds the installer's path.
    """
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = dest / release.asset
    part = dest / (release.asset + ".part")
    try:
        log(f"downloading {release.asset}")
        got = http.fetch(release.url, part, max_bytes=MAX_ZIP_BYTES)
        if got.lower() != release.sha256.lower():
            raise UpdateError(f"SHA256 mismatch for {release.asset}")
        os.replace(part, archive)
        log(f"{release.asset}: SHA256 verified")
        root = safe_extract(archive, dest, release.version)
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    finally:
        for leftover in (part, archive):
            with contextlib.suppress(OSError):
                leftover.unlink()
    installer = root / "setup_windows.bat"
    (dest / HANDOFF_FILE).write_text(f"{installer}\n", encoding="utf-8")
    return installer


def main(argv: list[str] | None = None, *, http: Any = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m videotranslator.updater",
                                     description="Update VideoTranslatorAI from its GitHub releases.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "download"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--local", type=Path, required=True,
                         help="folder with the files the installer would copy")
        cmd.add_argument("--log", type=Path, default=None, help="setup log to append to")
        if name == "download":
            cmd.add_argument("--dest", type=Path, required=True, help="folder for the new release")
    args = parser.parse_args(argv)
    out = stdout or sys.stdout

    def log(message: str) -> None:
        print(f"  [updater] {message}", file=out, flush=True)
        if args.log:
            with contextlib.suppress(OSError), open(args.log, "a", encoding="utf-8") as handle:
                handle.write(f"[{time.strftime('%H:%M:%S')}] Updater: {message}\n")

    if args.command == "download":
        with contextlib.suppress(OSError):
            (args.dest / HANDOFF_FILE).unlink()   # never hand over to a stale release
    http = http or HttpClient()
    local = read_local_version(args.local)
    log(f"files next to the installer: version {format_version(local)}")
    try:
        release = latest_release(http, log)
    except Exception as exc:   # the batch file must see an exit code, never a traceback
        log(f"cannot check for updates: {exc}")
        return EXIT_UNAVAILABLE
    if release is None:
        log("no verified release found: keeping the local files")
        return EXIT_UNAVAILABLE
    log(f"latest release on GitHub: {format_version(release.version)}")
    if not is_newer(release.version, local):
        log("already up to date")
        return EXIT_OK
    log(f"update available: {format_version(local)} -> {format_version(release.version)}")
    if args.command == "check":
        return EXIT_NEWER
    try:
        installer = download(release, args.dest, http, log)
    except (UpdateError, DownloadError) as exc:
        log(f"update refused: {exc}")
        return EXIT_REJECTED
    except (OSError, ValueError) as exc:
        log(f"download failed: {exc}")
        return EXIT_UNAVAILABLE
    log(f"verified release ready: {installer}")
    return EXIT_NEWER


if __name__ == "__main__":
    sys.exit(main())
