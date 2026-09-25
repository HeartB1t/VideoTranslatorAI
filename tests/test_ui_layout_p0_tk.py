"""P0 layout of the integrated player (spec 2026-09-25, sections 3.1, 7.4, 9).

The player pane (left) owns the body height and never scrolls, the card
column (right) scrolls alone in its own canvas, and the header is fixed.
These are Tk tests: they skip without a display (CI has none) and run
locally on a private Xvfb, never on the operator's screen:

    xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" -v

With VTAI_LAYOUT_LOG=1 they print the measured geometry (root x, root y,
width, height) to stderr; the plan's Evidence section records it.
"""
import json
import os
import sys
import tkinter as tk
import types
import unittest
from unittest import mock

from test_ui_theme_tk import HAS_DISPLAY, _pump_until, built_app

CFG = {"ui_theme": "graphite", "ui_accent": "default", "ui_scale": "normal",
       "ui_lang": "it", "ui_log_visible": False}
SIZES = ((900, 600), (1100, 780))
BODY_PAD_Y = 8  # App._build_ui: 8 px above and below the body row


def _geom(widget):
    """(root x, root y, width, height) of ``widget``."""
    return (widget.winfo_rootx(), widget.winfo_rooty(),
            widget.winfo_width(), widget.winfo_height())


def _log(label, **values):
    """Print measured geometry when VTAI_LAYOUT_LOG is set (evidence runs)."""
    if os.environ.get("VTAI_LAYOUT_LOG"):
        parts = ", ".join(f"{name}={value}" for name, value in values.items())
        sys.__stderr__.write(f"[layout] {label}: {parts}\n")


def _show_at(testcase, app, width, height):
    """Map ``app`` at ``width`` x ``height`` and let the resize handlers run."""
    app.deiconify()
    app.geometry(f"{width}x{height}+0+0")
    reached = _pump_until(app, lambda: bool(app.winfo_viewable())
                          and app.winfo_width() == width
                          and app.winfo_height() == height)
    testcase.assertTrue(reached, f"the window never reached {width}x{height}")
    for _ in range(3):
        app.update()


def _subtree(widget):
    """``widget`` and all its descendants."""
    found, stack = [], [widget]
    while stack:
        current = stack.pop()
        found.append(current)
        stack.extend(current.winfo_children())
    return found


