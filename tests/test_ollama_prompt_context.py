"""Unit tests for videotranslator.ollama_prompt.build_translation_prompt.

These cover the TASK 2D contract: a sliding-window CONTEXT block is injected
when prev_text / next_text are supplied, and the resulting prompt makes it
unambiguous to the LLM that the context must NOT be translated.
"""

import unittest

from videotranslator.ollama_prompt import (
    CONTEXT_SNIPPET_MAX_CHARS,
    build_translation_prompt,
)


# Default args used by most tests. Individual tests override what they care
# about via kwargs to keep the assertions focused.
def _build(
    text="The quick brown fox jumps over the lazy dog.",
    slot_s=4.0,
    src_name="English",
    tgt_name="Italian",
    *,
    slot_aware=True,
    is_qwen3=False,
    thinking=False,
    prev_text=None,
    next_text=None,
):
    return build_translation_prompt(
        text,
        slot_s,
        src_name,
        tgt_name,
        slot_aware=slot_aware,
        is_qwen3=is_qwen3,
        thinking=thinking,
        prev_text=prev_text,
        next_text=next_text,
    )


class TargetTextPresenceTests(unittest.TestCase):
    def test_target_text_always_present(self):
        prompt = _build(text="Hello world.")
        self.assertIn("Hello world.", prompt)

    def test_long_target_text_not_truncated(self):
        # The target text must survive at full length even when much longer
        # than CONTEXT_SNIPPET_MAX_CHARS — only neighbours get truncated.
        long_text = "a" * (CONTEXT_SNIPPET_MAX_CHARS * 3)
        prompt = _build(text=long_text)
        self.assertIn(long_text, prompt)

    def test_language_names_appear_in_prompt(self):
        prompt = _build(src_name="French", tgt_name="Japanese")
        self.assertIn("French", prompt)
        self.assertIn("Japanese", prompt)


class ContextBlockPresenceTests(unittest.TestCase):
    def test_no_context_when_neither_neighbour_provided(self):
        prompt = _build(prev_text=None, next_text=None)
        self.assertNotIn("CONTEXT", prompt)
        self.assertNotIn("[Previous]", prompt)
        self.assertNotIn("[Next]", prompt)

    def test_no_context_when_neighbours_are_empty_or_whitespace(self):
        # Empty / whitespace neighbour text is treated identically to None
        # so the CONTEXT block does not appear.
        prompt = _build(prev_text="", next_text="   \n\t  ")
        self.assertNotIn("CONTEXT", prompt)
        self.assertNotIn("[Previous]", prompt)
        self.assertNotIn("[Next]", prompt)

    def test_previous_only(self):
        prompt = _build(prev_text="they're less likely to", next_text=None)
        self.assertIn("CONTEXT", prompt)
        self.assertIn("[Previous] they're less likely to", prompt)
        # No actual [Next] context line is emitted. The literal token does
        # appear once inside the reinforced "ignoring the [Previous]/[Next]
        # context" reminder — that's an intentional reminder, not an
        # emitted context line. Assert by checking line-start position.
        next_lines = [
            line for line in prompt.splitlines() if line.startswith("[Next]")
        ]
        self.assertEqual(next_lines, [])

    def test_next_only(self):
        prompt = _build(prev_text=None, next_text="When I gave up sugar")
        self.assertIn("CONTEXT", prompt)
        self.assertIn("[Next] When I gave up sugar", prompt)
        # No actual [Previous] context line emitted (see test_previous_only).
        prev_lines = [
            line for line in prompt.splitlines() if line.startswith("[Previous]")
        ]
        self.assertEqual(prev_lines, [])

    def test_both_neighbours(self):
        prompt = _build(
            prev_text="they're less likely to",
            next_text="When I gave up sugar",
        )
        self.assertIn("[Previous] they're less likely to", prompt)
        self.assertIn("[Next] When I gave up sugar", prompt)


class DoNotTranslateInstructionTests(unittest.TestCase):
    def test_explicit_do_not_translate_when_context_present(self):
        prompt = _build(prev_text="hello there")
        # The CONTEXT header itself carries the instruction.
        self.assertIn("DO NOT translate", prompt)
        # And the source-text marker is reinforced to repeat the constraint.
        self.assertIn("TO TRANSLATE", prompt)
        self.assertIn("ignoring the [Previous]/[Next] context", prompt)

    def test_no_reinforced_marker_when_no_context(self):
        # Without context the standard "English text:" marker is used (no
        # need to remind the model what to ignore).
        prompt = _build(src_name="English", prev_text=None, next_text=None)
        self.assertNotIn("DO NOT translate", prompt)
        self.assertNotIn("TO TRANSLATE", prompt)
        self.assertIn("English text:", prompt)


