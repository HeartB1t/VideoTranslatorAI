import unittest

from videotranslator.difficulty_detector import (
    EASY_THRESHOLD,
    HARD_THRESHOLD,
    classify_difficulty,
    estimate_p90_ratio,
    estimate_segment_ratio,
    format_difficulty_log,
    tts_speed_factor_for,
)


class EstimateSegmentRatioTests(unittest.TestCase):
    def test_zero_slot_returns_zero(self):
        self.assertEqual(estimate_segment_ratio(60, 0.0, "it"), 0.0)
        self.assertEqual(estimate_segment_ratio(60, -1.0, "it"), 0.0)

    def test_zero_chars_returns_zero(self):
        self.assertEqual(estimate_segment_ratio(0, 4.0, "it"), 0.0)

    def test_basic_italian_unit_ratio(self):
        # Italian cps = 15. 60 chars in 4s slot = 60/(4*15) = 1.0
        self.assertAlmostEqual(estimate_segment_ratio(60, 4.0, "it"), 1.0)

    def test_dense_source_above_unit(self):
        # 90 chars in 4s italian = 90/(60) = 1.5
        self.assertAlmostEqual(estimate_segment_ratio(90, 4.0, "it"), 1.5)

    def test_with_expansion_factor_en_to_it(self):
        # 100 EN chars × 1.25 expansion / (5s × 15 cps) = 125/75 = 1.6667
        self.assertAlmostEqual(
            estimate_segment_ratio(100, 5.0, "it", 1.25), 1.6667, places=4
        )

    def test_logographic_lang_lower_cps_higher_ratio(self):
        # zh cps = 6. 60 chars in 4s = 60/(4*6) = 2.5
        self.assertAlmostEqual(estimate_segment_ratio(60, 4.0, "zh"), 2.5)

    def test_unknown_lang_falls_back_to_default_cps(self):
        # default cps = 14. 56 chars in 4s = 56/(4*14) = 1.0
        self.assertAlmostEqual(estimate_segment_ratio(56, 4.0, "xx"), 1.0)

    def test_locale_form_strips_region(self):
        self.assertAlmostEqual(
            estimate_segment_ratio(60, 4.0, "it-IT"),
            estimate_segment_ratio(60, 4.0, "it"),
        )

    def test_tts_speed_factor_compresses_predicted_ratio(self):
        # Italian cps=15. 90 chars in 4s = base ratio 1.5
        base = estimate_segment_ratio(90, 4.0, "it")
        with_speed = estimate_segment_ratio(90, 4.0, "it", tts_speed_factor=1.5)
        self.assertAlmostEqual(base, 1.5)
        self.assertAlmostEqual(with_speed, 1.0)

    def test_tts_speed_factor_default_neutral(self):
        # Default 1.0 must yield identical numbers to the un-parameterized call
        explicit = estimate_segment_ratio(90, 4.0, "it", tts_speed_factor=1.0)
        implicit = estimate_segment_ratio(90, 4.0, "it")
        self.assertEqual(explicit, implicit)

    def test_tts_speed_factor_invalid_returns_zero(self):
        self.assertEqual(estimate_segment_ratio(60, 4.0, "it", tts_speed_factor=0), 0.0)
        self.assertEqual(estimate_segment_ratio(60, 4.0, "it", tts_speed_factor=-1.5), 0.0)

    def test_tts_speed_factor_for_known_lang(self):
        # Italian has a calibrated empirical value
        self.assertAlmostEqual(tts_speed_factor_for("it"), 1.15)

    def test_tts_speed_factor_for_logographic(self):
        # zh/ja/ko share lower empirical compression
        self.assertAlmostEqual(tts_speed_factor_for("zh"), 1.05)
        self.assertAlmostEqual(tts_speed_factor_for("ja"), 1.05)
        self.assertAlmostEqual(tts_speed_factor_for("ko"), 1.05)

    def test_tts_speed_factor_for_unknown_lang_falls_back(self):
        # Default 1.10 for any language not in the table
        self.assertAlmostEqual(tts_speed_factor_for("xx"), 1.10)
        self.assertAlmostEqual(tts_speed_factor_for(""), 1.10)
        self.assertAlmostEqual(tts_speed_factor_for(None), 1.10)

    def test_tts_speed_factor_for_locale_form(self):
        # it-IT must resolve to the it entry, not fall back to default
        self.assertAlmostEqual(tts_speed_factor_for("it-IT"), 1.15)
        self.assertAlmostEqual(tts_speed_factor_for("EN-US"), 1.10)

    def test_tts_speed_factor_realistic_xtts_cap(self):
        # Empirical: XTTS adaptive cap 1.35 brings the Fitzgerald comedy
        # P90 from ~2.43 (observed) towards ~1.80 (calibrated estimate),
        # closing the over-pessimism gap reported by the smoke test.
        # Single-segment proxy: 90 chars in 4s with EN->IT expansion 1.25
        # at TTS speed 1.35:
        # base = 90 * 1.25 / (4 * 15) = 1.875
        # with cap = 1.875 / 1.35 = 1.389
        out = estimate_segment_ratio(90, 4.0, "it", expansion_factor=1.25,
                                     tts_speed_factor=1.35)
        self.assertAlmostEqual(out, 1.389, places=2)


