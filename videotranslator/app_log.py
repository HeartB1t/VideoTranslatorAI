"""The application log file: everything the Log panel shows, kept on disk.

Every line of the Log panel (pipeline output, button clicks, results,
errors with their traceback) is also written to ``<config dir>/logs/
videotranslator.log`` with its date and time. A new file starts every day
at midnight and the files older than ``KEEP_DAYS`` days are deleted, so the
log a user attaches to a bug report covers the last week.

Pure standard library, Windows and Linux alike. Never raises: a log that
cannot be written must not break the app.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import threading
import time
from pathlib import Path

KEEP_DAYS = 7
LOG_NAME = "videotranslator.log"
_STAMPED = re.compile(r"^\d{2}:\d{2}:\d{2} ")


def log_dir_for(config_path: Path) -> Path:
    """The logs folder next to the config file."""
    return Path(config_path).parent / "logs"


def stamp(text: str, *, clock=time.localtime) -> str:
    """``HH:MM:SS `` prefix for an event line of the Log panel."""
    return time.strftime("%H:%M:%S ", clock()) + text


class FileSink:
    """Writes the text of the Log panel to a daily rotating file.

    ``write`` takes raw panel text (pieces of lines, ``\\r`` progress bars
    included); complete lines are written with the date and time in front.
    Lines that already start with ``HH:MM:SS`` (the app's own events) only
    get the date, so the time is not repeated.
    """

    def __init__(self, directory: Path, *, keep_days: int = KEEP_DAYS) -> None:
        self.path = Path(directory) / LOG_NAME
        self._lock = threading.Lock()
        self._pending = ""
        self._logger = logging.getLogger(f"videotranslatorai.file.{id(self)}")
        self._logger.propagate = False
        self._logger.setLevel(logging.INFO)
        self._handler: logging.Handler | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.TimedRotatingFileHandler(
                self.path, when="midnight", backupCount=keep_days, encoding="utf-8",
                delay=True)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._handler = handler
        except Exception:                      # noqa: BLE001 - no file log, the app goes on
            self._handler = None

    @property
    def ok(self) -> bool:
        return self._handler is not None

    def write(self, text: str) -> None:
        if not text or self._handler is None:
            return
        with self._lock:
            data = self._pending + text
            lines = data.split("\n")
            self._pending = lines.pop()
            for line in lines:
                self._emit(line)

    def _emit(self, line: str) -> None:
        # A progress bar rewrites its line with \r: keep only the last state.
        line = line.rstrip("\r").rsplit("\r", 1)[-1].rstrip()
        if not line:
            return
        now = time.localtime()
        prefix = time.strftime("%Y-%m-%d ", now)
        if not _STAMPED.match(line):
            prefix += time.strftime("%H:%M:%S ", now)
        try:
            self._logger.info(prefix + line)
        except Exception:                      # noqa: BLE001
            pass

    def close(self) -> None:
        with self._lock:
            if self._pending:
                self._emit(self._pending)
                self._pending = ""
            if self._handler is not None:
                try:
                    self._handler.close()
                    self._logger.removeHandler(self._handler)
                except Exception:              # noqa: BLE001
                    pass
                self._handler = None


def short(text: object, limit: int = 80) -> str:
    """One-line label for the log (button texts can wrap)."""
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"
