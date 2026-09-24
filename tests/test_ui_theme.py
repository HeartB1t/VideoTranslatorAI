import itertools
import subprocess
import unittest
from unittest import mock

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

    def test_non_string_theme_or_accent_fall_back(self):
        # A non-string accent (e.g. a stray list from bad config) must not
        # raise: "accent in ACCENTS" only runs after an isinstance guard.
        self.assertEqual(resolve_palette("graphite", ["blue"]).ACC, resolve_palette("graphite").ACC)
        self.assertEqual(resolve_palette(None).name, DEFAULT_THEME)

    def test_font_family_role(self):
        self.assertEqual(resolve_palette("neon").font_family, "mono")
        self.assertEqual(resolve_palette("graphite").font_family, "sans")
        self.assertTrue(resolve_palette("light").dark is False)


class AccentForegroundTests(unittest.TestCase):
    """Regression coverage for the >=4.0 white-text preference (fix round 1, item 6)."""

    def test_graphite_accent_prefers_white_text(self):
        # #3574f0: white contrast is 4.28 (clears the 4.0 floor), black is
        # 4.91. White wins despite scoring a hair lower, matching the
        # approved UI mockup where the primary button shows white text.
        self.assertEqual(resolve_palette("graphite").ACC_FG, "#ffffff")

    def test_slate_accent_keeps_black_text_below_threshold(self):
        # #2aa198 (teal): white contrast is only ~3.16, below the 4.0 floor,
        # so the highest-contrast rule applies and black (~6.65) wins.
        self.assertEqual(resolve_palette("slate").ACC_FG, "#000000")

    def test_amber_accent_keeps_black_text(self):
        # #d9932a: white contrast is ~2.57, well below the 4.0 floor; black
        # (~8.16) wins under both the old and the new rule.
        self.assertEqual(resolve_palette("graphite", "amber").ACC_FG, "#000000")


class EnsureDistinctTests(unittest.TestCase):
    def test_terminates_and_returns_distinct_values(self):
        # "#000000" and "#000001" are both already taken, so the third
        # duplicate must walk past both before finding a free value. This
        # must terminate (fix round 1, item 1: no more infinite +-1 loop).
        result = ui_theme._ensure_distinct({"a": "#000000", "b": "#000001", "c": "#000000"})
        self.assertEqual(len(result), 3)
        self.assertEqual(len(set(result.values())), 3)
        self.assertEqual(result["a"], "#000000")
        self.assertEqual(result["b"], "#000001")
        self.assertEqual(result["c"], "#000002")


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


