"""Unit tests for :func:`videotranslator.segments.repair_split_sentences`.

These tests cover the TASK 2L heuristic that re-joins Whisper segments
which were cut mid-clause (typical pattern: "...going to." +
"Parlare di...").
"""

import unittest

from videotranslator.segments import repair_split_sentences


class RepairSplitSentencesTests(unittest.TestCase):
    # --- guard rails on degenerate input ----------------------------------

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(repair_split_sentences([]), [])

    def test_single_segment_returned_unchanged(self):
        seg = [{"start": 0.0, "end": 2.0, "text": "Solo questo."}]
        out = repair_split_sentences(seg)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"], "Solo questo.")
        # Defensive copy: caller's dict must not be mutated.
        self.assertIsNot(out[0], seg[0])

    # --- legitimate sentence boundaries are preserved --------------------

    def test_complete_sentence_then_new_sentence_no_join(self):
        # Both halves are independent sentences — no continuation token at
        # the end of the first, capitalised start on the second.
        segs = [
            {"start": 0.0, "end": 2.0, "text": "Hello world."},
            {"start": 2.1, "end": 4.0, "text": "Another sentence."},
        ]
        out = repair_split_sentences(segs)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["text"], "Hello world.")
        self.assertEqual(out[1]["text"], "Another sentence.")

    def test_question_then_question_no_join(self):
        # End in "?" with capitalised follow-up: clearly two sentences.
        segs = [
            {"start": 0.0, "end": 2.0, "text": "Are you sure?"},
            {"start": 2.1, "end": 4.0, "text": "Domanda?"},
        ]
        out = repair_split_sentences(segs)
        self.assertEqual(len(out), 2)

    # --- positive cases: real Whisper false-stops ------------------------

    def test_join_english_continuation_to_lowercase(self):
        # The exact pattern reported by the user.
        segs = [
            {"start": 0.0, "end": 1.5, "text": "I am going to."},
            {"start": 1.7, "end": 4.0, "text": "talk about another agent."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)
        self.assertEqual(
            out[0]["text"], "I am going to. talk about another agent."
        )
        self.assertAlmostEqual(out[0]["start"], 0.0)
        self.assertAlmostEqual(out[0]["end"], 4.0)

    def test_join_italian_della_lowercase(self):
        segs = [
            {"start": 0.0, "end": 1.0, "text": "Parlo della."},
            {"start": 1.2, "end": 3.0, "text": "casa nuova."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="it")
        self.assertEqual(len(out), 1)
        self.assertIn("della", out[0]["text"])
        self.assertIn("casa nuova", out[0]["text"])

    def test_join_token_followed_by_comma(self):
        # The connector keeps a comma instead of a period. Strip should
        # still surface "to" as the last word.
        segs = [
            {"start": 0.0, "end": 1.5, "text": "I want to,"},
            {"start": 1.7, "end": 3.0, "text": "go home."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)

    # --- gap and speaker constraints ------------------------------------

    def test_gap_too_large_blocks_join(self):
        segs = [
            {"start": 0.0, "end": 1.5, "text": "I am going to."},
            {"start": 4.0, "end": 6.0, "text": "talk about it."},
        ]
        out = repair_split_sentences(segs, max_join_gap_s=0.5)
        self.assertEqual(len(out), 2)

    def test_different_speaker_blocks_join(self):
        segs = [
            {
                "start": 0.0, "end": 1.5,
                "text": "I am going to.", "speaker": "SPEAKER_00",
            },
            {
                "start": 1.7, "end": 4.0,
                "text": "talk about it.", "speaker": "SPEAKER_01",
            },
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 2)

    def test_capitalised_follow_up_blocks_join(self):
        # End on continuation but next starts capitalised and not "I".
        segs = [
            {"start": 0.0, "end": 1.5, "text": "We came from."},
            {"start": 1.7, "end": 3.0, "text": "Paris was great."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 2)

    def test_first_person_I_does_not_block(self):
        # "I"/"I'm" at sentence-start are uppercase but legitimate
        # continuations after a connector.
        segs = [
            {"start": 0.0, "end": 1.5, "text": "I think that."},
            {"start": 1.7, "end": 3.0, "text": "I'm right."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)

    # --- cascading merges -----------------------------------------------

    def test_three_segment_cascade(self):
        segs = [
            {"start": 0.0, "end": 1.0, "text": "I am going to."},
            {"start": 1.1, "end": 2.0, "text": "talk by."},
            {"start": 2.1, "end": 3.0, "text": "phone tomorrow."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0]["start"], 0.0)
        self.assertAlmostEqual(out[0]["end"], 3.0)
        self.assertIn("phone tomorrow", out[0]["text"])

    # --- metadata preservation -------------------------------------------

    def test_text_tgt_concatenated_when_present(self):
        segs = [
            {
                "start": 0.0, "end": 1.5,
                "text": "I am going to.", "text_tgt": "Sto per.",
            },
            {
                "start": 1.7, "end": 3.0,
                "text": "talk now.", "text_tgt": "parlare ora.",
            },
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text_tgt"], "Sto per. parlare ora.")

    def test_speaker_preserved_when_shared(self):
        segs = [
            {
                "start": 0.0, "end": 1.5,
                "text": "I am going to.", "speaker": "SPEAKER_00",
            },
            {
                "start": 1.7, "end": 3.0,
                "text": "talk soon.", "speaker": "SPEAKER_00",
            },
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["speaker"], "SPEAKER_00")

    def test_words_field_concatenated(self):
        segs = [
            {
                "start": 0.0, "end": 1.0,
                "text": "I am going to.",
                "words": [{"w": "I"}, {"w": "going"}],
            },
            {
                "start": 1.1, "end": 2.0,
                "text": "talk now.",
                "words": [{"w": "talk"}],
            },
        ]
        out = repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["words"]), 3)

    # --- input never mutated --------------------------------------------

    def test_input_segments_not_mutated(self):
        segs = [
            {"start": 0.0, "end": 1.5, "text": "I am going to."},
            {"start": 1.7, "end": 3.0, "text": "talk."},
        ]
        snapshot = [dict(s) for s in segs]
        repair_split_sentences(segs, src_lang_hint="en")
        self.assertEqual(segs, snapshot)

    # --- region tags / unknown languages --------------------------------

    def test_region_tag_falls_back_to_base_lang(self):
        # "en-US" must behave like "en".
        segs = [
            {"start": 0.0, "end": 1.0, "text": "I want to."},
            {"start": 1.1, "end": 2.0, "text": "go."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="en-US")
        self.assertEqual(len(out), 1)

    def test_unknown_lang_falls_back_to_english_tokens(self):
        # "auto" / unknown → use EN list, which still catches "to.".
        segs = [
            {"start": 0.0, "end": 1.0, "text": "I want to."},
            {"start": 1.1, "end": 2.0, "text": "go."},
        ]
        out = repair_split_sentences(segs, src_lang_hint="auto")
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
