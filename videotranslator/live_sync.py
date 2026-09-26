"""Sync timing for live mode (design 5). Pure, fake-clock friendly.

This module carries the file-side pieces used by P4: the latency-budget helpers
(``recommended_delay_s``, ``derive_live_timing``, ``live_distance_s``) and the
``FilePacer`` that paces a local file played in real time. The stream-side
``EdgeEstimator`` and ``DelayController`` land with P6.
"""

from __future__ import annotations

from dataclasses import dataclass


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _is_gpu(device: str) -> bool:
    return device.startswith("cuda") or device == "gpu"


def _engine_class(engine: str) -> str:
    return "ollama" if engine in ("ollama", "llm_ollama") else "marian"


# "voice ready" and "caption ready" p95 rows from the latency budget (design 5.8),
# keyed by (device class, engine class).
_VOICE_READY = {
    ("gpu", "marian"): 3.85, ("gpu", "ollama"): 4.45,
    ("cpu", "marian"): 5.8, ("cpu", "ollama"): 5.8,
}
_CAPTION_READY = {
    ("gpu", "marian"): 2.35, ("gpu", "ollama"): 2.95,
    ("cpu", "marian"): 4.3, ("cpu", "ollama"): 4.3,
}


def recommended_delay_s(*, device: str, dub: bool) -> float:
    """Default target delay when ``live_delay_s`` is absent (design 5.8, Q8)."""
    if _is_gpu(device):
        return 12.0 if dub else 9.0
    return 15.0 if dub else 11.0


def live_distance_s(max_gap_s: float) -> float:
    """Live-mode distance behind the edge from the burst gap: clamp(1.5*gap, 2, 8)."""
    return _clamp(1.5 * max_gap_s, 2.0, 8.0)


@dataclass(frozen=True)
class LiveTiming:
    umax_s: float
    hold_s: float
    min_ahead_s: float
    resume_ahead_s: float


def derive_live_timing(delay_s: float, *, mode: str, device: str, engine: str,
                       dub: bool) -> LiveTiming:
    """Derive per-session timing from the target delay (design 5.8)."""
    key = ("gpu" if _is_gpu(device) else "cpu", _engine_class(engine))
    if mode == "live":
        umax = 5.0
    else:
        ready_p95 = (_VOICE_READY if dub else _CAPTION_READY)[key]
        umax = _clamp(delay_s - ready_p95 - 1.0, 4.0, 8.0)
    hold = 1.5 if mode != "live" else 0.4
    min_ahead = 8.0 if dub else 4.0
    return LiveTiming(umax_s=umax, hold_s=hold, min_ahead_s=min_ahead,
                      resume_ahead_s=min_ahead)


@dataclass(frozen=True)
class SyncAction:
    kind: str  # none | speed | pause | resume | seek | reload
    value: float | None = None


_NONE = SyncAction("none")
_PAUSE = SyncAction("pause")
_RESUME = SyncAction("resume")

# Pause when the translated coverage gets within this many seconds of the
# playhead (design 5.5).
_PAUSE_MARGIN_S = 2.0


class FilePacer:
    """Pace a local file played in real time (design 5.5).

    Delayed mode pauses when the translated coverage (``ready_until``) gets
    within 2 s ahead of the playhead and the source is not finished, resuming at
    ``resume_ahead_s``. Live mode never pauses. The pacer never changes speed on
    files, so ``step`` only ever returns pause, resume or none.
    """

    def __init__(self, *, mode: str, min_ahead_s: float, resume_ahead_s: float) -> None:
        self._mode = mode
        self._min_ahead = min_ahead_s
        self._resume_ahead = resume_ahead_s

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def step(self, *, player: float | None, ready_until: float, source_done: bool,
             user_paused: bool, self_paused: bool) -> SyncAction:
        if player is None or user_paused:
            return _NONE
        if self._mode == "live":
            # Never pauses; only lifts a pause left over from a mode switch.
            return _RESUME if self_paused else _NONE
        ahead = ready_until - player
        if self_paused:
            if source_done or ahead >= self._resume_ahead:
                return _RESUME
            return _NONE
        if not source_done and ahead < _PAUSE_MARGIN_S:
            return _PAUSE
        return _NONE
