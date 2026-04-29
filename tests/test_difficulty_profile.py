"""Unit tests for the difficulty-aware profile orchestrator.

The runtime decisions live in ``video_translator_gui.translate_video``
(profile resolution + parameter wiring) but the *policy* — which knobs
move when a video is classified easy / medium / hard — is exercised
here as a pure function. No I/O, no subprocess.
"""

import dataclasses
import unittest

from videotranslator.difficulty_profile import (
    EASY,
    HARD,
    MEDIUM,
    PROFILES,
    Profile,
    format_profile_log,
    resolve_profile,
)


class ResolveProfileTests(unittest.TestCase):
    def test_easy_resolves_to_easy(self):
        self.assertIs(resolve_profile("easy"), EASY)

    def test_medium_resolves_to_medium(self):
        self.assertIs(resolve_profile("medium"), MEDIUM)

    def test_hard_resolves_to_hard(self):
        self.assertIs(resolve_profile("hard"), HARD)

    def test_unknown_classification_falls_back_to_medium(self):
        self.assertIs(resolve_profile("unknown"), MEDIUM)
        self.assertIs(resolve_profile("HARDER"), MEDIUM)

    def test_empty_or_none_falls_back_to_medium(self):
        self.assertIs(resolve_profile(""), MEDIUM)
        self.assertIs(resolve_profile(None), MEDIUM)

    def test_classification_is_case_insensitive(self):
        # The runtime always passes lowercase, but a CLI override (e.g.
        # --difficulty-override HARD) should not silently fall through
        # to MEDIUM just because of casing.
        self.assertIs(resolve_profile("EASY"), EASY)
        self.assertIs(resolve_profile("Hard"), HARD)


class ProfileImmutabilityTests(unittest.TestCase):
    def test_profile_is_frozen(self):
        # dataclass(frozen=True) raises FrozenInstanceError (subclass of
        # AttributeError). Catching AttributeError keeps the test
        # tolerant to internal dataclass refactors.
        with self.assertRaises((AttributeError, dataclasses.FrozenInstanceError)):
            EASY.atempo_cap = 99.0  # type: ignore[misc]

    def test_profiles_dict_contains_all_three_classes(self):
        self.assertEqual(set(PROFILES.keys()), {"easy", "medium", "hard"})


class ProfileMonotonicityTests(unittest.TestCase):
    """HARD must be strictly more aggressive than MEDIUM, EASY strictly
    more conservative. These invariants guard against accidental
    regressions if someone tunes a single number without re-checking
    the full triplet."""

    def test_hard_more_aggressive_than_medium_on_retry(self):
        # Lower threshold = catches more overshoots = more aggressive.
        self.assertLess(
            HARD.length_retry_threshold, MEDIUM.length_retry_threshold
        )
        self.assertGreater(
            HARD.length_retry_max_iter, MEDIUM.length_retry_max_iter
        )

    def test_hard_more_aggressive_than_medium_on_stretch(self):
        # Higher cap = more compression headroom on dense videos.
        self.assertGreater(HARD.atempo_cap, MEDIUM.atempo_cap)
        # Wider rubberband window = stays on the high-quality engine
        # for higher ratios before falling back to atempo.
        self.assertGreater(HARD.rubberband_max, MEDIUM.rubberband_max)
        # Higher XTTS cap = synthesis absorbs more of the compression.
        self.assertGreater(HARD.xtts_speed_cap, MEDIUM.xtts_speed_cap)

    def test_easy_more_conservative_than_medium(self):
        self.assertGreater(
            EASY.length_retry_threshold, MEDIUM.length_retry_threshold
        )
        self.assertLessEqual(
            EASY.length_retry_max_iter, MEDIUM.length_retry_max_iter
        )
        self.assertLess(EASY.atempo_cap, MEDIUM.atempo_cap)
        self.assertLessEqual(EASY.rubberband_max, MEDIUM.rubberband_max)
        self.assertLess(EASY.xtts_speed_cap, MEDIUM.xtts_speed_cap)

    def test_medium_matches_legacy_constants(self):
        # MEDIUM must reproduce the v1.7 / pre-2G v2 hard-coded values
        # so --no-difficulty-profile (and unknown classifications) get
        # exact behavioural parity with the legacy code path.
        self.assertAlmostEqual(MEDIUM.length_retry_threshold, 1.10)
        self.assertEqual(MEDIUM.length_retry_max_iter, 1)
        self.assertAlmostEqual(MEDIUM.atempo_cap, 4.0)
        self.assertAlmostEqual(MEDIUM.rubberband_min, 1.15)
        self.assertAlmostEqual(MEDIUM.rubberband_max, 1.50)
        self.assertAlmostEqual(MEDIUM.xtts_speed_cap, 1.35)


class FormatProfileLogTests(unittest.TestCase):
    def test_message_uppercases_classification(self):
        msg = format_profile_log("hard", HARD, 2.43)
        self.assertIn("HARD", msg)

    def test_message_includes_p90(self):
        msg = format_profile_log("medium", MEDIUM, 1.50)
        self.assertIn("1.50", msg)

    def test_message_includes_all_profile_numbers(self):
        msg = format_profile_log("hard", HARD, 2.0)
        # Spot-check every knob shows up in the rendered log so a
        # future refactor that drops a field gets caught here.
        self.assertIn(str(HARD.length_retry_threshold), msg)
        self.assertIn(str(HARD.atempo_cap), msg)
        self.assertIn(str(HARD.rubberband_min), msg)
        self.assertIn(str(HARD.rubberband_max), msg)
        self.assertIn(str(HARD.xtts_speed_cap), msg)

    def test_message_starts_with_difficulty_tag(self):
        # The log line is grouped with the existing [difficulty] banner
        # in translate_video output; the tag is the grep marker users
        # rely on in bug reports.
        msg = format_profile_log("easy", EASY, 1.0)
        self.assertTrue(msg.startswith("[difficulty]"))


class ProfileTypeTests(unittest.TestCase):
    def test_all_profiles_are_profile_instances(self):
        for name, profile in PROFILES.items():
            with self.subTest(name=name):
                self.assertIsInstance(profile, Profile)


if __name__ == "__main__":
    unittest.main()
