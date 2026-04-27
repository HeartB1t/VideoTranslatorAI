"""Subprocess helper functions.

The runtime still launches tools from the legacy file, but these small helpers
make the subprocess contract explicit and testable before moving call sites.
"""

from __future__ import annotations

import locale
import shlex
from os import PathLike
from typing import Sequence


CommandPart = str | PathLike[str]


def normalize_command(cmd: Sequence[CommandPart]) -> list[str]:
    """Validate and stringify a subprocess command list."""
    if isinstance(cmd, (str, bytes)):
        raise TypeError("subprocess commands must be sequences, not shell strings")
    normalized = [str(part) for part in cmd]
    if not normalized or not normalized[0]:
        raise ValueError("subprocess command cannot be empty")
    return normalized


def command_for_log(cmd: Sequence[CommandPart]) -> str:
    """Return a shell-like representation for logs only."""
    return " ".join(shlex.quote(part) for part in normalize_command(cmd))


def text_subprocess_kwargs(sys_platform: str) -> dict[str, object]:
    """Return stable text-mode kwargs for subprocess calls."""
    if sys_platform == "win32":
        return {"text": True, "encoding": "utf-8", "errors": "replace"}
    return {
        "text": True,
        "encoding": locale.getpreferredencoding(False),
        "errors": "replace",
    }

