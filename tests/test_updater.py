"""Windows updater (spec docs/superpowers/specs/2026-09-27-windows-updater-design.md).

Hermetic: every download goes through a fake HTTP client, archives are built in
memory. No network, no Windows.
"""

import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from videotranslator import updater as up
from videotranslator.libmpv_runtime import DownloadError

API = up.API_LATEST
LATEST_PAGE = f"https://github.com/{up.REPO}/releases/latest"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_zip(version="2.1.0", *, root=None, members=None, extra=None) -> bytes:
    """A release archive: one top folder with the installer and the package."""
    root = root or f"VideoTranslatorAI-v{version}"
    files = members if members is not None else {
        f"{root}/setup_windows.bat": b"@echo off\r\n",
        f"{root}/video_translator_gui.py": b"print('app')\n",
        f"{root}/videotranslator/__init__.py": f'__version__ = "{version}"\n'.encode(),
        f"{root}/videotranslator/updater.py": b"# updater\n",
    }
    files = dict(files, **(extra or {}))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            if isinstance(data, zipfile.ZipInfo):   # a hand-built entry (symlink)
                zf.writestr(data, b"target")
            else:
                zf.writestr(name, data)
    return buf.getvalue()


def symlink_entry(name):
    info = zipfile.ZipInfo(name)
    info.external_attr = (0o120777 << 16)   # S_IFLNK: a symbolic link
    return info


def asset_url(version):
    return f"https://github.com/{up.REPO}/releases/download/v{version}/VideoTranslatorAI-v{version}.zip"


def sums_url(version):
    return f"https://github.com/{up.REPO}/releases/download/v{version}/sha256.txt"


def api_release(version, *, digest=True, data=None, name=None):
    data = make_zip(version) if data is None else data
    asset = {"name": name or f"VideoTranslatorAI-v{version}.zip",
             "browser_download_url": asset_url(version)}
    if digest:
        asset["digest"] = "sha256:" + _sha(data)
    return {"tag_name": f"v{version}", "draft": False, "prerelease": False, "assets": [asset]}


class FakeHttp:
    def __init__(self, files=None, api=None, text=None, redirects=None):
        self.files = dict(files or {})
        self.api = dict(api or {})
        self.text = dict(text or {})
        self.redirects = dict(redirects or {})
        self.fetched = []

    def get_json(self, url):
        if url not in self.api:
            raise OSError(f"HTTP 403 rate limit exceeded: {url}")
        return self.api[url]

    def get_text(self, url):
        if url not in self.text:
            raise OSError(f"HTTP 404: {url}")
        return self.text[url]

    def resolve(self, url):
        if url not in self.redirects:
            raise OSError(f"HTTP 404: {url}")
        return self.redirects[url]

    def fetch(self, url, dest, *, max_bytes):
        self.fetched.append(url)
        if url not in self.files:
            raise OSError(f"HTTP 404: {url}")
        data = self.files[url]
        if len(data) > max_bytes:
            raise DownloadError(f"{url} is larger than {max_bytes} bytes")
        Path(dest).write_bytes(data)
        return _sha(data)


def write_local(root: Path, version: str) -> Path:
    pkg = root / "videotranslator"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(f'"""doc"""\n\n__version__ = "{version}"\n', encoding="utf-8")
    return root


class VersionTests(unittest.TestCase):
    def test_parse_version_accepts_tags_and_plain_versions(self):
        self.assertEqual(up.parse_version("v2.1.0"), (2, 1, 0))
        self.assertEqual(up.parse_version("2.10.3"), (2, 10, 3))

    def test_parse_version_rejects_everything_else(self):
        for text in ("v2.1", "latest", "v2.1.0-rc1", "", None, "v2.1.0.4", "vX.Y.Z"):
            with self.subTest(text=text):
                self.assertIsNone(up.parse_version(text))

    def test_versions_compare_as_numbers_not_text(self):
        self.assertTrue(up.is_newer((2, 10, 0), (2, 9, 9)))
        self.assertFalse(up.is_newer((2, 1, 0), (2, 1, 0)))
        self.assertFalse(up.is_newer((2, 0, 9), (2, 1, 0)))

    def test_unknown_local_version_means_update(self):
        self.assertTrue(up.is_newer((2, 1, 0), None))

    def test_read_local_version_parses_without_importing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(up.read_local_version(write_local(Path(tmp), "2.0.0")), (2, 0, 0))

    def test_read_local_version_missing_or_malformed_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(up.read_local_version(Path(tmp)))
            write_local(Path(tmp), "two")
            self.assertIsNone(up.read_local_version(Path(tmp)))


