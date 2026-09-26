import unittest

from videotranslator.live_tts import (
    Clip,
    EdgeDurationModel,
    choose_rate,
    mp3_cbr_duration_s,
)


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


if __name__ == "__main__":
    unittest.main()
