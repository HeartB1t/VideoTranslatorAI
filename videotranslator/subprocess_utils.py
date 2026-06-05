"""Subprocess helper functions.

The runtime still launches tools from the legacy file, but these small helpers
make the subprocess contract explicit and testable before moving call sites.
"""

from __future__ import annotations

import locale
import shlex
import subprocess
import threading
from os import PathLike
from typing import Any, Sequence


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


def common_subprocess_kwargs(
    sys_platform: str,
    *,
    stdin_devnull: bool = False,
    stdout_pipe: bool = False,
    stderr_pipe: bool = False,
) -> dict[str, object]:
    """Return common kwargs suitable for subprocess.run and subprocess.Popen."""
    kwargs = text_subprocess_kwargs(sys_platform)
    if stdin_devnull:
        kwargs["stdin"] = subprocess.DEVNULL
    if stdout_pipe:
        kwargs["stdout"] = subprocess.PIPE
    if stderr_pipe:
        kwargs["stderr"] = subprocess.PIPE
    return kwargs


class ActiveSubprocessRegistry:
    """Thread-safe registry for subprocesses that should be stopped on exit."""

    def __init__(self) -> None:
        self._items: set[Any] = set()
        self._lock = threading.Lock()

    def register(self, proc: Any) -> None:
        with self._lock:
            self._items.add(proc)

    def unregister(self, proc: Any) -> None:
        with self._lock:
            self._items.discard(proc)

    def snapshot(self) -> list[Any]:
        with self._lock:
            return list(self._items)
