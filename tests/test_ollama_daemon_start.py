"""Starting the Ollama daemon when the port is already taken.

On a Windows 11 VM the freshly installed Ollama Desktop started its own
daemon a moment after our 12 s wait: our `ollama serve` then exited with
"bind: Only one usage of each socket address" and the app reported
"Daemon non avviato", while Ollama was in fact up and usable.
"""
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from videotranslator import ollama_runtime as rt
from videotranslator.ollama_runtime import _sha256_file

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


class _FakeInstallerProc:
    """What Popen returns for the silent installer: no output, exit code 0."""

    def __init__(self, argv):
        self.argv = argv
        self.stdout = iter(())
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        pass


class PinnedWindowsInstallerTests(unittest.TestCase):
    """OllamaSetup.exe comes from a pinned release and runs only if its SHA256 matches."""

    SIZE = 3 * 256 * 1024

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.requests = []
        self.launched = []

    def _urlopen(self, req, timeout=None):
        self.requests.append(req.full_url)
        return _FakeDownload(self.SIZE)

    def _popen(self, argv, **_kw):
        exe = Path(argv[0])
        self.launched.append((exe, exe.is_file()))
        return _FakeInstallerProc(argv)

    def _install(self, digest):
        with mock.patch("tempfile.gettempdir", return_value=self.tmp.name), \
                mock.patch("urllib.request.urlopen", side_effect=self._urlopen), \
                mock.patch.object(rt, "OLLAMA_WINDOWS_SETUP_SHA256", digest), \
                mock.patch.object(rt.subprocess, "Popen", side_effect=self._popen):
            return rt._ollama_install_windows(log_cb=lambda _s: None)

    def test_downloads_the_pinned_release(self):
        self._install("0" * 64)
        self.assertEqual(self.requests,
                         [f"https://github.com/ollama/ollama/releases/download/"
                          f"{rt.OLLAMA_VERSION}/OllamaSetup.exe"])

    def test_wrong_digest_never_runs_the_installer(self):
        ok, message = self._install("0" * 64)
        self.assertFalse(ok)
        self.assertIn("SHA256", message)
        self.assertEqual(self.launched, [])
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_matching_digest_runs_it_from_a_private_folder(self):
        import hashlib
        ok, message = self._install(hashlib.sha256(b"x" * self.SIZE).hexdigest())
        self.assertEqual((ok, message), (True, ""))
        [(exe, existed)] = self.launched
        self.assertTrue(existed)
        self.assertEqual(exe.name, "OllamaSetup.exe")
        # Not the predictable shared %TEMP%\OllamaSetup.exe: a folder of its own.
        self.assertNotEqual(exe.parent, Path(self.tmp.name))
        self.assertEqual(exe.parent.parent, Path(self.tmp.name))
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_the_pinned_digest_is_well_formed(self):
        self.assertRegex(rt.OLLAMA_VERSION, r"^v\d+\.\d+\.\d+$")
        self.assertRegex(rt.OLLAMA_WINDOWS_SETUP_SHA256, r"^[0-9a-f]{64}$")


def _make_tar_zst(path, members):
    """Write a real .tar.zst with ``members`` = {arcname: bytes}."""
    import io
    import subprocess
    import tarfile
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    subprocess.run(["zstd", "-q", "-o", str(path)], input=raw.getvalue(), check=True)


@unittest.skipIf(sys.platform.startswith("win"), "Linux installer")
@unittest.skipUnless(shutil.which("tar") and shutil.which("zstd"), "needs tar + zstd")
class LinuxUserInstallTests(unittest.TestCase):
    """Ollama on Linux: a verified per-user archive, no root, no curl | sh."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.dest = self.home / ".local" / "share" / "VideoTranslatorAI" / "ollama"
        self.archive = Path(self.tmp.name) / "ollama-linux-amd64.tar.zst"
        _make_tar_zst(self.archive, {"bin/ollama": b"#!/bin/sh\necho ollama\n",
                                     "lib/ollama/libggml.so": b"\x00lib"})

    def _digests(self, path=None):
        src = path or self.archive
        return {"ollama-linux-amd64.tar.zst": _sha256_file(src)}

    def _install(self, archive=None, digests=None):
        src = archive or self.archive
        return rt._ollama_install_linux(
            machine="x86_64", dest_dir=self.dest, log_cb=lambda _s: None,
            downloader=lambda url, out: shutil.copyfile(src, out),
            digests=digests if digests is not None else self._digests(src))

    def test_installs_into_the_user_dir_without_privilege(self):
        # Record every command run and prove none escalates (no pkexec/sudo,
        # no piped install.sh): the old path shelled out `curl ... | sh` as root.
        argvs = []
        real_run = rt.subprocess.run

        def spy(cmd, *a, **kw):
            argvs.append(cmd)
            return real_run(cmd, *a, **kw)

        with mock.patch.object(rt.subprocess, "run", side_effect=spy):
            ok, message = self._install()
        self.assertEqual((ok, message), (True, ""))
        self.assertTrue((self.dest / "bin" / "ollama").is_file())
        self.assertTrue((self.dest / "lib" / "ollama" / "libggml.so").is_file())
        self.assertEqual((self.dest / "bin" / "ollama").stat().st_mode & 0o111, 0o111)
        flat = " ".join(" ".join(map(str, cmd)) for cmd in argvs)
        for forbidden in ("pkexec", "sudo", "install.sh"):
            self.assertNotIn(forbidden, flat)
        self.assertTrue(all(cmd[0] == "tar" for cmd in argvs), argvs)

    def test_wrong_digest_leaves_nothing_behind(self):
        ok, message = self._install(digests={"ollama-linux-amd64.tar.zst": "0" * 64})
        self.assertFalse(ok)
        self.assertIn("SHA256", message)
        self.assertFalse(self.dest.exists())

    def test_an_archive_with_a_traversal_member_is_refused(self):
        evil = Path(self.tmp.name) / "evil.tar.zst"
        _make_tar_zst(evil, {"bin/ollama": b"x", "../escape.sh": b"pwned"})
        ok, message = self._install(archive=evil)
        self.assertFalse(ok)
        self.assertIn("..", message)
        self.assertFalse(self.dest.exists())

    def test_an_archive_without_the_binary_is_refused(self):
        nobin = Path(self.tmp.name) / "nobin.tar.zst"
        _make_tar_zst(nobin, {"lib/ollama/x.so": b"x"})
        ok, _message = self._install(archive=nobin)
        self.assertFalse(ok)
        self.assertFalse(self.dest.exists())

    def test_a_second_install_replaces_the_tree(self):
        self.assertTrue(self._install()[0])
        (self.dest / "bin" / "stale").write_text("old")
        self.assertTrue(self._install()[0])
        self.assertFalse((self.dest / "bin" / "stale").exists())

    def test_find_binary_sees_the_user_install(self):
        self._install()
        with mock.patch.object(rt.shutil, "which", return_value=None), \
                mock.patch.dict(os.environ, {"HOME": str(self.home)}, clear=False), \
                mock.patch.object(rt.Path, "home", staticmethod(lambda: self.home)):
            found = rt._ollama_find_binary()
        self.assertEqual(found, str(self.dest / "bin" / "ollama"))

    def test_missing_zstd_is_actionable(self):
        real_which = shutil.which
        with mock.patch.object(rt.shutil, "which",
                               side_effect=lambda n: None if n == "zstd" else real_which(n)):
            ok, message = self._install()
        self.assertFalse(ok)
        self.assertIn("zstd", message)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
