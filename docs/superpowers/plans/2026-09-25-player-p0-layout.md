# Player P0: Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the main window so the left player pane fills the body height and never scrolls, the card column (at least 460 px wide) scrolls alone in its own canvas, and the header stays fixed, while `self._player_area` remains the host that the P2 player will fill.

**Architecture:** The root grid becomes one column with four rows (header, body, log, progress). The body is a two-column grid: column 0 holds `_left_pane` with `_player_area` (weight 1), column 1 holds `_right_column`, a frame with a Canvas plus a ttk Scrollbar whose window item is the existing `_right_pane` with every card. The fit test (`_canvas_content_fits`), the resize pin of fd7eacc and the wheel binding move from the old whole-form canvas to the card column's canvas. A pure width rule and a pure wheel-step function go to `videotranslator/ui_layout.py`, so CI tests them without a display.

**Tech Stack:** Python 3.11 / 3.12, Tkinter 8.6 (grid, Canvas, ttk.Scrollbar), unittest, Xvfb (`xvfb-run`) for the Tk tests and the screenshots, ImageMagick `import`, `xwininfo`.

**Spec:** `docs/superpowers/specs/2026-09-25-video-player-live-design.md` (approved 2026-09-25; every section 10 question takes its recommended answer, Q1 included). This plan implements section 9 "P0 Layout" and the layout paragraphs of section 3.1 ("Layout", plus the structure that "Fullscreen" relies on). Testing follows 7.1 and 7.4; evidence follows 7.6 and the common gates at the top of section 9. Executors read spec 3.1, 7.4 and 9 (the common gates and P0) before starting.

## Global Constraints

Project rules (every task implicitly includes them):
- Commits directly on `main`, local only, never push. The push happens only when the operator asks; never force-push.
- Conventional commits: `feat`, `fix`, `docs`, `ui`, `refactor`, `test`, `chore`; imperative, explaining what and why. One logical change per commit.
- No `Co-Authored-By` trailer in any commit message (this rule wins over any session attribution reminder).
- No em dash (U+2014) or en dash (U+2013) anywhere: code, comments, docstrings, strings, docs, commit messages. Use `-`, a comma, a colon or parentheses.
- Every user-visible string in all 26 languages (it, en, ar, zh, cs, da, nl, fi, fr, de, el, hi, hu, id, ja, ko, no, pl, pt, ro, ru, es, sv, tr, uk, vi) in the module the spec designates (`videotranslator/ui_strings_player.py`, merged into `UI_STRINGS`, spec 2.6 and Q5), with the coverage test (`tests/test_ui_i18n_coverage.py`) green. P0 adds NO string (spec 9: "No new strings"); if one ever looks necessary, stop and report instead of adding it.
- Windows + Linux parity. For P1 this is the Windows installer story in `setup_windows.bat`: ASCII only, CRLF, the libmpv DLL, 7zr, the Vulkan fallback per Q1/Q2/Q6, and the static installer tests. P0 touches none of `setup_windows.bat`, `requirements*.txt`, `pyproject.toml`, the preflight or the README; its code is plain Tk geometry that behaves the same on both systems (each task carries a Windows note).
- Tests with `python3 -m unittest discover -s tests`, never `pytest` from the repo root (the backup folders collide).
- CI installs only `requirements-dev.txt`, so tests are hermetic: no libmpv, no network, lazy import of mpv, Tk tests skip without a display (the `HAS_DISPLAY` pattern of `tests/test_ui_theme_tk.py:11-16`).
- `python3 -m py_compile video_translator_gui.py videotranslator/*.py` before each commit.
- GUI checks only on a private Xvfb: the operator is working on the real display.
- Real libmpv checks use the unpacked libmpv 0.41 and python-mpv under `/home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI/_dev/research/player-2026-09-25/probe/` via `LD_LIBRARY_PATH` / `PYTHONPATH`, never a system-wide install or sudo. P0 needs no libmpv at all.

