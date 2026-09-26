import os
import tempfile
import unittest

import numpy as np

from videotranslator.live_asr import (
    AudioDecoder,
    HallucinationFilter,
    LanguageLock,
    StreamingVad,
    decoder_time,
)

_HEAVY = os.environ.get("VTAI_RUN_HEAVY_SMOKE")


class _FakeVadSession:
    def __init__(self):
        self.inputs = []

    def run(self, _outputs, feeds):
        self.inputs.append(np.array(feeds["input"], dtype=np.float32))
        return (np.array([[0.5]], dtype=np.float32), feeds["h"], feeds["c"])


class StreamingVadFramingTests(unittest.TestCase):
    def test_frames_context_and_remainder(self):
        fake = _FakeVadSession()
        vad = StreamingVad(session_factory=lambda: fake)
        data = np.arange(512 * 2 + 100, dtype=np.float32)
        probs = vad.probs(data)
        self.assertEqual(len(probs), 2)
        # first frame's context is the initial zeros
        self.assertTrue(np.all(fake.inputs[0][0, :64] == 0.0))
        # second frame's context is the last 64 samples of the first frame
        self.assertTrue(np.allclose(fake.inputs[1][0, :64], data[512 - 64:512]))
        # the 100-sample remainder completes into one more frame on the next call
        more = vad.probs(np.arange(412, dtype=np.float32))
        self.assertEqual(len(more), 1)


class _FakeSeg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text
        self.no_speech_prob, self.avg_logprob, self.compression_ratio = 0.1, -0.2, 1.5


class _FakeInfo:
    language = "en"
    language_probability = 0.92


class _FakeCuda:
    def __init__(self, available):
        self._available = available

    def is_available(self):
        return self._available

    def empty_cache(self):
        pass


class PersistentWhisperUnitTests(unittest.TestCase):
    def _utt(self, start=10.0):
        from types import SimpleNamespace
        return SimpleNamespace(samples=np.zeros(512, dtype=np.float32), start=start)

    def test_cpu_path_shifts_times_and_reports_language(self):
        from types import SimpleNamespace
        from videotranslator.live_asr import PersistentWhisper
        constructed = []

        class Model:
            def __init__(self, name, device, compute_type):
                constructed.append((name, device, compute_type))

            def transcribe(self, audio, **kw):
                return iter([_FakeSeg(0.0, 1.0, "hello")]), _FakeInfo()

        pw = PersistentWhisper(device_policy="auto", whisper_model_cls=Model,
                               torch_module=SimpleNamespace(cuda=_FakeCuda(False)))
        self.assertEqual(pw.device, "cpu")
        segs, lang, prob = pw.transcribe(self._utt(10.0), language="en")
        self.assertEqual(segs[0]["start"], 10.0)
        self.assertEqual(lang, "en")
        self.assertAlmostEqual(prob, 0.92, places=3)

    def test_cuda_error_falls_back_to_cpu(self):
        from types import SimpleNamespace
        from videotranslator.live_asr import PersistentWhisper

        class Model:
            def __init__(self, name, device, compute_type):
                self.device = device

            def transcribe(self, audio, **kw):
                if self.device == "cuda":
                    raise RuntimeError("CUDA failure: libcublas")
                return iter([_FakeSeg(0.0, 1.0, "ok")]), _FakeInfo()

        pw = PersistentWhisper(device_policy="auto", whisper_model_cls=Model,
                               torch_module=SimpleNamespace(cuda=_FakeCuda(True)))
        self.assertEqual(pw.device, "cuda")
        segs, lang, _ = pw.transcribe(self._utt(0.0), language="en")
        self.assertTrue(pw.fell_back)
        self.assertEqual(pw.device, "cpu")
        self.assertEqual(segs[0]["text"], "ok")


