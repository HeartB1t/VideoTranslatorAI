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
import platform
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

KEEP_DAYS = 7
LOG_NAME = "videotranslator.log"
_STAMPED = re.compile(r"^\d{2}:\d{2}:\d{2} ")

# Progress bars in the file: the first update of an activity, then at most
# one every PROGRESS_MIN_INTERVAL_S seconds or PROGRESS_MIN_STEP percent, then
# the last one (100%, or the last seen when something else is logged).
PROGRESS_MIN_INTERVAL_S = 2.0
PROGRESS_MIN_STEP = 25


# -- Progress lines (tqdm style) -----------------------------------------------
#
# transformers ("Loading weights"), huggingface_hub downloads, faster-whisper
# and Demucs all print tqdm bars. Off a terminal each update comes on its own
# line, so a plain log would show hundreds of them: the panel keeps one line
# per activity and rewrites it, the file thins them (FileSink).

@dataclass(frozen=True)
class Progress:
    key: str              # the same for every update of one activity
    label: str            # "Loading weights", "model.safetensors", "" for a bare bar
    percent: int | None   # None for a bar without a total ("24it [00:01, 20it/s]")

    @property
    def done(self) -> bool:
        return self.percent is not None and self.percent >= 100


# The panel's own prefix, so a file line and a raw line give the same activity.
_PANEL_PREFIX = re.compile(r"^\d{2}:\d{2}:\d{2} .*?\[[a-z][a-z0-9_-]{1,15}\] ")
# " 12%|#1        | 24/200": percentage, bar, count.
_TQDM_BAR = re.compile(r"(?<![\w.])(\d{1,3})%\|[^|]*\|\s*([^\s\[]*)")
# "[00:01<00:03, 52it/s]", "[00:10, 4.5seconds/s]", "[.., 1.2s/it]" closing the line.
_TQDM_TAIL = re.compile(r"\[[^\[\]]*\b(?:[\w.]+/s|s/it)\]\s*$")
_TRAILING_COUNT = re.compile(r"\s*[\d.,]+\w*\s*$")


