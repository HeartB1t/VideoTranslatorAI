"""The header's settings gear, drawn by the app instead of the "⚙" glyph.

On Windows the system font drew "⚙" as a thin, uneven outline; the gear is
now rasterised in pure Python, anti-aliased and blended over the header
background, the same on Linux and Windows.
"""
import math
import unittest

from videotranslator import gear_icon
from videotranslator.ui_theme import mix

FG, BG = "#dfe1e5", "#1e1f22"


class GearShapeTests(unittest.TestCase):
    def test_the_outline_has_eight_teeth_round_the_centre(self):
        outline = gear_icon.gear_outline()
        self.assertEqual(len(outline), gear_icon.TEETH * 5)
        radii = [math.hypot(x - 0.5, y - 0.5) for x, y in outline]
        self.assertAlmostEqual(max(radii), 0.47, places=6)          # tooth tips
        self.assertAlmostEqual(min(radii), 0.35, places=6)          # between the teeth
        self.assertTrue(all(0 <= v <= 1 for point in outline for v in point))

    def test_coverage_is_solid_in_the_body_empty_in_the_hole_and_outside(self):
        size = 40
        cover = gear_icon.gear_coverage(size)
        self.assertEqual(len(cover), size)
        self.assertTrue(all(len(row) == size for row in cover))
        middle = size // 2
        self.assertEqual(cover[middle][middle], 0.0)                 # the hole
        self.assertEqual(cover[middle][round(size * 0.25)], 1.0)     # the solid ring
        self.assertEqual(cover[0][0], 0.0)                           # a corner
        self.assertGreater(cover[round(size * 0.06)][middle], 0.5)   # the top tooth

    def test_edges_are_smoothed_and_the_gear_is_symmetric(self):
        cover = gear_icon.gear_coverage(24)
        values = {value for row in cover for value in row}
        self.assertTrue(any(0 < value < 1 for value in values))      # anti-aliased
        # Eight teeth: a quarter turn gives the same gear.
        rotated = [[cover[24 - 1 - x][y] for x in range(24)] for y in range(24)]
        diff = max(abs(a - b) for r1, r2 in zip(cover, rotated) for a, b in zip(r1, r2))
        self.assertLess(diff, 0.2)

    def test_pixels_blend_the_colour_over_the_background_by_coverage(self):
        size = 20
        pixels = gear_icon.gear_pixels(size, FG, BG)
        cover = gear_icon.gear_coverage(size)
        for y in (0, 3, size // 2):
            for x in (0, 5, size // 2):
                with self.subTest(x=x, y=y):
                    self.assertEqual(pixels[y][x], mix(FG, BG, cover[y][x]))
        self.assertEqual(pixels[size // 2][size // 2], BG)           # the hole shows the header

    def test_coverage_is_cached_per_size(self):
        self.assertIs(gear_icon.gear_coverage(22), gear_icon.gear_coverage(22))


class GearImageTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display: {exc}")
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_image_has_the_size_and_the_colours(self):
        image = gear_icon.gear_image(self.root, 22, FG, BG)
        self.assertEqual((image.width(), image.height()), (22, 22))
        self.assertEqual("#%02x%02x%02x" % image.get(0, 0), BG)
        self.assertEqual("#%02x%02x%02x" % image.get(11, 11), BG)            # hole
        solid = gear_icon.gear_coverage(22)[11].index(1.0)
        self.assertEqual("#%02x%02x%02x" % image.get(solid, 11), FG)


class HeaderGearTests(unittest.TestCase):
    def setUp(self):
        from test_ui_theme_tk import HAS_DISPLAY
        if not HAS_DISPLAY:
            self.skipTest("needs a display (Tk)")

    def test_the_header_shows_the_drawn_gear_and_repaints_it_on_hover_and_theme(self):
        from test_ui_theme_tk import built_app
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            gear = app._btn_settings

            def shown():
                images = {str(img): img for img in app._gear_images.values()}
                return images[str(gear.cget("image"))]

            app.deiconify()                 # pointer events reach mapped widgets only
            app.update()
            self.assertEqual(gear.cget("text"), "")
            idle = shown()
            self.assertEqual("#%02x%02x%02x" % idle.get(0, 0), app._theme.palette.BG)
            gear.event_generate("<Enter>")
            self.assertIsNot(shown(), idle)
            gear.event_generate("<Leave>")
            self.assertIs(shown(), idle)
            app._ui_theme_var.set("light")
            app._apply_ui_settings()
            light = app._theme.palette
            self.assertEqual(light.name, "light")
            self.assertEqual("#%02x%02x%02x" % shown().get(0, 0), light.BG)


if __name__ == "__main__":
    unittest.main()
