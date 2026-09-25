"""Thread-safe primitives and test backend for the integrated player.

This first layer does not import Tk or python-mpv. The real libmpv adapter is
added separately so queues, clocks, options and state ownership stay testable
without a display or native libraries.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .libmpv_runtime import VO_PROFILE_OPTIONS


@dataclass(frozen=True)
class BridgeEvent:
    kind: str
    payload: object = None


@dataclass(frozen=True)
class BridgeSnapshot:
    changed: dict[str, tuple[object, float]]
    events: tuple[BridgeEvent, ...]


class EventBridge:
    """Bounded, thread-safe path from mpv callbacks to the consumer thread."""

    LATEST = (
        "time-pos", "duration", "pause", "paused-for-cache", "seeking", "core-idle",
        "idle-active", "eof-reached", "speed", "demuxer-cache-time",
        "demuxer-cache-duration", "video-params", "track-list",
    )
    _LATEST_SET = frozenset(LATEST)

    def __init__(self, *, max_events: int = 512) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        self._max_events = int(max_events)
        self._values: dict[str, tuple[object, float]] = {}
        self._changed: set[str] = set()
        self._events: deque[BridgeEvent] = deque()
        self._closed = False
        self._lock = threading.Lock()

    def set_latest(self, name: str, value: object, mono: float) -> None:
        if name not in self._LATEST_SET:
            return
        with self._lock:
            if self._closed:
                return
            self._values[name] = (value, float(mono))
            self._changed.add(name)

    def post(self, kind: str, payload: object = None) -> None:
        if not isinstance(kind, str):
            return
        with self._lock:
            if self._closed:
                return
            if len(self._events) >= self._max_events:
                log_index = next((index for index, event in enumerate(self._events)
                                  if event.kind == "log"), None)
                if log_index is None:
                    self._events.popleft()
                else:
                    del self._events[log_index]
            self._events.append(BridgeEvent(kind, payload))

    def latest(self, name: str) -> tuple[object, float] | None:
        with self._lock:
            return self._values.get(name)

    def drain(self) -> BridgeSnapshot:
        with self._lock:
            changed = {name: self._values[name] for name in self._changed}
            events = tuple(self._events)
            self._changed.clear()
            self._events.clear()
        return BridgeSnapshot(changed, events)

    def close(self) -> None:
        with self._lock:
            self._closed = True


class PlaybackClock:
    """Extrapolate valid mpv time observations between callback updates."""

    def __init__(self, *, first_pts: float | None = None) -> None:
        self.first_pts = first_pts
        self._position: float | None = None
        self._stamp = 0.0
        self._speed = 1.0
        self._running = False
        self._valid = False
        self._expecting_restart = False
        self._epoch = 0
        self._lock = threading.Lock()

    @property
    def valid(self) -> bool:
        with self._lock:
            return self._valid

    @property
    def epoch(self) -> int:
        with self._lock:
            return self._epoch

    def expect_restart(self) -> None:
        with self._lock:
            self._expecting_restart = True
            self._valid = False

    def on_playback_restart(self, mono: float) -> None:
        with self._lock:
            self._epoch += 1
            self._expecting_restart = False
            self._valid = False
            self._stamp = float(mono)

    def observe(self, pos: float | None, mono: float, *, speed: float,
                running: bool, seeking: bool) -> None:
        with self._lock:
            invalid = (pos is None or seeking or self._expecting_restart
                       or (self.first_pts is not None and pos < self.first_pts))
            if invalid:
                self._valid = False
                return
            self._position = float(pos)
            self._stamp = float(mono)
            self._speed = max(0.0, float(speed))
            self._running = bool(running)
            self._valid = True

    def now(self, mono: float) -> float | None:
        with self._lock:
            if not self._valid or self._position is None:
                return None
            if not self._running:
                return self._position
            elapsed = max(0.0, float(mono) - self._stamp)
            return self._position + elapsed * self._speed


@dataclass
class _QueuedCommand:
    fn: Callable[[], None]
    key: str | None


class CommandQueue:
    """Small blocking queue with replacement by coalescing key."""

    def __init__(self, *, maxsize: int = 64) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = int(maxsize)
        self._items: list[_QueuedCommand] = []
        self._closed = False
        self._condition = threading.Condition()

    def put(self, fn: Callable[[], None], *, key: str | None = None) -> bool:
        with self._condition:
            if self._closed:
                return False
            if key is not None:
                for index, item in enumerate(self._items):
                    if item.key == key:
                        self._items[index] = _QueuedCommand(fn, key)
                        self._condition.notify()
                        return True
            if len(self._items) >= self._maxsize:
                return False
            self._items.append(_QueuedCommand(fn, key))
            self._condition.notify()
            return True

    def get(self, timeout: float) -> Callable[[], None] | None:
        deadline = time.monotonic() + max(0.0, float(timeout))
        with self._condition:
            while not self._items and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)
            if self._closed or not self._items:
                return None
            return self._items.pop(0).fn

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._items.clear()
            self._condition.notify_all()


@dataclass(frozen=True)
class MixState:
    version: int
    owner: str
    video_volume: float
    voice_volume: float
    muted: bool


class VolumeMixer:
    """Own volume and ducking state without calling a playback backend."""

    def __init__(self, *, user_volume: float = 100.0, muted: bool = False) -> None:
        self._user_volume = min(130.0, max(0.0, float(user_volume)))
        self._muted = bool(muted)
        self._duck_gain = 1.0
        self._owner = "cmd"
        self._version = 0
        self._lock = threading.Lock()

    def _set(self, attr: str, value: object) -> None:
        with self._lock:
            if getattr(self, attr) != value:
                setattr(self, attr, value)
                self._version += 1

    def set_user_volume(self, value: float) -> None:
        self._set("_user_volume", min(130.0, max(0.0, float(value))))

    def set_muted(self, muted: bool) -> None:
        self._set("_muted", bool(muted))

    def set_duck_gain(self, gain: float) -> None:
        self._set("_duck_gain", min(1.0, max(0.0, float(gain))))

    def set_owner(self, owner: str) -> None:
        if owner not in ("cmd", "sched"):
            raise ValueError("owner must be 'cmd' or 'sched'")
        self._set("_owner", owner)

    def snapshot(self) -> MixState:
        with self._lock:
            if self._muted:
                video = voice = 0.0
            else:
                video = self._user_volume * self._duck_gain
                voice = self._user_volume
            return MixState(self._version, self._owner, video, voice, self._muted)


VO_PROFILES: dict[str, tuple[str, ...]] = {
    platform: tuple(profiles) for platform, profiles in VO_PROFILE_OPTIONS.items()
}


def _profile_options(sys_platform: str, vo_profile: str) -> dict[str, str]:
    try:
        options = VO_PROFILE_OPTIONS[sys_platform][vo_profile]
    except KeyError as exc:
        raise ValueError(f"unsupported VO profile {vo_profile!r} on {sys_platform!r}") from exc
    return {key.replace("-", "_"): value for key, value in options.items()}


def build_mpv_options(kind: str, *, sys_platform: str, wid: int | None,
                      vo_profile: str) -> dict[str, str]:
    """Build python-mpv constructor options without loading the module."""
    common = {
        "idle": "yes",
        "ytdl": "no",
        "load_scripts": "no",
        "config": "no",
        "terminal": "no",
        "audio_buffer": "0.2",
    }
    if kind == "voice":
        return {
            **common,
            "vid": "no",
            "force_window": "no",
            "keep_open": "no",
            "cache": "no",
        }
    if kind != "video":
        raise ValueError(f"unsupported mpv backend kind: {kind!r}")
    if wid is None:
        raise ValueError("the video backend needs a window id")
    window_id = int(wid)
    if sys_platform == "win32":
        window_id &= 0xFFFFFFFF
    return {
        **common,
        "wid": str(window_id),
        "hwdec": "auto-safe",
        "keep_open": "yes",
        "force_window": "yes",
        "osc": "no",
        "osd_level": "0",
        "input_default_bindings": "no",
        "input_vo_keyboard": "no",
        "sub_auto": "no",
        "audio_file_auto": "no",
        "loglevel": "warn",
        **_profile_options(sys_platform, vo_profile),
    }


def next_vo_profile(sys_platform: str, current: str,
                    accepted: Sequence[str]) -> str | None:
    profiles = VO_PROFILES.get(sys_platform, ())
    accepted_set = set(accepted)
    try:
        start = profiles.index(current) + 1
    except ValueError:
        start = 0
    return next((profile for profile in profiles[start:] if profile in accepted_set), None)


_VO_FAILURE_MARKERS = (
    "Failed initializing any suitable GPU context",
    "Error opening/initializing the selected video_out",
)


def detect_vo_failure(log_lines: Sequence[str], *, video_params_seen: bool,
                      has_video_track: bool, seconds_since_loaded: float) -> bool:
    if any(marker in str(line) for line in log_lines for marker in _VO_FAILURE_MARKERS):
        return True
    return (has_video_track and not video_params_seen
            and float(seconds_since_loaded) >= 5.0)


def stream_session_options(delay_max_s: float) -> dict[str, str]:
    if not math.isfinite(float(delay_max_s)) or float(delay_max_s) < 0:
        raise ValueError("delay_max_s must be a finite non-negative number")
    return {
        "rebase_start_time": "no",
        "cache": "yes",
        "force_seekable": "yes",
        "demuxer_max_bytes": str(256 * 1024 * 1024),
        "demuxer_max_back_bytes": str(32 * 1024 * 1024),
        "cache_pause": "yes",
        "cache_pause_wait": "1",
    }


def duck_channel_for(mpv_version: tuple[int, int] | None) -> str:
    return "af" if mpv_version is not None and mpv_version >= (0, 37) else "volume"


def af_duck_command(gain: float) -> list[str]:
    safe_gain = min(1.0, max(0.0, float(gain)))
    return ["af-command", "vtduck", "volume", f"{safe_gain:.3f}", "volume"]


class _InMemoryRealtimeOps:
    def __init__(self, backend: "InMemoryBackend") -> None:
        self._backend = backend

    def set_overlay(self, ass_events: str | None) -> None:
        self._backend._record("rt_overlay", ass_events)

    def set_speed(self, value: float) -> None:
        self._backend._record("rt_speed", float(value))

    def set_pause(self, paused: bool) -> None:
        self._backend._record("rt_pause", bool(paused))

    def set_duck(self, gain: float) -> None:
        self._backend.mixer.set_duck_gain(gain)
        self._backend._record("rt_duck", float(gain))


class InMemoryBackend:
    """PlayerBackend test double that records every operation in order."""

    def __init__(self, *, mixer: VolumeMixer | None = None,
                 mpv_version: tuple[int, int] | None = None,
                 af_supported: bool = True) -> None:
        self.mixer = mixer if mixer is not None else VolumeMixer()
        self.mpv_version = mpv_version
        self.af_supported = bool(af_supported)
        self.calls: list[tuple[Any, ...]] = []
        self.rt = _InMemoryRealtimeOps(self)
        self.terminated = False
        self._lock = threading.Lock()

    def _record(self, name: str, *args: object) -> None:
        with self._lock:
            self.calls.append((name, *args))

    def load(self, uri: str, *, paused: bool, start: float | None = None,
             options: Mapping[str, str] | None = None) -> None:
        self._record("load", uri, bool(paused), start, dict(options or {}))

    def stop(self) -> None:
        self._record("stop")

    def set_pause(self, paused: bool) -> None:
        self._record("set_pause", bool(paused))

    def seek(self, seconds: float, mode: str = "exact") -> None:
        if mode not in ("exact", "keyframes", "relative"):
            raise ValueError(f"unsupported seek mode: {mode!r}")
        self._record("seek", float(seconds), mode)

    def apply_mix(self) -> None:
        self._record("apply_mix", self.mixer.snapshot())

    def add_external_audio(self, path: str, title: str) -> None:
        self._record("add_external_audio", path, title)

    def select_audio(self, track_id: int | None) -> None:
        self._record("select_audio", track_id)

    def add_subtitles(self, path: str, title: str) -> None:
        self._record("add_subtitles", path, title)

    def reload_subtitles(self) -> None:
        self._record("reload_subtitles")

    def set_subtitles_visible(self, visible: bool) -> None:
        self._record("set_subtitles_visible", bool(visible))

    def screenshot(self, path: str) -> None:
        self._record("screenshot", path)

    def set_af(self, value: str) -> bool:
        self._record("set_af", value)
        return self.af_supported

    def register_stream_protocol(self, name: str, open_adapter: Callable) -> None:
        self._record("register_stream_protocol", name, open_adapter)

    def terminate(self, timeout_s: float) -> bool:
        if self.terminated:
            return False
        self.terminated = True
        self._record("terminate", float(timeout_s))
        return True
