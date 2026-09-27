"""The header's settings gear, drawn by the app instead of a font glyph.

"⚙" (U+2699) took the glyph of the system font: a filled gear on Linux, a
thin and uneven outline on Windows. Here a filled gear with a round hole
is rasterised in pure Python (no Pillow), anti-aliased by supersampling and
blended over the header background, so it looks the same on both systems
and follows the theme: the caller rebuilds it when the colours change.
"""

from __future__ import annotations

import math
from functools import lru_cache

from .ui_theme import mix

TEETH = 8
# Radii as fractions of the image side: tooth tips, the valleys between the
# teeth, the hole. Tooth width as a share of one pitch, at the tip and at
# the root (a trapezoid, wider at the root like a real gear).
_OUTER, _ROOT, _HOLE = 0.47, 0.35, 0.15
_TIP_SHARE, _ROOT_SHARE = 0.40, 0.62
_SAMPLES = 4                      # per side: 16 samples a pixel


def gear_outline(teeth: int = TEETH) -> list[tuple[float, float]]:
    """The outer edge of the gear as a polygon in the unit square, centred
    on (0.5, 0.5), first tooth straight up. Five points per tooth: two at
    the root, two at the tip, one in the valley that follows, which keeps
    the valley on the root circle."""
    pitch = 2 * math.pi / teeth
    points: list[tuple[float, float]] = []
    for index in range(teeth):
        centre = index * pitch - math.pi / 2
        for angle, radius in ((centre - _ROOT_SHARE * pitch / 2, _ROOT),
                              (centre - _TIP_SHARE * pitch / 2, _OUTER),
                              (centre + _TIP_SHARE * pitch / 2, _OUTER),
                              (centre + _ROOT_SHARE * pitch / 2, _ROOT),
                              (centre + pitch / 2, _ROOT)):
            points.append((0.5 + radius * math.cos(angle), 0.5 + radius * math.sin(angle)))
    return points


def _inside(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Even-odd rule."""
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            crossing = (previous_x - current_x) * (y - current_y) / (previous_y - current_y)
            if x < crossing + current_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


@lru_cache(maxsize=8)
def gear_coverage(size: int) -> tuple[tuple[float, ...], ...]:
    """Share (0 to 1) of each pixel the gear covers, row by row."""
    polygon = gear_outline()
    step = 1.0 / _SAMPLES
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            hits = 0
            for sy in range(_SAMPLES):
                dy = (py + (sy + 0.5) * step) / size - 0.5
                for sx in range(_SAMPLES):
                    dx = (px + (sx + 0.5) * step) / size - 0.5
                    distance = math.hypot(dx, dy)
                    if distance < _HOLE or distance > _OUTER:
                        continue
                    if distance <= _ROOT or _inside(dx + 0.5, dy + 0.5, polygon):
                        hits += 1
            row.append(hits / (_SAMPLES * _SAMPLES))
        rows.append(tuple(row))
    return tuple(rows)


def gear_pixels(size: int, color: str, background: str) -> list[list[str]]:
    """``#rrggbb`` per pixel: ``color`` blended over ``background`` by coverage."""
    return [[mix(color, background, share) for share in row] for row in gear_coverage(size)]


def gear_image(master, size: int, color: str, background: str):
    """A ``size`` x ``size`` Tk image of the gear; keep a reference to it."""
    import tkinter as tk
    image = tk.PhotoImage(master=master, width=size, height=size)
    image.put(" ".join("{" + " ".join(row) + "}" for row in gear_pixels(size, color, background)))
    return image
