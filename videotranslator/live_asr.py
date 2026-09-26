"""ASR helpers for live mode (design 4.3, 4.8).

This module holds the PURE, dependency-free pieces: the decoder time-domain
conversion, the hallucination filter and the language lock. The stateful ML
components (``AudioDecoder`` with PyAV, ``StreamingVad`` with onnxruntime,
``PersistentWhisper``) import their heavy libraries lazily and are added with the
live session's real-hardware integration.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Sequence

import numpy as np


def decoder_time(pts: int, time_base: float, *, container_start_us: int | None,
                 domain: str) -> float:
    """Convert a decoded frame PTS to session time (design 4.3).

    ``rebased`` (files) subtracts the container start; ``container_start_us`` is
    in MICROSECONDS ([CT] finding 13). ``raw`` (streams) keeps the PTS as is.
    """
    t = pts * time_base
    if domain == "rebased":
        t -= (container_start_us or 0) / 1_000_000
    return t


class HallucinationFilter:
    """Drop Whisper hallucinations (design 4.8).

    Drops a segment when ``no_speech_prob > 0.6`` and ``avg_logprob < -1.0``,
    when ``compression_ratio > 2.4``, or when its text exactly repeats one of the
    last two kept texts.
    """

    def __init__(self) -> None:
        self._recent: deque[str] = deque(maxlen=2)

    def filter(self, segments: Sequence[dict]) -> list[dict]:
        out: list[dict] = []
        for seg in segments:
            if (seg.get("no_speech_prob", 0.0) > 0.6
                    and seg.get("avg_logprob", 0.0) < -1.0):
                continue
            if seg.get("compression_ratio", 0.0) > 2.4:
                continue
            text = (seg.get("text") or "").strip()
            if text and text in self._recent:
                continue
            out.append(seg)
            if text:
                self._recent.append(text)
        return out


class LanguageLock:
    """Lock the source language for a live session (design 4.8).

    An explicit source is locked from the start. In ``auto`` it locks at
    probability >= ``prob_threshold`` once >= ``min_speech_lock_s`` of speech is
    seen, otherwise by a majority vote (>= ``majority`` of per-utterance
    detections) once ``vote_window_s`` of speech is reached; if no language
    reaches the majority after ``fail_after_s`` of speech it fails (the caller
    shows ``live_err_need_source_lang``).
    """

    def __init__(self, source: str, *, prob_threshold: float = 0.8,
                 min_speech_lock_s: float = 5.0, vote_window_s: float = 30.0,
                 fail_after_s: float = 60.0, majority: float = 0.6) -> None:
        self._prob_threshold = prob_threshold
        self._min_speech_lock_s = min_speech_lock_s
        self._vote_window_s = vote_window_s
        self._fail_after_s = fail_after_s
        self._majority = majority
        explicit = source not in ("", "auto")
        self._locked: str | None = source if explicit else None
        self._failed = False
        self._speech_s = 0.0
        self._detections: list[str] = []
        self._pending_segments: list[dict] = []

    @property
    def locked(self) -> str | None:
        return self._locked

    @property
    def state(self) -> str:
        if self._locked is not None:
            return "locked"
        return "failed" if self._failed else "detecting"

    def observe(self, lang: str, prob: float, duration: float) -> str:
        """Feed one per-utterance detection; return the new state."""
        if self._locked is not None:
            return "locked"
        if self._failed:
            return "failed"
        self._speech_s += duration
        self._detections.append(lang)
        if prob >= self._prob_threshold and self._speech_s >= self._min_speech_lock_s:
            self._locked = lang
            return "locked"
        if self._speech_s >= self._vote_window_s:
            winner = self._majority_winner()
            if winner is not None:
                self._locked = winner
                return "locked"
        if self._speech_s >= self._fail_after_s:
            self._failed = True
            return "failed"
        return "detecting"

    def buffer_segments(self, segments: list[dict]) -> None:
        """Retain speech seen before auto language detection locks."""
        self._pending_segments.extend(segments)

    def take_buffered_segments(self) -> list[dict]:
        """Release pre-lock speech in order, only after the language is known."""
        if self._locked is None:
            return []
        segments, self._pending_segments = self._pending_segments, []
        return segments

    def clear_buffered_segments(self) -> None:
        self._pending_segments.clear()

    def _majority_winner(self) -> str | None:
        if not self._detections:
            return None
        lang, count = Counter(self._detections).most_common(1)[0]
        if count / len(self._detections) >= self._majority:
            return lang
        return None


# --- Real ML/IO components (design 4.7). Heavy deps imported lazily. ---------

class StreamingVad:
    """Stateful Silero VAD (faster-whisper asset) over a live audio stream.

    Mirrors ``faster_whisper.vad.SileroVADModel.__call__`` frame by frame,
    carrying the recurrent state ``h``/``c`` and the 64-sample context across
    calls, plus a remainder buffer because a 0.25 s block (4000 samples) is not a
    multiple of 512 ([CT] C37). Returns one probability per complete 512 frame.
    """

    def __init__(self, *, session_factory=None, frame: int = 512,
                 context_size: int = 64) -> None:
        self._session_factory = session_factory
        self._session = None
        self._frame = frame
        self._ctx_n = context_size
        self._h = np.zeros((1, 1, 128), dtype=np.float32)
        self._c = np.zeros((1, 1, 128), dtype=np.float32)
        self._context = np.zeros(context_size, dtype=np.float32)
        self._remainder = np.zeros(0, dtype=np.float32)

    def _ensure_session(self):
        if self._session is None:
            if self._session_factory is not None:
                self._session = self._session_factory()
            else:
                from faster_whisper.vad import get_vad_model
                self._session = get_vad_model().session
        return self._session

    def probs(self, samples) -> list[float]:
        session = self._ensure_session()
        buf = np.concatenate([self._remainder, np.asarray(samples, dtype=np.float32)])
        n_frames = len(buf) // self._frame
        out: list[float] = []
        for i in range(n_frames):
            frame = buf[i * self._frame:(i + 1) * self._frame]
            inp = np.concatenate([self._context, frame]).reshape(
                1, self._frame + self._ctx_n).astype(np.float32)
            prob, self._h, self._c = session.run(
                None, {"input": inp, "h": self._h, "c": self._c})
            out.append(float(np.asarray(prob).reshape(-1)[0]))
            self._context = frame[-self._ctx_n:].copy()
        self._remainder = buf[n_frames * self._frame:].copy()
        return out

    def reset(self) -> None:
        self._h = np.zeros((1, 1, 128), dtype=np.float32)
        self._c = np.zeros((1, 1, 128), dtype=np.float32)
        self._context = np.zeros(self._ctx_n, dtype=np.float32)
        self._remainder = np.zeros(0, dtype=np.float32)


class AudioDecoder:
    """Decode an audio/video source into 0.25 s float32 mono 16 kHz blocks.

    ``import av`` happens in ``__init__`` only (design 2.2). Block start times are
    anchored to decoded-frame timestamps via :func:`decoder_time`, re-anchored
    whenever the buffer drains, so gaps never skew later times.
    """

    _RATE = 16000
    _BLOCK = 4000  # 0.25 s at 16 kHz

    def __init__(self, source, *, container_format: str | None = None,
                 start_at: float = 0.0, time_domain: str = "rebased",
                 av_module=None, seek_index=None) -> None:
        if av_module is None:
            import av
            av_module = av
        self._av = av_module
        self._source = source
        self._start_at = start_at
        self._time_domain = time_domain
        self._seek_index = seek_index
        self._container = av_module.open(source, format=container_format)
        if not self._container.streams.audio:
            self._container.close()
            raise RuntimeError("the source has no audio track to transcribe")
        self._stream = self._container.streams.audio[0]
        start = getattr(self._container, "start_time", None)
        self._container_start_us = start if start is not None else None
        self._resampler = av_module.AudioResampler(
            format="s16", layout="mono", rate=self._RATE)
        self.first_pts: float | None = None

    def _frame_time(self, frame) -> float:
        if frame.pts is None:
            return 0.0
        return decoder_time(frame.pts, float(frame.time_base),
                            container_start_us=self._container_start_us,
                            domain=self._time_domain)

    def blocks(self, cancel):
        if self._start_at and self._start_at > 0:
            try:
                self._container.seek(int(self._start_at / float(self._stream.time_base)),
                                     stream=self._stream)
            except Exception:
                pass
        buf = np.zeros(0, dtype=np.float32)
        buf_start: float | None = None
        for frame in self._container.decode(self._stream):
            if cancel is not None and cancel.is_set():
                return
            t = self._frame_time(frame)
            if self.first_pts is None:
                self.first_pts = t
            samples = self._resample(frame)
            if samples.size == 0:
                continue
            if buf.size == 0:
                buf_start = t
            buf = np.concatenate([buf, samples])
            while buf.size >= self._BLOCK:
                yield (buf_start, buf[:self._BLOCK].copy())
                buf = buf[self._BLOCK:]
                buf_start = (buf_start or 0.0) + self._BLOCK / self._RATE
        if buf.size:
            yield (buf_start or 0.0, buf.copy())

    def _resample(self, frame) -> np.ndarray:
        out = np.zeros(0, dtype=np.float32)
        for resampled in self._resampler.resample(frame):
            arr = resampled.to_ndarray().reshape(-1).astype(np.float32) / 32768.0
            out = np.concatenate([out, arr])
        return out

    def close(self) -> None:
        try:
            self._container.close()
        except Exception:
            pass


class PersistentWhisper:
    """faster-Whisper loaded once per live session (design 4.8).

    CUDA: large-v3-turbo float16, beam 5. Otherwise: small int8, beam 1. On a
    CUDA runtime error it reloads small int8 on the CPU once and retries. Segment
    times are shifted by ``utt.start`` into session time.
    """

    _GPU = ("large-v3-turbo", "cuda", "float16", 5)
    _CPU = ("small", "cpu", "int8", 1)

    def __init__(self, *, device_policy: str = "auto", hotwords: str | None = None,
                 whisper_model_cls=None, torch_module=None,
                 log: Callable[[str], None] = lambda _m: None) -> None:
        self._hotwords = hotwords
        self._log = log
        if whisper_model_cls is None:
            from faster_whisper import WhisperModel
            whisper_model_cls = WhisperModel
        self._cls = whisper_model_cls
        if torch_module is None:
            import torch as torch_module
        self._torch = torch_module
        use_gpu = device_policy != "cpu" and bool(self._torch.cuda.is_available())
        self.model_name, self.device, self._compute, self._beam = (
            self._GPU if use_gpu else self._CPU)
        self.fell_back = False
        self._model = self._cls(self.model_name, device=self.device,
                                compute_type=self._compute)

    def _kwargs(self, language: str | None) -> dict:
        from .transcription import build_transcribe_kwargs
        kwargs = build_transcribe_kwargs(language or "auto", None)
        kwargs.update(vad_filter=False, condition_on_previous_text=False,
                      temperature=0, beam_size=self._beam,
                      language=None if not language or language == "auto" else language)
        from .hotwords import to_whisper_param
        param = to_whisper_param(self._hotwords) if self._hotwords else None
        if param:
            kwargs["hotwords"] = param
        return kwargs

    def transcribe(self, utt, *, language: str | None):
        try:
            return self._run(utt, language)
        except RuntimeError as exc:
            from .transcription import is_cuda_runtime_error
            if is_cuda_runtime_error(exc) and not self.fell_back:
                self._log("[live-asr] CUDA error, falling back to CPU")
                self._fallback_to_cpu()
                return self._run(utt, language)
            raise

    def _run(self, utt, language: str | None):
        segments, info = self._model.transcribe(
            np.asarray(utt.samples, dtype=np.float32), **self._kwargs(language))
        out = []
        for seg in segments:
            text = (getattr(seg, "text", "") or "").strip()
            if not text:
                continue
            out.append({
                "start": float(getattr(seg, "start", 0.0)) + utt.start,
                "end": float(getattr(seg, "end", 0.0)) + utt.start,
                "text": text,
                "no_speech_prob": float(getattr(seg, "no_speech_prob", 0.0)),
                "avg_logprob": float(getattr(seg, "avg_logprob", 0.0)),
                "compression_ratio": float(getattr(seg, "compression_ratio", 0.0)),
            })
        return out, getattr(info, "language", None), float(
            getattr(info, "language_probability", 0.0))

    def _fallback_to_cpu(self) -> None:
        self.close()
        self.model_name, self.device, self._compute, self._beam = self._CPU
        self.fell_back = True
        self._model = self._cls(self.model_name, device=self.device,
                                compute_type=self._compute)

    def close(self) -> None:
        self._model = None
        try:
            self._torch.cuda.empty_cache()
        except Exception:
            pass
