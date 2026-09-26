import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from videotranslator.live_session import (
    LiveConfig,
    LiveStatus,
    build_live_config,
    cleanup_stale_sessions,
    read_session_lock,
    write_session_lock,
)
from videotranslator.live_health import LIVE_STATES
from videotranslator.player_settings import normalize_live_settings

SETTINGS = normalize_live_settings({})


class LiveConfigTests(unittest.TestCase):
    def test_repr_hides_the_deepl_key(self):
        cfg = build_live_config(
            {"source": "/v.mp4", "lang_target": "it", "deepl_key": "SECRET-KEY-123"},
            settings=SETTINGS, cache_dir=Path("/tmp/cache"), now=1000.0)
        self.assertEqual(cfg.engine_opts["deepl_key"], "SECRET-KEY-123")
        self.assertNotIn("SECRET-KEY-123", repr(cfg))
        self.assertNotIn("deepl_key", repr(cfg))

    def test_build_is_deterministic(self):
        values = {"source": "/v.mp4", "lang_target": "it"}
        a = build_live_config(values, settings=SETTINGS, cache_dir=Path("/c"), now=1234.5)
        b = build_live_config(values, settings=SETTINGS, cache_dir=Path("/c"), now=1234.5)
        self.assertEqual(a.session_dir, b.session_dir)
        self.assertEqual(a.session_dir, Path("/c/session-1234500"))

    def test_no_deepl_key_means_empty_engine_opts(self):
        cfg = build_live_config({"source": "s", "lang_target": "it"},
                                settings=SETTINGS, cache_dir=Path("/c"), now=1.0)
        self.assertEqual(cfg.engine_opts, {})


class LiveStatusTests(unittest.TestCase):
    def test_default_state_is_valid(self):
        self.assertIn(LiveStatus().state, LIVE_STATES)


class SessionLockTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.lock"
            write_session_lock(path, pid=4321, start_token="tok-9")
            self.assertEqual(read_session_lock(path), (4321, "tok-9"))

    def test_missing_or_corrupt_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read_session_lock(Path(tmp) / "nope.lock"))
            bad = Path(tmp) / "bad.lock"
            bad.write_text("{not json", encoding="utf-8")
            self.assertIsNone(read_session_lock(bad))


class CleanupStaleSessionsTests(unittest.TestCase):
    def _session(self, root, name, *, lock=None, mtime=None):
        d = Path(root) / name
        d.mkdir()
        if lock is not None:
            write_session_lock(d / "session.lock", pid=lock[0], start_token=lock[1])
        if mtime is not None:
            os.utime(d, (mtime, mtime))
        return d

    def test_keeps_alive_owner_removes_dead_and_recycled(self):
        now = 1_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            self._session(tmp, "alive", lock=(10, "t10"))
            self._session(tmp, "dead", lock=(11, "t11"))
            self._session(tmp, "recycled", lock=(12, "t12"))
            removed = []

            def owner_alive(pid, token):
                return pid == 10 and token == "t10"

            got = cleanup_stale_sessions(
                tmp, owner_alive=owner_alive, now=now,
                remover=lambda p: removed.append(Path(p).name))
            self.assertEqual({p.name for p in got}, {"dead", "recycled"})
            self.assertEqual(set(removed), {"dead", "recycled"})

    def test_missing_lock_removed_only_when_old(self):
        now = 1_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            self._session(tmp, "old", mtime=now - 25 * 3600)
            self._session(tmp, "young", mtime=now - 3600)
            removed = []
            got = cleanup_stale_sessions(
                tmp, owner_alive=lambda p, t: False, now=now, max_age_h=24.0,
                remover=lambda p: removed.append(Path(p).name))
            self.assertEqual({p.name for p in got}, {"old"})

    def test_missing_root_is_empty(self):
        self.assertEqual(cleanup_stale_sessions(
            Path("/no/such/root"), owner_alive=lambda p, t: True, now=0.0), [])


import threading
import time
from types import SimpleNamespace

from videotranslator.live_session import LiveFactories, LiveSession
from videotranslator.live_scheduler import LiveSegment


class _FakeRt:
    def __init__(self):
        self.overlays = []
        self.pauses = []
        self.ducks = []

    def set_overlay(self, ass):
        self.overlays.append(ass)

    def set_pause(self, paused):
        self.pauses.append(paused)

    def set_speed(self, _x):
        pass

    def set_duck(self, g):
        self.ducks.append(g)


