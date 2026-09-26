import tempfile
import time
import unittest
import asyncio
import threading

import numpy as np

from videotranslator.live_tts import (
    Clip,
    EdgeClipSynth,
    EdgeDurationModel,
    LeadCalibrator,
    LiveTtsUnavailable,
    choose_rate,
    measure_silence,
    mp3_cbr_duration_s,
    silence_bounds,
)


async def _noop_sleep(_seconds):
    return None


class _FakeComm:
    def __init__(self, data):
        self._data = data

    async def stream(self):
        yield {"type": "WordBoundary"}          # non-audio, ignored
        yield {"type": "audio", "data": self._data}


class _FakeBreaker:
    def __init__(self, allow=True):
        self._allow = allow
        self.successes = 0
        self.failures = 0

    def allow(self):
        return self._allow

    def record_success(self):
        self.successes += 1

    def record_failure(self, *, kind):
        self.failures += 1
        return None


class EdgeClipSynthTests(unittest.TestCase):
    def test_shutdown_awaits_active_stream_cleanup_and_closes_loop(self):
        started, cleaned = threading.Event(), threading.Event()

        class BlockingComm:
            async def stream(self):
                try:
                    yield {"type": "audio", "data": b"partial"}
                    started.set()
                    await asyncio.Event().wait()
                finally:
                    cleaned.set()

        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, lambda *a, **kw: BlockingComm())
            s.start()
            try:
                self.assertTrue(s.submit(0, 0, "hello", 0, time.monotonic() + 60))
                self.assertTrue(started.wait(2))
            finally:
                self.assertTrue(s.stop(3))
            self.assertTrue(cleaned.is_set())
            self.assertTrue(s._loop.is_closed())
            self.assertEqual(s._in_flight, 0)
            self.assertEqual(list(s._out_dir.glob("*.part")), [])
            self.assertFalse(s.submit(1, 0, "late", 0, time.monotonic() + 60))

    def test_live_speech_uses_the_shared_sanitizer(self):
        from videotranslator.tts_text_sanitizer import sanitize_for_tts
        seen = []

        def factory(text, voice, **kwargs):
            seen.append(text)
            return _FakeComm(b"\x00" * 6000)

        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, factory)
            s.start()
            try:
                s.submit(0, 0, "Hello: world; again...", 0, time.monotonic() + 10)
                s.results.get(timeout=3)
            finally:
                s.stop(3)
            self.assertEqual(seen, [sanitize_for_tts("Hello: world; again...")])

    def _synth(self, tmp, factory, **kw):
        br = kw.pop("breaker", _FakeBreaker())
        s = EdgeClipSynth("v", tmp, breaker=br, communicate_factory=factory,
                          av_module=None, min_interval_s=0.0, sleep=_noop_sleep, **kw)
        s._breaker_ref = br
        return s

    def test_synthesizes_a_clip(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, lambda t, v, **k: _FakeComm(b"\x00" * 6000))
            s.start()
            self.assertTrue(s.submit(0, 0, "hello", 10, time.monotonic() + 10))
            seg_id, gen, clip, reason = s.results.get(timeout=5)
            s.stop(3.0)
            self.assertIsNone(reason)
            self.assertIsNotNone(clip)
            self.assertAlmostEqual(clip.duration, 1.0, places=2)
            self.assertEqual(clip.rate, "+10%")
            self.assertEqual(s._breaker_ref.successes, 1)

    def test_empty_text_reports_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, lambda t, v, **k: _FakeComm(b"\x00" * 100))
            s.start()
            s.submit(1, 0, "   ", 0, time.monotonic() + 10)
            _sid, _g, clip, reason = s.results.get(timeout=5)
            s.stop(3.0)
            self.assertIsNone(clip)
            self.assertEqual(reason, "empty")

    def test_failure_trips_the_breaker_and_reports_error(self):
        def boom(t, v, **k):
            raise RuntimeError("network down")
        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, boom)
            s.start()
            s.submit(2, 0, "hello", 0, time.monotonic() + 10)
            _sid, _g, clip, reason = s.results.get(timeout=5)
            s.stop(3.0)
            self.assertIsNone(clip)
            self.assertEqual(reason, "error")
            self.assertGreaterEqual(s._breaker_ref.failures, 1)

    def test_submit_rejected_when_breaker_open_or_deadline_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, lambda t, v, **k: _FakeComm(b"\x00" * 100),
                            breaker=_FakeBreaker(allow=False))
            s.start()
            self.assertFalse(s.submit(0, 0, "x", 0, time.monotonic() + 10))  # breaker open
            s.stop(3.0)
        with tempfile.TemporaryDirectory() as tmp:
            s = self._synth(tmp, lambda t, v, **k: _FakeComm(b"\x00" * 100))
            s.start()
            self.assertFalse(s.submit(0, 0, "x", 0, time.monotonic() - 1))   # past deadline
            s.stop(3.0)


class Mp3DurationTests(unittest.TestCase):
    def test_bytes_to_seconds(self):
        self.assertEqual(mp3_cbr_duration_s(6000), 1.0)
        self.assertEqual(mp3_cbr_duration_s(3000), 0.5)


class ClipTests(unittest.TestCase):
    def test_audible_span(self):
        clip = Clip(0, 0, "/x.mp3", 2.0, "+0%", voice_start_s=0.2, voice_end_s=1.7)
        self.assertAlmostEqual(clip.audible_s, 1.5, places=6)


