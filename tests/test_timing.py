import unittest

from videotranslator.timing import (
    compute_segment_speed,
    estimate_tts_duration_s,
    suggest_xtts_speed,
)


class TimingTests(unittest.TestCase):
    def test_suggest_speed_for_expanding_language_pair(self):
        speed, ratio, auto = suggest_xtts_speed("en", "it")

        self.assertTrue(auto)
        self.assertAlmostEqual(ratio, 1.25)
        self.assertEqual(speed, 1.35)

    def test_user_override_is_respected(self):
        speed, _ratio, auto = suggest_xtts_speed("en", "it", user_override=1.12)

        self.assertFalse(auto)
        self.assertEqual(speed, 1.12)

    def test_zh_cn_lookup_is_not_default_european_rate(self):
        self.assertGreater(
            estimate_tts_duration_s("1234567890123456", "zh-cn"),
            estimate_tts_duration_s("1234567890123456", "en"),
        )

    def test_segment_speed_is_capped(self):
        speed = compute_segment_speed("x" * 200, slot_s=1.0, lang_target="en")

        self.assertEqual(speed, 1.40)


if __name__ == "__main__":
    unittest.main()

