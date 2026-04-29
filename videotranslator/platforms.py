"""Platform policy and path resolution.

The project is developed on Linux and distributed to Windows users. This module
keeps that contract explicit so the rest of the code can avoid scattered
``sys.platform`` and environment-variable checks.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


SUPPORTED_PLATFORMS = {"win32", "linux"}
EXPERIMENTAL_PLATFORMS = {"darwin"}


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