class LatestReleaseTests(unittest.TestCase):
    def test_api_release_with_digest(self):
        data = make_zip("2.1.0")
        http = FakeHttp(api={API: api_release("2.1.0", data=data)})
        rel = up.latest_release(http, log=lambda _m: None)
        self.assertEqual(rel.version, (2, 1, 0))
        self.assertEqual(rel.sha256, _sha(data))
        self.assertEqual(rel.url, asset_url("2.1.0"))

    def test_api_release_without_digest_uses_sha256_txt(self):
        data = make_zip("2.1.0")
        http = FakeHttp(api={API: api_release("2.1.0", digest=False)},
                        text={sums_url("2.1.0"): f"{_sha(data)}  VideoTranslatorAI-v2.1.0.zip\n"})
        self.assertEqual(up.latest_release(http, log=lambda _m: None).sha256, _sha(data))

    def test_api_down_falls_back_to_latest_redirect(self):
        data = make_zip("2.1.0")
        http = FakeHttp(redirects={LATEST_PAGE: f"https://github.com/{up.REPO}/releases/tag/v2.1.0"},
                        text={sums_url("2.1.0"): f"{_sha(data)} *VideoTranslatorAI-v2.1.0.zip\n"})
        rel = up.latest_release(http, log=lambda _m: None)
        self.assertEqual((rel.version, rel.url), ((2, 1, 0), asset_url("2.1.0")))

    def test_no_checksum_anywhere_is_refused(self):
        logs = []
        http = FakeHttp(api={API: api_release("2.1.0", digest=False)})
        self.assertIsNone(up.latest_release(http, log=logs.append))
        self.assertTrue(any("checksum" in line for line in logs))

    def test_asset_of_another_version_is_ignored(self):
        http = FakeHttp(api={API: api_release("2.1.0", name="VideoTranslatorAI-v2.0.0.zip")})
        self.assertIsNone(up.latest_release(http, log=lambda _m: None))

    def test_draft_or_prerelease_is_ignored(self):
        release = dict(api_release("2.1.0"), prerelease=True)
        self.assertIsNone(up.latest_release(FakeHttp(api={API: release}), log=lambda _m: None))

    def test_no_release_at_all(self):
        self.assertIsNone(up.latest_release(FakeHttp(), log=lambda _m: None))

    def test_malformed_api_answer_never_crashes(self):
        for answer in (None, [], "text", {"tag_name": "v2.1.0", "assets": "x"}, {"assets": [1]}):
            with self.subTest(answer=answer):
                self.assertIsNone(up.latest_release(FakeHttp(api={API: answer}), log=lambda _m: None))


