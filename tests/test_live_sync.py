import unittest

from videotranslator.live_sync import (
    DelayController,
    EdgeEstimate,
    EdgeEstimator,
    FilePacer,
    derive_live_timing,
    live_distance_s,
    recommended_delay_s,
)


def _edge(effective, *, max_gap=5.0):
    return EdgeEstimate(effective, effective, effective, False, max_gap)


class TimingHelperTests(unittest.TestCase):
    def test_recommended_delay(self):
        self.assertEqual(recommended_delay_s(device="cuda", dub=True), 12.0)
        self.assertEqual(recommended_delay_s(device="cuda", dub=False), 9.0)
        self.assertEqual(recommended_delay_s(device="cpu", dub=True), 15.0)
        self.assertEqual(recommended_delay_s(device="cpu", dub=False), 11.0)

    def test_live_distance_clamped(self):
        self.assertEqual(live_distance_s(0.5), 2.0)   # 0.75 -> min 2
        self.assertEqual(live_distance_s(3.0), 4.5)   # 4.5 inside band
        self.assertEqual(live_distance_s(10.0), 8.0)  # 15 -> max 8

    def test_derive_delayed_umax_matches_budget(self):
        self.assertAlmostEqual(
            derive_live_timing(12, mode="delayed", device="cuda", engine="marian",
                               dub=True).umax_s, 7.15, places=2)
        self.assertAlmostEqual(
            derive_live_timing(12, mode="delayed", device="cuda", engine="ollama",
                               dub=True).umax_s, 6.55, places=2)
        self.assertAlmostEqual(
            derive_live_timing(15, mode="delayed", device="cpu", engine="marian",
                               dub=True).umax_s, 8.0, places=2)   # clamped
        self.assertAlmostEqual(
            derive_live_timing(9, mode="delayed", device="cuda", engine="marian",
                               dub=False).umax_s, 5.65, places=2)

    def test_derive_live_and_holds(self):
        live = derive_live_timing(12, mode="live", device="cuda", engine="marian",
                                  dub=True)
        self.assertEqual(live.umax_s, 5.0)
        self.assertEqual(live.hold_s, 0.4)
        delayed = derive_live_timing(12, mode="delayed", device="cuda",
                                     engine="marian", dub=True)
        self.assertEqual(delayed.hold_s, 1.5)

    def test_derive_min_ahead_depends_on_dub(self):
        self.assertEqual(derive_live_timing(12, mode="delayed", device="cuda",
                                            engine="marian", dub=True).min_ahead_s, 8.0)
        self.assertEqual(derive_live_timing(9, mode="delayed", device="cuda",
                                            engine="marian", dub=False).min_ahead_s, 4.0)


class FilePacerDelayedTests(unittest.TestCase):
    def _pacer(self):
        return FilePacer(mode="delayed", min_ahead_s=8.0, resume_ahead_s=8.0)

    def test_pauses_when_coverage_nearly_caught_up(self):
        act = self._pacer().step(player=10.0, ready_until=11.5, source_done=False,
                                 user_paused=False, self_paused=False)
        self.assertEqual(act.kind, "pause")

    def test_does_not_pause_with_enough_coverage(self):
        act = self._pacer().step(player=10.0, ready_until=20.0, source_done=False,
                                 user_paused=False, self_paused=False)
        self.assertEqual(act.kind, "none")

    def test_resumes_at_min_ahead(self):
        act = self._pacer().step(player=10.0, ready_until=18.0, source_done=False,
                                 user_paused=False, self_paused=True)
        self.assertEqual(act.kind, "resume")

    def test_stays_paused_below_min_ahead(self):
        act = self._pacer().step(player=10.0, ready_until=13.0, source_done=False,
                                 user_paused=False, self_paused=True)
        self.assertEqual(act.kind, "none")

    def test_source_done_resumes(self):
        act = self._pacer().step(player=10.0, ready_until=10.1, source_done=True,
                                 user_paused=False, self_paused=True)
        self.assertEqual(act.kind, "resume")

    def test_user_pause_is_respected(self):
        act = self._pacer().step(player=10.0, ready_until=11.0, source_done=False,
                                 user_paused=True, self_paused=False)
        self.assertEqual(act.kind, "none")

    def test_unknown_position_does_nothing(self):
        act = self._pacer().step(player=None, ready_until=11.0, source_done=False,
                                 user_paused=False, self_paused=False)
        self.assertEqual(act.kind, "none")


class FilePacerLiveTests(unittest.TestCase):
    def test_live_never_pauses(self):
        pacer = FilePacer(mode="live", min_ahead_s=8.0, resume_ahead_s=8.0)
        act = pacer.step(player=10.0, ready_until=10.1, source_done=False,
                         user_paused=False, self_paused=False)
        self.assertEqual(act.kind, "none")

    def test_live_lifts_a_leftover_pause(self):
        pacer = FilePacer(mode="live", min_ahead_s=8.0, resume_ahead_s=8.0)
        act = pacer.step(player=10.0, ready_until=10.1, source_done=False,
                         user_paused=False, self_paused=True)
        self.assertEqual(act.kind, "resume")


