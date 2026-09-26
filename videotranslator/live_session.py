"""Live session controller (design 4.1-4.15). Part 1: config, status, factories
and the session-lock helpers.

The session wires the already-built pure modules (live_segment, live_asr,
live_translate, live_scheduler, live_sync, live_health, live_tts) with heavy
components injected through :class:`LiveFactories`, so the orchestration runs
against fakes with no ML / mpv / audio / network. This file holds the pure and
lock-only pieces; the threaded ``LiveSession`` orchestrator is added on top.

Status/warning/error codes stored here are the SHORT codes (``"busy"``,
``"need_source_lang"``, ``"rate_limited"``); the GUI maps them to i18n keys via
``live_health.STATUS_KEYS/WARN_KEYS/ERROR_KEYS``. No ``live_*`` UI-key literal
ever appears in this module.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .live_health import LIVE_STATES, WARN_KEYS, CircuitBreaker
from .platforms import pid_alive, process_start_token
from .player_settings import LiveSettings

_LOCK_NAME = "session.lock"


@dataclass(frozen=True)
class LiveConfig:
    """Immutable options for one live session.

    ``engine_opts`` (which carries the DeepL key) is excluded from ``repr`` so a
    traceback or a log line never leaks the key ([CC] G25).
    """

    source: str
    source_kind: str            # "file" | "url"
    start_at: float
    lang_source: str
    lang_target: str
    voice: str
    engine: str
    settings: LiveSettings
    session_dir: Path
    device_policy: str = "auto"   # "auto" | "cpu"
    hotwords: str | None = None
    engine_opts: dict = field(default_factory=dict, repr=False)


@dataclass
class LiveStatus:
    """4 Hz snapshot the GUI pulls (design 4.11 step 5). Mutable; the session
    hands out copies under a lock."""

    state: str = "starting"
    lag_s: float | None = None
    target_delay_s: float | None = None
    device: str = "cpu"
    engine: str = "marian"
    voiced: int = 0
    dropped: int = 0
    skipped_s: float = 0.0
    status_params: dict = field(default_factory=dict)  # extra {s}/{total}/{n}
    warning_key: str | None = None
    warning_params: dict = field(default_factory=dict)
    warning_action: str | None = None
    error_key: str | None = None
    error_params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LiveFactories:
    """Callables that build the heavy components; tests pass fakes.

    For a FILE session only ``decoder, vad, whisper, translator, tts, clock`` are
    used; ``resolve, ingest, store`` belong to the URL path (P6).
    """

    decoder: Callable[..., Any]
    vad: Callable[..., Any]
    whisper: Callable[..., Any]
    translator: Callable[..., Any]
    tts: Callable[..., Any]
    clock: Callable[[], float] = time.monotonic
    resolve: Callable[..., Any] | None = None
    ingest: Callable[..., Any] | None = None
    store: Callable[..., Any] | None = None
    timeouts: Any | None = None


def build_live_factories(cfg: LiveConfig,
                         *, log: Callable[[str], None] = lambda _m: None) -> LiveFactories:
    """Assemble the real heavy components for a live FILE session (design 4.7-4.9).

    Lazily imports PyAV / faster-Whisper / MarianMT so a machine without them
    still loads the module; the callables build one component each when the
    producer threads start. The online engines (google/deepl/ollama) are not
    wired yet, so ``translator`` currently supports MarianMT (offline, with a
    Hub check so an uncached pair can still be downloaded); another engine
    raises :class:`LiveTranslateError`, which the session surfaces as an error.
    """

    def make_decoder(source, **kw):
        from .live_asr import AudioDecoder
        return AudioDecoder(source, **kw)

    def make_vad():
        from .live_asr import StreamingVad
        return StreamingVad()

    def make_whisper(**kw):
        from .live_asr import PersistentWhisper
        return PersistentWhisper(log=log, **kw)

    def make_translator_for(engine):
        from .live_translate import _default_is_cached, default_hub_has, make_translator
        if engine == "marian":
            return make_translator("marian", is_cached=_default_is_cached,
                                   hub_has=default_hub_has)
        if engine == "ollama":
            return make_translator(
                "ollama", sync_mode=cfg.settings.sync_mode,
                api_url=cfg.engine_opts.get("ollama_url", "http://localhost:11434"),
                model=cfg.engine_opts.get("ollama_model", "qwen3:8b"))
        return make_translator(engine, **cfg.engine_opts)

    def make_synth(*, out_dir, breaker, thread_factory, clock):
        from .live_tts import EdgeClipSynth
        av_module = None
        try:                                # optional: measure leading silence for skip_s
            import av as av_module          # noqa: F811
        except Exception:
            av_module = None
        return EdgeClipSynth(
            cfg.voice, out_dir, breaker=breaker, av_module=av_module,
            thread_factory=thread_factory, clock=clock)

    return LiveFactories(
        decoder=make_decoder, vad=make_vad, whisper=make_whisper,
        translator=make_translator_for, tts=make_synth,
        clock=time.monotonic)


def build_live_config(values: dict, *, settings: LiveSettings, cache_dir: Path,
                      now: float) -> LiveConfig:
    """Assemble a :class:`LiveConfig` from GUI values. Pure.

    ``now`` is passed in (scripts/tests provide it) so the session directory name
    is deterministic. The DeepL key travels only in ``engine_opts``.
    """
    session_dir = Path(cache_dir) / f"session-{int(now * 1000)}"
    engine_opts = {}
    if values.get("deepl_key"):
        engine_opts["deepl_key"] = values["deepl_key"]
    if values.get("ollama_url"):
        engine_opts["ollama_url"] = values["ollama_url"]
    if values.get("ollama_model"):
        engine_opts["ollama_model"] = values["ollama_model"]
    return LiveConfig(
        source=values["source"],
        source_kind=values.get("source_kind", "file"),
        start_at=float(values.get("start_at", 0.0)),
        lang_source=values.get("lang_source", "auto"),
        lang_target=values["lang_target"],
        voice=values.get("voice", ""),
        engine=values.get("engine", settings.engine),
        settings=settings,
        session_dir=session_dir,
        device_policy=values.get("device_policy", "auto"),
        hotwords=values.get("hotwords") or None,
        engine_opts=engine_opts,
    )


def write_session_lock(path: Path, *, pid: int, start_token: str | None) -> None:
    """Write ``session.lock`` with the owner pid and its start token."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "token": start_token}), encoding="utf-8")


