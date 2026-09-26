"""VAD utterance segmentation and sentence assembly for live mode (design 4.7, 4.8).

Pure state machines over frame probabilities and ASR pieces. No ML: the caller
supplies the per-frame speech probabilities (from ``StreamingVad``) and the ASR
segment pieces. Times are in session time (design 4.3).
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from videotranslator.segments import END_PUNCT_CHARS, split_on_punctuation

_END_PUNCT_SET = frozenset(END_PUNCT_CHARS)


@dataclass(frozen=True)
class Utterance:
    gen: int
    start: float
    end: float
    samples: np.ndarray  # float32 mono 16 kHz
    forced_cut: bool


class UtteranceSegmenter:
    """Turn per-frame speech probabilities into utterances (design 4.7).

    Starts an utterance at ``on_threshold``, continues while above
    ``off_threshold``, ends after ``min_silence_s`` of silence with ``pad_s`` of
    padding. At ``max_len_s`` it cuts at the last pause of at least
    ``min_pause_s`` inside the last ``soft_cut_window_s``, else at the
    lowest-probability frame (``forced_cut=True``). A time jump over
    ``discontinuity_s`` flushes the current utterance.
    """

    def __init__(self, *, on_threshold: float = 0.5, off_threshold: float = 0.35,
                 min_silence_s: float = 0.4, pad_s: float = 0.15, max_len_s: float = 8.0,
                 soft_cut_window_s: float = 1.5, min_pause_s: float = 0.1,
                 discontinuity_s: float = 0.25, sample_rate: int = 16000,
                 frame: int = 512) -> None:
        self._on = on_threshold
        self._off = off_threshold
        self._min_silence = min_silence_s
        self._pad = pad_s
        self._max_len = max_len_s
        self._soft_win = soft_cut_window_s
        self._min_pause = min_pause_s
        self._discont = discontinuity_s
        self._sr = sample_rate
        self._frame = frame
        self._frame_s = frame / sample_rate
        self._pad_frames = max(1, int(round(pad_s / self._frame_s)))
        self._gen = 0
        self._reset_state()

    def _reset_state(self) -> None:
        self._active = False
        self._frames: list[dict] = []
        self._prepad: deque[dict] = deque()
        self._silence_s = 0.0
        self._last_speech_idx = -1
        self._last_block_end: float | None = None

    def reset(self, gen: int) -> None:
        self._gen = gen
        self._reset_state()

    def set_max_len(self, seconds: float) -> None:
        self._max_len = seconds

    @property
    def speech_active(self) -> bool:
        """Whether the current VAD utterance still contains active speech."""
        return self._active

    def _slice(self, samples, k: int):
        return np.asarray(samples[k * self._frame:(k + 1) * self._frame],
                          dtype=np.float32)

    def push(self, block_start: float, samples, probs: Sequence[float]) -> list[Utterance]:
        out: list[Utterance] = []
        if (self._last_block_end is not None
                and abs(block_start - self._last_block_end) > self._discont):
            if self._active:
                out.append(self._emit(forced=False))
            self._prepad.clear()
        for k in range(len(probs)):
            frame = {
                "time": block_start + k * self._frame_s,
                "prob": float(probs[k]),
                "samples": self._slice(samples, k),
            }
            out.extend(self._consume(frame))
        self._last_block_end = block_start + len(samples) / self._sr
        return out

    def _consume(self, frame: dict) -> list[Utterance]:
        if not self._active:
            self._prepad.append(frame)
            while len(self._prepad) > self._pad_frames:
                self._prepad.popleft()
            if frame["prob"] >= self._on:
                self._active = True
                self._frames = list(self._prepad)
                self._prepad.clear()
                self._silence_s = 0.0
                self._last_speech_idx = len(self._frames) - 1
            return []
        self._frames.append(frame)
        if frame["prob"] > self._off:
            self._silence_s = 0.0
            self._last_speech_idx = len(self._frames) - 1
        else:
            self._silence_s += self._frame_s
        if self._silence_s >= self._min_silence:
            return [self._emit(forced=False)]
        span = self._frames[-1]["time"] - self._frames[0]["time"] + self._frame_s
        if span >= self._max_len:
            return [self._force_cut()]
        return []

    def _build(self, frames: list[dict], forced: bool) -> Utterance:
        start = frames[0]["time"]
        end = frames[-1]["time"] + self._frame_s
        samples = (np.concatenate([f["samples"] for f in frames])
                   if frames else np.zeros(0, dtype=np.float32))
        return Utterance(self._gen, start, end, samples, forced)

    def _emit(self, *, forced: bool) -> Utterance:
        # Keep at most pad_s of trailing silence after the last speech frame.
        keep = min(len(self._frames), self._last_speech_idx + 1 + self._pad_frames)
        utt = self._build(self._frames[:keep], forced)
        self._active = False
        self._frames = []
        self._silence_s = 0.0
        self._last_speech_idx = -1
        return utt

    def _force_cut(self) -> Utterance:
        frames = self._frames
        win_frames = max(1, int(round(self._soft_win / self._frame_s)))
        window_start = max(1, len(frames) - win_frames)
        cut = self._last_pause_cut(frames, window_start)
        if cut is None:
            cut = self._lowest_prob_cut(frames, window_start)
        head = frames[:cut]
        tail = frames[cut:]
        utt = self._build(head, forced=True)
        # Continue with the remainder as a fresh utterance (no overlap, v1).
        self._frames = tail
        self._silence_s = 0.0
        self._last_speech_idx = max(
            (i for i, f in enumerate(tail) if f["prob"] > self._off), default=len(tail) - 1)
        return utt

    def _last_pause_cut(self, frames: list[dict], window_start: int) -> int | None:
        min_pause_frames = max(1, int(round(self._min_pause / self._frame_s)))
        run = 0
        best_end: int | None = None
        for i in range(window_start, len(frames)):
            if frames[i]["prob"] < self._off:
                run += 1
                if run >= min_pause_frames:
                    best_end = i + 1  # cut after the pause
            else:
                run = 0
        return best_end

    def _lowest_prob_cut(self, frames: list[dict], window_start: int) -> int:
        lo_idx = window_start
        lo_val = math.inf
        for i in range(window_start, len(frames)):
            if frames[i]["prob"] < lo_val:
                lo_val = frames[i]["prob"]
                lo_idx = i
        return max(1, lo_idx)

    def flush(self) -> list[Utterance]:
        if self._active and self._frames:
            return [self._emit(forced=False)]
        self._active = False
        self._frames = []
        return []


@dataclass(frozen=True)
class Sentence:
    seg_id: int
    gen: int
    start: float
    end: float
    text: str
    flags: tuple[str, ...]


class SentenceAssembler:
    """Assemble ASR pieces into sentences (design 4.8).

    Flushes on end punctuation, on ``hold_s`` of MEDIA time without punctuation
    (via ``edge``), or on the ``max_words``/``max_span_s``/``max_chars`` caps.
    Multi-sentence text is split with proportional timing.
    """

    def __init__(self, *, hold_s: float, max_words: int = 30, max_span_s: float = 12.0,
                 max_chars: int = 300) -> None:
        self._hold_s = hold_s
        self._max_words = max_words
        self._max_span_s = max_span_s
        self._max_chars = max_chars
        self._gen = 0
        self._seg_id = 0
        self._buf: list[dict] = []

    def reset(self, gen: int) -> None:
        self._gen = gen
        self._buf = []

    def push(self, pieces: list[dict], gen: int) -> list[Sentence]:
        if gen != self._gen:
            self.reset(gen)
        out: list[Sentence] = []
        for piece in pieces:
            self._buf.append(piece)
            if self._should_flush():
                out.extend(self._flush())
        return out

    def edge(self, media_edge: float) -> list[Sentence]:
        if not self._buf:
            return []
        last_end = float(self._buf[-1]["end"])
        if media_edge - last_end >= self._hold_s:
            return self._flush()
        return []

    def _text(self) -> str:
        return " ".join((p.get("text") or "").strip() for p in self._buf).strip()

    def _should_flush(self) -> bool:
        text = self._text()
        if not text:
            return False
        if text[-1] in _END_PUNCT_SET:
            return True
        if len(text.split()) >= self._max_words:
            return True
        if len(text) >= self._max_chars:
            return True
        span = float(self._buf[-1]["end"]) - float(self._buf[0]["start"])
        return span >= self._max_span_s

    def _flush(self) -> list[Sentence]:
        if not self._buf:
            return []
        text = self._text()
        start = float(self._buf[0]["start"])
        end = float(self._buf[-1]["end"])
        flags: tuple[str, ...] = tuple(dict.fromkeys(
            flag for p in self._buf for flag in p.get("flags", ())))
        self._buf = []
        if not text:
            return []
        parts = split_on_punctuation([{"text": text, "start": start, "end": end}])
        out: list[Sentence] = []
        for part in parts:
            piece_text = (part.get("text") or "").strip()
            if not piece_text:
                continue
            out.append(Sentence(self._seg_id, self._gen, float(part["start"]),
                                float(part["end"]), piece_text, flags))
            self._seg_id += 1
        return out
