"""Unit tests for videotranslator.document_context.

TASK 2K — these cover the document-level context contract:
* a transcript that is long enough triggers the summary call,
* the summary prompt carries the concatenated transcript and the
  glossary-style instructions,
* the Qwen3 /no_think suffix is gated on the same logic as the
  per-segment translation prompt builder.
"""

import unittest

from videotranslator.document_context import (
    SUMMARY_DEFAULT_MAX_WORDS,
    SUMMARY_MIN_SEGMENTS,
    SUMMARY_TRANSCRIPT_MAX_CHARS,
    build_summary_prompt,
    is_summary_useful,
)


def _segs(*texts: str) -> list[dict]:
    """Build a list of {start,end,text} dicts mimicking Whisper output."""
    return [
        {"start": float(i), "end": float(i) + 1.0, "text": t}
        for i, t in enumerate(texts)
    ]


class IsSummaryUsefulTests(unittest.TestCase):
    def test_none_returns_false(self):
        self.assertFalse(is_summary_useful(None))

    def test_empty_returns_false(self):
        self.assertFalse(is_summary_useful([]))

    def test_below_min_returns_false(self):
        # Default min is 5; 3 segments → False.
        self.assertFalse(is_summary_useful(_segs("a", "b", "c")))

    def test_at_min_returns_true(self):
        # Exactly min_segments → True (boundary inclusive).
        self.assertTrue(is_summary_useful(_segs(*["x"] * SUMMARY_MIN_SEGMENTS)))

    def test_above_min_returns_true(self):
        self.assertTrue(is_summary_useful(_segs(*["x"] * (SUMMARY_MIN_SEGMENTS + 10))))

    def test_custom_min_segments(self):
        # Caller can override the threshold; useful for tests and for
        # opt-in aggressive mode in the future.
        segs = _segs("a", "b")
        self.assertFalse(is_summary_useful(segs, min_segments=3))
        self.assertTrue(is_summary_useful(segs, min_segments=2))


class SummaryPromptStructureTests(unittest.TestCase):
    def test_empty_segments_returns_empty_string(self):
        # Defensive default — caller can call unconditionally.
        prompt = build_summary_prompt([], "Italian", "English")
        self.assertEqual(prompt, "")

    def test_only_blank_segments_returns_empty(self):
        prompt = build_summary_prompt(
            _segs("", "   ", "\n\t"),
            "Italian",
            "English",
        )
        self.assertEqual(prompt, "")

    def test_transcript_concatenated_into_prompt(self):
        segs = _segs("First sentence.", "Second piece of text.", "Third bit.")
        prompt = build_summary_prompt(segs, "Italian", "English")
        # All three pieces must show up in the transcript that the model sees.
        self.assertIn("First sentence.", prompt)
        self.assertIn("Second piece of text.", prompt)
        self.assertIn("Third bit.", prompt)

    def test_language_names_appear_in_prompt(self):
        prompt = build_summary_prompt(_segs("hello"), "Japanese", "French")
        self.assertIn("Japanese", prompt)
        self.assertIn("French", prompt)

    def test_max_words_is_in_prompt(self):
        prompt = build_summary_prompt(
            _segs("hello", "world"),
            "Italian",
            "English",
            max_words=120,
        )
        self.assertIn("120 words", prompt)

    def test_default_max_words_used_when_omitted(self):
        prompt = build_summary_prompt(_segs("hello"), "Italian", "English")
        self.assertIn(f"{SUMMARY_DEFAULT_MAX_WORDS} words", prompt)

    def test_preserve_verbatim_instruction_present(self):
        prompt = build_summary_prompt(_segs("hello"), "Italian", "English")
        # The whole point of the global summary is to anchor terminology;
        # the explicit "preserve verbatim" instruction must be in the prompt.
        self.assertIn("PRESERVED", prompt)
        self.assertIn("VERBATIM", prompt)

    def test_do_not_translate_marker_for_transcript(self):
        # The transcript header must remind the model that the transcript
        # is for understanding only, not for translation as a whole.
        prompt = build_summary_prompt(_segs("hello"), "Italian", "English")
        self.assertIn("DO NOT translate", prompt)

    def test_output_only_the_summary_instruction(self):
        prompt = build_summary_prompt(_segs("hello"), "Italian", "English")
        # Same anti-preamble guard as the translation prompt: the strip
        # helper relies on this discipline upstream.
        self.assertIn("Output ONLY the summary", prompt)


class SummaryPromptQwen3SuffixTests(unittest.TestCase):
    def test_no_think_suffix_for_qwen3_non_thinking(self):
        prompt = build_summary_prompt(
            _segs("hello"), "Italian", "English",
            is_qwen3=True, thinking=False,
        )
        self.assertTrue(prompt.endswith("/no_think"))

    def test_no_suffix_for_qwen3_thinking(self):
        prompt = build_summary_prompt(
            _segs("hello"), "Italian", "English",
            is_qwen3=True, thinking=True,
        )
        self.assertNotIn("/no_think", prompt)

    def test_no_suffix_for_non_qwen3(self):
        prompt_a = build_summary_prompt(
            _segs("hello"), "Italian", "English",
            is_qwen3=False, thinking=False,
        )
        prompt_b = build_summary_prompt(
            _segs("hello"), "Italian", "English",
            is_qwen3=False, thinking=True,
        )
        self.assertNotIn("/no_think", prompt_a)
        self.assertNotIn("/no_think", prompt_b)


class SummaryPromptTranscriptCapTests(unittest.TestCase):
    def test_long_transcript_truncated(self):
        # Build a transcript well over the cap and verify the prompt does
        # not carry the over-the-cap tail. Single segment with a huge
        # text body is the cleanest way to control the length.
        big_text = "a" * (SUMMARY_TRANSCRIPT_MAX_CHARS + 5_000)
        prompt = build_summary_prompt(_segs(big_text), "Italian", "English")
        # Prompt itself is bigger than just the transcript (instructions),
        # but the literal over-cap suffix must NOT be inside it: count the
        # exact-length "a" run.
        self.assertNotIn("a" * (SUMMARY_TRANSCRIPT_MAX_CHARS + 1), prompt)

    def test_short_transcript_kept_intact(self):
        prompt = build_summary_prompt(
            _segs("Short transcript content."),
            "Italian",
            "English",
        )
        self.assertIn("Short transcript content.", prompt)


if __name__ == "__main__":
    unittest.main()
