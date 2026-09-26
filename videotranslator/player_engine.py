"""Thread-safe primitives and test backend for the integrated player.

This first layer does not import Tk or python-mpv. The real libmpv adapter is
added separately so queues, clocks, options and state ownership stay testable
without a display or native libraries.
"""

from __future__ import annotations

import math
import ctypes
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .libmpv_runtime import VO_PROFILE_OPTIONS, parse_mpv_version


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
        self._extra: dict[str, tuple[object, float]] = {}
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

    def extra_latest(self, name: str, value: object, mono: float) -> None:
        """Store a property outside the fixed LATEST set (the voice mpv time-pos).

        Kept separate from the video values so a second mpv instance sharing the
        bridge cannot overwrite the player's own time-pos or track list.
        """
        with self._lock:
            if self._closed:
                return
            self._extra[str(name)] = (value, float(mono))

    def extra(self, name: str) -> tuple[object, float] | None:
        with self._lock:
            return self._extra.get(str(name))

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


def duck_af(player: object, gain: float, *,
            on_error: Callable[[BaseException], None] | None = None) -> bool:
    """Apply the af-command duck on a live mpv player, returning success.

    Used for the smooth ramp on mpv >= 0.37 (the "vtduck" lavfi volume filter is
    installed at session start). Any failure is reported and returns False so the
    caller can fall back to the volume channel.
    """
    if player is None:
        return False
    try:
        player.command(*af_duck_command(gain))
        return True
    except Exception as exc:
        if on_error is not None:
            on_error(exc)
        return False


class X11ErrorGuard:
    """Capture and restore Tk's process-global Xlib error handler."""

    def __init__(self, *, load_libx11: Callable[[], object]) -> None:
        self._load_libx11 = load_libx11
        self._libx11: object | None = None
        self._tk_handler: object | None = None
        self._lock = threading.Lock()

    @property
    def captured(self) -> bool:
        with self._lock:
            return self._tk_handler not in (None, 0)

    def capture(self) -> None:
        with self._lock:
            if self._tk_handler not in (None, 0):
                return
            try:
                library = self._load_libx11()
                setter = library.XSetErrorHandler
                try:
                    setter.argtypes = [ctypes.c_void_p]
                    setter.restype = ctypes.c_void_p
                except (AttributeError, TypeError):
                    pass
                previous = setter(None)
                setter(previous)
            except Exception:
                return
            if previous in (None, 0):
                return
            self._libx11 = library
            self._tk_handler = previous

    def restore(self) -> None:
        with self._lock:
            if self._libx11 is None or self._tk_handler in (None, 0):
                return
            try:
                self._libx11.XSetErrorHandler(self._tk_handler)
            except Exception:
                return


class _MpvRealtimeOps:
    """Small direct-call surface reserved for the live scheduler thread."""

    def __init__(self, backend: "MpvBackend") -> None:
        self._backend = backend

    def set_overlay(self, ass_events: str | None) -> None:
        player = self._backend._live_player()
        if player is None:
            return
        try:
            if ass_events is None:
                player.command("osd-overlay", 1, "none", "")
            else:
                player.command("osd-overlay", 1, "ass-events", ass_events)
        except Exception as exc:
            self._backend._callback_error("overlay", exc)

    def set_speed(self, value: float) -> None:
        self._backend._direct_set("speed", float(value))

    def set_pause(self, paused: bool) -> None:
        self._backend._direct_set("pause", "yes" if paused else "no")

    def set_duck(self, gain: float) -> None:
        self._backend.mixer.set_duck_gain(gain)
        state = self._backend.mixer.snapshot()
        self._backend._direct_set("volume", state.video_volume)