Session rules for this plan:
- Start EVERY Bash command with `unset DISPLAY WAYLAND_DISPLAY;` (the shell inherits the operator's `DISPLAY=:0.0`). Tk code runs only under `xvfb-run -a -s "-screen 0 1920x1080x24"` (`-a` picks a free display number, so it never collides with the Plan 0 spike runs), heavy commands under `nice -n 10`. Never create a window, run xdotool or take a screenshot on `:0`.
- Window rule on Xvfb. The project rule is "find the window with `wmctrl -l` before and after the launch and close it by id, never by name". `wmctrl` needs a window manager and crashes on a WM-less Xvfb (it left core dumps in the repo root on 2026-09-25). On the private Xvfb, list the top-level windows with `xwininfo -root -children` before and after, take the window id from `App.wm_frame()`, and close the app by that id from the process that owns it.
- GUI launches use an isolated config: `XDG_CONFIG_HOME` in a temporary directory with the config file written there BEFORE the GUI module is imported (otherwise the import copies the legacy `~/.videotranslatorai_config.json`, which may hold an old token, into it), `CONFIG_PATH` asserted to be that file, `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`, the startup dependency check and the yt-dlp upgrade stubbed (both can run pip), and the directory removed at the end. Never touch `~/.config/videotranslatorai/config.json`.
- Other agents commit in this working tree. Stage files by explicit path only; never `git add .` or `-A`, `git stash`, `git checkout`, `git reset`. Do not touch `_backup_ui_redesign_20260617/`, `_demo_styles.py`, or `_dev/` (Task 4 may write only `_dev/CHANGELOG.md` and `_dev/screenshots/player-p0-2026-09-25/`).
- Coder and reviewer run on Opus; a task's review starts only after its coder has finished (spec 9).
- GUI file budget: spec 2.3 allows +360 net lines in `video_translator_gui.py` over all phases. P0 adds about +40 (+39 on the planning dry run of Tasks 1-3); Task 4 reports `git diff --stat`.
- Line numbers below are anchors at HEAD `ab9a167` (the GUI file is unchanged since `7848368`); they drift. Always locate code by the quoted text.

## Preconditions (before Task 1)

- The backlog work of spec 9 "Sequencing" has landed and nobody else has uncommitted changes in the files P0 stages (staging `video_translator_gui.py` would otherwise sweep someone else's edit into a P0 commit):

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git status --short -- video_translator_gui.py videotranslator/ui_layout.py tests/test_ui_layout.py tests/test_ui_theme_tk.py tests/test_ui_layout_p0_tk.py
```
Expected: no output. Otherwise stop and report to the controller; never stash, commit or revert someone else's change.
- Record the base commit (Task 4 reports it as P0_BASE):

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git rev-parse --short HEAD
```
- The baseline suite is green (748 tests, 4 skipped, at the last run recorded on 2026-09-25; write down the number you get):

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests 2>&1 | tail -3
```

## Scope

In (spec 9 P0): the root grid restructure (3.1); the right column in its own scroll canvas; the wheel binding only on the right column; a fixed header; `_player_area` stays the host. Also in, because the moved code is rewritten and the new tests measure it:
- the wheel step: one unit per notch, downwards when the wheel turns down on Linux. The inversion is a known backlog item (`_dev/CHANGELOG.md`, "rotellina invertita su Linux in `_on_mousewheel`"). The double step comes from `_build_ui` binding both the form canvas and its inner frame (:7387-7388), and every target-language change adds one more handler on the voice chips' frame (:7845);
- the column width re-synced after relabels (UI language, text size, target language), which change what the cards ask for without any `<Configure>`.

Decision: the column takes its widest state up front. Measured on Xvfb on 2026-09-25 with the current code (planning check, `it` and nine other languages): with every accordion section closed the cards ask for 375-425 px at the normal text size, but with the sections open they ask for 454-473 px (`it` 461, `en` 469, `fr` 472, `el` 473), 493 px at the large size and 569 px at extra large. Today's grid column (`minsize=460`, weight 0) therefore widens whenever a wide section opens; with the player beside it, every such toggle would resize the video, against the P0 acceptance "expanding accordions ... does not resize it". So the canvas width is `max(460, widest)`, where `widest` is what the cards ask for with every section open (`_cards_widest_width`, exact because a closed section's body still reports its requested size). The width then changes only on a relabel (UI language, text size, target language), never on an accordion toggle. Cost: at the normal text size the column is up to 13 px wider than 460 in some languages, so at the 900 px floor the player gets 364-377 px instead of about 377.

Out (other phases or backlog): the player panel, the fullscreen behaviour and every mpv item (P2; P0 only builds the structure fullscreen needs and tests that it can be hidden: the body's column 1 has no `minsize`, the 460 px live on the canvas, so the spec 3.1 save/restore of that column's `minsize` and `weight` finds zeros, and spike S1 (b)'s 1460x1080 stop cannot happen); the Settings "Player" section and the "Watch live" wrap items of spec 7.4 (P2 and P6 extend `tests/test_ui_layout_p0_tk.py` with them later); the header "Player" badge (P1); the backlog items "the wheel over a combobox changes its value", "Tab ignores the dragged card order" and "`_flat_btn` has no focus ring"; the optional CI Xvfb job (Q14, P2).

## File Structure

| File | Change | Task |
|---|---|---|
| `videotranslator/ui_layout.py` | pure helpers: `RIGHT_COLUMN_MIN_WIDTH`, `right_column_width` (T1), `wheel_units` (T2) | 1, 2 |
| `video_translator_gui.py` | imports; `_build_header` grid slot; `_build_ui` restructure; the scroll helpers and `_cards_widest_width`; the `_accordion_body` marker in `_make_accordion_section`; three one-line resync hooks; the dead `_row_label` (it still pointed at the old form frame) removed | 1, 2, 3 |
| `tests/test_ui_layout_p0_tk.py` | new Tk layout test of spec 7.4 | 1, 2, 3 |
| `tests/test_ui_layout.py` | pure tests of the new helpers | 1, 2 |
| `tests/test_ui_theme_tk.py` | one layout test adapted to the new structure | 1 |
| `docs/superpowers/plans/2026-09-25-player-p0-layout.md` | the Evidence section | 4 |
| `_dev/CHANGELOG.md`, `_dev/screenshots/player-p0-2026-09-25/` | local evidence (gitignored) | 4 |

## Acceptance map (spec 9 P0, each item with its measuring method)

| Acceptance item | Method | Task |
|---|---|---|
| At 900x600 and 1100x780 the left pane fills the window height and never scrolls | `test_player_pane_fills_the_body_at_both_sizes`, `test_only_the_card_column_scrolls`, `test_root_rows_body_columns_and_hosts` (no Canvas ancestor); Xvfb screenshots 01, 02, 03, 04 | 1, 4 |
| Expanding accordions or dragging cards does not resize it (widget geometry logged before and after) | `test_accordions_do_not_resize_the_player`, `test_card_drag_in_the_scrolled_column_leaves_the_player_alone`, run with `VTAI_LAYOUT_LOG=1`, output pasted in Evidence | 1, 4 |
| fd7eacc still holds | `test_a_column_that_fits_is_pinned_to_the_top` (wheel, scrollbar arrows, trough and thumb on a column that fits) | 1 |
| 0216809 still holds | the existing `LayoutTests` drag tests, `test_card_column_takes_its_widest_state_and_at_least_460_px`, `test_width_follows_the_cards_after_relabels`, the real-geometry drag with its sideways cancel | 1, 3 |
| The Tk layout test is added and the suite is green | Xvfb and headless suite runs pasted in Evidence | 1-4 |
| Screenshots (Xvfb) attached to the plan | paths and a verdict per screenshot in Evidence | 4 |
| Fixed header | header geometry unchanged while the column scrolls (`test_only_the_card_column_scrolls`) | 1 |
| `_player_area` stays the host | `test_root_rows_body_columns_and_hosts` | 1 |

---

## Task 1: Root grid with a fixed header, a full-height player pane and a scrolling card column

Review level: full

Why full: it rebuilds the geometry of the whole main window and moves every wheel binding, and the Windows wheel routing cannot be exercised on this machine.

**Files:**
- Modify: `videotranslator/ui_layout.py` (module docstring :1-8, after `PANEL_IDS` :11-12, end of file)
- Modify: `video_translator_gui.py`: imports (:312-315), `__init__` comment (:5965-5971), `_make_accordion_section` (:6627), `_build_header` (:6722-6727), `_build_ui` (:7261-7391), the scroll helpers (:7393-7470)
- Create: `tests/test_ui_layout_p0_tk.py`
- Modify: `tests/test_ui_layout.py` (imports :4-6, one new class)
- Modify: `tests/test_ui_theme_tk.py` (`LayoutTests.test_every_card_sits_in_the_right_pane_and_the_left_is_the_player_area`, :810-826)

**Interfaces:**
- Consumes: `built_app`, `HAS_DISPLAY`, `_pump_until` from `tests/test_ui_theme_tk.py`; the existing `App._panels`, `_panel_order`, `_panel_drag_start` / `_panel_drag_motion` / `_panel_drag_end`, `_drag_indicator`, `_repack_panels`, `_canvas_content_fits`, `_bind_mousewheel`, `_on_mousewheel`, `_lbl_panel_input`, `_lbl_panel_start`, `_btn_settings`, `_toggle_log`.
- Produces (Tasks 2-4 and P2 rely on these names):
  - `videotranslator.ui_layout.RIGHT_COLUMN_MIN_WIDTH: int` (460) and `right_column_width(content_width: int) -> int`.
  - App attributes: `_header_frame` (root row 0); `_body` (root row 1, columns 0 and 1); `_left_pane` (body column 0) holding `_player_area` (packed `fill="both", expand=True`); `_right_column` (body column 1) holding `_right_canvas` (its column 0) and `_right_vsb` (its column 1); `_right_canvas_window` (the canvas window item that shows `_right_pane`); `_right_pane` (same role as today: it packs every card); `_log_frame` (root row 2); `_progress` (root row 3). P2's fullscreen hides `_header_frame`, `_right_column`, `_log_frame` and `_progress` with `grid_remove()` and restores them with `grid()`.
  - App methods: `_sync_right_column(self, _event=None) -> None`; `_on_right_canvas_configure(self, event) -> None`; `_cards_widest_width(self) -> int` (what the cards ask for with every accordion section open). Every accordion section frame carries `_accordion_body` (its body frame).
  - Test helpers in `tests/test_ui_layout_p0_tk.py`: `CFG`, `SIZES`, `BODY_PAD_Y`, `_geom(widget)`, `_log(label, **values)`, `_show_at(testcase, app, width, height)`, `_subtree(widget)`, `_accordion_headers(app)`.

- [ ] **Step 1: Write the pure test of the width rule**

In `tests/test_ui_layout.py` replace the import block

```python
from videotranslator.ui_layout import (
    PANEL_IDS, drop_index, move_panel, normalize_panel_order,
)
```

with

```python
from videotranslator.ui_layout import (
    PANEL_IDS, RIGHT_COLUMN_MIN_WIDTH, drop_index, move_panel,
    normalize_panel_order, right_column_width,
)
```

and add this class right before `if __name__ == "__main__":`

```python
class RightColumnWidthTests(unittest.TestCase):
    def test_never_below_the_minimum(self):
        self.assertEqual(RIGHT_COLUMN_MIN_WIDTH, 460)
        for asked in (0, 1, 300, 459, 460):
            with self.subTest(asked=asked):
                self.assertEqual(right_column_width(asked), 460)

    def test_widens_when_the_cards_ask_for_more(self):
        self.assertEqual(right_column_width(461), 461)
        self.assertEqual(right_column_width(530), 530)


```

- [ ] **Step 2: Write the Tk layout tests**

Create `tests/test_ui_layout_p0_tk.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

If `test_accordions_do_not_resize_the_player` ever fails after Task 1 because the player width changes, `_cards_widest_width` missed a widening path: report it with the logged widths, never relax the assertion.

- [ ] **Step 3: Adapt the existing layout test**

In `tests/test_ui_theme_tk.py`, `LayoutTests.test_every_card_sits_in_the_right_pane_and_the_left_is_the_player_area`, replace

```python
            content = app._right_pane.master
            self.assertGreaterEqual(int(content.grid_columnconfigure(1)["minsize"]), 460)
            # Tk reports sticky in its own letter order: compare as sets.
            self.assertEqual(set(app._right_pane.grid_info()["sticky"]), set("new"))
            self.assertEqual(set(app._left_pane.grid_info()["sticky"]), set("nsew"))
```

with

```python
            # P0 layout: the cards live in the right column's own scroll
            # canvas, at least 460 px wide; the left pane is a body cell.
            self.assertIs(app._right_pane.master, app._right_canvas)
            self.assertGreaterEqual(int(app._right_canvas.cget("width")), 460)
            self.assertIs(app._left_pane.master, app._body)
            # Tk reports sticky in its own letter order: compare as sets.
            self.assertEqual(set(app._left_pane.grid_info()["sticky"]), set("nsew"))
```

- [ ] **Step 4: Run the new tests and watch them fail**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests -p "test_ui_layout.py" 2>&1 | tail -4
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" 2>&1 | tail -6
```
Expected: the first run errors with `ImportError: cannot import name 'RIGHT_COLUMN_MIN_WIDTH'`. The second reports `Ran 8 tests` and `FAILED`: most tests error with `AttributeError: '_tkinter.tkapp' object has no attribute '_header_frame'` (or `_right_canvas`); `test_root_rows_body_columns_and_hosts` fails on `(2, 3) != (1, 4)`; `test_accordions_do_not_resize_the_player` fails because today the player's height follows the cards (planning check: 1169 px, then 1760 px with the sections open).

- [ ] **Step 5: Add the width rule to `videotranslator/ui_layout.py`**

Replace the module docstring

```python
"""Pure helpers for the movable panels of the settings column.

The GUI stacks its cards (input, translation, profile, start, settings) in
one column and lets the user reorder them by dragging a handle. Everything
that does not need Tk lives here so it can be unit-tested without a display:
the canonical panel ids, the normalisation of the persisted order, the move
operation and the drop-position maths.
"""
```

with

```python
"""Pure helpers for the card column of the main window.

The GUI stacks its cards (input, translation, profile, start, settings) in
one column that scrolls in its own canvas, and lets the user reorder them by
dragging a handle. Everything that does not need Tk lives here so it can be
unit-tested without a display: the canonical panel ids, the normalisation of
the persisted order, the move operation, the drop-position maths and the
column's width rule.
"""
```

After the two lines

```python
PANEL_IDS: tuple[str, ...] = ("input", "translation", "profile", "start", "settings")
"""Canonical panel ids, in the default top-to-bottom order."""
```

insert

```python

RIGHT_COLUMN_MIN_WIDTH = 460
"""Minimum width in px of the card column (hints wrap at 370 px inside it)."""
```

and append at the end of the file

```python


def right_column_width(content_width: int) -> int:
    """Canvas width of the card column whose cards ask for ``content_width`` px.

    Never below :data:`RIGHT_COLUMN_MIN_WIDTH`, wider when the cards ask for
    more: the rule of the grid column (``minsize=460``, weight 0) that held
    the cards before they moved into their own scroll canvas.
    """
    return max(RIGHT_COLUMN_MIN_WIDTH, int(content_width))
```

- [ ] **Step 6: Import it in the GUI**

In `video_translator_gui.py`, after

```python
from videotranslator.ui_layout import drop_index as _drop_index  # noqa: E402
```

add

```python
from videotranslator.ui_layout import RIGHT_COLUMN_MIN_WIDTH as _RIGHT_COLUMN_MIN_WIDTH  # noqa: E402
from videotranslator.ui_layout import right_column_width as _right_column_width  # noqa: E402
```

- [ ] **Step 7: Give the header its own root row**

In `_build_header`, replace

```python
        # Outer header frame - spans both columns
        header_wrap = tk.Frame(parent, bg=BG)
        header_wrap.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_wrap.columnconfigure(1, weight=1)
```

with

```python
        # Outer header frame: root row 0, fixed above the body (it never
        # scrolls). Kept as _header_frame so the player's fullscreen can
        # hide it (spec 3.1).
        header_wrap = tk.Frame(parent, bg=BG)
        header_wrap.grid(row=0, column=0, sticky="ew")
        header_wrap.columnconfigure(1, weight=1)
        self._header_frame = header_wrap
```

- [ ] **Step 8: Rebuild the top of `_build_ui`**

Replace the part of `_build_ui` from its `def _build_ui(self):` line down to and including its first `self._repack_panels()` line (today: the old root grid comment and weights, the "Scrollable canvas" block, `_main_frame`, the header call, the content frame, the left pane and the right pane, lines :7261-7330) with:

```python
    def _build_ui(self):
        # ── Root grid (player design, spec 2026-09-25 section 3.1) ────────
        # row 0 = header, fixed: it never scrolls
        # row 1 = body: column 0 = the player pane, which fills the height
        #         and never scrolls; column 1 = the card column, scrolled
        #         alone by its own canvas
        # row 2 = log panel
        # row 3 = progress bar
        # Only row 1 stretches and no row or column keeps a minimum size, so
        # the player's fullscreen can grid_remove() rows 0, 2, 3 and the card
        # column and hand the whole window to the player.
        for row, weight in ((0, 0), (1, 1), (2, 0), (3, 0)):
            self.grid_rowconfigure(row, weight=weight)
        self.grid_columnconfigure(0, weight=1)

        # Header first: it is also the first Tab stop of the window.
        self._build_header(self)

        # ── Body (root row 1) ─────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(8, 8))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        self._body = body

        # Left pane: the video player's host (a FIELD-coloured surface until
        # the player exists). It sits outside every canvas, so it follows the
        # window height and a wheel over it scrolls nothing.
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._left_pane = left
        self._player_area = tk.Frame(left, bg=FIELD, highlightthickness=1,
                                     highlightbackground=BORDER,
                                     highlightcolor=BORDER)
        self._player_area.pack(fill="both", expand=True)

        # Right column: input, translation, profile, start, then the settings
        # accordion, in a canvas that scrolls only this column. The canvas
        # takes the width of the cards' widest state, never below 460 px
        # (_sync_right_column); its height follows the window.
        column = tk.Frame(body, bg=BG)
        column.grid(row=0, column=1, sticky="ns")
        column.rowconfigure(0, weight=1)
        self._right_column = column
        self._right_canvas = tk.Canvas(column, bg=BG, highlightthickness=0,
                                       width=_RIGHT_COLUMN_MIN_WIDTH)
        self._right_canvas.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        self._right_vsb = ttk.Scrollbar(column, orient="vertical",
                                        command=self._right_canvas.yview)
        self._right_vsb.grid(row=0, column=1, sticky="ns")
        self._right_canvas.configure(yscrollcommand=self._right_vsb.set)

        right = tk.Frame(self._right_canvas, bg=BG)
        self._right_pane = right
        self._right_canvas_window = self._right_canvas.create_window(
            (0, 0), window=right, anchor="nw")
        # Keep width, scroll region and top pin in sync with the cards
        # (accordion toggles, drags, relabels) and with the window.
        right.bind("<Configure>", self._sync_right_column)
        self._right_canvas.bind("<Configure>", self._on_right_canvas_configure)

        self._build_input_section(right)
        self._build_lang_voice_section(right)
        self._build_profile_section(right)
        self._build_start_section(right)
        self._build_advanced_panel(right)
        # Built in the default order; apply the order the user saved.
        self._repack_panels()
```

- [ ] **Step 9: Move the log and the progress bar to rows 2 and 3, bind the wheel once on the card column**

Still in `_build_ui`, replace

```python
        # ── Log panel (root row 1, outside canvas) ────────────────────────
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=1, column=0, columnspan=2, padx=16,
                       pady=(0, 4), sticky="nsew")
```

with

```python
        # ── Log panel (root row 2) ────────────────────────────────────────
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="nsew")
        self._log_frame = log_frame
