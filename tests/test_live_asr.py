import unittest

from videotranslator.live_asr import HallucinationFilter, LanguageLock, decoder_time


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
        self.assertEqual(lock.observe("it", 0.9, 3.0), "locked")     # 6 s, prob high
        self.assertEqual(lock.locked, "it")

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
