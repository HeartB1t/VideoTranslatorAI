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


class _EofClockView:
    """Media clock that advances while playing, then freezes on the last frame
    (or reports an invalid position, None) at EOF, like _MediaClock past end of
    file. Set ``media`` to advance/freeze it and ``invalid`` to make it None.
    """
    def __init__(self, media=0.0):
        self.media = media
        self.invalid = False
        self.epoch = 0

    def now(self, _mono):
        return None if self.invalid else self.media


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
    def test_startup_hold_keeps_pacer_from_resuming_before_first_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp)
            sess._startup_hold = True
            sess._self_paused = True
            sess._run_pacer(1.0)
            self.assertTrue(sess._self_paused)
            self.assertEqual(video.rt.pauses, [])
            sess._startup_hold = False
            sess._control.put(("startup_release", None))
            sess._drain_control(1.02)
            self.assertFalse(sess._self_paused)
            self.assertEqual(video.rt.pauses[-1], False)

    def test_user_pause_and_pacer_pause_have_independent_ownership(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp)
            sess._tick_once(0.0)  # pacer owns the pause, user still wants playback
            self.assertTrue(sess._self_paused)
            self.assertFalse(sess._user_paused)
            sess.toggle_user_pause()
            sess._tick_once(0.02)
            self.assertTrue(sess._user_paused)
            sess._source_done = True
            sess._tick_once(2.0)
            self.assertTrue(video.rt.pauses[-1])  # EOF cannot override user pause
            sess.toggle_user_pause()
            sess._tick_once(2.02)
            self.assertFalse(sess._user_paused)
            self.assertFalse(sess._self_paused)
            self.assertFalse(video.rt.pauses[-1])

    def test_resume_intent_does_not_override_buffering(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _ = _session(tmp)
            sess._tick_once(0.0)
            sess.notify_user_pause(True)
            sess.notify_user_pause(False)
            sess._tick_once(0.02)
            self.assertTrue(video.rt.pauses[-1])
            self.assertFalse(sess._user_paused)

    def test_cached_seek_keeps_producers_and_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)
            sess.submit_segment(_seg())
            sess._tick_once(0.0)
            cancel = sess._decode_cancel
            sess.notify_user_seek(2.0)
            sess._tick_once(0.02)
            self.assertEqual(sess._gen, 0)
            self.assertFalse(cancel.is_set())

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


class FileBufferTests(unittest.TestCase):
    """On files the delay slider is the buffer rebuilt after a pause."""

    def _paused_once(self, sess, clock):
        sess._clock = lambda: clock
        sess._self_paused = False
        sess._scheduler.ready_until = lambda now: now + 0.5        # nearly no coverage
        sess._run_pacer(10.0)
        self.assertTrue(sess._self_paused)

    def test_repeated_pauses_raise_the_buffer_and_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, overrides={"live_file_ahead_s": 8.0})
            self.assertEqual(sess._timing_delay(), 8.0)
            self._paused_once(sess, 100.0)
            self.assertIsNone(sess.status().warning_key)
            self._paused_once(sess, 110.0)
            self.assertEqual(sess._pacer.resume_ahead_s, 12.0)
            self.assertEqual(sess._timing_delay(), 12.0)
            st = sess.status()
            self.assertEqual(st.warning_key, "live_warn_falling_behind")
            self.assertEqual(st.warning_params, {"s": 12})
            sess._scheduler.ready_until = lambda now: now + 13.0
            sess._run_pacer(10.0)                                 # buffer rebuilt
            self.assertFalse(sess._self_paused)
            self.assertIsNone(sess.status().warning_key)

    def test_a_paused_engine_keeps_its_banner_and_its_switch_button(self):
        # Seen on the real GUI: in delayed mode the picture waits for sentences
        # held for a rate-limited Google, and "falling behind" replaced the
        # banner that offers "Switch to MarianMT", the only way out.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, overrides={"live_file_ahead_s": 8.0})
            sess._set_warning("rate_limited", "google", s=30, action="live_btn_switch_marian")
            self._paused_once(sess, 100.0)
            self._paused_once(sess, 110.0)
            self.assertEqual(sess._pacer.resume_ahead_s, 12.0)    # the buffer still grows
            st = sess.status()
        self.assertEqual((st.warning_key, st.warning_action),
                         ("live_warn_rate_limited", "live_btn_switch_marian"))

    def test_pauses_right_after_a_seek_do_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)
            for clock in (100.0, 104.0):
                sess._clock = lambda c=clock: c
                sess.notify_user_seek(50.0)
                sess._drain_control(0.0)
                self._paused_once(sess, clock + 1.0)
            self.assertEqual(sess._pacer.resume_ahead_s, 8.0)
            self.assertIsNone(sess.status().warning_key)

    def test_auto_off_keeps_the_buffer(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, overrides={"live_delay_auto": False})
            for clock in (100.0, 101.0, 102.0):
                self._paused_once(sess, clock)
            self.assertEqual(sess._pacer.resume_ahead_s, 8.0)

    def test_delay_control_changes_the_file_buffer(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)
            sess.set_delay(20.0)
            sess._drain_control(0.0)
            self.assertEqual(sess._pacer.resume_ahead_s, 20.0)


class StartupSilenceTests(unittest.TestCase):
    """A leading silence releases the startup hold only when it is long."""

    def _silences(self, pattern):
        """Run the decode loop over ``pattern`` [(seconds, speech), ...]."""
        from dataclasses import replace
        from videotranslator.live_session import _PipelineEnd, _PipelineSilence

        class Decoder(_FakeDecoder):
            def blocks(self, cancel):
                t = 0.0
                for seconds, speech in pattern:
                    for _ in range(int(round(seconds / 0.25))):
                        yield (t, np.full(4000, 1.0 if speech else 0.0, dtype=np.float32))
                        t += 0.25

        events = []
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)
            sess._factories = replace(_pipeline_factories(), decoder=lambda source, **k:
                                      Decoder())

            def put(utt):
                events.append(utt)
                if isinstance(utt, _PipelineEnd):
                    sess._stop.set()
            sess._put_utt = put
            sess._decode_loop()
        return sess, [e for e in events if isinstance(e, _PipelineSilence)]

    def _ready(self, sess, silences):
        for event in silences:
            if event.leading and event.end - event.start >= 6.0:
                return True
        return False

    def test_short_leading_silence_does_not_release_the_start(self):
        sess, silences = self._silences([(3.0, False), (2.0, True), (1.0, False)])
        self.assertTrue(silences)                   # still reported for sentence flush
        self.assertTrue(all(e.end - e.start < 6.0 for e in silences if e.leading))
        self.assertFalse(self._ready(sess, silences))

    def test_long_leading_silence_releases_the_start(self):
        sess, silences = self._silences([(8.0, False), (1.0, True)])
        self.assertTrue(self._ready(sess, silences))
        leading = [e for e in silences if e.leading]
        self.assertGreaterEqual(max(e.end for e in leading), 7.0)   # reported repeatedly

    def test_silence_after_speech_is_not_leading(self):
        sess, silences = self._silences([(1.0, True), (9.0, False)])
        self.assertTrue(silences)
        self.assertFalse(any(e.leading for e in silences))

    def test_asr_loop_marks_ready_only_for_a_long_leading_silence(self):
        from videotranslator.live_session import _PipelineSilence
        for event, expected in ((_PipelineSilence(0, 3.0, 0.0, leading=True), False),
                                (_PipelineSilence(0, 7.0, 0.0, leading=True), True),
                                (_PipelineSilence(0, 20.0, 5.0, leading=False), False)):
            with tempfile.TemporaryDirectory() as tmp:
                sess, _, _ = _session(tmp)
                sess._utt_q.put(event)

                class _StopAfterFirst(_FakeWhisper):
                    pass
                from dataclasses import replace
                sess._factories = replace(_pipeline_factories(),
                                          whisper=lambda **k: _StopAfterFirst())
                import threading as _t
                worker = _t.Thread(target=sess._asr_loop, daemon=True)
                worker.start()
                deadline = time.monotonic() + 2
                while not sess._utt_q.empty() and time.monotonic() < deadline:
                    time.sleep(0.01)
                time.sleep(0.05)
                sess._stop.set()
                worker.join(2)
                self.assertEqual(sess._startup_silence_ready.is_set(), expected, event)


