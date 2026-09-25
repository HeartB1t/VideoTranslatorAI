"""Pure tests for the movable-panels helpers (no display needed)."""
import unittest

from videotranslator.ui_layout import (
    PANEL_IDS, RIGHT_COLUMN_MIN_WIDTH, WheelAccumulator, drop_index,
    move_panel, normalize_panel_order, right_column_width,
)

DEFAULT = list(PANEL_IDS)


class NormalizePanelOrderTests(unittest.TestCase):
    def test_default_when_missing_or_wrong_type(self):
        for value in (None, "", 3, {"a": 1}, "input"):
            with self.subTest(value=value):
                self.assertEqual(normalize_panel_order(value), DEFAULT)

    def test_full_valid_order_is_kept(self):
        order = ["start", "settings", "input", "profile", "translation"]
        self.assertEqual(normalize_panel_order(order), order)
        self.assertEqual(normalize_panel_order(tuple(order)), order)

    def test_partial_order_is_completed_in_default_order(self):
        self.assertEqual(normalize_panel_order(["start", "input"]),
                         ["start", "input", "translation", "profile", "settings"])

    def test_unknown_duplicates_and_non_strings_are_dropped(self):
        value = ["start", "bogus", "start", 7, None, "input", "input"]
        self.assertEqual(normalize_panel_order(value),
                         ["start", "input", "translation", "profile", "settings"])

    def test_result_always_has_every_id_once(self):
        for value in ([], ["settings"], DEFAULT[::-1], ["x", "y"]):
            with self.subTest(value=value):
                out = normalize_panel_order(value)
                self.assertEqual(sorted(out), sorted(DEFAULT))
                self.assertEqual(len(out), len(set(out)))


class MovePanelTests(unittest.TestCase):
    def test_move_to_start_and_end(self):
        self.assertEqual(move_panel(DEFAULT, "start", 0),
                         ["start", "input", "translation", "profile", "settings"])
        self.assertEqual(move_panel(DEFAULT, "input", 4),
                         ["translation", "profile", "start", "settings", "input"])

    def test_index_counts_positions_without_the_moved_panel(self):
        # "input" removed -> [translation, profile, start, settings];
        # index 2 puts it between profile and start.
        self.assertEqual(move_panel(DEFAULT, "input", 2),
                         ["translation", "profile", "input", "start", "settings"])

    def test_index_is_clamped(self):
        self.assertEqual(move_panel(DEFAULT, "settings", -5)[0], "settings")
        self.assertEqual(move_panel(DEFAULT, "input", 99)[-1], "input")

    def test_unknown_panel_returns_a_copy(self):
        out = move_panel(DEFAULT, "bogus", 1)
        self.assertEqual(out, DEFAULT)
        self.assertIsNot(out, DEFAULT)

    def test_does_not_mutate_the_input(self):
        order = list(DEFAULT)
        move_panel(order, "start", 0)
        self.assertEqual(order, DEFAULT)


class DropIndexTests(unittest.TestCase):
    SPANS = [(0, 100), (100, 200), (200, 300), (300, 400)]

    def test_above_the_first_panel(self):
        self.assertEqual(drop_index(-10, self.SPANS), 0)
        self.assertEqual(drop_index(40, self.SPANS), 0)

    def test_between_panels(self):
        self.assertEqual(drop_index(60, self.SPANS), 1)
        self.assertEqual(drop_index(151, self.SPANS), 2)
        self.assertEqual(drop_index(250, self.SPANS), 2)

    def test_below_the_last_panel(self):
        self.assertEqual(drop_index(351, self.SPANS), 4)
        self.assertEqual(drop_index(9999, self.SPANS), 4)

    def test_exact_midpoint_means_before(self):
        self.assertEqual(drop_index(50, self.SPANS), 0)
        self.assertEqual(drop_index(150, self.SPANS), 1)

    def test_no_spans(self):
        self.assertEqual(drop_index(123, []), 0)


class RightColumnWidthTests(unittest.TestCase):
    def test_never_below_the_minimum(self):
        self.assertEqual(RIGHT_COLUMN_MIN_WIDTH, 460)
        for asked in (0, 1, 300, 459, 460):
            with self.subTest(asked=asked):
                self.assertEqual(right_column_width(asked), 460)

    def test_widens_when_the_cards_ask_for_more(self):
        self.assertEqual(right_column_width(461), 461)
        self.assertEqual(right_column_width(530), 530)


class WheelAccumulatorTests(unittest.TestCase):
    """Scroll units per wheel event: positive down, negative up."""

    def test_x11_buttons_are_one_notch_each(self):
        # Tk 8.6 on X11: button 4 is the wheel turned up, button 5 down.
        wheel = WheelAccumulator()
        self.assertEqual(wheel.feed(4, 0), -1)
        self.assertEqual(wheel.feed(5, 0), 1)
        self.assertEqual(wheel.feed(5, 0), 1)

    def test_whole_notches_on_windows(self):
        # Windows and Tk 8.7+ on X11: +120 per notch up, -120 per notch down.
        for delta, units in ((120, -1), (-120, 1), (240, -2), (-360, 3)):
            with self.subTest(delta=delta):
                self.assertEqual(WheelAccumulator().feed("??", delta), units)

    def test_small_touchpad_deltas_add_up_to_one_notch(self):
        # Windows precision touchpads send many small deltas per gesture:
        # one unit per 120 accumulated, never one unit per event.
        wheel = WheelAccumulator()
        self.assertEqual([wheel.feed("??", -40) for _ in range(6)],
                         [0, 0, 1, 0, 0, 1])
        self.assertEqual(wheel.feed("??", -100), 0)
        self.assertEqual(wheel.feed("??", -30), 1)  # 130 accumulated

    def test_turning_back_drops_the_other_direction(self):
        wheel = WheelAccumulator()
        self.assertEqual(wheel.feed("??", -100), 0)
        # The residue of the downward gesture must not delay the upward one.
        self.assertEqual(wheel.feed("??", 120), -1)
        self.assertEqual(wheel.feed("??", 60), 0)
        self.assertEqual(wheel.feed(5, 0), 1)  # a button resets the residue
        self.assertEqual(wheel.feed("??", 60), 0)

    def test_no_wheel_no_scroll(self):
        wheel = WheelAccumulator()
        for num, delta in ((1, 0), ("??", 0), (None, None), ("??", "x")):
            with self.subTest(num=num, delta=delta):
                self.assertEqual(wheel.feed(num, delta), 0)


if __name__ == "__main__":
    unittest.main()
