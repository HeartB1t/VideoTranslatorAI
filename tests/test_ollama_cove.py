"""Unit tests for videotranslator.ollama_cove (TASK 2U).

Chain-of-Verification is a pure-text contract: detect risky source
patterns, build a verification prompt for the same model, parse the
single-line response. No Ollama daemon involved here — all I/O lives
in ``_translate_with_ollama`` and is exercised by the integration
smoke tests.
"""

import unittest

from videotranslator.ollama_cove import (
    build_verification_prompt,
    needs_verification,
    parse_verification_response,
)


class NeedsVerificationTests(unittest.TestCase):
    def test_empty_input_returns_false(self):
        needs, reasons = needs_verification("")
        self.assertFalse(needs)
        self.assertEqual(reasons, [])

    def test_whitespace_only_returns_false(self):
        needs, reasons = needs_verification("   \t\n  ")
        self.assertFalse(needs)
        self.assertEqual(reasons, [])

    def test_plain_positive_sentence_no_trigger(self):
        # "I am happy." has no negation, no quantifier — the Ollama
        # call cost is wasted on this segment, so we skip it.
        needs, reasons = needs_verification("I am happy.")
        self.assertFalse(needs)
        self.assertEqual(reasons, [])

    def test_negation_haven_t_triggers(self):
        # The exact bug pattern from the 2026-04-29 Pen-Testing video:
        # "if you haven't seen this" → qwen3 dropped the negation.
        needs, reasons = needs_verification("if you haven't seen this video")
        self.assertTrue(needs)
        self.assertIn("negation", reasons)

    def test_negation_never_triggers(self):
        needs, reasons = needs_verification("I never said that.")
        self.assertTrue(needs)
        self.assertIn("negation", reasons)

    def test_negation_italian_non_triggers(self):
        # IT→EN reverse direction must also trigger.
        needs, reasons = needs_verification("non l'ho mai visto")
        self.assertTrue(needs)
        self.assertIn("negation", reasons)

    def test_quantifier_all_triggers(self):
        needs, reasons = needs_verification("all of them are here")
        self.assertTrue(needs)
        self.assertIn("quantifier", reasons)

    def test_quantifier_every_triggers(self):
        needs, reasons = needs_verification("every single one matters")
        self.assertTrue(needs)
        self.assertIn("quantifier", reasons)

    def test_negation_and_quantifier_both_triggered(self):
        # Both reasons must appear in order so the prompt builder can
        # emit the right pair of yes/no questions.
        needs, reasons = needs_verification("I never saw all of them")
        self.assertTrue(needs)
        self.assertIn("negation", reasons)
        self.assertIn("quantifier", reasons)

    def test_case_insensitive(self):
        needs, reasons = needs_verification("NEVER again")
        self.assertTrue(needs)
        self.assertIn("negation", reasons)

    def test_negation_inside_word_does_not_trigger(self):
        # "snorkel" contains the substring "no" but not the word "no".
        # The regex uses \b boundaries so this must not trigger.
        needs, reasons = needs_verification("the snorkel was blue")
        self.assertFalse(needs)

    def test_quantifier_inside_word_does_not_trigger(self):
        # "wallpaper" contains "all" — must not trigger.
        needs, reasons = needs_verification("the wallpaper is nice")
        self.assertFalse(needs)


