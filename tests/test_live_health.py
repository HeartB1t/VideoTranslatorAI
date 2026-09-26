import unittest

from videotranslator.live_health import (
    CircuitBreaker,
    FaultRule,
    RollingStats,
    parse_fault_spec,
)


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class CircuitBreakerTests(unittest.TestCase):
    def _breaker(self, **kw):
        self.clock = _Clock()
        return CircuitBreaker(clock=self.clock, **kw)

    def test_closed_allows(self):
        b = self._breaker()
        self.assertTrue(b.allow())
        self.assertEqual(b.state, "closed")

    def test_opens_after_threshold_and_blocks(self):
        b = self._breaker(threshold=3)
        self.assertIsNone(b.record_failure(kind="error"))
        self.assertIsNone(b.record_failure(kind="error"))
        self.assertEqual(b.record_failure(kind="error"), "engine_slow")
        self.assertEqual(b.state, "open")
        self.assertFalse(b.allow())

    def test_rate_limited_warn_code(self):
        b = self._breaker(threshold=1)
        self.assertEqual(b.record_failure(kind="rate_limited"), "rate_limited")

    def test_warn_reported_once_per_episode(self):
        b = self._breaker(threshold=1, cooldown_s=1)
        self.assertEqual(b.record_failure(kind="rate_limited"), "rate_limited")
        # still open, another failure does not re-report
        self.assertIsNone(b.record_failure(kind="rate_limited"))
        # a success ends the episode; the next open reports again
        b.record_success()
        self.assertEqual(b.record_failure(kind="rate_limited"), "rate_limited")

    def test_half_open_probe_then_success_closes(self):
        b = self._breaker(threshold=1, cooldown_s=5)
        b.record_failure(kind="error")
        self.assertFalse(b.allow())
        self.clock.advance(5)
        self.assertTrue(b.allow())            # the one probe
        self.assertEqual(b.state, "half_open")
        self.assertFalse(b.allow())           # no second probe
        b.record_success()
        self.assertEqual(b.state, "closed")
        self.assertTrue(b.allow())

    def test_reopen_doubles_cooldown(self):
        b = self._breaker(threshold=1, cooldown_s=1, max_cooldown_s=100)
        b.record_failure(kind="error")
        self.assertAlmostEqual(b.retry_in_s(), 1.0, places=3)
        self.clock.advance(1)
        b.allow()                              # half-open probe
        b.record_failure(kind="error")         # probe fails -> reopen
        self.assertAlmostEqual(b.retry_in_s(), 2.0, places=3)
        self.clock.advance(2)
        b.allow()
        b.record_failure(kind="error")
        self.assertAlmostEqual(b.retry_in_s(), 4.0, places=3)

    def test_cooldown_capped(self):
        b = self._breaker(threshold=1, cooldown_s=100, max_cooldown_s=150)
        b.record_failure(kind="error")         # 100
        self.clock.advance(100)
        b.allow()
        b.record_failure(kind="error")         # min(200, 150) = 150
        self.assertAlmostEqual(b.retry_in_s(), 150.0, places=3)

    def test_quota_opens_permanently(self):
        b = self._breaker()
        self.assertEqual(b.record_failure(kind="quota"), "quota")
        self.assertEqual(b.state, "open")
        self.clock.advance(10_000)
        self.assertFalse(b.allow())
        self.assertEqual(b.retry_in_s(), float("inf"))

    def test_failures_outside_window_do_not_accumulate(self):
        b = self._breaker(threshold=3, window_s=10)
        b.record_failure(kind="error")         # t=0
        b.record_failure(kind="error")         # t=0
        self.clock.advance(12)
        self.assertIsNone(b.record_failure(kind="error"))  # only 1 in window
        self.assertEqual(b.state, "closed")


class RollingStatsTests(unittest.TestCase):
    def test_empty_returns_none(self):
        s = RollingStats()
        self.assertIsNone(s.p50())
        self.assertIsNone(s.p90())
        self.assertEqual(s.count(), 0)

    def test_percentiles(self):
        s = RollingStats()
        for x in range(1, 11):             # 1..10
            s.add(x)
        self.assertEqual(s.count(), 10)
        self.assertEqual(s.p50(), 5)
        self.assertEqual(s.p90(), 9)
        self.assertEqual(s.p95(), 10)

    def test_window_cap(self):
        s = RollingStats(window=32)
        for x in range(100):
            s.add(x)
        self.assertEqual(s.count(), 32)
        self.assertEqual(s.p50(), 83)      # last 32 are 68..99, median-ish


class ParseFaultSpecTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(parse_fault_spec(""), {})
        self.assertEqual(parse_fault_spec("   "), {})

    def test_count_and_at_forms(self):
        rules = parse_fault_spec("mt_429:3,cuda_oom@60,tts_fail:2,ingest_stall@120")
        self.assertEqual(rules["mt_429"], FaultRule("mt_429", 3, None))
        self.assertEqual(rules["cuda_oom"], FaultRule("cuda_oom", None, 60.0))
        self.assertEqual(rules["tts_fail"], FaultRule("tts_fail", 2, None))
        self.assertEqual(rules["ingest_stall"], FaultRule("ingest_stall", None, 120.0))

    def test_bare_name_and_whitespace(self):
        rules = parse_fault_spec(" mt_429 , cuda_oom@5 ")
        self.assertEqual(rules["mt_429"], FaultRule("mt_429", None, None))
        self.assertEqual(rules["cuda_oom"], FaultRule("cuda_oom", None, 5.0))


if __name__ == "__main__":
    unittest.main()
