"""Where the bundled assets (icons, fonts and their licences) are.

The repository, the release ZIP and the Windows installation keep them in
``assets/`` next to the package. A wheel ships them inside the package, as
``videotranslator/assets`` (``package-dir`` in pyproject.toml): an ``assets``
folder at the top of site-packages could clash with other projects.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def assets_dir(package_dir: Path = PACKAGE_DIR) -> Path:
    """The assets folder: inside the package when installed from a wheel,
    otherwise next to it. Callers check the files they need, so a missing
    folder degrades to the default icon and fonts as before."""
    packaged = package_dir / "assets"
    if packaged.is_dir():
        return packaged
    return package_dir.parent / "assets"