class BuildVerificationPromptTests(unittest.TestCase):
    def test_contains_source_and_candidate(self):
        prompt = build_verification_prompt(
            source_text="I haven't seen it.",
            candidate_translation="L'ho visto.",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["negation"],
        )
        self.assertIn("I haven't seen it.", prompt)
        self.assertIn("L'ho visto.", prompt)

    def test_contains_language_names(self):
        prompt = build_verification_prompt(
            source_text="all of them",
            candidate_translation="loro",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["quantifier"],
        )
        self.assertIn("English", prompt)
        self.assertIn("Italian", prompt)

    def test_negation_only_emits_negation_question(self):
        prompt = build_verification_prompt(
            source_text="I never said that.",
            candidate_translation="L'ho detto.",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["negation"],
        )
        # Negation question is present.
        self.assertIn("negation", prompt.lower())
        # Quantifier question is NOT present.
        self.assertNotIn("quantifier", prompt.lower())

    def test_quantifier_only_emits_quantifier_question(self):
        prompt = build_verification_prompt(
            source_text="all of them",
            candidate_translation="loro",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["quantifier"],
        )
        self.assertIn("quantifier", prompt.lower())
        self.assertNotIn("preserve every negation", prompt.lower())

    def test_both_reasons_emits_both_questions(self):
        prompt = build_verification_prompt(
            source_text="I never saw all of them",
            candidate_translation="li ho visti",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["negation", "quantifier"],
        )
        self.assertIn("preserve every negation", prompt.lower())
        self.assertIn("quantifier", prompt.lower())

    def test_qwen3_non_thinking_appends_no_think_suffix(self):
        prompt = build_verification_prompt(
            source_text="I haven't seen it.",
            candidate_translation="L'ho visto.",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["negation"],
            is_qwen3=True,
            thinking=False,
        )
        self.assertTrue(prompt.rstrip().endswith("/no_think"))

    def test_qwen3_thinking_does_not_append_no_think(self):
        prompt = build_verification_prompt(
            source_text="I haven't seen it.",
            candidate_translation="L'ho visto.",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["negation"],
            is_qwen3=True,
            thinking=True,
        )
        self.assertNotIn("/no_think", prompt)

    def test_non_qwen3_does_not_append_no_think(self):
        prompt = build_verification_prompt(
            source_text="I haven't seen it.",
            candidate_translation="L'ho visto.",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=["negation"],
            is_qwen3=False,
            thinking=False,
        )
        self.assertNotIn("/no_think", prompt)

    def test_empty_reasons_falls_back_to_generic_check(self):
        # Defensive: callers SHOULD skip CoVe when reasons is empty,
        # but if they pass through, the prompt must still be valid.
        prompt = build_verification_prompt(
            source_text="hello",
            candidate_translation="ciao",
            src_lang_name="English",
            tgt_lang_name="Italian",
            reasons=[],
        )
        self.assertIn("preserve the meaning", prompt.lower())


class ParseVerificationResponseTests(unittest.TestCase):
    def test_empty_response_returns_empty_unchanged(self):
        corrected, was_changed = parse_verification_response("")
        self.assertEqual(corrected, "")
        self.assertFalse(was_changed)

    def test_whitespace_only_returns_empty_unchanged(self):
        corrected, was_changed = parse_verification_response("   \n\n  ")
        self.assertEqual(corrected, "")
        self.assertFalse(was_changed)

    def test_meta_string_unchanged_returns_original(self):
        corrected, was_changed = parse_verification_response(
            "Same as before",
            original_translation="L'ho visto.",
        )
        self.assertEqual(corrected, "L'ho visto.")
        self.assertFalse(was_changed)

    def test_meta_string_no_changes_needed(self):
        corrected, was_changed = parse_verification_response(
            "No changes needed.",
            original_translation="loro",
        )
        self.assertFalse(was_changed)
        self.assertEqual(corrected, "loro")

    def test_meta_string_just_yes(self):
        # Some models ignore "do NOT print the answers" and just emit
        # "YES". Treat as no-change.
        corrected, was_changed = parse_verification_response(
            "YES",
            original_translation="L'ho visto.",
        )
        self.assertFalse(was_changed)

    def test_corrected_translation_returns_changed(self):
        # The bug-fix path: candidate dropped the negation, model
        # restores it.
        corrected, was_changed = parse_verification_response(
            "Non l'ho visto.",
            original_translation="L'ho visto.",
        )
        self.assertEqual(corrected, "Non l'ho visto.")
        self.assertTrue(was_changed)

    def test_identical_translation_returns_unchanged(self):
        # Model echoed the candidate verbatim — counted as YES-YES.
        corrected, was_changed = parse_verification_response(
            "L'ho visto.",
            original_translation="L'ho visto.",
        )
        self.assertFalse(was_changed)

    def test_whitespace_only_difference_treated_as_unchanged(self):
        # Trailing space drift must not flip the was_changed flag.
        corrected, was_changed = parse_verification_response(
            "  L'ho visto.  ",
            original_translation="L'ho visto.",
        )
        self.assertFalse(was_changed)

    def test_strips_surrounding_quotes(self):
        # qwen3 sometimes wraps the output in quotes despite the
        # explicit instruction; we strip them so the comparison
        # against the original is fair.
        corrected, was_changed = parse_verification_response(
            '"Non l\'ho visto."',
            original_translation="L'ho visto.",
        )
        self.assertEqual(corrected, "Non l'ho visto.")
        self.assertTrue(was_changed)

    def test_takes_first_non_empty_line(self):
        # Preamble strip is supposed to be done upstream, but if a
        # leading blank line slips through, we still pick the actual
        # output line.
        corrected, was_changed = parse_verification_response(
            "\n\nNon l'ho visto.\n",
            original_translation="L'ho visto.",
        )
        self.assertEqual(corrected, "Non l'ho visto.")
        self.assertTrue(was_changed)


if __name__ == "__main__":
    unittest.main()
