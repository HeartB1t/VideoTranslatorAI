"""Health primitives for the live translation subsystem (design 4.14, 4.9).

Pure and dependency free: a per-engine circuit breaker, a small rolling
percentile window, and a parser for the developer fault-injection spec (env
``VTAI_LIVE_FAULTS``).

The status/warning/error code maps (``STATUS_KEYS``/``WARN_KEYS``/``ERROR_KEYS``
and ``LIVE_STATES``) map internal codes to UI keys that exist in all 26 languages
(``ui_strings_player``). ``wrap_factories_with_faults`` lands with the live
session (it needs the ``LiveFactories`` protocol).
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass


# Warning code returned by CircuitBreaker.record_failure per failure kind.
_WARN_FOR_KIND = {
    "rate_limited": "rate_limited",
    "quota": "quota",
    "timeout": "engine_slow",
    "error": "engine_slow",
}


class CircuitBreaker:
    """One breaker per engine (design 4.9).

    Closed lets calls through. ``threshold`` failures inside ``window_s`` open
    it for a cooldown that doubles on every reopen (``cooldown_s`` up to
    ``max_cooldown_s``). When the cooldown elapses the next ``allow()`` returns
    a single half-open probe; its success closes the breaker, its failure
    reopens with a longer cooldown. A ``quota`` failure opens the breaker for
    the rest of the session. ``record_failure`` returns a warning code the first
    time an open episode begins, then ``None`` until the next success.
    """

    def __init__(self, *, threshold: int = 3, window_s: float = 30.0,
                 cooldown_s: float = 30.0, max_cooldown_s: float = 300.0,
                 clock=time.monotonic) -> None:
        self._threshold = threshold
        self._window_s = window_s
        self._base_cooldown = cooldown_s
        self._max_cooldown = max_cooldown_s
        self._clock = clock
        self._failures: deque[float] = deque()
        self._state = "closed"
        self._open_until = 0.0
        self._cooldown = cooldown_s
        self._opens = 0
        self._episode_reported = False
        self._permanent = False

    @property
    def state(self) -> str:
        return self._state

    def allow(self) -> bool:
        if self._permanent:
            return False
        if self._state == "closed":
            return True
        if self._state == "open":
            if self._clock() >= self._open_until:
                self._state = "half_open"
                return True  # the single probe
            return False
        # half_open: the probe is already out, wait for its result
        return False

    def record_success(self) -> None:
        self._failures.clear()
        self._state = "closed"
        self._cooldown = self._base_cooldown
        self._opens = 0
        self._episode_reported = False

    def record_failure(self, *, kind: str) -> str | None:
        now = self._clock()
        if kind == "quota":
            self._permanent = True
            self._state = "open"
            self._open_until = float("inf")
            return self._report(kind)
        if self._state == "half_open":
            return self._open(now, kind)
        self._failures.append(now)
        cutoff = now - self._window_s
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()
        if len(self._failures) >= self._threshold:
            return self._open(now, kind)
        return None

    def _open(self, now: float, kind: str) -> str | None:
        self._opens += 1
        self._cooldown = min(self._base_cooldown * (2 ** (self._opens - 1)),
                             self._max_cooldown)
        self._state = "open"
        self._open_until = now + self._cooldown
        self._failures.clear()
        return self._report(kind)

    def _report(self, kind: str) -> str | None:
        if self._episode_reported:
            return None
        self._episode_reported = True
        return _WARN_FOR_KIND.get(kind, "engine_slow")

    def retry_in_s(self) -> float:
        if self._permanent:
            return float("inf")
        if self._state == "open":
            return max(0.0, self._open_until - self._clock())
        return 0.0


class RollingStats:
    """Nearest-rank percentiles over the last ``window`` samples (default 32)."""

    def __init__(self, window: int = 32) -> None:
        self._values: deque[float] = deque(maxlen=window)

    def add(self, x: float) -> None:
        self._values.append(float(x))

    def count(self) -> int:
        return len(self._values)

    def _percentile(self, pct: float) -> float | None:
        if not self._values:
            return None
        ordered = sorted(self._values)
        # nearest-rank: rank = ceil(pct/100 * n), 1-based
        rank = max(1, -(-int(pct) * len(ordered) // 100))
        return ordered[min(rank, len(ordered)) - 1]

    def p50(self) -> float | None:
        return self._percentile(50)

    def p90(self) -> float | None:
        return self._percentile(90)

    def p95(self) -> float | None:
        return self._percentile(95)


# Session states and their UI keys (design 4.3). A test asserts
# set(STATUS_KEYS) == LIVE_STATES.
LIVE_STATES: frozenset[str] = frozenset({
    "starting", "loading_models", "connecting", "detecting", "buffering",
    "waiting", "running", "lag", "reconnecting", "stopping", "ended",
    "stopped", "failed", "time_limit",
})

STATUS_KEYS: dict[str, str] = {
    "starting": "live_status_starting",
    "loading_models": "live_status_loading_models",
    "connecting": "live_status_connecting",
    "detecting": "live_status_detecting",
    "buffering": "live_status_buffering",
    "waiting": "live_status_waiting",
    "running": "live_status_running",
    "lag": "live_status_lag",
    "reconnecting": "live_status_reconnecting",
    "stopping": "live_status_stopping",
    "ended": "live_status_ended",
    "stopped": "live_status_stopped",
    "failed": "live_status_failed",
    "time_limit": "live_status_time_limit",
}

WARN_KEYS: dict[str, str] = {
    "online_engine": "live_warn_online_engine",
    "rate_limited": "live_warn_rate_limited",
    "quota": "live_warn_quota",
    "engine_slow": "live_warn_engine_slow",
    "tts_unavailable": "live_warn_tts_unavailable",
    "cpu_fallback": "live_warn_cpu_fallback",
    "falling_behind": "live_warn_falling_behind",
    "skipped": "live_warn_skipped",
}

ERROR_KEYS: dict[str, str] = {
    "busy": "live_err_busy",
    "busy_job": "live_err_busy_job",
    "busy_install": "live_err_busy_install",
    "editor_open": "live_err_editor_open",
    "no_url": "live_err_no_url",
    "deps": "live_err_deps",
    "disk": "live_err_disk",
    "deepl_key": "live_err_deepl_key",
    "marian_pair": "live_err_marian_pair",
    "ollama": "live_err_ollama",
    "resolve": "live_err_resolve",
    "upcoming": "live_err_upcoming",
    "codec": "live_err_codec",
    "need_source_lang": "live_err_need_source_lang",
    "ingest": "live_err_ingest",
    "asr": "live_err_asr",
    "internal": "live_err_internal",
}


@dataclass(frozen=True)
class FaultRule:
    """One developer fault: fail ``count`` times, or start failing at ``at_s``."""

    kind: str
    count: int | None
    at_s: float | None


def parse_fault_spec(spec: str) -> dict[str, FaultRule]:
    """Parse ``VTAI_LIVE_FAULTS`` (dev only).

    Grammar: comma separated ``name:count`` (fail the first ``count`` calls) or
    ``name@seconds`` (start failing at that session time). Blank tokens and a
    blank spec yield an empty mapping.
    """
    rules: dict[str, FaultRule] = {}
    for token in (spec or "").split(","):
        token = token.strip()
        if not token:
            continue
        if "@" in token:
            name, _, value = token.partition("@")
            rules[name.strip()] = FaultRule(name.strip(), None, float(value))
        elif ":" in token:
            name, _, value = token.partition(":")
            rules[name.strip()] = FaultRule(name.strip(), int(value), None)
        else:
            rules[token] = FaultRule(token, None, None)
    return rules
