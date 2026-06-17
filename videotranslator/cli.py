"""Installable command-line entry point for VideoTranslatorAI."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int | None:
    """Run the legacy-compatible CLI, or launch the GUI when no args are given."""

    args = list(sys.argv[1:] if argv is None else argv)

    # Keep importing the legacy module lazy: package metadata and lightweight
    # imports should not eagerly initialize Tk-related code.
    import video_translator_gui as legacy

    if not args:
        legacy.App().mainloop()
        return 0

    old_argv = sys.argv[:]
    try:
        sys.argv = [old_argv[0], *args]
        legacy._cli()
    finally:
        sys.argv = old_argv
    return 0
