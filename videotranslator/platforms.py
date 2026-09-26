"""Platform policy and path resolution.

The project is developed on Linux and distributed to Windows users. This module
keeps that contract explicit so the rest of the code can avoid scattered
``sys.platform`` and environment-variable checks.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any


SUPPORTED_PLATFORMS = {"win32", "linux"}
EXPERIMENTAL_PLATFORMS = {"darwin"}

# Sentinel that signals a Wav2Lip asset directory is "complete" (cloned repo
# AND downloaded model). Both must be present; the resolver refuses to claim
# a half-populated directory because callers would still trigger a 416 MB
# re-download or a fresh git clone.
_WAV2LIP_REPO_SENTINEL = ("Wav2Lip", "inference.py")
_WAV2LIP_MODEL_SENTINEL = "wav2lip_gan.pth"


@dataclass(frozen=True)
class PlatformInfo:
    key: str
    name: str
    supported: bool
    experimental: bool = False


@dataclass(frozen=True)
class AppPaths:
    config_dir: PurePath
    data_dir: PurePath
    cache_dir: PurePath
    wav2lip_dir: PurePath
    default_videos_dir: PurePath


@dataclass(frozen=True)
class RuntimeAppPaths:
    config_dir: Path
    data_dir: Path
    cache_dir: Path
    wav2lip_dir: Path
    default_videos_dir: Path


@dataclass(frozen=True)
class Wav2LipPaths:
    """Two-tier path layout for the Wav2Lip lip-sync stage.

    ``asset_dir`` hosts read-only inputs (cloned Wav2Lip repo + 416 MB model
    weights). It may live under a system-wide, possibly read-only location
    populated by the installer (``%ProgramFiles%\\VideoTranslatorAI\\wav2lip``
    on Windows, ``/opt/VideoTranslatorAI/wav2lip`` on Linux).

    ``work_dir`` hosts pipeline scratch space (extracted frames, audio chunks,
    intermediate sync output). It MUST be writable by the unprivileged user
    running the GUI; the resolver therefore always picks a per-user location.
    """

    asset_dir: Path
    work_dir: Path


def platform_info(sys_platform: str) -> PlatformInfo:
    """Return support metadata for a Python ``sys.platform`` value."""
    if sys_platform == "win32":
        return PlatformInfo("win32", "Windows 10/11 x64", supported=True)
    if sys_platform.startswith("linux"):
        return PlatformInfo("linux", "Debian/Ubuntu and derivatives", supported=True)
    if sys_platform == "darwin":
        return PlatformInfo("darwin", "macOS", supported=False, experimental=True)
    return PlatformInfo(sys_platform, sys_platform, supported=False)


def resolve_app_paths(
    sys_platform: str,
    env: dict[str, str],
    home: PurePath,
) -> AppPaths:
    """Resolve pure config/data/cache paths without touching the filesystem.

    ``env`` is injected to make Windows and Linux behavior testable from any
    development machine. This function is for policy and tests; use
    ``runtime_app_paths`` when callers need concrete ``Path`` objects for IO.
    """
    info = platform_info(sys_platform)
    if info.key == "win32":
        home_win = PureWindowsPath(home)
        appdata = PureWindowsPath(env.get("APPDATA", home_win / "AppData" / "Roaming"))
        localappdata = PureWindowsPath(
            env.get("LOCALAPPDATA", home_win / "AppData" / "Local")
        )
        public = PureWindowsPath(env.get("PUBLIC", "C:/Users/Public"))
        return AppPaths(
            config_dir=appdata / "VideoTranslatorAI",
            data_dir=localappdata / "VideoTranslatorAI",
            cache_dir=localappdata / "VideoTranslatorAI" / "Cache",
            wav2lip_dir=localappdata / "VideoTranslatorAI" / "wav2lip",
            default_videos_dir=public / "Videos",
        )

    if info.key == "linux":
        home_posix = PurePosixPath(home)
        config_root = PurePosixPath(env.get("XDG_CONFIG_HOME", home_posix / ".config"))
        data_root = PurePosixPath(
            env.get("XDG_DATA_HOME", home_posix / ".local" / "share")
        )
        cache_root = PurePosixPath(env.get("XDG_CACHE_HOME", home_posix / ".cache"))
        return AppPaths(
            config_dir=config_root / "videotranslatorai",
            data_dir=data_root / "videotranslatorai",
            cache_dir=cache_root / "videotranslatorai",
            wav2lip_dir=data_root / "wav2lip",
            default_videos_dir=home_posix / "Videos",
        )

    # macOS and unknown platforms are intentionally best-effort. The support
    # matrix should stay honest until the project has real test coverage there.
    home_posix = PurePosixPath(home)
    data_root = home_posix / "Library" / "Application Support" / "VideoTranslatorAI"
    return AppPaths(
        config_dir=data_root,
        data_dir=data_root,
        cache_dir=home_posix / "Library" / "Caches" / "VideoTranslatorAI",
        wav2lip_dir=data_root / "wav2lip",
        default_videos_dir=home_posix / "Movies",
    )


def runtime_app_paths(
    sys_platform: str,
    env: dict[str, str],
    home: Path,
) -> RuntimeAppPaths:
    """Resolve concrete runtime paths for filesystem IO on this host.

    Unlike ``resolve_app_paths``, this function returns concrete ``Path``
    instances. It should only be called for the platform the process is running
    on; synthetic Windows paths in cross-platform tests belong in the pure
    resolver.
    """
    info = platform_info(sys_platform)
    if info.key != platform_info(sys.platform).key:
        raise ValueError(
            "runtime_app_paths requires sys_platform to match the current host; "
            "use resolve_app_paths for synthetic platform tests"
        )

    home_path = Path(home)
    if info.key == "win32":
        appdata = Path(env.get("APPDATA", home_path / "AppData" / "Roaming"))
        localappdata = Path(env.get("LOCALAPPDATA", home_path / "AppData" / "Local"))
        public = Path(env.get("PUBLIC", home_path.parent / "Public"))
        return RuntimeAppPaths(
            config_dir=appdata / "VideoTranslatorAI",
            data_dir=localappdata / "VideoTranslatorAI",
            cache_dir=localappdata / "VideoTranslatorAI" / "Cache",
            wav2lip_dir=localappdata / "VideoTranslatorAI" / "wav2lip",
            default_videos_dir=public / "Videos",
        )

    if info.key == "linux":
        config_root = Path(env.get("XDG_CONFIG_HOME", home_path / ".config"))
        data_root = Path(env.get("XDG_DATA_HOME", home_path / ".local" / "share"))
        cache_root = Path(env.get("XDG_CACHE_HOME", home_path / ".cache"))
        return RuntimeAppPaths(
            config_dir=config_root / "videotranslatorai",
            data_dir=data_root / "videotranslatorai",
            cache_dir=cache_root / "videotranslatorai",
            wav2lip_dir=data_root / "wav2lip",
            default_videos_dir=home_path / "Videos",
        )

    data_root = home_path / "Library" / "Application Support" / "VideoTranslatorAI"
    return RuntimeAppPaths(
        config_dir=data_root,
        data_dir=data_root,
        cache_dir=home_path / "Library" / "Caches" / "VideoTranslatorAI",
        wav2lip_dir=data_root / "wav2lip",
        default_videos_dir=home_path / "Movies",
    )


def linux_xdg_videos_dir(
    *,
    run: Callable[..., Any] = subprocess.run,
) -> Path | None:
    """Return ``xdg-user-dir VIDEOS`` when available on Linux."""
    try:
        out = run(
            ["xdg-user-dir", "VIDEOS"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return Path(out) if out else None


def windows_known_videos_dir(sys_platform: str | None = None) -> Path | None:
    """Resolve the real Windows Videos Known Folder via Shell32 when possible."""
    if sys_platform is None:
        sys_platform = sys.platform
    if not sys_platform.startswith("win"):
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        folderid_videos = _GUID(
            0x18989B1D,
            0x99B5,
            0x455B,
            (ctypes.c_ubyte * 8)(0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC),
        )
        sh_get_known_folder_path = ctypes.windll.shell32.SHGetKnownFolderPath
        sh_get_known_folder_path.argtypes = [
            ctypes.POINTER(_GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        sh_get_known_folder_path.restype = ctypes.c_long
        out = ctypes.c_wchar_p()
        hr = sh_get_known_folder_path(ctypes.byref(folderid_videos), 0, None, ctypes.byref(out))
        if hr == 0 and out.value:
            path_str = out.value
            ctypes.windll.ole32.CoTaskMemFree(out)
            return Path(path_str)
    except Exception:
        return None
    return None


# One dedicated folder, identical on Windows and Linux, where translated files
# land by default. It is a subfolder of the user's videos directory so the
# output is easy to find; the user can override it with an explicit folder.
APP_OUTPUT_DIR_NAME = "VideoTranslatorAI"


def default_videos_dir(
    sys_platform: str | None = None,
    home: Path | None = None,
    *,
    xdg_videos_dir: Callable[[], Path | None] | None = None,
    windows_videos_dir: Callable[[], Path | None] | None = None,
) -> Path:
    """Return the user's preferred videos folder for the current platform."""
    if sys_platform is None:
        sys_platform = sys.platform
    if home is None:
        home = Path.home()

    if sys_platform.startswith("linux"):
        resolver = xdg_videos_dir or linux_xdg_videos_dir
        xdg_path = resolver()
        if xdg_path is not None:
            return xdg_path

    if sys_platform == "darwin":
        movies = home / "Movies"
        if movies.exists():
            return movies

    if sys_platform.startswith("win"):
        resolver = windows_videos_dir or (lambda: windows_known_videos_dir(sys_platform))
        known_folder = resolver()
        if known_folder is not None:
            return known_folder

    return home / "Videos"