```

then replace

```python
        # ── Progress bar (root row 2) ─────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=2, column=0, columnspan=2,
                            padx=16, pady=(0, 12))

        # ── Mouse-wheel scrolling ──────────────────────────────────────────
        self._bind_mousewheel(self._main_canvas)
        self._bind_mousewheel(self._main_frame)
```

with

```python
        # ── Progress bar (root row 3) ─────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self._progress.grid(row=3, column=0, padx=16, pady=(0, 12))

        # ── Mouse-wheel scrolling: the card column only ───────────────────
        # One call covers the canvas and every card (they are its
        # descendants). The header, the player pane and the log stay unbound.
        self._bind_mousewheel(self._right_canvas)
```

The lines between (log header, log buttons, log text and its scrollbar) stay exactly as they are.

- [ ] **Step 10: Replace the form-canvas helpers**

Replace (the dead `_row_label` still pointed at the removed `_main_frame`; nothing calls it)

```python
    def _row_label(self, row, text):
        # All form rows live inside `self._main_frame` (a child of the
        # scrollable canvas built in `_build_ui`). Anchoring labels to the
        # root would break the scrolling layout, so we route them through
        # the inner frame just like every other form widget.
        lbl = tk.Label(self._main_frame, text=text, bg=BG, fg=FG2,
                       font="VT.Bold", anchor="e")
        lbl.grid(row=row, column=0, sticky="e", padx=(16, 8), pady=7)
        return lbl

    # ── Mouse wheel scrolling for the form canvas ──────────────────────────
