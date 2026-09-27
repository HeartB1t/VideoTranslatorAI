"""Starting the Ollama daemon when the port is already taken.

On a Windows 11 VM the freshly installed Ollama Desktop started its own
daemon a moment after our 12 s wait: our `ollama serve` then exited with
"bind: Only one usage of each socket address" and the app reported
"Daemon non avviato", while Ollama was in fact up and usable.
"""
import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from videotranslator import ollama_runtime as rt

WINDOWS_BIND_ERROR = (
    "Error: listen tcp 127.0.0.1:11434: bind: Only one usage of each socket address "
    "(protocol/network address/port) is normally permitted."
)


@unittest.skipIf(sys.platform.startswith("win"), "fake binary is a POSIX script")
class StartDaemonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logged = []

    def _fake_ollama(self, message: str) -> str:
        """An `ollama` that prints ``message`` and exits 1 when asked to serve."""
        path = Path(self.tmp.name) / "ollama"
        path.write_text(f"#!/bin/sh\necho '{message}'\nexit 1\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def _start(self, binary, **kw):
        return rt._ollama_start_daemon(binary, api_url="http://localhost:11434",
                                       log_cb=self.logged.append, **kw)

    def test_port_taken_by_a_running_daemon_is_a_success(self):
        answers = iter([False] + [True] * 50)        # the desktop daemon comes up
        with mock.patch.object(rt, "_ollama_is_daemon_running",
                               side_effect=lambda *a, **k: next(answers)):
            ok, message = self._start(self._fake_ollama(WINDOWS_BIND_ERROR),
                                      wait_seconds=5.0, conflict_wait=5.0)
        self.assertEqual((ok, message), (True, ""))
        text = "".join(self.logged)
        self.assertIn("11434", text)
        self.assertNotIn("exited early", text)

    def test_linux_and_italian_windows_wordings_count_as_a_taken_port(self):
        for wording in ("bind: address already in use",
                        "bind: Di norma è consentito un solo utilizzo di ogni indirizzo"):
            with self.subTest(wording=wording):
                self.assertTrue(rt._is_port_conflict(f"Error: listen tcp :11434: {wording}"))
        self.assertFalse(rt._is_port_conflict("Error: invalid configuration"))

    def test_port_taken_by_something_that_never_answers_is_still_an_error(self):
        with mock.patch.object(rt, "_ollama_is_daemon_running", return_value=False):
            ok, message = self._start(self._fake_ollama(WINDOWS_BIND_ERROR),
                                      wait_seconds=5.0, conflict_wait=0.3)
        self.assertFalse(ok)
        self.assertIn("rc=1", message)
        self.assertIn("exited early", "".join(self.logged))

    def test_another_failure_does_not_wait_for_the_port(self):
        with mock.patch.object(rt, "_ollama_is_daemon_running", return_value=False), \
                mock.patch.object(rt, "_ollama_wait_for_daemon") as wait:
            started = time.monotonic()
            ok, _message = self._start(self._fake_ollama("Error: invalid configuration"),
                                       wait_seconds=5.0, conflict_wait=30.0)
        self.assertFalse(ok)
        wait.assert_not_called()
        self.assertLess(time.monotonic() - started, 5.0)


class _FakeDownload:
    """What urlopen returns: a sized body read in chunks."""

    def __init__(self, size: int, fail_after: int | None = None):
        self.headers = {"Content-Length": str(size)}
        self._left, self._sent, self._fail_after = size, 0, fail_after

    def read(self, n):
        if self._fail_after is not None and self._sent >= self._fail_after:
            raise OSError("connection reset")
        n = min(n, self._left)
        self._left -= n
        self._sent += n
        return b"x" * n

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class InstallerDownloadProgressTests(unittest.TestCase):
    """The ~1 GB OllamaSetup.exe download: one line rewritten in place (\\r),
    not twenty "Download... N%" lines in the log panel and file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logged = []

    def _install(self, body):
        with mock.patch("tempfile.gettempdir", return_value=self.tmp.name), \
                mock.patch("urllib.request.urlopen", return_value=body), \
                mock.patch.object(rt.subprocess, "Popen", side_effect=OSError("stop here")):
            return rt._ollama_install_windows(log_cb=self.logged.append)

    def _progress(self):
        return [text for text in self.logged if "Download..." in text]

    def test_progress_rewrites_one_line_and_ends_it_once(self):
        self._install(_FakeDownload(40 * 256 * 1024))
        progress = self._progress()
        self.assertGreater(len(progress), 5)
        self.assertTrue(all(text.startswith("\r") for text in progress))
        self.assertTrue(all(not text.endswith("\n") for text in progress))
        self.assertIn("Download... 100%", progress[-1])
        text = "".join(self.logged)
        self.assertEqual(text.count("Download... 100%\n"), 1)

    def test_a_broken_download_still_ends_the_progress_line(self):
        ok, message = self._install(_FakeDownload(40 * 256 * 1024, fail_after=10 * 256 * 1024))
        self.assertFalse(ok)
        self.assertIn("Download fallito", message)
        text = "".join(self.logged)
        self.assertTrue(text.endswith("\n"))
        self.assertNotIn("Download... 100%", text)


if __name__ == "__main__":
    unittest.main()