def default_output_dir(
    sys_platform: str | None = None,
    home: Path | None = None,
    *,
    xdg_videos_dir: Callable[[], Path | None] | None = None,
    windows_videos_dir: Callable[[], Path | None] | None = None,
) -> Path:
    """The default single output folder: ``<videos>/VideoTranslatorAI``."""
    return default_videos_dir(
        sys_platform, home,
        xdg_videos_dir=xdg_videos_dir,
        windows_videos_dir=windows_videos_dir,
    ) / APP_OUTPUT_DIR_NAME


def resolve_output_dir(
    configured: str | None,
    sys_platform: str | None = None,
    home: Path | None = None,
) -> Path:
    """Return the configured output folder when set, else the default one.

    An empty or missing configuration falls back to :func:`default_output_dir`
    so translated files always land in one predictable place on both platforms.
    """
    if configured:
        return Path(configured).expanduser()
    return default_output_dir(sys_platform, home)


def _windows_pid_alive(pid: int) -> bool:
    try:
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        exit_code = wintypes.DWORD()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        kernel32.CloseHandle(handle)
        return bool(ok) and exit_code.value == 259  # STILL_ACTIVE
    except Exception:
        return True  # inconclusive: do not treat as dead


def pid_alive(pid: int, *, sys_platform: str | None = None,
              kill: Callable[[int, int], None] = os.kill,
              win_probe: Callable[[int], bool] | None = None) -> bool:
    """Whether ``pid`` is a live process (design G12).

    ``os.kill(pid, 0)`` is a liveness probe on POSIX only; on Windows a handle is
    opened and its exit code checked. Injected ``kill``/``win_probe`` keep both
    branches testable.
    """
    if sys_platform is None:
        sys_platform = sys.platform
    if pid <= 0:
        return False
    if sys_platform.startswith("win"):
        return (win_probe or _windows_pid_alive)(pid)
    try:
        kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def process_start_token(pid: int, *, sys_platform: str | None = None,
                        proc_stat_reader: Callable[[int], str] | None = None) -> str | None:
    """A token that changes when a PID is reused (design G12, 4.15).

    On Linux it is field 22 (``starttime``) of ``/proc/<pid>/stat``. On other
    platforms it returns ``None`` unless a reader is injected. Paired with the
    PID, it detects a stale ``session.lock`` whose owner has exited and a new
    process took the number.
    """
    if sys_platform is None:
        sys_platform = sys.platform
    if not sys_platform.startswith("linux") and proc_stat_reader is None:
        return None
    reader = proc_stat_reader or _read_proc_stat
    try:
        stat = reader(pid)
    except OSError:
        return None
    # The comm field is in parentheses and may contain spaces/parens; split
    # after the last ')'.
    tail = stat[stat.rfind(")") + 1:].split()
    # After comm, fields are state (index 0), ..., starttime is field 22 overall
    # which is index 22 - 3 = 19 in the post-comm tail.
    if len(tail) <= 19:
        return None
    return tail[19]