def progress_of(line: str) -> Progress | None:
    """The progress update carried by a raw log line, or None for anything else.

    Recognises tqdm output only: a ``NN%|bar|`` or a closing ``[elapsed,
    rate]`` bracket. A percentage inside a sentence ("CPU at 50%") is not
    progress. Handles a line with the panel prefix and one rewritten with
    ``\\r`` (the last state counts).
    """
    text = line.rstrip("\r").rsplit("\r", 1)[-1].strip()
    text = _PANEL_PREFIX.sub("", text, count=1)
    bar = _TQDM_BAR.search(text)
    if bar is not None:
        percent: int | None = int(bar.group(1))
        head, count = text[:bar.start()], bar.group(2)
    else:
        tail = _TQDM_TAIL.search(text)
        if tail is None:
            return None
        percent = None
        head, count = _TRAILING_COUNT.sub("", text[:tail.start()]), ""
    label = head.strip().rstrip(":").strip()
    total = count.rpartition("/")[2] if "/" in count else ""
    return Progress(key=f"{label}|{total}", label=label, percent=percent)


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
    get the date, so the time is not repeated. Progress updates of one
    activity (``progress_of``) are thinned: first, a few steps, last.
    """

    def __init__(self, directory: Path, *, keep_days: int = KEEP_DAYS,
                 clock=time.monotonic) -> None:
        self.path = Path(directory) / LOG_NAME
        self._lock = threading.Lock()
        self._pending = ""
        self._clock = clock
        self._progress_key: str | None = None      # activity of the bar being thinned
        self._progress_pending: str | None = None  # its last update, not written yet
        self._progress_written_pct: int | None = None
        self._progress_written_at = 0.0
        self._progress_written_text = ""
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
        formatted = prefix + line
        progress = progress_of(line)
        if progress is None:
            self._flush_progress()
            self._write(formatted)
            return
        body = _PANEL_PREFIX.sub("", line, count=1)
        if body == self._progress_written_text:
            return                             # tqdm repeats the final state on close
        if progress.key != self._progress_key:
            self._flush_progress()             # the last state of the previous bar
            self._progress_key = progress.key
            self._write_progress(formatted, body, progress)
            return
        percent = progress.percent
        due = progress.done or self._clock() - self._progress_written_at >= PROGRESS_MIN_INTERVAL_S
        if not due and percent is not None and self._progress_written_pct is not None:
            due = percent - self._progress_written_pct >= PROGRESS_MIN_STEP
        if due:
            self._write_progress(formatted, body, progress)
        else:
            self._progress_pending = formatted

    def _write_progress(self, formatted: str, body: str, progress: Progress) -> None:
        self._write(formatted)
        self._progress_pending = None
        self._progress_written_pct = progress.percent
        self._progress_written_at = self._clock()
        self._progress_written_text = body
        if progress.done:
            self._progress_key = None          # the next bar with this label is a new one

    def _flush_progress(self) -> None:
        if self._progress_pending is not None:
            self._write(self._progress_pending)
            self._progress_pending = None
        self._progress_key = None
        self._progress_written_text = ""

    def _write(self, formatted: str) -> None:
        try:
            self._logger.info(formatted)
        except Exception:                      # noqa: BLE001
            pass

    def close(self) -> None:
        with self._lock:
            if self._pending:
                self._emit(self._pending)
                self._pending = ""
            self._flush_progress()
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
# "12.3s ..." is a sentence line: its level comes from its shape, never from
# the words of the subtitle it carries.
_LIVE_SENTENCE = re.compile(r"^\d+(?:\.\d+)?s ")
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
        sentence = _LIVE_SENTENCE.match(body)
        if sentence:
            kept = body[sentence.end():].startswith("kept original")
            return ("warn" if kept else "info"), "live", body
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


# -- System facts for the session header (cheap, no torch, never raise) --------

# Installed distributions whose versions explain most bug reports.
LIBRARIES = ("torch", "faster-whisper", "ctranslate2", "transformers", "demucs",
             "coqui-tts", "pyannote.audio", "edge-tts", "yt-dlp", "deep-translator",
             "mpv", "av", "numpy", "keyring")


def os_description(sys_platform: str = sys.platform, *, os_release: str | None = None,
                   win_ver: tuple | None = None, mac_ver: tuple | None = None) -> str:
    """Distribution or edition, e.g. 'Kali GNU/Linux Rolling', 'Windows 11 (10.0.26100)'."""
    try:
        if sys_platform.startswith("linux"):
            if os_release is None:
                for path in ("/etc/os-release", "/usr/lib/os-release"):
                    try:
                        os_release = Path(path).read_text(encoding="utf-8")
                        break
                    except OSError:
                        continue
            for line in (os_release or "").splitlines():
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
            return "Linux"
        if sys_platform == "win32":
            release, version, _csd, _ptype = win_ver or platform.win32_ver()
            edition = ""
            try:
                edition = platform.win32_edition() or ""
            except Exception:                  # noqa: BLE001
                pass
            text = f"Windows {release} ({version})".strip()
            return f"{text} {edition}".strip()
        if sys_platform == "darwin":
            release = (mac_ver or platform.mac_ver())[0]
            return f"macOS {release}".strip()
    except Exception:                          # noqa: BLE001
        pass
    return platform.platform()


def library_versions(names=LIBRARIES, *, version=None) -> str:
    """'torch 2.6.0+cu124, faster-whisper 1.2.1, ...' for the installed ones."""
    if version is None:
        from importlib.metadata import version
    found = []
    for name in names:
        try:
            found.append(f"{name} {version(name)}")
        except Exception:                      # noqa: BLE001 - not installed
            continue
    return ", ".join(found)


_SMI_DRIVER = re.compile(r"Driver Version:\s*([\w.]+)")
_SMI_CUDA = re.compile(r"CUDA Version:\s*([\w.]+)")


def parse_nvidia_smi_banner(text: str) -> tuple[str, str]:
    """(driver, CUDA) from the header of plain ``nvidia-smi`` output."""
    driver = _SMI_DRIVER.search(text or "")
    cuda = _SMI_CUDA.search(text or "")
    return (driver.group(1) if driver else "", cuda.group(1) if cuda else "")


def tool_output(cmd: list[str], *, run=None, timeout: float = 5.0) -> str:
    """A tool's standard output ('' when missing or failing); no console
    window on Windows."""
    import subprocess
    from .subprocess_utils import no_window_kwargs
    run = run or subprocess.run
    try:
        out = run(cmd, capture_output=True, text=True, timeout=timeout,
                  stdin=subprocess.DEVNULL, **no_window_kwargs(sys.platform))
        return out.stdout or ""
    except Exception:                          # noqa: BLE001
        return ""


def tool_first_line(cmd: list[str], *, run=None, timeout: float = 5.0) -> str:
    """First line of a tool's output ('' when missing or failing)."""
    lines = tool_output(cmd, run=run, timeout=timeout).strip().splitlines()
    return lines[0] if lines else ""


def ffmpeg_version(first_line: str) -> str:
    """'ffmpeg version 8.1.2-2+b3 Copyright ...' -> '8.1.2-2+b3'."""
    parts = (first_line or "").split()
    return parts[2] if len(parts) > 2 and parts[1] == "version" else ""
