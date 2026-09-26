"""Sync timing for live mode (design 5). Pure, fake-clock friendly.

This module carries the file-side pieces used by P4: the latency-budget helpers
(``recommended_delay_s``, ``derive_live_timing``, ``live_distance_s``) and the
``FilePacer`` that paces a local file played in real time. The stream-side
``EdgeEstimator`` and ``DelayController`` land with P6.
"""

from __future__ import annotations

from collections import deque
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


# --- Stream-side sync (design 5.2, 5.3, 5.4). Pure; used by P6. -------------

@dataclass(frozen=True)
class EdgeEstimate:
    observed: float | None   # end of the last decoded block (session time)
    linear: float | None     # now + max(edge_i - mono_i) over the window
    effective: float | None  # linear unless stalled, then observed
    stalled: bool
    max_gap_s: float


class EdgeEstimator:
    """Turn the HLS burst sawtooth into a smooth edge line (design 5.2)."""

    def __init__(self, *, window_s: float = 60.0, burst_gap_s: float = 0.5,
                 default_gap_s: float = 6.0, min_gaps: int = 3,
                 stall_factor: float = 2.0, warmup_s: float = 10.0) -> None:
        self._window_s = window_s
        self._burst_gap_s = burst_gap_s
        self._default_gap_s = default_gap_s
        self._min_gaps = min_gaps
        self._stall_factor = stall_factor
        self._warmup_s = warmup_s
        self.reset(0.0)

    def reset(self, mono: float) -> None:
        self._obs: deque[tuple[float, float]] = deque()
        self._gaps: deque[tuple[float, float]] = deque()
        self._last_block_mono: float | None = None
        self._reset_mono = mono

    def observe(self, edge: float, mono: float) -> None:
        if self._last_block_mono is not None:
            idle = mono - self._last_block_mono
            if idle > self._burst_gap_s and mono - self._reset_mono >= self._warmup_s:
                self._gaps.append((idle, mono))
        self._obs.append((edge, mono))
        self._last_block_mono = mono
        self._prune(mono)

    def _prune(self, mono: float) -> None:
        cutoff = mono - self._window_s
        while self._obs and self._obs[0][1] < cutoff:
            self._obs.popleft()
        while self._gaps and self._gaps[0][1] < cutoff:
            self._gaps.popleft()

    def estimate(self, mono: float) -> EdgeEstimate:
        self._prune(mono)
        observed = self._obs[-1][0] if self._obs else None
        linear = mono + max(e - m for e, m in self._obs) if self._obs else None
        if len(self._gaps) >= self._min_gaps:
            max_gap = max(g for g, _ in self._gaps)
        else:
            max_gap = self._default_gap_s
        if self._last_block_mono is None:
            stalled = False
        else:
            stalled = (mono - self._last_block_mono) > self._stall_factor * max_gap
        if observed is None:
            effective = None
        else:
            effective = observed if stalled else linear
        return EdgeEstimate(observed, linear, effective, stalled, max_gap)


class DelayController:
    """Keep a stream at the target lag with speed nudges, seeks or pauses
    (design 5.3 delayed, 5.4 live). Pure; a new action is held back until the
    band changes or ``hold_s`` passes (hysteresis)."""

    def __init__(self, *, mode: str, delay_s: float, tolerance_s: float = 0.5,
                 band_s: float = 3.0, max_nudge: float = 0.03, hold_s: float = 2.0,
                 live_extra_s: float = 4.0) -> None:
        self._mode = mode
        self._delay = delay_s
        self._tol = tolerance_s
        self._band = band_s
        self._max_nudge = max_nudge
        self._hold_s = hold_s
        self._live_extra = live_extra_s
        self._last_band: str | None = None
        self._last_action_mono = -1e9

    def set_delay(self, delay_s: float, *, immediate: bool) -> None:
        self._delay = delay_s
        self._immediate = immediate
        self._last_band = None

    def target_lag(self, edge: EdgeEstimate) -> float:
        if self._mode == "live":
            return live_distance_s(edge.max_gap_s)
        return self._delay

    def _banded(self, band: str, mono: float, action: SyncAction) -> SyncAction:
        if band == self._last_band and (mono - self._last_action_mono) < self._hold_s:
            return _NONE
        self._last_band = band
        self._last_action_mono = mono
        return action

    def step(self, *, mono: float, edge: EdgeEstimate, player: float | None,
             user_paused: bool, paused_for_cache: bool, self_paused: bool,
             cache_end: float | None) -> SyncAction:
        if player is None or edge.effective is None:
            return _NONE
        lag = edge.effective - player
        if self._mode == "live":
            if user_paused:
                return _NONE
            distance = live_distance_s(edge.max_gap_s)
            if lag > distance + self._live_extra:
                return self._banded("live_seek", mono,
                                    SyncAction("seek", edge.effective - distance))
            return _NONE
        err = lag - self._delay
        if user_paused or paused_for_cache:
            return _NONE
        if self_paused:
            return _RESUME if err >= -self._tol else _NONE
        if abs(err) <= self._tol:
            return self._banded("center", mono, SyncAction("speed", 1.0))
        if abs(err) <= self._band:
            nudge = 1.0 + _clamp(0.01 * err, -self._max_nudge, self._max_nudge)
            return self._banded("nudge", mono, SyncAction("speed", nudge))
        if err > self._band:
            target = edge.effective - self._delay
            if cache_end is not None and cache_end >= target:
                return self._banded("seek", mono, SyncAction("seek", target))
            return self._banded("reload", mono, SyncAction("reload", target))
        return self._banded("buffer", mono, _PAUSE)

    def resume_action(self, *, edge: EdgeEstimate, player: float,
                      cache_end: float | None) -> SyncAction:
        if edge.effective is None:
            return _NONE
        lag = edge.effective - player
        if lag <= self._delay + 3.0:
            return _NONE
        target = edge.effective - self._delay
        if cache_end is not None and cache_end >= target:
            return SyncAction("seek", target)
        return SyncAction("reload", target)

    def set_mode(self, mode: str, *, mono: float, edge: EdgeEstimate,
                 player: float | None, cache_end: float | None) -> SyncAction:
        self._mode = mode
        self._last_band = None
        if edge.effective is None or player is None:
            return _NONE
        if mode == "live":
            distance = live_distance_s(edge.max_gap_s)
            return SyncAction("seek", edge.effective - distance)
        if edge.effective - player < self._delay:
            return _PAUSE
        return _NONE
