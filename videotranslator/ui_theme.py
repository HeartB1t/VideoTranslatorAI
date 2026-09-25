"""Theme definitions for the GUI: palettes, accents, scales and helpers.

Pure Python, no tkinter import: everything here is unit-testable without a
display. The Tk side (named fonts, ttk styles, live recolour) lives in
``videotranslator.ui_theme_tk``.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from dataclasses import dataclass


# -- Choices and defaults ---------------------------------------------

THEME_CHOICES: tuple[str, ...] = ("auto", "graphite", "slate", "light", "neon")
DEFAULT_THEME = "graphite"

ACCENTS: dict[str, str] = {
    "blue":   "#3574f0",
    "teal":   "#2aa198",
    "violet": "#7c5cff",
    "green":  "#3fa34d",
    "amber":  "#d9932a",
    "rose":   "#e0507a",
}
ACCENT_CHOICES: tuple[str, ...] = ("default",) + tuple(ACCENTS)
DEFAULT_ACCENT = "default"

SCALES: dict[str, float] = {"small": 0.9, "normal": 1.0, "large": 1.15, "xlarge": 1.3}
DEFAULT_SCALE = "normal"

DEFAULT_LANG = "it"

# Colours Tk gives to options a widget never set (X11 defaults, also the
# common Windows system colours once resolved). No palette role may equal
# one of these: the live recolour maps old hex -> new hex per role, so a
# widget left at a default would otherwise be recoloured as if it carried
# that role.
TK_DEFAULT_COLORS: frozenset[str] = frozenset({
    # X11 defaults
    "#000000", "#ffffff", "#d9d9d9", "#ececec", "#a3a3a3", "#c3c3c3",
    # Windows system colours as Tk resolves them (SystemButtonFace, button
    # face, SystemHighlight, SystemGrayText)
    "#f0f0f0", "#e1e1e1", "#0078d7", "#6d6d6d",
})


# -- Palette ------------------------------------------------------------

@dataclass(frozen=True)
class Palette:
    """A fully resolved theme. Colour fields are lower-case ``#rrggbb``."""

    name: str
    dark: bool
    font_family: str  # "sans" | "mono"
    BG: str
    SURFACE: str
    FIELD: str
    BORDER: str
    FG: str
    FG2: str
    SEL: str
    BTN: str
    ACC: str
    ACC_HOVER: str
    ACC_SOFT: str
    ACC_FG: str
    OK: str
    WARN: str
    ERR: str

    COLOR_FIELDS = (
        "BG", "SURFACE", "FIELD", "BORDER", "FG", "FG2", "SEL", "BTN",
        "ACC", "ACC_HOVER", "ACC_SOFT", "ACC_FG", "OK", "WARN", "ERR",
    )

    def colors(self) -> dict[str, str]:
        return {f: getattr(self, f) for f in self.COLOR_FIELDS}


# Base values per theme. ACC_HOVER / ACC_SOFT / ACC_FG are derived at
# resolve time from ACC and SURFACE, so they are not listed here.
_BASE_FIELDS = ("BG", "SURFACE", "FIELD", "BORDER", "FG", "FG2", "SEL", "BTN", "ACC", "OK", "WARN", "ERR")

THEMES: dict[str, dict[str, object]] = {
    # Neutral anthracite, single blue accent (JetBrains / VS Code feel).
    "graphite": {
        "dark": True, "font": "sans",
        "BG": "#1e1f22", "SURFACE": "#2b2d30", "FIELD": "#1a1b1e", "BORDER": "#3c3f44",
        "FG": "#dfe1e5", "FG2": "#8c9099", "SEL": "#2e436e", "BTN": "#393b40",
        "ACC": "#3574f0", "OK": "#5fb865", "WARN": "#d6a243", "ERR": "#e5484d",
    },
    # Cold blue-grey with muted teal accent (DaVinci / Linear feel).
    "slate": {
        "dark": True, "font": "sans",
        "BG": "#0f141b", "SURFACE": "#161d27", "FIELD": "#0c1015", "BORDER": "#263241",
        "FG": "#d7dee8", "FG2": "#7b8899", "SEL": "#1d3a3a", "BTN": "#1e2733",
        "ACC": "#2aa198", "OK": "#4caf7d", "WARN": "#c9a24a", "ERR": "#e0565b",
    },
    # Light, white cards, blue accent (Descript / Figma feel).
    "light": {
        "dark": False, "font": "sans",
        "BG": "#f3f4f6", "SURFACE": "#ffffff", "FIELD": "#fbfbfc", "BORDER": "#d9dce1",
        "FG": "#1f2328", "FG2": "#6b7280", "SEL": "#dbe6fd", "BTN": "#f6f7f9",
        "ACC": "#2563eb", "OK": "#16a34a", "WARN": "#b7791f", "ERR": "#d92d20",
    },
    # The historical neon look, kept as an option but with flat widgets.
    "neon": {
        "dark": True, "font": "mono",
        "BG": "#060612", "SURFACE": "#0d0d1f", "FIELD": "#11111b", "BORDER": "#1a1a3a",
        "FG": "#e0e0ff", "FG2": "#7878b8", "SEL": "#0d0d2a", "BTN": "#15152e",
        "ACC": "#00ff88", "OK": "#33ff99", "WARN": "#ff00aa", "ERR": "#ff4466",
    },
}


