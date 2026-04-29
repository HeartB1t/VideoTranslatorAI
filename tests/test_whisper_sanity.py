"""Unit tests for ``videotranslator.whisper_sanity`` (TASK 2M).

Pure tests: no I/O, no external services. Cover the happy path
(real-world cases observed on 2026-04-29 Pen-Testing video
transcript), boundary cases (empty input, malformed input) and
explicit non-regressions (numbers, common short words, longer
words must not be flagged).
"""

from __future__ import annotations

import unittest

from videotranslator.whisper_sanity import (
    detect_repeated_words,
    find_suspicious_tokens,
    sanity_score_segments,
)


class FindSuspiciousTokensTests(unittest.TestCase):
    def test_empty_text_returns_empty(self) -> None:
        self.assertEqual(find_suspicious_tokens(""), [])
        self.assertEqual(find_suspicious_tokens(None), [])  # type: ignore[arg-type]

    def test_real_words_not_flagged(self) -> None:
        # "okay" is 4 chars so it's not even inspected by the 1-3
        # filter. "I" and "am" are in the whitelist.
        self.assertEqual(find_suspicious_tokens("I am okay"), [])

    def test_isolated_ay_flagged(self) -> None:
        # Real Whisper artefact observed in 2026-04-29 Pen-Testing
        # video at line 33: "okay" → "ay".
        self.assertEqual(find_suspicious_tokens("I am ay"), ["ay"])

    def test_em_um_flagged(self) -> None:
        self.assertEqual(find_suspicious_tokens("em was here"), ["em"])
        self.assertEqual(find_suspicious_tokens("um, well"), ["um"])

    def test_numbers_not_flagged(self) -> None:
        # Numbers must never trigger; the regex only matches alpha.
        self.assertEqual(find_suspicious_tokens("42 was the answer"), [])
        self.assertEqual(find_suspicious_tokens("on day 365 of"), [])

    def test_long_words_not_flagged(self) -> None:
        # 4+ chars are out of scope of this heuristic.
        self.assertEqual(
            find_suspicious_tokens("hello world testing"),
            [],
        )

    def test_dedup_and_order_preserved(self) -> None:
        # ``ay`` appears twice but should be reported only once,
        # in order of first appearance.
        self.assertEqual(
            find_suspicious_tokens("ay was um the ay"),
            ["ay", "um"],
        )

    def test_documented_false_positive_short_real_words(self) -> None:
        # Short real words (3 chars) that aren't in the compact
        # whitelist WILL be flagged. This is a documented limitation:
        # the editor pass surfaces these for human review, the cost
        # of a false positive is just one extra glance in the editor.
        # Examples: ``cat``, ``dog``, ``sun`` are not in the whitelist.
        flagged = find_suspicious_tokens("the cat sat")
        self.assertIn("cat", flagged)
        self.assertIn("sat", flagged)

    def test_apostrophes_skipped(self) -> None:
        # ``don't`` -> regex can match ``t`` if we weren't careful;
        # the ``\b`` boundary plus alpha-only [A-Za-z] keeps it out
        # because the apostrophe is the boundary between ``don`` and
        # ``t`` so ``t`` would be a 1-char match. We accept that
        # ``t`` matches but it's NOT in the common-words list either,
        # so it'd be flagged. Verify behaviour: should we treat
        # contractions specially? For now we just document the
        # actual behaviour: ``don`` (3-char) is not in the whitelist.
        # So ``don't`` produces flags. This documents the limitation
        # for the editor pass — manual review recommended.
        flagged = find_suspicious_tokens("I don't know")
        # "don" 3 chars NOT in whitelist → flagged.
        # "t" 1 char NOT in whitelist → flagged.
        # We assert the *behaviour*, not perfection.
        self.assertIn("don", flagged)


class DetectRepeatedWordsTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(detect_repeated_words(""), [])
        self.assertEqual(detect_repeated_words(None), [])  # type: ignore[arg-type]

    def test_no_repeats(self) -> None:
        self.assertEqual(
            detect_repeated_words("the quick brown fox"),
            [],
        )

    def test_single_repeat(self) -> None:
        self.assertEqual(detect_repeated_words("the the cat"), ["the"])

    def test_multiple_repeats_ordered(self) -> None:
        self.assertEqual(
            detect_repeated_words("and and the the cat"),
            ["and", "the"],
        )

    def test_repeat_case_insensitive(self) -> None:
        self.assertEqual(
            detect_repeated_words("The the cat"),
            ["the"],
        )

    def test_repeat_dedup(self) -> None:
        # ``the the`` appears twice in different positions.
        self.assertEqual(
            detect_repeated_words("the the cat the the"),
            ["the"],
        )


class SanityScoreSegmentsTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        self.assertEqual(sanity_score_segments([]), {})
        self.assertEqual(sanity_score_segments(None), {})  # type: ignore[arg-type]

    def test_clean_segments_no_flags(self) -> None:
        segs = [
            {"start": 0, "end": 1, "text": "I am here"},
            {"start": 1, "end": 2, "text": "Hello world"},
        ]
        self.assertEqual(sanity_score_segments(segs), {})

    def test_one_flagged_segment(self) -> None:
        segs = [
            {"start": 0, "end": 1, "text": "I am ay"},  # ay suspicious
            {"start": 1, "end": 2, "text": "Hello world"},
        ]
        result = sanity_score_segments(segs)
        self.assertEqual(set(result.keys()), {0})
        self.assertEqual(result[0]["suspicious"], ["ay"])
        self.assertEqual(result[0]["repeats"], [])

    def test_repeat_only(self) -> None:
        # Use only whitelisted short words ("be") to verify the
        # ``repeats`` channel in isolation. (``cat`` would be flagged
        # by the 3-char heuristic — that's a documented false positive.)
        segs = [{"start": 0, "end": 1, "text": "let it be be"}]
        result = sanity_score_segments(segs)
        self.assertEqual(result, {0: {"suspicious": [], "repeats": ["be"]}})

    def test_text_src_preferred_over_text(self) -> None:
        # When both fields exist, text_src (post-translate raw source)
        # is the more accurate transcript and should be checked.
        segs = [{
            "start": 0, "end": 1,
            "text": "translated clean text",
            "text_src": "I am ay",
        }]
        result = sanity_score_segments(segs)
        self.assertEqual(result[0]["suspicious"], ["ay"])

    def test_segment_without_text_skipped(self) -> None:
        segs = [
            {"start": 0, "end": 1},  # no text fields
            {"start": 1, "end": 2, "text": "   "},  # whitespace only
            {"start": 2, "end": 3, "text": "I am ay"},  # flagged
        ]
        result = sanity_score_segments(segs)
        self.assertEqual(set(result.keys()), {2})

    def test_non_dict_segment_ignored(self) -> None:
        segs = [
            "not a dict",  # type: ignore[list-item]
            {"start": 0, "end": 1, "text": "I am ay"},
        ]
        result = sanity_score_segments(segs)
        self.assertEqual(set(result.keys()), {1})

    def test_mixed_flags(self) -> None:
        segs = [
            {"start": 0, "end": 1, "text": "um ay was the the"},
        ]
        result = sanity_score_segments(segs)
        self.assertEqual(result[0]["suspicious"], ["um", "ay"])
        self.assertEqual(result[0]["repeats"], ["the"])


if __name__ == "__main__":
    unittest.main()