def read_session_lock(path: Path) -> tuple[int, str | None] | None:
    """Return ``(pid, token)`` from a lock file, or None if missing/unreadable."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return int(data["pid"]), data.get("token")
    except (OSError, ValueError, KeyError, TypeError):
        return None


def default_owner_alive(pid: int, token: str | None) -> bool:
    """A live pid whose start token still matches (protects a second instance)."""
    return pid_alive(pid) and process_start_token(pid) == token


def cleanup_stale_sessions(root: Path, *, owner_alive: Callable[[int, str | None], bool]
                           = default_owner_alive, now: float, max_age_h: float = 24.0,
                           remover: Callable[[str], None] = shutil.rmtree) -> list[Path]:
    """Remove dead session directories under ``root`` (design 4.15, [CC] G12).

    A directory with a lock whose owner is alive is never touched. A dead or
    recycled owner (token mismatch) is removed. When the lock is missing or
    unreadable, the directory is removed only if older than ``max_age_h``.
    """
    root = Path(root)
    removed: list[Path] = []
    if not root.exists():
        return removed
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        lock = read_session_lock(entry / _LOCK_NAME)
        if lock is not None:
            pid, token = lock
            if owner_alive(pid, token):
                continue
            drop = True
        else:
            try:
                age_h = (now - entry.stat().st_mtime) / 3600.0
            except OSError:
                continue
            drop = age_h > max_age_h
        if drop:
            try:
                remover(str(entry))
                removed.append(entry)
            except OSError:
                pass
    return removed


def _assert_state(state: str) -> str:
    """Guard used by the orchestrator: every published state is a known one."""
    if state not in LIVE_STATES:
        raise ValueError(f"unknown live state: {state!r}")
    return state


# --- Threaded orchestrator (design 4.11 live-sched). ------------------------
# Part 2: the scheduler loop that turns translated segments into caption/clip
# actions on the injected backend, paces a file, publishes a 4 Hz status and
# tears down cleanly. The decode/ASR/MT producer threads are wired on top; here
# the loop consumes `sched_in` (translated LiveSegments), so it is unit-testable
# by feeding that queue and calling `_tick_once` with no threads and a fake clock.

import os
import queue
import threading


@dataclass(frozen=True)
class _PipelineEnd:
    gen: int

from .live_scheduler import (
    ClearSubtitle, ClipSpeed, Drop, DubScheduler, Duck, DuckEnvelope, LiveSegment,
    PauseClip, PreloadClip, RequestTts, ResumeClip, ShowSubtitle, StartClip, StopClip,
)
from .live_sync import FilePacer, derive_live_timing
from .live_translate import TIMEOUTS_S, LiveTranslateError
from .live_tts import LiveTtsUnavailable


class LiveSession:
    """Owns the live worker threads and the orchestration state (design 4.1)."""

    def __init__(self, cfg: LiveConfig, *, video: Any, clock_view: Any,
                 factories: LiveFactories, voice: Any = None,
                 thread_factory: Callable[..., Any] = threading.Thread,
                 log: Callable[[str], None] = lambda _m: None,
                 device: str = "cpu", tick_interval: float = 0.02) -> None:
        self._cfg = cfg
        self._video = video
        self._voice = voice
        self._clock_view = clock_view
        self._factories = factories
        self._thread_factory = thread_factory
        self._log = log
        self._clock = factories.clock
        self._tick_interval = tick_interval

        s = cfg.settings
        self._timing = derive_live_timing(
            s.delay_s if s.delay_s is not None else (s.file_ahead_s or 8.0),
            mode=s.sync_mode, device=device, engine=cfg.engine, dub=s.dub_enabled)
        from .live_tts import EdgeDurationModel, choose_rate
        from .timing import estimate_tts_duration_s
        from .tts_text_sanitizer import sanitize_for_tts
        # Speed the TTS to fit the slot (was hard +0%: long translations overran
        # and dropped the next clip) and use the user's duck level (was fixed 0.3).
        self._dur_model = EdgeDurationModel(cfg.lang_target,
                                            seed_estimate=estimate_tts_duration_s)
        self._scheduler = DubScheduler(
            mode=s.sync_mode, overhang_s=0.6, merge_gap_s=0.6,
            dub=s.dub_enabled, subs=s.subs_enabled, duck_gain=s.duck_level,
            rate_for=lambda text, slot: choose_rate(sanitize_for_tts(text), slot,
                                                    self._dur_model))
        self._pacer = FilePacer(mode=s.sync_mode, min_ahead_s=self._timing.min_ahead_s,
                                resume_ahead_s=self._timing.resume_ahead_s)

        from .live_asr import HallucinationFilter, LanguageLock
        from .live_segment import SentenceAssembler, UtteranceSegmenter
        self._segmenter = UtteranceSegmenter(max_len_s=self._timing.umax_s)
        self._segmenter.reset(0)
        self._assembler = SentenceAssembler(hold_s=self._timing.hold_s)
        self._langlock = LanguageLock(cfg.lang_source)
        self._hallucination = HallucinationFilter()
        self._device = device

        self._utt_q: queue.Queue = queue.Queue(maxsize=8)
        self._mt_q: queue.Queue = queue.Queue(maxsize=64)
        self._sched_in: queue.Queue = queue.Queue(maxsize=256)
        self._control: queue.Queue = queue.Queue()
        self._decode_cancel = threading.Event()
        self._decode_lock = threading.Lock()
        self._decode_request = (0, cfg.start_at, self._decode_cancel)
        self._decode_wake = threading.Event()
        self._seg_id = 0
        self._seg_id_lock = threading.Lock()
        self._stop = threading.Event()
        self._threads: list[Any] = []
        self._gen = 0
        self._self_paused = False
        self._user_paused = False
        self._source_done = False
        self._last_pacer_mono = -1e9
        self._last_status_mono = -1e9
        self._overlay: str | None = None

        # Dub/voice state (design 4.11). The voice backend and the TTS worker are
        # created lazily on start(); the scheduler drives them through _execute.
        self._synth: Any = None
        self._voice_state = "idle"          # idle | preloaded | playing
        self._bridge = getattr(video, "bridge", None)
        self._last_eof_count = 0
        self._voice_fail = 0
        self._duck_env = DuckEnvelope(ramp_s=0.2)
        self._duck_applied = 1.0
        self._mix_version = -1

        self._status_lock = threading.Lock()
        self._status = LiveStatus(
            state="starting", engine=cfg.engine, device=device,
            target_delay_s=self._timing_delay())

    # -- public control surface (setters only enqueue) ----------------------

    def start(self) -> None:
        self._cfg.session_dir.mkdir(parents=True, exist_ok=True)
        pid = os.getpid()
        write_session_lock(self._cfg.session_dir / _LOCK_NAME, pid=pid,
                           start_token=process_start_token(pid))
        self._start_dub()
        # The voice backend lives for the whole app run and the bridge keeps the
        # last session's end marker; snapshot it so a stale marker does not close
        # this session's first clip after one tick.
        if self._bridge is not None:
            marker = self._bridge.extra("voice-eof")
            self._last_eof_count = marker[0][0] if marker else 0
        self._set_state("running")
        targets = [("live-sched", self._sched_loop)]
        # A file OR a resolved VOD stream URL is decoded the same way: PyAV opens
        # a local path or an HTTP URL. (A growing live broadcast, P6, would need a
        # dedicated ingest instead.)
        if self._cfg.source_kind in ("file", "url"):
            targets = [("live-decode", self._decode_loop),
                       ("live-asr", self._asr_loop),
                       ("live-mt", self._mt_loop),
                       ("live-sched", self._sched_loop)]
        for name, fn in targets:
            thread = self._thread_factory(target=fn, name=name, daemon=True)
            self._threads.append(thread)
            thread.start()

    def _start_dub(self) -> None:
        """Start the TTS worker for the dub on start(), degrading if it is absent.

        If the voice backend or edge-tts is missing, the dub is turned off for the
        session and subtitles keep working (design row 21).
        """
        if not self._cfg.settings.dub_enabled:
            return
        if self._voice is None:
            # Dub was requested but no voice backend was provided (libmpv failed
            # to build a second instance): turn the dub off so the scheduler stops
            # requesting clips, which would otherwise stall the pacer forever.
            self._disable_dub("tts_unavailable")
            return
        self._ensure_synth()

    def _ensure_synth(self) -> bool:
        """Create, start and register the TTS worker; return True on success."""
        if self._synth is not None:
            return True
        if self._voice is None:
            return False
        try:
            synth = self._factories.tts(
                out_dir=self._cfg.session_dir / "clips", breaker=CircuitBreaker(),
                thread_factory=self._thread_factory, clock=self._clock)
            if synth is None:
                self._disable_dub(None)
                return False
            synth.start()
        except LiveTtsUnavailable:
            self._disable_dub("tts_unavailable")
            return False
        except Exception as exc:            # noqa: BLE001 - never block the session
            self._log(f"live: TTS worker unavailable ({exc}); dub off")
            self._disable_dub(None)
            return False
        self._synth = synth
        # The scheduler now owns the video volume so the Tk mixer defers to the duck.
        mixer = getattr(self._video, "mixer", None)
        if mixer is not None:
            try:
                mixer.set_owner("sched")
            except Exception:
                pass
        return True

    def _disable_dub(self, warn_code: str | None) -> None:
        # Keep the worker: set_dub(False) stops new RequestTts, join() stops the
        # thread. Nulling it here would leak the live-tts thread and event loop on
        # every runtime dub toggle (review finding 7).
        self._execute(self._scheduler.set_dub(False))
        if warn_code is not None:
            self._set_warning(warn_code, "edge-tts")

    def request_stop(self) -> None:
        self._set_state("stopping")
        self._decode_cancel.set()
        self._stop.set()
        self._decode_wake.set()

    def join(self, timeout_s: float) -> bool:
        deadline = self._clock() + timeout_s
        ok = True
        stuck = []
        for thread in self._threads:
            remaining = max(0.0, deadline - self._clock())
            thread.join(remaining)
            if thread.is_alive():
                ok = False
                stuck.append(thread.name)
        if self._synth is not None:
            try:
                if not self._synth.stop(max(0.0, deadline - self._clock())):
                    ok = False
                    stuck.append("live-tts")
            except Exception:
                ok = False
        mixer = getattr(self._video, "mixer", None)
        if mixer is not None:
            try:
                mixer.set_owner("cmd")
                mixer.set_original_muted(False)
                # Re-assert the user volume through the command path now that the
                # scheduler no longer owns the mixer, so the player does not stay
                # at the ducked level after the session ends (review finding 5).
                self._video.apply_mix()
            except Exception:
                pass
        if stuck:
            # The state still goes to stopped so the GUI can start again, but a
            # thread that outlived the join (e.g. a model still in VRAM) is worth
            # flagging: a new session then briefly runs two of them (review S8).
            self._log(f"live: threads still alive after join: {', '.join(stuck)}")
        with self._status_lock:
            if self._status.state != "failed":
                self._status.state = "stopped"
        return ok

    def set_sync_mode(self, mode: str) -> None:
        self._control.put(("mode", mode))

    def set_delay(self, seconds: float) -> None:
        self._control.put(("delay", float(seconds)))

    def set_engine(self, engine: str) -> None:
        self._control.put(("engine", engine))

    def set_dub_enabled(self, on: bool) -> None:
        self._control.put(("dub", bool(on)))

    def set_subs_enabled(self, on: bool) -> None:
        self._control.put(("subs", bool(on)))

    def notify_user_seek(self, t: float) -> None:
        self._control.put(("seek", float(t)))

    def notify_user_pause(self, paused: bool) -> None:
        self._control.put(("pause", bool(paused)))

    def toggle_user_pause(self) -> None:
        """Toggle user intent on the scheduler thread, independent of pacer pauses."""
        self._control.put(("pause_toggle", None))

    def set_original_muted(self, muted: bool) -> None:
        self._control.put(("original_mute", bool(muted)))

    def submit_segment(self, seg: LiveSegment) -> None:
        """Producer entry point (the MT thread; tests call it directly)."""
        try:
            self._sched_in.put_nowait(seg)
        except queue.Full:
            pass

    def status(self) -> LiveStatus:
        with self._status_lock:
            st = self._status
            return LiveStatus(
                state=st.state, lag_s=st.lag_s, target_delay_s=st.target_delay_s,
                device=st.device, engine=st.engine, voiced=st.voiced, dropped=st.dropped,
                skipped_s=st.skipped_s, status_params=dict(st.status_params),
                warning_key=st.warning_key, warning_params=dict(st.warning_params),
                warning_action=st.warning_action, error_key=st.error_key,
                error_params=dict(st.error_params))

    # -- internals ----------------------------------------------------------

    def _timing_delay(self) -> float:
        s = self._cfg.settings
        return s.delay_s if s.delay_s is not None else (s.file_ahead_s or 8.0)

    def _set_state(self, state: str) -> None:
        with self._status_lock:
            self._status.state = _assert_state(state)

    def _sched_loop(self) -> None:
        try:
            while not self._stop.is_set():
                self._tick_once(self._clock())
                self._stop.wait(self._tick_interval)
        finally:
            self._teardown_outputs()

    def _teardown_outputs(self) -> None:
        """Clear the caption, stop any voice clip and un-duck when the loop ends.

        mpv's osd-overlay and the ducked volume persist across loadfile, so a
        stopped or failed session must not leave the last subtitle on screen, a
        clip still playing, or the original audio attenuated on the next video.
        Safe after the backend is terminated (rt calls become no-ops).
        """
        mixer = getattr(self._video, "mixer", None)
        if mixer is not None:
            mixer.set_original_muted(False)
        rt = getattr(self._video, "rt", None)
        if rt is not None:
            try:
                rt.set_overlay(None)
            except Exception:
                pass
            if self._duck_applied != 1.0 or mixer is not None:
                try:
                    rt.set_duck(1.0)
                except Exception:
                    pass
                self._duck_applied = 1.0
        if self._voice is not None and self._voice_state != "idle":
            try:
                self._voice.stop()
            except Exception:
                pass
            self._voice_state = "idle"
        self._overlay = None

    def _tick_once(self, mono: float) -> list[object]:
        self._drain_control(mono)
        self._drain_sched_in()
        self._drain_synth()
        now = self._clock_view.now(mono)
        epoch = getattr(self._clock_view, "epoch", 0)
        if mono - self._last_pacer_mono >= 1.0:
            self._last_pacer_mono = mono
            self._run_pacer(now)
        # The voice freezes whenever the picture is paused, by the user or by the
        # file pacer catching translation up.
        main_running = not (self._user_paused or self._self_paused)
        self._sync_voice_state()
        actions = self._scheduler.tick(now, mono, main_running=main_running,
                                       main_speed=1.0, voice_state=self._voice_state,
                                       clock_epoch=epoch)
        self._execute(actions)
        self._apply_duck(frozen=not main_running)
        if mono - self._last_status_mono >= 0.25:
            self._last_status_mono = mono
            self._publish_status(now)
            self._reassert_mixer()
        return actions

    def _reassert_mixer(self) -> None:
        """While the scheduler owns the mixer, apply user volume/mute changes.

        With owner 'sched' the Tk apply_mix defers, so a volume or mute change
        would otherwise not take until the next duck ramp, and the voice would
        follow neither. Re-write on the mixer version bump (design 4.13).
        """
        mixer = getattr(self._video, "mixer", None)
        if mixer is None:
            return
        st = mixer.snapshot()
        if st.owner != "sched" or st.version == self._mix_version:
            return
        self._mix_version = st.version
        rt = getattr(self._video, "rt", None)
        if rt is not None:
            rt.set_duck(self._duck_env.current)     # user volume at the current duck
        if self._voice is not None:
            self._voice.set_volume(st.voice_volume)  # 0 when muted

    def _drain_synth(self) -> None:
        """Hand synthesized clips (or failures) to the scheduler."""
        if self._synth is None:
            return
        while True:
            try:
                seg_id, gen, clip, reason = self._synth.results.get_nowait()
            except queue.Empty:
                return
            except Exception:
                return
            accepted = self._scheduler.clip_ready(seg_id, gen, clip, reason)
            if accepted:
                seg = self._scheduler.segment_for_clip(seg_id, gen, clip)
                if seg is not None:
                    from .tts_text_sanitizer import sanitize_for_tts
                    self._dur_model.observe(sanitize_for_tts(seg.text_tgt),
                                            int(clip.rate.rstrip("%")), clip.audible_s)

    def _sync_voice_state(self) -> None:
        """Consume the voice end marker and flip to idle when a CLIP ends.

        Every new marker must be consumed in any state, or a marker that arrives
        while not "playing" (our own StopClip/loadfile, which report reason
        "stop") goes stale and, read one tick into the next clip, cuts it short.
        A "stop" reason is our own doing, not a clip end; "error" feeds the
        dub-off rule (design row 21).
        """
        if self._bridge is None:
            return
        marker = self._bridge.extra("voice-eof")
        if marker is None:
            return
        count, reason = marker[0]
        if count <= self._last_eof_count:
            return
        self._last_eof_count = count            # consumed in EVERY state
        if reason == "stop":
            return                              # our own stop/loadfile, not a clip end
        if reason == "error":
            self._voice_fail += 1
            self._voice_state = "idle"
            if self._voice_fail >= 3:
                self._disable_dub("tts_unavailable")
            return
        if self._voice_state == "playing":
            self._voice_state = "idle"

    def _drain_control(self, mono: float) -> None:
        while True:
            try:
                kind, value = self._control.get_nowait()
            except queue.Empty:
                return
            if kind == "mode":
                self._scheduler.set_mode(value)
                self._pacer.set_mode(value)
            elif kind == "subs":
                self._execute(self._scheduler.set_subs(value))
            elif kind == "original_mute":
                mixer = getattr(self._video, "mixer", None)
                if mixer is not None:
                    mixer.set_original_muted(value)
                    rt = getattr(self._video, "rt", None)
                    if rt is not None:
                        rt.set_duck(self._duck_env.current)
                    self._reassert_mixer()
            elif kind in ("pause", "pause_toggle"):
                self._user_paused = (not self._user_paused if kind == "pause_toggle"
                                     else value)
                # The scheduler is the only pause writer during a live session.
                # Resuming user intent cannot override buffering owned by the pacer.
                self._run_pacer(self._clock_view.now(mono))
                rt = getattr(self._video, "rt", None)
                if rt is not None:
                    rt.set_pause(self._user_paused or self._self_paused)
            elif kind == "seek":
                if not self._scheduler.covers(value):
                    with self._decode_lock:
                        self._gen += 1
                        self._source_done = False
                        self._decode_cancel.set()
                        self._decode_cancel = threading.Event()
                        self._decode_request = (self._gen, max(0.0, value - 0.5),
                                                self._decode_cancel)
                        self._decode_wake.set()
                self._execute(self._scheduler.on_seek(value, self._gen))
                self._last_pacer_mono = -1e9
            elif kind == "engine":
                with self._status_lock:
                    self._status.engine = value
            elif kind == "dub":
                if value:
                    if self._ensure_synth():
                        self._execute(self._scheduler.set_dub(True))
                else:
                    self._disable_dub(None)
            # "delay" refines the timing; applied by the pipeline.

    def _drain_sched_in(self) -> None:
        while True:
            try:
                seg = self._sched_in.get_nowait()
            except queue.Empty:
                return
            if getattr(seg, "gen", 0) < self._gen:
                continue  # stale generation, dropped by the consumer
            self._scheduler.upsert(seg)

    def _execute(self, actions: list[object]) -> None:
        rt = getattr(self._video, "rt", None)
        for action in actions:
            if isinstance(action, ShowSubtitle):
                self._overlay = action.ass
                if rt is not None:
                    rt.set_overlay(action.ass)
            elif isinstance(action, ClearSubtitle):
                self._overlay = None
                if rt is not None:
                    rt.set_overlay(None)
            elif isinstance(action, RequestTts):
                ok = self._synth is not None and self._synth.submit(
                    action.seg_id, action.gen, action.text,
                    action.rate_pct, action.deadline_mono)
                if not ok:
                    # Rejected (no worker, breaker open, in-flight full, deadline
                    # passed): mark it dropped now so it never stays "synth" and
                    # stalls the pacer waiting for a result that will not come.
                    self._scheduler.clip_ready(action.seg_id, action.gen, None,
                                               "rejected")
            elif isinstance(action, PreloadClip):
                if self._voice is not None:
                    self._voice.preload(action.path, skip_s=action.skip_s)
                self._voice_state = "preloaded"
            elif isinstance(action, StartClip):
                if self._voice is not None:
                    self._voice.start(action.speed)
                self._voice_state = "playing"
            elif isinstance(action, ClipSpeed):
                if self._voice is not None:
                    self._voice.set_speed(action.value)
            elif isinstance(action, PauseClip):
                if self._voice is not None:
                    self._voice.set_pause(True)
            elif isinstance(action, ResumeClip):
                if self._voice is not None:
                    self._voice.set_pause(False)
            elif isinstance(action, StopClip):
                if self._voice is not None:
                    self._voice.stop()
                self._voice_state = "idle"
            elif isinstance(action, Duck):
                self._duck_env.set_target(action.gain)
            elif isinstance(action, Drop):
                self._log(f"live: clip {action.seg_id} dropped ({action.reason})")

    def _apply_duck(self, *, frozen: bool) -> None:
        """Ramp the original audio toward the scheduler's duck target each tick.

        The ramp lives here (not in the backend) so it is smooth on every platform
        and on mpv < 0.37; the value is written only when it actually moves.
        """
        gain = self._duck_env.step(frozen=frozen)
        if gain is None:
            return
        rt = getattr(self._video, "rt", None)
        if rt is not None and abs(gain - self._duck_applied) >= 0.001:
            self._duck_applied = gain
            rt.set_duck(gain)

    def _run_pacer(self, now: float | None) -> None:
        action = self._pacer.step(
            player=now, ready_until=self._scheduler.ready_until(now or 0.0),
            source_done=self._source_done, user_paused=self._user_paused,
            self_paused=self._self_paused)
        rt = getattr(self._video, "rt", None)
        if action.kind == "pause":
            self._self_paused = True
            if rt is not None:
                rt.set_pause(True)
        elif action.kind == "resume":
            self._self_paused = False
            if rt is not None:
                rt.set_pause(False)

    def _publish_status(self, now: float | None) -> None:
        metrics = self._scheduler.metrics()
        with self._status_lock:
            self._status.voiced = int(metrics.get("voiced", 0))
            self._status.dropped = int(metrics.get("dropped", 0))
            self._status.target_delay_s = self._timing_delay()

    # -- producer threads (design 4.7-4.9): decode -> asr -> mt -> sched_in ----

    def _next_seg_id(self) -> int:
        with self._seg_id_lock:
            self._seg_id += 1
            return self._seg_id

    def _put_utt(self, utt) -> None:
        while not self._stop.is_set():
            if utt.gen != self._gen:
                return
            try:
                self._utt_q.put(utt, timeout=0.2)
                return
            except queue.Full:
                continue

    def _emit_segment(self, start, end, src, tgt, *, italic, gen=None, seg_id=None) -> None:
        seg = LiveSegment(
            seg_id if seg_id is not None else self._next_seg_id(),
            gen if gen is not None else self._gen, start, end, src,
            text_tgt=tgt, italic=italic,
            dub_ok=(tgt is not None and self._cfg.settings.dub_enabled))
        self.submit_segment(seg)

    def _fail(self, error_key: str, detail: str) -> None:
        with self._status_lock:
            self._status.error_key = error_key
            self._status.error_params = {"detail": detail} if detail else {}
            self._status.state = "failed"
        self._decode_cancel.set()
        self._stop.set()

    def _set_warning(self, code: str, engine: str) -> None:
        with self._status_lock:
            self._status.warning_key = WARN_KEYS.get(code, code)
            self._status.warning_params = {"engine": engine}
            self._status.warning_action = None

    def _clear_warning(self) -> None:
        with self._status_lock:
            if self._status.warning_key is not None:
                self._status.warning_key = None
                self._status.warning_params = {}
                self._status.warning_action = None

    def _decode_loop(self) -> None:
        try:
            vad = self._factories.vad()
            while not self._stop.is_set():
                with self._decode_lock:
                    gen, start_at, cancel = self._decode_request
                    self._decode_wake.clear()
                self._segmenter.reset(gen)  # decoder exclusively owns the segmenter
                if hasattr(vad, "reset"):
                    vad.reset()
                decoder = None
                try:
                    decoder = self._factories.decoder(
                        self._cfg.source, start_at=start_at, time_domain="rebased")
                    for block_start, samples in decoder.blocks(cancel):
                        if self._stop.is_set() or cancel.is_set():
                            break
                        probs = vad.probs(samples)
                        for utt in self._segmenter.push(block_start, samples, probs):
                            self._put_utt(utt)
                    if not cancel.is_set():
                        for utt in self._segmenter.flush():
                            self._put_utt(utt)
                        self._put_utt(_PipelineEnd(gen))
                except Exception:
                    if not cancel.is_set():
                        raise
                finally:
                    if decoder is not None:
                        try:
                            decoder.close()
                        except Exception:
                            pass
                # Keep the worker available for a seek after EOF; no second ASR model.
                while not self._stop.is_set() and not self._decode_wake.wait(0.2):
                    pass
        except Exception as exc:            # noqa: BLE001 - surfaced as a live error
            self._fail("asr", str(exc))

    def _put_sentence(self, sentence) -> None:
        while not self._stop.is_set() and sentence.gen == self._gen:
            try:
                self._mt_q.put(sentence, timeout=0.2)
                return
            except queue.Full:
                pass

    def _asr_loop(self) -> None:
        whisper = None
        media_edge = 0.0
        try:
            whisper = self._factories.whisper(
                device_policy=self._cfg.device_policy, hotwords=self._cfg.hotwords)
            # Report the device Whisper actually loaded on (the GUI defaults to
            # "cpu"; on a GPU box the model picks "cuda"), so the badge is honest.
            actual = getattr(whisper, "device", None)
            if actual:
                with self._status_lock:
                    self._status.device = actual
            while not self._stop.is_set():
                try:
                    utt = self._utt_q.get(timeout=0.2)
                except queue.Empty:
                    for sentence in self._assembler.edge(media_edge):
                        self._put_sentence(sentence)
                    continue
                if utt.gen != self._gen:
                    continue
                if self._assembler._gen != utt.gen:
                    self._assembler.reset(utt.gen)
                    from .live_asr import HallucinationFilter
                    self._hallucination = HallucinationFilter()
                    media_edge = 0.0
                if isinstance(utt, _PipelineEnd):
                    for sentence in self._assembler.edge(1e12):
                        self._put_sentence(sentence)
                    self._put_sentence(utt)
                    continue
                segs, lang, prob = whisper.transcribe(utt, language=self._langlock.locked)
                if utt.gen != self._gen:
                    continue  # seek completed while the model was transcribing
                media_edge = max(media_edge, float(utt.end))
                state = self._langlock.observe(lang, prob, max(0.0, utt.end - utt.start))
                segs = self._hallucination.filter(segs)
                if state == "failed":
                    self._fail("need_source_lang", "")
                    break
                if self._langlock.locked is None:
                    for seg in segs:            # pre-lock: source text, italic, no dub
                        self._emit_segment(seg["start"], seg["end"], seg["text"], None,
                                           italic=True, gen=utt.gen)
                    continue
                pieces = [{"start": s["start"], "end": s["end"], "text": s["text"],
                           "flags": ()} for s in segs]
                for sentence in self._assembler.push(pieces, utt.gen):
                    self._put_sentence(sentence)
        except Exception as exc:            # noqa: BLE001
            self._fail("asr", str(exc))
        finally:
            if whisper is not None:
                try:
                    whisper.close()
                except Exception:
                    pass

    def _mt_loop(self) -> None:
        translator = None
        prepared = False
        key = self._cfg.engine
        if key == "ollama":
            key = "ollama_live" if self._cfg.settings.sync_mode == "live" else "ollama_delayed"
        timeout = TIMEOUTS_S.get(key, 5.0)
        breaker = CircuitBreaker()
        try:
            translator = self._factories.translator(self._cfg.engine)
            online = bool(getattr(translator, "online", False))
            while not self._stop.is_set():
                try:
                    sentence = self._mt_q.get(timeout=0.2)
                except queue.Empty:
                    continue
                if getattr(sentence, "gen", 0) < self._gen:
                    continue
                if isinstance(sentence, _PipelineEnd):
                    with self._decode_lock:
                        if sentence.gen == self._gen:
                            self._source_done = True
                    continue
                if not prepared:
                    src = self._langlock.locked or self._cfg.lang_source
                    translator.prepare(src, self._cfg.lang_target)
                    prepared = True
                # An online engine whose breaker is open keeps the original text
                # (shown in the source language) without spending a call.
                if online and not breaker.allow():
                    self._emit_segment(sentence.start, sentence.end, sentence.text,
                                       None, italic=True, gen=sentence.gen,
                                       seg_id=None)
                    continue
                outcome = translator.translate(sentence.text, context=(),
                                               timeout_s=timeout)
                if sentence.gen != self._gen:
                    continue
                if online:
                    if outcome.ok:
                        breaker.record_success()
                        self._clear_warning()
                    else:
                        warn = breaker.record_failure(kind=outcome.error or "error")
                        if warn:
                            self._set_warning(warn, self._cfg.engine)
                self._emit_segment(
                    sentence.start, sentence.end, sentence.text,
                    outcome.text if outcome.ok else None, italic=not outcome.ok,
                    gen=sentence.gen, seg_id=None)
        except LiveTranslateError as exc:
            self._fail(exc.key, "")
        except Exception as exc:            # noqa: BLE001
            self._fail("internal", str(exc))
        finally:
            if translator is not None:
                try:
                    translator.close()
                except Exception:
                    pass