# -- Colour maths ---------------------------------------------------------

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    clamp = lambda x: max(0, min(255, int(round(x))))  # noqa: E731
    return "#%02x%02x%02x" % (clamp(r), clamp(g), clamp(b))


def mix(a_hex: str, b_hex: str, t: float) -> str:
    """Linear mix in sRGB space: ``t=1`` returns ``a``, ``t=0`` returns ``b``."""
    ar, ag, ab = _hex_to_rgb(a_hex)
    br, bg, bb = _hex_to_rgb(b_hex)
    return _rgb_to_hex(ar * t + br * (1 - t), ag * t + bg * (1 - t), ab * t + bb * (1 - t))


def lighten(value: str, amount: float) -> str:
    return mix("#ffffff", value, amount)


def darken(value: str, amount: float) -> str:
    return mix("#000000", value, amount)


def relative_luminance(value: str) -> float:
    """WCAG 2.x relative luminance of an ``#rrggbb`` colour."""
    def channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = _hex_to_rgb(value)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(a_hex: str, b_hex: str) -> float:
    la, lb = relative_luminance(a_hex), relative_luminance(b_hex)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def derive_accent(base_hex: str, surface_hex: str, dark: bool) -> tuple[str, str, str, str]:
    """Return ``(acc, hover, soft, fg)`` for an accent on a given surface.

    hover: accent lightened (dark themes) or darkened (light themes) by 12%.
    soft:  22% accent blended over the surface (selection / chip background).
    fg:    white when it already clears a 4.0 contrast ratio on the accent
           (matches the approved UI mockup, where mid-tone accents such as
           Graphite's blue show white text even though black scores a hair
           higher); otherwise whichever of black/white has the higher
           contrast, so low-contrast accents (teal, amber, ...) still fall
           back to black.
    """
    acc = base_hex.lower()
    hover = lighten(acc, 0.12) if dark else darken(acc, 0.12)
    soft = mix(acc, surface_hex, 0.22)
    white_contrast = contrast_ratio("#ffffff", acc)
    if white_contrast >= 4.0:
        fg = "#ffffff"
    else:
        fg = "#ffffff" if white_contrast >= contrast_ratio("#000000", acc) else "#000000"
    return acc, hover, soft, fg


def _find_free_value(start: str, seen: set[str]) -> str:
    """Find a colour close to ``start`` that is not in ``seen``.

    Walks outward with increasing distance (1, -1, 2, -2, ...) on the blue
    channel first, then green, then red, skipping out-of-range candidates.
    Bounded to at most 255 steps per channel, so it always terminates.
    Raises ``ValueError`` if no free value exists on any of the three
    channels (never happens with real palettes, but never loops either).
    """
    r0, g0, b0 = _hex_to_rgb(start)
    for channel in range(3):  # 0 = blue, 1 = green, 2 = red
        for step in range(1, 256):
            for delta in (step, -step):
                r, g, b = r0, g0, b0
                if channel == 0:
                    b = b0 + delta
                    in_range = 0 <= b <= 255
                elif channel == 1:
                    g = g0 + delta
                    in_range = 0 <= g <= 255
                else:
                    r = r0 + delta
                    in_range = 0 <= r <= 255
                if not in_range:
                    continue
                candidate = _rgb_to_hex(r, g, b)
                if candidate not in seen:
                    return candidate
    raise ValueError(f"cannot find a colour distinct from {start!r} near {seen!r}")


def _ensure_distinct(colors: dict[str, str],
                     reserved: frozenset[str] | set[str] = frozenset()) -> dict[str, str]:
    """Nudge duplicated values until every one is unique.

    The live recolour maps old hex -> new hex per role, so two roles sharing
    a hex would be indistinguishable. Duplicates, and values found in
    ``reserved``, are nudged to a nearby free value via ``_find_free_value``,
    which is bounded and never loops.
    """
    seen: set[str] = set(reserved)
    out: dict[str, str] = {}
    for key, value in colors.items():
        v = value.lower()
        if v in seen:
            v = _find_free_value(v, seen)
        seen.add(v)
        out[key] = v
    return out


def auto_is_dark(system_dark: bool | None) -> bool:
    """Whether ``auto`` paints dark: only a known light system gives light."""
    return system_dark is not False


def resolve_palette(theme: str, accent: str = DEFAULT_ACCENT,
                    system_dark: bool | None = None) -> Palette:
    """Build the fully resolved palette for ``theme`` and ``accent``.

    ``auto`` maps to ``light`` when ``system_dark`` is False, else ``graphite``
    (unknown counts as dark). Unknown or wrongly-typed names fall back to the
    defaults instead of raising.
    """
    if not isinstance(theme, str) or theme not in THEME_CHOICES:
        theme = DEFAULT_THEME
    if theme == "auto":
        theme = DEFAULT_THEME if auto_is_dark(system_dark) else "light"
    base = THEMES[theme]
    acc_base = ACCENTS[accent] if isinstance(accent, str) and accent in ACCENTS else str(base["ACC"])
    acc, hover, soft, fg = derive_accent(acc_base, str(base["SURFACE"]), bool(base["dark"]))
    raw = {f: str(base[f]) for f in _BASE_FIELDS}
    raw.update({"ACC": acc, "ACC_HOVER": hover, "ACC_SOFT": soft, "ACC_FG": fg})
    ordered = {f: raw[f] for f in Palette.COLOR_FIELDS}
    colors = _ensure_distinct(ordered, TK_DEFAULT_COLORS)
    return Palette(name=theme, dark=bool(base["dark"]), font_family=str(base["font"]), **colors)


