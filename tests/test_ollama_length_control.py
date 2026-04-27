import unittest

from videotranslator.ollama_length_control import (
    build_rewrite_shorter_prompt,
    compute_target_chars,
    should_reprompt_for_length,
)


class ComputeTargetCharsTests(unittest.TestCase):
    def test_typical_en_to_it(self):
        # 100 src chars * 1.25 expansion * 1.20 slack = 150
        self.assertEqual(compute_target_chars(100, 1.25, 1.20), 150)

    def test_neutral_expansion_no_slack(self):
        # 100 src chars * 1.0 * 1.0 = 100, but the floor is 50 so >= 50
        self.assertEqual(compute_target_chars(100, 1.0, 1.0), 100)

    def test_floor_for_short_input(self):
        self.assertEqual(compute_target_chars(10, 1.25, 1.20), 50)

    def test_floor_for_zero_input(self):
        self.assertEqual(compute_target_chars(0, 1.25, 1.20), 50)

    def test_floor_for_invalid_args(self):
        self.assertEqual(compute_target_chars(100, 0, 1.20), 50)
        self.assertEqual(compute_target_chars(100, 1.25, 0), 50)
        self.assertEqual(compute_target_chars(-5, 1.25, 1.20), 50)


class ShouldReprompForLengthTests(unittest.TestCase):
    def test_under_threshold(self):
        # 100 chars vs 100 target with 1.10 threshold = 110 effective limit
        self.assertFalse(should_reprompt_for_length(100, 100, threshold=1.10))
        self.assertFalse(should_reprompt_for_length(110, 100, threshold=1.10))

    def test_over_threshold(self):
        self.assertTrue(should_reprompt_for_length(111, 100, threshold=1.10))
        self.assertTrue(should_reprompt_for_length(200, 100, threshold=1.10))

    def test_invalid_target_returns_false(self):
        # Without a sensible target we cannot decide, so do nothing.
        self.assertFalse(should_reprompt_for_length(100, 0))
        self.assertFalse(should_reprompt_for_length(100, -1))

    def test_invalid_threshold_returns_false(self):
        self.assertFalse(should_reprompt_for_length(100, 100, threshold=0))
        self.assertFalse(should_reprompt_for_length(100, 100, threshold=-1))

    def test_zero_translation_never_triggers(self):
        # An empty translation has its own retry path (handled elsewhere);
        # the length controller should not piggyback on it.
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
        # /no_think is a Qwen3-specific instruction, never send to other models.
        p = build_rewrite_shorter_prompt(
            "x", 3.0, 80, "Italian", is_qwen3=False, thinking=False
        )
        self.assertNotIn("/no_think", p)

    def test_output_only_instruction_present(self):
        # Critical: without this, the model often returns "Sure, here's a shorter
        # version: ..." which the strip_preamble has to clean up.
        p = build_rewrite_shorter_prompt("x", 3.0, 80, "Italian")
        self.assertIn("Output ONLY", p)


if __name__ == "__main__":
    unittest.main()