class EdgeEstimatorTests(unittest.TestCase):
    def test_default_gap_before_min_gaps(self):
        est = EdgeEstimator()
        est.observe(0.0, 0.0)
        est.observe(0.2, 0.2)
        self.assertEqual(est.estimate(0.3).max_gap_s, 6.0)

    def test_max_gap_from_bursts(self):
        est = EdgeEstimator(warmup_s=0.0, min_gaps=3)
        for i in range(6):
            m = i * 5.0
            est.observe(m + 2.0, m)      # edge leads the wall clock by 2 s
        e = est.estimate(27.0)
        self.assertEqual(e.max_gap_s, 5.0)
        self.assertAlmostEqual(e.linear, 29.0, places=6)   # 27 + offset 2
        self.assertFalse(e.stalled)

    def test_stall_freezes_effective_to_observed(self):
        est = EdgeEstimator(warmup_s=0.0, min_gaps=1)
        est.observe(2.0, 0.0)
        est.observe(7.0, 5.0)            # gap 5
        e = est.estimate(40.0)           # 35 s idle > 2 * 5
        self.assertTrue(e.stalled)
        self.assertEqual(e.effective, e.observed)

    def test_reset_clears(self):
        est = EdgeEstimator()
        est.observe(1.0, 1.0)
        est.reset(2.0)
        self.assertIsNone(est.estimate(3.0).observed)


class DelayControllerTests(unittest.TestCase):
    def _ctrl(self, mode="delayed", delay=12.0):
        return DelayController(mode=mode, delay_s=delay)

    def test_center_holds_speed_one(self):
        act = self._ctrl().step(mono=0.0, edge=_edge(112.0), player=100.0,
                                user_paused=False, paused_for_cache=False,
                                self_paused=False, cache_end=None)
        self.assertEqual((act.kind, act.value), ("speed", 1.0))

    def test_small_error_nudges_speed(self):
        act = self._ctrl().step(mono=0.0, edge=_edge(114.0), player=100.0,
                                user_paused=False, paused_for_cache=False,
                                self_paused=False, cache_end=None)
        self.assertEqual(act.kind, "speed")
        self.assertAlmostEqual(act.value, 1.02, places=6)

    def test_far_ahead_seeks_when_cache_covers_target(self):
        act = self._ctrl().step(mono=0.0, edge=_edge(120.0), player=100.0,
                                user_paused=False, paused_for_cache=False,
                                self_paused=False, cache_end=120.0)
        self.assertEqual((act.kind, act.value), ("seek", 108.0))

    def test_far_ahead_reloads_when_cache_short(self):
        act = self._ctrl().step(mono=0.0, edge=_edge(120.0), player=100.0,
                                user_paused=False, paused_for_cache=False,
                                self_paused=False, cache_end=105.0)
        self.assertEqual((act.kind, act.value), ("reload", 108.0))

    def test_too_far_behind_pauses(self):
        act = self._ctrl().step(mono=0.0, edge=_edge(105.0), player=100.0,
                                user_paused=False, paused_for_cache=False,
                                self_paused=False, cache_end=None)
        self.assertEqual(act.kind, "pause")

    def test_self_paused_resumes_near_target(self):
        ctrl = self._ctrl()
        act = ctrl.step(mono=0.0, edge=_edge(111.7), player=100.0, user_paused=False,
                        paused_for_cache=False, self_paused=True, cache_end=None)
        self.assertEqual(act.kind, "resume")

    def test_user_paused_is_none(self):
        act = self._ctrl().step(mono=0.0, edge=_edge(120.0), player=100.0,
                                user_paused=True, paused_for_cache=False,
                                self_paused=False, cache_end=None)
        self.assertEqual(act.kind, "none")

    def test_live_mode_seeks_when_too_far(self):
        ctrl = self._ctrl(mode="live")
        act = ctrl.step(mono=0.0, edge=_edge(120.0, max_gap=5.0), player=100.0,
                        user_paused=False, paused_for_cache=False,
                        self_paused=False, cache_end=None)
        self.assertEqual(act.kind, "seek")
        self.assertAlmostEqual(act.value, 112.5, places=6)   # 120 - clamp(7.5,2,8)

    def test_target_lag(self):
        self.assertEqual(self._ctrl().target_lag(_edge(100.0)), 12.0)
        self.assertEqual(self._ctrl(mode="live").target_lag(_edge(100.0, max_gap=5.0)), 7.5)

    def test_hysteresis_holds_repeat_actions(self):
        ctrl = self._ctrl()
        first = ctrl.step(mono=0.0, edge=_edge(114.0), player=100.0, user_paused=False,
                          paused_for_cache=False, self_paused=False, cache_end=None)
        self.assertEqual(first.kind, "speed")
        held = ctrl.step(mono=1.0, edge=_edge(114.0), player=100.0, user_paused=False,
                         paused_for_cache=False, self_paused=False, cache_end=None)
        self.assertEqual(held.kind, "none")           # same band, within hold
        again = ctrl.step(mono=3.0, edge=_edge(114.0), player=100.0, user_paused=False,
                          paused_for_cache=False, self_paused=False, cache_end=None)
        self.assertEqual(again.kind, "speed")         # hold elapsed

    def test_resume_action(self):
        ctrl = self._ctrl()
        self.assertEqual(ctrl.resume_action(edge=_edge(114.0), player=100.0,
                                            cache_end=None).kind, "none")
        far = ctrl.resume_action(edge=_edge(130.0), player=100.0, cache_end=130.0)
        self.assertEqual((far.kind, far.value), ("seek", 118.0))

    def test_set_mode_to_live_seeks(self):
        ctrl = self._ctrl()
        act = ctrl.set_mode("live", mono=0.0, edge=_edge(120.0, max_gap=5.0),
                            player=100.0, cache_end=None)
        self.assertEqual((act.kind, act.value), ("seek", 112.5))


if __name__ == "__main__":
    unittest.main()