def _read_proc_stat(pid: int) -> str:
    with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
        return fh.read()


def reveal_in_file_manager(
    path: PurePath,
    *,
    sys_platform: str | None = None,
    popen: Callable[..., Any] = subprocess.Popen,
    startfile: Callable[[str], Any] | None = None,
) -> bool:
    """Reveal a media file with the native file manager.

    Windows Explorer accepts its ``/select`` invocation as one command line;
    Linux opens the containing directory because xdg-open has no portable
    select-file operation.  The injected runners keep both branches testable
    on either host.
    """
    if sys_platform is None:
        sys_platform = sys.platform
    if sys_platform.startswith("win"):
        windows_path = str(PureWindowsPath(path))
        command = f'explorer /select,"{windows_path}"'
        try:
            popen(command)
            return True
        except OSError:
            fallback = startfile if startfile is not None else getattr(os, "startfile", None)
            if fallback is None:
                return False
            try:
                fallback(windows_path)
                return True
            except OSError:
                return False
    if sys_platform.startswith("linux"):
        folder = str(PurePosixPath(path).parent)
        try:
            popen(["xdg-open", folder])
            return True
        except OSError:
            return False
    return False


def _wav2lip_asset_candidates(
    sys_platform: str,
    env: dict[str, str],
    home: Path,
) -> list[Path]:
    """Return ordered candidates for the Wav2Lip asset directory.

    The first candidate is the system-wide install path that the installer
    can pre-populate; the remaining ones are user-local fallbacks that are
    always reachable even without admin privileges. Order matters: the
    resolver picks the first candidate that already contains valid assets,
    otherwise it falls back to the first writable one.
    """
    info = platform_info(sys_platform)
    home_path = Path(home)
    if info.key == "win32":
        program_files = env.get("ProgramFiles") or env.get("PROGRAMFILES")
        if not program_files:
            program_files = r"C:\Program Files"
        localappdata = env.get("LOCALAPPDATA") or str(home_path / "AppData" / "Local")
        return [
            Path(program_files) / "VideoTranslatorAI" / "wav2lip",
            Path(localappdata) / "VideoTranslatorAI" / "wav2lip",
        ]

    if info.key == "linux":
        data_root = Path(env.get("XDG_DATA_HOME") or (home_path / ".local" / "share"))
        return [
            Path("/opt/VideoTranslatorAI/wav2lip"),
            data_root / "wav2lip",
        ]

    # macOS / unknown: keep a single user-local candidate.
    return [home_path / "Library" / "Application Support" / "VideoTranslatorAI" / "wav2lip"]