class LiveSessionPipelineTests(unittest.TestCase):
    def test_asr_loop_passes_the_chosen_live_model(self):
        from dataclasses import replace
        for choice, expected in (("base", {"model": "base"}), ("auto", {})):
            seen = []

            def whisper(**kw):
                seen.append(kw)
                raise RuntimeError("stop here")
            with tempfile.TemporaryDirectory() as tmp:
                sess, _, _ = _session(tmp, overrides={"live_asr_model": choice})
                sess._factories = replace(_pipeline_factories(), whisper=whisper)
                sess._asr_loop()
            self.assertEqual(len(seen), 1)
            self.assertEqual({k: v for k, v in seen[0].items() if k == "model"}, expected)

    def test_seek_during_transcription_discards_old_result(self):
        from dataclasses import replace
        from videotranslator.live_segment import Utterance
        from videotranslator.live_asr import LanguageLock
        entered, release = threading.Event(), threading.Event()

        class BlockingWhisper(_FakeWhisper):
            def transcribe(self, utt, *, language):
                entered.set()
                if not release.wait(3):
                    raise RuntimeError("test did not release transcription")
                return super().transcribe(utt, language=language)

        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)
            sess._langlock = LanguageLock("en")
            sess._factories = replace(_pipeline_factories(), whisper=BlockingWhisper)
            sess._utt_q.put(Utterance(0, 0, 1, np.ones(16000), False))
            worker = threading.Thread(target=sess._asr_loop)
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                sess.notify_user_seek(20)
                sess._drain_control(0)
                release.set()
                sess.request_stop()
                worker.join(3)
                self.assertFalse(worker.is_alive())
                self.assertTrue(sess._mt_q.empty())
                self.assertTrue(sess._sched_in.empty())
            finally:
                release.set()
                sess.request_stop()
                worker.join(3)

    def test_seek_after_eof_reopens_decoder_without_reloading_whisper(self):
        from dataclasses import replace
        opened, closed, models = [], [], []

        class Decoder(_FakeDecoder):
            def __init__(self, source, *, start_at, **kw):
                self.offset = start_at
                opened.append(start_at)

            def blocks(self, cancel):
                for t, pcm in super().blocks(cancel):
                    yield t + self.offset, pcm

            def close(self):
                closed.append(self.offset)

        class Whisper(_FakeWhisper):
            def __init__(self, **kw):
                models.append(self)

            def transcribe(self, utt, *, language):
                segs, lang, prob = super().transcribe(utt, language=language)
                for seg in segs:
                    seg.update(start=utt.start, end=utt.end)
                return segs, lang, prob

        with tempfile.TemporaryDirectory() as tmp:
            sess, _, cfg = _session(tmp, media=0.1)
            sess._cfg = replace(cfg, lang_source="en")
            from videotranslator.live_asr import LanguageLock
            sess._langlock = LanguageLock("en")
            sess._factories = replace(_pipeline_factories(), decoder=Decoder, whisper=Whisper)
            sess.start()
            try:
                deadline = time.monotonic() + 3
                while not sess._source_done and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(sess._source_done)
                sess._clock_view.media = 20.0
                sess.notify_user_seek(20.0)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    if sess._gen == 1 and sess._source_done:
                        break
                    time.sleep(0.01)
                self.assertEqual(opened, [0.0, 19.5])
                self.assertEqual(closed, opened)
                self.assertEqual(len(models), 1)
                self.assertTrue(sess._source_done)
                deadline = time.monotonic() + 1
                while sess._sched_in.qsize() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(any(s.gen == 1 and s.start >= 19.5
                                    for s in sess._scheduler._segments.values()))
            finally:
                sess.request_stop()
                self.assertTrue(sess.join(3.0))

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


class SchedulerCrashTests(unittest.TestCase):
    def test_a_crash_in_the_tick_fails_the_session_and_stops_the_producers(self):
        # Before: the producers kept decoding and transcribing, and the status
        # stayed "running" on a session that no longer moved.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp)

            def boom(now):
                raise RuntimeError("tick bug")
            sess._tick_once = boom
            sess._sched_loop()
            st = sess.status()
        self.assertTrue(sess._stop.is_set())
        self.assertEqual(st.state, "failed")
        self.assertEqual(st.error_params, {"detail": "tick bug"})


class _LimitedTranslator(_FakeTranslator):
    """An online engine that never answers in time."""
    name, online = "google", True

    def __init__(self, engine="google"):
        self.closed = False

    def translate(self, text, *, context=(), timeout_s=5.0):
        from videotranslator.live_translate import Outcome
        return Outcome(text, False, 0.01, error="rate_limited")

    def close(self):
        self.closed = True


class _FakeMarian(_FakeTranslator):
    name, online = "marian", False

    def __init__(self, fail_key=None):
        self.prepared = None
        self.closed = False
        self._fail_key = fail_key

    def prepare(self, src, tgt):
        if self._fail_key:
            from videotranslator.live_translate import LiveTranslateError
            raise LiveTranslateError(self._fail_key, {"src": src, "tgt": tgt})
        self.prepared = (src, tgt)

    def describe(self):
        return "MarianMT fake"

    def close(self):
        self.closed = True


def _sentence(n):
    return SimpleNamespace(gen=0, start=float(n), end=n + 1.0, text=f"sentence {n}")