class _FakeClockView:
    def __init__(self, media=0.0):
        self.media = media
        self.epoch = 0

    def now(self, _mono):
        return self.media


def _factories():
    noop = lambda *a, **k: None
    return LiveFactories(decoder=noop, vad=noop, whisper=noop, translator=noop,
                         tts=noop, clock=time.monotonic)


def _session(tmp, *, media=1.5, overrides=None):
    settings = normalize_live_settings(
        {"live_dub_enabled": False, "live_subs_enabled": True,
         "live_sync_mode": "delayed", **(overrides or {})})
    cfg = build_live_config({"source": "/v.mp4", "lang_target": "it"},
                            settings=settings, cache_dir=Path(tmp), now=1.0)
    video = SimpleNamespace(rt=_FakeRt())
    sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(media),
                       factories=_factories())
    return sess, video, cfg


def _seg(tgt="ciao", *, gen=0, start=1.0, end=3.0):
    return LiveSegment(0, gen, start, end, "hello", text_tgt=tgt)


class LiveSessionTickTests(unittest.TestCase):
    def test_translated_segment_becomes_a_caption(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp, media=1.5)
            sess.submit_segment(_seg("ciao"))
            sess._tick_once(0.0)
            self.assertTrue(any("ciao" in (a or "") for a in video.rt.overlays))

    def test_stale_generation_segment_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp, media=1.5)
            sess.notify_user_seek(9.0)          # gen -> 1
            sess._tick_once(0.0)
            sess.submit_segment(_seg("old", gen=0))  # stale
            sess._tick_once(0.02)
            self.assertFalse(any("old" in (a or "") for a in video.rt.overlays))

    def test_subtitles_off_clears_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp, media=1.5)
            sess.submit_segment(_seg("ciao"))
            sess._tick_once(0.0)
            sess.set_subs_enabled(False)
            sess._tick_once(0.02)
            self.assertIsNone(video.rt.overlays[-1])   # last action cleared it

    def test_pacer_pauses_when_coverage_nearly_caught_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp, media=2.9)
            sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
            sess._tick_once(0.0)               # pacer runs (first time)
            self.assertIn(True, video.rt.pauses)

    def test_status_copy_is_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)
            snap = sess.status()
            snap.state = "mutated"
            self.assertNotEqual(sess.status().state, "mutated")

    def test_sched_loop_clears_the_overlay_on_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp, media=1.5)
            sess.submit_segment(_seg("ciao"))
            sess._tick_once(0.0)
            self.assertTrue(any(a for a in video.rt.overlays if a))
            sess._stop.set()
            sess._sched_loop()          # exits at once, runs the finally teardown
            self.assertIsNone(video.rt.overlays[-1])


class _FakeDecoder:
    def __init__(self, *a, **k):
        self.first_pts = 0.0

    def blocks(self, cancel):
        yield (0.0, np.ones(4000, dtype=np.float32))    # speech
        yield (0.25, np.zeros(4000, dtype=np.float32))  # silence
        yield (0.5, np.zeros(4000, dtype=np.float32))   # ends the utterance

    def close(self):
        pass


