"""Raised key buttons (bevel_tk). Tk tests: skip without a display, run under Xvfb."""

import tkinter as tk
import unittest

from test_ui_theme_tk import HAS_DISPLAY
from videotranslator import bevel_tk
from videotranslator.ui_theme import bevel_colors, bevel_edges, resolve_palette


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class BevelButtonTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("+0+0")
        self.palette = resolve_palette("graphite")
        self.clicks = []

    def tearDown(self):
        self.root.destroy()

    def _button(self, **kw):
        options = dict(text="Go", bg=self.palette.BTN, fg=self.palette.FG,
                       activebackground=self.palette.BORDER,
                       command=lambda: self.clicks.append(1))
        options.update(kw)
        button = bevel_tk.BevelButton(self.root, palette_fn=lambda: self.palette, **options)
        button.pack(padx=10, pady=10)
        self.root.update()
        return button

    def _edges(self, button):
        return button._inner.cget("bg"), button.outer.cget("bg")

    def test_raised_edge_is_painted_from_the_face(self):
        button = self._button()
        raised = bevel_colors(self.palette.BTN)
        self.assertEqual(self._edges(button), (raised.top_left, raised.bottom_right))

    def test_the_bottom_edge_is_thicker_than_the_others(self):
        button = self._button()
        edge, depth = bevel_edges(self.palette)
        inner, outer = button._inner, button.outer
        self.assertEqual(button.winfo_x(), edge)                   # left edge
        self.assertEqual(button.winfo_y(), edge)                   # top edge
        self.assertEqual(outer.winfo_width() - inner.winfo_width(), edge)    # right
        self.assertEqual(outer.winfo_height() - inner.winfo_height(), depth)  # bottom

    def test_geometry_calls_place_the_whole_key(self):
        button = self._button()
        self.assertIn(button.outer, self.root.pack_slaves())
        self.assertNotIn(button, self.root.pack_slaves())
        self.assertEqual(button.pack_info()["padx"], 10)
        button.pack_forget()
        self.root.update()
        self.assertFalse(button.outer.winfo_ismapped())
        button.grid(row=0, column=0)
        self.assertEqual(button.outer.winfo_manager(), "grid")

    def test_press_sinks_the_key_and_release_still_runs_the_command(self):
        button = self._button()
        raised = self._edges(button)
        button.event_generate("<Enter>", x=5, y=5)
        button.event_generate("<ButtonPress-1>", x=5, y=5)
        self.root.update()
        hover = bevel_colors(self.palette.BORDER)
        self.assertEqual(self._edges(button), (hover.bottom_right, hover.top_left))
        button.event_generate("<ButtonRelease-1>", x=5, y=5)
        self.root.update()
        self.assertEqual(self._edges(button), (hover.top_left, hover.bottom_right))
        self.assertEqual(self.clicks, [1])
        button.event_generate("<Leave>")
        self.root.update()
        self.assertEqual(self._edges(button), raised)

    def test_disabled_key_keeps_a_faded_edge_and_does_not_sink(self):
        button = self._button()
        button.configure(state="disabled")
        faded = bevel_colors(self.palette.BTN, enabled=False)
        self.assertEqual(self._edges(button), (faded.top_left, faded.bottom_right))
        button.event_generate("<ButtonPress-1>", x=5, y=5)
        self.root.update()
        self.assertEqual(self._edges(button), (faded.top_left, faded.bottom_right))
        button["state"] = "normal"                     # item assignment repaints too
        raised = bevel_colors(self.palette.BTN)
        self.assertEqual(self._edges(button), (raised.top_left, raised.bottom_right))

    def test_selected_key_stays_sunk(self):
        button = self._button()
        button.configure(bg=self.palette.ACC_SOFT)
        button.set_selected(True)
        sunk = bevel_colors(self.palette.ACC_SOFT, pressed=True)
        self.assertEqual(self._edges(button), (sunk.top_left, sunk.bottom_right))
        button.set_selected(False)
        raised = bevel_colors(self.palette.ACC_SOFT)
        self.assertEqual(self._edges(button), (raised.top_left, raised.bottom_right))

    def test_keyboard_focus_draws_a_ring_in_the_accent_or_in_fg_on_a_primary_key(self):
        for primary, ring in ((False, self.palette.ACC), (True, self.palette.FG)):
            with self.subTest(primary=primary):
                button = self._button(primary=primary)
                idle = self._edges(button)
                button.focus_force()
                self.root.update()
                self.assertEqual(self._edges(button), (ring, ring))
                self.root.focus_force()
                self.root.update()
                self.assertEqual(self._edges(button), idle)
                button.destroy()

    def test_a_theme_change_repaints_every_key(self):
        button = self._button()
        self.palette = resolve_palette("light")
        button.configure(bg=self.palette.BTN)      # what the theme recolouring does
        bevel_tk.repaint_all()
        raised = bevel_colors(self.palette.BTN)
        self.assertEqual(self._edges(button), (raised.top_left, raised.bottom_right))

    def test_the_chunky_skins_get_thicker_edges(self):
        self.palette = resolve_palette("dex")
        button = self._button(bg=self.palette.BTN)
        edge, depth = bevel_edges(self.palette)
        self.assertEqual((button.winfo_x(), button.winfo_y()), (edge, edge))
        self.assertEqual(button.outer.winfo_height() - button._inner.winfo_height(), depth)

    def test_a_push_radiobutton_is_a_key_too(self):
        var = tk.StringVar(master=self.root, value="a")
        keys = {}
        for value in ("a", "b"):
            keys[value] = bevel_tk.BevelRadiobutton(
                self.root, palette_fn=lambda: self.palette, text=value, variable=var,
                value=value, indicatoron=False, bg=self.palette.BTN,
                selectcolor=self.palette.ACC_SOFT)
            keys[value].pack(side="left")
        self.root.update()
        self.assertEqual(self.root.pack_slaves(), [keys["a"].outer, keys["b"].outer])
        keys["b"].invoke()
        self.assertEqual(var.get(), "b")
        keys["b"].set_selected(True)
        sunk = bevel_colors(self.palette.BTN, pressed=True)
        self.assertEqual(self._edges(keys["b"]), (sunk.top_left, sunk.bottom_right))
        raised = bevel_colors(self.palette.BTN)
        self.assertEqual(self._edges(keys["a"]), (raised.top_left, raised.bottom_right))

    def test_destroying_the_button_removes_its_edge(self):
        button = self._button()
        outer = button.outer
        button.destroy()
        self.root.update()
        self.assertFalse(outer.winfo_exists())
        self.assertNotIn(button, list(bevel_tk._live))
        other = self._button()
        other.outer.destroy()                       # the parent side works too
        self.root.update()
        self.assertFalse(other.winfo_exists())


if __name__ == "__main__":
    unittest.main()
