"""Pure helpers for the movable panels of the settings column.

The GUI stacks its cards (input, translation, profile, start, settings) in
one column and lets the user reorder them by dragging a handle. Everything
that does not need Tk lives here so it can be unit-tested without a display:
the canonical panel ids, the normalisation of the persisted order, the move
operation and the drop-position maths.
"""
from __future__ import annotations

PANEL_IDS: tuple[str, ...] = ("input", "translation", "profile", "start", "settings")
"""Canonical panel ids, in the default top-to-bottom order."""


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
