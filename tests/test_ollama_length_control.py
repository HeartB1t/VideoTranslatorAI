import unittest

from videotranslator.ollama_length_control import (
    DEFAULT_CHARS_PER_SECOND,
    build_rewrite_shorter_prompt,
    chars_per_second_for,
    compute_target_chars,
    should_reprompt_for_length,
)


class CharsPerSecondTests(unittest.TestCase):
    def test_known_language(self):
        self.assertEqual(chars_per_second_for("it"), 15.0)
        self.assertEqual(chars_per_second_for("en"), 14.0)
        self.assertEqual(chars_per_second_for("zh"), 6.0)

    def test_locale_style_strips_region(self):
        self.assertEqual(chars_per_second_for("it-IT"), 15.0)
        self.assertEqual(chars_per_second_for("EN-US"), 14.0)

    def test_unknown_language_uses_default(self):
        self.assertEqual(chars_per_second_for("xx"), DEFAULT_CHARS_PER_SECOND)

    def test_empty_or_none_uses_default(self):
        self.assertEqual(chars_per_second_for(""), DEFAULT_CHARS_PER_SECOND)
        self.assertEqual(chars_per_second_for(None), DEFAULT_CHARS_PER_SECOND)


class ComputeTargetCharsTests(unittest.TestCase):
    def test_typical_italian_4s_slot(self):
        # 4s × 15 chars/s × 1.10 slack = 66
        self.assertEqual(compute_target_chars(4.0, "it"), 66)

    def test_typical_english_5s_slot(self):
        # 5s × 14 × 1.10 = 77
        self.assertEqual(compute_target_chars(5.0, "en"), 77)

    def test_logographic_script_lower_budget(self):
        # 4s × 6 × 1.10 = 26 → floor 50
        self.assertEqual(compute_target_chars(4.0, "zh"), 50)

    def test_long_slot_gets_proportional_budget(self):
        # 10s × 15 × 1.10 = 165
        self.assertEqual(compute_target_chars(10.0, "it"), 165)

    def test_floor_for_short_slot(self):
        # 0.5s × 15 × 1.10 = 8 → floor 50
        self.assertEqual(compute_target_chars(0.5, "it"), 50)

    def test_floor_for_zero_slot(self):
        self.assertEqual(compute_target_chars(0.0, "it"), 50)

    def test_floor_for_invalid_slack(self):
        self.assertEqual(compute_target_chars(4.0, "it", slack=0), 50)
        self.assertEqual(compute_target_chars(4.0, "it", slack=-1), 50)

    def test_unknown_language_falls_back_to_default(self):
        # 4s × 14 × 1.10 = 61
        self.assertEqual(compute_target_chars(4.0, "xx"), 61)

    def test_regression_dense_segment_now_triggers(self):
        # The 2026-04-28 production case that motivated the slot-based
        # rewrite: slot 4.02s, src 113 EN chars, IT translation 94 chars.
        # The old proportional formula gave target=169 → no re-prompt.
        # The new slot-based formula gives target=66 → 94 > 66 × 1.10 = 73
        # → re-prompt fires, as required.
        target = compute_target_chars(4.02, "it")
        self.assertLess(target, 94)  # critical: budget < actual translation
        self.assertTrue(should_reprompt_for_length(94, target))


class ShouldReprompForLengthTests(unittest.TestCase):
    def test_under_threshold(self):
        self.assertFalse(should_reprompt_for_length(100, 100, threshold=1.10))
        self.assertFalse(should_reprompt_for_length(110, 100, threshold=1.10))

    def test_over_threshold(self):
        self.assertTrue(should_reprompt_for_length(111, 100, threshold=1.10))
        self.assertTrue(should_reprompt_for_length(200, 100, threshold=1.10))

    def test_invalid_target_returns_false(self):
        self.assertFalse(should_reprompt_for_length(100, 0))
        self.assertFalse(should_reprompt_for_length(100, -1))

    def test_invalid_threshold_returns_false(self):
        self.assertFalse(should_reprompt_for_length(100, 100, threshold=0))
        self.assertFalse(should_reprompt_for_length(100, 100, threshold=-1))

    def test_zero_translation_never_triggers(self):
        self.assertFalse(should_reprompt_for_length(0, 100, threshold=1.10))


class BuildRewriteShorterPromptTests(unittest.TestCase):
    def test_includes_numeric_budget(self):
        p = build_rewrite_shorter_prompt("Lorem ipsum", 3.0, 80, "Italian")
        self.assertIn("80 characters", p)

    def test_includes_slot_duration(self):
        p = build_rewrite_shorter_prompt("Lorem ipsum", 3.5, 80, "Italian")
        self.assertIn("3.5 seconds", p)

    def test_includes_target_language_name(self):
        p = build_rewrite_shorter_prompt("Lorem ipsum", 3.0, 80, "Italian")
        self.assertIn("Italian", p)

    def test_includes_previous_translation(self):
        p = build_rewrite_shorter_prompt("Lorem ipsum dolor", 3.0, 80, "Italian")
        self.assertIn("Lorem ipsum dolor", p)

    def test_includes_previous_translation_length(self):
        prev = "Lorem ipsum dolor"
        p = build_rewrite_shorter_prompt(prev, 3.0, 80, "Italian")
        self.assertIn(f"({len(prev)} chars)", p)

    def test_qwen3_no_think_appends_suffix(self):
        p = build_rewrite_shorter_prompt(
            "x", 3.0, 80, "Italian", is_qwen3=True, thinking=False
        )
        self.assertTrue(p.rstrip().endswith("/no_think"))

    def test_qwen3_thinking_omits_suffix(self):
        p = build_rewrite_shorter_prompt(
            "x", 3.0, 80, "Italian", is_qwen3=True, thinking=True
        )
        self.assertNotIn("/no_think", p)

    def test_non_qwen3_omits_suffix(self):
        p = build_rewrite_shorter_prompt(
            "x", 3.0, 80, "Italian", is_qwen3=False, thinking=False
        )
        self.assertNotIn("/no_think", p)

    def test_output_only_instruction_present(self):
        p = build_rewrite_shorter_prompt("x", 3.0, 80, "Italian")
        self.assertIn("Output ONLY", p)


if __name__ == "__main__":
    unittest.main()