class EdgeDurationModelTests(unittest.TestCase):
    def _model(self, seed=3.0):
        return EdgeDurationModel("en", seed_estimate=lambda text, lang: seed)

    def test_uses_seed_before_any_observation(self):
        model = self._model(seed=4.0)
        self.assertEqual(model.estimate("hello", 0), 4.0)

    def test_rate_shortens_estimate(self):
        model = self._model(seed=4.0)
        self.assertAlmostEqual(model.estimate("hello", 100), 2.0, places=6)  # /2

    def test_observation_drives_estimate(self):
        model = self._model(seed=99.0)   # seed deliberately wrong
        # 10 chars audible in 2 s at rate 0 -> 5 cps
        model.observe("0123456789", 0, 2.0)
        self.assertAlmostEqual(model.estimate("0123456789", 0), 2.0, places=6)

    def test_rate_normalisation_in_observe(self):
        model = self._model(seed=99.0)
        # 10 chars audible in 1 s at +100% -> rate0 duration 2 s -> 5 cps
        model.observe("0123456789", 100, 1.0)
        self.assertAlmostEqual(model.estimate("0123456789", 0), 2.0, places=6)


class ChooseRateTests(unittest.TestCase):
    def _model(self, seed):
        return EdgeDurationModel("en", seed_estimate=lambda text, lang: seed)

    def test_speeds_up_when_too_long(self):
        # estimate 6 s into a 5 s slot -> +20%
        self.assertEqual(choose_rate("x", 5.0, self._model(6.0)), 20)

    def test_zero_when_it_fits(self):
        self.assertEqual(choose_rate("x", 5.0, self._model(4.0)), 0)

    def test_clamped_to_max(self):
        self.assertEqual(choose_rate("x", 1.0, self._model(10.0)), 30)

    def test_nonpositive_slot_returns_max(self):
        self.assertEqual(choose_rate("x", 0.0, self._model(4.0)), 30)


class SilenceBoundsTests(unittest.TestCase):
    def test_finds_the_audible_span(self):
        rate = 16000
        sil = np.zeros(rate // 2, dtype=np.float32)          # 0.5 s silence
        tone = (0.5 * np.sin(2 * np.pi * 220 * np.arange(rate) / rate)).astype(np.float32)
        clip = np.concatenate([sil, tone, sil])              # silence, 1 s tone, silence
        bounds = silence_bounds(clip, rate)
        self.assertIsNotNone(bounds)
        start, end = bounds
        self.assertAlmostEqual(start, 0.5, delta=0.05)
        self.assertAlmostEqual(end, 1.5, delta=0.05)

    def test_all_silence_is_none(self):
        self.assertIsNone(silence_bounds(np.zeros(16000, dtype=np.float32), 16000))

    def test_empty_is_none(self):
        self.assertIsNone(silence_bounds(np.zeros(0, dtype=np.float32), 16000))


class MeasureSilenceTests(unittest.TestCase):
    def test_uses_injected_av_and_delegates(self):
        rate = 16000
        tone = (0.5 * np.sin(2 * np.pi * 220 * np.arange(rate) / rate))
        pcm16 = (np.concatenate([np.zeros(rate // 2), tone]) * 32768).astype(np.int16)

        class _Frame:
            pass

        class _Resampled:
            def to_ndarray(self):
                return pcm16.reshape(1, -1)

        class _Resampler:
            def resample(self, frame):
                return [_Resampled()]

        class _Container:
            streams = type("S", (), {"audio": [object()]})()

            def decode(self, stream):
                return [_Frame()]

            def close(self):
                pass

        class _Av:
            AudioResampler = staticmethod(lambda **k: _Resampler())

            @staticmethod
            def open(path):
                return _Container()

        bounds = measure_silence("x.mp3", av_module=_Av())
        self.assertIsNotNone(bounds)
        self.assertAlmostEqual(bounds[0], 0.5, delta=0.05)

    def test_returns_none_on_failure(self):
        class _Av:
            @staticmethod
            def open(path):
                raise OSError("no file")
        self.assertIsNone(measure_silence("x.mp3", av_module=_Av()))


class LeadCalibratorTests(unittest.TestCase):
    def test_seed_is_bounded(self):
        self.assertEqual(LeadCalibrator(0.9, hi=0.6).lead, 0.6)
        self.assertEqual(LeadCalibrator(0.0, lo=0.1).lead, 0.1)

    def test_measures_onset_and_emas(self):
        cal = LeadCalibrator(0.25, alpha=0.5)
        cal.on_start(mono_unpause=10.0, skip_s=0.1)
        # first audible pts (>= skip) at mono 10.30 -> onset 0.30
        self.assertAlmostEqual(cal.on_voice_pts(10.30, 0.12), 0.30, places=3)
        cal.on_start(mono_unpause=20.0, skip_s=0.1)
        # onset 0.20 -> EMA 0.5*0.20 + 0.5*0.30 = 0.25
        self.assertAlmostEqual(cal.on_voice_pts(20.20, 0.15), 0.25, places=3)

    def test_ignores_pts_before_skip(self):
        cal = LeadCalibrator(0.25)
        cal.on_start(mono_unpause=10.0, skip_s=0.2)
        self.assertIsNone(cal.on_voice_pts(10.10, 0.05))     # pts below skip


if __name__ == "__main__":
    unittest.main()