class SlotAwareTests(unittest.TestCase):
    def test_slot_clause_present_when_slot_aware_and_positive(self):
        prompt = _build(slot_aware=True, slot_s=4.2)
        self.assertIn("Target reading time", prompt)
        self.assertIn("4.2 seconds", prompt)
        # The trailing hint also surfaces.
        self.assertIn("~4.2s", prompt)

    def test_no_slot_clause_when_slot_aware_disabled(self):
        prompt = _build(slot_aware=False, slot_s=4.2)
        self.assertNotIn("Target reading time", prompt)
        self.assertNotIn("~4.2s", prompt)

    def test_no_slot_clause_when_slot_zero(self):
        prompt = _build(slot_aware=True, slot_s=0.0)
        self.assertNotIn("Target reading time", prompt)
        self.assertNotIn("~0.0s", prompt)


class Qwen3NoThinkSuffixTests(unittest.TestCase):
    def test_no_think_suffix_for_qwen3_non_thinking(self):
        prompt = _build(is_qwen3=True, thinking=False)
        self.assertTrue(prompt.endswith("/no_think"))

    def test_no_suffix_for_qwen3_thinking(self):
        prompt = _build(is_qwen3=True, thinking=True)
        self.assertNotIn("/no_think", prompt)

    def test_no_suffix_for_non_qwen3(self):
        prompt = _build(is_qwen3=False, thinking=False)
        self.assertNotIn("/no_think", prompt)
        prompt2 = _build(is_qwen3=False, thinking=True)
        self.assertNotIn("/no_think", prompt2)


class ContextTruncationTests(unittest.TestCase):
    def test_long_prev_truncated_to_cap(self):
        long_prev = "x" * (CONTEXT_SNIPPET_MAX_CHARS + 50)
        prompt = _build(prev_text=long_prev)
        # Exactly the cap should appear after the [Previous] marker.
        self.assertIn("[Previous] " + "x" * CONTEXT_SNIPPET_MAX_CHARS, prompt)
        # And the over-the-cap suffix should NOT appear standalone.
        self.assertNotIn("x" * (CONTEXT_SNIPPET_MAX_CHARS + 1), prompt)

    def test_long_next_truncated_to_cap(self):
        long_next = "y" * (CONTEXT_SNIPPET_MAX_CHARS + 25)
        prompt = _build(next_text=long_next)
        self.assertIn("[Next] " + "y" * CONTEXT_SNIPPET_MAX_CHARS, prompt)
        self.assertNotIn("y" * (CONTEXT_SNIPPET_MAX_CHARS + 1), prompt)

    def test_short_prev_kept_intact(self):
        prompt = _build(prev_text="short context")
        self.assertIn("[Previous] short context", prompt)

    def test_prev_is_stripped_of_outer_whitespace(self):
        prompt = _build(prev_text="   padded text   \n")
        self.assertIn("[Previous] padded text", prompt)
        # The padded version with leading spaces must not leak through.
        self.assertNotIn("[Previous]    padded", prompt)


class IntegrationStyleTests(unittest.TestCase):
    """End-to-end sanity check: the CONTEXT block lands BEFORE the
    requirements list, so the model reads it first and the requirements
    apply only to the target text."""

    def test_context_appears_before_requirements(self):
        prompt = _build(prev_text="prev", next_text="next")
        ctx_idx = prompt.index("CONTEXT")
        req_idx = prompt.index("CRITICAL REQUIREMENTS")
        self.assertLess(ctx_idx, req_idx)

    def test_target_text_appears_after_requirements(self):
        prompt = _build(text="target sentence.", prev_text="prev")
        req_idx = prompt.index("CRITICAL REQUIREMENTS")
        # The target appears after the requirements block.
        target_idx = prompt.index("target sentence.")
        self.assertLess(req_idx, target_idx)