# -- Settings -------------------------------------------------------------

def normalize_ui_settings(cfg: object, lang_codes: set[str] | None = None) -> dict:
    """Validate the UI keys of a config dict, replacing bad values by defaults."""
    src = cfg if isinstance(cfg, dict) else {}

    def pick(key: str, allowed, default: str) -> str:
        value = src.get(key)
        return value if isinstance(value, str) and value in allowed else default

    lang = src.get("ui_lang")
    if not isinstance(lang, str) or not lang or (lang_codes is not None and lang not in lang_codes):
        lang = DEFAULT_LANG
    return {
        "ui_theme": pick("ui_theme", THEME_CHOICES, DEFAULT_THEME),
        "ui_accent": pick("ui_accent", ACCENT_CHOICES, DEFAULT_ACCENT),
        "ui_scale": pick("ui_scale", SCALES, DEFAULT_SCALE),
        "ui_lang": lang,
    }


# -- Auto theme: cached system value -------------------------------------
#
# The OS probes below can take seconds, so the GUI runs them in the
# background and paints first with the value the previous run found, cached
# in the config under ``SYSTEM_DARK_KEY``.

SYSTEM_DARK_KEY = "ui_last_system_dark"


def cached_system_dark(cfg: object) -> bool | None:
    """The system value cached in a config dict; ``None`` if absent or malformed."""
    value = cfg.get(SYSTEM_DARK_KEY) if isinstance(cfg, dict) else None
    return value if isinstance(value, bool) else None


def settle_system_dark(previous: bool | None, detected: bool | None) -> bool | None:
    """The value to keep after a probe: a known answer wins, unknown keeps ``previous``."""
    return previous if detected is None else detected


def needs_auto_reapply(theme: object, before: bool | None, after: bool | None) -> bool:
    """Whether the system value moving from ``before`` to ``after`` changes the palette.

    Only the ``auto`` theme follows the system, and only a move between a
    dark and a light result changes what it paints (unknown counts as dark).
    """
    return theme == "auto" and auto_is_dark(before) != auto_is_dark(after)


# -- System dark-mode detection --------------------------------------------

def _run_quiet(cmd: list[str]) -> tuple[int, str] | None:
    """Run ``cmd`` with a short timeout; ``None`` when it cannot run at all."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=2,
            stdin=subprocess.DEVNULL, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.returncode, proc.stdout or ""


def detect_system_dark(sys_platform: str | None = None, runner=None,
                       winreg_module=None, env: dict | None = None) -> bool | None:
    """Best-effort OS dark-mode detection. ``None`` means unknown.

    Windows: registry ``AppsUseLightTheme``. macOS: ``defaults read -g
    AppleInterfaceStyle`` (non-zero exit means light). Linux: gsettings
    colour-scheme, then gtk-theme name, then xfconf theme name - except
    when ``XDG_CURRENT_DESKTOP`` names XFCE, where xfconf is checked first
    (gsettings is usually absent or stale on a plain XFCE session).
    """
    plat = sys_platform or sys.platform
    run = runner or _run_quiet
    environ = env if env is not None else os.environ

    if plat.startswith("win"):
        try:
            wr = winreg_module if winreg_module is not None else importlib.import_module("winreg")
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with wr.OpenKey(wr.HKEY_CURRENT_USER, key_path) as key:
                value, _ = wr.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
        except Exception:
            return None

    if plat == "darwin":
        res = run(["defaults", "read", "-g", "AppleInterfaceStyle"])
        if res is None:
            return None
        rc, out = res
        return False if rc != 0 else "dark" in out.lower()

    def check_color_scheme() -> bool | None:
        res = run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])
        if res is not None and res[0] == 0:
            out = res[1].lower()
            if "prefer-dark" in out:
                return True
            if "prefer-light" in out:
                return False
        return None

    def check_gtk_theme() -> bool | None:
        res = run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"])
        if res is not None and res[0] == 0 and res[1].strip():
            return "dark" in res[1].lower()
        return None

    def check_xfconf() -> bool | None:
        res = run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"])
        if res is not None and res[0] == 0 and res[1].strip():
            return "dark" in res[1].lower()
        return None

    is_xfce = "xfce" in str(environ.get("XDG_CURRENT_DESKTOP", "")).lower()
    checks = (check_xfconf, check_color_scheme, check_gtk_theme) if is_xfce \
        else (check_color_scheme, check_gtk_theme, check_xfconf)
    for check in checks:
        result = check()
        if result is not None:
            return result
    return None
