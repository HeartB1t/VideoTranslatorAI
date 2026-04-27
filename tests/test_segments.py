import unittest

from videotranslator.segments import merge_short_segments, split_on_punctuation


class SegmentTests(unittest.TestCase):
    def test_split_on_latin_sentence_boundary(self):
        segments = [{"start": 0.0, "end": 4.0, "text": "Hello. World."}]

        out = split_on_punctuation(segments)

        self.assertEqual([s["text"] for s in out], ["Hello.", "World."])
        self.assertAlmostEqual(out[0]["start"], 0.0)
        self.assertGreater(out[0]["end"], out[0]["start"])
        self.assertAlmostEqual(out[-1]["end"], 4.0)

    def test_does_not_split_decimal(self):
        segments = [{"start": 0.0, "end": 4.0, "text": "Version 3.14 works."}]

        out = split_on_punctuation(segments)

        self.assertEqual(len(out), 1)

    def test_merge_short_previous_segment(self):
        segments = [
            {"start": 0.0, "end": 1.0, "text": "This is"},
            {"start": 1.5, "end": 4.0, "text": "one sentence."},
        ]

        out = merge_short_segments(segments)

        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"], "This is one sentence.")

    def test_merge_orphan_tail_fragment(self):
        segments = [
            {"start": 0.0, "end": 5.0, "text": "I used to work"},
            {"start": 6.0, "end": 7.5, "text": "for fun."},
        ]

        out = merge_short_segments(segments)

        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"], "I used to work for fun.")


if __name__ == "__main__":
    unittest.main()

