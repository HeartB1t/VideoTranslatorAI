"""Flat ``player_*`` / ``live_*`` config keys of the integrated player (spec 2.5).

Pure: no I/O, no Tk. The GUI reads the config with ``load_config`` and saves
with ``save_config`` on the Tk thread; this module only turns the raw mapping
into typed settings and back. Every malformed or out-of-range value falls
back to its default, so a hand-edited config can never break the player.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .libmpv_runtime import VO_PROFILE_OPTIONS

AUDIO_CHOICES = ("dubbed", "original")
SYNC_MODES = ("delayed", "live")
LIVE_ENGINES = ("marian", "ollama", "google", "deepl")
LIVE_MAX_HEIGHTS = (480, 720, 1080)


@dataclass(frozen=True)
class PlayerSettings:
    volume: int
    muted: bool
    audio: str
    subs_visible: bool
    autoload_result: bool
    vo_profile: str | None
    keep_original_audio: bool


@dataclass(frozen=True)
class LiveSettings:
    sync_mode: str
    delay_s: float | None
    file_ahead_s: float | None
    delay_auto: bool
    engine: str
    dub_enabled: bool
    subs_enabled: bool
    duck_level: float
    max_height: int
    buffer_max_mb: int


def _bool(cfg: Mapping[str, Any], key: str, default: bool) -> bool:
    value = cfg.get(key)
    return value if isinstance(value, bool) else default


def _int(cfg: Mapping[str, Any], key: str, default: int, lo: int, hi: int) -> int:
    value = cfg.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        return default
    return value


def _float(cfg: Mapping[str, Any], key: str, default: float | None,
           lo: float, hi: float) -> float | None:
    value = cfg.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    return value if lo <= value <= hi else default


def _choice(cfg: Mapping[str, Any], key: str, choices: tuple, default: Any) -> Any:
    value = cfg.get(key)
    return value if value in choices else default


def vo_profiles_for(sys_platform: str) -> tuple[str, ...]:
    """The VO profile names of a platform, in fallback order (spec 3.1)."""
    return tuple(VO_PROFILE_OPTIONS["win32" if sys_platform == "win32" else "linux"])


def normalize_player_settings(cfg: Mapping[str, Any], *, sys_platform: str) -> PlayerSettings:
    return PlayerSettings(
        volume=_int(cfg, "player_volume", 100, 0, 130),
        muted=_bool(cfg, "player_muted", False),
        audio=_choice(cfg, "player_audio", AUDIO_CHOICES, "dubbed"),
        subs_visible=_bool(cfg, "player_subs_visible", True),
        autoload_result=_bool(cfg, "player_autoload_result", True),
        vo_profile=_choice(cfg, "player_vo_profile", vo_profiles_for(sys_platform), None),
        keep_original_audio=_bool(cfg, "keep_original_audio", True),
    )


def normalize_live_settings(cfg: Mapping[str, Any]) -> LiveSettings:
    return LiveSettings(
        sync_mode=_choice(cfg, "live_sync_mode", SYNC_MODES, "delayed"),
        delay_s=_float(cfg, "live_delay_s", None, 6.0, 30.0),
        file_ahead_s=_float(cfg, "live_file_ahead_s", None, 4.0, 30.0),
        delay_auto=_bool(cfg, "live_delay_auto", True),
        engine=_choice(cfg, "live_engine", LIVE_ENGINES, "marian"),
        dub_enabled=_bool(cfg, "live_dub_enabled", True),
        subs_enabled=_bool(cfg, "live_subs_enabled", True),
        duck_level=_float(cfg, "live_duck_level", 0.3, 0.1, 0.6),
        max_height=_choice(cfg, "live_max_height", LIVE_MAX_HEIGHTS, 720),
        buffer_max_mb=_int(cfg, "live_buffer_max_mb", 1024, 256, 8192),
    )


def settings_to_config(settings: PlayerSettings | LiveSettings) -> dict[str, Any]:
    """Flat keys for ``save_config``. Optional values that are unset stay absent."""
    if isinstance(settings, PlayerSettings):
        cfg: dict[str, Any] = {
            "player_volume": settings.volume,
            "player_muted": settings.muted,
            "player_audio": settings.audio,
            "player_subs_visible": settings.subs_visible,
            "player_autoload_result": settings.autoload_result,
            "keep_original_audio": settings.keep_original_audio,
        }
        if settings.vo_profile is not None:
            cfg["player_vo_profile"] = settings.vo_profile
        return cfg
    cfg = {
        "live_sync_mode": settings.sync_mode,
        "live_delay_auto": settings.delay_auto,
        "live_engine": settings.engine,
        "live_dub_enabled": settings.dub_enabled,
        "live_subs_enabled": settings.subs_enabled,
        "live_duck_level": settings.duck_level,
        "live_max_height": settings.max_height,
        "live_buffer_max_mb": settings.buffer_max_mb,
    }
    if settings.delay_s is not None:
        cfg["live_delay_s"] = settings.delay_s
    if settings.file_ahead_s is not None:
        cfg["live_file_ahead_s"] = settings.file_ahead_s
    return cfg