class ExtractTests(unittest.TestCase):
    def _extract(self, data, version="2.1.0"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        archive = Path(tmp.name) / "r.zip"
        archive.write_bytes(data)
        dest = Path(tmp.name) / "out"
        return up.safe_extract(archive, dest, (2, 1, 0) if version == "2.1.0" else up.parse_version(version)), dest

    def test_good_archive_returns_the_top_folder(self):
        root, dest = self._extract(make_zip("2.1.0"))
        self.assertEqual(root, dest / "VideoTranslatorAI-v2.1.0")
        self.assertTrue((root / "setup_windows.bat").is_file())

    def test_rejects_zip_slip_and_absolute_paths(self):
        root = "VideoTranslatorAI-v2.1.0"
        for bad in (f"{root}/../evil.txt", "/etc/evil.txt", "C:/evil.txt", f"{root}\\..\\evil.txt"):
            with self.subTest(member=bad):
                with self.assertRaises(up.UpdateError):
                    self._extract(make_zip("2.1.0", extra={bad: b"x"}))

    def test_rejects_more_than_one_top_folder(self):
        with self.assertRaises(up.UpdateError):
            self._extract(make_zip("2.1.0", extra={"other/readme.txt": b"x"}))

    def test_rejects_archive_without_a_required_file(self):
        root = "VideoTranslatorAI-v2.1.0"
        full = {
            f"{root}/setup_windows.bat": b"@echo off\r\n",
            f"{root}/video_translator_gui.py": b"x\n",
            f"{root}/videotranslator/__init__.py": b'__version__ = "2.1.0"\n',
            f"{root}/videotranslator/updater.py": b"x\n",
        }
        for missing in list(full):
            with self.subTest(missing=missing):
                members = {k: v for k, v in full.items() if k != missing}
                with self.assertRaises(up.UpdateError):
                    self._extract(make_zip("2.1.0", members=members))

    def test_rejects_windows_aliases_and_streams(self):
        root = "VideoTranslatorAI-v2.1.0"
        for bad in (f"{root}/setup_windows.bat:evil", f"{root}/trailing.", f"{root}/space /x.py",
                    f"{root}/CON", f"{root}/sub/nul.txt", f"{root}/COM1.py"):
            with self.subTest(member=bad):
                with self.assertRaises(up.UpdateError):
                    self._extract(make_zip("2.1.0", extra={bad: b"x"}))

    def test_rejects_names_that_collide_when_case_folded(self):
        with self.assertRaises(up.UpdateError):
            self._extract(make_zip("2.1.0", extra={"VideoTranslatorAI-v2.1.0/SETUP_WINDOWS.BAT": b"x"}))

    def test_rejects_symbolic_links(self):
        name = "VideoTranslatorAI-v2.1.0/link.py"
        with self.assertRaises(up.UpdateError):
            self._extract(make_zip("2.1.0", extra={name: symlink_entry(name)}))

    def test_rejects_too_many_entries(self):
        original = up.MAX_ENTRIES
        up.MAX_ENTRIES = 3
        self.addCleanup(setattr, up, "MAX_ENTRIES", original)
        with self.assertRaises(up.UpdateError):
            self._extract(make_zip("2.1.0"))

    def test_rejects_version_that_does_not_match_the_tag(self):
        with self.assertRaises(up.UpdateError):
            self._extract(make_zip("2.0.0", root="VideoTranslatorAI-v2.1.0"))

    def test_rejects_archives_that_unpack_too_big(self):
        big = make_zip("2.1.0", extra={"VideoTranslatorAI-v2.1.0/big.bin": b"0" * 2048})
        original = up.MAX_UNPACKED_BYTES
        up.MAX_UNPACKED_BYTES = 1024
        self.addCleanup(setattr, up, "MAX_UNPACKED_BYTES", original)
        with self.assertRaises(up.UpdateError):
            self._extract(big)

    def test_nothing_is_written_when_the_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "r.zip"
            archive.write_bytes(make_zip("2.1.0", extra={"../evil.txt": b"x"}))
            with self.assertRaises(up.UpdateError):
                up.safe_extract(archive, Path(tmp) / "out", (2, 1, 0))
            self.assertFalse((Path(tmp) / "out").exists())
            self.assertFalse((Path(tmp) / "evil.txt").exists())


class DownloadTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dest = Path(tmp.name) / "update"

    def test_download_verifies_extracts_and_writes_the_handoff(self):
        data = make_zip("2.1.0")
        http = FakeHttp(files={asset_url("2.1.0"): data})
        rel = up.Release((2, 1, 0), "v2.1.0", "VideoTranslatorAI-v2.1.0.zip", asset_url("2.1.0"), _sha(data))
        bat = up.download(rel, self.dest, http, log=lambda _m: None)
        self.assertEqual(bat, self.dest / "VideoTranslatorAI-v2.1.0" / "setup_windows.bat")
        self.assertEqual((self.dest / up.HANDOFF_FILE).read_text(encoding="utf-8").strip(), str(bat))
        self.assertFalse(any(p.suffix in (".zip", ".part") for p in self.dest.iterdir()))

    def test_checksum_mismatch_leaves_nothing_behind(self):
        http = FakeHttp(files={asset_url("2.1.0"): make_zip("2.1.0")})
        rel = up.Release((2, 1, 0), "v2.1.0", "VideoTranslatorAI-v2.1.0.zip", asset_url("2.1.0"), "0" * 64)
        with self.assertRaises(up.UpdateError):
            up.download(rel, self.dest, http, log=lambda _m: None)
        self.assertEqual(list(self.dest.iterdir()) if self.dest.exists() else [], [])

    def test_old_update_folder_is_replaced(self):
        self.dest.mkdir(parents=True)
        (self.dest / "stale.txt").write_text("old")
        data = make_zip("2.1.0")
        http = FakeHttp(files={asset_url("2.1.0"): data})
        rel = up.Release((2, 1, 0), "v2.1.0", "VideoTranslatorAI-v2.1.0.zip", asset_url("2.1.0"), _sha(data))
        up.download(rel, self.dest, http, log=lambda _m: None)
        self.assertFalse((self.dest / "stale.txt").exists())


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.local = write_local(self.tmp / "local", "2.0.0")
        self.log = self.tmp / "setup.log"
        self.out = io.StringIO()

    def run_cli(self, argv, http):
        return up.main(argv, http=http, stdout=self.out)

    def test_check_reports_a_newer_release(self):
        http = FakeHttp(api={API: api_release("2.1.0")})
        code = self.run_cli(["check", "--local", str(self.local), "--log", str(self.log)], http)
        self.assertEqual(code, up.EXIT_NEWER)
        self.assertIn("2.1.0", self.out.getvalue())
        self.assertIn("2.1.0", self.log.read_text(encoding="utf-8"))

    def test_check_up_to_date(self):
        write_local(self.local, "2.1.0")
        http = FakeHttp(api={API: api_release("2.1.0")})
        self.assertEqual(self.run_cli(["check", "--local", str(self.local)], http), up.EXIT_OK)

    def test_check_without_any_release_cannot_check(self):
        self.assertEqual(self.run_cli(["check", "--local", str(self.local)], FakeHttp()),
                         up.EXIT_UNAVAILABLE)

    def test_download_success_and_handoff(self):
        data = make_zip("2.1.0")
        http = FakeHttp(api={API: api_release("2.1.0", data=data)}, files={asset_url("2.1.0"): data})
        dest = self.tmp / "update"
        code = self.run_cli(["download", "--local", str(self.local), "--dest", str(dest)], http)
        self.assertEqual(code, up.EXIT_NEWER)
        self.assertTrue((dest / up.HANDOFF_FILE).is_file())

    def test_download_removes_a_stale_handoff_when_already_current(self):
        write_local(self.local, "2.1.0")
        dest = self.tmp / "update"
        dest.mkdir()
        (dest / up.HANDOFF_FILE).write_text("C:\\old\\setup_windows.bat\n", encoding="utf-8")
        http = FakeHttp(api={API: api_release("2.1.0")})
        self.assertEqual(self.run_cli(["download", "--local", str(self.local), "--dest", str(dest)], http),
                         up.EXIT_OK)
        self.assertFalse((dest / up.HANDOFF_FILE).exists())

    def test_download_when_already_current_does_nothing(self):
        write_local(self.local, "2.1.0")
        http = FakeHttp(api={API: api_release("2.1.0")})
        dest = self.tmp / "update"
        self.assertEqual(self.run_cli(["download", "--local", str(self.local), "--dest", str(dest)], http),
                         up.EXIT_OK)
        self.assertEqual(http.fetched, [])
        self.assertFalse((dest / up.HANDOFF_FILE).exists())

    def test_download_rejected_archive(self):
        bad = make_zip("2.1.0", extra={"../evil.txt": b"x"})
        http = FakeHttp(api={API: api_release("2.1.0", data=bad)}, files={asset_url("2.1.0"): bad})
        code = self.run_cli(["download", "--local", str(self.local), "--dest", str(self.tmp / "u")], http)
        self.assertEqual(code, up.EXIT_REJECTED)

    def test_download_network_failure(self):
        http = FakeHttp(api={API: api_release("2.1.0")})   # asset URL missing: fetch fails
        code = self.run_cli(["download", "--local", str(self.local), "--dest", str(self.tmp / "u")], http)
        self.assertEqual(code, up.EXIT_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
