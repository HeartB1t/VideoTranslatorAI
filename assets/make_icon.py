"""
Generate the Video Translator AI launcher icon.

Produces:
    assets/icon.png          (1024x1024 source)
    assets/icon_256.png      (256x256 for Linux .desktop)
    assets/icon.ico          (Windows .ico multi-res: 16/32/48/64/128/256)

Design: dark blue-purple squircle, centered white play triangle,
translation glyph pair (A → 文) below, AI sparkle in upper right.
Palette inspired by the Catppuccin Mocha theme already used in the GUI.

Run:
    python3 assets/make_icon.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent
SIZE = 1024  # source resolution

# Catppuccin Mocha inspired palette
MAUVE_DARK = (24, 24, 37)       # base / dark backstop
BLUE_ACC   = (137, 180, 250)    # accent blue
MAUVE_ACC  = (203, 166, 247)    # accent mauve
WHITE      = (245, 245, 255)
YELLOW     = (249, 226, 175)


def squircle_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    """Return an L-mode mask of a rounded square (iOS-like)."""
    r = int(size * radius_ratio)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=255)
    return m


def radial_gradient(size: int, inner: tuple[int, int, int], outer: tuple[int, int, int]) -> Image.Image:
    """Create a radial gradient: inner colour at the centre, outer at the corners."""
    cx, cy = size / 2, size / 2
    max_d = math.hypot(cx, cy)
    img = Image.new("RGB", (size, size), outer)
    px = img.load()
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - cx, y - cy) / max_d
            d = min(1.0, d)
            r = int(inner[0] * (1 - d) + outer[0] * d)
            g = int(inner[1] * (1 - d) + outer[1] * d)
            b = int(inner[2] * (1 - d) + outer[2] * d)
            px[x, y] = (r, g, b)
    return img


def linear_gradient_v(size: int, top: tuple[int, int, int], bot: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (size, size), top)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return img


def draw_play_triangle(base: Image.Image) -> None:
    """Draw a centred, slightly right-shifted play triangle in white."""
    size = base.size[0]
    cx, cy = size / 2, size / 2 - size * 0.04  # shift up a touch to make room for glyphs below
    # equilateral-ish triangle with rounded corners, pointing right
    side = size * 0.34
    # Triangle points
    p1 = (cx - side * 0.30, cy - side * 0.55)
    p2 = (cx - side * 0.30, cy + side * 0.55)
    p3 = (cx + side * 0.72, cy)
    tri = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tri)
    d.polygon([p1, p2, p3], fill=(*WHITE, 255))
    # Soft inner shadow for depth
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    off = int(size * 0.008)
    ds.polygon([(p1[0] + off, p1[1] + off),
                (p2[0] + off, p2[1] + off),
                (p3[0] + off, p3[1] + off)], fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=size * 0.012))
    base.alpha_composite(shadow)
    base.alpha_composite(tri)


def find_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_translation_glyphs(base: Image.Image) -> None:
    """Draw 'A → 文' under the play triangle, in a translucent pill."""
    size = base.size[0]
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Pill background
    pill_w = int(size * 0.48)
    pill_h = int(size * 0.15)
    pill_x = (size - pill_w) // 2
    pill_y = int(size * 0.68)
    d.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=pill_h // 2,
        fill=(0, 0, 0, 110),
    )

    # Glyphs
    latin_font = find_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        int(size * 0.085),
    )
    cjk_font = find_font(
        [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ],
        int(size * 0.085),
    )

    # We draw three elements centred inside the pill: "A"  "→"  "文"
    parts = [("A", latin_font), ("→", latin_font), ("文", cjk_font)]
    gap = int(size * 0.02)

    # Measure total width
    widths = []
    for text, font in parts:
        bbox = font.getbbox(text)
        widths.append(bbox[2] - bbox[0])
    total = sum(widths) + gap * (len(parts) - 1)
    x = pill_x + (pill_w - total) // 2
    cy = pill_y + pill_h // 2
    for (text, font), w in zip(parts, widths):
        bbox = font.getbbox(text)
        h = bbox[3] - bbox[1]
        y = cy - h // 2 - bbox[1]
        d.text((x, y), text, font=font, fill=(*WHITE, 240))
        x += w + gap

    base.alpha_composite(overlay)


def draw_sparkle(base: Image.Image) -> None:
    """Four-point sparkle in the upper-right for the AI vibe."""
    size = base.size[0]
    cx = int(size * 0.80)
    cy = int(size * 0.22)
    r_outer = int(size * 0.075)
    r_inner = int(r_outer * 0.32)

    sparkle = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sparkle)

    # four-point star as two overlapping diamonds
    pts = []
    for i in range(8):
        angle = math.radians(90 * (i // 2) + (45 if i % 2 else 0))
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    d.polygon(pts, fill=(*YELLOW, 255))

    # soft glow behind the sparkle
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.ellipse(
        (cx - int(r_outer * 1.8), cy - int(r_outer * 1.8),
         cx + int(r_outer * 1.8), cy + int(r_outer * 1.8)),
        fill=(*YELLOW, 70),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size * 0.025))
    base.alpha_composite(glow)
    base.alpha_composite(sparkle)


def draw_highlight(base: Image.Image) -> None:
    """Subtle top highlight for a glossy-but-flat feel."""
    size = base.size[0]
    hl = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(hl)
    d.ellipse(
        (-int(size * 0.2), -int(size * 0.55),
         int(size * 1.2), int(size * 0.45)),
        fill=(255, 255, 255, 40),
    )
    hl = hl.filter(ImageFilter.GaussianBlur(radius=size * 0.04))
    base.alpha_composite(hl)


def build(size: int = SIZE) -> Image.Image:
    # Background: radial gradient from mauve to deep navy, then masked to squircle
    bg = radial_gradient(size, MAUVE_ACC, MAUVE_DARK)
    # Blend with a vertical linear gradient for extra colour depth
    bg2 = linear_gradient_v(size, BLUE_ACC, MAUVE_DARK)
    blended = Image.blend(bg, bg2, 0.55).convert("RGBA")

    mask = squircle_mask(size)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(blended, (0, 0), mask)

    draw_highlight(canvas)
    draw_play_triangle(canvas)
    draw_translation_glyphs(canvas)
    draw_sparkle(canvas)

    return canvas


def main() -> None:
    icon = build(SIZE)
    icon.save(OUT / "icon.png", "PNG")
    icon.resize((256, 256), Image.LANCZOS).save(OUT / "icon_256.png", "PNG")

    # Windows .ico: multi-res, PIL handles embedded sizes automatically
    icon.save(
        OUT / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Wrote: {OUT / 'icon.png'}")
    print(f"Wrote: {OUT / 'icon_256.png'}")
    print(f"Wrote: {OUT / 'icon.ico'}")


if __name__ == "__main__":
    main()