@unittest.skipUnless(_HEAVY, "heavy smoke: set VTAI_RUN_HEAVY_SMOKE=1")
class LiveAsrHeavySmokeTests(unittest.TestCase):
    def _wav(self, path):
        import soundfile as sf
        sr = 16000
        t = np.linspace(0, 1, sr, endpoint=False)
        tone = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        audio = np.concatenate([tone, np.zeros(sr, dtype=np.float32)])
        sf.write(path, audio, sr)
        return audio

    def test_audio_decoder_yields_quarter_second_blocks(self):
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.wav")
            self._wav(path)
            dec = AudioDecoder(path, start_at=0.0, time_domain="rebased")
            blocks = list(dec.blocks(threading.Event()))
            dec.close()
            full = [b for (_t, b) in blocks if b.size == 4000]
            self.assertGreaterEqual(len(full), 7)          # ~2 s / 0.25 s
            times = [t for (t, _b) in blocks]
            self.assertAlmostEqual(times[0], 0.0, places=2)
            self.assertAlmostEqual(times[1] - times[0], 0.25, places=3)

    def test_audio_decoder_rejects_a_source_without_audio(self):
        closed = []

        class _Container:
            streams = type("S", (), {"audio": []})()

            def close(self):
                closed.append(True)

        class _Av:
            @staticmethod
            def open(source, format=None):
                return _Container()

            AudioResampler = staticmethod(lambda **k: object())

        with self.assertRaises(RuntimeError):
            AudioDecoder("x.m4s", av_module=_Av())
        self.assertEqual(closed, [True])       # the container is closed on the error

    def test_persistent_whisper_transcribes_real_speech(self):
        import asyncio
        import threading
        from types import SimpleNamespace
        import edge_tts
        from videotranslator.live_asr import PersistentWhisper
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = os.path.join(tmp, "speech.mp3")

            async def synth():
                await edge_tts.Communicate(
                    "This is a test of speech recognition.", "en-US-AriaNeural").save(mp3)

            asyncio.run(synth())
            dec = AudioDecoder(mp3, time_domain="rebased")
            samples = np.concatenate([b for (_t, b) in dec.blocks(threading.Event())])
            dec.close()
            utt = SimpleNamespace(samples=samples, start=0.0)
            pw = PersistentWhisper(device_policy="cpu")   # small int8, no big download
            segs, lang, prob = pw.transcribe(utt, language="en")
            pw.close()
            text = " ".join(s["text"] for s in segs).lower()
            self.assertEqual(lang, "en")
            self.assertTrue(any(w in text for w in ("test", "speech", "recognition")),
                            f"unexpected transcript: {text!r}")

    def test_streaming_vad_matches_silero(self):
        from faster_whisper.vad import get_vad_model
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.wav")
            audio = self._wav(path)
        n = (audio.shape[0] // 512) * 512
        reference = get_vad_model()(audio[:n].copy()).reshape(-1)
        vad = StreamingVad()
        streamed = []
        for i in range(0, n, 4000):
            streamed.extend(vad.probs(audio[i:i + 4000]))
        m = min(len(streamed), len(reference))
        self.assertGreater(m, 30)
        self.assertLess(float(np.max(np.abs(np.array(streamed[:m]) - reference[:m]))), 1e-3)


class DecoderTimeTests(unittest.TestCase):
    def test_rebased_subtracts_container_start(self):
        # container starts at 1001.378667 s (1001378667 us)
        t = decoder_time(0, 1.0, container_start_us=1001378667, domain="rebased")
        self.assertAlmostEqual(t, -1001.378667, places=6)

    def test_rebased_without_start(self):
        self.assertEqual(decoder_time(100, 0.01, container_start_us=None,
                                      domain="rebased"), 1.0)

    def test_raw_keeps_pts(self):
        self.assertAlmostEqual(
            decoder_time(90000, 1 / 90000, container_start_us=None, domain="raw"),
            1.0, places=6)


class HallucinationFilterTests(unittest.TestCase):
    def test_drops_no_speech_low_logprob(self):
        f = HallucinationFilter()
        segs = [{"text": "x", "no_speech_prob": 0.7, "avg_logprob": -1.5}]
        self.assertEqual(f.filter(segs), [])

    def test_keeps_confident_segment(self):
        f = HallucinationFilter()
        segs = [{"text": "hello", "no_speech_prob": 0.1, "avg_logprob": -0.2}]
        self.assertEqual(f.filter(segs), segs)

    def test_drops_high_compression_ratio(self):
        f = HallucinationFilter()
        self.assertEqual(f.filter([{"text": "la la la", "compression_ratio": 3.0}]), [])

    def test_drops_exact_repeats_of_last_two(self):
        f = HallucinationFilter()
        f.filter([{"text": "same"}])
        f.filter([{"text": "other"}])
        self.assertEqual(f.filter([{"text": "same"}]), [])   # still within last 2
        # a third distinct pushes "same" out of the window
        f.filter([{"text": "third"}])
        self.assertEqual(f.filter([{"text": "same"}]), [{"text": "same"}])


class LanguageLockTests(unittest.TestCase):
    def test_explicit_source_locked_from_start(self):
        lock = LanguageLock("it")
        self.assertEqual(lock.state, "locked")
        self.assertEqual(lock.locked, "it")

    def test_auto_fast_lock_on_confident_detection(self):
        lock = LanguageLock("auto")
        self.assertEqual(lock.observe("it", 0.9, 3.0), "detecting")  # < 5 s speech
        early = [{"start": 0.0, "end": 1.0, "text": "inizio", "flags": ()}]
        lock.buffer_segments(early)
        self.assertEqual(lock.take_buffered_segments(), [])
        self.assertEqual(lock.observe("it", 0.9, 3.0), "locked")     # 6 s, prob high
        self.assertEqual(lock.locked, "it")
        self.assertEqual(lock.take_buffered_segments(), early)
        self.assertEqual(lock.take_buffered_segments(), [])

    def test_prelock_buffer_can_be_discarded_on_seek(self):
        lock = LanguageLock("auto")
        lock.buffer_segments([{"text": "old generation"}])
        lock.clear_buffered_segments()
        lock.observe("it", 0.9, 6.0)
        self.assertEqual(lock.take_buffered_segments(), [])

    def test_auto_majority_vote_locks(self):
        lock = LanguageLock("auto", min_speech_lock_s=5.0, vote_window_s=10.0)
        # low prob so the fast path never triggers; reach the vote window
        for _ in range(4):
            lock.observe("it", 0.5, 3.0)   # 12 s of "it"
        self.assertEqual(lock.state, "locked")
        self.assertEqual(lock.locked, "it")

    def test_auto_fails_on_mixed_languages(self):
        # Vote and fail windows coincide so the vote is only taken once, on the
        # balanced 50/50 sample, which has no majority.
        lock = LanguageLock("auto", vote_window_s=12.0, fail_after_s=12.0)
        state = None
        for lang in ("it", "ja", "it", "ja"):
            state = lock.observe(lang, 0.5, 3.0)   # 12 s, 50/50 -> no majority
        self.assertEqual(state, "failed")
        self.assertIsNone(lock.locked)


if __name__ == "__main__":
    unittest.main()