def _wav2lip_work_dir(
    sys_platform: str,
    env: dict[str, str],
    home: Path,
) -> Path:
    """Return the user-local writable scratch directory for Wav2Lip."""
    info = platform_info(sys_platform)
    home_path = Path(home)
    if info.key == "win32":
        localappdata = env.get("LOCALAPPDATA") or str(home_path / "AppData" / "Local")
        return Path(localappdata) / "VideoTranslatorAI" / "wav2lip-work"
    if info.key == "linux":
        cache_root = Path(env.get("XDG_CACHE_HOME") or (home_path / ".cache"))
        return cache_root / "wav2lip"
    return home_path / "Library" / "Caches" / "VideoTranslatorAI" / "wav2lip-work"


def _wav2lip_assets_present(candidate: Path) -> bool:
    """Return True if *candidate* already contains a usable Wav2Lip layout.

    Both the cloned repo (with its ``inference.py``) AND the downloaded model
    weights must exist. A half-populated directory is rejected so the caller
    falls back to a writable location and finishes the install there instead
    of trying to mkdir/git clone under a read-only system path.
    """
    try:
        if not candidate.is_dir():
            return False
        repo_ok = (
            candidate / _WAV2LIP_REPO_SENTINEL[0] / _WAV2LIP_REPO_SENTINEL[1]
        ).exists()
        model_ok = (candidate / _WAV2LIP_MODEL_SENTINEL).exists()
        return repo_ok and model_ok
    except (OSError, PermissionError):
        return False


