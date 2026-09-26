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


def _percentile(values: Sequence[float], pct: int) -> float:
    """Nearest-rank percentile of ``values`` (0.0 when empty)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, -(-pct * len(ordered) // 100))   # ceil(pct/100 * n)
    return float(ordered[min(rank, len(ordered)) - 1])


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
                 dub: bool = False, subs: bool = True,
                 rate_for=lambda text, slot_s: 0, lead_s: float = 0.25,
                 preload_s: float = 1.5, late_tolerance_s: float = 0.5,
                 max_live_lag_s: float = 4.0, max_speed: float = 1.3,
                 unduck_tail_s: float = 0.2, duck_gain: float = 0.3,
                 duck_ramp_s: float = 0.2, duck_latency_s: float = 0.4,
                 max_in_flight: int = 8) -> None:
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
        self._last_now: float | None = None
        self._metrics = {"voiced": 0.0, "dropped": 0.0, "late": 0.0, "margin_p90": 0.0}
        # --- dub path (P5) ---
        self._rate_for = rate_for
        self._lead = lead_s
        self._preload_s = preload_s
        self._late_tol = late_tolerance_s
        self._max_live_lag = max_live_lag_s
        self._max_speed = max_speed
        self._unduck_tail = unduck_tail_s
        self._duck_gain = duck_gain
        self._duck_ramp = duck_ramp_s
        self._duck_latency = duck_latency_s
        self._max_in_flight = max_in_flight
        self._dub_state: dict[int, str] = {}   # seg_id -> translated/synth/ready/
                                               # preloaded/playing/done/dropped
        self._clips: dict[int, object] = {}    # seg_id -> Clip
        self._clip_cache: dict[tuple, object] = {}  # (rstart, rend, tgt) -> Clip
        self._preloaded: int | None = None
        self._playing: int | None = None
        self._pacer_recovery_seg: int | None = None
        self._clip_paused = False
        self._expected_end: float = 0.0
        self._duck_target: float = 1.0
        self._margins: list[float] = []        # recent start margins for p90
        self._voiced = 0
        self._dub_dropped = 0

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
        if self._dub and self._dub_eligible(seg) and seg.seg_id not in self._dub_state:
            cached = self._clip_cache.get(self._cache_key(seg))
            if cached is not None:              # replay after a seek: reuse the clip
                self._clips[seg.seg_id] = cached
                seg.clip = cached
                self._dub_state[seg.seg_id] = "ready"
            else:
                self._dub_state[seg.seg_id] = "translated"

    # -- dub path (P5) ------------------------------------------------------

    def _dub_eligible(self, seg: LiveSegment) -> bool:
        return bool(seg.dub_ok and seg.text_tgt and seg.seg_id not in self._dropped)

    def _cache_key(self, seg: LiveSegment) -> tuple:
        return (round(seg.start, 2), round(seg.end, 2), seg.text_tgt)

    def segment_for_clip(self, seg_id: int, gen: int, clip: object) -> LiveSegment | None:
        seg = self._segments.get(seg_id)
        if seg is not None and seg.gen == gen and self._clips.get(seg_id) is clip:
            return seg
        return None

    def _slot_end(self, seg: LiveSegment) -> float:
        cap = seg.end + self._overhang
        nexts = [s.start for s in self._segments.values()
                 if s.start > seg.start and self._dub_eligible(s)]
        return min(cap, min(nexts)) if nexts else cap

    def _slot_len(self, seg: LiveSegment) -> float:
        return max(0.1, self._slot_end(seg) - seg.start)

    def set_lead(self, lead_s: float) -> None:
        self._lead = lead_s

    def set_duck_latency(self, seconds: float) -> None:
        self._duck_latency = seconds

    def clip_ready(self, seg_id: int, gen: int, clip: object | None,
                   reason: str | None = None) -> bool:
        """Consume a synthesized clip (or a failure) for a requested segment."""
        seg = self._segments.get(seg_id)
        if seg is None or seg.gen != gen:
            return False
        if self._dub_state.get(seg_id) not in ("synth", "translated"):
            return False
        if clip is None:
            self._dub_state[seg_id] = "dropped"
            self._dub_dropped += 1
            return False
        self._clips[seg_id] = clip
        seg.clip = clip
        self._dub_state[seg_id] = "ready"
        self._clip_cache[self._cache_key(seg)] = clip
        return True

    def set_dub(self, on: bool) -> list[object]:
        self._dub = on
        actions: list[object] = []
        if not on:
            if self._playing is not None or self._preloaded is not None:
                actions.append(StopClip(0.18))
            self._playing = self._preloaded = None
            self._pacer_recovery_seg = None
            self._clip_paused = False
            if self._duck_target != 1.0:
                self._duck_target = 1.0
                actions.append(Duck(1.0))
            return actions
        for seg in self._segments.values():
            if self._dub_eligible(seg) and seg.seg_id not in self._dub_state:
                self._dub_state[seg.seg_id] = "translated"
        return actions

    def _finish_playing(self) -> None:
        if self._playing is not None:
            self._dub_state[self._playing] = "done"
            if self._pacer_recovery_seg == self._playing:
                self._pacer_recovery_seg = None
            self._playing = None
        self._clip_paused = False

    @property
    def pacer_recovery_pending(self) -> bool:
        return self._pacer_recovery_seg is not None

    def _next_ready(self, now: float, pacer_paused: bool = False) -> LiveSegment | None:
        tol = self._max_live_lag if self._mode == "live" else self._late_tol
        cands = [s for s in self._segments.values()
                 if self._dub_state.get(s.seg_id) == "ready"
                 and (s.start >= now - tol or
                      (pacer_paused and now - s.start <= self._max_live_lag))]
        return min(cands, key=lambda s: s.start) if cands else None

    def _imminent_clip(self, now: float) -> bool:
        return any(self._dub_state.get(s.seg_id) in ("ready", "preloaded")
                   and 0.0 <= s.start - now <= 0.6 for s in self._segments.values())

    def _dub_reset(self) -> list[object]:
        """Stop any clip and unduck (epoch change / seek)."""
        actions: list[object] = []
        if self._playing is not None or self._preloaded is not None:
            actions.append(StopClip(0.0))
        self._playing = self._preloaded = None
        self._pacer_recovery_seg = None
        self._clip_paused = False
        if self._duck_target != 1.0:
            self._duck_target = 1.0
            actions.append(Duck(1.0))
        return actions

    def _dub_freeze(self) -> list[object]:
        """Pause a playing clip while the media clock is invalid (load/seek)."""
        if self._playing is not None and not self._clip_paused:
            self._clip_paused = True
            return [PauseClip()]
        return []

    def _dub_actions(self, now: float, mono: float, main_running: bool,
                     main_speed: float, voice_state: str,
                     pacer_paused: bool = False) -> list[object]:
        actions: list[object] = []
        live = self._mode == "live"
        # Pause/resume the playing clip with the main transport, then detect end.
        if self._playing is not None:
            recovery_playing = (self._playing == self._pacer_recovery_seg
                                and pacer_paused)
            if recovery_playing and voice_state == "idle":
                self._finish_playing()
            elif not main_running and not recovery_playing:
                if not self._clip_paused:
                    self._clip_paused = True
                    actions.append(PauseClip())
            elif self._clip_paused and not recovery_playing:
                if now < self._expected_end:
                    self._clip_paused = False
                    actions.append(ResumeClip())
                else:
                    actions.append(StopClip(0.0))
                    self._finish_playing()
            elif voice_state == "idle":
                self._finish_playing()
            elif now >= self._expected_end + 1.0:
                actions.append(StopClip(0.0))
                self._finish_playing()
        # Request TTS for translated segments still inside their slot; also let a
        # "synth" that never produced a result expire, so a stuck or rejected
        # request cannot leave a permanent coverage hole (the pacer then waits
        # only for requests that can still arrive).
        in_flight = sum(1 for st in self._dub_state.values() if st == "synth")
        for seg in sorted(self._segments.values(), key=lambda s: s.start):
            st = self._dub_state.get(seg.seg_id)
            if st not in ("translated", "synth"):
                continue
            expired = (now - seg.start > self._max_live_lag) if live else (now >= self._slot_end(seg))
            if expired:
                self._dub_state[seg.seg_id] = "dropped"
                self._dub_dropped += 1
                continue
            if st == "synth":
                continue                      # already requested, awaiting a result
            if in_flight >= self._max_in_flight:
                continue
            rate = int(self._rate_for(seg.text_tgt, self._slot_len(seg)))
            if live:
                deadline = mono + max(0.5, seg.start + self._max_live_lag - now)
            else:
                # The deadline only bounds the network wait; the media-time "late"
                # rule below protects sync. While the picture is paused (the pacer
                # holding for coverage) there is no rush, so give TTS real time
                # instead of a sub-second deadline the first clip can never meet.
                floor = 0.5 if main_running else 4.0
                deadline = mono + max(floor, (seg.start - self._lead - now) / max(main_speed, 0.1))
            actions.append(RequestTts(seg.seg_id, seg.gen, seg.text_tgt, rate, deadline))
            self._dub_state[seg.seg_id] = "synth"
            in_flight += 1
        # Drop clips that missed their window (late in delayed, too far behind in live).
        for seg in list(self._segments.values()):
            if self._dub_state.get(seg.seg_id) not in ("ready", "preloaded"):
                continue
            if live:
                too_late, reason = now - seg.start > self._max_live_lag, "lag"
            else:
                too_late, reason = now > seg.start - self._lead + self._late_tol, "late"
            recover_late = (pacer_paused and not live
                            and now - seg.start <= self._max_live_lag)
            if recover_late and self._pacer_recovery_seg is None:
                self._pacer_recovery_seg = seg.seg_id
            if too_late:
                if recover_late:
                    continue
                if self._preloaded == seg.seg_id:
                    # The clip was loaded into the voice device: stop it so the
                    # device returns to idle, otherwise the session's voice_state
                    # stays "preloaded" forever and no further clip can start.
                    self._preloaded = None
                    actions.append(StopClip(0.0))
                actions.append(Drop(seg.seg_id, reason))
                self._dub_state[seg.seg_id] = "dropped"
                self._dub_dropped += 1
        # Preload the next ready clip when the voice device is free.
        if voice_state == "idle" and self._preloaded is None and self._playing is None:
            cand = self._next_ready(now, pacer_paused)
            if cand is not None:
                if live:
                    ready_to_preload = now - cand.start <= self._max_live_lag
                else:
                    ready_to_preload = (cand.start - self._preload_s <= now
                                        < cand.start - self._lead + self._late_tol
                                        or (pacer_paused
                                            and now - cand.start <= self._max_live_lag))
                if ready_to_preload:
                    clip = self._clips[cand.seg_id]
                    actions.append(PreloadClip(cand.seg_id, clip.path,
                                               getattr(clip, "voice_start_s", 0.0)))
                    self._dub_state[cand.seg_id] = "preloaded"
                    self._preloaded = cand.seg_id
                    if live and self._duck_target != self._duck_gain:
                        self._duck_target = self._duck_gain  # duck with the preload
                        actions.append(Duck(self._duck_gain))
        # Duck ahead of the preloaded clip (delayed mode only; live ducks above).
        if not live and self._preloaded is not None:
            seg = self._segments[self._preloaded]
            if (now >= seg.start - self._duck_latency - self._duck_ramp
                    and self._duck_target != self._duck_gain):
                self._duck_target = self._duck_gain
                actions.append(Duck(self._duck_gain))
        # Start the preloaded clip (at its lead time in delayed, at once in live).
        if self._preloaded is not None and voice_state == "preloaded":
            seg = self._segments[self._preloaded]
            clip = self._clips[seg.seg_id]
            slot_len = self._slot_len(seg)
            audible = getattr(clip, "audible_s", slot_len) or slot_len
            if live:
                start_now = True
                fit = min(self._max_speed, max(1.0, 1.0 + (now - seg.start) / 8.0))
                base = now
            else:
                start_now = (now >= seg.start - self._lead
                             or (pacer_paused and seg.seg_id == self._pacer_recovery_seg))
                fit = min(self._max_speed, max(1.0, audible / slot_len))
                base = now if seg.seg_id == self._pacer_recovery_seg else seg.start
            if start_now and (main_running or (pacer_paused
                                               and seg.seg_id == self._pacer_recovery_seg)):
                actions.append(StartClip(seg.seg_id, fit * main_speed))
                self._playing = seg.seg_id
                self._preloaded = None
                self._clip_paused = False
                self._dub_state[seg.seg_id] = "playing"
                self._expected_end = base + audible / max(fit, 0.1)
                self._voiced += 1
                self._margins.append(seg.start - self._lead - now)
                self._margins = self._margins[-32:]
        # Unduck after the clip ends, unless another clip is imminent.
        if self._playing is None and self._duck_target != 1.0 and not self._imminent_clip(now):
            if now >= self._expected_end + self._unduck_tail - self._duck_latency:
                self._duck_target = 1.0
                actions.append(Duck(1.0))
        return actions

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
             clock_epoch: int = 0, pacer_paused: bool = False) -> list[object]:
        actions: list[object] = []
        if now is None:  # invalid clock (loading / seeking)
            if self._shown is not None:
                self._shown = None
                actions.append(ClearSubtitle())
            if self._dub:
                actions.extend(self._dub_freeze())
            return actions
        if (clock_epoch != self._last_epoch and self._last_now is not None
                and abs(now - self._last_now) > 1.0):
            actions.extend(self.on_seek(now, 0))
        self._last_epoch = clock_epoch
        self._last_now = now
        # Caption path (only when subtitles are on).
        if self._subs:
            for seg in self._segments.values():
                if seg.seg_id not in self._arrival and self._caption_ready(seg):
                    self._arrival[seg.seg_id] = now
            visible = self._visible(now)
            if visible is None:
                if self._shown is not None:
                    self._shown = None
                    actions.append(ClearSubtitle())
            else:
                seg, page_idx, lines = visible
                key = (seg.seg_id, page_idx)
                if key != self._shown:
                    self._shown = key
                    self._shown_at = now
                    actions.append(ShowSubtitle(
                        seg.seg_id,
                        caption_ass(lines, font_px=self._font_px, italic=seg.italic)))
        elif self._shown is not None:
            self._shown = None
            actions.append(ClearSubtitle())
        # Dub path (independent of subtitles).
        if self._dub:
            actions.extend(self._dub_actions(now, mono, main_running, main_speed,
                                             voice_state, pacer_paused))
        return actions

    def _coverage_ready(self, seg: LiveSegment) -> bool:
        if not self._caption_ready(seg):
            return False
        if self._dub and self._dub_eligible(seg):
            # With dub on the FilePacer waits for the voice, not just the subtitle
            # (design 5.5), but only while the clip can still arrive: a dropped or
            # rejected segment must NOT leave a permanent hole that stalls the
            # pacer at frame 0. "translated"/"synth" are still pending; every other
            # state (ready/preloaded/playing/done/dropped) is resolved.
            return self._dub_state.get(seg.seg_id) not in ("translated", "synth")
        return True

    def ready_until(self, now: float) -> float:
        ready = sorted((s for s in self._segments.values() if self._coverage_ready(s)),
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

    @property
    def startup_ready(self) -> bool:
        """Whether at least one initial unit can be presented without a hole."""
        resolved = {"ready", "preloaded", "playing", "done", "dropped"}
        for seg in sorted(self._segments.values(), key=lambda item: item.start):
            if not self._caption_ready(seg):
                continue
            if (self._dub and self._dub_eligible(seg)
                    and self._dub_state.get(seg.seg_id) not in resolved):
                continue
            return True
        return False

    def on_seek(self, now: float, gen: int) -> list[object]:
        self._last_now = now
        # Clear the caption and let segments after the new position show again.
        for seg in self._segments.values():
            if seg.end > now:
                self._arrival.pop(seg.seg_id, None)
                self._dropped.discard(seg.seg_id)
        actions: list[object] = []
        if self._shown is not None:
            self._shown = None
            actions.append(ClearSubtitle())
        if self._dub:
            actions.extend(self._dub_reset())    # stop any clip, unduck
            # Segments after the new position play again: ready if the clip is
            # cached, else re-request from scratch.
            for seg in self._segments.values():
                if seg.end > now and self._dub_eligible(seg):
                    if self._dub_state.get(seg.seg_id) != "synth":
                        self._dub_state[seg.seg_id] = (
                            "ready" if seg.seg_id in self._clips else "translated")
                    # An in-flight request retains its original gen and filename.
                    # Reissuing it races os.replace and wastes a network request.
        return actions

    def covers(self, now: float) -> bool:
        """Whether a seek target already has a translated/caption fallback segment."""
        return any(s.start <= now < s.end and self._caption_ready(s)
                   for s in self._segments.values())

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
        return {
            "voiced": float(self._voiced),
            "dropped": float(len(self._dropped) + self._dub_dropped),
            "late": float(self._dub_dropped),
            "margin_p90": _percentile(self._margins, 90),
        }
