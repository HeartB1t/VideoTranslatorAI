"""Pure logic of the integrated player (spec 2.2, 2.3, 3.7).

No Tk, no mpv: time format, seek-bar maths, audio track picking, snapshot
names, the reflow of the controls, the key map and its focus filter, the
mouse mapping and the playlist groups. The controller state machine lives
here too (PlayerController, driven by a PlayerBackend).
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MediaItem:
    path: str
    kind: str                         # source | dubbed | live
    title: str
    source_path: str | None = None    # original, when it can be added as external audio
    srt_path: str | None = None
    temp: bool = False                # owned temp file (URL editor flow)


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
