import os
import tempfile
import unittest
from pathlib import Path

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

    def set_overlay(self, ass):
        self.overlays.append(ass)

    def set_pause(self, paused):
        self.pauses.append(paused)

    def set_speed(self, _x):
        pass

    def set_duck(self, _g):
        pass


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


class LiveSessionLifecycleTests(unittest.TestCase):
    def test_start_run_stop_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, video, cfg = _session(tmp, media=1.5)
            sess.start()
            self.assertEqual(sess.status().state, "running")
            sess.submit_segment(_seg("ciao"))
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and not video.rt.overlays:
                time.sleep(0.02)
            self.assertTrue(any("ciao" in (a or "") for a in video.rt.overlays))
            sess.request_stop()
            self.assertTrue(sess.join(3.0))
            self.assertEqual(sess.status().state, "stopped")
            self.assertFalse(any(t.name == "live-sched" and t.is_alive()
                                 for t in threading.enumerate()))
            self.assertTrue((cfg.session_dir / "session.lock").exists())


if __name__ == "__main__":
    unittest.main()
