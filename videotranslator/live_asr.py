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

    def _majority_winner(self) -> str | None:
        if not self._detections:
            return None
        lang, count = Counter(self._detections).most_common(1)[0]
        if count / len(self._detections) >= self._majority:
            return lang
        return None
