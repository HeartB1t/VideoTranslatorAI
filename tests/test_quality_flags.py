"""Unit tests for ``videotranslator.quality_flags`` (TASK 5C).

Pure tests for the per-segment quality flag helpers used by the
subtitle editor to surface candidates for human review (length unfit,
Whisper suspicious tokens, translation fallback).
"""

from __future__ import annotations

import unittest

from videotranslator.quality_flags import (
    FLAG_LENGTH_UNFIT,
    FLAG_TRANSLATION_FALLBACK,
    FLAG_WHISPER_SUSPICIOUS,
    QUALITY_FLAG_COLOURS,
    add_quality_flag,
    compute_segment_quality_flags,
    has_any_flag,
    primary_flag,
)


class AddQualityFlagTests(unittest.TestCase):
    def test_adds_first_flag(self) -> None:
        seg: dict = {"start": 0.0, "end": 1.0, "text_tgt": "x"}
        add_quality_flag(seg, FLAG_LENGTH_UNFIT)
        self.assertEqual(seg["_quality_flags"], [FLAG_LENGTH_UNFIT])

    def test_appends_distinct_flag(self) -> None:
        seg: dict = {}
        add_quality_flag(seg, FLAG_LENGTH_UNFIT)
        add_quality_flag(seg, FLAG_WHISPER_SUSPICIOUS)
        self.assertEqual(
            seg["_quality_flags"],
            [FLAG_LENGTH_UNFIT, FLAG_WHISPER_SUSPICIOUS],
        )

    def test_dedup_same_flag(self) -> None:
        seg: dict = {}
        add_quality_flag(seg, FLAG_LENGTH_UNFIT)
        add_quality_flag(seg, FLAG_LENGTH_UNFIT)
        self.assertEqual(seg["_quality_flags"], [FLAG_LENGTH_UNFIT])

    def test_empty_flag_is_noop(self) -> None:
        seg: dict = {}
        add_quality_flag(seg, "")
        add_quality_flag(seg, None)  # type: ignore[arg-type]
        # No key should be initialised when no real flag has been added.
        self.assertNotIn("_quality_flags", seg)

    def test_non_dict_segment_silently_ignored(self) -> None:
        # Defensive contract: pipeline stages may pass through wrong types
        # (e.g. a stringified row from a CSV); the helper must not crash.
        add_quality_flag("not a dict", FLAG_LENGTH_UNFIT)  # type: ignore[arg-type]
        # Reaching here means no exception — pass.

    def test_corrupted_existing_value_replaced(self) -> None:
        # A previous version of the codebase may have set _quality_flags
        # to a non-list (e.g. a string). The helper must reset it cleanly
        # rather than crash on .append.
        seg: dict = {"_quality_flags": "broken"}
        add_quality_flag(seg, FLAG_LENGTH_UNFIT)
        self.assertEqual(seg["_quality_flags"], [FLAG_LENGTH_UNFIT])


class ComputeSegmentQualityFlagsTests(unittest.TestCase):
    def test_no_flag_returns_empty_list(self) -> None:
        self.assertEqual(compute_segment_quality_flags({}), [])
        self.assertEqual(
            compute_segment_quality_flags({"text_tgt": "ok"}), [],
        )

    def test_returns_copy_not_reference(self) -> None:
        seg: dict = {"_quality_flags": [FLAG_LENGTH_UNFIT]}
        out = compute_segment_quality_flags(seg)
        out.append("garbage")
        # Mutating the copy must not affect the segment state.
        self.assertEqual(seg["_quality_flags"], [FLAG_LENGTH_UNFIT])

    def test_filters_garbage_entries(self) -> None:
        seg: dict = {"_quality_flags": [FLAG_LENGTH_UNFIT, "", None, 42]}
        self.assertEqual(
            compute_segment_quality_flags(seg),
            [FLAG_LENGTH_UNFIT],
        )

    def test_non_dict_returns_empty(self) -> None:
        self.assertEqual(compute_segment_quality_flags(None), [])  # type: ignore[arg-type]
        self.assertEqual(compute_segment_quality_flags("x"), [])  # type: ignore[arg-type]


class PrimaryFlagTests(unittest.TestCase):
    def test_empty_returns_none(self) -> None:
        self.assertIsNone(primary_flag([]))
        self.assertIsNone(primary_flag(None))  # type: ignore[arg-type]

    def test_unknown_only_returns_none(self) -> None:
        self.assertIsNone(primary_flag(["totally_made_up"]))

    def test_priority_fallback_beats_length(self) -> None:
        # translation_fallback is the most severe.
        self.assertEqual(
            primary_flag([FLAG_LENGTH_UNFIT, FLAG_TRANSLATION_FALLBACK]),
            FLAG_TRANSLATION_FALLBACK,
        )

    def test_priority_length_beats_whisper(self) -> None:
        self.assertEqual(
            primary_flag([FLAG_WHISPER_SUSPICIOUS, FLAG_LENGTH_UNFIT]),
            FLAG_LENGTH_UNFIT,
        )

    def test_single_flag_returned(self) -> None:
        self.assertEqual(
            primary_flag([FLAG_WHISPER_SUSPICIOUS]),
            FLAG_WHISPER_SUSPICIOUS,
        )


class HasAnyFlagTests(unittest.TestCase):
    def test_true_when_flagged(self) -> None:
        self.assertTrue(has_any_flag({"_quality_flags": [FLAG_LENGTH_UNFIT]}))

    def test_false_when_no_key(self) -> None:
        self.assertFalse(has_any_flag({"text_tgt": "x"}))

    def test_false_when_only_garbage(self) -> None:
        self.assertFalse(has_any_flag({"_quality_flags": ["", None]}))


class ColourTableTests(unittest.TestCase):
    def test_all_flags_have_colours(self) -> None:
        for flag in (
            FLAG_TRANSLATION_FALLBACK,
            FLAG_LENGTH_UNFIT,
            FLAG_WHISPER_SUSPICIOUS,
        ):
            self.assertIn(flag, QUALITY_FLAG_COLOURS)
            colours = QUALITY_FLAG_COLOURS[flag]
            self.assertIn("background", colours)
            self.assertIn("foreground", colours)
            # Hex format check: must start with '#' and be 7 chars.
            self.assertTrue(colours["background"].startswith("#"))
            self.assertEqual(len(colours["background"]), 7)
            self.assertTrue(colours["foreground"].startswith("#"))
            self.assertEqual(len(colours["foreground"]), 7)


if __name__ == "__main__":
    unittest.main()