```

with

```python
    # ── Scrolling of the card column ───────────────────────────────────────
```

In the `_canvas_content_fits` docstring replace

```python
        Scrolling in that case only shifts the form down and leaves an empty
        band above the header, so callers skip the scroll and pin the view.
```

with

```python
        Scrolling in that case only shifts the cards down and leaves an empty
        band above the first card, so callers skip the scroll and pin the view.
```

Replace

```python
    def _on_main_frame_configure(self, event):
        self._main_canvas.configure(scrollregion=self._main_canvas.bbox("all"))
        if self._canvas_content_fits(self._main_canvas):
            self._main_canvas.yview_moveto(0)

    def _on_main_canvas_configure(self, event):
        self._main_canvas.itemconfig(self._main_canvas_window, width=event.width)
        if self._canvas_content_fits(self._main_canvas):
            self._main_canvas.yview_moveto(0)
```

with

```python
    def _cards_widest_width(self):
        """Width the cards ask for with every accordion section open.

        A closed section's body still computes the size it would ask for
        (Tk propagates the requested size of unmapped frames), so the column
        can take its widest state up front: opening or closing a section
        then never changes the column's width, nor the player's (spec 9, P0).
        """
        widest = self._right_pane.winfo_reqwidth()
        card = getattr(self, "_advanced_card", None)  # settings card, inner frame
        if card is not None:
            # border and padding between that inner frame and the column
            chain = card.master.winfo_reqwidth() - card.winfo_reqwidth()
            for section in card.winfo_children():
                body = getattr(section, "_accordion_body", None)
                if body is not None:
                    widest = max(widest, body.winfo_reqwidth() + chain)
        return widest

    def _sync_right_column(self, _event=None):
        """Fit the card column's canvas to its cards.

        Runs on every size change of the cards (accordion toggles, drags,
        relabels). The canvas takes the width of the cards' widest state,
        never less than 460 px (0216809); the scroll region follows the
        content; a column that fits is pinned to the top, so no empty band
        can open above the first card (fd7eacc).
        """
        canvas = getattr(self, "_right_canvas", None)
        if canvas is None:
            return
        try:
            width = _right_column_width(self._cards_widest_width())
            if int(canvas.cget("width")) != width:
                canvas.configure(width=width)
            canvas.configure(scrollregion=canvas.bbox("all"))
            if self._canvas_content_fits(canvas):
                canvas.yview_moveto(0)
        except tk.TclError:
            pass  # the window is being destroyed

    def _on_right_canvas_configure(self, event):
        """Stretch the cards to the canvas width; pin a column that fits."""
        self._right_canvas.itemconfig(self._right_canvas_window, width=event.width)
        if self._canvas_content_fits(self._right_canvas):
            self._right_canvas.yview_moveto(0)
```

In `_on_mousewheel`, change only the target canvas (Task 2 rewrites the step logic). The method becomes:

```python
    def _on_mousewheel(self, event):
        """Scroll the card column in response to a wheel event over it.

        Cross-platform delta normalisation:
          * Linux delivers Button-4 (up) / Button-5 (down) without `delta`.
          * Windows / macOS deliver MouseWheel with `delta` in multiples
            of 120 (positive = up).
        """
        # Defensive: the canvas may have been destroyed mid-shutdown.
        if not hasattr(self, "_right_canvas"):
            return
        try:
            if self._canvas_content_fits(self._right_canvas):
                return
        except tk.TclError:
            return
        if sys.platform.startswith("linux"):
            delta = -1 if getattr(event, "num", 0) == 5 else 1
        else:
            delta = int(-1 * (event.delta / 120))
        try:
            self._right_canvas.yview_scroll(delta, "units")
        except tk.TclError:
            # Window being destroyed
            pass
```

`_bind_mousewheel` stays as it is in this task.

Finally, let every accordion section expose its body to `_cards_widest_width`. In `_make_accordion_section` replace

```python
        body = tk.Frame(outer, bg=SURFACE, padx=24, pady=6)
```

with

```python
        body = tk.Frame(outer, bg=SURFACE, padx=24, pady=6)
        outer._accordion_body = body  # measured by _cards_widest_width