class _FakeVad:
    def probs(self, samples):
        p = 0.9 if float(np.asarray(samples).mean()) > 0.5 else 0.0
        return [p] * (len(samples) // 512)


class _FakeWhisper:
    device = "cuda"       # the model reports the device it loaded on

    def __init__(self, **k):
        pass

    def transcribe(self, utt, *, language):
        return ([{"start": 0.0, "end": 0.3, "text": "hello.", "no_speech_prob": 0.1,
                  "avg_logprob": -0.2, "compression_ratio": 1.5}], "en", 0.95)

    def close(self):
        pass


class _FakeTranslator:
    name = "marian"
    online = False

    def __init__(self, engine="marian"):
        pass

    def prepare(self, src, tgt):
        pass

    def translate(self, text, *, context=(), timeout_s=5.0):
        from videotranslator.live_translate import Outcome
        return Outcome("ciao.", True, 0.01)

    def close(self):
        pass


def _pipeline_factories():
    return LiveFactories(
        decoder=lambda source, **k: _FakeDecoder(),
        vad=lambda: _FakeVad(),
        whisper=lambda **k: _FakeWhisper(),
        translator=lambda engine: _FakeTranslator(engine),
        tts=lambda *a, **k: None, clock=time.monotonic)


class LiveSessionPipelineTests(unittest.TestCase):
    def test_end_to_end_fake_pipeline_produces_a_caption(self):
        settings = normalize_live_settings(
            {"live_dub_enabled": False, "live_subs_enabled": True,
             "live_sync_mode": "delayed"})
        with tempfile.TemporaryDirectory() as tmp:
            cfg = build_live_config(
                {"source": "/v.mp4", "source_kind": "file", "lang_source": "en",
                 "lang_target": "it"}, settings=settings, cache_dir=Path(tmp), now=1.0)
            video = SimpleNamespace(rt=_FakeRt())
            sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(0.1),
                               factories=_pipeline_factories())
            sess.start()
            deadline = time.monotonic() + 6.0
            while time.monotonic() < deadline and not any(
                    a and "ciao" in a for a in video.rt.overlays):
                time.sleep(0.02)
            sess.request_stop()
            sess.join(4.0)
            self.assertTrue(any(a and "ciao" in a for a in video.rt.overlays),
                            "no translated caption reached the player")
            # the badge reflects the device Whisper actually loaded on, not the
            # "cpu" default (S3)
            self.assertEqual(sess.status().device, "cuda")
            self.assertEqual(sess.status().state, "stopped")
            live = [t for t in threading.enumerate() if t.name.startswith("live-")]
            self.assertEqual([t.name for t in live if t.is_alive()], [])


class LiveSessionLifecycleTests(unittest.TestCase):
    def test_start_run_stop_is_clean(self):
        # start() spawns the file producer threads, so this drives the real
        # (fake-backed) decode -> asr -> mt -> sched pipeline and checks the
        # running/stopped states, a clean join and the session lock file. The
        # try/finally stops the session even if an assertion fails, so a failure
        # here never leaks the daemon threads into the next test.
        settings = normalize_live_settings(
            {"live_dub_enabled": False, "live_subs_enabled": True,
             "live_sync_mode": "delayed"})
        with tempfile.TemporaryDirectory() as tmp:
            cfg = build_live_config(
                {"source": "/v.mp4", "source_kind": "file", "lang_source": "en",
                 "lang_target": "it"}, settings=settings, cache_dir=Path(tmp), now=1.0)
            video = SimpleNamespace(rt=_FakeRt())
            sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(0.1),
                               factories=_pipeline_factories())
            sess.start()
            try:
                self.assertEqual(sess.status().state, "running")
                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline and not any(
                        a and "ciao" in a for a in video.rt.overlays):
                    time.sleep(0.02)
                self.assertTrue(any(a and "ciao" in a for a in video.rt.overlays))
                self.assertTrue((cfg.session_dir / "session.lock").exists())
            finally:
                sess.request_stop()
                joined = sess.join(3.0)
            self.assertTrue(joined)
            self.assertEqual(sess.status().state, "stopped")


class BuildLiveFactoriesTests(unittest.TestCase):
    def test_returns_lazy_callables(self):
        from videotranslator.live_session import build_live_factories
        settings = normalize_live_settings({})
        cfg = build_live_config({"source": "/v.mp4", "lang_target": "it"},
                                settings=settings, cache_dir=Path("/c"), now=1.0)
        fac = build_live_factories(cfg)
        for f in (fac.decoder, fac.vad, fac.whisper, fac.translator, fac.tts):
            self.assertTrue(callable(f))

    def test_factory_builds_engines_and_rejects_unknown(self):
        # marian/google/deepl/ollama all build without a network call at
        # construction (prepare/translate do the work); an unknown engine raises.
        from videotranslator.live_session import build_live_factories
        from videotranslator.live_translate import LiveTranslateError
        settings = normalize_live_settings({})
        for engine in ("marian", "google", "deepl", "ollama"):
            cfg = build_live_config(
                {"source": "s", "lang_target": "it", "engine": engine, "deepl_key": "k"},
                settings=settings, cache_dir=Path("/c"), now=1.0)
            self.assertIsNotNone(build_live_factories(cfg).translator(engine))
        cfg = build_live_config({"source": "s", "lang_target": "it", "engine": "bing"},
                                settings=settings, cache_dir=Path("/c"), now=1.0)
        with self.assertRaises(LiveTranslateError):
            build_live_factories(cfg).translator("bing")


