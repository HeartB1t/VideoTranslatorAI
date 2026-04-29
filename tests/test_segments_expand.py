"""Tests for the smart slot expansion / time borrowing helper.

Covers TASK 2E: ``expand_tight_slots`` should grant a few hundred extra
milliseconds to "tight" segments by stealing from silent gaps and from
adjacent "easy" segments, without ever mutating the input list.
"""

import copy
import unittest

from videotranslator.segments import expand_tight_slots
from videotranslator.ollama_length_control import chars_per_second_for


# Build a Whisper-shaped segment with a text whose length matches a
# requested pre-stretch ratio. Useful so the tests don't depend on
# fragile char-counting in literals.
def _make_seg(start: float, end: float, ratio: float, target_lang: str = "it") -> dict:
    slot = max(end - start, 1e-6)
    cps = chars_per_second_for(target_lang)
    n_chars = max(1, int(round(ratio * slot * cps)))
    text = "x" * n_chars
    return {"start": start, "end": end, "text": text}


class ExpandTightSlotsTests(unittest.TestCase):

    # 1. Empty input → empty output, never raises.
    def test_empty_input_returns_empty(self):
        self.assertEqual(expand_tight_slots([], "it"), [])

    # 2. Single segment → returned unchanged (no neighbor, no gap).
    def test_single_segment_unchanged(self):
        seg = _make_seg(0.0, 4.0, ratio=1.80)
        out = expand_tight_slots([seg], "it")
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0]["start"], 0.0)
        self.assertAlmostEqual(out[0]["end"], 4.0)
        self.assertEqual(out[0]["text"], seg["text"])

    # 3. Tight segment followed by easy neighbor with usable gap → extends end.
    def test_extends_tight_segment_using_gap(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=1.80)
        seg_easy = _make_seg(3.5, 7.5, ratio=0.50)  # 1.5s gap, easy
        out = expand_tight_slots([seg_tight, seg_easy], "it",
                                 max_gap_steal_s=1.5,
                                 min_gap_keep_s=0.15)
        # Stole min(1.5 - 0.15, 1.5) = 1.35s
        self.assertAlmostEqual(out[0]["end"], 2.0 + 1.35, places=5)
        self.assertAlmostEqual(out[1]["start"], 3.5)  # neighbor untouched (we never reached step 2)

    # 4. Tiny gap (< 2 × min_gap_keep_s) AND non-easy neighbor → no stealing.
    def test_tiny_gap_skipped(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=1.80)
        # Neighbor ratio 1.00 ≥ neighbor_easy_ratio (0.80) → step 2 also skipped.
        seg_next = _make_seg(2.10, 5.0, ratio=1.00)
        out = expand_tight_slots([seg_tight, seg_next], "it",
                                 min_gap_keep_s=0.15)
        # gap = 0.10 < 2 × 0.15 = 0.30 → skip step 1; neighbor not easy → skip step 2.
        self.assertAlmostEqual(out[0]["end"], 2.0)
        self.assertAlmostEqual(out[1]["start"], 2.10)

    # 5. Large gap is capped at max_gap_steal_s.
    def test_large_gap_capped_at_max(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=1.80)
        seg_next = _make_seg(10.0, 12.0, ratio=0.50)  # huge 8s gap
        out = expand_tight_slots([seg_tight, seg_next], "it",
                                 max_gap_steal_s=1.5,
                                 min_gap_keep_s=0.15)
        self.assertAlmostEqual(out[0]["end"], 2.0 + 1.5, places=5)

    # 6. Already-loose segment is left untouched.
    def test_loose_segment_untouched(self):
        seg_loose = _make_seg(0.0, 5.0, ratio=1.10)
        seg_next = _make_seg(6.0, 9.0, ratio=0.40)
        out = expand_tight_slots([seg_loose, seg_next], "it",
                                 tight_ratio_threshold=1.50)
        self.assertAlmostEqual(out[0]["end"], 5.0)
        self.assertAlmostEqual(out[1]["start"], 6.0)

    # 7. Borrowing from an easy neighbor when the gap alone isn't enough.
    def test_borrows_from_easy_neighbor_when_gap_insufficient(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=1.80)
        # No gap at all so step 1 does nothing; neighbor very easy and long.
        seg_easy = _make_seg(2.0, 8.0, ratio=0.30)
        out = expand_tight_slots([seg_tight, seg_easy], "it",
                                 max_neighbor_steal_s=0.5,
                                 min_gap_keep_s=0.15)
        # Step 1 stole nothing (gap=0). Step 2 should steal up to 0.5s.
        delta = out[0]["end"] - 2.0
        self.assertGreater(delta, 0.0)
        self.assertLessEqual(delta, 0.5 + 1e-6)
        # Neighbor start shifts by the same amount; end is preserved.
        self.assertAlmostEqual(out[1]["start"] - 2.0, delta, places=5)
        self.assertAlmostEqual(out[1]["end"], 8.0)

    # 8. Neighbor that is not "easy" → no Step 2 borrowing.
    def test_no_borrow_when_neighbor_not_easy(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=1.80)
        seg_medium = _make_seg(2.0, 6.0, ratio=1.00)  # above 0.80 threshold
        out = expand_tight_slots([seg_tight, seg_medium], "it",
                                 neighbor_easy_ratio=0.80,
                                 min_gap_keep_s=0.15)
        # Gap = 0 → step 1 nothing. Neighbor not easy → step 2 nothing.
        self.assertAlmostEqual(out[0]["end"], 2.0)
        self.assertAlmostEqual(out[1]["start"], 2.0)

    # 9. max_neighbor_steal_s is respected.
    def test_neighbor_steal_capped(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=2.50)  # very tight
        seg_easy = _make_seg(2.0, 30.0, ratio=0.10)  # huge & very easy
        cap = 0.4
        out = expand_tight_slots([seg_tight, seg_easy], "it",
                                 max_neighbor_steal_s=cap,
                                 min_gap_keep_s=0.15)
        delta = out[0]["end"] - 2.0
        self.assertLessEqual(delta, cap + 1e-6)
        self.assertAlmostEqual(out[1]["start"] - 2.0, delta, places=5)

    # 10. Order of segments preserved.
    def test_order_preserved(self):
        segs = [
            _make_seg(0.0, 1.5, ratio=1.80),
            _make_seg(2.0, 3.5, ratio=0.40),
            _make_seg(4.0, 5.5, ratio=1.70),
            _make_seg(6.0, 9.0, ratio=0.50),
        ]
        out = expand_tight_slots(segs, "it")
        self.assertEqual(len(out), 4)
        starts = [s["start"] for s in out]
        self.assertEqual(starts, sorted(starts))

    # 11. Input is NOT mutated in place.
    def test_input_not_mutated(self):
        segs = [
            _make_seg(0.0, 2.0, ratio=1.80),
            _make_seg(3.0, 7.0, ratio=0.40),
        ]
        snapshot = copy.deepcopy(segs)
        _ = expand_tight_slots(segs, "it")
        self.assertEqual(segs, snapshot)
        # And the same dicts are NOT shared with the output (new dicts).
        out = expand_tight_slots(segs, "it")
        out[0]["start"] = -999.0
        self.assertNotEqual(segs[0]["start"], -999.0)

    # 12. Combined gap + neighbor borrowing on a middle segment.
    def test_combined_gap_and_neighbor_on_middle(self):
        first = _make_seg(0.0, 2.0, ratio=0.30)
        middle_tight = _make_seg(2.5, 4.0, ratio=2.00)  # 0.5s gap before; tight
        easy_next = _make_seg(4.3, 9.0, ratio=0.20)     # 0.3s gap after; very easy
        out = expand_tight_slots([first, middle_tight, easy_next], "it",
                                 max_gap_steal_s=1.5,
                                 min_gap_keep_s=0.15,
                                 max_neighbor_steal_s=0.5,
                                 neighbor_easy_ratio=0.80)
        # Step 1: middle steals from gap-after (0.30 - 0.15 = 0.15s).
        # Step 2: middle still tight → borrow from easy_next, capped at 0.5s.
        delta = out[1]["end"] - 4.0
        self.assertGreater(delta, 0.15 - 1e-6)  # at least the gap part
        # First segment is loose enough to be untouched on its right edge.
        self.assertAlmostEqual(out[0]["end"], 2.0)

    # 13. The text content is preserved exactly (no translation re-flow here).
    def test_text_preserved(self):
        seg_tight = _make_seg(0.0, 2.0, ratio=1.80)
        seg_easy = _make_seg(3.5, 7.5, ratio=0.40)
        original_texts = [seg_tight["text"], seg_easy["text"]]
        out = expand_tight_slots([seg_tight, seg_easy], "it")
        self.assertEqual([s["text"] for s in out], original_texts)


if __name__ == "__main__":
    unittest.main()
