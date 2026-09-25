"""Pure logic of the integrated player (spec 2.2, 2.3, 3.7).

No Tk, no mpv: time format, seek-bar maths, audio track picking, snapshot
names, the reflow of the controls, the key map and its focus filter, the
mouse mapping and the playlist groups. The controller state machine lives
here too (PlayerController, driven by a PlayerBackend).
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from .output_media import segments_to_srt
from .player_engine import BridgeSnapshot
from .player_settings import (
    PLAYER_AUDIO_KEY,
    PLAYER_MUTED_KEY,
    PLAYER_SUBS_VISIBLE_KEY,
    PLAYER_VOLUME_KEY,
    PlayerSettings,
)


# Stable controller/backend message codes mapped to translated UI keys.  Keeping
# the indirection here prevents playback threads from ever touching UI strings.
STATUS_KEYS: dict[str, str] = {
    "idle": "player_idle_hint",
    "initializing": "player_initializing",
    "now-playing": "player_now_playing",
    "nothing-loaded": "player_nothing_loaded",
    "snapshot-saved": "player_snapshot_saved",
    "snapshot-failed": "player_snapshot_failed",
    "load-error": "player_err_load",
    "video-output-error": "player_err_video_output",
    "vo-fallback": "player_vo_fallback_used",
    "busy": "player_busy",
}


@dataclass(frozen=True)
class MediaItem:
    path: str
    kind: str                         # source | dubbed | live
    title: str
    source_path: str | None = None    # original, when it can be added as external audio
    srt_path: str | None = None
    temp: bool = False                # owned temp file (URL editor flow)


@dataclass(frozen=True)
class PlayerState:
    status: str
    item: MediaItem | None
    position: float
    duration: float | None
    volume: int
    muted: bool
    audio: str
    ab_available: bool
    subs_available: bool
    subs_visible: bool
    message_key: str | None = None
    message_params: dict = field(default_factory=dict)


class PlayerController:
    """Tk-thread state machine backed by a non-blocking PlayerBackend."""

    def __init__(self, backend, settings: PlayerSettings, *,
                 on_change: Callable[[PlayerState], None],
                 save: Callable[[dict], None]) -> None:
        self._backend = backend
        self._settings = settings
        self._on_change = on_change
        self._save = save
        self._playlist: list[MediaItem] = []
        self._playlist_index: int | None = None
        self._pending_load: tuple[MediaItem, bool, float] | None = None
        self._paused = True
        self._dubbed_track: int | None = None
        self._original_track: int | None = None
        self.state = PlayerState(
            status="idle" if backend is not None else "initializing",
            item=None,
            position=0.0,
            duration=None,
            volume=settings.volume,
            muted=settings.muted,
            audio=settings.audio,
            ab_available=False,
            subs_available=False,
            subs_visible=settings.subs_visible,
        )
        if backend is not None:
            self._apply_initial_mix(backend)

    @property
    def playlist(self) -> tuple[MediaItem, ...]:
        return tuple(self._playlist)

    def _apply_initial_mix(self, backend) -> None:
        backend.mixer.set_user_volume(self.state.volume)
        backend.mixer.set_muted(self.state.muted)
        backend.apply_mix()

    def _update(self, **changes) -> None:
        new_state = replace(self.state, **changes)
        if new_state != self.state:
            self.state = new_state
            self._on_change(new_state)

    def attach_backend(self, backend) -> None:
        self._backend = backend
        self._apply_initial_mix(backend)
        pending = self._pending_load
        self._pending_load = None
        if pending is None:
            self._update(status="idle")
            return
        item, paused, start = pending
        backend.load(item.path, paused=paused, start=start, options=None)

    def detach_backend(self) -> None:
        """Detach a failed backend and retain the current load for its replacement."""
        self._backend = None
        if self.state.item is not None:
            self._pending_load = (
                self.state.item, self._paused, max(0.0, float(self.state.position)))

    def report_error(self, message_key: str) -> None:
        self._pending_load = None
        self._update(status="error", message_key=message_key, message_params={})

    def load(self, item: MediaItem, *, paused: bool = True, start: float = 0.0) -> None:
        start = max(0.0, float(start))
        self._paused = bool(paused)
        self._dubbed_track = None
        self._original_track = None
        for index, candidate in enumerate(self._playlist):
            if candidate.path == item.path:
                self._playlist_index = index
                break
        self._update(
            status="loading",
            item=item,
            position=start,
            duration=None,
            audio="dubbed",
            ab_available=False,
            subs_available=bool(item.srt_path),
            message_key=None,
            message_params={},
        )
        if self._backend is None:
            self._pending_load = (item, bool(paused), start)
            return
        self._pending_load = None
        self._backend.load(item.path, paused=bool(paused), start=start, options=None)

    def set_playlist(self, items: Sequence[MediaItem], index: int | None = None) -> None:
        self._playlist = list(items)
        if index is None:
            self._playlist_index = None
        elif 0 <= index < len(self._playlist):
            self._playlist_index = int(index)
        else:
            raise IndexError("playlist index out of range")

    def play_pause(self) -> None:
        if self.state.item is None or self._backend is None:
            return
        self._paused = not self._paused
        self._backend.set_pause(self._paused)
        self._update(status="paused" if self._paused else "playing")

    def stop(self) -> None:
        if self._backend is not None:
            self._backend.stop()
        self._pending_load = None
        self._paused = True
        self._dubbed_track = None
        self._original_track = None
        self._update(
            status="idle",
            item=None,
            position=0.0,
            duration=None,
            audio="dubbed",
            ab_available=False,
            subs_available=False,
            message_key=None,
            message_params={},
        )

    def _move(self, delta: int) -> None:
        if not self._playlist:
            return
        index = self._playlist_index
        if index is None and self.state.item is not None:
            index = next((i for i, item in enumerate(self._playlist)
                          if item.path == self.state.item.path), None)
        if index is None:
            index = 0 if delta > 0 else len(self._playlist) - 1
        target = index + delta
        if 0 <= target < len(self._playlist):
            self._playlist_index = target
            self.load(self._playlist[target], paused=True)

    def next(self) -> None:
        self._move(1)

    def previous(self) -> None:
        self._move(-1)

    def seek(self, seconds: float, *, dragging: bool = False) -> None:
        if self.state.item is None or self._backend is None:
            return
        target = max(0.0, float(seconds))
        self._backend.seek(target, "keyframes" if dragging else "exact")
        self._update(position=target)

    def seek_relative(self, delta: float) -> None:
        if self.state.item is None or self._backend is None:
            return
        self._backend.seek(float(delta), "relative")

    def set_volume(self, value: int) -> None:
        value = min(130, max(0, int(value)))
        if value == self.state.volume:
            return
        if self._backend is not None:
            self._backend.mixer.set_user_volume(value)
            self._backend.apply_mix()
        self._update(volume=value)
        self._save({PLAYER_VOLUME_KEY: value})

    def toggle_mute(self) -> None:
        muted = not self.state.muted
        if self._backend is not None:
            self._backend.mixer.set_muted(muted)
            self._backend.apply_mix()
        self._update(muted=muted)
        self._save({PLAYER_MUTED_KEY: muted})

    def select_audio(self, which: str) -> bool:
        track_id = {"dubbed": self._dubbed_track,
                    "original": self._original_track}.get(which)
        if track_id is None or self._backend is None:
            return False
        self._backend.select_audio(track_id)
        self._update(audio=which)
        self._save({PLAYER_AUDIO_KEY: which})
        return True

    def set_subtitles_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if self._backend is not None:
            self._backend.set_subtitles_visible(visible)
        self._update(subs_visible=visible)
        self._save({PLAYER_SUBS_VISIBLE_KEY: visible})

    def show_segments_as_subtitles(self, segments: Sequence[dict], srt_path: Path) -> None:
        path = Path(srt_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(segments_to_srt(tuple(segments)), encoding="utf-8")
        if self._backend is not None:
            self._backend.add_subtitles(str(path), "Translated")
            self._backend.reload_subtitles()
            self._backend.set_subtitles_visible(self.state.subs_visible)
        item = self.state.item
        if item is not None:
            item = replace(item, srt_path=str(path))
        self._update(item=item, subs_available=True)

    def update_segments_as_subtitles(self, segments: Sequence[dict], srt_path: Path) -> None:
        """Rewrite the active editor preview subtitle and reload it in mpv."""
        path = Path(srt_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(segments_to_srt(tuple(segments)), encoding="utf-8")
        if self._backend is not None:
            self._backend.reload_subtitles()
        item = self.state.item
        if item is not None:
            self._update(item=replace(item, srt_path=str(path)), subs_available=True)

    def snapshot(self, dest_dir: Path, now: datetime) -> Path:
        if self.state.item is None or self._backend is None:
            raise RuntimeError("no media loaded")
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_path(dest_dir, self.state.item.title, self.state.position, now)
        self._backend.screenshot(str(path))
        return path

    def remove_items(self, paths: Sequence[str]) -> None:
        removed = set(paths)
        self._playlist = [item for item in self._playlist if item.path not in removed]
        self._playlist_index = next(
            (index for index, item in enumerate(self._playlist)
             if self.state.item is not None and item.path == self.state.item.path),
            None,
        )
        if (self.state.item is not None and self.state.item.kind == "source"
                and self.state.item.path in removed):
            self.stop()

    def release_for_job(self) -> bool:
        if self.state.item is None or self.state.item.kind != "dubbed":
            return False
        self.stop()
        return True

    def release(self, path: str) -> bool:
        item = self.state.item
        if item is None or path not in (item.path, item.source_path):
            return False
        self.stop()
        return True

    @staticmethod
    def is_released(latest: Mapping) -> bool:
        value = latest.get("idle-active")
        if isinstance(value, tuple) and len(value) == 2:
            value = value[0]
        return value is True

    def apply_events(self, snapshot: BridgeSnapshot, clock_now: float | None) -> None:
        changed = snapshot.changed
        tracks_value = changed.get("track-list")
        if tracks_value is not None:
            self._dubbed_track, self._original_track = pick_audio_track_ids(tracks_value[0])
        duration_value = changed.get("duration")
        duration = self.state.duration if duration_value is None else duration_value[0]
        pause_value = changed.get("pause")
        if pause_value is not None:
            self._paused = bool(pause_value[0])
        status = self.state.status
        if self.state.item is not None and pause_value is not None:
            status = "paused" if self._paused else "playing"
        item = self.state.item
        for event in snapshot.events:
            if event.kind == "file-loaded" and item is not None and self._backend is not None:
                if item.source_path and self._original_track is None:
                    self._backend.add_external_audio(item.source_path, "Original")
                if item.srt_path:
                    self._backend.add_subtitles(item.srt_path, "Translated")
                    self._backend.set_subtitles_visible(self.state.subs_visible)
            elif event.kind == "end-file" and item is not None:
                reason = event.payload.get("reason") if isinstance(event.payload, dict) else event.payload
                status = "paused" if reason in (None, "eof", "stop") else "error"
        available = self._dubbed_track is not None and self._original_track is not None
        audio = self.state.audio if available else "dubbed"
        if (available and tracks_value is not None and self._settings.audio == "original"
                and self.state.audio != "original" and self._backend is not None):
            self._backend.select_audio(self._original_track)
            audio = "original"
        self._update(
            status=status,
            position=self.state.position if clock_now is None else max(0.0, float(clock_now)),
            duration=duration,
            audio=audio,
            ab_available=available,
            subs_available=bool(item and item.srt_path),
        )


# -- time and seek maths ----------------------------------------------------

def format_clock(seconds: float | None, *, hours: bool) -> str:
    """``MM:SS`` or ``H:MM:SS``; dashes when the time is unknown."""
    if seconds is None:
        return "--:--:--" if hours else "--:--"
    total = max(0, int(seconds))
    if hours:
        return f"{total // 3600}:{total // 60 % 60:02d}:{total % 60:02d}"
    return f"{total // 60:02d}:{total % 60:02d}"


def x_to_seconds(x: float, width: float, start: float, end: float) -> float:
    """Seek-bar pixel to media time, clamped to the bar."""
    if width <= 0 or end <= start:
        return start
    return start + min(max(x, 0.0), width) / width * (end - start)


def seconds_to_x(t: float, width: float, start: float, end: float) -> float:
    """Media time to seek-bar pixel, clamped to the bar."""
    if width <= 0 or end <= start:
        return 0.0
    return (min(max(t, start), end) - start) / (end - start) * width


def pick_audio_track_ids(track_list: list[dict] | None) -> tuple[int | None, int | None]:
    """(dubbed, original) audio track ids: by title, then by external flag, then order."""
    audio = [t for t in track_list or [] if isinstance(t, dict) and t.get("type") == "audio"]
    by_title = {str(t.get("title", "")).lower(): t.get("id") for t in audio}
    if "dubbed" in by_title or "original" in by_title:
        return by_title.get("dubbed"), by_title.get("original")
    external = [t.get("id") for t in audio if t.get("external")]
    internal = [t.get("id") for t in audio if not t.get("external")]
    if external and internal:
        return internal[0], external[0]
    ids = [t.get("id") for t in audio]
    return (ids[0] if ids else None), (ids[1] if len(ids) > 1 else None)


# -- snapshot ----------------------------------------------------------------

_UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def snapshot_path(dest_dir: Path, media_title: str, position: float, now: datetime,
                  exists: Callable[[Path], bool] = os.path.exists) -> Path:
    """``<stem>_<HH-MM-SS>.png`` in ``dest_dir``; ``_2``, ``_3`` ... on collisions."""
    safe = _UNSAFE_NAME.sub("_", media_title or "")
    stem = os.path.splitext(safe)[0].strip(" .")[:80] or f"snapshot_{now:%Y%m%d-%H%M%S}"
    total = max(0, int(position or 0))
    base = f"{stem}_{total // 3600:02d}-{total // 60 % 60:02d}-{total % 60:02d}"
    candidate = Path(dest_dir) / f"{base}.png"
    number = 2
    while exists(candidate):
        candidate = Path(dest_dir) / f"{base}_{number}.png"
        number += 1
    return candidate


# -- reflow ------------------------------------------------------------------

CONTROLS = frozenset({"previous", "back", "stop", "play_pause", "forward", "next",
                      "snapshot", "open_folder", "volume", "fullscreen", "audio",
                      "subtitles", "playlist", "live"})


def controls_visible(width_px: int, scale: float) -> frozenset[str]:
    """Controls shown at this pane width (spec 2.3): the hidden ones keep their keys."""
    hidden: set[str] = set()
    if width_px < 440 * scale:
        hidden |= {"back", "forward"}
    if width_px < 380 * scale:
        hidden |= {"snapshot", "open_folder"}
    return CONTROLS - hidden


def editor_geometry(right_x: int, right_w: int, main_x: int, main_y: int,
                    main_h: int, screen_w: int, screen_h: int) -> tuple[int, int, int, int]:
    """Return a right-column-anchored editor rectangle clamped to the screen."""
    screen_w = max(1, int(screen_w))
    screen_h = max(1, int(screen_h))
    width = min(900, max(int(right_w), 520), max(1, screen_w - 40))
    height = min(max(1, int(main_h)), max(1, screen_h - 80))
    x = min(max(0, int(right_x)), max(0, screen_w - width))
    y = min(max(0, int(main_y)), max(0, screen_h - height))
    return x, y, width, height


# -- keyboard and mouse -------------------------------------------------------

PLAYER_KEYS: dict[str, str] = {
    "space": "play_pause", "Left": "back_10", "Right": "forward_10",
    "Up": "volume_up", "Down": "volume_down", "m": "mute", "f": "fullscreen",
    "Escape": "exit_fullscreen", "s": "snapshot", "o": "open_folder",
    "n": "next", "p": "previous",   # the n/p pair follows VLC
}

# Widget classes whose own bindings use these keys and do not return "break":
# a global action would double-fire (space on Start = start a job AND toggle play).
_INTERACTIVE_CLASSES = frozenset({
    "Entry", "TEntry", "Text", "Listbox", "TCombobox", "Spinbox", "TSpinbox", "Treeview",
    "Button", "TButton", "Checkbutton", "TCheckbutton", "Radiobutton", "TRadiobutton",
    "Scale", "TScale", "Menubutton", "TMenubutton",
})


def handles_player_key(widget_class: str | None, keysym: str, *, focus_in_player: bool) -> bool:
    """True when the main window's <Key> handler may run the player action (spec 3.7)."""
    if keysym not in PLAYER_KEYS:
        return False
    if focus_in_player:
        return True
    return widget_class not in _INTERACTIVE_CLASSES


def mouse_action(name: str, state: str) -> str | None:
    """Map a python-mpv key-binding callback to an action, deciding on ``state[0]`` only.

    0.41 sends "dm-", "um-", "p--"; 0.34.1 and 0.35.1 send "dm", "um", "p-" ("pm" for
    injected keypresses). A click acts on "u", a double click on "p"/"d", a wheel
    notch (real: "d" then "u") on "p"/"d" only.
    """
    phase = state[:1]
    if name == "MBTN_LEFT":
        return "toggle_pause" if phase == "u" else None
    if name == "MBTN_LEFT_DBL":
        return "toggle_fullscreen" if phase in ("p", "d") else None
    if name in ("WHEEL_UP", "WHEEL_DOWN"):
        if phase in ("p", "d"):
            return "volume_up" if name == "WHEEL_UP" else "volume_down"
    return None


# -- playlist ------------------------------------------------------------------

def playlist_groups(sources: Sequence[MediaItem], results: Sequence[MediaItem], *,
                    job_running: bool) -> list[tuple[str, list[MediaItem], bool]]:
    """The two popup groups; results are disabled while a job may overwrite one."""
    return [("player_playlist_sources", list(sources), True),
            ("player_playlist_results", list(results), not job_running)]