def _wait(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        time.sleep(0.01)
    return predicate()


class LiveTranslationWarningTests(unittest.TestCase):
    """The banner about a struggling online engine, and its "Switch to MarianMT".

    On the Windows VM (no GPU) Ollama never answered in time: the banner said
    so but never offered the switch (the session set no action), and the
    engine change it would have sent only relabelled the status."""

    def _mt_session(self, tmp, marian):
        from dataclasses import replace
        from unittest.mock import Mock
        from videotranslator.live_asr import LanguageLock
        sess, _, _ = _session(tmp, overrides={"live_engine": "google"})
        sess._langlock = LanguageLock("en")
        sess._logs = []
        sess._log = sess._logs.append
        limited = _LimitedTranslator()
        sess._factories = replace(
            _pipeline_factories(),
            translator=lambda engine: marian if engine == "marian" else limited)
        sess._emitted = Mock()
        sess._emit_segment = sess._emitted
        return sess, limited

    def test_a_rate_limited_engine_says_for_how_many_seconds_and_offers_marian(self):
        # live_warn_rate_limited reads "... for {s} s": the seconds were never
        # passed, and the banner said "for  s." (seen on the Windows VM).
        with tempfile.TemporaryDirectory() as tmp:
            sess, _ = self._mt_session(tmp, _FakeMarian())
            for n in range(3):
                sess._mt_q.put(_sentence(n))
            worker = threading.Thread(target=sess._mt_loop)
            worker.start()
            try:
                self.assertTrue(_wait(lambda: sess.status().warning_key is not None))
                st = sess.status()
            finally:
                sess.request_stop()
                worker.join(3)
        self.assertEqual(st.warning_key, "live_warn_rate_limited")
        self.assertEqual(st.warning_params, {"engine": "google", "s": 30})
        self.assertEqual(st.warning_action, "live_btn_switch_marian")

    def test_an_exhausted_quota_warns_instead_of_failing_the_session(self):
        # A quota failure keeps the breaker open for good: retry_in_s() is inf,
        # and int(round(inf)) used to end the session as an internal error.
        from dataclasses import replace

        class _QuotaTranslator(_LimitedTranslator):
            def translate(self, text, *, context=(), timeout_s=5.0):
                from videotranslator.live_translate import Outcome
                return Outcome(text, False, 0.01, error="quota")

        with tempfile.TemporaryDirectory() as tmp:
            sess, _ = self._mt_session(tmp, _FakeMarian())
            quota = _QuotaTranslator()
            sess._factories = replace(
                sess._factories,
                translator=lambda engine: _FakeMarian() if engine == "marian" else quota)
            sess._mt_q.put(_sentence(0))
            worker = threading.Thread(target=sess._mt_loop)
            worker.start()
            try:
                self.assertTrue(_wait(lambda: sess.status().warning_key is not None
                                      or sess.status().state == "failed"))
                st = sess.status()
            finally:
                sess.request_stop()
                worker.join(3)
        self.assertNotEqual(st.state, "failed", st.error_params)
        self.assertEqual(st.warning_key, "live_warn_quota")
        self.assertEqual(st.warning_action, "live_btn_switch_marian")

    def test_the_switch_to_marian_replaces_the_translator_mid_session(self):
        marian = _FakeMarian()
        with tempfile.TemporaryDirectory() as tmp:
            sess, limited = self._mt_session(tmp, marian)
            for n in range(3):
                sess._mt_q.put(_sentence(n))
            worker = threading.Thread(target=sess._mt_loop)
            worker.start()
            try:
                self.assertTrue(_wait(lambda: sess.status().warning_action is not None))
                sess.set_engine("marian")
                sess._drain_control(0)
                self.assertTrue(_wait(lambda: sess.status().warning_key is None))
                sess._mt_q.put(_sentence(3))
                self.assertTrue(_wait(lambda: sess._emitted.call_count >= 4))
                st = sess.status()
                last = sess._emitted.call_args
            finally:
                sess.request_stop()
                worker.join(3)
        self.assertEqual(st.engine, "marian")
        self.assertEqual(marian.prepared, ("en", "it"))
        self.assertTrue(limited.closed)
        self.assertEqual((last.args[2], last.args[3], last.kwargs["italic"]),
                         ("sentence 3", "ciao.", False))
        self.assertTrue(any("translator ready: MarianMT fake" in line for line in sess._logs))
        self.assertTrue(marian.closed)             # closed with the session

    def test_a_failed_switch_keeps_the_running_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, limited = self._mt_session(tmp, _FakeMarian(fail_key="marian_pair"))
            # The video is past these sentences: they are due, so they come out
            # in the original instead of waiting for the paused engine.
            sess._clock_view = _FakeClockView(10.0)
            for n in range(3):
                sess._mt_q.put(_sentence(n))
            worker = threading.Thread(target=sess._mt_loop)
            worker.start()
            try:
                self.assertTrue(_wait(lambda: sess.status().warning_action is not None))
                sess.set_engine("marian")
                sess._drain_control(0)
                self.assertTrue(_wait(lambda: any("switch to marian failed" in line
                                                  for line in sess._logs)))
                closed_by_the_switch = limited.closed
                sess._mt_q.put(_sentence(3))
                self.assertTrue(_wait(lambda: sess._emitted.call_count >= 4))
                st = sess.status()
                alive = worker.is_alive()
            finally:
                sess.request_stop()
                worker.join(3)
        self.assertTrue(alive)
        self.assertEqual((st.engine, st.warning_key, st.warning_action),
                         ("google", "live_warn_rate_limited", None))
        self.assertFalse(closed_by_the_switch)
        self.assertTrue(limited.closed)            # by the session's end
        self.assertIn("marian_pair", " ".join(sess._logs))


class _ScriptedOnline(_LimitedTranslator):
    """Online engine: rate-limited for the first ``fail`` calls, then answers."""

    def __init__(self, fail=10 ** 6, on_call=None, error="rate_limited"):
        super().__init__()
        self.calls, self._fail, self._on_call, self._error = [], fail, on_call, error

    def translate(self, text, *, context=(), timeout_s=5.0):
        from videotranslator.live_translate import Outcome
        self.calls.append(text)
        if self._on_call is not None:
            self._on_call(len(self.calls))
        if len(self.calls) <= self._fail:
            return Outcome(text, False, 0.01, error=self._error)
        return Outcome("tradotta", True, 0.01)


from videotranslator.live_health import CircuitBreaker as _Breaker  # noqa: E402


class _FastBreaker(_Breaker):
    def __init__(self, **kw):
        super().__init__(cooldown_s=0.6, max_cooldown_s=0.6)


class OnlineEnginePauseTests(unittest.TestCase):
    """A file runs far ahead of playback: a paused online engine must not turn
    every sentence of the video into the original (seen 02/10 with Google in
    HTTP 429: 75 sentences kept original in 3 s, the dub silent)."""

    def _start(self, tmp, online, *, media=0.0, marian=None, mode="live", items=10,
               clock_view=None):
        from dataclasses import replace
        from unittest import mock
        from videotranslator.live_asr import LanguageLock
        sess, _, _ = _session(tmp, overrides={"live_engine": "google", "live_sync_mode": mode})
        sess._langlock = LanguageLock("en")
        sess._logs = []
        sess._log = sess._logs.append
        sess._clock_view = clock_view or _FakeClockView(media)
        sess._factories = replace(
            _pipeline_factories(),
            translator=lambda engine: (marian or _FakeMarian()) if engine == "marian" else online)
        sess._emitted = mock.Mock()
        sess._emit_segment = sess._emitted
        for n in range(items):
            sess._mt_q.put(_sentence(n))
        patcher = mock.patch("videotranslator.live_session.CircuitBreaker", _FastBreaker)
        patcher.start()
        self.addCleanup(patcher.stop)
        worker = threading.Thread(target=sess._mt_loop)
        worker.start()

        def stop():
            sess.request_stop()
            worker.join(3)
        self.addCleanup(stop)
        return sess

    @staticmethod
    def _emitted(sess):
        return [(c.args[0], c.args[3]) for c in sess._emitted.call_args_list]

    def test_a_paused_engine_holds_the_sentences_still_ahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess = self._start(tmp, _ScriptedOnline(), media=1.0)
            self.assertTrue(_wait(lambda: sess.status().warning_key is not None))
            time.sleep(0.15)                    # well inside the breaker's pause
            early = self._emitted(sess)
            sess.set_engine("marian")
            sess._drain_control(0)
            self.assertTrue(_wait(lambda: len(self._emitted(sess)) >= 10))
            final = self._emitted(sess)
        # The failure that paused the engine keeps its sentence waiting too.
        self.assertEqual([start for start, _ in early], [0.0, 1.0])
        self.assertEqual(final[2:], [(float(n), "ciao.") for n in range(2, 10)])

    def test_sentences_that_passed_during_the_pause_cost_no_call(self):
        view = _FakeClockView(0.0)

        def on_call(n):
            if n == 3:
                view.media = 5.6                # live mode: the video went on
        online = _ScriptedOnline(fail=3, on_call=on_call)
        with tempfile.TemporaryDirectory() as tmp:
            sess = self._start(tmp, online, items=8, clock_view=view)
            self.assertTrue(_wait(lambda: len(self._emitted(sess)) >= 8, timeout=4))
            final = self._emitted(sess)
        self.assertEqual(len(online.calls), 4)   # 3 failures, then only sentence 7
        self.assertEqual(final[3:7], [(float(n), None) for n in range(3, 7)])
        self.assertEqual(final[7], (7.0, "tradotta"))

    def test_a_seek_during_the_pause_drops_the_held_sentences(self):
        online = _ScriptedOnline(fail=3)
        with tempfile.TemporaryDirectory() as tmp:
            sess = self._start(tmp, online, media=0.0)
            self.assertTrue(_wait(lambda: sess.status().warning_key is not None))
            sess._gen = 1                       # a seek restarted the decoder
            time.sleep(1.0)                     # past the pause: the engine answers again
            final = self._emitted(sess)
        self.assertEqual(len(online.calls), 3)
        self.assertEqual([start for start, _ in final], [0.0, 1.0])

    def test_delayed_mode_keeps_the_source_open_while_sentences_wait(self):
        # The pacer stops buffering once the source is done: the end marker must
        # wait behind the held sentences, or the video would play on untranslated.
        from videotranslator.live_session import _PipelineEnd
        with tempfile.TemporaryDirectory() as tmp:
            sess = self._start(tmp, _ScriptedOnline(), media=0.0, mode="delayed", items=6)
            sess._mt_q.put(_PipelineEnd(0))
            self.assertTrue(_wait(lambda: sess.status().warning_key is not None))
            time.sleep(0.15)
            done = sess._source_done
            emitted = self._emitted(sess)
        self.assertFalse(done)
        self.assertEqual(len(emitted), 2)

    def test_an_exhausted_quota_on_a_file_goes_on_with_marian(self):
        online = _ScriptedOnline(error="quota")
        with tempfile.TemporaryDirectory() as tmp:
            sess = self._start(tmp, online, media=0.0, items=5)
            self.assertTrue(_wait(lambda: len(self._emitted(sess)) >= 5))
            final = self._emitted(sess)
            st = sess.status()
        self.assertEqual(len(online.calls), 1)
        self.assertEqual(final, [(0.0, None)] + [(float(n), "ciao.") for n in range(1, 5)])
        self.assertNotEqual(st.state, "failed")
        self.assertIn("live: translation engine switched to marian", sess._logs)


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
            sess.start(startup_hold=True)
            try:
                self.assertTrue(video.rt.pauses[-1])
                self.assertIn(sess.status().state,
                              {"loading_models", "detecting", "buffering", "running"})
                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline and not any(
                        a and "ciao" in a for a in video.rt.overlays):
                    time.sleep(0.02)
                self.assertTrue(any(a and "ciao" in a for a in video.rt.overlays))
                deadline = time.monotonic() + 1.0
                while time.monotonic() < deadline and not sess.startup_ready:
                    time.sleep(0.01)
                self.assertTrue(sess.startup_ready)
                sess.release_startup_hold()
                time.sleep(0.05)
                self.assertFalse(video.rt.pauses[-1])
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


    def test_tts_factory_picks_edge_or_elevenlabs(self):
        from videotranslator.elevenlabs_tts import ElevenLabsClipSynth, FallbackClipSynth
        from videotranslator.live_health import CircuitBreaker
        from videotranslator.live_session import build_live_factories
        from videotranslator.live_tts import EdgeClipSynth
        settings = normalize_live_settings({})
        el_opts = {"engine": "elevenlabs", "api_key": "sk_secret", "voice_id": "v",
                   "model_id": "eleven_flash_v2_5"}
        cases = ((None, EdgeClipSynth, "edge-tts"),
                 (el_opts, FallbackClipSynth, "ElevenLabs"),
                 ({**el_opts, "fallback": False}, ElevenLabsClipSynth, "ElevenLabs"))
        for opts, expected, name in cases:
            cfg = build_live_config({"source": "s", "lang_target": "it", "tts_opts": opts},
                                    settings=settings, cache_dir=Path("/c"), now=1.0)
            synth = build_live_factories(cfg).tts(
                out_dir=Path("/c/clips"), breaker=CircuitBreaker(),
                thread_factory=threading.Thread, clock=time.monotonic)
            self.assertIsInstance(synth, expected)
            self.assertEqual(cfg.tts_name, name)
            self.assertNotIn("sk_secret", repr(cfg))
            self.assertNotIn("api_key", cfg.engine_opts)     # never reaches translators


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
            # Wait through the startup states (starting, loading_models,
            # detecting, buffering) until a caption shows or the session ends.
            while (time.monotonic() < deadline
                   and sess.status().state not in ("stopped", "failed", "ended")
                   and not any(a for a in video.rt.overlays if a)):
                time.sleep(0.1)
            caps = [a for a in video.rt.overlays if a]
            sess.request_stop()
            # Real models can still be loading: wait for every live thread, so
            # none leaks into (and slows or fails) the tests that follow.
            self.assertTrue(sess.join(120.0), "live threads did not stop")
            self.assertIsNone(sess.status().error_key,
                              f"pipeline error: {sess.status().error_key}")
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
    def test_original_mute_control_and_teardown_preserve_voice_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice, _, _ = _dub_session(tmp)
            sess._start_dub()
            sess.set_original_muted(True)
            sess._drain_control(0)
            state = video.mixer.snapshot()
            self.assertEqual((state.video_volume, state.voice_volume), (0, 100))
            self.assertTrue(video.rt.ducks)
            sess._teardown_outputs()
            self.assertEqual(video.mixer.snapshot().video_volume, 100)

    def test_duration_feedback_uses_successful_clip_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _, synth, _ = _dub_session(tmp)
            sess._start_dub()
            sess.submit_segment(_dub_seg("abcdefghij"))
            sess._tick_once(0)
            clip = Clip(0, 0, "/clip.mp3", 1.3, "+20%", 0.1, 1.1)
            synth.push(0, 0, clip)
            sess._drain_synth()
            self.assertAlmostEqual(sess._dur_model.estimate("abcdefghij", 0), 1.2)
            # A stale result must not update the rate estimator.
            synth.push(0, 99, Clip(0, 99, "/old.mp3", 20, "+0%", 0, 20))
            sess._drain_synth()
            self.assertAlmostEqual(sess._dur_model.estimate("abcdefghij", 0), 1.2)

    def test_toggle_keeps_worker_and_join_stops_it_and_restores_mix(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, _, synth, _ = _dub_session(tmp)
            video.apply_mix = Mock()
            sess._start_dub()
            sess.set_dub_enabled(False)
            sess._drain_control(0)
            self.assertIs(sess._synth, synth)
            sess.set_dub_enabled(True)
            sess._drain_control(0)
            self.assertIs(sess._synth, synth)
            sess.request_stop()
            self.assertTrue(sess.join(1))
            self.assertTrue(synth.stopped)
            self.assertEqual(video.mixer.snapshot().owner, "cmd")
            video.apply_mix.assert_called_once_with()

    def test_mute_is_reasserted_on_voice_and_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice, _, _ = _dub_session(tmp)
            sess._start_dub()
            video.mixer.set_muted(True)
            sess._reassert_mixer()
            self.assertIn(("set_volume", 0.0), voice.calls)
            self.assertTrue(video.rt.ducks)

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
            self.assertFalse(sess._scheduler._dub)   # dub turned off
            self.assertEqual(sess.status().warning_key, "live_warn_tts_unavailable")

    def test_tts_unavailable_disables_dub_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth = _FakeSynth(start_exc=LiveTtsUnavailable("no edge-tts"))
            sess, _v, _voice, _s, _ = _dub_session(tmp, synth=synth)
            sess._start_dub()
            self.assertIsNone(sess._synth)
            self.assertEqual(sess.status().warning_key, "live_warn_tts_unavailable")

    def _voiceless_session(self, tmp, *, dub, voice_pending):
        settings = normalize_live_settings(
            {"live_dub_enabled": dub, "live_subs_enabled": True,
             "live_sync_mode": "live"})
        cfg = build_live_config({"source": "/v.mp4", "lang_target": "it", "voice": "x"},
                                settings=settings, cache_dir=Path(tmp), now=1.0)
        synth = _FakeSynth()
        factories = LiveFactories(
            decoder=lambda *a, **k: None, vad=lambda *a, **k: None,
            whisper=lambda *a, **k: None, translator=lambda *a, **k: None,
            tts=lambda **k: synth, clock=time.monotonic)
        video = SimpleNamespace(rt=_FakeRt(), mixer=pe.VolumeMixer(),
                                bridge=pe.EventBridge(), apply_mix=lambda: None)
        sess = LiveSession(cfg, video=video, clock_view=_FakeClockView(1.0),
                           factories=factories, voice=None,
                           voice_pending=voice_pending)
        sess._last_pacer_mono = 1e9
        return sess, synth

    def test_lost_voice_lines_are_logged_with_their_reason(self):
        # Both cases that used to be silent now leave a log line: a rejected TTS
        # request and a sentence whose voice was not ready in time.
        with tempfile.TemporaryDirectory() as tmp:
            logged = []
            synth = _FakeSynth(submit_ok=False)
            sess, _v, _voice, _s, view = _dub_session(
                tmp, media=5.5, synth=synth, overrides={"live_sync_mode": "live"})
            sess._log = logged.append
            sess._start_dub()
            sess._last_pacer_mono = 1e9
            sess.submit_segment(_dub_seg("ciao", start=5.0, end=7.0))
            sess._tick_once(time.monotonic())                # rejected
            self.assertTrue(any("rejected" in line for line in logged), logged)
        with tempfile.TemporaryDirectory() as tmp:
            logged = []
            sess, _v, _voice, synth, view = _dub_session(
                tmp, media=5.5, overrides={"live_sync_mode": "live"})
            sess._log = logged.append
            sess._start_dub()
            sess._last_pacer_mono = 1e9
            sess.submit_segment(_dub_seg("ciao", start=5.0, end=7.0))
            sess._tick_once(time.monotonic())                # requested, no clip yet
            view.media = 9.6                                 # 4.6 s behind the start
            sess._tick_once(time.monotonic())
            self.assertTrue(any("expired" in line for line in logged), logged)

    def test_status_reports_voice_lines_said_and_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth = _FakeSynth(submit_ok=False)
            sess, _v, _voice, _s, _view = _dub_session(
                tmp, media=5.5, synth=synth, overrides={"live_sync_mode": "live"})
            sess._start_dub()
            sess._last_pacer_mono = 1e9
            sess.submit_segment(_dub_seg("ciao", start=5.0, end=7.0))
            sess._tick_once(time.monotonic())
            sess._publish_status(5.5)
            st = sess.status()
            self.assertTrue(st.dub_on)
            self.assertEqual((st.voiced, st.voice_dropped), (0, 1))

    def test_pending_voice_keeps_dub_off_quietly_until_attached(self):
        # The GUI builds the voice mpv on a worker: until it arrives the dub stays
        # off without the "TTS unavailable" warning, then turns on by itself.
        with tempfile.TemporaryDirectory() as tmp:
            sess, synth = self._voiceless_session(tmp, dub=True, voice_pending=True)
            sess._start_dub()
            self.assertFalse(sess._scheduler._dub)
            self.assertIsNone(sess.status().warning_key)
            sess.attach_voice(pe.InMemoryVoice())
            sess._tick_once(time.monotonic())
            self.assertTrue(synth.started)
            self.assertTrue(sess._scheduler._dub)

    def test_enabling_dub_at_runtime_waits_for_the_voice_backend(self):
        # Started with the dub off (no voice backend): turning it on must not be a
        # silent no-op; it waits for the backend and then enables the dub.
        with tempfile.TemporaryDirectory() as tmp:
            sess, synth = self._voiceless_session(tmp, dub=False, voice_pending=False)
            sess._start_dub()
            sess.set_dub_enabled(True)
            sess._tick_once(time.monotonic())
            self.assertFalse(synth.started)                  # nothing to play on yet
            self.assertFalse(sess._scheduler._dub)
            sess.attach_voice(pe.InMemoryVoice())
            sess._tick_once(time.monotonic())
            self.assertTrue(synth.started)
            self.assertTrue(sess._scheduler._dub)

    def test_attached_voice_does_not_enable_an_unwanted_dub(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, synth = self._voiceless_session(tmp, dub=False, voice_pending=False)
            sess._start_dub()
            sess.attach_voice(pe.InMemoryVoice())
            sess._tick_once(time.monotonic())
            self.assertFalse(synth.started)
            self.assertFalse(sess._scheduler._dub)

    def test_voice_build_failure_turns_the_dub_off_with_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, synth = self._voiceless_session(tmp, dub=True, voice_pending=True)
            sess._start_dub()
            sess.voice_unavailable()
            sess._tick_once(time.monotonic())
            self.assertFalse(sess._scheduler._dub)
            self.assertEqual(sess.status().warning_key, "live_warn_tts_unavailable")

    def test_seek_outside_coverage_keeps_one_segment_per_sentence(self):
        # review D: the restarted decoder re-emits the span after the target with
        # new ids; the superseded segment must go, and its late clip must not be
        # accepted, so the sentence is never voiced twice. Both sync modes.
        for mode in ("live", "delayed"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                sess, _v, _voice, synth, view = _dub_session(
                    tmp, media=9.0, overrides={"live_sync_mode": mode})
                sess._start_dub()
                sess._last_pacer_mono = 1e9          # isolate from the file pacer
                sess._emit_segment(10.0, 12.0, "hello", "ciao", italic=False)
                sess._tick_once(time.monotonic())
                old_id = synth.submitted[0][0]
                sess.notify_user_seek(5.0)           # not covered: decoder restarts
                view.media = 5.0
                sess._tick_once(time.monotonic())
                sess._emit_segment(10.0, 12.0, "hello", "ciao", italic=False)
                view.media = 9.5
                sess._tick_once(time.monotonic())
                covering = [s for s in sess._scheduler._segments.values()
                            if s.start <= 10.5 < s.end]
                self.assertEqual([s.gen for s in covering], [sess._gen])
                # the old request's clip arrives late: it is not accepted
                synth.push(old_id, 0, Clip(old_id, 0, "/old.mp3", 2.0, "+0%",
                                           voice_start_s=0.0, voice_end_s=2.0))
                sess._tick_once(time.monotonic())
                self.assertNotIn(old_id, sess._scheduler._dub_state)

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


class LeadCalibrationTests(unittest.TestCase):
    """The voice lead is learned from the first clips' real start delay."""

    def test_first_voice_position_after_start_sets_the_lead(self):
        from videotranslator.live_scheduler import PreloadClip, StartClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice, _, _ = _dub_session(tmp)
            clock = {"t": 100.0}
            sess._clock = lambda: clock["t"]
            video.bridge.extra_latest("voice-time-pos", 3.0, 99.0)   # previous clip
            sess._execute([PreloadClip(1, "/c.mp3", 0.1), StartClip(1, 1.0)])
            sess._calibrate_lead()
            self.assertEqual(sess._scheduler._lead, 0.25)          # stale: ignored
            video.bridge.extra_latest("voice-time-pos", 0.1, 100.05)  # still at skip
            sess._calibrate_lead()
            self.assertEqual(sess._scheduler._lead, 0.25)
            video.bridge.extra_latest("voice-time-pos", 0.15, 100.18)
            sess._calibrate_lead()
            self.assertAlmostEqual(sess._scheduler._lead, 0.18)
            video.bridge.extra_latest("voice-time-pos", 0.9, 100.9)  # later reads
            sess._calibrate_lead()
            self.assertAlmostEqual(sess._scheduler._lead, 0.18)    # one per clip


class LiveSessionVoiceFadeTests(unittest.TestCase):
    """StopClip(fade_s) fades the voice out before stopping it (design 4.11)."""

    def _playing(self, tmp):
        sess, video, voice, _, _ = _dub_session(tmp)
        sess._voice_state = "playing"
        voice.calls.clear()
        return sess, video, voice

    def test_fade_lowers_the_volume_then_stops_and_restores(self):
        from videotranslator.live_scheduler import StopClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice = self._playing(tmp)
            sess._execute([StopClip(0.18)])
            self.assertEqual(sess._voice_state, "fading")      # device still busy
            self.assertNotIn(("stop",), voice.calls)
            for _ in range(20):
                sess._step_voice_fade()
            vols = [c[1] for c in voice.calls if c[0] == "set_volume"]
            self.assertGreater(len(vols), 5)
            self.assertEqual(vols[:-1], sorted(vols[:-1], reverse=True))
            self.assertIn(("stop",), voice.calls)
            self.assertEqual(vols[-1], 100.0)                   # restored after stop
            self.assertLess(voice.calls.index(("stop",)),
                            len(voice.calls) - 1)
            self.assertEqual(sess._voice_state, "idle")
            self.assertIsNone(sess._voice_fade)

    def test_clip_ending_during_the_fade_restores_the_volume(self):
        from videotranslator.live_scheduler import StopClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice = self._playing(tmp)
            sess._execute([StopClip(0.18)])
            sess._step_voice_fade()
            video.bridge.extra_latest("voice-eof", (3, "eof"), 1.0)
            sess._sync_voice_state()
            self.assertEqual(sess._voice_state, "idle")
            self.assertIsNone(sess._voice_fade)
            self.assertEqual(voice.calls[-1], ("set_volume", 100.0))

    def test_immediate_stop_cancels_a_fade(self):
        from videotranslator.live_scheduler import StopClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice = self._playing(tmp)
            sess._execute([StopClip(0.18)])
            sess._step_voice_fade()
            sess._execute([StopClip(0.0)])                      # seek / stop
            self.assertEqual(sess._voice_state, "idle")
            self.assertIsNone(sess._voice_fade)
            self.assertEqual(voice.calls[-2:], [("stop",), ("set_volume", 100.0)])

    def test_fade_while_idle_is_an_immediate_stop(self):
        from videotranslator.live_scheduler import StopClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice = self._playing(tmp)
            sess._voice_state = "preloaded"
            sess._execute([StopClip(0.18)])
            self.assertEqual(sess._voice_state, "idle")
            self.assertEqual(voice.calls, [("stop",)])

    def test_mute_during_the_fade_is_applied_at_its_end(self):
        from videotranslator.live_scheduler import StopClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice = self._playing(tmp)
            sess._start_dub()
            voice.calls.clear()
            sess._voice_state = "playing"
            sess._execute([StopClip(0.18)])
            sess._step_voice_fade()
            video.mixer.set_muted(True)
            sess._reassert_mixer()                 # does not jump the fade back up
            vols = [c[1] for c in voice.calls if c[0] == "set_volume"]
            self.assertTrue(all(v < 100.0 for v in vols))
            for _ in range(20):
                sess._step_voice_fade()
            self.assertEqual(voice.calls[-1], ("set_volume", 0.0))  # muted, not 100

    def test_teardown_during_a_fade_restores_the_volume(self):
        from videotranslator.live_scheduler import StopClip
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, voice = self._playing(tmp)
            sess._execute([StopClip(0.18)])
            sess._step_voice_fade()
            sess._teardown_outputs()
            self.assertIn(("stop",), voice.calls)
            self.assertEqual(voice.calls[-1], ("set_volume", 100.0))
            self.assertIsNone(sess._voice_fade)


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


class SchedulerDrainedTests(unittest.TestCase):
    """DubScheduler.drained gates the soft auto-stop at end of source."""

    def _sched(self, **kw):
        from videotranslator.live_scheduler import DubScheduler
        return DubScheduler(mode="delayed", **kw)

    def test_none_clock_is_never_drained(self):
        self.assertFalse(self._sched().drained(None))

    def test_empty_scheduler_is_drained(self):
        self.assertTrue(self._sched().drained(0.0))

    def test_pending_caption_is_not_drained_until_its_span_elapses(self):
        sched = self._sched()
        sched.upsert(LiveSegment(1, 0, 1.0, 3.0, "hi", text_tgt="ciao"))
        sched.tick(1.5)                       # caption shown, span not over
        self.assertFalse(sched.drained(1.5))
        self.assertTrue(sched.drained(4.0))   # now past its end

    def test_dub_line_still_synthesizing_is_not_drained(self):
        sched = self._sched(dub=True)
        seg = LiveSegment(1, 0, 1.0, 3.0, "hi", text_tgt="ciao", dub_ok=True)
        sched.upsert(seg)                     # dub state -> "translated"
        self.assertFalse(sched.drained(5.0))  # a dubbed line is still pending

    def test_drained_after_the_dub_line_is_dropped(self):
        sched = self._sched(dub=True)
        seg = LiveSegment(1, 0, 1.0, 3.0, "hi", text_tgt="ciao", dub_ok=True)
        sched.upsert(seg)
        # No TTS worker feeds a clip: ticking past the slot drops the line.
        for now in (1.0, 3.0, 6.0, 9.0):
            sched.tick(now, main_running=True, voice_state="idle")
        self.assertTrue(sched.drained(9.0))

    _ACTIVE = ("translated", "synth", "ready", "preloaded", "playing")

    def _play_a_clip(self, sched):
        """Drive one segment to a playing clip (returns its seg_id)."""
        seg = LiveSegment(1, 0, 1.0, 3.0, "hi", text_tgt="ciao", dub_ok=True)
        clip = SimpleNamespace(path="/tmp/x.wav", audible_s=0.5, voice_start_s=0.0)
        sched.upsert(seg)                            # -> translated
        sched.tick(0.5, voice_state="idle")          # -> requests TTS (synth)
        sched.clip_ready(1, 0, clip)                 # -> ready
        sched.tick(1.0, voice_state="idle")          # -> preloaded
        sched.tick(1.2, voice_state="preloaded")     # -> playing
        self.assertEqual(sched._dub_state[1], "playing")
        return 1

    def test_seek_past_a_playing_line_does_not_orphan_it(self):
        # A forward seek past a clip that is playing must not leave the segment in
        # a "playing" dub state after _dub_reset clears the _playing pointer: no
        # drop loop handles that state, so drained() would hang forever (the
        # intermittent field bug after a seek toward the end). Both a within
        # coverage seek (restart False) and a decoder restart (restart True).
        for restart in (False, True):
            with self.subTest(restart=restart):
                sched = self._sched(dub=True, subs=False)
                self._play_a_clip(sched)
                sched.on_seek(10.0, 1, restart=restart)   # forward seek past the line
                sched.tick(10.0, voice_state="idle")
                self.assertNotIn(sched._dub_state.get(1), self._ACTIVE)
                self.assertTrue(sched.drained(10.0))

    def test_seek_past_a_preloaded_line_resolves_it(self):
        # A preloaded clip whose pointer is cleared must not orphan either: it
        # becomes "ready" and the normal late-drop path resolves it.
        sched = self._sched(dub=True, subs=False)
        seg = LiveSegment(1, 0, 1.0, 3.0, "hi", text_tgt="ciao", dub_ok=True)
        clip = SimpleNamespace(path="/tmp/x.wav", audible_s=0.5, voice_start_s=0.0)
        sched.upsert(seg)
        sched.tick(0.5, voice_state="idle")
        sched.clip_ready(1, 0, clip)
        sched.tick(1.0, voice_state="idle")          # -> preloaded
        self.assertEqual(sched._dub_state[1], "preloaded")
        sched.on_seek(10.0, 0)                        # forward seek past it
        sched.tick(10.0, voice_state="idle")          # late-drop resolves the "ready"
        self.assertNotIn(sched._dub_state.get(1), self._ACTIVE)
        self.assertTrue(sched.drained(10.0))

    def test_dub_off_while_playing_does_not_orphan_the_line(self):
        # The same orphan via set_dub(False): drained() checks dub states even
        # when dub is off, so turning it off mid-clip must resolve the line.
        sched = self._sched(dub=True, subs=False)
        self._play_a_clip(sched)
        sched.set_dub(False)                          # user disables dub mid-clip
        self.assertTrue(sched.drained(5.0))

    def test_dub_off_with_queued_voices_drains_at_end(self):
        # Dub off must leave no active voice: a playing clip, a ready line and a
        # synth line in flight. _dub_actions no longer runs at dub off, so any
        # active state would orphan drained() at end of source.
        sched = self._sched(dub=True, subs=False)
        self._play_a_clip(sched)                      # seg 1 -> playing
        sched.upsert(LiveSegment(2, 0, 5.0, 7.0, "b", text_tgt="bb", dub_ok=True))
        sched.upsert(LiveSegment(3, 0, 9.0, 11.0, "c", text_tgt="cc", dub_ok=True))
        sched._dub_state[2] = "ready"
        sched._clips[2] = SimpleNamespace(path="/y.wav", audible_s=0.5, voice_start_s=0.0)
        sched._dub_state[3] = "synth"
        sched.set_dub(False)
        self.assertEqual(sched._dub_state.get(1), "done")   # spoken clip kept
        self.assertNotIn(sched._dub_state.get(2), self._ACTIVE)
        self.assertNotIn(sched._dub_state.get(3), self._ACTIVE)
        self.assertTrue(sched.drained(20.0))

    def test_dub_off_then_on_re_arms_future_lines_only(self):
        # Re-enabling dub re-arms only the lines still in time: a cached one as
        # "ready" (no second TTS request), a past one not at all. Counters intact.
        sched = self._sched(dub=True, subs=False)
        sched.upsert(LiveSegment(2, 0, 20.0, 22.0, "b", text_tgt="bb", dub_ok=True))
        sched.upsert(LiveSegment(3, 0, 1.0, 3.0, "c", text_tgt="cc", dub_ok=True))
        sched._dub_state[2] = "ready"
        sched._clips[2] = SimpleNamespace(path="/y.wav", audible_s=0.5, voice_start_s=0.0)
        sched._dub_state[3] = "ready"
        sched._last_now = 10.0
        voiced0, dropped0 = sched.metrics()["voiced"], sched.metrics()["dropped"]
        sched.set_dub(False)
        sched.set_dub(True)
        self.assertEqual(sched._dub_state.get(2), "ready")  # cached -> ready, no re-request
        self.assertNotIn(3, sched._dub_state)               # past -> not re-armed
        self.assertEqual(sched.metrics()["voiced"], voiced0)
        self.assertEqual(sched.metrics()["dropped"], dropped0)

    def test_late_tts_result_after_dub_off_is_discarded(self):
        # A TTS result that lands after the line was dropped at dub off must be
        # discarded by clip_ready's state guard, with no error and no state.
        sched = self._sched(dub=True, subs=False)
        sched.upsert(LiveSegment(1, 0, 1.0, 3.0, "a", text_tgt="aa", dub_ok=True))
        sched._dub_state[1] = "synth"
        sched.set_dub(False)
        self.assertNotIn(1, sched._dub_state)
        accepted = sched.clip_ready(1, 0, SimpleNamespace(path="/z.wav",
                                                          audible_s=0.5, voice_start_s=0.0))
        self.assertFalse(accepted)
        self.assertNotIn(sched._dub_state.get(1), self._ACTIVE)

    def test_recovery_armed_unloads_a_blocking_preloaded_clip(self):
        # Delayed-mode recovery deadlock: R is late (recovery) but the device
        # holds a later clip X (preloaded) that can neither start (picture held)
        # nor expire (clock frozen). Arming the recovery must unload X so R can
        # preload, or the pacer waits for R forever.
        sched = self._sched(dub=True, subs=False)
        sched.upsert(LiveSegment(1, 0, 1.0, 3.0, "r", text_tgt="rr", dub_ok=True))
        sched.upsert(LiveSegment(2, 0, 3.0, 4.0, "x", text_tgt="xx", dub_ok=True))
        sched._clips[1] = SimpleNamespace(path="/r.wav", audible_s=1.5, voice_start_s=0.0)
        sched._clips[2] = SimpleNamespace(path="/x.wav", audible_s=0.5, voice_start_s=0.0)
        sched._dub_state[1] = "ready"          # R late, waiting
        sched._dub_state[2] = "preloaded"      # X loaded in the device
        sched._preloaded = 2
        sched.tick(3.5, voice_state="preloaded", pacer_paused=True)
        self.assertEqual(sched._pacer_recovery_seg, 1)   # R armed for recovery
        self.assertNotEqual(sched._preloaded, 2)         # X unloaded
        self.assertEqual(sched._dub_state[2], "ready")   # X back to ready (re-preloads)

    def test_recovery_never_playing_is_released_by_the_wall_clock(self):
        # Backstop: a recovery that never reaches "playing" (a lost preload/expire
        # path) is released past a wall-clock bound, so the pacer does not hang.
        sched = self._sched(dub=True, subs=False)
        sched.upsert(LiveSegment(1, 0, 1.0, 3.0, "r", text_tgt="rr", dub_ok=True))
        sched._clips[1] = SimpleNamespace(path="/r.wav", audible_s=1.5, voice_start_s=0.0)
        sched._dub_state[1] = "ready"
        sched.tick(3.5, mono=100.0, voice_state="idle", pacer_paused=True)   # arm R
        self.assertEqual(sched._pacer_recovery_seg, 1)
        sched.tick(3.5, mono=109.0, voice_state="idle", pacer_paused=True)   # bound passed
        self.assertIsNone(sched._pacer_recovery_seg)
        self.assertFalse(sched.pacer_recovery_pending)
        self.assertTrue(sched.drained(20.0))

    def test_pacer_recovery_then_drop_clears_the_pointer(self):
        # A clip armed for pacer recovery then dropped must release the recovery
        # pointer, or drained() stays false and the pacer stays blocked (
        # pacer_recovery_pending) for the whole session.
        sched = self._sched(dub=True, subs=False)
        sched.upsert(LiveSegment(1, 0, 1.0, 3.0, "a", text_tgt="aa", dub_ok=True))
        sched._dub_state[1] = "ready"
        sched._clips[1] = SimpleNamespace(path="/x.wav", audible_s=0.5, voice_start_s=0.0)
        sched.tick(2.0, voice_state="idle", pacer_paused=True)    # armed for recovery
        self.assertEqual(sched._pacer_recovery_seg, 1)
        self.assertTrue(sched.pacer_recovery_pending)
        sched.tick(2.5, voice_state="idle", pacer_paused=False)   # hold ended -> dropped
        self.assertEqual(sched._dub_state[1], "dropped")
        self.assertIsNone(sched._pacer_recovery_seg)
        self.assertFalse(sched.pacer_recovery_pending)
        self.assertTrue(sched.drained(5.0))


class LiveSessionAutoStopTests(unittest.TestCase):
    """Soft auto-stop: a finished source with an empty queue ends by itself."""

    def test_ends_after_source_done_and_everything_drained(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5)
            sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
            sess._tick_once(0.0)                       # caption shown
            sess._source_done = True
            sess._tick_once(0.5)                       # still inside the caption
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())
            sess._clock_view.media = 4.0               # picture reached the end
            sess._media_eof = True                     # mpv reports eof-reached
            sess._tick_once(1.0)
            self.assertEqual(sess.status().state, "ended")
            self.assertTrue(sess._stop.is_set())

    def test_no_stop_while_source_not_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=4.0)      # past any caption
            sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
            sess._tick_once(0.0)
            sess._tick_once(0.5)
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())

    def test_no_stop_during_startup_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=4.0)
            sess._startup_hold = True
            sess._source_done = True
            sess._tick_once(0.0)
            self.assertNotEqual(sess.status().state, "ended")

    def test_no_stop_while_a_voice_clip_is_playing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=4.0)
            sess._source_done = True
            sess._media_eof = True                     # at EOF, but a clip is playing
            sess._voice_state = "playing"              # dubbing not finished yet
            sess._tick_once(0.0)
            self.assertNotEqual(sess.status().state, "ended")

    # -- end-of-source clock: the real bug and its guards -------------------
    #
    # The field bug: at EOF the picture freezes on the last frame, so the media
    # clock stops advancing (frozen last PTS) or reports None. The drain must
    # not depend on it, or the session never auto-stops. These tests drive a
    # clock that freezes/goes None at EOF (they do NOT push the clock past the
    # caption to fake the gate) and check that the stop still fires, after the
    # caption's display window, without truncating anything.

    def _eof_session(self, tmp, **overrides):
        sess, _, _ = _session(tmp, media=1.5, overrides=overrides or None)
        clock = _EofClockView(1.5)
        sess._clock_view = clock
        sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
        sess._tick_once(0.0)                    # caption shown, arrival 1.5
        clock.media = 2.98                      # picture advances to just before end
        sess._tick_once(1.48)
        sess._media_eof = True                  # mpv reports eof-reached (last frame)
        return sess, clock

    def test_frozen_clock_at_eof_still_ends_after_the_window(self):
        # Last PTS freezes just before the caption end (seg.end > frozen now),
        # so without the fix drained() stays False forever and the session hangs.
        with tempfile.TemporaryDirectory() as tmp:
            sess, clock = self._eof_session(tmp)
            sess._source_done = True
            sess._tick_once(1.6)                # frozen; still inside the window
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())
            sess._tick_once(2.4)                # wall clock past the window
            self.assertEqual(sess.status().state, "ended")
            self.assertTrue(sess._stop.is_set())

    def test_invalid_none_clock_at_eof_still_ends(self):
        # mpv can report an invalid position (None) at EOF; drained(None) is
        # never True, so without the fix the session hangs. The wall clock seeded
        # from the last real media position must still drain it.
        with tempfile.TemporaryDirectory() as tmp:
            sess, clock = self._eof_session(tmp)
            sess._source_done = True
            clock.invalid = True                # now() -> None from here on
            sess._tick_once(1.6)
            self.assertNotEqual(sess.status().state, "ended")
            sess._tick_once(2.4)
            self.assertEqual(sess.status().state, "ended")

    def test_frozen_clock_waits_for_the_caption_display_window(self):
        # The last PTS freezes exactly at seg.end: the old seg.end gate would
        # stop at once and the teardown would clear the subtitle before its
        # _SUB_MIN_DISPLAY_S. The drain must wait for the full display window.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5)
            clock = _EofClockView(1.5)
            sess._clock_view = clock
            sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
            sess._tick_once(0.0)                # arrival 1.5 -> clear_time 3.3
            clock.media = 3.0                   # picture reaches exactly the end
            sess._tick_once(1.5)
            sess._source_done = True
            sess._media_eof = True              # mpv reports eof-reached
            sess._tick_once(1.6)                # frozen at 3.0, window not over
            self.assertNotEqual(sess.status().state, "ended")
            sess._tick_once(2.0)                # wall clock past clear_time 3.3
            self.assertEqual(sess.status().state, "ended")

    def test_no_stop_while_source_not_done_even_with_a_frozen_clock(self):
        # An unfinished (or endless) source never sets _source_done: the frozen
        # clock and any amount of wall clock must not trigger the stop.
        with tempfile.TemporaryDirectory() as tmp:
            sess, clock = self._eof_session(tmp)
            for mono in (1.6, 2.4, 4.0, 8.0):
                sess._tick_once(mono)
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())

    def test_voice_clip_blocks_the_stop_despite_the_wall_clock(self):
        # A dubbed line still speaking must not be cut short by the wall-clock
        # drain: the stop waits until the voice device is idle again.
        with tempfile.TemporaryDirectory() as tmp:
            sess, clock = self._eof_session(tmp)
            sess._source_done = True
            sess._voice_state = "playing"       # a dub line is still speaking
            for mono in (1.6, 2.4, 4.0, 8.0):   # wall clock well past the window
                sess._tick_once(mono)
            self.assertNotEqual(sess.status().state, "ended")
            sess._voice_state = "idle"          # the dub finished speaking
            for mono in (9.0, 9.5, 10.0):
                sess._tick_once(mono)
            self.assertEqual(sess.status().state, "ended")

    def test_no_autostop_while_user_paused_mid_video(self):
        # A VOD decoder runs far ahead of the picture, so _source_done is set
        # early, with the video still playing. The user then pauses mid-video:
        # the media clock freezes, but this is a PAUSE, not EOF. The wall-clock
        # drain must not advance past the pending captions and stop during the
        # pause (subs only: no dub line holds it). Guards the pause regression.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5)
            clock = _EofClockView(1.5)
            sess._clock_view = clock
            sess.submit_segment(_seg("uno", start=1.0, end=3.0))
            sess.submit_segment(LiveSegment(2, 0, 7.0, 9.0, "two", text_tgt="due"))
            sess._tick_once(0.0)
            clock.media = 8.0                  # picture advanced to 8 s
            sess._tick_once(1.0)
            sess._source_done = True           # decoder finished early, picture at 8 s
            sess._user_paused = True           # user pauses at 8 s (NOT eof)
            for mono in (2.0, 5.0, 12.0, 30.0):   # long pause, lots of wall clock
                sess._tick_once(mono)
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())

    def test_no_autostop_mid_video_past_last_caption_without_eof(self):
        # The last caption ends well before the video does (a captionless tail:
        # credits or silence). _source_done fires early and the picture plays on
        # PAST the last caption with the clock still advancing. Without the EOF
        # gate drained() would be True and the session would stop mid-video. It
        # must wait until the picture actually reaches the end.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5)
            clock = _EofClockView(1.5)
            sess._clock_view = clock
            sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
            sess._tick_once(0.0)
            sess._source_done = True            # decoder finished; silent tail remains
            clock.media = 8.0                   # picture plays on, past the last caption
            sess._tick_once(1.0)
            self.assertNotEqual(sess.status().state, "ended")
            clock.media = 12.0
            sess._tick_once(1.5)
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())
            sess._media_eof = True              # picture reaches the last frame
            sess._tick_once(2.0)
            self.assertEqual(sess.status().state, "ended")

    def test_no_autostop_during_a_seek_none_clock_without_eof(self):
        # A within-coverage seek briefly makes now() None while _source_done stays
        # True (restart=False keeps it). This is not EOF (no eof-reached), so the
        # None must not arm the wall clock and stop the session.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5)
            clock = _EofClockView(1.5)
            sess._clock_view = clock
            sess.submit_segment(_seg("ciao", start=1.0, end=3.0))
            sess._tick_once(0.0)
            clock.media = 2.5
            sess._tick_once(1.0)
            sess._source_done = True
            clock.invalid = True                # seek in progress: now() -> None
            for mono in (1.5, 2.0, 5.0, 12.0):
                sess._tick_once(mono)
            self.assertNotEqual(sess.status().state, "ended")
            self.assertFalse(sess._stop.is_set())

    def test_frozen_clock_expires_the_tail_dub_and_ends(self):
        # The tail dub gate: with the clock frozen below seg.end the tail line
        # stays _still_voiceable (slot_end = end + overhang > frozen now), so it
        # never expires and drained() hangs on _ACTIVE_DUB. The end-of-source
        # wall clock must advance the scheduler tick so the slot ends, the line
        # is dropped, and the session stops. Guards the primary fix, not only the
        # _clear_time swap (which does not touch the dub gate).
        import queue as _queue
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5,
                                  overrides={"live_dub_enabled": True})
            # A TTS worker that accepts the request but never returns a clip, so
            # the line stays "synth" (active) until its slot ends.
            sess._synth = SimpleNamespace(submit=lambda *a, **k: True,
                                          results=_queue.Queue(), name="fake",
                                          stop=lambda *a, **k: True)
            clock = _EofClockView(1.5)
            sess._clock_view = clock
            sess.submit_segment(LiveSegment(1, 0, 1.0, 3.0, "hi",
                                            text_tgt="ciao", dub_ok=True))
            sess._tick_once(0.0)                # translated -> RequestTts -> synth
            clock.media = 2.98
            sess._tick_once(1.48)
            sess._source_done = True
            sess._media_eof = True             # mpv reports eof-reached
            sess._tick_once(1.6)               # frozen: tail dub still voiceable
            self.assertNotEqual(sess.status().state, "ended")
            for mono in (2.4, 3.0, 4.0, 5.0):  # wall clock past slot_end + window
                sess._tick_once(mono)
            self.assertEqual(sess.status().state, "ended")

    def test_tail_dub_starting_past_the_frozen_pts_still_ends(self):
        # Point 2: the last line starts just past the last video frame (its audio
        # ends a hair after the picture). With the clock frozen at the last frame
        # its slot (start .. end + overhang) is never reached by the frozen now,
        # so _still_voiceable stays True and it hangs in _ACTIVE_DUB. The EOF wall
        # clock must carry the scheduler past its slot so it is voiced or expires.
        import queue as _queue
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.5,
                                  overrides={"live_dub_enabled": True})
            sess._synth = SimpleNamespace(submit=lambda *a, **k: True,
                                          results=_queue.Queue(), name="fake",
                                          stop=lambda *a, **k: True)
            clock = _EofClockView(1.5)
            sess._clock_view = clock
            sess.submit_segment(LiveSegment(1, 0, 3.05, 3.5, "hi",
                                            text_tgt="ciao", dub_ok=True))
            sess._tick_once(0.0)
            clock.media = 3.0                  # picture stops on the last frame
            sess._tick_once(1.0)
            sess._source_done = True
            sess._media_eof = True
            sess._tick_once(1.6)               # frozen: line not yet at its slot end
            self.assertNotEqual(sess.status().state, "ended")
            for mono in (2.4, 3.0, 4.0, 6.0):  # wall clock past slot_end (4.1)
                sess._tick_once(mono)
            self.assertEqual(sess.status().state, "ended")

    def test_disable_dub_after_voice_errors_leaves_no_orphan(self):
        # The dub is also disabled automatically after 3 voice-output errors,
        # through _disable_dub -> set_dub(False). Queued voices must not orphan
        # the auto-stop, and a late TTS result must be discarded.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=1.0,
                                  overrides={"live_dub_enabled": True})
            sched = sess._scheduler
            sched.upsert(LiveSegment(1, 0, 1.0, 3.0, "a", text_tgt="aa", dub_ok=True))
            sched.upsert(LiveSegment(2, 0, 5.0, 7.0, "b", text_tgt="bb", dub_ok=True))
            sched._dub_state[1] = "ready"
            sched._clips[1] = SimpleNamespace(path="/x.wav", audible_s=0.5, voice_start_s=0.0)
            sched._dub_state[2] = "synth"
            sess._voice_fail = 3
            sess._disable_dub("tts_unavailable")     # automatic path after 3 errors
            active = ("translated", "synth", "ready", "preloaded", "playing")
            self.assertNotIn(sched._dub_state.get(1), active)
            self.assertNotIn(sched._dub_state.get(2), active)
            self.assertTrue(sched.drained(20.0))
            self.assertFalse(sched.clip_ready(2, 0, SimpleNamespace(
                path="/y.wav", audible_s=0.5, voice_start_s=0.0)))

    def test_session_seek_past_a_speaking_clip_still_autostops_at_eof(self):
        # The field bug end to end: a within-coverage forward seek past a clip
        # that is speaking abandons it. Without finalizing its state the segment
        # orphans in "playing" and drained() hangs forever (auto-stop never
        # fires). After the fix the session still auto-stops at end of media.
        with tempfile.TemporaryDirectory() as tmp:
            sess, _, _ = _session(tmp, media=0.5,
                                  overrides={"live_dub_enabled": True})
            clock = _EofClockView(0.5)
            sess._clock_view = clock
            sched = sess._scheduler
            # A playing clip for seg1, and a later caption covering the seek
            # target so the seek stays within coverage (restart False).
            seg1 = LiveSegment(1, 0, 1.0, 3.0, "one", text_tgt="uno", dub_ok=True)
            seg2 = LiveSegment(2, 0, 14.0, 16.0, "two", text_tgt="due", dub_ok=True)
            clip = SimpleNamespace(path="/tmp/x.wav", audible_s=1.5, voice_start_s=0.0)
            sched.upsert(seg1)
            sched.upsert(seg2)
            sched.tick(0.5, voice_state="idle")
            sched.clip_ready(1, 0, clip)
            sched.tick(1.0, voice_state="idle")
            sched.tick(1.2, voice_state="preloaded")
            self.assertEqual(sched._dub_state[1], "playing")
            sess._voice_state = "playing"          # as in the field dump before the seek
            sess._control.put(("seek", 15.0))      # real session seek path, within coverage
            clock.media = 15.0
            sess._tick_once(1.0)                    # on_seek abandons the speaking clip
            self.assertNotIn(sched._dub_state.get(1), ("translated", "synth", "ready",
                                                       "preloaded", "playing"))
            sess._voice_state = "idle"             # the clip stopped (dump: voice_state idle)
            sess._source_done = True
            sess._media_eof = True
            clock.media = 16.0
            for mono in (1.5, 2.0, 3.0, 5.0):
                sess._tick_once(mono)
            self.assertEqual(sess.status().state, "ended")


if __name__ == "__main__":
    unittest.main()