class DetectSystemDarkTests(unittest.TestCase):
    def _runner(self, table):
        """Build a fake runner: command tuple -> (rc, stdout) or None."""
        calls = []

        def run(cmd):
            calls.append(list(cmd))
            return table.get(tuple(cmd))
        run.calls = calls
        return run

    def test_linux_prefer_dark(self):
        # env={} pins the non-XFCE order (gsettings first) regardless of the
        # host this suite runs on (this dev box's own XDG_CURRENT_DESKTOP is
        # XFCE, see fix round 1 item 4).
        run = self._runner({
            ("gsettings", "get", "org.gnome.desktop.interface", "color-scheme"): (0, "'prefer-dark'\n"),
        })
        self.assertIs(ui_theme.detect_system_dark("linux", runner=run, env={}), True)

    def test_linux_prefer_light(self):
        run = self._runner({
            ("gsettings", "get", "org.gnome.desktop.interface", "color-scheme"): (0, "'prefer-light'\n"),
        })
        self.assertIs(ui_theme.detect_system_dark("linux", runner=run, env={}), False)

    def test_linux_falls_back_to_gtk_theme_name(self):
        run = self._runner({
            ("gsettings", "get", "org.gnome.desktop.interface", "color-scheme"): (0, "'default'\n"),
            ("gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"): (0, "'Kali-Dark'\n"),
        })
        self.assertIs(ui_theme.detect_system_dark("linux", runner=run, env={}), True)

    def test_linux_falls_back_to_xfconf(self):
        run = self._runner({
            ("xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"): (0, "Adwaita\n"),
        })
        self.assertIs(ui_theme.detect_system_dark("linux", runner=run, env={}), False)

    def test_linux_nothing_available_is_unknown(self):
        run = self._runner({})
        self.assertIsNone(ui_theme.detect_system_dark("linux", runner=run, env={}))

    def test_linux_color_scheme_nonzero_falls_back(self):
        # (a) gsettings color-scheme exits non-zero (no schema / no daemon):
        # must fall through to the next check instead of stopping.
        run = self._runner({
            ("gsettings", "get", "org.gnome.desktop.interface", "color-scheme"): (1, ""),
            ("gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"): (0, "'Kali-Dark'\n"),
        })
        self.assertIs(ui_theme.detect_system_dark("linux", runner=run, env={}), True)

    def test_linux_gtk_theme_empty_falls_back_to_xfconf(self):
        # (b) gtk-theme returns rc=0 but an empty string: must fall through
        # to xfconf rather than treating empty as a theme name.
        run = self._runner({
            ("gsettings", "get", "org.gnome.desktop.interface", "color-scheme"): (0, "'default'\n"),
            ("gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"): (0, ""),
            ("xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"): (0, "Kali-Dark\n"),
        })
        self.assertIs(ui_theme.detect_system_dark("linux", runner=run, env={}), True)

    def test_linux_fallback_order_when_not_xfce(self):
        # (e) order check: color-scheme, then gtk-theme, then xfconf, when
        # XDG_CURRENT_DESKTOP does not mention XFCE.
        run = self._runner({})
        ui_theme.detect_system_dark("linux", runner=run, env={"XDG_CURRENT_DESKTOP": "GNOME"})
        self.assertEqual(run.calls, [
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"],
        ])

    def test_linux_xfce_checks_xfconf_first(self):
        # Fix round 1, item 4: on an XFCE session, xfconf is authoritative
        # and gsettings is often absent or stale, so it goes first.
        run = self._runner({
            ("xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"): (0, "Kali-Dark\n"),
            ("gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"): (0, "'Adwaita'\n"),
        })
        result = ui_theme.detect_system_dark("linux", runner=run, env={"XDG_CURRENT_DESKTOP": "XFCE"})
        self.assertIs(result, True)
        self.assertEqual(run.calls[0], ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"])

    def test_linux_xfce_detection_is_case_insensitive(self):
        run = self._runner({
            ("xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"): (0, "Adwaita\n"),
        })
        ui_theme.detect_system_dark("linux", runner=run, env={"XDG_CURRENT_DESKTOP": "xfce"})
        self.assertEqual(run.calls[0], ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"])

    def test_macos_dark_and_light(self):
        dark = self._runner({("defaults", "read", "-g", "AppleInterfaceStyle"): (0, "Dark\n")})
        light = self._runner({("defaults", "read", "-g", "AppleInterfaceStyle"): (1, "")})
        self.assertIs(ui_theme.detect_system_dark("darwin", runner=dark), True)
        self.assertIs(ui_theme.detect_system_dark("darwin", runner=light), False)

    def test_macos_runner_returns_none_is_unknown(self):
        # (c) the command is simply not in the fake runner's table.
        run = self._runner({})
        self.assertIsNone(ui_theme.detect_system_dark("darwin", runner=run))

    def test_windows_registry(self):
        class FakeKey:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        class FakeWinreg:
            HKEY_CURRENT_USER = object()

            def __init__(self, value):
                self._value = value

            def OpenKey(self, root, path):
                return FakeKey()

            def QueryValueEx(self, key, name):
                return (self._value, 4)

        self.assertIs(ui_theme.detect_system_dark("win32", winreg_module=FakeWinreg(0)), True)
        self.assertIs(ui_theme.detect_system_dark("win32", winreg_module=FakeWinreg(1)), False)

    def test_windows_registry_error_is_unknown(self):
        class Broken:
            HKEY_CURRENT_USER = object()

            def OpenKey(self, root, path):
                raise OSError("no key")

        self.assertIsNone(ui_theme.detect_system_dark("win32", winreg_module=Broken()))

    def test_run_quiet_handles_missing_binary(self):
        self.assertIsNone(ui_theme._run_quiet(["definitely-not-a-real-binary-xyz"]))

    def test_run_quiet_handles_timeout(self):
        # (d) subprocess.TimeoutExpired is a SubprocessError subclass, so
        # the existing except clause already covers it; this pins that.
        timeout_error = subprocess.TimeoutExpired(cmd=["slow"], timeout=2)
        with mock.patch("videotranslator.ui_theme.subprocess.run", side_effect=timeout_error):
            self.assertIsNone(ui_theme._run_quiet(["slow"]))


if __name__ == "__main__":
    unittest.main()
