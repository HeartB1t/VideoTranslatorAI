"""Caption rendering helpers for live mode (design 4.11, 4.12).

Pure helpers used by the live scheduler: greedy caption wrapping, time-boxed
pagination of long captions, and ASS escaping/rendering that mirrors mpv's own
OSD escaping. The stateful ``DubScheduler`` (segment state machine, clip and
duck actions) lands with the live session.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# U+2060 WORD JOINER, inserted after every backslash so a literal "\n"/"\N" in
# speech stays literal (design 4.12, [CT] finding 12).
_WORD_JOINER = "\u2060"


def _greedy_lines(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def wrap_caption(text: str, max_chars: int = 42, max_lines: int = 2) -> list[str]:
    """Greedy word-wrap into lines of at most ``max_chars``, at most ``max_lines``.

    Returns one page of lines; use :func:`paginate_caption` for text that needs
    more than ``max_lines`` lines.
    """
    return _greedy_lines(text, max_chars)[:max_lines]


def paginate_caption(text: str, start: float, end: float
                     ) -> list[tuple[float, float, list[str]]]:
    """Split a long caption into time-boxed pages of at most two lines.

    Each page's duration is proportional to its character count; the last page
    ends exactly at ``end``.
    """
    max_chars, max_lines = 42, 2
    lines = _greedy_lines(text, max_chars)
    if not lines:
        return []
    pages = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
    weights = [max(1, len(" ".join(page))) for page in pages]
    total = sum(weights)
    span = end - start
    out: list[tuple[float, float, list[str]]] = []
    cursor = start
    for i, (page, weight) in enumerate(zip(pages, weights)):
        page_end = end if i == len(pages) - 1 else cursor + span * weight / total
        out.append((cursor, page_end, page))
        cursor = page_end
    return out


def ass_escape(text: str) -> str:
    """Mirror mpv's OSD escaping (osd_libass.c:200-252, [CT] finding 12).

    Every backslash is followed by U+2060 so typed "\\n"/"\\N" stays literal, and
    every "{" becomes "\\{". Nothing is doubled. Real line breaks are inserted as
    "\\N" by :func:`caption_ass` after escaping.
    """
    return text.replace("\\", "\\" + _WORD_JOINER).replace("{", "\\{")


def caption_ass(lines: Sequence[str], *, font_px: int, italic: bool) -> str:
    """Render caption lines as an ASS events string (design 4.12 style)."""
    style = "{\\an2\\fs%d\\bord2\\shad0}" % font_px
    if italic:
        style += "{\\i1}"
    return style + "\\N".join(ass_escape(line) for line in lines)


# --- Live scheduler: caption path (design 4.11) -----------------------------
# The dub/clip/duck actions and their scheduling are P5; this carries the
# caption state machine only (dub=False), which is pure and fake-clock testable.

@dataclass
class LiveSegment:
    seg_id: int
    gen: int
    start: float
    end: float
    text_src: str
    text_tgt: str | None = None
    italic: bool = False
    dub_ok: bool = False
    clip: object | None = None
    state: str = "transcribed"


@dataclass(frozen=True)
class ShowSubtitle:
    seg_id: int
    ass: str


@dataclass(frozen=True)
class ClearSubtitle:
    pass


@dataclass(frozen=True)
class Drop:
    seg_id: int
    reason: str


# --- Dub/voice/duck actions (design 2.2, P5) --------------------------------
# Emitted by DubScheduler on the dub path and applied by LiveSession._execute on
# the injected voice backend and video.rt. Pure data; no behaviour here.

@dataclass(frozen=True)
class RequestTts:
    """Ask the TTS worker to synthesize ``text`` to fit its slot by ``deadline``."""
    seg_id: int
    gen: int
    text: str
    rate_pct: int
    deadline_mono: float


@dataclass(frozen=True)
class PreloadClip:
    """Load a synthesized clip paused, skipping its leading silence."""
    seg_id: int
    path: str
    skip_s: float


@dataclass(frozen=True)
class StartClip:
    seg_id: int
    speed: float


@dataclass(frozen=True)
class PauseClip:
    pass


@dataclass(frozen=True)
class ResumeClip:
    pass


@dataclass(frozen=True)
class StopClip:
    fade_s: float = 0.0


@dataclass(frozen=True)
class ClipSpeed:
    value: float


@dataclass(frozen=True)
class Duck:
    """Target duck gain for the original audio (1.0 = no duck)."""
    gain: float


class DuckEnvelope:
    """Linear ramp of the duck gain toward a target, one step per ~20 ms tick.

    A full transition takes about ``ramp_s`` (``round(ramp_s/tick_s)`` steps), so
    each step moves ``delta / n_steps`` toward the target (0.07 for the default
    1.0 -> 0.3 duck). ``step`` returns the gain to write, or ``None`` when there
    is nothing to write (already at target, or frozen while the player is paused).
    """

    def __init__(self, *, ramp_s: float = 0.2, tick_s: float = 0.02,
                 min_delta: float = 0.02) -> None:
        self._n_steps = max(1, round(ramp_s / tick_s)) if tick_s > 0 else 1
        self._min_delta = min_delta
        self._current = 1.0
        self._target = 1.0
        self._step = 0.0

    @property
    def current(self) -> float:
        return self._current

    def set_target(self, gain: float) -> None:
        self._target = min(1.0, max(0.0, float(gain)))
        remaining = abs(self._target - self._current)
        self._step = remaining / self._n_steps if remaining else 0.0

    def step(self, *, frozen: bool = False) -> float | None:
        if frozen or self._current == self._target:
            return None
        delta = self._target - self._current
        move = min(abs(delta), max(self._step, self._min_delta))
        self._current += move if delta > 0 else -move
        if abs(self._target - self._current) < 1e-6:
            self._current = self._target
        return self._current

    def snap(self, gain: float) -> float:
        """Jump immediately to ``gain`` (used on stop/seek). Returns it."""
        self._current = self._target = min(1.0, max(0.0, float(gain)))
        self._step = 0.0
        return self._current


class FadeRamp:
    """Linear fade of a value to zero over ``fade_s``, one step per ``tick_s``.

    Used for ``StopClip(fade_s)``: the voice volume goes from its current value
    to 0 before the clip is stopped, so a cut is not audible.
    """

    def __init__(self, start: float, *, fade_s: float, tick_s: float = 0.02) -> None:
        self._value = max(0.0, float(start))
        steps = max(1, math.ceil(fade_s / tick_s)) if fade_s > 0 else 1
        self._step = self._value / steps
        self._done = fade_s <= 0 or self._value <= 0.0

    @property
    def done(self) -> bool:
        return self._done

    def step(self) -> float:
        if self._done:
            return 0.0
        self._value = max(0.0, self._value - self._step)
        if self._value <= 1e-6:
            self._value = 0.0
            self._done = True
        return self._value


_GRACE = {"delayed": 1.5, "live": 6.0}
_SUB_MIN_DISPLAY_S = 1.5
_CAPTION_CLEAR_TAIL_S = 0.3


class DubScheduler:
    """Media-time caption scheduler (design 4.11, caption path).

    ``upsert`` registers translated segments; ``tick(now, ...)`` returns the
    caption actions for the current media time. Captions are shown at
    ``max(start, arrival)`` while ``now`` is inside the grace window, paginated
    into two-line pages, and cleared at ``max(end + 0.3, shown + 1.5)`` or when a
    newer caption takes over. Voice, clips and ducking are added with P5.
    """

    def __init__(self, *, mode: str = "delayed", overhang_s: float = 0.6,
                 merge_gap_s: float = 0.6, caption_font_px: int = 40,
                 dub: bool = False, subs: bool = True) -> None:
        self._mode = mode
        self._overhang = overhang_s
        self._merge_gap = merge_gap_s
        self._font_px = caption_font_px
        self._dub = dub
        self._subs = subs
        self._segments: dict[int, LiveSegment] = {}
        self._arrival: dict[int, float] = {}
        self._dropped: set[int] = set()
        self._shown: tuple[int, int] | None = None  # (seg_id, page index)
        self._shown_at: float | None = None
        self._last_epoch = 0
        self._metrics = {"voiced": 0.0, "dropped": 0.0, "late": 0.0, "margin_p90": 0.0}

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def set_subs(self, on: bool) -> list[object]:
        self._subs = on
        if not on and self._shown is not None:
            self._shown = None
            return [ClearSubtitle()]
        return []

    def upsert(self, seg: LiveSegment) -> None:
        self._segments[seg.seg_id] = seg

    def _caption_ready(self, seg: LiveSegment) -> bool:
        return seg.seg_id not in self._dropped and (
            seg.text_tgt is not None or seg.italic)

    def _caption_text(self, seg: LiveSegment) -> str:
        if seg.italic or seg.text_tgt is None:
            return seg.text_src
        return seg.text_tgt

    def _grace(self) -> float:
        return _GRACE.get(self._mode, 1.5)

    def _show_time(self, seg: LiveSegment) -> float:
        return max(seg.start, self._arrival.get(seg.seg_id, seg.start))

    def _clear_time(self, seg: LiveSegment) -> float:
        return max(seg.end + _CAPTION_CLEAR_TAIL_S,
                   self._show_time(seg) + _SUB_MIN_DISPLAY_S)

    def _visible(self, now: float):
        best = None
        for seg in self._segments.values():
            if not self._caption_ready(seg):
                continue
            show = self._show_time(seg)
            if show > now:
                continue
            if now >= self._clear_time(seg):
                continue
            if show >= seg.end + self._grace():
                continue  # arrived too late to be worth showing
            if best is None or show > self._show_time(best):
                best = seg
        if best is None:
            return None
        pages = paginate_caption(self._caption_text(best), best.start, best.end)
        if not pages:
            return None
        page_idx = 0
        for i, (ps, pe) in enumerate((p[0], p[1]) for p in pages):
            if now >= ps:
                page_idx = i
            if ps <= now < pe:
                page_idx = i
                break
        return best, page_idx, pages[page_idx][2]

    def tick(self, now: float | None, mono: float = 0.0, *, main_running: bool = True,
             main_speed: float = 1.0, voice_state: str = "idle",
             clock_epoch: int = 0) -> list[object]:
        actions: list[object] = []
        if clock_epoch != self._last_epoch:
            self._last_epoch = clock_epoch
            if self._shown is not None:
                self._shown = None
                actions.append(ClearSubtitle())
        if now is None or not self._subs:  # invalid clock or captions off
            if now is None and self._shown is not None:
                self._shown = None
                actions.append(ClearSubtitle())
            return actions
        for seg in self._segments.values():
            if seg.seg_id not in self._arrival and self._caption_ready(seg):
                self._arrival[seg.seg_id] = now
        visible = self._visible(now)
        if visible is None:
            if self._shown is not None:
                self._shown = None
                actions.append(ClearSubtitle())
            return actions
        seg, page_idx, lines = visible
        key = (seg.seg_id, page_idx)
        if key != self._shown:
            self._shown = key
            self._shown_at = now
            actions.append(ShowSubtitle(
                seg.seg_id, caption_ass(lines, font_px=self._font_px, italic=seg.italic)))
        return actions

    def ready_until(self, now: float) -> float:
        ready = sorted((s for s in self._segments.values() if self._caption_ready(s)),
                       key=lambda s: s.start)
        coverage = now
        for seg in ready:
            if seg.end <= now:
                continue
            if seg.start <= coverage + self._merge_gap:
                coverage = max(coverage, seg.end)
            else:
                break
        return coverage

    def on_seek(self, now: float, gen: int) -> list[object]:
        # Clear the caption and let segments after the new position show again.
        for seg in self._segments.values():
            if seg.end > now:
                self._arrival.pop(seg.seg_id, None)
                self._dropped.discard(seg.seg_id)
        actions: list[object] = []
        if self._shown is not None:
            self._shown = None
            actions.append(ClearSubtitle())
        return actions

    def on_discontinuity(self, now: float) -> list[object]:
        # Drop the slots already passed; keep the ASR (caller's concern).
        actions: list[object] = []
        for seg in self._segments.values():
            if seg.end < now and seg.seg_id not in self._dropped:
                self._dropped.add(seg.seg_id)
                actions.append(Drop(seg.seg_id, "late"))
        if self._shown is not None and self._shown[0] in self._dropped:
            self._shown = None
            actions.append(ClearSubtitle())
        return actions

    def metrics(self) -> dict[str, float]:
        return dict(self._metrics, dropped=float(len(self._dropped)))