@unittest.skipUnless(os.environ.get("VTAI_RUN_HEAVY_SMOKE"),
                     "heavy smoke: set VTAI_RUN_HEAVY_SMOKE=1")
class LiveSessionHeavyTests(unittest.TestCase):
    def test_real_file_pipeline_produces_a_translated_caption(self):
        import asyncio
        import edge_tts
        from videotranslator.live_session import build_live_factories
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = os.path.join(tmp, "speech.mp3")

            async def synth():
                await edge_tts.Communicate(
                    "Hello, this is a live translation test.",
                    "en-US-AriaNeural").save(mp3)

            asyncio.run(synth())
            settings = normalize_live_settings(
                {"live_dub_enabled": False, "live_subs_enabled": True,
                 "live_sync_mode": "delayed"})
            cfg = build_live_config(
                {"source": mp3, "source_kind": "file", "lang_source": "en",
                 "lang_target": "it", "engine": "marian"},
                settings=settings, cache_dir=Path(tmp), now=1.0)
            video = SimpleNamespace(rt=_FakeRt())
            # a constant media position inside the clip's speech, so the scheduler
            # shows whichever produced segment covers it, decoupled from the
            # whisper model load time.
            sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(1.0),
                               factories=build_live_factories(cfg))
            sess.start()
            deadline = time.monotonic() + 180.0
            while (time.monotonic() < deadline
                   and sess.status().state == "running"
                   and not any(a for a in video.rt.overlays if a)):
                time.sleep(0.1)
            sess.request_stop()
            sess.join(15.0)
            self.assertIsNone(sess.status().error_key,
                              f"pipeline error: {sess.status().error_key}")
            caps = [a for a in video.rt.overlays if a]
            self.assertTrue(caps, "the real pipeline produced no translated caption")


import queue as _queue

from videotranslator import player_engine as pe
from videotranslator.live_tts import Clip, EdgeClipSynth, LiveTtsUnavailable
from videotranslator.live_health import CircuitBreaker


class _FakeSynth:
    def __init__(self, *, start_exc=None, submit_ok=True):
        self.results = _queue.Queue()
        self.submitted = []
        self.started = False
        self.stopped = False
        self._start_exc = start_exc
        self._submit_ok = submit_ok

    def start(self):
        if self._start_exc is not None:
            raise self._start_exc
        self.started = True

    def submit(self, seg_id, gen, text, rate, deadline):
        self.submitted.append((seg_id, gen, text, rate))
        return self._submit_ok

    def stop(self, _timeout):
        self.stopped = True
        return True

    def push(self, seg_id, gen, clip, reason=None):
        self.results.put((seg_id, gen, clip, reason))


def _dub_session(tmp, *, media=1.8, synth=None, overrides=None):
    settings = normalize_live_settings(
        {"live_dub_enabled": True, "live_subs_enabled": True,
         "live_sync_mode": "delayed", **(overrides or {})})
    cfg = build_live_config({"source": "/v.mp4", "lang_target": "it", "voice": "it-IT-X"},
                            settings=settings, cache_dir=Path(tmp), now=1.0)
    made = synth if synth is not None else _FakeSynth()
    factories = LiveFactories(
        decoder=lambda *a, **k: None, vad=lambda *a, **k: None,
        whisper=lambda *a, **k: None, translator=lambda *a, **k: None,
        tts=lambda **k: made, clock=time.monotonic)
    video = SimpleNamespace(rt=_FakeRt(), mixer=pe.VolumeMixer(), bridge=pe.EventBridge())
    voice = pe.InMemoryVoice(mpv_version=(0, 41))
    view = _FakeClockView(media)
    sess = LiveSession(cfg, video=video, clock_view=view, factories=factories,
                       voice=voice)
    return sess, video, voice, made, view


def _dub_seg(tgt="ciao", *, gen=0, start=2.0, end=3.0):
    return LiveSegment(0, gen, start, end, "hello", text_tgt=tgt, dub_ok=True)


