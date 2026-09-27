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


# -- One line format for the panel and the file -------------------------------
#
#   HH:MM:SS LEVEL [area] message
#
# The app's own events come with their area and level; everything else (print
# from the pipeline, library output, the live session's lines) is classified
# from the start of the line by ``classify``.

LEVELS = ("info", "warn", "error")

# Event key -> area / level (keys of ui_strings_log).
EVENT_AREAS = {
    "log_click": "ui", "log_click_disabled": "ui", "log_on": "ui", "log_off": "ui",
    "log_choice": "ui", "log_window": "ui", "log_settings": "ui",
    "log_player": "player", "log_live": "live", "log_live_start": "live",
    "log_live_end": "live", "log_session_live": "live", "log_vp": "voice",
    "log_error": "app", "log_started": "app", "log_file": "app",
}
EVENT_LEVELS = {"log_error": "error"}

_AREA_TAG = re.compile(r"^\[([a-z][a-z0-9_-]{1,15})\]\s+(.*)$", re.S)
_ERROR_WORDS = re.compile(r"\b(failed|fatal|crash(ed)?)\b", re.I)
_LIVE_WARN = re.compile(r"\b(lost|kept original|refused|unavailable|falling behind|"
                        r"still alive|not fully configured)\b", re.I)
_EXCEPTION_LINE = re.compile(r"^[A-Za-z_][\w.]*(Error|Exception|Warning)\b.*:")
_STEP = re.compile(r"^\[\d+/\d+\]")


def classify(fragment: str) -> tuple[str | None, str, str]:
    """``(level, area, message)`` for the start of a raw log line.

    ``level`` is None for a continuation line (indented, like a traceback's
    frames): it keeps the previous line's level and gets no prefix.
    """
    text = fragment.rstrip("\n")
    if not text or text[0] in " \t":
        return None, "", fragment
    if text.startswith("Traceback (most recent call last)") or _EXCEPTION_LINE.match(text):
        return "error", "app", text
    if text.startswith("live: "):
        body = text[len("live: "):]
        if _ERROR_WORDS.search(body):
            return "error", "live", body
        return ("warn" if _LIVE_WARN.search(body) else "info"), "live", body
    for marker, level in (("[!] ", "warn"), ("[+] ", "info"), ("[i] ", "info"),
                          ("[✗] ", "error"), ("[x] ", "error"), ("[✓] ", "info")):
        if text.startswith(marker):
            return level, "app", (text if marker in ("[✓] ",) else text[len(marker):])
    if _STEP.match(text):
        return "info", "job", text
    match = _AREA_TAG.match(text)
    if match:
        area, body = match.group(1), match.group(2)
        if area == "mpv":
            return "info", "mpv", body          # its own warnings are mostly harmless
        if _ERROR_WORDS.search(body):
            return "error", area, body
        return "info", area, body
    if text.startswith(("ERROR", "Error:")):
        return "error", "app", text
    if text.startswith(("WARNING", "Warning:")):
        return "warn", "app", text
    return "info", "app", text


def level_words(words: dict[str, str]) -> dict[str, str]:
    """Level words padded to the same width, so the areas line up."""
    width = max(len(w) for w in words.values())
    return {level: word.ljust(width) for level, word in words.items()}


def prefix(level: str, area: str, words: dict[str, str], *, clock=time.localtime) -> str:
    return f"{time.strftime('%H:%M:%S', clock())} {words[level]} [{area}] "


def git_commit(root: Path) -> str:
    """Short commit of a source checkout (``.git`` files only, no git process);
    "" for an installed copy without ``.git``."""
    try:
        git = Path(root) / ".git"
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref: "):
            return head[:7]
        ref = head[5:]
        ref_file = git / ref
        if ref_file.is_file():
            return ref_file.read_text(encoding="utf-8").strip()[:7]
        packed = git / "packed-refs"
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.endswith(" " + ref):
                return line.split(" ", 1)[0][:7]
    except Exception:                          # noqa: BLE001
        pass
    return ""