def _is_dir_writable(path: Path) -> bool:
    """Probe-write check that respects NTFS ACLs / UAC virtualisation.

    ``os.access(..., os.W_OK)`` is unreliable on Windows: it inspects only the
    read-only attribute and routinely reports True for ``C:\\Program Files``
    even when a real write would be denied. A tempfile create+delete is the
    only portable way to get a truthful answer without pulling in pywin32.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        return False
    try:
        if not path.is_dir():
            return False
    except (OSError, PermissionError):
        return False
    try:
        with tempfile.NamedTemporaryFile(
            dir=str(path), prefix=".vtai_wtest_", delete=True
        ):
            pass
        return True
    except (OSError, PermissionError):
        return False


def resolve_wav2lip_paths(
    sys_platform: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
    *,
    writable_check: "callable[[Path], bool] | None" = None,
    assets_check: "callable[[Path], bool] | None" = None,
) -> Wav2LipPaths:
    """Resolve the asset and work directories for the Wav2Lip stage.

    Resolution policy for ``asset_dir``:

      1. Walk the platform-specific candidate list in priority order. The
         first candidate that already contains a valid layout (repo + model)
         is returned as-is, even if it lives under a read-only system install
         path. Runtime scratch IO is routed to ``work_dir`` by the caller.
      2. If no candidate is fully populated, fall back to the first writable
         candidate (creating it on demand). This is the "fresh install" path:
         the caller will git-clone + download into a guaranteed-writable
         location instead of crashing under ``%ProgramFiles%``.
      3. As a last resort, return the first candidate even if not writable;
         the caller will surface an actionable error.

    ``work_dir`` is always resolved to a per-user, guaranteed-writable
    location and created on the spot.

    The function takes ``sys_platform``, ``env`` and ``home`` so unit tests
    can simulate Windows from a Linux developer machine. ``writable_check``
    and ``assets_check`` are seams for the same reason - both default to the
    real filesystem probes.
    """
    if sys_platform is None:
        sys_platform = sys.platform
    if env is None:
        env = dict(os.environ)
    if home is None:
        home = Path.home()
    if writable_check is None:
        writable_check = _is_dir_writable
    if assets_check is None:
        assets_check = _wav2lip_assets_present

    candidates = _wav2lip_asset_candidates(sys_platform, env, Path(home))

    chosen: Path | None = None
    for cand in candidates:
        if assets_check(cand):
            chosen = cand
            break

    if chosen is None:
        for cand in candidates:
            if writable_check(cand):
                chosen = cand
                break

    if chosen is None:
        # Nothing writable: surface the first candidate so the caller can
        # report a precise "asset dir not writable" error instead of crashing
        # later with a less actionable PermissionError.
        chosen = candidates[0]

    work_dir = _wav2lip_work_dir(sys_platform, env, Path(home))
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        # Even the user-local cache failed (read-only home?). Returning the
        # path anyway lets the caller decide whether to abort or retry.
        pass

    return Wav2LipPaths(asset_dir=chosen, work_dir=work_dir)


# --- Multi-monitor geometry (center a window on the screen it opens on) -------

_XRANDR_MON_RE = re.compile(r"(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)")


def parse_xrandr_monitors(text: str) -> list[tuple[int, int, int, int]]:
    """Parse ``xrandr --listmonitors`` into ``(x, y, w, h)`` rectangles.

    Each monitor line carries a token like ``1920/600x1080/340+1080+293``
    (``w/mmw x h/mmh + x + y``); the physical millimetre parts are ignored.
    """
    rects: list[tuple[int, int, int, int]] = []
    for line in text.splitlines():
        match = _XRANDR_MON_RE.search(line)
        if match:
            w, h, x, y = (int(g) for g in match.groups())
            if w > 0 and h > 0:
                rects.append((x, y, w, h))
    return rects


def _rect_contains(rect: tuple[int, int, int, int], px: int, py: int) -> bool:
    x, y, w, h = rect
    return x <= px < x + w and y <= py < y + h


def _x11_monitor_bounds(px: int, py: int, *, run=None):
    """Bounds of the X11 monitor under ``(px, py)`` via ``xrandr``.

    ``run`` (injectable for tests) returns the ``xrandr --listmonitors`` text.
    Falls back to the first monitor when the point is outside all of them.
    """
    if run is None:
        def run() -> str:
            return subprocess.run(
                ["xrandr", "--listmonitors"], capture_output=True, text=True,
                timeout=3, stdin=subprocess.DEVNULL).stdout
    rects = parse_xrandr_monitors(run())
    for rect in rects:
        if _rect_contains(rect, px, py):
            return rect
    return rects[0] if rects else None


def _win_monitor_bounds(px: int, py: int):
    """Work-area bounds of the Windows monitor under ``(px, py)`` (no taskbar)."""
    import ctypes
    from ctypes import wintypes

    class _RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    class _MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", _RECT),
                    ("rcWork", _RECT), ("dwFlags", wintypes.DWORD)]

    user32 = ctypes.windll.user32
    point = wintypes.POINT(int(px), int(py))
    hmon = user32.MonitorFromPoint(point, 2)  # MONITOR_DEFAULTTONEAREST
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
        return None
    work = info.rcWork
    return (work.left, work.top, work.right - work.left, work.bottom - work.top)


def monitor_bounds_at(px: int, py: int, *, fallback: tuple[int, int, int, int],
                      sys_platform: str = sys.platform, run=None
                      ) -> tuple[int, int, int, int]:
    """``(x, y, w, h)`` of the monitor containing ``(px, py)``.

    Lets the app center itself on the screen it opens on instead of the middle
    of the whole virtual desktop (which straddles monitors). Returns
    ``fallback`` (the whole screen) when detection fails or there is one screen.
    """
    try:
        if sys_platform.startswith("win"):
            bounds = _win_monitor_bounds(px, py)
        elif sys_platform == "darwin":
            bounds = None  # Tk reports one logical screen on macOS
        else:
            bounds = _x11_monitor_bounds(px, py, run=run)
    except Exception:  # noqa: BLE001 - detection is best effort
        bounds = None
    return bounds if bounds is not None else fallback
