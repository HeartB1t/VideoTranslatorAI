"""Live TTS helpers (design 4.10).

Pure, dependency-free pieces: the MP3 CBR duration, the Clip descriptor, the
per-language duration model and rate choice. The real ``EdgeClipSynth`` (an
asyncio edge-tts worker) and ``measure_silence`` (PyAV) land with the real-audio
integration (spike S3).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

# 48 kbit/s CBR mono mp3: bytes / 6000 equals the decoded duration to the
# millisecond ([CT] C34).
EDGE_BYTES_PER_SECOND = 6000


def mp3_cbr_duration_s(n_bytes: int) -> float:
    """Duration of an Edge-TTS CBR mp3 from its byte count, no probe needed."""
    return n_bytes / EDGE_BYTES_PER_SECOND


@dataclass(frozen=True)
class Clip:
    seg_id: int
    gen: int
    path: str
    duration: float
    rate: str
    voice_start_s: float  # measured leading silence
    voice_end_s: float    # end of audible speech

    @property
    def audible_s(self) -> float:
        """The audible span used for slot fitting and speed."""
        return self.voice_end_s - self.voice_start_s


class EdgeDurationModel:
    """Per-session, per-language characters-per-second estimate (design 4.10).

    Seeded from the XTTS estimate ([CT] C35 refuted it for Edge), then driven by
    the session's own rate-normalised audible durations (EMA, alpha 0.3).
    """

    def __init__(self, lang: str, *, seed_estimate: Callable[[str, str], float],
                 alpha: float = 0.3) -> None:
        self._lang = lang
        self._seed = seed_estimate
        self._alpha = alpha
        self._cps_ema: float | None = None

    def estimate(self, text: str, rate_pct: int) -> float:
        """Predicted audible duration of ``text`` spoken at ``rate_pct``."""
        if self._cps_ema is None or self._cps_ema <= 0:
            base = self._seed(text, self._lang)
        else:
            base = len(text) / self._cps_ema
        return base / (1 + rate_pct / 100)

    def observe(self, text: str, rate_pct: int, audible_s: float) -> None:
        if audible_s <= 0 or not text:
            return
        rate0 = audible_s * (1 + rate_pct / 100)
        if rate0 <= 0:
            return
        cps = len(text) / rate0
        if self._cps_ema is None:
            self._cps_ema = cps
        else:
            self._cps_ema = self._alpha * cps + (1 - self._alpha) * self._cps_ema


def choose_rate(text: str, slot_s: float, model: EdgeDurationModel, *,
                max_pct: int = 30) -> int:
    """Edge-TTS rate percent to fit ``text`` into ``slot_s`` (design 4.10).

    The playback speed clamp (1.0-1.3) corrects what the estimate misses.
    """
    if slot_s <= 0:
        return max_pct
    n = math.ceil((model.estimate(text, 0) / slot_s - 1) * 100)
    return max(0, min(max_pct, n))
