"""JSON configuration helpers.

This module keeps file IO small and injectable so it can be tested without
touching the user's real config file or keyring.

It also owns the platform-aware *user* config location (XDG on Linux,
``%APPDATA%`` on Windows, ``~/Library/Application Support`` on macOS) and the
one-shot migration from the legacy ``~/.videotranslatorai_config.json`` path
used up to v1.9.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .platforms import platform_info


# ---------------------------------------------------------------------------
# Low-level JSON IO (already used by tests; signatures kept stable on purpose)
# ---------------------------------------------------------------------------

def load_json_config(path: Path) -> dict[str, Any]:
    """Load a JSON object config; return an empty dict on absent/invalid files."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def write_json_config(path: Path, cfg: dict[str, Any]) -> None:
    """Write a full config dict atomically with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2)
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    tmp.replace(path)


def merge_json_config(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Merge ``data`` into the existing config, persist it, and return it."""
    existing = load_json_config(path)
    existing.update(data)
    write_json_config(path, existing)
    return existing


# ---------------------------------------------------------------------------
# Platform-aware user config path resolution + legacy migration
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "config.json"
LEGACY_CONFIG_NAME = ".videotranslatorai_config.json"


def _resolve_env_and_home(
    sys_platform: str | None,
    env: dict[str, str] | None,
    home: Path | None,
) -> tuple[str, dict[str, str], Path]:
    """Fill defaults for the injectable trio used by every public helper."""
    sp = sys_platform if sys_platform is not None else sys.platform
    en = env if env is not None else dict(os.environ)
    hm = home if home is not None else Path.home()
    return sp, en, hm


def get_default_config_path(
    sys_platform: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the platform-appropriate config file path.

    * Linux: ``$XDG_CONFIG_HOME/videotranslatorai/config.json`` (default
      ``~/.config/videotranslatorai/config.json``).
    * Windows: ``%APPDATA%\\VideoTranslatorAI\\config.json``.
    * macOS / fallback: ``~/Library/Application Support/VideoTranslatorAI/config.json``.

    ``sys_platform`` / ``env`` / ``home`` are injected for testability; defaults
    use the real environment.
    """
    sp, en, hm = _resolve_env_and_home(sys_platform, env, home)
    info = platform_info(sp)

    if info.key == "win32":
        appdata = Path(en.get("APPDATA", Path(hm) / "AppData" / "Roaming"))
        return appdata / "VideoTranslatorAI" / CONFIG_FILENAME

    if info.key == "linux":
        config_root = Path(en.get("XDG_CONFIG_HOME", Path(hm) / ".config"))
        return config_root / "videotranslatorai" / CONFIG_FILENAME

    # macOS and any unknown platform: stay aligned with platforms.resolve_app_paths.
    return Path(hm) / "Library" / "Application Support" / "VideoTranslatorAI" / CONFIG_FILENAME


def get_legacy_config_path(home: Path | None = None) -> Path:
    """Return the v1.0–v1.9 legacy path: ``~/.videotranslatorai_config.json``."""
    hm = home if home is not None else Path.home()
    return Path(hm) / LEGACY_CONFIG_NAME


def migrate_legacy_config_if_needed(
    sys_platform: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> bool:
    """Copy legacy → new config when only the legacy file exists.

    Returns ``True`` when a copy actually happened so the caller can log it.
    Idempotent: a second call is a no-op because the new path now exists.
    The legacy file is intentionally left in place for backward safety.
    """
    sp, en, hm = _resolve_env_and_home(sys_platform, env, home)
    new_path = get_default_config_path(sp, en, hm)
    legacy_path = get_legacy_config_path(hm)

    if new_path.exists():
        return False
    if not legacy_path.exists():
        return False

    try:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, new_path)
        try:
            os.chmod(new_path, 0o600)
        except Exception:
            pass
        return True
    except Exception:
        return False


def load_user_config(
    sys_platform: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """Load the user config with backward compat for the legacy path.

    Resolution order:
    1. New XDG / APPDATA / macOS path → use it.
    2. Otherwise, if the legacy ``~/.videotranslatorai_config.json`` exists,
       read it AND copy it to the new path so future writes land there.
    3. If neither exists, return ``{}``.
    """
    sp, en, hm = _resolve_env_and_home(sys_platform, env, home)
    new_path = get_default_config_path(sp, en, hm)

    if new_path.exists():
        return load_json_config(new_path)

    legacy_path = get_legacy_config_path(hm)
    if legacy_path.exists():
        # Best-effort migration so the next save_user_config writes to new_path.
        migrate_legacy_config_if_needed(sp, en, hm)
        return load_json_config(legacy_path)

    return {}


def save_user_config(
    data: dict[str, Any],
    sys_platform: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Write ``data`` to the new platform-aware path. Returns the path written.

    Parents are created as needed. The legacy file is never deleted here so
    older versions of the tool keep working during the transition window.
    """
    sp, en, hm = _resolve_env_and_home(sys_platform, env, home)
    new_path = get_default_config_path(sp, en, hm)
    write_json_config(new_path, data)
    return new_path
