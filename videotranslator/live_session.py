"""Live session controller (design 4.1-4.15). Part 1: config, status, factories
and the session-lock helpers.

The session wires the already-built pure modules (live_segment, live_asr,
live_translate, live_scheduler, live_sync, live_health, live_tts) with heavy
components injected through :class:`LiveFactories`, so the orchestration runs
against fakes with no ML / mpv / audio / network. This file holds the pure and
lock-only pieces; the threaded ``LiveSession`` orchestrator is added on top.

Status/warning/error codes stored here are the SHORT codes (``"busy"``,
``"need_source_lang"``, ``"rate_limited"``); the GUI maps them to i18n keys via
``live_health.STATUS_KEYS/WARN_KEYS/ERROR_KEYS``. No ``live_*`` UI-key literal
ever appears in this module.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .live_health import LIVE_STATES
from .platforms import pid_alive, process_start_token
from .player_settings import LiveSettings

_LOCK_NAME = "session.lock"


@dataclass(frozen=True)
class LiveConfig:
    """Immutable options for one live session.

    ``engine_opts`` (which carries the DeepL key) is excluded from ``repr`` so a
    traceback or a log line never leaks the key ([CC] G25).
    """

    source: str
    source_kind: str            # "file" | "url"
    start_at: float
    lang_source: str
    lang_target: str
    voice: str
    engine: str
    settings: LiveSettings
    session_dir: Path
    device_policy: str = "auto"   # "auto" | "cpu"
    hotwords: str | None = None
    engine_opts: dict = field(default_factory=dict, repr=False)


@dataclass
class LiveStatus:
    """4 Hz snapshot the GUI pulls (design 4.11 step 5). Mutable; the session
    hands out copies under a lock."""

    state: str = "starting"
    lag_s: float | None = None
    target_delay_s: float | None = None
    device: str = "cpu"
    engine: str = "marian"
    voiced: int = 0
    dropped: int = 0
    skipped_s: float = 0.0
    status_params: dict = field(default_factory=dict)  # extra {s}/{total}/{n}
    warning_key: str | None = None
    warning_params: dict = field(default_factory=dict)
    warning_action: str | None = None
    error_key: str | None = None
    error_params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LiveFactories:
    """Callables that build the heavy components; tests pass fakes.

    For a FILE session only ``decoder, vad, whisper, translator, tts, clock`` are
    used; ``resolve, ingest, store`` belong to the URL path (P6).
    """

    decoder: Callable[..., Any]
    vad: Callable[..., Any]
    whisper: Callable[..., Any]
    translator: Callable[..., Any]
    tts: Callable[..., Any]
    clock: Callable[[], float] = time.monotonic
    resolve: Callable[..., Any] | None = None
    ingest: Callable[..., Any] | None = None
    store: Callable[..., Any] | None = None
    timeouts: Any | None = None


def build_live_config(values: dict, *, settings: LiveSettings, cache_dir: Path,
                      now: float) -> LiveConfig:
    """Assemble a :class:`LiveConfig` from GUI values. Pure.

    ``now`` is passed in (scripts/tests provide it) so the session directory name
    is deterministic. The DeepL key travels only in ``engine_opts``.
    """
    session_dir = Path(cache_dir) / f"session-{int(now * 1000)}"
    engine_opts = {}
    if values.get("deepl_key"):
        engine_opts["deepl_key"] = values["deepl_key"]
    return LiveConfig(
        source=values["source"],
        source_kind=values.get("source_kind", "file"),
        start_at=float(values.get("start_at", 0.0)),
        lang_source=values.get("lang_source", "auto"),
        lang_target=values["lang_target"],
        voice=values.get("voice", ""),
        engine=values.get("engine", settings.engine),
        settings=settings,
        session_dir=session_dir,
        device_policy=values.get("device_policy", "auto"),
        hotwords=values.get("hotwords") or None,
        engine_opts=engine_opts,
    )


def write_session_lock(path: Path, *, pid: int, start_token: str | None) -> None:
    """Write ``session.lock`` with the owner pid and its start token."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "token": start_token}), encoding="utf-8")


def read_session_lock(path: Path) -> tuple[int, str | None] | None:
    """Return ``(pid, token)`` from a lock file, or None if missing/unreadable."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return int(data["pid"]), data.get("token")
    except (OSError, ValueError, KeyError, TypeError):
        return None


def default_owner_alive(pid: int, token: str | None) -> bool:
    """A live pid whose start token still matches (protects a second instance)."""
    return pid_alive(pid) and process_start_token(pid) == token


def cleanup_stale_sessions(root: Path, *, owner_alive: Callable[[int, str | None], bool]
                           = default_owner_alive, now: float, max_age_h: float = 24.0,
                           remover: Callable[[str], None] = shutil.rmtree) -> list[Path]:
    """Remove dead session directories under ``root`` (design 4.15, [CC] G12).

    A directory with a lock whose owner is alive is never touched. A dead or
    recycled owner (token mismatch) is removed. When the lock is missing or
    unreadable, the directory is removed only if older than ``max_age_h``.
    """
    root = Path(root)
    removed: list[Path] = []
    if not root.exists():
        return removed
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        lock = read_session_lock(entry / _LOCK_NAME)
        if lock is not None:
            pid, token = lock
            if owner_alive(pid, token):
                continue
            drop = True
        else:
            try:
                age_h = (now - entry.stat().st_mtime) / 3600.0
            except OSError:
                continue
            drop = age_h > max_age_h
        if drop:
            try:
                remover(str(entry))
                removed.append(entry)
            except OSError:
                pass
    return removed


def _assert_state(state: str) -> str:
    """Guard used by the orchestrator: every published state is a known one."""
    if state not in LIVE_STATES:
        raise ValueError(f"unknown live state: {state!r}")
    return state
