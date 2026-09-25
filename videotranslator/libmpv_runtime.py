"""Find, probe and import libmpv for the integrated player (spec 2.2, 3.1, 6.1).

Policy:

* ``quick_presence`` loads nothing: it looks for the library file (Windows)
  or asks ``ldconfig -p`` (Linux). It feeds the startup badge.
* ``probe_libmpv`` loads the library with ctypes, reads the client API and
  the mpv version and checks which video-output profiles this build accepts.
  It runs ONLY inside ``python -m videotranslator.libmpv_runtime check``
  (``probe_in_subprocess``), so a library that crashes on load cannot take
  the application down.
* ``load_mpv`` is the only ``import mpv`` in the code base; it must run off
  the Tk thread (P2).

Every side effect is a parameter, so the tests run without libmpv,
python-mpv, network or display. Log and detail text stays English; the GUI
shows translated keys (REASON_KEYS).
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import ctypes.util
import dataclasses
import hashlib
import importlib
import importlib.util
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
import urllib.request
import zipfile
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from .js_runtime import app_data_dir
from .subprocess_utils import no_window_kwargs

MIN_API = (1, 108)          # python-mpv refuses older libmpv at import (mpv.py:565)
TESTED_FLOOR = (0, 34)      # lowest mpv release covered by the S1/S3 checks (Q13)
AF_TARGET_MIN = (0, 37)     # `af-command ... <target>` exists from 0.37 ([CT] C29)
RUNTIME_DIR_NAME = "mpv-runtime"   # a hyphen: never importable as a package
WINDOWS_DLL_TARGET = "mpv-2.dll"   # python-mpv tries this name first
WINDOWS_DLL_NAMES = (WINDOWS_DLL_TARGET, "libmpv-2.dll")
LINUX_SONAMES = ("libmpv.so.2", "libmpv.so.1", "libmpv.so")
VULKAN_DIR_NAME = "vulkan-fallback"
VULKAN_DLL = "vulkan-1.dll"
PYTHON_MPV_REQUIREMENT = "mpv>=1.0.6,<2"
PROBE_TIMEOUT_S = 20.0
# The folder that contains the videotranslator package: the working directory
# of `python -m videotranslator...` children (the desktop shortcut may start
# the GUI from anywhere).
PACKAGE_ROOT = Path(__file__).resolve().parents[1]

REASONS: tuple[str, ...] = (
    "ok", "python-mpv-missing", "libmpv-missing", "libmpv-too-old",
    "libmpv-load-failed", "vulkan-loader-missing", "probe-crashed", "restart-required",
)
# The library itself loads in these states (python-mpv is judged separately).
LIBRARY_OK_REASONS = frozenset({"ok", "python-mpv-missing"})
REASON_KEYS: dict[str, str] = {
    "ok": "player_badge_ok",
    "python-mpv-missing": "player_missing_pymod",
    "libmpv-missing": "player_missing_libmpv_linux",
    "libmpv-too-old": "player_libmpv_too_old",
    "libmpv-load-failed": "player_libmpv_load_failed",
    "vulkan-loader-missing": "player_vulkan_missing",
    "probe-crashed": "player_probe_crashed",
    "restart-required": "player_restart_required",
}
REASON_KEYS_WIN32: dict[str, str] = {**REASON_KEYS, "libmpv-missing": "player_missing_libmpv_win"}
_ERROR_REASONS = frozenset({"libmpv-too-old", "libmpv-load-failed", "probe-crashed"})
_INSTALLABLE_REASONS = frozenset({"python-mpv-missing", "libmpv-missing"})

# Video-output profiles, in fallback order, with libmpv option names (dashes).
# P2's player_engine derives VO_PROFILES from this table. x11glx is absent on
# purpose: gpu-context=x11 is rejected by the Kali 0.41 build ([CT] R1).
VO_PROFILE_OPTIONS: dict[str, dict[str, dict[str, str]]] = {
    "linux": {
        "x11egl": {"vo": "gpu", "gpu-context": "x11egl"},
        "x11vk": {"vo": "gpu", "gpu-api": "vulkan", "gpu-context": "x11vk"},
        "x11sw": {"vo": "x11"},
    },
    "win32": {
        "auto": {"vo": "gpu"},
        "d3d11-warp": {"vo": "gpu", "gpu-api": "d3d11", "d3d11-warp": "yes"},
    },
}
_VERSION_PROBE_OPTIONS = (
    ("vo", "null"), ("ao", "null"), ("idle", "yes"), ("load-scripts", "no"),
    ("ytdl", "no"), ("config", "no"), ("terminal", "no"),
)

# Handles returned by os.add_dll_directory must stay referenced for the whole
# process: closing one drops the directory while libmpv may still resolve
# imports from it ([CT] C9).
_DLL_DIR_HANDLES: list[Any] = []
_MPV_MODULE: ModuleType | None = None
_MPV_LOCK = threading.Lock()


@dataclass(frozen=True)
class LibmpvStatus:
    ok: bool
    reason: str
    api_version: tuple[int, int] | None = None
    mpv_version: tuple[int, int] | None = None
    path: str | None = None
    vo_profiles_ok: tuple[str, ...] = ()
    detail: str = ""
    build: Mapping[str, str] = field(default_factory=dict)
    fingerprint: str | None = None


def _status(reason: str, **fields: Any) -> LibmpvStatus:
    return LibmpvStatus(ok=reason == "ok", reason=reason, **fields)


class PlayerUnavailable(Exception):
    """Raised by load_mpv; ``status`` says why."""

    def __init__(self, status: LibmpvStatus) -> None:
        super().__init__(f"{status.reason}: {status.detail}")
        self.status = status


# -- UI helpers (pure) ---------------------------------------------------

def library_loaded(status: LibmpvStatus) -> bool:
    return status.reason in LIBRARY_OK_REASONS


def reason_key(reason: str, sys_platform: str) -> str:
    keys = REASON_KEYS_WIN32 if sys_platform == "win32" else REASON_KEYS
    return keys[reason]


def format_version(status: LibmpvStatus) -> str:
    if status.mpv_version:
        return f"{status.mpv_version[0]}.{status.mpv_version[1]}"
    if status.api_version:
        return f"API {status.api_version[0]}.{status.api_version[1]}"
    return "?"


def _shorten(text: str, limit: int = 120) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def status_message(status: LibmpvStatus, *, sys_platform: str,
                   install_cmd: str | None = None) -> tuple[str, dict[str, str]]:
    """Return (UI_STRINGS key, format params) that explain ``status``."""
    params: dict[str, str] = {}
    if status.reason in ("ok", "libmpv-too-old"):
        params["version"] = format_version(status)
    elif status.reason == "libmpv-load-failed":
        params["detail"] = _shorten(status.detail or status.reason)
    elif status.reason == "libmpv-missing" and sys_platform != "win32":
        params["cmd"] = install_cmd or "libmpv2"
    return reason_key(status.reason, sys_platform), params


def badge_level(status: LibmpvStatus) -> str:
    if status.ok:
        return "ok"
    if status.reason in _ERROR_REASONS:
        return "error"
    return "warn"


def offers_install(status: LibmpvStatus, *, sys_platform: str) -> bool:
    """True when an Install action can fix ``status`` (spec 6.1)."""
    if status.reason in _INSTALLABLE_REASONS:
        return True
    return status.reason == "vulkan-loader-missing" and sys_platform == "win32"


def windows_download_mb(*, vulkan: bool) -> int:
    """Download size announced by player_install_confirm (spec 8.3)."""
    return 32 + (18 if vulkan else 0)


# -- paths -----------------------------------------------------------------

def per_user_runtime_dir(env: Mapping[str, str] | None = None) -> Path:
    """%LOCALAPPDATA%\\VideoTranslatorAI\\mpv-runtime (the GUI per-user install, Q6)."""
    return app_data_dir(system="win32", env=dict(env) if env is not None else None) / RUNTIME_DIR_NAME


def windows_candidate_dirs(env: Mapping[str, str], app_dir: Path) -> list[Path]:
    """Folders searched for mpv-2.dll, in order (spec 2.2)."""
    dirs: list[Path] = []
    if env.get("VTAI_LIBMPV_DIR"):
        dirs.append(Path(env["VTAI_LIBMPV_DIR"]))
    dirs.append(Path(app_dir) / RUNTIME_DIR_NAME)
    if env.get("ProgramFiles"):
        dirs.append(Path(env["ProgramFiles"]) / "VideoTranslatorAI" / RUNTIME_DIR_NAME)
    if env.get("LOCALAPPDATA"):
        dirs.append(Path(env["LOCALAPPDATA"]) / "VideoTranslatorAI" / RUNTIME_DIR_NAME)
    unique: list[Path] = []
    seen: set[str] = set()
    for directory in dirs:
        key = os.path.normcase(str(directory))
        if key not in seen:
            seen.add(key)
            unique.append(directory)
    return unique


def find_vulkan_fallback(runtime_dir: Path | None, env: Mapping[str, str]) -> Path | None:
    """The folder holding our vulkan-1.dll copy: next to the DLL, then per user."""
    candidates = []
    if runtime_dir is not None:
        candidates.append(Path(runtime_dir) / VULKAN_DIR_NAME)
    candidates.append(per_user_runtime_dir(env) / VULKAN_DIR_NAME)
    for candidate in candidates:
        if (candidate / VULKAN_DLL).is_file():
            return candidate
    return None


def default_system32(env: Mapping[str, str]) -> Path:
    root = env.get("SystemRoot") or env.get("SYSTEMROOT") or "C:\\Windows"
    return Path(root) / "System32"


# -- parsing ---------------------------------------------------------------

def parse_api_version(raw: int) -> tuple[int, int]:
    raw = int(raw)
    return raw >> 16, raw & 0xFFFF


_MPV_VERSION_RE = re.compile(r"\bmpv\s+v?(\d+)\.(\d+)")


def parse_mpv_version(text: str) -> tuple[int, int] | None:
    """"mpv 0.41.0" or "mpv v0.41.0-1050-ge76a35ec9" -> (0, 41)."""
    match = _MPV_VERSION_RE.search(text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


_LDCONFIG_RE = re.compile(r"^\s*(?P<name>\S+)\s+\((?P<flags>[^)]*)\)\s+=>\s+(?P<path>\S.*?)\s*$")


def parse_ldconfig(output: str, soname_prefix: str = "libmpv.so", *,
                   want_64bit: bool = sys.maxsize > 2**32) -> str | None:
    """Path of the newest ``soname_prefix`` entry for this architecture in ``ldconfig -p``."""
    best: tuple[tuple[int, ...], str] | None = None
    for line in (output or "").splitlines():
        match = _LDCONFIG_RE.match(line)
        if not match:
            continue
        name = match.group("name")
        if name != soname_prefix and not name.startswith(soname_prefix + "."):
            continue
        if ("64" in match.group("flags")) != want_64bit:
            continue
        version = tuple(int(part) for part in name[len(soname_prefix):].split(".") if part.isdigit())
        if best is None or version > best[0]:
            best = (version, match.group("path"))
    return best[1] if best else None


def parse_maps(text: str, marker: str = "libmpv.so") -> str | None:
    """Path of the mapped library from /proc/self/maps text."""
    for line in (text or "").splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and marker in os.path.basename(parts[5].strip()):
            return parts[5].strip()
    return None


def library_fingerprint(path: str | None) -> str | None:
    """"<realpath>|<size>|<mtime_ns>": an apt upgrade or a new DLL changes it."""
    if not path:
        return None
    try:
        real = os.path.realpath(path)
        stat = os.stat(real)
    except (OSError, TypeError, ValueError):
        return None
    return f"{real}|{stat.st_size}|{stat.st_mtime_ns}"


def read_build_txt(directory: Path) -> dict[str, str]:
    """BUILD.txt written by install_windows (key=value lines), {} when absent."""
    try:
        text = (Path(directory) / "BUILD.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    return fields


def read_ldconfig_cache(*, run: Callable[..., Any] = subprocess.run,
                        which: Callable[[str], str | None] = shutil.which) -> str:
    """Output of ``ldconfig -p`` (it lives in /sbin, often off a user's PATH)."""
    for exe in (which("ldconfig"), "/sbin/ldconfig", "/usr/sbin/ldconfig"):
        if not exe or not os.path.isfile(exe):
            continue
        try:
            proc = run([exe, "-p"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=10, check=False, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            continue
        return proc.stdout or ""
    return ""


def _read_self_maps() -> str:
    try:
        return Path("/proc/self/maps").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def classify_import_error(exc: BaseException, *, sys_platform: str, vulkan_present: bool) -> str:
    """Map a load or ``import mpv`` failure to a LibmpvStatus reason (spec 6.1)."""
    if isinstance(exc, ImportError):
        return "python-mpv-missing"
    if isinstance(exc, OSError):
        if "Cannot find" in str(exc):   # python-mpv's own "not found" messages
            return "libmpv-missing"
        if sys_platform == "win32":
            code = getattr(exc, "winerror", None) or getattr(exc.__cause__, "winerror", None)
            if code == 126 and not vulkan_present:
                return "vulkan-loader-missing"
        return "libmpv-load-failed"
    if isinstance(exc, AttributeError):
        return "libmpv-too-old"
    if isinstance(exc, RuntimeError) and "API version" in str(exc):
        return "libmpv-too-old"
    return "libmpv-load-failed"


def _module_present(name: str, find_spec: Callable[[str], Any]) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _locate_library(*, sys_platform: str, env: Mapping[str, str], app_dir: Path,
                    runtime_dir: Path | None, find_library: Callable[[str], str | None],
                    run_ldconfig: Callable[[], str],
                    isfile: Callable[[str], bool]) -> tuple[str | None, dict[str, str]]:
    """(library path or soname, BUILD.txt fields) without loading anything."""
    if sys_platform == "win32":
        dirs = [Path(runtime_dir)] if runtime_dir is not None else windows_candidate_dirs(env, app_dir)
        for directory in dirs:
            for name in WINDOWS_DLL_NAMES:
                candidate = directory / name
                if isfile(str(candidate)):
                    return str(candidate), read_build_txt(directory)
        return None, {}
    if runtime_dir is not None:
        dirs = [Path(runtime_dir)]
    elif env.get("VTAI_LIBMPV_DIR"):
        dirs = [Path(env["VTAI_LIBMPV_DIR"])]   # dev override (plan decision 5)
    else:
        dirs = []
    for directory in dirs:
        for name in LINUX_SONAMES:
            candidate = directory / name
            if isfile(str(candidate)):
                return str(candidate), {}
    if runtime_dir is not None:
        return None, {}
    path = parse_ldconfig(run_ldconfig())
    if path:
        return path, {}
    return find_library("mpv"), {}


# -- detection -------------------------------------------------------------

def quick_presence(*, sys_platform: str = sys.platform, env: Mapping[str, str] | None = None,
                   app_dir: Path | None = None,
                   find_library: Callable[[str], str | None] = ctypes.util.find_library,
                   run_ldconfig: Callable[[], str] = read_ldconfig_cache,
                   find_spec: Callable[[str], Any] = importlib.util.find_spec,
                   isfile: Callable[[str], bool] = os.path.isfile) -> LibmpvStatus:
    """Startup status without loading libmpv: the library first, then python-mpv."""
    env = os.environ if env is None else env
    app_dir = PACKAGE_ROOT if app_dir is None else Path(app_dir)
    path, build = _locate_library(sys_platform=sys_platform, env=env, app_dir=app_dir,
                                  runtime_dir=None, find_library=find_library,
                                  run_ldconfig=run_ldconfig, isfile=isfile)
    if path is None:
        if sys_platform == "win32":
            where = ", ".join(str(d) for d in windows_candidate_dirs(env, app_dir))
            return _status("libmpv-missing", detail=f"no {WINDOWS_DLL_TARGET} in {where}")
        return _status("libmpv-missing", detail="no libmpv.so in ldconfig -p")
    fingerprint = library_fingerprint(path)
    if not _module_present("mpv", find_spec):
        return _status("python-mpv-missing", path=path, build=build, fingerprint=fingerprint,
                       detail="python-mpv (module mpv) is not importable")
    return _status("ok", path=path, build=build, fingerprint=fingerprint,
                   detail="library found (not loaded)")


def _declare_prototypes(lib: Any) -> None:
    lib.mpv_client_api_version.restype = ctypes.c_ulong
    lib.mpv_create.restype = ctypes.c_void_p
    lib.mpv_set_option_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.mpv_set_option_string.restype = ctypes.c_int
    lib.mpv_initialize.argtypes = [ctypes.c_void_p]
    lib.mpv_initialize.restype = ctypes.c_int
    lib.mpv_get_property_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.mpv_get_property_string.restype = ctypes.c_void_p
    lib.mpv_free.argtypes = [ctypes.c_void_p]
    lib.mpv_free.restype = None
    lib.mpv_terminate_destroy.argtypes = [ctypes.c_void_p]
    lib.mpv_terminate_destroy.restype = None


def _vo_profiles_for(sys_platform: str) -> dict[str, dict[str, str]]:
    return VO_PROFILE_OPTIONS["win32" if sys_platform == "win32" else "linux"]


def _accepted_vo_profiles(lib: Any, sys_platform: str) -> tuple[str, ...]:
    """Profiles whose options this build accepts, each on a fresh uninitialised handle.

    An invalid choice fails at option-set time, so the in-process MPV() of P2
    never gets an option that leaks a half-created core ([CT] finding 2).
    """
    accepted = []
    for name, options in _vo_profiles_for(sys_platform).items():
        handle = lib.mpv_create()
        if not handle:
            continue
        try:
            ok = all(lib.mpv_set_option_string(handle, key.encode(), value.encode()) >= 0
                     for key, value in options.items())
        finally:
            lib.mpv_terminate_destroy(handle)
        if ok:
            accepted.append(name)
    return tuple(accepted)


def _read_mpv_version(lib: Any) -> str | None:
    """The `mpv-version` property of a headless, initialised handle (C54)."""
    handle = lib.mpv_create()
    if not handle:
        return None
    try:
        for key, value in _VERSION_PROBE_OPTIONS:
            lib.mpv_set_option_string(handle, key.encode(), value.encode())
        if lib.mpv_initialize(handle) < 0:
            return None
        pointer = lib.mpv_get_property_string(handle, b"mpv-version")
        if not pointer:
            return None
        try:
            return ctypes.string_at(pointer).decode("utf-8", "replace")
        finally:
            lib.mpv_free(pointer)
    finally:
        lib.mpv_terminate_destroy(handle)


def probe_libmpv(*, sys_platform: str = sys.platform, env: Mapping[str, str] | None = None,
                 app_dir: Path | None = None, runtime_dir: Path | None = None,
                 find_library: Callable[[str], str | None] = ctypes.util.find_library,
                 cdll: Callable[[str], Any] = ctypes.CDLL,
                 run_ldconfig: Callable[[], str] = read_ldconfig_cache,
                 read_maps: Callable[[], str] | None = None,
                 isfile: Callable[[str], bool] = os.path.isfile,
                 add_dll_directory: Callable[[str], Any] | None = None,
                 system32: Path | None = None) -> LibmpvStatus:
    """Load libmpv and report what it is. ONLY for the `check` subprocess.

    The python-mpv verdict is not part of this result: ``main`` adds it for
    the CLI, and resolve_status takes it from the calling process.
    """
    env = os.environ if env is None else env
    app_dir = PACKAGE_ROOT if app_dir is None else Path(app_dir)
    path, build = _locate_library(sys_platform=sys_platform, env=env, app_dir=app_dir,
                                  runtime_dir=runtime_dir, find_library=find_library,
                                  run_ldconfig=run_ldconfig, isfile=isfile)
    if path is None:
        return _status("libmpv-missing", detail="library not found")
    vulkan_present = True
    if sys_platform == "win32":
        vulkan_present = ((system32 or default_system32(env)) / VULKAN_DLL).is_file()
        if not vulkan_present:
            fallback = find_vulkan_fallback(Path(path).parent, env)
            adder = add_dll_directory or getattr(os, "add_dll_directory", None)
            if fallback is not None and adder is not None:
                _DLL_DIR_HANDLES.append(adder(str(fallback)))
                vulkan_present = True
    try:
        lib = cdll(path)
    except OSError as exc:
        reason = classify_import_error(exc, sys_platform=sys_platform, vulkan_present=vulkan_present)
        return _status(reason, path=path, build=build, detail=f"{type(exc).__name__}: {exc}")
    try:
        _declare_prototypes(lib)
        api = parse_api_version(lib.mpv_client_api_version())
    except AttributeError as exc:
        return _status("libmpv-too-old", path=path, build=build, detail=f"missing symbol: {exc}")
    real_path = path
    if sys_platform != "win32":
        real_path = parse_maps((read_maps or _read_self_maps)()) or path
    fingerprint = library_fingerprint(real_path)
    if api < MIN_API:
        return _status("libmpv-too-old", api_version=api, path=real_path, build=build,
                       fingerprint=fingerprint,
                       detail=f"client API {api[0]}.{api[1]} is older than "
                              f"{MIN_API[0]}.{MIN_API[1]}")
    profiles = _accepted_vo_profiles(lib, sys_platform)
    version_text = _read_mpv_version(lib)
    mpv_version = parse_mpv_version(version_text or "")
    detail = f"{version_text or 'mpv version unknown'}, client API {api[0]}.{api[1]}"
    if mpv_version is not None and mpv_version < TESTED_FLOOR:
        return _status("libmpv-too-old", api_version=api, mpv_version=mpv_version,
                       path=real_path, build=build, fingerprint=fingerprint, detail=detail)
    return _status("ok", api_version=api, mpv_version=mpv_version, path=real_path,
                   vo_profiles_ok=profiles, detail=detail, build=build, fingerprint=fingerprint)


# -- the check subprocess --------------------------------------------------

def status_to_json(status: LibmpvStatus) -> str:
    data = dataclasses.asdict(status)
    data["build"] = dict(status.build)
    return json.dumps(data, ensure_ascii=True, sort_keys=True)


def _pair(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    first, second = value
    return int(first), int(second)


def status_from_json(text: str) -> LibmpvStatus | None:
    """The status printed by `check --json` (last JSON line), None when absent or invalid."""
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            reason = str(data["reason"])
            if reason not in REASONS:
                return None
            return LibmpvStatus(
                ok=bool(data["ok"]) and reason == "ok", reason=reason,
                api_version=_pair(data.get("api_version")),
                mpv_version=_pair(data.get("mpv_version")),
                path=data.get("path"),
                vo_profiles_ok=tuple(str(item) for item in data.get("vo_profiles_ok") or ()),
                detail=str(data.get("detail", "")),
                build={str(k): str(v) for k, v in (data.get("build") or {}).items()},
                fingerprint=data.get("fingerprint"))
        except (KeyError, TypeError, ValueError):
            return None
    return None


def probe_in_subprocess(*, run: Callable[..., Any] = subprocess.run, python: str = sys.executable,
                        timeout: float = PROBE_TIMEOUT_S, runtime_dir: Path | None = None,
                        cwd: Path = PACKAGE_ROOT, sys_platform: str = sys.platform) -> LibmpvStatus:
    """Run `check --json` in a child: a crash or a hang becomes `probe-crashed`."""
    cmd = [python, "-m", "videotranslator.libmpv_runtime", "check", "--json"]
    if runtime_dir is not None:
        cmd += ["--dir", str(runtime_dir)]
    try:
        proc = run(cmd, cwd=str(cwd), capture_output=True, stdin=subprocess.DEVNULL, text=True,
                   encoding="utf-8", errors="replace", timeout=timeout, check=False,
                   **no_window_kwargs(sys_platform))
    except subprocess.TimeoutExpired:
        return _status("probe-crashed", detail=f"libmpv probe timed out after {timeout:.0f} s")
    except OSError as exc:
        return _status("probe-crashed", detail=f"libmpv probe could not start: {exc}")
    status = status_from_json(proc.stdout)
    if status is None or proc.returncode not in (0, 2):
        tail = (proc.stderr or "").strip().splitlines()[-1:]
        detail = f"libmpv probe exit code {proc.returncode}"
        if tail:
            detail += f": {_shorten(tail[0])}"
        return _status("probe-crashed", detail=detail)
    return status


# -- probe cache (config key player_probe, written by the GUI) -------------

def cache_entry(status: LibmpvStatus) -> dict[str, Any] | None:
    """What the GUI stores under `player_probe` (spec 2.5); None when not cacheable."""
    if not library_loaded(status) or status.api_version is None or not status.fingerprint:
        return None
    return {
        "fingerprint": status.fingerprint,
        "ok": True,
        "api": list(status.api_version),
        "mpv_version": list(status.mpv_version) if status.mpv_version else None,
        "vo_profiles_ok": list(status.vo_profiles_ok),
    }


def status_from_cache(quick: LibmpvStatus, cached: Any) -> LibmpvStatus | None:
    """``quick`` completed with a cached probe of the same library file, else None."""
    if not isinstance(cached, Mapping) or cached.get("ok") is not True:
        return None
    if not quick.fingerprint or cached.get("fingerprint") != quick.fingerprint:
        return None
    try:
        api = tuple(int(part) for part in cached["api"])
        raw_version = cached.get("mpv_version")
        mpv_version = tuple(int(part) for part in raw_version) if raw_version else None
        profiles = tuple(str(name) for name in cached.get("vo_profiles_ok") or ())
    except (KeyError, TypeError, ValueError):
        return None
    if len(api) != 2 or (mpv_version is not None and len(mpv_version) != 2):
        return None
    return dataclasses.replace(quick, api_version=api, mpv_version=mpv_version,
                               vo_profiles_ok=profiles, detail="cached probe result")


def resolve_status(*, cached: Any = None, force_probe: bool = False,
                   quick: Callable[[], LibmpvStatus] | None = None,
                   probe: Callable[[], LibmpvStatus] | None = None) -> LibmpvStatus:
    """Worker-thread status for the GUI (plan decision 2). Never loads libmpv here."""
    quick_status = (quick or quick_presence)()
    if not library_loaded(quick_status):
        return quick_status
    if not force_probe:
        hit = status_from_cache(quick_status, cached)
        if hit is not None:
            return hit
    probed = (probe or probe_in_subprocess)()
    if not library_loaded(probed):
        return probed
    # Library facts from the child, python-mpv verdict from this process (a
    # user site created during this run is importable in a fresh child only).
    return dataclasses.replace(probed, ok=quick_status.ok, reason=quick_status.reason,
                               fingerprint=quick_status.fingerprint or probed.fingerprint,
                               build=quick_status.build or probed.build)


# -- import gate (P2 calls load_mpv on its player-init thread) -------------

def prepare_import(env: MutableMapping[str, str], *, sys_platform: str,
                   runtime_dir: Path | None, add_dll_directory: Callable[[str], Any] | None,
                   system32_has_vulkan: bool) -> Callable[[], None]:
    """Windows: PREPEND ``runtime_dir`` to PATH for the import; return a restore callable.

    Prepending (not narrowing) keeps ffmpeg visible to a job that starts at
    the same instant (spec 2.2). The Vulkan fallback dir is added through
    add_dll_directory only when System32 lacks the loader, and its handle is
    kept for the process lifetime. Linux: no-op.
    """
    if sys_platform != "win32" or runtime_dir is None:
        return lambda: None
    old = env.get("PATH")
    env["PATH"] = str(runtime_dir) + (";" + old if old else "")
    if not system32_has_vulkan and add_dll_directory is not None:
        fallback = find_vulkan_fallback(Path(runtime_dir), env)
        if fallback is not None:
            _DLL_DIR_HANDLES.append(add_dll_directory(str(fallback)))

    def restore() -> None:
        if old is None:
            env.pop("PATH", None)
        else:
            env["PATH"] = old

    return restore


def load_mpv(*, importer: Callable[[str], ModuleType] = importlib.import_module,
             sys_platform: str = sys.platform, env: MutableMapping[str, str] | None = None,
             app_dir: Path | None = None, add_dll_directory: Callable[[str], Any] | None = None,
             system32: Path | None = None) -> ModuleType:
    """The only `import mpv` of the code base; cached; raises PlayerUnavailable. Off the Tk thread."""
    global _MPV_MODULE
    with _MPV_LOCK:
        if _MPV_MODULE is not None:
            return _MPV_MODULE
        env = os.environ if env is None else env
        runtime_dir = None
        vulkan_ok = True
        if sys_platform == "win32":
            path, _ = _locate_library(sys_platform=sys_platform, env=env,
                                      app_dir=PACKAGE_ROOT if app_dir is None else Path(app_dir),
                                      runtime_dir=None, find_library=lambda name: None,
                                      run_ldconfig=lambda: "", isfile=os.path.isfile)
            runtime_dir = Path(path).parent if path else None
            vulkan_ok = ((system32 or default_system32(env)) / VULKAN_DLL).is_file()
        restore = prepare_import(env, sys_platform=sys_platform, runtime_dir=runtime_dir,
                                 add_dll_directory=add_dll_directory or getattr(os, "add_dll_directory", None),
                                 system32_has_vulkan=vulkan_ok)
        try:
            module = importer("mpv")
        except Exception as exc:  # python-mpv raises OSError/RuntimeError at import time
            reason = classify_import_error(exc, sys_platform=sys_platform, vulkan_present=vulkan_ok)
            raise PlayerUnavailable(_status(reason, detail=f"{type(exc).__name__}: {exc}")) from exc
        finally:
            restore()
        _MPV_MODULE = module
        return module


# -- Windows installer (spec 8.3; setup_windows.bat and the GUI per-user install) --

USER_AGENT = "VideoTranslatorAI-Setup"   # SourceForge serves HTML to browser-like agents
DOWNLOAD_TIMEOUT_S = 60.0
BUILD_FILE = "BUILD.txt"
STAGING_DIR_NAME = "_staging"
LICENCE_URL = "https://raw.githubusercontent.com/mpv-player/mpv/{ref}/LICENSE.{flavour}"


@dataclass(frozen=True)
class AssetSource:
    kind: str                            # "github-latest" | "pinned"
    name: str
    licence: str
    urls: tuple[str, ...] = ()           # pinned: mirrors in order
    sha256: str | None = None            # pinned: the archive
    member: str = "libmpv-2.dll"
    member_sha256: str | None = None     # pinned: the extracted file
    repo: str | None = None              # github-latest: "owner/name"
    asset_pattern: str | None = None     # github-latest: full-match regex on asset names
    max_releases: int = 3                # github-latest: newest N tried in order
    max_bytes: int = 64 << 20


# Operator decision Q1: the zhongfly LGPL build first (newest 3 daily
# releases, each verified by its GitHub digest), the pinned shinchiro GPL
# snapshot as the reproducible fallback. A licence choice changes this data,
# not the code. Both are mpv master snapshots: BUILD.txt records the commit.
WINDOWS_LIBMPV_SOURCES: tuple[AssetSource, ...] = (
    AssetSource(kind="github-latest", name="zhongfly-lgpl", licence="LGPL",
                repo="zhongfly/mpv-winbuild",
                asset_pattern=r"mpv-dev-lgpl-x86_64-\d{8}-git-[0-9a-f]+\.7z",
                max_releases=3),
    AssetSource(kind="pinned", name="shinchiro-gpl-20260920", licence="GPL",
                urls=("https://downloads.sourceforge.net/project/mpv-player-windows/libmpv/"
                      "mpv-dev-x86_64-20260920-git-e76a35ec95.7z",
                      "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/"
                      "20260920/mpv-dev-x86_64-20260920-git-e76a35ec95.7z"),
                sha256="60f9102db46aea8cef9bfb4345ee6a106f34fdbd1df9587e38f0660688039341",
                member_sha256="63e1fbb4ee890d153a9f5086410157174ee18582846bf35f6cc4e5d08d4bb662"),
)
# py7zr cannot decode the BCJ2 filter of both archives ([06] 2): 7zr.exe does.
SEVENZR = AssetSource(kind="pinned", name="7zr-26.03", licence="LGPL",
                      urls=("https://github.com/ip7z/7zip/releases/download/26.03/7zr.exe",),
                      sha256="ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d",
                      member="7zr.exe", max_bytes=4 << 20)
# Q2: fetched only when the load check reports a missing vulkan-1.dll.
VULKAN_RUNTIME = AssetSource(
    kind="pinned", name="vulkan-runtime-1.4.357.0", licence="MIT and Apache-2.0",
    urls=("https://sdk.lunarg.com/sdk/download/1.4.357.0/windows/vulkan-runtime-components.zip",),
    sha256="a14672efed15aafc7f5a16572d35cd3a3416eadf670aeee3cdf50ee32d5fbf83",
    member="VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll",
    member_sha256="cd862090370454630b31b174e3d4eb474fda38ea034998d1fe1767b0c99a8696")

_SUMS_LINE_RE = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(\S+)\s*$")
_COMMIT_RE = re.compile(r"-git-([0-9a-f]{7,40})\.7z$")


@dataclass(frozen=True)
class DownloadCandidate:
    source: AssetSource
    url: str
    sha256: str
    release: str
    asset: str


class DownloadError(Exception):
    """A download, a checksum or an extraction failed; the next candidate is tried."""


class HttpClient:
    """urllib with the installer's user agent, a timeout and chunked, hashed reads."""

    def __init__(self, *, opener: Callable[..., Any] = urllib.request.urlopen,
                 timeout: float = DOWNLOAD_TIMEOUT_S, chunk: int = 1 << 16) -> None:
        self._opener = opener
        self._timeout = timeout
        self._chunk = chunk

    def _open(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        return self._opener(request, timeout=self._timeout)

    def get_json(self, url: str) -> Any:
        with self._open(url) as response:
            return json.loads(response.read(4 << 20).decode("utf-8"))

    def get_text(self, url: str) -> str:
        with self._open(url) as response:
            return response.read(1 << 20).decode("utf-8", "replace")

    def resolve(self, url: str) -> str:
        """The final URL after redirects (GitHub /releases/latest -> /releases/tag/<tag>)."""
        with self._open(url) as response:
            return response.geturl()

    def fetch(self, url: str, dest: Path, *, max_bytes: int) -> str:
        """Stream ``url`` into ``dest``; return its SHA256 hex digest."""
        digest = hashlib.sha256()
        size = 0
        with self._open(url) as response:
            headers = getattr(response, "headers", None) or {}
            if str(headers.get("Content-Type", "")).lower().startswith("text/html"):
                raise DownloadError(f"{url} returned an HTML page instead of a file")
            with open(dest, "wb") as out:
                while True:
                    block = response.read(self._chunk)
                    if not block:
                        break
                    size += len(block)
                    if size > max_bytes:
                        raise DownloadError(f"{url} is larger than {max_bytes} bytes")
                    digest.update(block)
                    out.write(block)
        return digest.hexdigest()


def pinned_candidates(source: AssetSource) -> list[DownloadCandidate]:
    if not source.sha256:
        return []   # never install an unverified pinned file
    return [DownloadCandidate(source, url, source.sha256.lower(), source.name,
                              url.rstrip("/").rsplit("/", 1)[-1]) for url in source.urls]


def _release_sums(http: Any, repo: str, tag: str) -> dict[str, str]:
    text = http.get_text(f"https://github.com/{repo}/releases/download/{tag}/sha256.txt")
    sums: dict[str, str] = {}
    for line in text.splitlines():
        match = _SUMS_LINE_RE.match(line.strip())
        if match:
            sums[match.group(2)] = match.group(1).lower()
    return sums


_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _valid_sha256(value: Any) -> str | None:
    """A lower-case 64-hex SHA256, or None (a bad digest would waste a download)."""
    text = str(value or "").strip().lower()
    return text if _SHA256_RE.fullmatch(text) else None


def github_candidates(source: AssetSource, http: Any,
                      log: Callable[[str], None]) -> list[DownloadCandidate]:
    """Newest-first candidates of a github-latest source, each with a SHA256 to verify.

    Primary: the releases API and each asset's `digest`. When the API fails
    (60 requests per hour per IP): the /releases/latest redirect and that
    release's sha256.txt. An asset without a checksum is skipped. The digest
    comes from the same origin as the file: it guards against transport
    errors, not against a compromised upstream (spec 8.3, C46).
    """
    pattern = re.compile(source.asset_pattern or r"(?!)")
    base = f"https://github.com/{source.repo}/releases/download"
    try:
        releases = http.get_json(
            f"https://api.github.com/repos/{source.repo}/releases?per_page={source.max_releases}")
    except (OSError, ValueError) as exc:
        log(f"[!] GitHub API unavailable for {source.repo} ({exc}): using the latest release page")
        releases = None
    candidates: list[DownloadCandidate] = []
    if isinstance(releases, list):
        for release in releases[: source.max_releases]:
            if not isinstance(release, dict):
                continue  # malformed API entry: never crash before the fallback source
            tag = str(release.get("tag_name", ""))
            assets = release.get("assets")
            for asset in assets if isinstance(assets, list) else []:
                if not isinstance(asset, dict):
                    continue
                name = str(asset.get("name", ""))
                if not pattern.fullmatch(name):
                    continue
                digest = str(asset.get("digest") or "")
                sha = _valid_sha256(digest.split(":", 1)[1]) if digest.startswith("sha256:") else None
                if sha is None:
                    try:
                        sha = _valid_sha256(_release_sums(http, source.repo, tag).get(name))
                    except (OSError, ValueError, AttributeError):
                        sha = None
                if not sha:
                    log(f"[!] {name}: no published checksum, skipped")
                    continue
                url = str(asset.get("browser_download_url") or f"{base}/{tag}/{name}")
                candidates.append(DownloadCandidate(source, url, sha, tag, name))
        return candidates
    try:
        tag = http.resolve(f"https://github.com/{source.repo}/releases/latest").rstrip("/").rsplit("/", 1)[-1]
        sums = _release_sums(http, source.repo, tag)
    except (OSError, ValueError) as exc:
        log(f"[!] Cannot resolve the latest {source.repo} release: {exc}")
        return []
    for name, sha in sorted(sums.items()):
        if pattern.fullmatch(name):
            candidates.append(DownloadCandidate(source, f"{base}/{tag}/{name}", sha, tag, name))
    return candidates


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_hidden(cmd: Sequence[str], *, timeout_s: float = 300.0,
               run: Callable[..., Any] = subprocess.run, sys_platform: str = sys.platform) -> int:
    """Run a console tool (7zr.exe) with no window and no stdin; its exit code, -1 on failure."""
    try:
        proc = run([str(part) for part in cmd], capture_output=True, stdin=subprocess.DEVNULL,
                   timeout=timeout_s, check=False, **no_window_kwargs(sys_platform))
    except (OSError, subprocess.SubprocessError):
        return -1
    return int(proc.returncode)


def _fetch_verified(http: Any, url: str, target: Path, sha256: str, max_bytes: int) -> None:
    """Download to ``target.part``, check the hash, then rename; never leaves a .part behind."""
    part = target.with_name(target.name + ".part")
    try:
        got = http.fetch(url, part, max_bytes=max_bytes)
        if got.lower() != sha256.lower():
            raise DownloadError(f"SHA256 mismatch for {url}")
        os.replace(part, target)
    finally:
        with contextlib.suppress(OSError):
            part.unlink()


def _fetch_pinned(source: AssetSource, target: Path, http: Any, log: Callable[[str], None]) -> Path:
    errors = []
    for url in source.urls:
        try:
            _fetch_verified(http, url, target, source.sha256 or "", source.max_bytes)
            return target
        except (OSError, ValueError, DownloadError) as exc:
            log(f"[!] {source.name}: {url} failed: {exc}")
            errors.append(str(exc))
    raise DownloadError(f"{source.name}: " + "; ".join(errors or ["no URL"]))


def _extract_member(tool: Path, archive: Path, member: str, work: Path,
                    runner: Callable[[Sequence[str]], int]) -> Path:
    code = runner([str(tool), "e", "-y", f"-o{work}", str(archive), member])
    out = work / Path(member).name
    if code != 0 or not out.is_file() or out.stat().st_size == 0:
        with contextlib.suppress(OSError):
            out.unlink()   # a failed extraction can leave a 0-byte file ([06] 2)
        raise DownloadError(f"7zr could not extract {member} (exit code {code})")
    return out


def _fetch_vulkan(vulkan: AssetSource, target_dir: Path, work: Path, http: Any,
                  log: Callable[[str], None]) -> None:
    archive = _fetch_pinned(vulkan, work / "vulkan-runtime.zip", http, log)
    target_dir.mkdir(parents=True, exist_ok=True)
    part = target_dir / (VULKAN_DLL + ".part")
    try:
        with zipfile.ZipFile(archive) as bundle, bundle.open(vulkan.member) as src, \
                open(part, "wb") as dst:
            shutil.copyfileobj(src, dst)
        if vulkan.member_sha256 and sha256_file(part) != vulkan.member_sha256:
            raise DownloadError("vulkan-1.dll SHA256 mismatch")
        os.replace(part, target_dir / VULKAN_DLL)
    except (KeyError, zipfile.BadZipFile) as exc:
        raise DownloadError(f"Vulkan runtime archive: {exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            part.unlink()
        with contextlib.suppress(OSError):
            archive.unlink()


def _seed_vulkan(dest: Path, work: Path, vulkan: AssetSource) -> None:
    """Reuse a verified vulkan-1.dll of a previous install instead of downloading it again."""
    existing = dest / VULKAN_DIR_NAME / VULKAN_DLL
    if not existing.is_file():
        return
    if vulkan.member_sha256 and sha256_file(existing) != vulkan.member_sha256:
        return
    (work / VULKAN_DIR_NAME).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(existing, work / VULKAN_DIR_NAME / VULKAN_DLL)


def _clean_work(work: Path, keep: set[str]) -> None:
    for entry in work.iterdir():
        if entry.name in keep:
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            with contextlib.suppress(OSError):
                entry.unlink()


def _try_candidate(cand: DownloadCandidate, work: Path, tool: Path, http: Any,
                   runner: Callable[[Sequence[str]], int], check: Callable[[Path], LibmpvStatus],
                   vulkan: AssetSource, dest: Path, log: Callable[[str], None]) -> LibmpvStatus:
    archive = work / cand.asset
    _fetch_verified(http, cand.url, archive, cand.sha256, cand.source.max_bytes)
    try:
        dll = _extract_member(tool, archive, cand.source.member, work, runner)
    finally:
        with contextlib.suppress(OSError):
            archive.unlink()
    with open(dll, "rb") as handle:
        if handle.read(2) != b"MZ":
            raise DownloadError(f"{cand.source.member} is not a Windows DLL")
    if cand.source.member_sha256 and sha256_file(dll) != cand.source.member_sha256:
        raise DownloadError(f"{cand.source.member} SHA256 mismatch")
    os.replace(dll, work / WINDOWS_DLL_TARGET)
    _seed_vulkan(dest, work, vulkan)
    # The load check runs in a child process: a crashing DLL cannot kill the installer.
    status = check(work)
    if status.reason == "vulkan-loader-missing" and not (work / VULKAN_DIR_NAME / VULKAN_DLL).is_file():
        log("[*] vulkan-1.dll is missing on this system: downloading the Vulkan runtime ...")
        _fetch_vulkan(vulkan, work / VULKAN_DIR_NAME, work, http, log)
        status = check(work)
    return status


def _promote(work: Path, dest: Path) -> bool:
    """Move the checked files from the staging folder (same volume) into ``dest``."""
    vulkan_src = work / VULKAN_DIR_NAME / VULKAN_DLL
    if vulkan_src.is_file():
        (dest / VULKAN_DIR_NAME).mkdir(parents=True, exist_ok=True)
        os.replace(vulkan_src, dest / VULKAN_DIR_NAME / VULKAN_DLL)
    os.replace(work / WINDOWS_DLL_TARGET, dest / WINDOWS_DLL_TARGET)
    return (dest / VULKAN_DIR_NAME / VULKAN_DLL).is_file()


def write_build_txt(dest: Path, cand: DownloadCandidate, status: LibmpvStatus, *,
                    vulkan_fallback: bool, now: datetime) -> None:
    """Record what this user received (source, flavour, mpv commit, hashes) next to the DLL."""
    match = _COMMIT_RE.search(cand.asset)
    lines = [
        "# Written by: python -m videotranslator.libmpv_runtime install",
        f"source={cand.source.name}",
        f"licence={cand.source.licence}",
        f"url={cand.url}",
        f"release={cand.release}",
        f"archive={cand.asset}",
        f"archive_sha256={cand.sha256}",
        f"dll_sha256={sha256_file(dest / WINDOWS_DLL_TARGET)}",
        f"mpv_commit={match.group(1) if match else 'unknown'}",
        f"mpv_version={format_version(status)}",
        f"vulkan_fallback={'yes' if vulkan_fallback else 'no'}",
        f"installed={now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ]
    part = dest / (BUILD_FILE + ".part")
    part.write_text("\n".join(lines) + "\n", encoding="ascii", errors="replace")
    os.replace(part, dest / BUILD_FILE)


def _fetch_licence(dest: Path, cand: DownloadCandidate, http: Any, log: Callable[[str], None]) -> None:
    flavour = "LGPL" if cand.source.licence.upper().startswith("LGPL") else "GPL"
    match = _COMMIT_RE.search(cand.asset)
    for ref in ([match.group(1)] if match else []) + ["master"]:
        try:
            text = http.get_text(LICENCE_URL.format(ref=ref, flavour=flavour))
        except (OSError, ValueError):
            continue
        if text.strip():
            (dest / f"LICENSE.{flavour}").write_text(text, encoding="utf-8")
            return
    log(f"[!] Could not fetch LICENSE.{flavour}; see "
        "https://github.com/mpv-player/mpv/blob/master/Copyright")


def installed_build_is_current(dest: Path, sources: Sequence[AssetSource]) -> bool:
    """True when BUILD.txt names a listed source and the DLL hash matches (Repair skips the download)."""
    build = read_build_txt(dest)
    dll = Path(dest) / WINDOWS_DLL_TARGET
    if not build or not dll.is_file():
        return False
    if build.get("source") not in {source.name for source in sources}:
        return False
    return sha256_file(dll) == build.get("dll_sha256", "").lower()


def _repair_vulkan(dest: Path, vulkan: AssetSource, http: Any,
                   check: Callable[[Path], LibmpvStatus],
                   log: Callable[[str], None]) -> LibmpvStatus:
    """Load-check a current install; fetch the Vulkan fallback if the loader went missing.

    A machine can lose System32\\vulkan-1.dll after the install (driver change,
    moved to a VM without 3D): Repair must then restore the fallback instead of
    reporting vulkan-loader-missing forever (spec 6.1 row 5).
    """
    existing = dest / VULKAN_DIR_NAME / VULKAN_DLL
    if (existing.is_file() and vulkan.member_sha256
            and sha256_file(existing) != vulkan.member_sha256):
        log("[!] The Vulkan fallback in the runtime folder is damaged: replacing it.")
        with contextlib.suppress(OSError):
            existing.unlink()
    status = check(dest)
    if status.reason != "vulkan-loader-missing" or existing.is_file():
        return status
    log("[*] vulkan-1.dll is missing on this system: downloading the Vulkan runtime ...")
    work = dest / STAGING_DIR_NAME
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        _fetch_vulkan(vulkan, dest / VULKAN_DIR_NAME, work, http, log)
    except (OSError, ValueError, DownloadError) as exc:
        log(f"[!] Vulkan runtime: {exc}")
        return status
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return check(dest)


def install_windows(dest: Path, *, sources: Sequence[AssetSource] = WINDOWS_LIBMPV_SOURCES,
                    sevenzr: AssetSource = SEVENZR, vulkan: AssetSource = VULKAN_RUNTIME,
                    downloader: Any = None, runner: Callable[[Sequence[str]], int] | None = None,
                    probe: Callable[[Path], LibmpvStatus] | None = None,
                    log: Callable[[str], None] = print,
                    now: Callable[[], datetime] | None = None) -> LibmpvStatus:
    """Download, verify, extract, load-check and install libmpv into ``dest`` (spec 8.3).

    Every candidate is load-checked in a child process inside a staging
    folder before it replaces anything in ``dest``. Idempotent: a current
    BUILD.txt skips every download. Returns the status of ``dest``.
    """
    http = downloader or HttpClient()
    runner = runner or run_hidden
    check = probe or (lambda directory: probe_in_subprocess(runtime_dir=directory))
    clock = now or (lambda: datetime.now(timezone.utc))
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if installed_build_is_current(dest, sources):
        log(f"[+] libmpv already installed ({read_build_txt(dest).get('source')}), "
            "skipping the download.")
        return _repair_vulkan(dest, vulkan, http, check, log)
    work = dest / STAGING_DIR_NAME
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    failures: list[str] = []
    try:
        try:
            log("[*] Downloading 7zr.exe (7-Zip extractor, used only during the install) ...")
            tool = _fetch_pinned(sevenzr, work / "7zr.exe", http, log)
        except DownloadError as exc:
            return _status("libmpv-missing", detail=f"7zr.exe could not be downloaded: {exc}")
        for source in sources:
            candidates = (github_candidates(source, http, log) if source.kind == "github-latest"
                          else pinned_candidates(source))
            for cand in candidates:
                log(f"[*] Downloading libmpv ({source.name}, {source.licence} build): {cand.asset} ...")
                try:
                    status = _try_candidate(cand, work, tool, http, runner, check, vulkan, dest, log)
                except (OSError, ValueError, DownloadError) as exc:
                    failures.append(f"{cand.asset}: {exc}")
                    log(f"[!] {cand.asset}: {exc}")
                    _clean_work(work, keep={"7zr.exe", VULKAN_DIR_NAME})
                    continue
                if not library_loaded(status):
                    failures.append(f"{cand.asset}: {status.reason} ({status.detail})")
                    log(f"[!] {cand.asset} failed the load check: {status.reason}")
                    _clean_work(work, keep={"7zr.exe", VULKAN_DIR_NAME})
                    continue
                try:
                    vulkan_used = _promote(work, dest)
                except OSError as exc:
                    return _status("libmpv-load-failed", detail=(
                        f"could not replace {WINDOWS_DLL_TARGET} ({exc}): close VideoTranslatorAI "
                        "and run the installer again"))
                write_build_txt(dest, cand, status, vulkan_fallback=vulkan_used, now=clock())
                _fetch_licence(dest, cand, http, log)
                log(f"[+] libmpv installed in {dest}")
                return check(dest)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return _status("libmpv-missing", detail=_shorten(
        "no libmpv build could be installed: " + "; ".join(failures or ["no candidate"]), 500))


# -- command line ----------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m videotranslator.libmpv_runtime",
        description="Probe libmpv for the integrated video player, or install it on Windows.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="load libmpv in this process and report its status")
    check.add_argument("--dir", help="probe the library in this folder only")
    check.add_argument("--json", action="store_true", help="print the status as one JSON line")
    install = sub.add_parser("install", help="Windows: download, verify and install libmpv")
    install.add_argument("--dest", required=True, help="target folder (the mpv-runtime directory)")
    return parser


def _cmd_check(args: argparse.Namespace, *, sys_platform: str) -> int:
    if sys_platform != "win32":
        # libmpv refuses to create a handle under a non-C LC_NUMERIC.
        locale.setlocale(locale.LC_NUMERIC, "C")
    status = probe_libmpv(sys_platform=sys_platform,
                          runtime_dir=Path(args.dir) if args.dir else None)
    if status.ok and not _module_present("mpv", importlib.util.find_spec):
        status = dataclasses.replace(status, ok=False, reason="python-mpv-missing",
                                     detail=status.detail + "; python-mpv (module mpv) is not importable")
    if args.json:
        print(status_to_json(status))
    else:
        print(f"{status.reason}: {status.detail} [{status.path or 'no library'}]")
    return 0 if status.ok else 2


def _cmd_install(args: argparse.Namespace, *, sys_platform: str) -> int:
    if sys_platform != "win32":
        print("[!] install is for Windows only: on Linux install libmpv with the package manager.")
        return 2
    status = install_windows(Path(args.dest))
    if library_loaded(status):
        print(f"[+] libmpv ready: {status.path} ({status.detail})")
        return 0
    print(f"[!] libmpv not installed: {status.reason} ({status.detail})")
    return 2


def main(argv: list[str] | None = None, *, sys_platform: str = sys.platform) -> int:
    """Exit codes: 0 ok, 2 unavailable, 3 unexpected error; never 1."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 3
    try:
        if args.command == "install":
            return _cmd_install(args, sys_platform=sys_platform)
        return _cmd_check(args, sys_platform=sys_platform)
    except Exception:
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
