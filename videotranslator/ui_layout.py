"""Pure helpers for the card column of the main window.

The GUI stacks its cards (input, translation, profile, start, settings) in
one column that scrolls in its own canvas, and lets the user reorder them by
dragging a handle. Everything that does not need Tk lives here so it can be
unit-tested without a display: the canonical panel ids, the normalisation of
the persisted order, the move operation, the drop-position maths, the
column's width rule and the mouse-wheel step.
"""
from __future__ import annotations

PANEL_IDS: tuple[str, ...] = ("input", "translation", "profile", "start", "settings")
"""Canonical panel ids, in the default top-to-bottom order."""

RIGHT_COLUMN_MIN_WIDTH = 460
"""Minimum width in px of the card column (hints wrap at 370 px inside it)."""


def normalize_panel_order(value: object) -> list[str]:
    """Return a complete, valid panel order from any config value.

    Unknown ids, duplicates and non-string items are dropped; ids missing
    from ``value`` are appended in the default order; anything that is not
    a list or tuple yields the default order. The result always contains
    every id of ``PANEL_IDS`` exactly once.
    """
    order: list[str] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str) and item in PANEL_IDS and item not in order:
                order.append(item)
    for pid in PANEL_IDS:
        if pid not in order:
            order.append(pid)
    return order


def move_panel(order: list[str], panel_id: str, new_index: int) -> list[str]:
    """Return a copy of ``order`` with ``panel_id`` at ``new_index``.

    ``new_index`` counts positions in the list WITHOUT the moved panel (the
    same convention as :func:`drop_index`) and is clamped to the valid
    range. An unknown ``panel_id`` returns an unchanged copy.
    """
    if panel_id not in order:
        return list(order)
    rest = [pid for pid in order if pid != panel_id]
    idx = max(0, min(int(new_index), len(rest)))
    rest.insert(idx, panel_id)
    return rest


def drop_index(pointer_y: float, spans: list[tuple[float, float]]) -> int:
    """Insertion index for a pointer at ``pointer_y``.

    ``spans`` are the ``(top, bottom)`` extents of the panels the dragged
    one can be dropped around, in their current order and in the same
    coordinate system as ``pointer_y``. A pointer below a panel's midpoint
    means "after that panel"; the result ranges from 0 (before the first)
    to ``len(spans)`` (after the last).
    """
    idx = 0
    for top, bottom in spans:
        if pointer_y > (top + bottom) / 2.0:
            idx += 1
        else:
            break
    return idx


def right_column_width(content_width: int) -> int:
    """Canvas width of the card column whose cards ask for ``content_width`` px.

    Never below :data:`RIGHT_COLUMN_MIN_WIDTH`, wider when the cards ask for
    more: the rule of the grid column (``minsize=460``, weight 0) that held
    the cards before they moved into their own scroll canvas.
    """
    return max(RIGHT_COLUMN_MIN_WIDTH, int(content_width))


WHEEL_NOTCH = 120
"""``<MouseWheel>`` delta of one wheel notch (Windows, Tk 8.7+ on X11)."""


class WheelAccumulator:
    """Turn mouse-wheel events into scroll units: positive down, negative up.

    Tk 8.6 on X11 reports the wheel as buttons 4 (turned up) and 5 (turned
    down), one event per notch. Windows and Tk 8.7+ on X11 report
    ``<MouseWheel>`` with a ``delta`` (positive = up): a mouse notch is 120,
    while a precision touchpad sends many small deltas per gesture. Deltas
    are therefore summed and one unit is scrolled per 120 accumulated, so a
    touchpad gesture scrolls as far as the notches it adds up to, not one
    unit per event. Turning back, or an X11 button, drops the residue.
    """

    def __init__(self) -> None:
        self._residue = 0

    def feed(self, num: object, delta: object) -> int:
        if num in (4, 5):
            self._residue = 0
            return -1 if num == 4 else 1
        try:
            amount = int(delta or 0)
        except (TypeError, ValueError):
            return 0
        if amount == 0:
            return 0
        if self._residue and (self._residue > 0) != (amount > 0):
            self._residue = 0
        self._residue += amount
        notches = int(self._residue / WHEEL_NOTCH)  # truncates toward zero
        self._residue -= notches * WHEEL_NOTCH
        return -notches