class LiveSessionDubTests(unittest.TestCase):
    def test_start_dub_creates_and_starts_the_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _voice, synth, _ = _dub_session(tmp)
            sess._start_dub()
            self.assertTrue(synth.started)
            # the scheduler now owns the mixer so the Tk volume defers to the duck
            self.assertEqual(video.mixer.snapshot().owner, "sched")

    def test_translated_segment_requests_tts(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _v, _voice, synth, _ = _dub_session(tmp, media=1.8)
            sess._start_dub()
            sess.submit_segment(_dub_seg("ciao"))
            sess._tick_once(0.0)
            self.assertEqual(len(synth.submitted), 1)
            self.assertEqual(synth.submitted[0][2], "ciao")

    def test_full_preload_start_and_duck_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice, synth, _ = _dub_session(tmp, media=1.8)
            sess._start_dub()
            sess._last_pacer_mono = 1e9                 # isolate from the file pacer
            sess.submit_segment(_dub_seg("ciao", start=2.0, end=3.0))
            sess._tick_once(0.0)                       # RequestTts
            clip = Clip(0, 0, "/clip.mp3", 1.0, "+0%",
                        voice_start_s=0.1, voice_end_s=1.0)
            synth.push(0, 0, clip)
            for i in range(1, 40):                     # clip_ready -> preload -> start + duck ramp
                sess._tick_once(i * 0.02)
            names = [c[0] for c in voice.calls]
            self.assertIn("preload", names)
            self.assertIn("start", names)
            self.assertLess(names.index("preload"), names.index("start"))
            self.assertTrue(video.rt.ducks, "the original audio never ducked")
            self.assertLess(min(video.rt.ducks), 1.0)  # ramped down toward 0.3

    def test_voice_end_marker_returns_state_to_idle(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _voice, _synth, _ = _dub_session(tmp)
            sess._voice_state = "playing"
            video.bridge.extra_latest("voice-eof", (1, "eof"), 5.0)
            sess._sync_voice_state()
            self.assertEqual(sess._voice_state, "idle")

    def test_three_voice_errors_disable_the_dub(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _voice, _synth, _ = _dub_session(tmp)
            sess._start_dub()
            for n in range(1, 4):
                sess._voice_state = "playing"
                video.bridge.extra_latest("voice-eof", (n, "error"), float(n))
                sess._sync_voice_state()
            self.assertIsNone(sess._synth)
            self.assertEqual(sess.status().warning_key, "live_warn_tts_unavailable")

    def test_tts_unavailable_disables_dub_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth = _FakeSynth(start_exc=LiveTtsUnavailable("no edge-tts"))
            sess, _v, _voice, _s, _ = _dub_session(tmp, synth=synth)
            sess._start_dub()
            self.assertIsNone(sess._synth)
            self.assertEqual(sess.status().warning_key, "live_warn_tts_unavailable")

    def test_rejected_tts_marks_the_segment_dropped_not_synth(self):
        # review finding 1: a submit that returns False must drop the segment, or
        # it stays "synth" forever and stalls the pacer.
        with tempfile.TemporaryDirectory() as tmp:
            synth = _FakeSynth(submit_ok=False)
            sess, _v, _voice, _s, _ = _dub_session(tmp, media=1.8, synth=synth)
            sess._start_dub()
            sess.submit_segment(_dub_seg("ciao", start=2.0, end=3.0))
            sess._tick_once(0.0)
            self.assertEqual(sess._scheduler._dub_state.get(0), "dropped")

    def test_voice_none_with_dub_disables_it(self):
        # review finding 8: dub requested but no voice backend -> dub off, so the
        # scheduler does not request clips that would stall the pacer.
        with tempfile.TemporaryDirectory() as tmp:
            settings = normalize_live_settings(
                {"live_dub_enabled": True, "live_subs_enabled": True,
                 "live_sync_mode": "delayed"})
            cfg = build_live_config({"source": "/v.mp4", "lang_target": "it"},
                                    settings=settings, cache_dir=Path(tmp), now=1.0)
            factories = LiveFactories(
                decoder=lambda *a, **k: None, vad=lambda *a, **k: None,
                whisper=lambda *a, **k: None, translator=lambda *a, **k: None,
                tts=lambda **k: _FakeSynth(), clock=time.monotonic)
            video = SimpleNamespace(rt=_FakeRt(), mixer=pe.VolumeMixer(),
                                    bridge=pe.EventBridge())
            sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(1.0),
                               factories=factories, voice=None)
            sess._start_dub()
            self.assertFalse(sess._scheduler._dub)
            self.assertEqual(sess.status().warning_key, "live_warn_tts_unavailable")

    def test_stale_stop_marker_does_not_end_the_next_clip(self):
        # review finding 3: a "stop" eof marker (our own StopClip/loadfile) must be
        # consumed without ending the clip; only a real "eof" ends it.
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _voice, _s, _ = _dub_session(tmp)
            sess._voice_state = "playing"
            video.bridge.extra_latest("voice-eof", (5, "stop"), 1.0)
            sess._sync_voice_state()
            self.assertEqual(sess._voice_state, "playing")   # stop ignored
            self.assertEqual(sess._last_eof_count, 5)        # but consumed
            video.bridge.extra_latest("voice-eof", (6, "eof"), 2.0)
            sess._sync_voice_state()
            self.assertEqual(sess._voice_state, "idle")      # real end applies

    def test_start_snapshots_a_prior_eof_marker(self):
        # review finding 3 (cross-session): a marker left by a previous session on
        # the shared backend must not close this session's first clip.
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _voice, _s, _ = _dub_session(tmp)
            video.bridge.extra_latest("voice-eof", (57, "eof"), 1.0)
            sess.start()
            try:
                self.assertEqual(sess._last_eof_count, 57)
            finally:
                sess.request_stop()
                sess.join(2.0)

    def test_missing_factory_result_disables_dub_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = normalize_live_settings(
                {"live_dub_enabled": True, "live_subs_enabled": True,
                 "live_sync_mode": "delayed"})
            cfg = build_live_config({"source": "/v.mp4", "lang_target": "it"},
                                    settings=settings, cache_dir=Path(tmp), now=1.0)
            factories = LiveFactories(
                decoder=lambda *a, **k: None, vad=lambda *a, **k: None,
                whisper=lambda *a, **k: None, translator=lambda *a, **k: None,
                tts=lambda **k: None, clock=time.monotonic)
            video = SimpleNamespace(rt=_FakeRt(), mixer=pe.VolumeMixer(),
                                    bridge=pe.EventBridge())
            sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(1.0),
                               factories=factories, voice=pe.InMemoryVoice())
            sess._start_dub()
            self.assertIsNone(sess._synth)
            self.assertIsNone(sess.status().warning_key)


class _RecordingVoice:
    """Wraps a real voice backend, recording the ops the session issues."""

    def __init__(self, real):
        self._real = real
        self.calls = []
        self.mpv_version = real.mpv_version

    def preload(self, path, *, skip_s=0.0):
        self.calls.append(("preload", path, skip_s))
        self._real.preload(path, skip_s=skip_s)

    def start(self, speed):
        self.calls.append(("start", speed))
        self._real.start(speed)

    def set_pause(self, paused):
        self.calls.append(("set_pause", paused))
        self._real.set_pause(paused)

    def stop(self):
        self.calls.append(("stop",))
        self._real.stop()

    def set_volume(self, value):
        self.calls.append(("set_volume", value))
        self._real.set_volume(value)

    def set_speed(self, x):
        self.calls.append(("set_speed", x))
        self._real.set_speed(x)

    def terminate(self, t):
        return self._real.terminate(t)


@unittest.skipUnless(os.environ.get("VTAI_RUN_HEAVY_SMOKE"),
                     "heavy smoke: set VTAI_RUN_HEAVY_SMOKE=1 (needs libmpv, edge-tts, audio)")
class LiveDubHeavyTests(unittest.TestCase):
    """Real P5 voice path: edge-tts synth + a real, video-less mpv (item 10).

    Verified live on Linux (2026-09-26): a clip synthesizes, plays on the second
    mpv, ends with the eof marker, and the session ducks the original audio.
    """

    def _av(self):
        try:
            import av
            return av
        except Exception:
            return None

    def test_real_voice_backend_plays_a_synthesized_clip(self):
        from videotranslator import libmpv_runtime
        with tempfile.TemporaryDirectory() as tmp:
            synth = EdgeClipSynth("it-IT-ElsaNeural", tmp, breaker=CircuitBreaker(),
                                  av_module=self._av())
            synth.start()
            self.assertTrue(synth.submit(1, 0, "Ciao, prova di doppiaggio.", 0,
                                         time.monotonic() + 20))
            _sid, _g, clip, reason = synth.results.get(timeout=20)
            synth.stop(5.0)
            self.assertIsNotNone(clip, f"no clip (reason={reason})")
            self.assertTrue(Path(clip.path).exists() and Path(clip.path).stat().st_size)

            module = libmpv_runtime.load_mpv()
            bridge = pe.EventBridge()
            voice = pe.create_voice_backend(bridge=bridge, mpv_module=module,
                                            sys_platform="linux", log=None)
            try:
                voice.preload(clip.path, skip_s=getattr(clip, "voice_start_s", 0.0))
                time.sleep(0.3)
                voice.start(1.0)
                deadline = time.monotonic() + max(6.0, clip.duration + 4.0)
                played = 0.0
                while time.monotonic() < deadline:
                    pts = bridge.extra("voice-time-pos")
                    if pts and pts[0]:
                        played = pts[0]
                    if bridge.extra("voice-eof") is not None:
                        break
                    time.sleep(0.05)
                self.assertGreater(played, 0.0, "voice never advanced")
                self.assertIsNotNone(bridge.extra("voice-eof"), "no eof marker")
            finally:
                self.assertTrue(voice.terminate(5.0))

    def test_real_session_dub_flow_plays_and_ducks(self):
        from videotranslator import libmpv_runtime
        with tempfile.TemporaryDirectory() as tmp:
            module = libmpv_runtime.load_mpv()
            bridge = pe.EventBridge()
            real = pe.create_voice_backend(bridge=bridge, mpv_module=module,
                                           sys_platform="linux", log=None)
            voice = _RecordingVoice(real)
            av_mod = self._av()

            def make_synth(*, out_dir, breaker, thread_factory, clock):
                return EdgeClipSynth("it-IT-ElsaNeural", out_dir, breaker=breaker,
                                     av_module=av_mod, thread_factory=thread_factory,
                                     clock=clock)

            factories = LiveFactories(
                decoder=lambda *a, **k: None, vad=lambda *a, **k: None,
                whisper=lambda *a, **k: None, translator=lambda *a, **k: None,
                tts=make_synth, clock=time.monotonic)
            settings = normalize_live_settings(
                {"live_dub_enabled": True, "live_subs_enabled": True,
                 "live_sync_mode": "delayed"})
            cfg = build_live_config(
                {"source": "/v.mp4", "lang_target": "it", "voice": "it-IT-ElsaNeural"},
                settings=settings, cache_dir=Path(tmp), now=1.0)
            video = SimpleNamespace(rt=_FakeRt(), mixer=pe.VolumeMixer(), bridge=bridge)
            view = _FakeClockView(0.5)
            sess = LiveSession(cfg, video=video, clock_view=view,
                               factories=factories, voice=voice)
            try:
                sess._start_dub()
                sess._last_pacer_mono = 1e9      # isolate from the file pacer
                sess.submit_segment(LiveSegment(
                    1, 0, 6.0, 9.0, "Hello everyone.",
                    text_tgt="Ciao a tutti, benvenuti alla prova di doppiaggio.",
                    dub_ok=True))
                deadline = time.monotonic() + 40.0
                started = False
                while time.monotonic() < deadline:
                    view.media = min(9.5, view.media + 0.05)
                    sess._tick_once(time.monotonic())
                    if "start" in [c[0] for c in voice.calls]:
                        started = True
                    if started and (bridge.extra("voice-eof") is not None
                                    or sess._voice_state == "idle"):
                        break
                    time.sleep(0.05)
                names = [c[0] for c in voice.calls]
                self.assertIn("preload", names)
                self.assertIn("start", names)
                self.assertTrue(video.rt.ducks and min(video.rt.ducks) < 1.0,
                                "original audio never ducked")
                self.assertTrue(any(a for a in video.rt.overlays if a), "no caption")
            finally:
                if sess._synth is not None:
                    sess._synth.stop(5.0)
                self.assertTrue(real.terminate(5.0))


if __name__ == "__main__":
    unittest.main()
