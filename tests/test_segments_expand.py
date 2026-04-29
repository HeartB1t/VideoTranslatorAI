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

    # ---- TASK 2O: bidirectional slot expansion -----------------------------

    # 14. Step 1b: backward gap stealing when forward neighbor is dense.
    #     Tight middle segment has a small forward gap (skip step 1) but a
    #     large backward gap → should anticipate i.start by stealing from
    #     the silence after [i-1].
    def test_step_1b_backward_gap_stealing(self):
        # Loose first; long silence; tight middle; dense next (no fwd gap, not easy).
        first = _make_seg(0.0, 2.0, ratio=0.30)         # [i-1] ends at 2.0
        middle_tight = _make_seg(4.0, 6.0, ratio=1.80)  # 2.0s back-gap, fwd gap=0
        dense_next = _make_seg(6.0, 9.0, ratio=1.20)    # not easy, no gap
        out = expand_tight_slots(
            [first, middle_tight, dense_next], "it",
            max_gap_steal_s=1.5, min_gap_keep_s=0.15,
            neighbor_easy_ratio=0.80,
        )
        # Step 1: forward gap = 0 → nothing.
        # Step 1b: backward gap = 2.0 → steal min(2.0 - 0.15, 1.5) = 1.5s.
        self.assertAlmostEqual(out[1]["start"], 4.0 - 1.5, places=5)
        self.assertAlmostEqual(out[1]["end"], 6.0, places=5)
        # Previous segment end is preserved (gap shrinks but stays > 0.15).
        self.assertAlmostEqual(out[0]["end"], 2.0, places=5)

    # 15. Step 2b: backward neighbor borrowing when forward neighbor is dense.
    def test_step_2b_backward_neighbor_borrow(self):
        easy_first = _make_seg(0.0, 6.0, ratio=0.30)    # very easy, long
        middle_tight = _make_seg(6.0, 8.0, ratio=2.00)  # tight, no fwd/bwd gap
        dense_next = _make_seg(8.0, 11.0, ratio=1.20)   # not easy, no gap
        out = expand_tight_slots(
            [easy_first, middle_tight, dense_next], "it",
            min_gap_keep_s=0.15, max_neighbor_steal_s=0.5,
            neighbor_easy_ratio=0.80,
        )
        # Step 1, 1b, 2: nothing (gaps=0, fwd neighbor not easy).
        # Step 2b: easy_first is loose → cede up to 0.5s from its tail.
        delta = 6.0 - out[1]["start"]
        self.assertGreater(delta, 0.0)
        self.assertLessEqual(delta, 0.5 + 1e-6)
        # Previous segment end shifts back by the same delta.
        self.assertAlmostEqual(easy_first["end"] - out[0]["end"], delta, places=5)
        # Previous segment start preserved.
        self.assertAlmostEqual(out[0]["start"], 0.0, places=5)
        # Middle segment end preserved (only start anticipated).
        self.assertAlmostEqual(out[1]["end"], 8.0, places=5)

    # 16. Order matters: when both forward AND backward gaps are usable,
    #     forward is consumed first (Step 1 before 1b). The middle segment
    #     should grow from its END (forward gap), not its START.
    def test_forward_gap_preferred_over_backward(self):
        # Both gaps are 1.0s. Tight middle should consume forward first.
        first = _make_seg(0.0, 1.0, ratio=0.30)            # ends at 1.0
        middle_tight = _make_seg(2.0, 3.0, ratio=2.50)     # very tight
        last = _make_seg(4.0, 6.0, ratio=0.30)             # easy
        out = expand_tight_slots(
            [first, middle_tight, last], "it",
            max_gap_steal_s=1.5, min_gap_keep_s=0.15,
        )
        # Forward gap consumed: middle.end shifts from 3.0 to 3.0 + (1.0-0.15) = 3.85
        self.assertAlmostEqual(out[1]["end"], 3.85, places=5)
        # Backward gap consumption depends on whether middle is still tight
        # after step 1. With ratio=2.50 and slot doubling, ratio drops to ~1.25
        # which is below tight (1.50) → step 1b should NOT fire.
        self.assertAlmostEqual(out[1]["start"], 2.0, places=5)
        # First segment end untouched (we only stole silence after it).
        self.assertAlmostEqual(out[0]["end"], 1.0, places=5)

    # 17. bidirectional=False reproduces the pre-2O behaviour: even when a
    #     backward gap is the only option, the segment stays tight.
    def test_bidirectional_false_disables_backward_steps(self):
        first = _make_seg(0.0, 2.0, ratio=0.30)
        middle_tight = _make_seg(4.0, 6.0, ratio=1.80)
        dense_next = _make_seg(6.0, 9.0, ratio=1.20)
        out = expand_tight_slots(
            [first, middle_tight, dense_next], "it",
            min_gap_keep_s=0.15, max_gap_steal_s=1.5,
            bidirectional=False,
        )
        # No forward gap, no easy forward neighbor → nothing to do.
        # With bidirectional=False the backward gap is ignored.
        self.assertAlmostEqual(out[1]["start"], 4.0, places=5)
        self.assertAlmostEqual(out[1]["end"], 6.0, places=5)
        self.assertAlmostEqual(out[0]["end"], 2.0, places=5)

    # 18. Cumulative borrowing: 3 consecutive tight segments sandwiched
    #     between two very loose ones. The runner should optimise each
    #     in turn without producing overlap or shifting later segments
    #     into earlier ones.
    def test_cumulative_no_overlap(self):
        easy_left = _make_seg(0.0, 8.0, ratio=0.20)        # very loose
        tight_a = _make_seg(8.0, 9.5, ratio=1.80)
        tight_b = _make_seg(9.5, 11.0, ratio=1.80)
        tight_c = _make_seg(11.0, 12.5, ratio=1.80)
        easy_right = _make_seg(12.5, 20.0, ratio=0.20)     # very loose
        out = expand_tight_slots(
            [easy_left, tight_a, tight_b, tight_c, easy_right], "it",
            min_gap_keep_s=0.15, max_neighbor_steal_s=0.5,
        )
        # Sanity: timestamps remain sorted and non-overlapping.
        for k in range(len(out) - 1):
            self.assertLessEqual(out[k]["end"], out[k + 1]["start"] + 1e-6,
                                 f"overlap at index {k}: {out[k]} / {out[k+1]}")
            self.assertLess(out[k]["start"], out[k]["end"],
                            f"non-positive slot at {k}: {out[k]}")
        # Bidirectional should expand more segments than unidirectional.
        out_uni = expand_tight_slots(
            [easy_left, tight_a, tight_b, tight_c, easy_right], "it",
            min_gap_keep_s=0.15, max_neighbor_steal_s=0.5,
            bidirectional=False,
        )
        def _grew(orig, res):
            return sum(
                1 for a, b in zip(orig, res)
                if (b["end"] - b["start"]) > (a["end"] - a["start"]) + 1e-6
            )
        n_bi = _grew([easy_left, tight_a, tight_b, tight_c, easy_right], out)
        n_uni = _grew([easy_left, tight_a, tight_b, tight_c, easy_right], out_uni)
        self.assertGreaterEqual(n_bi, n_uni)

    # 19. Edge: first segment never triggers Step 1b nor 2b (no [i-1]).
    def test_first_segment_no_backward_steps(self):
        tight_first = _make_seg(0.0, 2.0, ratio=2.00)
        easy_next = _make_seg(2.0, 8.0, ratio=0.30)
        out = expand_tight_slots(
            [tight_first, easy_next], "it",
            min_gap_keep_s=0.15, max_neighbor_steal_s=0.5,
        )
        # First should still expand (Step 2 forward) but never get start<0.
        self.assertGreaterEqual(out[0]["start"], 0.0)
        self.assertAlmostEqual(out[0]["start"], 0.0, places=5)

    # 20. Edge: last segment was a no-op pre-2O (only Step 1+2 forward),
    #     post-2O it can use Step 1b / 2b if a backward path exists.
    def test_last_segment_now_uses_backward_steps(self):
        # Use a non-easy first segment so only Step 1b (gap) fires, not 2b.
        # That isolates the backward gap stealing assertion cleanly.
        non_easy_first = _make_seg(0.0, 6.0, ratio=1.20)  # not easy
        tight_last = _make_seg(6.5, 8.5, ratio=1.80)      # 0.5s back-gap
        out = expand_tight_slots(
            [non_easy_first, tight_last], "it",
            min_gap_keep_s=0.15, max_neighbor_steal_s=0.5,
            neighbor_easy_ratio=0.80,
        )
        # Step 1b: back gap=0.5 → steal min(0.5-0.15, 1.5) = 0.35s.
        # After: slot=2.35, ratio=1.80*2/2.35≈1.53 still > 1.50 (tight).
        # Step 2b: previous ratio=1.20 not < 0.80 → no borrow.
        self.assertAlmostEqual(out[1]["start"], 6.5 - 0.35, places=5)
        self.assertAlmostEqual(out[1]["end"], 8.5, places=5)
        # First segment end unchanged (gap-stealing doesn't move neighbour).
        self.assertAlmostEqual(out[0]["end"], 6.0, places=5)


if __name__ == "__main__":
    unittest.main()
