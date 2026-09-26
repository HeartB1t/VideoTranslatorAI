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

# Provisional timing constants, to be replaced by real measurements from spike S3
# (design Plan 0 S3). DUCK_LATENCY_S = ducking p95 + 0.05 per platform;
# VOICE_DEVICE_OFFSET_S = median audible onset minus unpause; VOICE_LEAD_INITIAL_S
# = audio_buffer 0.2 + start overhead.
DUCK_LATENCY_S = {"linux": 0.4, "win32": 0.4, "darwin": 0.4}       # provisional (S3)
VOICE_DEVICE_OFFSET_S = {"linux": 0.0, "win32": 0.0, "darwin": 0.0}  # provisional (S3)
VOICE_LEAD_INITIAL_S = 0.25                                        # provisional (S3)


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


def silence_bounds(samples, rate: int, *, threshold_dbfs: float = -45.0,
                   frame_s: float = 0.01) -> tuple[float, float] | None:
    """First and last audible times in ``samples`` (mono float32), or None.

    Pure: RMS per ``frame_s`` frame in dBFS (0 dBFS = full scale); the span runs
    from the first to the last frame at or above ``threshold_dbfs``. Returns None
    when the whole clip is below the threshold (silence).
    """
    import numpy as np
    data = np.asarray(samples, dtype=np.float32).reshape(-1)
    if data.size == 0:
        return None
    frame = max(1, int(rate * frame_s))
    n = data.size // frame
    if n == 0:
        rms = float(np.sqrt(np.mean(data ** 2)))
        db = 20.0 * np.log10(max(rms, 1e-10))
        return (0.0, data.size / rate) if db >= threshold_dbfs else None
    frames = data[:n * frame].reshape(n, frame)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    dbfs = 20.0 * np.log10(np.maximum(rms, 1e-10))
    voiced = np.where(dbfs >= threshold_dbfs)[0]
    if voiced.size == 0:
        return None
    return (float(voiced[0] * frame) / rate, float((voiced[-1] + 1) * frame) / rate)


def measure_silence(path: str, *, av_module, threshold_dbfs: float = -45.0,
                    frame_s: float = 0.01) -> tuple[float, float] | None:
    """Audible bounds of an audio file via PyAV, or None on any failure.

    ``av_module`` is injected (``import av``) so tests never touch PyAV. Decodes
    to mono 16 kHz float32 like ``live_asr.AudioDecoder`` and calls
    :func:`silence_bounds`.
    """
    import numpy as np
    container = None
    try:
        container = av_module.open(path)
        stream = container.streams.audio[0]
        resampler = av_module.AudioResampler(format="s16", layout="mono", rate=16000)
        chunks = []
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                arr = resampled.to_ndarray().reshape(-1).astype(np.float32) / 32768.0
                chunks.append(arr)
        if not chunks:
            return None
        return silence_bounds(np.concatenate(chunks), 16000,
                              threshold_dbfs=threshold_dbfs, frame_s=frame_s)
    except Exception:                       # noqa: BLE001 - best effort
        return None
    finally:
        if container is not None:
            try:
                container.close()
            except Exception:
                pass


class LeadCalibrator:
    """Learn the voice lead (unpause -> first audible sample) over the first clips.

    Seeded from ``initial``; each measured onset updates an EMA, bounded to
    ``[lo, hi]``, for at most ``warmup`` clips. Used so the scheduler starts a
    clip early enough that it becomes audible right at the segment start.
    """

    def __init__(self, initial: float, *, alpha: float = 0.4, lo: float = 0.1,
                 hi: float = 0.6, warmup: int = 5) -> None:
        self._lo = lo
        self._hi = hi
        self._alpha = alpha
        self._warmup = warmup
        self._count = 0
        self._lead = min(hi, max(lo, initial))
        self._unpause: float | None = None
        self._skip = 0.0

    @property
    def lead(self) -> float:
        return self._lead

    def on_start(self, mono_unpause: float, skip_s: float) -> None:
        self._unpause = mono_unpause
        self._skip = skip_s

    def on_voice_pts(self, mono: float, pts: float) -> float | None:
        """Feed a decoded audio pts; returns the updated lead, or None.

        The first pts past the skipped leading silence marks the audible onset;
        the onset delay (``mono - unpause``) updates the lead EMA. Ignored after
        the warmup window.
        """
        if self._unpause is None or self._count >= self._warmup:
            return None
        if pts < self._skip:
            return None
        measured = min(self._hi, max(self._lo, mono - self._unpause))
        self._unpause = None
        self._count += 1
        self._lead = (measured if self._count == 1
                      else self._alpha * measured + (1 - self._alpha) * self._lead)
        return self._lead