class MpvBackend:
    """Non-blocking video adapter owning one python-mpv instance."""

    _MOUSE_BINDINGS = ("MBTN_LEFT", "MBTN_LEFT_DBL", "WHEEL_UP", "WHEEL_DOWN")

    def __init__(self, *, mpv_module, options: Mapping[str, object],
                 bridge: EventBridge, mixer: VolumeMixer,
                 log: Callable[..., None] | object | None = None) -> None:
        self.bridge = bridge
        self.mixer = mixer
        self.mpv_version: tuple[int, int] | None = None
        self._mpv_module = mpv_module
        self._log = log
        self._queue = CommandQueue(maxsize=64)
        self._stopping = threading.Event()
        self._state_lock = threading.Lock()
        self._terminated = False
        self._terminate_done = threading.Event()
        self._terminate_helper: threading.Thread | None = None
        self._terminate_error: BaseException | None = None
        self._session_defaults: dict[str, object] = {}
        self._session_keys: set[str] = set()
        constructor_options = dict(options)
        constructor_options["log_handler"] = self._on_log
        self._player = mpv_module.MPV(**constructor_options)
        try:
            self.mpv_version = parse_mpv_version(str(self._player.mpv_version))
        except Exception:
            self.mpv_version = None
        self.rt = _MpvRealtimeOps(self)
        self._register_callbacks()
        self._command_thread = threading.Thread(
            target=self._command_loop, name="mpv-cmd", daemon=True,
        )
        self._command_thread.start()

    def _live_player(self):
        with self._state_lock:
            return None if self._terminated or self._stopping.is_set() else self._player

    def _callback_error(self, where: str, exc: BaseException) -> None:
        try:
            self.bridge.post("adapter-error", {"where": where, "detail": str(exc)})
        except Exception:
            pass

    def _on_log(self, level, component, message) -> None:
        try:
            text = str(message).rstrip()
            self.bridge.post("log", text)
            if callable(self._log):
                self._log(level, component, text)
            elif self._log is not None:
                method = getattr(self._log, "warning", None)
                if method is not None:
                    method("mpv %s: %s", component, text)
        except Exception:
            pass

    @staticmethod
    def _event_value(event) -> int | None:
        try:
            value = event.event_id
            return int(getattr(value, "value", value))
        except (AttributeError, TypeError, ValueError):
            return None

    def _event_id(self, name: str) -> int | None:
        try:
            value = getattr(self._mpv_module.MpvEventID, name)
            return int(getattr(value, "value", value))
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _end_reason(event) -> str | None:
        reasons = {0: "eof", 1: "restart", 2: "stop", 3: "quit", 4: "error", 5: "redirect"}
        try:
            return reasons.get(int(event.data.reason), str(event.data.reason))
        except (AttributeError, TypeError, ValueError):
            try:
                payload = event.as_dict()
                raw = payload.get("event", payload).get("reason")
                return reasons.get(int(raw), str(raw))
            except Exception:
                return None

    def _on_event(self, event) -> None:
        try:
            event_id = self._event_value(event)
            if event_id is None:
                return
            if event_id == self._event_id("FILE_LOADED"):
                self.bridge.post("file-loaded")
            elif event_id == self._event_id("END_FILE"):
                self.bridge.post("end-file", {"reason": self._end_reason(event)})
            elif event_id == self._event_id("PLAYBACK_RESTART"):
                self.bridge.post("playback-restart")
        except Exception:
            pass

    def _observe(self, expected_name: str):
        def callback(_name, value) -> None:
            try:
                self.bridge.set_latest(expected_name, value, time.monotonic())
            except Exception:
                pass
        return callback

    def _mouse_callback(self, binding: str):
        def callback(*args) -> None:
            try:
                state = args[0] if args else ""
                self.bridge.post("mouse", (binding, state))
            except Exception:
                pass
        return callback

    def _register_callbacks(self) -> None:
        for name in EventBridge.LATEST:
            self._player.observe_property(name, self._observe(name))
        self._player.register_event_callback(self._on_event)
        for binding in self._MOUSE_BINDINGS:
            self._player.register_key_binding(binding, self._mouse_callback(binding), "force")

    def _command_loop(self) -> None:
        while not self._stopping.is_set():
            command = self._queue.get(0.1)
            if command is None:
                continue
            try:
                command()
            except Exception as exc:
                self._callback_error("command", exc)

    def _enqueue(self, fn: Callable[[], None], *, key: str | None = None) -> bool:
        if self._stopping.is_set():
            return False
        accepted = self._queue.put(fn, key=key)
        if not accepted:
            self.bridge.post("busy")
        return accepted

    @staticmethod
    def _option_name(name: str) -> str:
        return str(name).replace("_", "-")

    def load(self, uri: str, *, paused: bool, start: float | None = None,
             options: Mapping[str, str] | None = None) -> None:
        requested = {self._option_name(key): value for key, value in (options or {}).items()}
        requested["pause"] = "yes" if paused else "no"
        if start is not None:
            requested["start"] = float(start)

        def run() -> None:
            player = self._live_player()
            if player is None:
                return
            for key in self._session_keys:
                player[key] = self._session_defaults[key]
            for key, value in requested.items():
                if key not in self._session_defaults:
                    self._session_defaults[key] = player[key]
                player[key] = value
            self._session_keys = set(requested)
            player.command("loadfile", str(uri), "replace")

        self._enqueue(run, key="load")

    def stop(self) -> None:
        self._enqueue(lambda: self._player.command("stop"), key="transport")

    def set_pause(self, paused: bool) -> None:
        value = "yes" if paused else "no"
        self._enqueue(lambda: self._player.command("set", "pause", value), key="pause")

    def seek(self, seconds: float, mode: str = "exact") -> None:
        modes = {
            "exact": "absolute+exact",
            "keyframes": "absolute+keyframes",
            "relative": "relative+exact",
        }
        if mode not in modes:
            raise ValueError(f"unsupported seek mode: {mode!r}")
        self._enqueue(
            lambda: self._player.command("seek", float(seconds), modes[mode]), key="seek",
        )

    def apply_mix(self) -> None:
        state = self.mixer.snapshot()
        if state.owner != "cmd":
            return

        def run() -> None:
            self._player.command("set", "volume", state.video_volume)
            self._player.command("set", "mute", "yes" if state.muted else "no")
        self._enqueue(run, key="mix")

    def add_external_audio(self, path: str, title: str) -> None:
        self._enqueue(lambda: self._player.command("audio-add", path, "auto", title))

    def select_audio(self, track_id: int | None) -> None:
        value = "no" if track_id is None else int(track_id)
        self._enqueue(lambda: self._player.command("set", "aid", value), key="audio")

    def add_subtitles(self, path: str, title: str) -> None:
        self._enqueue(lambda: self._player.command("sub-add", path, "select", title))

    def reload_subtitles(self) -> None:
        self._enqueue(lambda: self._player.command("sub-reload"))

    def set_subtitles_visible(self, visible: bool) -> None:
        value = "yes" if visible else "no"
        self._enqueue(lambda: self._player.command("set", "sub-visibility", value), key="subs")

    def screenshot(self, path: str) -> None:
        def reply(error, _result) -> None:
            try:
                if error:
                    self.bridge.post("snapshot-failed", {"path": path, "detail": str(error)})
                else:
                    self.bridge.post("snapshot-saved", {"path": path})
            except Exception:
                pass

        def run() -> None:
            self._player.command_async(
                "screenshot-to-file", path, "video", callback=reply,
            )
        self._enqueue(run)

    def set_af(self, value: str) -> bool:
        return self._enqueue(lambda: self._player.command("set", "af", value), key="af")

    def register_stream_protocol(self, name: str, open_adapter: Callable) -> None:
        self._enqueue(lambda: self._player.register_stream_protocol(name, open_adapter))

    def _direct_set(self, name: str, value: object) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("set", name, value)
        except Exception as exc:
            self._callback_error(f"direct-{name}", exc)

    def terminate(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        with self._state_lock:
            player = self._player
            if self._terminated or player is None:
                return False
        if threading.current_thread() is getattr(player, "_event_thread", None):
            self.bridge.post("terminate-refused")
            return False
        if threading.current_thread() is self._command_thread:
            self.bridge.post("terminate-refused")
            return False
        self._stopping.set()
        self._queue.close()
        self._command_thread.join(max(0.0, deadline - time.monotonic()))
        if self._command_thread.is_alive():
            return False

        def stop_player() -> None:
            try:
                player.terminate()
            except Exception as exc:
                self._terminate_error = exc
                self._callback_error("terminate", exc)
            finally:
                self._terminate_done.set()

        with self._state_lock:
            if self._terminate_helper is None:
                self._terminate_helper = threading.Thread(
                    target=stop_player, name="mpv-stop", daemon=True,
                )
                self._terminate_helper.start()
            helper = self._terminate_helper
        helper.join(max(0.0, deadline - time.monotonic()))
        if not self._terminate_done.is_set():
            return False
        with self._state_lock:
            self._terminated = True
            self._player = None
        return self._terminate_error is None


def create_video_backend(*, wid: int, bridge: EventBridge, mixer: VolumeMixer,
                         vo_profile: str, mpv_module,
                         sys_platform: str = sys.platform, log=None) -> MpvBackend:
    """Construct the single video mpv instance for a Tk-owned window id."""
    options = build_mpv_options(
        "video", sys_platform=sys_platform, wid=wid, vo_profile=vo_profile,
    )
    return MpvBackend(
        mpv_module=mpv_module, options=options, bridge=bridge, mixer=mixer, log=log,
    )


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


class MpvVoiceBackend:
    """Second, video-less mpv instance that plays the translated voice clips.

    Owned exclusively by the live scheduler thread, so ordinary commands are
    issued directly (loadfile and set are non-blocking in libmpv). Only
    terminate, which blocks, runs on a helper thread, and never on the mpv event
    thread. It shares the video EventBridge but writes only namespaced values
    (extra_latest) and voice-prefixed events, so it can never clobber the
    player's own state.
    """

    def __init__(self, *, mpv_module, options: Mapping[str, object],
                 bridge: EventBridge,
                 log: Callable[..., None] | None = None) -> None:
        self.bridge = bridge
        self.mpv_version: tuple[int, int] | None = None
        self._mpv_module = mpv_module
        self._log = log
        self._state_lock = threading.Lock()
        self._terminated = False
        self._terminate_done = threading.Event()
        self._terminate_helper: threading.Thread | None = None
        self._terminate_error: BaseException | None = None
        constructor_options = dict(options)
        constructor_options["log_handler"] = self._on_log
        self._player = mpv_module.MPV(**constructor_options)
        try:
            self.mpv_version = parse_mpv_version(str(self._player.mpv_version))
        except Exception:
            self.mpv_version = None
        self._register_callbacks()

    def _live_player(self):
        with self._state_lock:
            return None if self._terminated else self._player

    def _callback_error(self, where: str, exc: BaseException) -> None:
        try:
            self.bridge.post("voice-error", {"where": where, "detail": str(exc)})
        except Exception:
            pass

    def _on_log(self, level, component, message) -> None:
        try:
            if callable(self._log):
                self._log(level, component, str(message).rstrip())
        except Exception:
            pass

    def _event_id(self, name: str) -> int | None:
        try:
            value = getattr(self._mpv_module.MpvEventID, name)
            return int(getattr(value, "value", value))
        except (AttributeError, TypeError, ValueError):
            return None

    def _observe_time(self, _name, value) -> None:
        try:
            self.bridge.extra_latest("voice-time-pos", value, time.monotonic())
        except Exception:
            pass

    def _on_event(self, event) -> None:
        try:
            event_id = MpvBackend._event_value(event)
            if event_id is None:
                return
            if event_id == self._event_id("END_FILE"):
                self.bridge.post("voice-end-file")
        except Exception:
            pass

    def _register_callbacks(self) -> None:
        self._player.observe_property("time-pos", self._observe_time)
        self._player.register_event_callback(self._on_event)

    def preload(self, path: str, *, skip_s: float = 0.0) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("set", "pause", "yes")
            player.command("set", "start", max(0.0, float(skip_s)))
            player.command("loadfile", str(path), "replace")
        except Exception as exc:
            self._callback_error("preload", exc)

    def start(self, speed: float) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("set", "speed", max(0.01, float(speed)))
            player.command("set", "pause", "no")
        except Exception as exc:
            self._callback_error("start", exc)

    def set_pause(self, paused: bool) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("set", "pause", "yes" if paused else "no")
        except Exception as exc:
            self._callback_error("pause", exc)

    def stop(self) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("stop")
        except Exception as exc:
            self._callback_error("stop", exc)

    def set_volume(self, value: float) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("set", "volume", min(130.0, max(0.0, float(value))))
        except Exception as exc:
            self._callback_error("volume", exc)

    def set_speed(self, x: float) -> None:
        player = self._live_player()
        if player is None:
            return
        try:
            player.command("set", "speed", max(0.01, float(x)))
        except Exception as exc:
            self._callback_error("speed", exc)

    def terminate(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        with self._state_lock:
            player = self._player
            if self._terminated or player is None:
                return False
        if threading.current_thread() is getattr(player, "_event_thread", None):
            self.bridge.post("voice-terminate-refused")
            return False

        def stop_player() -> None:
            try:
                player.terminate()
            except Exception as exc:
                self._terminate_error = exc
                self._callback_error("terminate", exc)
            finally:
                self._terminate_done.set()

        with self._state_lock:
            if self._terminate_helper is None:
                self._terminate_helper = threading.Thread(
                    target=stop_player, name="mpv-voice-stop", daemon=True,
                )
                self._terminate_helper.start()
            helper = self._terminate_helper
        helper.join(max(0.0, deadline - time.monotonic()))
        if not self._terminate_done.is_set():
            return False
        with self._state_lock:
            self._terminated = True
            self._player = None
        return self._terminate_error is None


def create_voice_backend(*, bridge: EventBridge, mpv_module,
                         sys_platform: str = sys.platform,
                         log=None) -> MpvVoiceBackend:
    """Construct the second, video-less mpv instance for translated voice clips."""
    options = build_mpv_options(
        "voice", sys_platform=sys_platform, wid=None, vo_profile="none",
    )
    return MpvVoiceBackend(
        mpv_module=mpv_module, options=options, bridge=bridge, log=log,
    )


class InMemoryVoice:
    """VoiceBackend test double that records every operation in order."""

    def __init__(self, *, mpv_version: tuple[int, int] | None = None) -> None:
        self.mpv_version = mpv_version
        self.calls: list[tuple[Any, ...]] = []
        self.terminated = False
        self._lock = threading.Lock()

    def _record(self, name: str, *args: object) -> None:
        with self._lock:
            self.calls.append((name, *args))

    def preload(self, path: str, *, skip_s: float = 0.0) -> None:
        self._record("preload", path, float(skip_s))

    def start(self, speed: float) -> None:
        self._record("start", float(speed))

    def set_pause(self, paused: bool) -> None:
        self._record("set_pause", bool(paused))

    def stop(self) -> None:
        self._record("stop")

    def set_volume(self, value: float) -> None:
        self._record("set_volume", float(value))

    def set_speed(self, x: float) -> None:
        self._record("set_speed", float(x))

    def terminate(self, timeout_s: float) -> bool:
        if self.terminated:
            return False
        self.terminated = True
        self._record("terminate", float(timeout_s))
        return True