class EstimateP90RatioTests(unittest.TestCase):
    def _seg(self, text: str, start: float, end: float) -> dict:
        return {"text": text, "start": start, "end": end}

    def test_empty_input_returns_zero(self):
        self.assertEqual(estimate_p90_ratio([], "it"), 0.0)

    def test_uniform_segments(self):
        # 10 segments all at ratio 1.0
        segs = [self._seg("x" * 60, 0, 4) for _ in range(10)]
        self.assertAlmostEqual(estimate_p90_ratio(segs, "it"), 1.0)

    def test_one_outlier_in_ten_segments(self):
        # 9 segments at ratio 1.0, 1 at ratio 2.0
        # Sorted: 9 * 1.0 + 1 * 2.0
        # P90 idx = max(0, min(9, round(0.9*10)-1)) = 8 -> ratios[8] = 1.0
        segs = [self._seg("x" * 60, 0, 4) for _ in range(9)]
        segs.append(self._seg("x" * 120, 0, 4))
        self.assertAlmostEqual(estimate_p90_ratio(segs, "it"), 1.0)

    def test_two_outliers_in_ten_lift_p90(self):
        # 8 at 1.0, 2 at 2.0 -> P90 = 2.0 (top 20%)
        segs = [self._seg("x" * 60, 0, 4) for _ in range(8)]
        segs += [self._seg("x" * 120, 0, 4) for _ in range(2)]
        self.assertAlmostEqual(estimate_p90_ratio(segs, "it"), 2.0)

    def test_uses_text_src_when_present(self):
        # If text_src exists, it wins over text. Mismatch lengths to verify.
        seg = {"text_src": "x" * 60, "text": "ignored " * 50, "start": 0, "end": 4}
        self.assertAlmostEqual(estimate_p90_ratio([seg], "it"), 1.0)

    def test_zero_slot_segment_contributes_zero(self):
        # 1 dense segment with zero slot: ratio 0, P90 = 0
        seg = self._seg("x" * 200, 5.0, 5.0)
        self.assertEqual(estimate_p90_ratio([seg], "it"), 0.0)

    def test_realistic_matt_cutts_distribution(self):
        # Approximate the Matt Cutts video: 30 segments, mostly fluent
        # (ratio ~1.0-1.3), a few outliers around 1.5-1.7.
        segs = [self._seg("x" * 60, 0, 4) for _ in range(20)]  # ratio 1.0
        segs += [self._seg("x" * 90, 0, 4) for _ in range(7)]  # ratio 1.5
        segs += [self._seg("x" * 102, 0, 4) for _ in range(3)]  # ratio 1.7
        p90 = estimate_p90_ratio(segs, "it")
        # P90 idx = max(0, min(29, 26)) = 26 -> ratios[26] is in the 1.5-1.7 group
        self.assertGreater(p90, 1.4)
        self.assertLess(p90, 1.8)


class ClassifyDifficultyTests(unittest.TestCase):
    def test_easy_at_or_below_threshold(self):
        self.assertEqual(classify_difficulty(1.0), "easy")
        self.assertEqual(classify_difficulty(EASY_THRESHOLD), "easy")

    def test_medium_just_above_easy(self):
        self.assertEqual(classify_difficulty(EASY_THRESHOLD + 0.01), "medium")
        self.assertEqual(classify_difficulty(HARD_THRESHOLD), "medium")

    def test_hard_above_hard_threshold(self):
        self.assertEqual(classify_difficulty(HARD_THRESHOLD + 0.01), "hard")
        self.assertEqual(classify_difficulty(2.43), "hard")

    def test_custom_thresholds(self):
        self.assertEqual(
            classify_difficulty(1.5, easy_threshold=2.0, hard_threshold=3.0),
            "easy",
        )


class FormatDifficultyLogTests(unittest.TestCase):
    def test_easy_message_mentions_fluent(self):
        msg = format_difficulty_log(1.0, "easy", "it")
        self.assertIn("1.00", msg)
        self.assertIn("fluent", msg.lower())

    def test_medium_message_mentions_some(self):
        msg = format_difficulty_log(1.5, "medium", "it")
        self.assertIn("1.50", msg)
        self.assertIn("some", msg.lower())

    def test_hard_message_mentions_most(self):
        msg = format_difficulty_log(2.43, "hard", "it")
        self.assertIn("2.43", msg)
        self.assertIn("most", msg.lower())

    def test_lang_code_uppercased_and_region_stripped(self):
        msg = format_difficulty_log(1.0, "easy", "it-IT")
        self.assertIn("IT", msg)

    def test_empty_lang_code_falls_back(self):
        msg = format_difficulty_log(1.0, "easy", "")
        # Just verify it does not crash and contains a placeholder
        self.assertTrue(len(msg) > 0)


if __name__ == "__main__":
    unittest.main()
