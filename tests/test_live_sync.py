import unittest

from videotranslator.live_sync import (
    FilePacer,
    derive_live_timing,
    live_distance_s,
    recommended_delay_s,
)


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


if __name__ == "__main__":
    unittest.main()
