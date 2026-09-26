"""Live TTS helpers (design 4.10).

Pure pieces (MP3 CBR duration, Clip, per-language duration model, rate choice,
silence bounds) plus ``EdgeClipSynth``, the asyncio edge-tts worker that
synthesizes one clip per sentence on a dedicated thread. Network and PyAV are
injected so the worker is unit-testable without either.
"""

from __future__ import annotations

import asyncio
import inspect
import math
import os
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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


class LiveTtsUnavailable(RuntimeError):
    """Raised by EdgeClipSynth.start() when edge-tts cannot be used."""


class EdgeClipSynth:
    """Synthesize one mp3 clip per sentence with edge-tts on a live-tts thread.

    Owns its own asyncio loop on a daemon thread. ``submit`` (called from the
    live-sched thread) enqueues a request; each is streamed to a ``.mp3.part``
    file, atomically renamed, measured, and pushed to :attr:`results` as
    ``(seg_id, gen, Clip | None, reason | None)``. Concurrency is bounded and
    calls are spaced to stay under the free endpoint's limits; a failure trips
    the injected circuit breaker (kind "tts") with one retry when time allows.
    ``communicate_factory`` (edge-tts) and ``av_module`` (PyAV) are injected so
    the worker runs in tests without the network or PyAV.
    """

    def __init__(self, voice: str, out_dir, *, breaker,
                 communicate_factory=None, av_module=None,
                 max_concurrent: int = 2, min_interval_s: float = 0.25,
                 connect_timeout: int = 3, receive_timeout: int = 5,
                 max_in_flight: int = 8, clock: Callable[[], float] | None = None,
                 sleep=None, thread_factory=threading.Thread, sanitize=None) -> None:
        self._voice = voice
        self._out_dir = Path(out_dir)
        self._breaker = breaker
        self._factory = communicate_factory
        self._av = av_module
        self._max_concurrent = max_concurrent
        self._min_interval = min_interval_s
        self._connect_timeout = connect_timeout
        self._receive_timeout = receive_timeout
        self._max_in_flight = max_in_flight
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._thread_factory = thread_factory
        self._sanitize = sanitize
        self.results: queue.Queue = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread = None
        self._ready = threading.Event()
        self._stopping = threading.Event()
        self._sem: asyncio.Semaphore | None = None
        self._aq: asyncio.Queue | None = None
        self._tasks: set = set()
        self._in_flight = 0
        self._last_start = 0.0
        self._accepts_timeout_kwargs = False

    def start(self) -> None:
        if self._factory is None:
            try:
                import edge_tts
            except ImportError as exc:
                raise LiveTtsUnavailable("edge-tts is not installed") from exc
            self._factory = lambda text, voice, **kw: edge_tts.Communicate(text, voice, **kw)
        try:
            params = inspect.signature(self._factory).parameters
            self._accepts_timeout_kwargs = ("connect_timeout" in params
                                            or any(p.kind == p.VAR_KEYWORD
                                                   for p in params.values()))
        except (TypeError, ValueError):
            self._accepts_timeout_kwargs = False
        try:
            self._out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LiveTtsUnavailable(f"cannot create tts dir: {exc}") from exc
        self._thread = self._thread_factory(target=self._run, name="live-tts", daemon=True)
        self._thread.start()
        self._ready.wait(5.0)

    def submit(self, seg_id: int, gen: int, text: str, rate_pct: int,
               deadline_mono: float) -> bool:
        if (not self._ready.is_set() or self._loop is None or self._stopping.is_set()
                or not self._breaker.allow() or self._in_flight >= self._max_in_flight
                or deadline_mono - self._clock() <= 0):
            return False
        self._in_flight += 1
        self._loop.call_soon_threadsafe(
            self._aq.put_nowait, (seg_id, gen, text, rate_pct, deadline_mono))
        return True

    def stop(self, timeout_s: float) -> bool:
        self._stopping.set()
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._aq.put_nowait, None)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout_s)
        try:
            for part in self._out_dir.glob("clip_*.mp3.part"):
                part.unlink()
        except OSError:
            pass
        return self._thread is None or not self._thread.is_alive()

    # -- internals (run on the live-tts thread) -----------------------------

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._sem = asyncio.Semaphore(self._max_concurrent)
        self._aq = asyncio.Queue()
        self._ready.set()
        try:
            self._loop.run_until_complete(self._dispatch())
        finally:
            for task in list(self._tasks):
                task.cancel()
            self._loop.close()

    async def _dispatch(self) -> None:
        while not self._stopping.is_set():
            try:
                req = await asyncio.wait_for(self._aq.get(), timeout=0.2)
            except asyncio.TimeoutError:
                continue
            if req is None:
                return
            task = self._loop.create_task(self._one(req))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def _clean(self, text: str) -> str:
        if self._sanitize is not None:
            return self._sanitize(text)
        return (text or "").strip()

    async def _one(self, req) -> None:
        seg_id, gen, text, rate_pct, deadline = req
        try:
            clean = self._clean(text)
            if not clean:
                self.results.put((seg_id, gen, None, "empty"))
                return
            async with self._sem:
                wait = self._min_interval - (self._clock() - self._last_start)
                if wait > 0:
                    await self._sleep(wait)
                self._last_start = self._clock()
                if deadline - self._clock() < 0.3:
                    self.results.put((seg_id, gen, None, "late"))
                    return
                clip = await self._synth(seg_id, gen, clean, rate_pct,
                                         deadline - self._clock())
                if clip is None:
                    self._breaker.record_failure(kind="tts")
                    if deadline - self._clock() > 3.0:
                        clip = await self._synth(seg_id, gen, clean, rate_pct,
                                                 deadline - self._clock())
                if clip is not None:
                    self._breaker.record_success()
                    self.results.put((seg_id, gen, clip, None))
                else:
                    self.results.put((seg_id, gen, None, "error"))
        except asyncio.CancelledError:
            raise
        except Exception:                       # noqa: BLE001 - never crash the loop
            self.results.put((seg_id, gen, None, "error"))
        finally:
            self._in_flight = max(0, self._in_flight - 1)

    async def _synth(self, seg_id: int, gen: int, text: str, rate_pct: int,
                     timeout: float):
        part = self._out_dir / f"clip_{gen}_{seg_id}.mp3.part"
        final = self._out_dir / f"clip_{gen}_{seg_id}.mp3"
        try:
            kwargs = {"rate": f"+{rate_pct}%"}
            if self._accepts_timeout_kwargs:
                kwargs["connect_timeout"] = int(self._connect_timeout)
                kwargs["receive_timeout"] = int(self._receive_timeout)
            comm = self._factory(text, self._voice, **kwargs)
            await asyncio.wait_for(self._stream_to(comm, part), timeout=max(0.1, timeout))
            size = part.stat().st_size if part.exists() else 0
            if size <= 0:
                return None
            os.replace(part, final)
            duration = mp3_cbr_duration_s(size)
            bounds = (measure_silence(str(final), av_module=self._av)
                      if self._av is not None else None)
            vstart, vend = bounds if bounds else (0.0, duration)
            return Clip(seg_id, gen, str(final), duration, f"+{rate_pct}%", vstart, vend)
        except (asyncio.TimeoutError, Exception):   # noqa: BLE001
            return None
        finally:
            try:
                if part.exists():
                    part.unlink()
            except OSError:
                pass

    async def _stream_to(self, comm, part: Path) -> None:
        with open(part, "wb") as handle:
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    handle.write(chunk["data"])