class NegationPreservationRulesTests(unittest.TestCase):
    """TASK 2N: prompt must explicitly tell the model to preserve
    English negations and quantifiers. Regression scenario from the
    2026-04-29 EN→IT run: 'if you haven't seen' got translated as
    'se hai visto' (negation dropped). The fix is purely prompt-level
    so it must show up in the rendered prompt text."""

    def test_negation_clause_present(self):
        prompt = _build()
        self.assertIn("PRESERVE NEGATIONS", prompt)

    def test_negation_clause_lists_canonical_forms(self):
        prompt = _build()
        # Spot-check: the prompt must namedrop the contractions the
        # model is most likely to drop. Listing them explicitly tends
        # to anchor instruction-tuned models on the rule.
        for token in ("not", "haven't", "can't", "won't", "never"):
            self.assertIn(token, prompt)

    def test_quantifier_clause_present(self):
        prompt = _build()
        # Same idea but for quantifiers (all/some/none) which the model
        # also occasionally weakens or strengthens.
        self.assertIn("PRESERVE quantifiers", prompt)

    def test_negation_rule_is_a_critical_requirement(self):
        prompt = _build()
        req_idx = prompt.index("CRITICAL REQUIREMENTS")
        neg_idx = prompt.index("PRESERVE NEGATIONS")
        # The rule must live inside the CRITICAL REQUIREMENTS block,
        # not after the source text.
        self.assertLess(req_idx, neg_idx)
        text_marker = prompt.index("text:") if "text:" in prompt else len(prompt)
        self.assertLess(neg_idx, text_marker)


class GlobalContextTests(unittest.TestCase):
    """TASK 2K: optional document-level summary injected as GLOBAL CONTEXT.

    The block must appear BEFORE the local prev/next CONTEXT block, and
    above the requirements list, so the model reads the global anchor
    first and applies it while parsing the local context."""

    def test_no_global_block_when_global_context_none(self):
        prompt = build_translation_prompt(
            "Hello world.", 4.0, "English", "Italian",
            global_context=None,
        )
        self.assertNotIn("GLOBAL CONTEXT", prompt)

    def test_no_global_block_when_global_context_blank(self):
        # Whitespace-only is treated as None.
        prompt = build_translation_prompt(
            "Hello world.", 4.0, "English", "Italian",
            global_context="   \n\t  ",
        )
        self.assertNotIn("GLOBAL CONTEXT", prompt)

    def test_global_block_emitted_when_provided(self):
        summary = (
            "Tutorial on keyboard shortcuts. Preserve verbatim: Ctrl+C, Cmd+V, VS Code."
        )
        prompt = build_translation_prompt(
            "Press the key combination.", 4.0, "English", "Italian",
            global_context=summary,
        )
        self.assertIn("GLOBAL CONTEXT", prompt)
        self.assertIn(summary, prompt)
        # Anti-translate framing must appear next to the global block too.
        self.assertIn("DO NOT translate", prompt)

    def test_global_block_appears_before_local_context(self):
        # When BOTH are present the document-level summary must come
        # first so the model has the global anchor before the locale.
        prompt = build_translation_prompt(
            "Press the key combination.", 4.0, "English", "Italian",
            prev_text="Earlier we set up the editor.",
            next_text="It saves the file.",
            global_context="VS Code tutorial. Preserve: Ctrl+S.",
        )
        global_idx = prompt.index("GLOBAL CONTEXT")
        local_idx = prompt.index("[Previous]")
        self.assertLess(global_idx, local_idx)

    def test_global_block_appears_before_requirements(self):
        prompt = build_translation_prompt(
            "Press the key combination.", 4.0, "English", "Italian",
            global_context="VS Code tutorial. Preserve: Ctrl+S.",
        )
        global_idx = prompt.index("GLOBAL CONTEXT")
        req_idx = prompt.index("CRITICAL REQUIREMENTS")
        self.assertLess(global_idx, req_idx)

    def test_global_only_uses_dedicated_target_marker(self):
        # With only a global summary (no prev/next) the reinforced
        # marker must reference the GLOBAL CONTEXT, not [Previous]/[Next]
        # which are not present in the prompt.
        prompt = build_translation_prompt(
            "Press the key combination.", 4.0, "English", "Italian",
            global_context="VS Code tutorial. Preserve: Ctrl+S.",
        )
        self.assertIn("ignoring the GLOBAL CONTEXT above", prompt)
        # The local-context wording should NOT appear when prev/next are
        # absent (the regression test for the local case still passes
        # because it provides a prev_text).
        self.assertNotIn("ignoring the [Previous]/[Next] context", prompt)

    def test_target_text_still_appears_after_global_block(self):
        prompt = build_translation_prompt(
            "Press the key combination.", 4.0, "English", "Italian",
            global_context="VS Code tutorial. Preserve: Ctrl+S.",
        )
        global_idx = prompt.index("GLOBAL CONTEXT")
        target_idx = prompt.index("Press the key combination.")
        self.assertLess(global_idx, target_idx)


if __name__ == "__main__":
    unittest.main()
