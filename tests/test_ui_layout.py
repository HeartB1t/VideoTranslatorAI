"""Pure tests for the movable-panels helpers (no display needed)."""
import unittest

from videotranslator.ui_layout import (
    PANEL_IDS, drop_index, move_panel, normalize_panel_order,
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


if __name__ == "__main__":
    unittest.main()