```

- [ ] **Step 11: Update the `__init__` comment**

In `App.__init__`, replace

```python
        # Windows scaling 125%/150%. The form area is wrapped in a Canvas
        # with a vertical Scrollbar (see `_build_ui`), so even when the
        # window is resized below the form's natural height the user can
        # scroll to reach every control. Log + progress bar stay outside
        # the canvas and remain visible at all times.
```

with

```python
        # Windows scaling 125%/150%. The card column is wrapped in its own
        # Canvas with a vertical Scrollbar (see `_build_ui`), so even when
        # the window is shorter than the cards the user can scroll to reach
        # every control. Header, player pane, log and progress bar stay
        # outside that canvas and remain visible at all times.
```

- [ ] **Step 12: Run the tests and see them pass**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests -p "test_ui_layout.py" 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 env VTAI_LAYOUT_LOG=1 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" -v 2>&1 | tail -30
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests -p "test_ui_theme_tk.py" 2>&1 | tail -3
```
Expected: `OK` for all three; the P0 file reports `Ran 8 tests` and prints `[layout]` lines. `KeyboardAccessTests.test_tab_reaches_the_gear_first_and_walks_the_settings_in_reading_order` must still pass: the header is built first, so the gear is still the first Tab stop.

Then the whole suite, on Xvfb and headless:

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests 2>&1 | tail -3
```
Expected: `OK` both times; the Xvfb run has the baseline count plus 10 tests (2 pure, 8 Tk); the headless run skips every Tk test.

- [ ] **Step 13: Static checks**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m py_compile video_translator_gui.py videotranslator/*.py && echo compile-ok
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && grep -n '_main_canvas\|_main_frame\|_on_main_\|_row_label' video_translator_gui.py tests/*.py; echo "old-names exit=$?"
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && grep -nP '[\x{2013}\x{2014}]' video_translator_gui.py videotranslator/ui_layout.py tests/test_ui_layout.py tests/test_ui_theme_tk.py tests/test_ui_layout_p0_tk.py; echo "dash exit=$?"
```
Expected: `compile-ok`; `old-names exit=1` with no match; `dash exit=1` with no match.

- [ ] **Step 14: Commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git add videotranslator/ui_layout.py video_translator_gui.py tests/test_ui_layout.py tests/test_ui_theme_tk.py tests/test_ui_layout_p0_tk.py && git commit -F - <<'EOF'
ui: give the player pane the window height and scroll only the card column

The root grid now has four rows: a fixed header, the body, the log and
the progress bar. In the body the left pane (the future player host,
self._player_area) fills the whole height and never scrolls; the card
column scrolls alone in its own canvas, so the wheel over the video area
is free (spec 2026-09-25, section 3.1, phase P0). The fit test and resize
pin of fd7eacc and the 460 px minimum of 0216809 move to that canvas. The
column takes up front the width its cards ask for with every accordion
section open (461 px in Italian at the normal text size), so opening or
closing a section never resizes the player; the old grid column widened
on each wide section. The wheel is bound once per widget of the card
column: the old code bound the form canvas and its inner frame, so every
notch scrolled twice. The dead _row_label helper, which still pointed at
the old form frame, is removed. Tk layout tests cover both window sizes,
accordions, card drags and the rows fullscreen will hide.
EOF
```

Windows note: the code is plain Tk grid and Canvas geometry with pixel sizes, as before (the old column used `minsize=460` in pixels too). On Windows, Tk 8.6 sends `<MouseWheel>` to the widget under the pointer (TIP 171), which the per-widget bindings already relied on since v1.6, so "the wheel works only over the card column" holds there as well. Nothing changes in the installer. A Windows look at this layout is part of the P2 Windows items (spec 7.6: embedding and resize, accordion toggling and card drag while playing).

---

## Task 2: One wheel notch scrolls one unit, in the wheel's direction

Review level: light

**Files:**
- Modify: `videotranslator/ui_layout.py` (docstring, end of file)
- Modify: `video_translator_gui.py`: imports, `_on_mousewheel`, `_bind_mousewheel`
- Modify: `tests/test_ui_layout.py` (imports, one new class)
- Modify: `tests/test_ui_layout_p0_tk.py` (one new class)

**Interfaces:**
- Consumes: Task 1's `_right_canvas`, `_lbl_panel_input`, `_voice_frame`, `_tgt_combo`, `_on_lang_tgt_change` and the test helpers `CFG`, `_show_at`.
- Produces: `videotranslator.ui_layout.wheel_units(num: object, delta: object) -> int` (positive = down, negative = up, 0 = no scroll); `App._on_mousewheel` built on it; `App._bind_mousewheel(widget)` that REPLACES the widget-level wheel bindings of `widget` and its descendants.

- [ ] **Step 1: Write the pure test of the wheel step**

In `tests/test_ui_layout.py` extend the import block to

```python
from videotranslator.ui_layout import (
    PANEL_IDS, RIGHT_COLUMN_MIN_WIDTH, drop_index, move_panel,
    normalize_panel_order, right_column_width, wheel_units,
)
```

and add before `if __name__ == "__main__":`

```python
class WheelUnitsTests(unittest.TestCase):
    def test_x11_buttons(self):
        # Tk 8.6 on X11: button 4 is the wheel turned up, button 5 down.
        self.assertEqual(wheel_units(4, 0), -1)
        self.assertEqual(wheel_units(5, 0), 1)

    def test_mousewheel_deltas_of_whole_notches(self):
        # Windows (and Tk 8.7+ on X11): +120 per notch up, -120 per notch down.
        for delta, units in ((120, -1), (-120, 1), (240, -2), (-360, 3)):
            with self.subTest(delta=delta):
                self.assertEqual(wheel_units("??", delta), units)

    def test_small_deltas_still_move_one_unit(self):
        # macOS and fine-grained wheels send small deltas.
        for delta, units in ((1, -1), (-3, 1), (119, -1), (-60, 1)):
            with self.subTest(delta=delta):
                self.assertEqual(wheel_units("??", delta), units)

    def test_no_wheel_no_scroll(self):
        for num, delta in ((1, 0), ("??", 0), (None, None), ("??", "x")):
            with self.subTest(num=num, delta=delta):
                self.assertEqual(wheel_units(num, delta), 0)


```

- [ ] **Step 2: Write the Tk test of the step**

Append to `tests/test_ui_layout_p0_tk.py`, before `if __name__ == "__main__":`

```python
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


```

- [ ] **Step 3: Run them and watch them fail**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests -p "test_ui_layout.py" 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" 2>&1 | tail -8
```
Expected: `ImportError: cannot import name 'wheel_units'`; in the Tk file `WheelStepTests` fails (Button-5 scrolls up today, `delta=120` scrolls down, and the voice frame scrolls three units after two target changes).

- [ ] **Step 4: Add `wheel_units` to `videotranslator/ui_layout.py`**

In the module docstring replace

```python
the persisted order, the move operation, the drop-position maths and the
column's width rule.
```

with

```python
the persisted order, the move operation, the drop-position maths, the
column's width rule and the mouse-wheel step.
```

Append at the end of the file:

```python


def wheel_units(num: object, delta: object) -> int:
    """Scroll units for one mouse-wheel event: positive down, negative up.

    Tk 8.6 on X11 reports the wheel as buttons 4 (turned up) and 5 (turned
    down) without a delta. Windows, macOS and Tk 8.7+ on X11 report
    ``<MouseWheel>`` with a ``delta``: positive means up, one Windows notch
    is 120, macOS sends small values that still move one unit. Any other
    event (another button, a zero or unreadable delta) scrolls nothing.
    """
    if num == 4:
        return -1
    if num == 5:
        return 1
    try:
        amount = int(delta or 0)
    except (TypeError, ValueError):
        return 0
    if amount == 0:
        return 0
    steps = -int(amount / 120)
    if steps == 0:
        steps = -1 if amount > 0 else 1
    return steps
```

