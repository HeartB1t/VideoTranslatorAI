"""Make the fonts bundled in ``assets/fonts`` visible to Tk.

The skins use two free fonts (SIL Open Font License, licences next to them):
Pixelify Sans for the pocket-console looks and VT323 for the phosphor monitor.
Tk 8.6 cannot load a font file, so they are registered with the OS before
the first ``tk.Tk()``; after that Tk would not see them.

- Linux (and other X11 systems): copied into ``~/.local/share/fonts/
  VideoTranslatorAI``, which fontconfig reads when Tk starts (no fc-cache).
- macOS: copied into ``~/Library/Fonts``.
- Windows: ``AddFontResourceExW`` with ``FR_PRIVATE``: only this process
  sees them, no administrator rights and no registry change.

Everything is best effort: on any error the skin keeps its colours and falls
back to the system sans-serif or monospace font.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Callable

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = PACKAGE_ROOT / "assets" / "fonts"
FONT_FILES = ("PixelifySans.ttf", "VT323-Regular.ttf")
FR_PRIVATE = 0x10
USER_FONT_SUBDIR = "VideoTranslatorAI"


def user_font_dir(sys_platform: str, home: Path) -> Path:
    if sys_platform == "darwin":
        return home / "Library" / "Fonts"
    return home / ".local" / "share" / "fonts" / USER_FONT_SUBDIR


def _windows_add_font() -> Callable[[str], bool]:
    import ctypes

    gdi32 = ctypes.WinDLL("gdi32")
    add = gdi32.AddFontResourceExW
    add.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p)
    add.restype = ctypes.c_int
    return lambda path: add(path, FR_PRIVATE, None) > 0


def register_bundled_fonts(fonts_dir: Path = FONTS_DIR, *,
                           sys_platform: str = sys.platform,
                           home: Path | None = None,
                           add_font: Callable[[str], bool] | None = None) -> list[str]:
    """Register the bundled fonts; return the file names made available.

    Call it before creating the Tk root. Never raises.
    """
    done: list[str] = []
    try:
        sources = [Path(fonts_dir) / name for name in FONT_FILES]
        sources = [path for path in sources if path.is_file()]
        if not sources:
            return done
        if sys_platform == "win32":
            add = add_font or _windows_add_font()
            for path in sources:
                try:
                    if add(str(path)):
                        done.append(path.name)
                except Exception:              # noqa: BLE001
                    continue
            return done
        target = user_font_dir(sys_platform, Path(home) if home else Path.home())
        target.mkdir(parents=True, exist_ok=True)
        for path in sources:
            dest = target / path.name
            try:
                if not dest.is_file() or dest.stat().st_size != path.stat().st_size:
                    part = dest.with_name(dest.name + ".part")
                    shutil.copyfile(path, part)
                    part.replace(dest)
                done.append(path.name)
            except OSError:
                continue
    except Exception:                          # noqa: BLE001 - fonts are cosmetic
        pass
    return done