def _accordion_headers(app):
    """The clickable header row of every accordion section of the card column."""
    return [child
            for widget in _subtree(app._right_pane)
            if getattr(widget, "_is_accordion_section", False)
            for child in widget.winfo_children()
            if str(child.cget("cursor")) == "hand2"]


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class P0LayoutTests(unittest.TestCase):
    def test_root_rows_body_columns_and_hosts(self):
        with built_app(CFG) as (gui, app, _):
            # Root: one column, four rows. Only the body row stretches and no
            # row keeps a minimum, so P2's fullscreen can hide rows 0, 2, 3.
            self.assertEqual(app.grid_size(), (1, 4))
            rows = ((app._header_frame, 0), (app._body, 1),
                    (app._log_frame, 2), (app._progress, 3))
            for widget, row in rows:
                with self.subTest(row=row):
                    self.assertIs(widget.master, app)
                    info = widget.grid_info()
                    self.assertEqual((int(info["row"]), int(info["column"])), (row, 0))
                    config = app.grid_rowconfigure(row)
                    self.assertEqual(int(config["weight"]), 1 if row == 1 else 0)
                    self.assertEqual(int(config["minsize"]), 0)
            # Body: the player pane stretches; the card column keeps its width
            # through the canvas, never through a column minsize.
            body = app._body
            self.assertEqual(body.grid_size(), (2, 1))
            self.assertEqual(int(body.grid_rowconfigure(0)["weight"]), 1)
            self.assertEqual(int(body.grid_columnconfigure(0)["weight"]), 1)
            self.assertEqual(int(body.grid_columnconfigure(1)["weight"]), 0)
            self.assertEqual(int(body.grid_columnconfigure(1)["minsize"]), 0)
            left = app._left_pane.grid_info()
            self.assertIs(app._left_pane.master, body)
            self.assertEqual((int(left["row"]), int(left["column"])), (0, 0))
            # Tk reports sticky in its own letter order: compare as sets.
            self.assertEqual(set(left["sticky"]), set("nsew"))
            self.assertEqual(app._left_pane.pack_slaves(), [app._player_area])
            self.assertIs(app._right_column.master, body)
            self.assertEqual(int(app._right_column.grid_info()["column"]), 1)
            self.assertIs(app._right_canvas.master, app._right_column)
            self.assertIs(app._right_vsb.master, app._right_column)
            self.assertIs(app._right_pane.master, app._right_canvas)
            self.assertEqual(
                app._right_canvas.itemcget(app._right_canvas_window, "window"),
                str(app._right_pane))
            # Neither the player host nor the header lives inside a canvas.
            for widget in (app._player_area, app._btn_settings):
                ancestor = widget
                while ancestor is not app:
                    self.assertNotIsInstance(ancestor, tk.Canvas, str(widget))
                    ancestor = ancestor.master

    def test_player_pane_fills_the_body_at_both_sizes(self):
        with built_app(CFG) as (gui, app, _):
            for width, height in SIZES:
                with self.subTest(size=f"{width}x{height}"):
                    _show_at(self, app, width, height)
                    header = _geom(app._header_frame)
                    body = _geom(app._body)
                    log = _geom(app._log_frame)
                    player = _geom(app._player_area)
                    canvas = _geom(app._right_canvas)
                    _log(f"fill {width}x{height}", header=header, body=body,
                         player=player, canvas=canvas, log=log)
                    # header | 8 px | body | 8 px | log, nothing in between
                    self.assertEqual(header[1] + header[3] + BODY_PAD_Y, body[1])
                    self.assertEqual(body[1] + body[3] + BODY_PAD_Y, log[1])
                    # the player and the card column both span the body height
                    self.assertEqual((player[1], player[3]), (body[1], body[3]))
                    self.assertEqual((canvas[1], canvas[3]), (body[1], body[3]))
                    # at the 900 px floor about 377 px remain for the player
                    self.assertGreaterEqual(player[2], 360)

    def test_only_the_card_column_scrolls(self):
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 900, 600)
            canvas = app._right_canvas
            self.assertFalse(gui.App._canvas_content_fits(canvas))
            # No wheel binding outside the card column.
            areas = (("player", app._left_pane), ("header", app._header_frame),
                     ("log", app._log_frame))
            for area, root in areas:
                for widget in _subtree(root):
                    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                        with self.subTest(area=area, widget=str(widget),
                                          sequence=sequence):
                            self.assertEqual(widget.bind(sequence), "")
            fixed = {"player": app._player_area, "header": app._header_frame,
                     "log": app._log_frame}
            before = {name: _geom(w) for name, w in fixed.items()}
            canvas.yview_moveto(0.3)
            app.update()
            middle = canvas.yview()[0]
            self.assertGreater(middle, 0.0)
            # A wheel over the player or the header moves nothing...
            for widget in (app._player_area, app._btn_settings):
                widget.event_generate("<Button-5>")
                widget.event_generate("<Button-4>")
            app.update()
            self.assertEqual(canvas.yview()[0], middle)
            # ...a wheel over a card scrolls the column.
            app._lbl_panel_input.event_generate("<Button-5>")
            app.update()
            self.assertNotEqual(canvas.yview()[0], middle)
            # Scrolling moves the cards and nothing else.
            pane_top = app._right_pane.winfo_rooty()
            canvas.yview_moveto(1.0)
            app.update()
            self.assertLess(app._right_pane.winfo_rooty(), pane_top)
            after = {name: _geom(w) for name, w in fixed.items()}
            _log("scroll 900x600", before=before, after=after)
            self.assertEqual(after, before)

    def test_accordions_do_not_resize_the_player(self):
        with built_app(CFG) as (gui, app, _):
            headers = _accordion_headers(app)
            self.assertEqual(len(headers), 8)
            for width, height in SIZES:
                with self.subTest(size=f"{width}x{height}"):
                    _show_at(self, app, width, height)
                    before = _geom(app._player_area)
                    closed_height = app._right_pane.winfo_reqheight()
                    for header in headers:
                        header.event_generate("<Button-1>")
                    app.update()
                    self.assertGreater(app._right_pane.winfo_reqheight(), closed_height)
                    opened = _geom(app._player_area)
                    for header in headers:
                        header.event_generate("<Button-1>")
                    app.update()
                    closed = _geom(app._player_area)
                    _log(f"accordions {width}x{height}", before=before,
                         opened=opened, closed=closed)
                    self.assertEqual(opened, before)
                    self.assertEqual(closed, before)

    def test_card_drag_in_the_scrolled_column_leaves_the_player_alone(self):
        with built_app(CFG) as (gui, app, cfg_path):
            _show_at(self, app, 1100, 780)
            app._right_canvas.yview_moveto(0)
            app.update()
            self.assertEqual(app._panel_order[0], "input")
            before = _geom(app._player_area)
            start = app._panels["start"][0]
            first = app._panels["input"][0]
            x_column = app._right_pane.winfo_rootx() + 40
            x_player = app._player_area.winfo_rootx() + 20
            y_from = start.winfo_rooty() + 10
            y_to = first.winfo_rooty() + 2

            def ev(x, y):
                return types.SimpleNamespace(x_root=x, y_root=y)

            # Leaving the column sideways (over the player) cancels the drop.
            app._panel_drag_start("start", ev(x_column, y_from))
            app._panel_drag_motion(ev(x_player, y_to))
            self.assertFalse(app._drag_indicator.winfo_manager())
            app._panel_drag_end(ev(x_player, y_to))
            self.assertEqual(app._panel_order[0], "input")
            # A drag inside the column moves the card to the top and saves it.
            app._panel_drag_start("start", ev(x_column, y_from))
            app._panel_drag_motion(ev(x_column, y_to))
            app.update()
            self.assertTrue(app._drag_indicator.winfo_manager())
            during = _geom(app._player_area)
            app._panel_drag_end(ev(x_column, y_to))
            app.update()
            after = _geom(app._player_area)
            _log("drag 1100x780", before=before, during=during, after=after)
            self.assertEqual(app._panel_order[0], "start")
            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["ui_panel_order"][0], "start")
            self.assertEqual(during, before)
            self.assertEqual(after, before)

    def test_a_column_that_fits_is_pinned_to_the_top(self):
        # fd7eacc: no empty band above the first card. Tk lets a canvas view
        # move even when the content is shorter than the view (yview() still
        # says 0.0 then), so the test compares the cards' screen position.
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 900, 600)
            canvas = app._right_canvas
            # Only the small Start card left: the content fits now. (Shrink
            # with the view at the top: a shrink that leaves the whole content
            # above the view fires no <Configure> in Tk; users reach that only
            # through relabels, which Task 3 resyncs explicitly.)
            for pid in ("input", "translation", "profile", "settings"):
                app._panels[pid][0].pack_forget()
            app.update()
            self.assertTrue(gui.App._canvas_content_fits(canvas))
            top = canvas.winfo_rooty()
            self.assertEqual(app._right_pane.winfo_rooty(), top)
            # The wheel handler refuses to move it; every other path (the
            # scrollbar's arrows, trough and thumb) moves the cards, whose
            # <Configure> then pins the view back before the next paint.
            command = str(app._right_vsb.cget("command"))
            moves = (
                ("wheel up", lambda: app._lbl_panel_start.event_generate("<Button-4>")),
                ("wheel down", lambda: app._lbl_panel_start.event_generate("<Button-5>")),
                ("arrow up", lambda: app.tk.call(command, "scroll", "-3", "units")),
                ("page up", lambda: app.tk.call(command, "scroll", "-1", "pages")),
                ("thumb", lambda: app.tk.call(command, "moveto", "0.5")),
            )
            for name, move in moves:
                with self.subTest(move=name):
                    move()
                    app.update()
                    self.assertEqual(app._right_pane.winfo_rooty(), top)

    def test_card_column_takes_its_widest_state_and_at_least_460_px(self):
        # 0216809 kept the column at 460 px or more. Beside the player it also
        # takes up front the width of its widest state (every accordion
        # section open), so a toggle never changes it; the cards stretch to it.
        with built_app(CFG) as (gui, app, _):
            for width, height in SIZES:
                with self.subTest(size=f"{width}x{height}"):
                    _show_at(self, app, width, height)
                    widest = app._cards_widest_width()
                    want = max(460, widest)
                    _log(f"column {width}x{height}",
                         closed=app._right_pane.winfo_reqwidth(), widest=widest,
                         canvas=_geom(app._right_canvas), pane=_geom(app._right_pane))
                    self.assertEqual(int(app._right_canvas.cget("width")), want)
                    self.assertEqual(app._right_canvas.winfo_width(), want)
                    self.assertEqual(app._right_pane.winfo_width(), want)
            # The estimate is exact: with every section open the cards ask
            # for the widest width computed while they were closed.
            for header in _accordion_headers(app):
                header.event_generate("<Button-1>")
            app.update()
            self.assertEqual(app._right_pane.winfo_reqwidth(), widest)
            self.assertEqual(int(app._right_canvas.cget("width")), want)

    def test_hiding_rows_and_column_hands_the_window_to_the_player(self):
        # Spec 3.1 "Fullscreen": P2 grid_remove()s rows 0, 2, 3 and the card
        # column. Nothing may keep their space: no minsize, no weight (spike
        # S1 (b): with the old minsize=460 the host stopped at 1460x1080).
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 1100, 780)
            before = _geom(app._player_area)
            hidden = (app._header_frame, app._right_column, app._log_frame,
                      app._progress)
            for widget in hidden:
                widget.grid_remove()
            app.update()
            _, _, width, height = _geom(app._player_area)
            _log("rows hidden 1100x780", player=_geom(app._player_area))
            # 16 px left pad + 16 px gap remain, 8 px above and below
            self.assertEqual((width, height), (1100 - 32, 780 - 2 * BODY_PAD_Y))
            for widget in hidden:
                widget.grid()
            app.update()
            self.assertEqual(_geom(app._player_area), before)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class WheelStepTests(unittest.TestCase):
    """One notch scrolls the card column by one unit, in the wheel's direction."""

    def _after_scrolling(self, app, start, units):
        """View top after scrolling ``units`` from ``start``, then back to ``start``."""
        canvas = app._right_canvas
        canvas.yview_moveto(start)
        app.update()
        canvas.yview_scroll(units, "units")
        app.update()
        expected = canvas.yview()[0]
        canvas.yview_moveto(start)
        app.update()
        return expected

    def test_one_notch_one_unit_in_the_wheel_direction(self):
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 900, 600)
            canvas = app._right_canvas
            for sequence, units in (("<Button-5>", 1), ("<Button-4>", -1)):
                with self.subTest(sequence=sequence):
                    expected = self._after_scrolling(app, 0.3, units)
                    app._lbl_panel_input.event_generate(sequence)
                    app.update()
                    self.assertEqual(canvas.yview()[0], expected)
            # <MouseWheel> (Windows, Tk 8.7+): delta -120 is one notch down.
            for delta, units in ((-120, 1), (120, -1)):
                with self.subTest(delta=delta):
                    expected = self._after_scrolling(app, 0.3, units)
                    app._on_mousewheel(types.SimpleNamespace(num="??", delta=delta))
                    app.update()
                    self.assertEqual(canvas.yview()[0], expected)

    def test_touchpad_deltas_scroll_once_per_notch(self):
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 900, 600)
            canvas = app._right_canvas
            expected = self._after_scrolling(app, 0.3, 1)
            canvas.yview_moveto(0.3)
            app.update()
            for _ in range(3):  # 3 x -40 = one notch down
                app._on_mousewheel(types.SimpleNamespace(num="??", delta=-40))
            app.update()
            self.assertEqual(canvas.yview()[0], expected)

    def test_rebinding_the_voice_chips_does_not_stack_handlers(self):
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 900, 600)
            targets = list(gui.LANGUAGES.keys())
            for code in ("en", "de"):
                app._tgt_combo.current(targets.index(code))
                app._on_lang_tgt_change()
            app.update()
            expected = self._after_scrolling(app, 0.3, 1)
            app._voice_frame.event_generate("<Button-5>")
            app.update()
            self.assertEqual(app._right_canvas.yview()[0], expected)


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class ColumnSyncTests(unittest.TestCase):
    def test_width_follows_the_cards_after_relabels(self):
        # 0216809 after a relabel: it can change what the cards (or a closed
        # section's body) ask for without changing the column's height, and
        # then no <Configure> fires on the cards.
        with built_app(CFG) as (gui, app, _):
            _show_at(self, app, 1100, 780)
            refreshes = (("ui language", app._apply_lang),
                         ("theme and text size", app._apply_ui_settings),
                         ("target language", app._on_lang_tgt_change))
            for name, refresh in refreshes:
                with self.subTest(refresh=name):
                    with mock.patch.object(app, "_cards_widest_width",
                                           return_value=530):
                        refresh()
                        app.update()
                        self.assertEqual(int(app._right_canvas.cget("width")), 530)
                        self.assertEqual(app._right_pane.winfo_width(), 530)
                    refresh()
                    app.update()
                    self.assertEqual(int(app._right_canvas.cget("width")),
                                     max(460, app._cards_widest_width()))
            # Real long languages and a larger text size.
            for lang, scale in (("de", "normal"), ("fi", "large")):
                with self.subTest(lang=lang, scale=scale):
                    app._ui_lang.set(lang)
                    app._apply_lang()
                    app._ui_scale_var.set(scale)
                    app._apply_ui_settings()
                    app.update()
                    widest = app._cards_widest_width()
                    _log(f"column {lang} {scale}", widest=widest,
                         canvas=_geom(app._right_canvas))
                    self.assertEqual(int(app._right_canvas.cget("width")),
                                     max(460, widest))
                    self.assertEqual(app._right_pane.winfo_width(), max(460, widest))


if __name__ == "__main__":
    unittest.main()