- [ ] **Step 5: Use it in the GUI**

After

```python
from videotranslator.ui_layout import right_column_width as _right_column_width  # noqa: E402
```

add

```python
from videotranslator.ui_layout import wheel_units as _wheel_units  # noqa: E402
```

Replace the whole `_on_mousewheel` method (the Task 1 version) and the whole `_bind_mousewheel` method with:

```python
    def _on_mousewheel(self, event):
        """Scroll the card column in response to a wheel event over it.

        ``wheel_units`` turns the event into scroll units on every platform
        (X11 buttons 4/5, ``<MouseWheel>`` deltas on Windows and Tk 8.7+).
        """
        canvas = getattr(self, "_right_canvas", None)
        if canvas is None:
            return
        try:
            if self._canvas_content_fits(canvas):
                return
            units = _wheel_units(getattr(event, "num", None),
                                 getattr(event, "delta", 0))
            if units:
                canvas.yview_scroll(units, "units")
        except tk.TclError:
            pass  # the window is being destroyed

    def _bind_mousewheel(self, widget):
        """Bind wheel scrolling on ``widget`` and all its descendants.

        Tk does not pass wheel events on to parent widgets, so the canvas
        would otherwise stop scrolling as soon as the cursor hovers over an
        inner control (entry, combobox, button, ...). The bindings REPLACE
        any earlier widget-level wheel binding: re-binding a subtree (the
        voice chips after a target change) must not stack a second handler,
        or one notch would scroll twice. No other code binds wheel events at
        widget level; class bindings (Listbox, Text, Combobox) are separate.
        """
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel)  # Win/Mac, Tk 8.7+
            widget.bind("<Button-4>", self._on_mousewheel)    # X11 up
            widget.bind("<Button-5>", self._on_mousewheel)    # X11 down
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_mousewheel(child)
```

Check that nothing else binds wheel events at widget level:

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && grep -n 'MouseWheel\|Button-4\|Button-5' video_translator_gui.py
```
Expected: only the lines inside `_bind_mousewheel` and the `_on_mousewheel` docstring.

- [ ] **Step 6: Run the tests and see them pass**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests -p "test_ui_layout.py" 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests 2>&1 | tail -3
```
Expected: `OK` everywhere; the P0 file now reports `Ran 10 tests`; the full Xvfb run is Task 1's count plus 6.

