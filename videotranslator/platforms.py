"""Platform policy and path resolution.

The project is developed on Linux and distributed to Windows users. This module
keeps that contract explicit so the rest of the code can avoid scattered
``sys.platform`` and environment-variable checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


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
    config_dir: Path | PureWindowsPath
    data_dir: Path | PureWindowsPath
    cache_dir: Path | PureWindowsPath
    wav2lip_dir: Path | PureWindowsPath
    default_videos_dir: Path | PureWindowsPath


def platform_info(sys_platform: str) -> PlatformInfo:
    """Return support metadata for a Python ``sys.platform`` value."""
    if sys_platform == "win32":
        return PlatformInfo("win32", "Windows 10/11 x64", supported=True)
    if sys_platform.startswith("linux"):
        return PlatformInfo("linux", "Debian/Ubuntu/Kali-like Linux", supported=True)
    if sys_platform == "darwin":
        return PlatformInfo("darwin", "macOS", supported=False, experimental=True)
    return PlatformInfo(sys_platform, sys_platform, supported=False)


def resolve_app_paths(
    sys_platform: str,
    env: dict[str, str],
    home: Path | PureWindowsPath,
) -> AppPaths:
    """Resolve config/data/cache paths without touching the filesystem.

    ``env`` is injected to make Windows and Linux behavior testable from any
    development machine.
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
        config_root = Path(env.get("XDG_CONFIG_HOME", Path(home) / ".config"))
        data_root = Path(env.get("XDG_DATA_HOME", Path(home) / ".local" / "share"))
        cache_root = Path(env.get("XDG_CACHE_HOME", Path(home) / ".cache"))
        return AppPaths(
            config_dir=config_root / "videotranslatorai",
            data_dir=data_root / "videotranslatorai",
            cache_dir=cache_root / "videotranslatorai",
            wav2lip_dir=data_root / "wav2lip",
            default_videos_dir=Path(home) / "Videos",
        )

    # macOS and unknown platforms are intentionally best-effort. The support
    # matrix should stay honest until the project has real test coverage there.
    data_root = Path(home) / "Library" / "Application Support" / "VideoTranslatorAI"
    return AppPaths(
        config_dir=data_root,
        data_dir=data_root,
        cache_dir=Path(home) / "Library" / "Caches" / "VideoTranslatorAI",
        wav2lip_dir=data_root / "wav2lip",
        default_videos_dir=Path(home) / "Movies",
    )

