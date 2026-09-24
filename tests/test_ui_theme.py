import itertools
import unittest

from videotranslator import ui_theme
from videotranslator.ui_theme import (
    ACCENT_CHOICES,
    DEFAULT_ACCENT,
    DEFAULT_LANG,
    DEFAULT_SCALE,
    DEFAULT_THEME,
    Palette,
    SCALES,
    THEME_CHOICES,
    contrast_ratio,
    derive_accent,
    normalize_ui_settings,
    resolve_palette,
)

CONCRETE_THEMES = [t for t in THEME_CHOICES if t != "auto"]


class ContrastTests(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0, places=1)

    def test_symmetry(self):
        self.assertAlmostEqual(
            contrast_ratio("#3574f0", "#1e1f22"), contrast_ratio("#1e1f22", "#3574f0"))

    def test_same_colour_is_1(self):
        self.assertAlmostEqual(contrast_ratio("#808080", "#808080"), 1.0, places=6)


class DeriveAccentTests(unittest.TestCase):
    def test_returns_four_lower_hex_values(self):
        for value in derive_accent("#3574F0", "#2b2d30", dark=True):
            self.assertRegex(value, r"^#[0-9a-f]{6}$")

    def test_dark_theme_hover_is_lighter_light_theme_hover_is_darker(self):
        _, hover_dark, _, _ = derive_accent("#3574f0", "#2b2d30", dark=True)
        _, hover_light, _, _ = derive_accent("#3574f0", "#ffffff", dark=False)
        lum = ui_theme.relative_luminance
        self.assertGreater(lum(hover_dark), lum("#3574f0"))
        self.assertLess(lum(hover_light), lum("#3574f0"))

    def test_fg_picks_highest_contrast(self):
        _, _, _, fg_on_blue = derive_accent("#2563eb", "#ffffff", dark=False)
        _, _, _, fg_on_amber = derive_accent("#d9932a", "#ffffff", dark=False)
        self.assertEqual(fg_on_blue, "#ffffff")
        self.assertEqual(fg_on_amber, "#000000")

    def test_soft_is_between_accent_and_surface(self):
        acc, _, soft, _ = derive_accent("#3574f0", "#2b2d30", dark=True)
        lum = ui_theme.relative_luminance
        self.assertTrue(min(lum(acc), lum("#2b2d30")) <= lum(soft) <= max(lum(acc), lum("#2b2d30")))


class ResolvePaletteTests(unittest.TestCase):
    def test_every_theme_and_accent_has_distinct_colours(self):
        for theme, accent in itertools.product(CONCRETE_THEMES, ACCENT_CHOICES):
            with self.subTest(theme=theme, accent=accent):
                colours = resolve_palette(theme, accent).colors()
                self.assertEqual(len(colours), len(Palette.COLOR_FIELDS))
                self.assertEqual(len(set(colours.values())), len(colours))
                for value in colours.values():
                    self.assertRegex(value, r"^#[0-9a-f]{6}$")

    def test_contrast_floors(self):
        for theme, accent in itertools.product(CONCRETE_THEMES, ACCENT_CHOICES):
            with self.subTest(theme=theme, accent=accent):
                p = resolve_palette(theme, accent)
                self.assertGreaterEqual(contrast_ratio(p.FG, p.BG), 4.5)
                self.assertGreaterEqual(contrast_ratio(p.FG, p.SURFACE), 4.5)
                self.assertGreaterEqual(contrast_ratio(p.FG2, p.SURFACE), 3.0)
                self.assertGreaterEqual(contrast_ratio(p.ACC_FG, p.ACC), 3.0)

    def test_default_accent_uses_theme_own_accent(self):
        self.assertEqual(resolve_palette("graphite", "default").ACC, "#3574f0")
        self.assertEqual(resolve_palette("slate", "default").ACC, "#2aa198")
        self.assertEqual(resolve_palette("neon", "default").ACC, "#00ff88")

    def test_named_accent_overrides(self):
        self.assertEqual(resolve_palette("graphite", "rose").ACC, ui_theme.ACCENTS["rose"])

    def test_auto_follows_system(self):
        self.assertEqual(resolve_palette("auto", system_dark=True).name, "graphite")
        self.assertEqual(resolve_palette("auto", system_dark=False).name, "light")
        self.assertEqual(resolve_palette("auto", system_dark=None).name, "graphite")

    def test_unknown_theme_or_accent_fall_back(self):
        p = resolve_palette("banana", "cyanmagenta")
        self.assertEqual(p.name, DEFAULT_THEME)
        self.assertEqual(p.ACC, resolve_palette(DEFAULT_THEME).ACC)

    def test_font_family_role(self):
        self.assertEqual(resolve_palette("neon").font_family, "mono")
        self.assertEqual(resolve_palette("graphite").font_family, "sans")
        self.assertTrue(resolve_palette("light").dark is False)


class NormalizeSettingsTests(unittest.TestCase):
    def test_defaults_when_missing(self):
        self.assertEqual(normalize_ui_settings({}), {
            "ui_theme": DEFAULT_THEME, "ui_accent": DEFAULT_ACCENT,
            "ui_scale": DEFAULT_SCALE, "ui_lang": DEFAULT_LANG})

    def test_defaults_when_wrong_types_or_unknown(self):
        cfg = {"ui_theme": 42, "ui_accent": ["blue"], "ui_scale": "huge", "ui_lang": None}
        self.assertEqual(normalize_ui_settings(cfg), normalize_ui_settings({}))

    def test_not_a_dict(self):
        self.assertEqual(normalize_ui_settings("nope"), normalize_ui_settings({}))

    def test_valid_values_pass_through(self):
        cfg = {"ui_theme": "slate", "ui_accent": "rose", "ui_scale": "large", "ui_lang": "fr"}
        self.assertEqual(normalize_ui_settings(cfg, lang_codes={"it", "en", "fr"}), cfg)

    def test_lang_validated_against_codes(self):
        out = normalize_ui_settings({"ui_lang": "xx"}, lang_codes={"it", "en"})
        self.assertEqual(out["ui_lang"], DEFAULT_LANG)

    def test_scales_are_sane(self):
        self.assertIn(DEFAULT_SCALE, SCALES)
        self.assertEqual(SCALES[DEFAULT_SCALE], 1.0)
        for v in SCALES.values():
            self.assertTrue(0.5 < v < 2.0)


if __name__ == "__main__":
    unittest.main()