- [ ] **Step 7: Static checks**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m py_compile video_translator_gui.py videotranslator/*.py && echo compile-ok
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && grep -nP '[\x{2013}\x{2014}]' video_translator_gui.py videotranslator/ui_layout.py tests/test_ui_layout.py tests/test_ui_layout_p0_tk.py; echo "dash exit=$?"
```
Expected: `compile-ok`, `dash exit=1`.

- [ ] **Step 8: Commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git add videotranslator/ui_layout.py video_translator_gui.py tests/test_ui_layout.py tests/test_ui_layout_p0_tk.py && git commit -F - <<'EOF'
fix(ui): scroll one unit per wheel notch, down when the wheel turns down

On X11 the wheel scrolled the card column the wrong way (button 5, the
wheel turned down, scrolled up), and re-binding the voice chips after a
target language change stacked one more handler each time, so a notch
over them scrolled several units. The step now comes from the pure
wheel_units helper (X11 buttons 4/5, <MouseWheel> deltas on Windows and
Tk 8.7+) and _bind_mousewheel replaces its bindings instead of adding.
EOF
```

Windows note: Windows deltas are multiples of 120 and give the same units as before (`-int(delta / 120)`); only the X11 direction changes, and Tk 8.7+ `<MouseWheel>` events on X11 are now read from their delta. The pure tests cover every branch.

---

## Task 3: Relabels resync the card column's width

Review level: light

**Files:**
- Modify: `video_translator_gui.py`: one line each (plus a comment) at the end of `_apply_lang`, `_refresh_theme_dependents` and `_on_lang_tgt_change`
- Modify: `tests/test_ui_layout_p0_tk.py` (one import, one new class)

**Interfaces:**
- Consumes: Task 1's `_right_canvas`, `_right_pane`, `_sync_right_column`, `_cards_widest_width`, the test helpers; the existing `_apply_lang`, `_apply_ui_settings`, `_refresh_theme_dependents`, `_on_lang_tgt_change`, `_ui_lang`, `_ui_scale_var`.
- Produces: after `_apply_lang`, `_apply_ui_settings` (through `_refresh_theme_dependents`, which also runs on a late automatic theme answer) and `_on_lang_tgt_change`, `_sync_right_column` runs once at idle time.

Why: `_sync_right_column` runs on `<Configure>` of the cards and of the canvas. A relabel can change the width a closed accordion section's body asks for (and so `_cards_widest_width`) without changing any visible height, and a text-size change can shrink the cards so much that the whole content ends above the current view; in both cases Tk sends no `<Configure>` and the column keeps a stale width or an empty view. Scrolling itself needs nothing more: the planning check showed that any view move of a fitting column (wheel, scrollbar arrows, trough or thumb) moves the embedded cards, whose `<Configure>` pins the view back before the next paint (Task 1's `test_a_column_that_fits_is_pinned_to_the_top` covers each path), so no separate scrollbar guard is added.

- [ ] **Step 1: Write the failing test**

In `tests/test_ui_layout_p0_tk.py` add after `import unittest`:

```python
from unittest import mock
```

and append before `if __name__ == "__main__":`

```python
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


```

- [ ] **Step 2: Run it and watch it fail**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" 2>&1 | tail -12
```
Expected: `test_width_follows_the_cards_after_relabels` fails in the three relabel subtests with `AssertionError: 461 != 530` (the width Task 1 set, not the patched one) and in the `de`/`normal` subtest with `461 != 460` (a stale width: German asks for 454 px).

- [ ] **Step 3: Resync the column after relabels**

At the end of `_apply_lang`, replace

```python
        self._src_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, k=src_keys: (
                self._lang_src.set(k[self._src_combo.current()]),
                self._update_start_summary(),
            ))
        self._update_start_summary()
```

with

```python
        self._src_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, k=src_keys: (
                self._lang_src.set(k[self._src_combo.current()]),
                self._update_start_summary(),
            ))
        self._update_start_summary()
        # A relabel can change what the cards ask for (closed accordion
        # sections included) without changing their height, and then no
        # <Configure> reaches _sync_right_column.
        self.after_idle(self._sync_right_column)
```

In `_refresh_theme_dependents`, replace

```python
        if self._settings_win is not None and self._settings_win.winfo_exists():
            for row in (self._seg_theme, self._seg_scale):
                row._refresh()
            self._refresh_accent_dots()
        self._update_profile_buttons()
```

with

```python
        if self._settings_win is not None and self._settings_win.winfo_exists():
            for row in (self._seg_theme, self._seg_scale):
                row._refresh()
            self._refresh_accent_dots()
        self._update_profile_buttons()
        # Another text size changes the cards' width, and a large shrink can
        # leave the view below the content without any <Configure>.
        self.after_idle(self._sync_right_column)
```

In `_on_lang_tgt_change`, replace

```python
        # Re-bind mousewheel to newly created voice pill buttons
        try:
            self._bind_mousewheel(self._voice_frame)
        except Exception:
            pass
        self._update_start_summary()
```

with

```python
        # Re-bind mousewheel to newly created voice pill buttons
        try:
            self._bind_mousewheel(self._voice_frame)
        except Exception:
            pass
        self._update_start_summary()
        # New voice chips can change the cards' width.
        self.after_idle(self._sync_right_column)
```

- [ ] **Step 4: Run the tests and see them pass**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 env VTAI_LAYOUT_LOG=1 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" -v 2>&1 | tail -30
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests 2>&1 | tail -3
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests 2>&1 | tail -3
```
Expected: `OK` everywhere; the P0 file reports `Ran 11 tests`; the full Xvfb run is Task 2's count plus 1. The `[layout] column de normal` and `column fi large` lines show the width each case asks for.

- [ ] **Step 5: Static checks**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m py_compile video_translator_gui.py videotranslator/*.py && echo compile-ok
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && grep -nP '[\x{2013}\x{2014}]' video_translator_gui.py tests/test_ui_layout_p0_tk.py; echo "dash exit=$?"
```
Expected: `compile-ok`, `dash exit=1`.

- [ ] **Step 6: Commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git add video_translator_gui.py tests/test_ui_layout_p0_tk.py && git commit -F - <<'EOF'
fix(ui): resync the card column after language, text size and voice changes

A relabel (UI language, theme or text size, target language) can change
the width the cards ask for, closed accordion sections included, without
changing the column's height, and a large text-size shrink can end the
content above the current view; in both cases Tk sends no <Configure>.
Those paths now resync the column once at idle time, so it keeps its
widest-state width and the 460 px minimum of 0216809 after them too.
EOF
```

Windows note: pure Tk, no platform branch.

---

## Task 4: Xvfb evidence, screenshots and the phase record

Review level: light

**Files:**
- Create (local, gitignored): `_dev/screenshots/player-p0-2026-09-25/p0_layout_shots.py`, its PNGs and the test logs in the same folder
- Modify (local, gitignored): `_dev/CHANGELOG.md` (a new entry at the top)
- Modify: `docs/superpowers/plans/2026-09-25-player-p0-layout.md` (the Evidence section at the end)

**Interfaces:**
- Consumes: everything from Tasks 1-3 (`_player_area`, `_right_canvas`, `_right_pane`, `_toggle_log`, `_apply_ui_settings`, `_apply_lang`, `_ui_theme_var`, `_ui_scale_var`, `_ui_lang`, the `_is_accordion_section` marker).
- Produces: the Evidence section and the `_dev/CHANGELOG.md` entry that close the phase (spec 9: acceptance, "screenshots attached to the plan", Tk output "pasted into the plan"; spec 7.6: the per-phase record).

- [ ] **Step 1: Check the starting point**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git status --short -- video_translator_gui.py videotranslator/ tests/ && git log --oneline -5
```
Expected: no modified tracked file; the three commits of Tasks 1-3 on top of P0_BASE.

- [ ] **Step 2: Run the Tk layout tests three times in a row**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && mkdir -p _dev/screenshots/player-p0-2026-09-25 && for run in 1 2 3; do xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 env VTAI_LAYOUT_LOG=1 python3 -m unittest discover -s tests -p "test_ui_layout_p0_tk.py" -v > _dev/screenshots/player-p0-2026-09-25/tk-tests-run$run.txt 2>&1; tail -3 _dev/screenshots/player-p0-2026-09-25/tk-tests-run$run.txt; done
```
Expected: `Ran 11 tests` and `OK` three times. A failure in any run is a flaky layout: find the cause (usually a missing `app.update()` after a geometry change) before going on.

- [ ] **Step 3: Run the whole suite on Xvfb and headless**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 -m unittest discover -s tests > _dev/screenshots/player-p0-2026-09-25/suite-xvfb.txt 2>&1; tail -3 _dev/screenshots/player-p0-2026-09-25/suite-xvfb.txt
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m unittest discover -s tests > _dev/screenshots/player-p0-2026-09-25/suite-headless.txt 2>&1; tail -3 _dev/screenshots/player-p0-2026-09-25/suite-headless.txt
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 -m py_compile video_translator_gui.py videotranslator/*.py && echo compile-ok
```
Expected: `OK` twice (baseline plus 17 tests on Xvfb; the headless run skips every Tk test), then `compile-ok`.

- [ ] **Step 4: Write the screenshot driver**

Create `_dev/screenshots/player-p0-2026-09-25/p0_layout_shots.py`:

```python
"""P0 layout evidence: screenshots of the real App on a private Xvfb.

Local only (inside _dev/, gitignored). Run from the repository root:

    xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 _dev/screenshots/player-p0-2026-09-25/p0_layout_shots.py

It refuses the operator's display, uses a throw-away config directory (removed
at the end) and the null keyring, stubs the startup dependency check and the
yt-dlp upgrade (both can run pip), prints what it measures and writes PNGs
next to itself.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DISPLAY = os.environ.get("DISPLAY", "")
if DISPLAY in ("", ":0", ":0.0"):
    sys.exit(f"refusing to run on DISPLAY={DISPLAY!r}: use a private Xvfb")

CFG_ROOT = Path(tempfile.mkdtemp(prefix="vt-p0-cfg-"))
os.environ["XDG_CONFIG_HOME"] = str(CFG_ROOT)
os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
# Write the config BEFORE the import: an existing config file stops the
# one-time copy of the legacy ~/.videotranslatorai_config.json into it.
CFG_FILE = CFG_ROOT / "videotranslatorai" / "config.json"
CFG_FILE.parent.mkdir(parents=True)
CFG_FILE.write_text(json.dumps({
    "ui_theme": "graphite", "ui_accent": "default", "ui_scale": "normal",
    "ui_lang": "it", "ui_log_visible": False, "yt_dlp_auto_upgrade": False,
}), encoding="utf-8")
sys.path.insert(0, str(REPO))

import video_translator_gui as gui  # noqa: E402

if gui.CONFIG_PATH != CFG_FILE:
    shutil.rmtree(CFG_ROOT, ignore_errors=True)
    sys.exit(f"config would go to {gui.CONFIG_PATH}, not {CFG_FILE}")
gui.App._check_deps_on_start = lambda self: None
gui.App._upgrade_ytdlp_in_background = lambda self: None


def toplevels():
    out = subprocess.run(["xwininfo", "-root", "-children"], capture_output=True,
                         text=True, check=True).stdout
    return [line.split()[0] for line in out.splitlines()
            if line.strip().startswith("0x")]


def pump(app, seconds=0.5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.update()
        time.sleep(0.02)


def geom(widget):
    return (widget.winfo_rootx(), widget.winfo_rooty(),
            widget.winfo_width(), widget.winfo_height())


def resize(app, width, height):
    app.geometry(f"{width}x{height}+0+0")
    pump(app)


def shot(app, name):
    path = HERE / name
    subprocess.run(["import", "-window", app.wm_frame(), str(path)], check=True)
    view = tuple(round(v, 3) for v in app._right_canvas.yview())
    print(f"{name}: window {app.winfo_width()}x{app.winfo_height()}, "
          f"player {geom(app._player_area)}, column {geom(app._right_canvas)}, "
          f"yview {view}")


def accordion_headers(app):
    found, stack = [], [app._right_pane]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        if getattr(widget, "_is_accordion_section", False):
            found.extend(child for child in widget.winfo_children()
                         if str(child.cget("cursor")) == "hand2")
    return found


before = toplevels()
app = gui.App()
pump(app, 1.0)
after = toplevels()
frame = app.wm_frame()
print(f"top-level windows before {len(before)}, after {len(after)}, "
      f"new {[w for w in after if w not in before]}, app frame {frame}")
try:
    resize(app, 1100, 780)
    shot(app, "01-1100x780-it-graphite.png")
    resize(app, 900, 600)
    shot(app, "02-900x600-it-graphite.png")
    player = geom(app._player_area)
    headers = accordion_headers(app)
    for header in headers:
        header.event_generate("<Button-1>")
    pump(app)
    app._right_canvas.yview_moveto(1.0)
    pump(app)
    print(f"accordions opened: {len(headers)}, player before {player}, "
          f"after {geom(app._player_area)}")
    shot(app, "03-900x600-accordions-open-scrolled-to-bottom.png")
    for header in headers:
        header.event_generate("<Button-1>")
    app._right_canvas.yview_moveto(0.0)
    app._toggle_log()
    pump(app)
    shot(app, "04-900x600-log-visible.png")
    app._toggle_log()
    resize(app, 1100, 780)
    app._ui_theme_var.set("light")
    app._apply_ui_settings()
    pump(app)
    shot(app, "05-1100x780-light.png")
    app._ui_lang.set("de")
    app._apply_lang()
    app._ui_scale_var.set("large")
    app._apply_ui_settings()
    resize(app, 900, 600)
    shot(app, "06-900x600-de-large.png")
finally:
    app._destroying = True
    for after_id in app.tk.splitlist(app.tk.call("after", "info")):
        app.after_cancel(after_id)
    app.destroy()
    gone = subprocess.run(["xwininfo", "-id", frame],
                          capture_output=True).returncode != 0
    print(f"closed {frame} (gone: {gone}); top-level windows now {len(toplevels())}")
    shutil.rmtree(CFG_ROOT, ignore_errors=True)
```

- [ ] **Step 5: Run it on a private Xvfb**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && xvfb-run -a -s "-screen 0 1920x1080x24" nice -n 10 python3 _dev/screenshots/player-p0-2026-09-25/p0_layout_shots.py 2>&1 | tee _dev/screenshots/player-p0-2026-09-25/driver-output.txt
```
Expected: no `Config migrated` line (the driver's config exists before the import); new top-level windows appear after the launch (without a window manager Tk shows its wrapper plus a 1x1 helper, so expect two new ids; the printed app frame is the toplevel inside the wrapper), and after `closed` the line says `gone: True` and the count drops by one (the helper lives until the process exits); six `NN-...png: window ...` lines; `accordions opened: 8` with identical player geometry before and after; six PNG files in the folder; no `vt-p0-cfg-*` directory left under the temporary directory. On the planning dry run (2026-09-25) the player measured `(16, 69, 376, 463)` at 900x600 and `(16, 69, 576, 643)` at 1100x780, with the column at 461 px (493 px in German at the large size).

- [ ] **Step 6: Look at every screenshot**

Open each PNG with the Read tool and check:
- 01, 02: the header spans the whole width at the top; on the left the FIELD-coloured surface runs from under the header down to the log bar with 16 px margins; on the right the cards with their own scrollbar at the window edge; no empty band above the first card.
- 03: every accordion open and the cards scrolled to the bottom, while the header is still at the top and the player surface has the size printed for 02.
- 04: log visible: the player surface is shorter but still reaches from the header down to the log.
- 05: light theme on the new frames and on the column canvas (no dark strip left around the cards or the player).
- 06: German at large text size: the column is at least 460 px wide, no clipped text, the player takes the rest.
Anything wrong is a defect of Tasks 1-3: report it with the screenshot, do not paper over it here.

- [ ] **Step 7: Record the phase in `_dev/CHANGELOG.md`**

Insert a new entry right after the first `---` line of `_dev/CHANGELOG.md` (above the `[backlog-hardening + player-design] - 2026-09-25` entry). Its heading line is the level-2 heading `[player-p0-layout] - YYYY-MM-DD` (same form as the entries below it, with the date of the run), followed by a blank line and this body, with the real values of this run in place of the angle-bracketed fields:

```markdown
Piano `docs/superpowers/plans/2026-09-25-player-p0-layout.md` (spec player 2026-09-25,
sezione 9, fase P0). Commit locali <hash Task 1>, <hash Task 2>, <hash Task 3> su
<P0_BASE>, non pushati.
- Layout: griglia root a quattro righe (header fisso, corpo, log, barra di avanzamento).
  Nel corpo il riquadro del player (`self._player_area`) occupa tutta l'altezza e non
  scorre; la colonna delle card (minimo 460 px) scorre da sola nel suo canvas, con la
  sua scrollbar. La rotella agisce solo sopra la colonna delle card.
- La colonna prende subito la larghezza del suo stato piu' largo (tutte le sezioni
  dell'accordion aperte, <n> px in italiano a dimensione normale): aprire o chiudere
  una sezione non ridimensiona piu' il player (prima la colonna si allargava).
- Rotella: su Linux ora scende quando la rotella gira verso il basso (prima era
  invertita) e uno scatto vale una unita' (prima due, e cresceva a ogni cambio della
  lingua di destinazione sopra le voci).
- fd7eacc vale anche per la scrollbar; 0216809 vale anche dopo cambio di lingua, tema,
  dimensione testo e lingua di destinazione.
- Verifica: test Tk P0 <n> OK per 3 run di fila su Xvfb; suite completa <n> OK su Xvfb e
  <n> OK headless (<k> skip); screenshot e log in `_dev/screenshots/player-p0-2026-09-25/`.
- Aperti (backlog, fuori P0): rotella sopra una combobox ne cambia il valore; Tab ignora
  l'ordine delle card trascinate; `_flat_btn` senza focus ring.
```

- [ ] **Step 8: Fill the Evidence section of this plan**

Replace the paragraph under `## Evidence` at the end of this file with:
- P0_BASE and `git log --oneline P0_BASE..HEAD` (the three task commits);
- `git diff --stat P0_BASE..HEAD` and the net line change of `video_translator_gui.py`;
- the full content of `tk-tests-run3.txt` in a fenced block, and the last three lines of runs 1 and 2;
- the last three lines of `suite-xvfb.txt` and of `suite-headless.txt`;
- the full `driver-output.txt` in a fenced block;
- the six screenshot paths (`_dev/screenshots/player-p0-2026-09-25/NN-....png`), each with its one-line verdict from Step 6.

- [ ] **Step 9: Check dashes and commit the plan**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && grep -nP '[\x{2013}\x{2014}]' docs/superpowers/plans/2026-09-25-player-p0-layout.md _dev/CHANGELOG.md | head; echo "dash exit=$?"
```
Expected: no line from the plan. (`_dev/CHANGELOG.md` may still show historic lines further down; the new entry must add none.) Then:

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && git add docs/superpowers/plans/2026-09-25-player-p0-layout.md && git commit -m "docs(plan): record the P0 layout evidence" -m "Tk layout test output (three runs on Xvfb), full suite on Xvfb and headless, the screenshot driver output and the six screenshots of the P0 layout, as required by the phase gates of the player spec (section 9)."
```

Windows note: this evidence is Linux only by design (private Xvfb). The first Windows look at the layout belongs to the P2 Windows items (spec 9, "from P2 on, each phase has at least one Windows item").

---

## Evidence

Task 4 replaces this paragraph with the recorded results listed in its Step 8. Nothing is recorded here before Tasks 1-3 have run.
